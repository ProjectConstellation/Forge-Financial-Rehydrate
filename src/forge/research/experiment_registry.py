"""Durable typed experiments with append-only decisions and independent paper/live evidence."""
from __future__ import annotations

import hashlib
import json
import math
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PaperHypothesis(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    objective_id: str = Field(min_length=1, max_length=120)
    mechanism: Literal['relative_momentum', 'dip_reversion', 'trend_following']
    symbol: Literal['QQQ', 'SPY', 'IWM', 'GLD', 'TLT'] = 'QQQ'
    lookback_sessions: Literal[10,20,40] = 20
    hypothesis: str = Field(min_length=10, max_length=1200)


def queue_paper_hypothesis(db, hypothesis: PaperHypothesis, source: str):
    payload=hypothesis.model_dump()
    identity=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:32]
    with db.transaction():
        queue=db.kv_get('research.paper_proposals') or []
        if any(row['id']==identity for row in queue):return {'id':identity,'state':'ALREADY_QUEUED'}
        if len(queue)>=50:raise ValueError('paper proposal queue full; reuse measured decisions')
        queue.append(dict(id=identity,**payload,source=source,ts=time.time(),authority='PAPER_ONLY',incremental_inference_usd=0.))
        db.kv_set('research.paper_proposals',queue)
    return {'id':identity,'state':'QUEUED_FOR_AUTOMATIC_PAPER_TRIAL','live_eligible':False}


def hypothesis_signal(mechanism, history, lookback=20):
    from forge.research.autonomous_equity import signal
    if lookback==20:return signal(mechanism,history)
    if len(history)<lookback+1:return False
    close=[float(b[0]['c']) for b in history];market=[float(b[1]['c']) for b in history]
    if not all(math.isfinite(v) and v>0 for v in close+market):return False
    if mechanism=='relative_momentum':return close[-1]/close[-lookback-1]-market[-1]/market[-lookback-1]>.01
    if mechanism=='dip_reversion':return close[-1]/close[-4]-1<-.02 and market[-1]>sum(market[-lookback:])/lookback
    if mechanism=='trend_following':return close[-1]>sum(close[-lookback:])/lookback and market[-1]>sum(market[-lookback:])/lookback
    raise ValueError('unknown mechanism')


class ExperimentContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    rail: Literal['alpaca.paper', 'crypto.paper', 'kalshi.paper']
    mechanism: Literal['relative_momentum', 'dip_reversion', 'trend_following']
    generation: int = Field(ge=1)
    capital_usd: float = Field(gt=0, allow_inf_nan=False)
    stop_loss_fraction: float = Field(default=.05, gt=0, le=.1)
    review_sessions: int = Field(default=20, ge=5, le=60)
    min_closed_trades: int = Field(default=3, ge=3)
    max_loss_usd: float = Field(gt=0, allow_inf_nan=False)
    registered_at: float = Field(gt=0, allow_inf_nan=False)
    evidence_after: str
    parameters: dict = Field(default_factory=dict)


class ExperimentRegistry:
    def __init__(self, db):
        self.db = db
        db.execute('CREATE TABLE IF NOT EXISTS economic_experiments (id TEXT PRIMARY KEY, contract TEXT NOT NULL, state TEXT NOT NULL, updated_at REAL NOT NULL, result TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS experiment_decisions (id INTEGER PRIMARY KEY, experiment_id TEXT NOT NULL, ts REAL NOT NULL, event TEXT NOT NULL, evidence TEXT NOT NULL)')

    def register(self, contract: ExperimentContract):
        raw = contract.model_dump_json()
        eid = hashlib.sha256(raw.encode()).hexdigest()[:32]
        with self.db.transaction():
            inserted = self.db.insert('economic_experiments',dict(id=eid,contract=raw,state='READY',updated_at=time.time()),or_ignore=True)
            if inserted:self.db.insert('experiment_decisions',dict(experiment_id=eid,ts=time.time(),event='REGISTERED',evidence=raw))
        return eid

    def transition(self, eid, event, evidence):
        allowed = {'READY': {'PAPER_RUNNING','BLOCKED','RETIRED'}, 'PAPER_RUNNING': {'MEASURED','BLOCKED'},
                   'BLOCKED': {'PAPER_RUNNING','RETIRED'}, 'MEASURED': {'RETAINED','RETIRED'},
                   'RETAINED':set(), 'RETIRED':set()}
        with self.db.transaction():
            row = self.db.query_one('SELECT * FROM economic_experiments WHERE id=?',(eid,))
            if not row or event not in allowed[row['state']]:raise ValueError('invalid experiment transition')
            payload = json.dumps(evidence,sort_keys=True,allow_nan=False)
            self.db.execute('UPDATE economic_experiments SET state=?,updated_at=?,result=? WHERE id=?',(event,time.time(),payload,eid))
            self.db.insert('experiment_decisions',dict(experiment_id=eid,ts=time.time(),event=event,evidence=payload))

    def measure(self, eid, *, trades, benchmark_usd, operating_cost_usd=0.):
        row=self.db.query_one('SELECT * FROM economic_experiments WHERE id=?',(eid,))
        contract=ExperimentContract.model_validate_json(row['contract'])
        if row['state']!='PAPER_RUNNING':raise ValueError('experiment not running')
        if not all(math.isfinite(float(v)) for v in (benchmark_usd,operating_cost_usd)) or operating_cost_usd<0:
            raise ValueError('invalid measured costs')
        if any(t['closed_at']<=contract.evidence_after or not math.isfinite(float(t['net_usd'])) for t in trades):
            raise ValueError('non-independent or invalid evidence')
        ids = [t.get('position_id') for t in trades]
        if any(not identity for identity in ids) or len(set(ids)) != len(ids):
            raise ValueError('trade evidence must have unique position identities')
        if any(t.get('opened_at', '') < contract.evidence_after for t in trades):
            raise ValueError('trade entered before registration')
        net=sum(float(t['net_usd']) for t in trades)-operating_cost_usd
        retained=len(trades)>=contract.min_closed_trades and net>max(0.,benchmark_usd)
        result=dict(net_usd=net,benchmark_usd=benchmark_usd,n_trades=len(trades),
                    operating_cost_usd=operating_cost_usd,earned_live_usd=0.,live_eligible=False,
                    result='RETAINED' if retained else 'RETIRED')
        with self.db.transaction():
            self.transition(eid,'MEASURED',result)
            self.transition(eid,result['result'],result)
        return result
