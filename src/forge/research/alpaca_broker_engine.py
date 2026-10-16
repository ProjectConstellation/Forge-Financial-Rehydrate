"""Autonomous broker-paper experiments through the existing deterministic Forge gateway."""
from __future__ import annotations

import asyncio
import fcntl
import json
import logging
import os
import time
from datetime import UTC, datetime
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from forge.audit.journal import AuditJournal
from forge.core.ids import idempotency_key
from forge.domain.market import BestBidAsk
from forge.domain.trading import TradeIntent, IntentPurpose, ExitPlan, RiskVerdict
from forge.execution.gateway import ExecutionGateway, MarketView
from forge.ledger.ledger import Ledger
from forge.opportunities.alpaca_bankroll import PaperBankrollPolicy, read_runtime_state
from forge.persistence.db import Database, dumps
from forge.research.autonomous_equity import MECHANISMS, signal
from forge.research.experiment_registry import ExperimentContract, ExperimentRegistry, PaperHypothesis, hypothesis_signal
from forge.risk.breakers import BreakerBoard
from forge.risk.governor import RiskGovernor, RiskContext
from forge.treasury.regimes import CapitalRegimeEngine
from forge.venues.alpaca import AlpacaClient
from forge.venues.alpaca_paper_adapter import AlpacaPaperAdapter

D=Decimal
log=logging.getLogger('forge.alpaca_broker')


class BrokerExperimentEngine:
    def __init__(self, root, client):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.db=Database(self.root/'state/forge.sqlite');self.db.migrate()
        self.ledger=Ledger(self.db);self.registry=ExperimentRegistry(self.db)
        self.venue=AlpacaPaperAdapter(client,self.db,self.ledger)
        self.bbos={};self.rules={};self.breakers=BreakerBoard();self.risk=RiskGovernor()
        self.gateway=ExecutionGateway(self.db,self.ledger,self.venue,'paper',
            MarketView(self.bbos.get,self.rules.get),AuditJournal(self.root/'audit'),self.breakers,
            taker_fee=.0005,maker_fee=.0005)
        self.history=[];self.history_at=0.;self.last_session=None
        self.treasury_checked=0.;self.recon=None;self.clock={};self.account={}
        self.active_id=None

    def bootstrap(self, policy):
        existing=self.db.kv_get('broker.contract')
        if existing:
            with self.db.transaction():
                # An increase is explicitly simulated capital from the founder's stage policy.
                # It is never attributed as earned income, nor inferred from broker toy equity.
                if policy.treasury_nav_usd>0 and policy.bankroll_usd>existing['bankroll_usd']:
                    delta=policy.bankroll_usd-existing['bankroll_usd']
                    self.ledger.deposit('paper',D(str(delta)),memo='simulated stage-policy capital increase',
                                        ref_id=f"alpaca-training-policy-{policy.bankroll_usd}")
                    existing['bankroll_usd']=policy.bankroll_usd
                existing['max_order_usd']=policy.max_per_order_usd
                existing['max_open_usd']=policy.max_open_usd
                existing['max_positions']=min(2,policy.max_positions)
                self.db.kv_set('broker.contract',existing)
            return existing
        contract=dict(bankroll_usd=policy.bankroll_usd,max_order_usd=min(10.,policy.max_per_order_usd),
                      max_open_usd=policy.max_open_usd,max_positions=min(2,policy.max_positions),
                      cost_basis='actual_paper_fill_prices_plus_assumed_5bps_fee_per_leg',
                      authority='PAPER_ONLY',registered_at=datetime.now(UTC).isoformat())
        with self.db.transaction():
            self.ledger.deposit('paper',D(str(policy.bankroll_usd)),memo='isolated broker training seed',ref_id='alpaca-paper-bootstrap-v1')
            self.db.kv_set('broker.contract',contract)
        return contract

    def experiment(self, contract):
        current=self.db.kv_get('broker.current_experiment')
        if current:
            if 'capital_usd' not in current:
                row=self.db.query_one('SELECT contract FROM economic_experiments WHERE id=?',(current['id'],))
                current['capital_usd']=ExperimentContract.model_validate_json(row['contract']).capital_usd
                self.db.kv_set('broker.current_experiment',current)
            return current
        generation=int(self.db.kv_get('broker.generation') or 1)
        after=datetime.now(UTC).isoformat()
        mechanism=MECHANISMS[(generation-1)%len(MECHANISMS)]
        proposal=None
        consumed=self.db.kv_get('broker.consumed_proposals') or []
        queue=read_runtime_state('research.paper_proposals') or []
        if not isinstance(queue,list):queue=[]
        retained=self.db.kv_get('broker.retained_spec')
        for row in ([] if retained else queue):
            if row.get('id') in consumed:continue
            proposal=PaperHypothesis.model_validate({k:row[k] for k in ('objective_id','mechanism','symbol','lookback_sessions','hypothesis')})
            consumed.append(row['id'])
            break
        if proposal:mechanism=proposal.mechanism
        symbol=proposal.symbol if proposal else 'QQQ'
        lookback=proposal.lookback_sessions if proposal else (20,10,40)[((generation-1)//3)%3]
        if retained:
            mechanism=retained['mechanism'];symbol=retained['symbol'][:-4];lookback=retained['lookback']
        state=self.ledger.state('paper')
        capital=min(contract['max_order_usd'],contract['max_open_usd'],max(1.,float(state.cash_usd)*.2))
        spec=ExperimentContract(rail='alpaca.paper',mechanism=mechanism,generation=generation,
             capital_usd=capital,max_loss_usd=capital*.1,
             registered_at=time.time(),evidence_after=after,
             parameters={'lookback':lookback,'hold_days':7,'symbol':symbol+'-USD','round_trip_fee_bps':10,
                         'objective_id':proposal.objective_id if proposal else 'autonomous_equity_improvement'})
        with self.db.transaction():
            eid=self.registry.register(spec)
            self.registry.transition(eid,'PAPER_RUNNING',{'source':'autonomous_broker_engine','mode':'paper'})
            current=dict(id=eid,mechanism=mechanism,generation=generation,sessions=0,last_session=None,first_mid=None,
                         symbol=symbol+'-USD',lookback=lookback,capital_usd=capital)
            self.db.kv_set('broker.current_experiment',current)
            self.db.kv_set('broker.consumed_proposals',consumed)
        return current

    async def tick(self):
        now=time.time();policy=PaperBankrollPolicy.from_env();contract=self.bootstrap(policy)
        current=self.experiment(contract);symbol=current['symbol'];ticker=symbol[:-4]
        if self.active_id!=current['id']:
            self.active_id=current['id'];self.history=[];self.history_at=0.;self.bbos.clear();self.rules.clear()
        authority=read_runtime_state('trading.state') or {};trading=authority.get('state','STOPPED')
        if now-self.treasury_checked>=30:
            self.clock,self.account=await asyncio.gather(self.venue.client.clock(),self.venue.client.account())
            self.treasury_checked=now
        market_open=bool(self.clock.get('is_open'))
        if market_open:
            quote=(await self.venue.client.latest_quote(ticker)).get('quote') or {}
            if quote.get('t'):
                ts=datetime.fromisoformat(quote['t'].replace('Z','+00:00')).timestamp()
                bid,ask=float(quote.get('bp') or 0),float(quote.get('ap') or 0)
                if 0<=time.time()-ts<=30 and 0<bid<=ask:
                    self.bbos[symbol]=BestBidAsk('alpaca',symbol,bid,float(quote.get('bs') or 0),ask,float(quote.get('as') or 0),int(ts*1e9),time.time_ns())
                else:self.bbos.clear()
            else:self.bbos.clear()
            if not self.rules:self.rules[symbol]=await self.venue.get_market_rules(symbol)
        else:self.bbos.clear()
        # Refresh/cancel orders even when stopped or closed. Stale quotes never trigger exits.
        await self.gateway.tick(trading_state=trading)
        if trading=='STOPPED' and authority.get('safe_stop_policy')=='flatten_when_safe' and self.bbos:
            await self.gateway.liquidate('EMERGENCY')
        if now-self.history_at>=3600 and market_open:
            qqq,spy=await asyncio.gather(self.venue.client.bars(ticker,limit=100),self.venue.client.bars('SPY',limit=100))
            market={str(b['t'])[:10]:b for b in spy.get('bars') or []}
            self.history=[(b,market[str(b['t'])[:10]]) for b in sorted(qqq.get('bars') or [],key=lambda b:b['t']) if str(b['t'])[:10] in market]
            self.history_at=now
        if now-self.db.kv_get('broker.reconciled_at',0)>=30:
            self.recon=await self.venue.reconcile();self.db.kv_set('broker.reconciled_at',now)
            self.db.kv_set('broker.reconciliation',dict(ts=now,ok=self.recon.ok,issues=self.recon.issues))
        current=self.experiment(contract)
        today=datetime.now(UTC).date().isoformat()
        if market_open and current['last_session']!=today:
            current['sessions']+=1;current['last_session']=today
            if self.bbos:current['first_mid']=current['first_mid'] or self.bbos[symbol].mid
            self.db.kv_set('broker.current_experiment',current)
        positions=self.db.query("SELECT * FROM positions WHERE status!='CLOSED'")
        closed=self.db.query("SELECT id,opened_at,closed_at,realized_pnl_usd,fees_usd FROM positions WHERE status='CLOSED' AND strategy_id=? AND exit_reason!='ENTRY_REJECTED' AND CAST(cost_usd AS REAL)>0",(current['id'],))
        net=sum(float(p['realized_pnl_usd'])-float(p['fees_usd']) for p in closed)
        capital=current.get('capital_usd',contract['max_order_usd'])
        review=current['sessions']>=20 or net<=-capital*.1
        if review and not positions and self.bbos:
            trades=[dict(position_id=p['id'],opened_at=p['opened_at'],closed_at=p['closed_at'],net_usd=float(p['realized_pnl_usd'])-float(p['fees_usd'])) for p in closed]
            baseline=capital*(self.bbos[symbol].mid/current['first_mid']-1-.001) if current['first_mid'] else 0.
            result=self.registry.measure(current['id'],trades=trades,benchmark_usd=baseline)
            generation=current['generation']+(3 if result['result']=='RETAINED' else 1)
            with self.db.transaction():
                self.db.kv_set('broker.retained_spec',current if result['result']=='RETAINED' else None)
                self.db.kv_set('broker.generation',generation);self.db.kv_set('broker.current_experiment',None)
            current=self.experiment(contract)
            self.bbos.clear();self.history=[]
        bbo=self.bbos.get(current['symbol']);state=self.ledger.state('paper')
        lifetime_net=state.realized_pnl_usd-state.fees_usd
        reason='AWAITING_SIGNAL'
        if trading!='RUNNING':reason='GLOBAL_'+trading
        elif not market_open:reason='SESSION_CLOSED'
        elif not bbo:reason='QUOTE_STALE_OR_MISSING'
        elif not self.recon or not self.recon.ok:reason='RECONCILIATION_REQUIRED'
        elif positions:reason='MANAGING_EXISTING_POSITION'
        elif review:reason='REVIEW_PENDING'
        elif lifetime_net<=-D(str(contract['bankroll_usd']))*D('.1'):reason='SHARED_PAPER_LOSS_STOP'
        elif (signal(current['mechanism'],self.history) if current['lookback']==20 else hypothesis_signal(current['mechanism'],self.history,current['lookback'])):
            history_day=str(self.history[-1][0]['t'])[:10]
            if (datetime.fromisoformat(today)-datetime.fromisoformat(history_day)).days>7:
                reason='HISTORICAL_INPUT_STALE'
            else:
                idem=idempotency_key('alpaca',current['id'],today)
                if self.db.scalar('SELECT 1 FROM trade_intents WHERE idem_key=?',(idem,)):
                    reason='SIGNAL_ALREADY_ATTEMPTED'
                else:
                    reason=await self.enter(current,contract,state,bbo,idem,trading)
        report=dict(ts=now,mode='ALPACA_BROKER_PAPER',authority=trading,status=reason,
             experiment=current,open_positions=self.gateway.open_summary(),
             paper_cash_usd=float(state.cash_usd),paper_closed_net_usd=float(lifetime_net),
             live_income_usd=0.,live_eligible=False,cost_basis=contract['cost_basis'],
             reconciliation=self.db.kv_get('broker.reconciliation'),contract=contract)
        self.db.kv_set('broker.status',report)
        dest=self.root.parent/'alpaca_broker_trials.json';tmp=dest.with_suffix('.tmp')
        tmp.write_text(json.dumps(report,indent=2)+'\n');os.replace(tmp,dest)
        return report

    async def enter(self,current,contract,state,bbo,idem,trading):
        equity=state.cash_usd+sum(h.qty*D(str(bbo.bid)) for h in state.holdings.values())
        policy=replace(CapitalRegimeEngine().policy(equity),max_concurrent_positions=contract['max_positions'])
        amount=min(D(str(current.get('capital_usd',contract['max_order_usd']))),D(str(contract['max_order_usd'])),D(str(contract['max_open_usd'])))
        intent=TradeIntent(id=idem,ts_ns=time.time_ns(),book='paper',opportunity_id=None,strategy_id=current['id'],
            venue='alpaca',symbol=current['symbol'],side='buy',purpose=IntentPurpose.ENTRY,requested_notional_usd=amount,
            order_type='market',exit_plan=ExitPlan(take_profit_pct=1.,stop_loss_pct=.05,time_stop_s=7*86400,exit_order='taker'),
            evidence={'family':current['mechanism'],'paper_hypothesis_only':True},idem_key=idem)
        # Positive net is a preregistered PAPER hypothesis, not empirical live permission.
        context=RiskContext(trading_state=trading,mode='PAPER',now_ns=time.time_ns(),equity_usd=equity,
            cash_available_usd=state.cash_usd,reserve_required_usd=equity*D('.1'),exit_buffer_usd=D('.10'),
            deployed_usd=D(0),open_positions=0,family_exposure_usd={},policy=policy,
            treasury_snapshot_age_s=time.time()-self.treasury_checked,reconciliation_ok=self.recon.ok,
            market_fresh=time.time_ns()-bbo.exchange_ts_ns<=30_000_000_000,book_valid=True,
            spread_bps=bbo.spread_bps,rules=self.rules.get(current['symbol']),
            daily_pnl_usd=state.realized_pnl_usd-state.fees_usd,day_start_equity_usd=D(str(contract['bankroll_usd'])),
            expected_net_bps=1.,est_cost_bps=bbo.spread_bps+10.,breakers=self.breakers.blocking())
        decision=self.risk.evaluate(intent,context)
        with self.db.transaction():
            self.db.insert('trade_intents',dict(id=intent.id,ts=datetime.now(UTC).isoformat(),book='paper',opportunity_id=None,
                 strategy_id=intent.strategy_id,venue='alpaca',symbol=intent.symbol,side='buy',purpose='entry',
                 requested_notional=str(amount),approved_notional=str(decision.approved_notional_usd),order_type='market',
                 max_slippage_bps=str(intent.max_slippage_bps),exit_plan=dumps(intent.exit_plan.model_dump()),
                 evidence=dumps(intent.evidence),status=decision.verdict.value,idem_key=idem))
            self.db.insert('risk_decisions',dict(intent_id=intent.id,ts=datetime.now(UTC).isoformat(),decision=decision.verdict.value,
                 approved_notional=str(decision.approved_notional_usd),reasons=dumps(decision.reasons),checks=dumps(decision.checks)))
        if decision.verdict==RiskVerdict.REJECT:return 'RISK_REJECTED'
        pid=await self.gateway.execute_entry(intent,decision,ttl_s=60,maker_offset_bps=0,entry_style='taker',
                                             meta={'experiment_id':current['id'],'flatten_on_stop':False})
        return 'ORDER_PERSISTED' if pid else 'ENTRY_REJECTED'

    async def close(self):
        await self.venue.close();self.db.close()


async def main():
    root=Path(os.environ.get('FORGE_HOME','/srv/forge/var'))/'alpaca-broker'
    root.mkdir(parents=True,exist_ok=True)
    with (root/'engine.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        engine=BrokerExperimentEngine(root,AlpacaClient(paper=True))
        try:
            while True:
                try:
                    report=await engine.tick()
                    log.info('paper engine status=%s',report['status'])
                except Exception as exc:
                    # Retain positions/reservations; no random retry order or fabricated success.
                    log.error('paper engine tick blocked: %s',type(exc).__name__)
                    dest=root.parent/'alpaca_broker_trials.json'
                    report=engine.db.kv_get('broker.status') or {'mode':'ALPACA_BROKER_PAPER','live_income_usd':0.}
                    last_success=report.get('last_success_ts') or report.get('ts')
                    report.update(ts=time.time(),status='TICK_BLOCKED',error_type=type(exc).__name__,
                                  last_success_ts=last_success)
                    tmp=dest.with_suffix('.tmp');tmp.write_text(json.dumps(report,indent=2)+'\n');os.replace(tmp,dest)
                await asyncio.sleep(15 if engine.clock.get('is_open') else 60)
        finally:await engine.close()


if __name__=='__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
