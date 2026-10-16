import asyncio
import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest

from forge.ledger.ledger import Ledger
from forge.treasury.spend_admission import inference_reserve, reserve, settle


@pytest.mark.parametrize('mode,authorized',[('PAPER',True),('SHADOW',True),('LIVE',False)])
def test_kalshi_never_submits_from_paper_or_without_live_authority(mode,authorized):
    from forge.opportunities.kalshi_live import KalshiLive
    rail = KalshiLive.__new__(KalshiLive)
    rail.f = SimpleNamespace(s=SimpleNamespace(mode=mode,live_trading=authorized))
    assert rail.decision()[0] == 0


def test_inference_reservation_uses_peak_price_even_offpeak(monkeypatch,db):
    from forge.brain.deepseek import DeepSeekClient
    from forge.config import DeepSeekConfig
    client = DeepSeekClient(DeepSeekConfig(), 'test', db, Ledger(db), 'paper')
    monkeypatch.setattr('forge.brain.deepseek.is_peak',lambda cfg:False)
    usage = dict(prompt_tokens=1000,completion_tokens=1000)
    assert client.cost('deepseek-flash',usage,worst_case=True) == pytest.approx(2*client.cost('deepseek-flash',usage))
    asyncio.run(client.close())


def reservation(db, key='experiment', cost=.01, budget=.1, ttl=60):
    return reserve(db,provider='deepseek',owner='critic',objective_id='objective',
                   experiment_key=key,max_cost_usd=cost,budget_usd=budget,spent_usd=0,ttl_s=ttl)


def test_atomic_concurrent_admission(db):
    with ThreadPoolExecutor(max_workers=16) as pool:
        results=list(pool.map(lambda i:reservation(db,str(i)),range(32)))
    assert sum(r['allowed'] for r in results)==10
    assert db.scalar("SELECT SUM(max_cost_usd) FROM spend_reservations")==pytest.approx(.1)


@pytest.mark.parametrize('cost',[0,-1,float('nan'),float('inf')])
def test_bad_spend_bounds(db,cost):
    assert not reservation(db,cost=cost)['allowed']


def test_uncertain_cost_is_not_free(db):
    r=reservation(db,cost=.1)
    db.execute('UPDATE spend_reservations SET expires_at=0')
    assert not reservation(db,key='other')['allowed']
    assert db.scalar('SELECT state FROM spend_reservations')=='UNCERTAIN'
    settle(db,r['reservation_id'],.02,'actual-receipt')
    assert reservation(db,key='after',cost=.01)['allowed']
    assert not reservation(db,key='after')['allowed']


def test_unknown_and_stale_provider_balance(db):
    args=dict(owner='critic',objective_id='test',experiment_key='test',max_cost_usd=.001,floor=.1)
    assert not inference_reserve(db,**args)['allowed']
    db.kv_set('deepseek.sentinel',{'balance':1,'checked':datetime.fromtimestamp(time.time()-601,UTC).isoformat()})
    assert not inference_reserve(db,**args)['allowed']
    db.kv_set('deepseek.sentinel',{'balance':1,'checked':datetime.now(UTC).isoformat()})
    assert inference_reserve(db,**args)['allowed']


def add_position(db,book='paper',pnl=1000,fees=1,status='CLOSED'):
    stamp=datetime.now(UTC).isoformat()
    db.insert('positions',dict(id=book,book=book,venue='coinbase',symbol='BTC-USD',strategy_id='test',
                              status=status,cost_usd=10,realized_pnl_usd=pnl,fees_usd=fees,
                              opened_at=stamp,closed_at=stamp))


def test_paper_profit_and_deposits_never_fund_inference(db):
    from forge.treasury.intelligence import profit_7d
    led=Ledger(db)
    led.deposit('live',Decimal('50000'))
    add_position(db)
    assert profit_7d(db)==0
    add_position(db,'live',10,1)
    led.record_opex('paper','COMPUTE',Decimal('20'),'job')
    assert profit_7d(db)==-11


def test_canonical_true_net_books_and_costs(db):
    from forge.treasury.economic_truth import realized_window
    led=Ledger(db)
    led.deposit('live',Decimal('2000'))
    add_position(db,'paper',10000)
    add_position(db,'live',10,1)
    led.record_opex('paper','COMPUTE',Decimal('2'),'job')
    led.record_opex('paper','INFERENCE',Decimal('.1'),'call')
    led.record_opex('paper','DATA',Decimal('.5'),'data')
    result=realized_window(db,time.time()-3600,time.time())
    assert result['net_usd']==pytest.approx(6.4)
    assert result['settled_income_usd']==9
    assert result['operating_cost_usd']==pytest.approx(2.6)


def test_budget_scales_with_real_net_income(db):
    from forge.treasury.spend_admission import inference_runway
    assert inference_runway(db)==7
    add_position(db,'paper',100000)
    assert inference_runway(db)==7
    add_position(db,'live',100,0)
    Ledger(db).record_opex('paper','INFERENCE',Decimal('10'),'call')
    assert inference_runway(db)==1.5


def test_treasury_does_not_lock_real_cash_for_paper(db):
    from forge.treasury.truth import TreasuryTruth
    add_position(db,'paper',0,0,'OPEN')
    db.kv_set('velocity',{'ts':time.time(),'treasury':{'coinbase':28,'kalshi':0,'total':28}})
    f=SimpleNamespace(db=db,book='paper',treasury={'equity_usd':23})
    r=TreasuryTruth(f).compute()
    assert r['live_nav']==28 and r['paper_nav']==23
    assert r['capital_locked']==0 and r['paper_capital_deployed']==10
    assert r['investment_cash_available']==28
    assert r['reconciliation']['ok'] is None


def test_workflow_invalid_stage_and_structural_failure_are_atomic(db):
    from forge.agents.workflow_engine import WorkflowEngine
    engine=WorkflowEngine(SimpleNamespace(db=db))
    wid=engine.start_income('test',{'rail':'test','family':'test','needs_early_exec':False})
    assert engine.advance(wid,'ops','CLOSE_LEARN',{})['error']=='unexpected_role_or_stage'
    assert db.scalar("SELECT COUNT(*) FROM agent_handoffs WHERE status='PENDING'")==1
    engine.advance(wid,'scout','ANOMALY_DETECT',{})
    result=engine.advance(wid,'alpha_inventor','STRATEGY_ALGORITHM',{})
    assert result['error']=='income_requires_strategy_and_algorithm'
    assert db.scalar("SELECT COUNT(*) FROM agent_handoffs WHERE status='PENDING'")==1
    assert db.scalar("SELECT stage FROM agent_workflows")=="STRATEGY_ALGORITHM"


def test_replay_and_self_reported_earnings_do_not_count(db):
    from forge.agents.workflow_engine import WorkflowEngine
    engine=WorkflowEngine(SimpleNamespace(db=db))
    wid=engine.start_income('test',{'rail':'test','family':'test'})
    result=engine.advance(wid,'scout','ANOMALY_DETECT',{'delta_usd_per_h':999},result_type='VETO')
    assert result['status']=='DONE'
    assert engine.advance(wid,'scout','ANOMALY_DETECT',{})['error']=='workflow_already_closed'
    assert db.kv_get('lab.money_scorecard')['totals']['sum_delta_usd_per_h']==0


def test_diagnostic_language_cannot_be_an_earner(db):
    from forge.agents.results_enforcer import ResultsEnforcer
    result=ResultsEnforcer(SimpleNamespace(db=db)).score_report('critic','OK',{
        'result_type':'ACTION_TAKEN','summary':'PASS workflow implemented challenger allocated',
        'economic_attribution':{'delta_usd_per_h':100},'evidence_refs':['report']},closed_directives=4,handoffs_out=3)
    assert result['grade']!='EARNER'
    assert result['outcome_class']=='UNPRODUCTIVE'


def test_expired_contamination_cannot_rehabilitate_old_data(db):
    from forge.agents.opportunity_memory import OpportunityMemory
    from forge.treasury.evidence_eligibility import income_block
    memory=OpportunityMemory(SimpleNamespace(db=db))
    memory.record_negative(family='stable_triangle',rail='coinbase.stable_triangle',status='CONTAMINATED',
                           reason='bad accounting',expires_at=0)
    assert income_block(db,'coinbase.stable_triangle')
    assert not income_block(db,'kalshi.TAKE_THRESH')


def test_risk_sets_are_json_serializable():
    import json
    from forge.api.firm_v1 import _j
    assert json.loads(_j({'breakers':{'STOPPED'}}).body)=={'breakers':['STOPPED']}


def test_alpaca_paper_endpoint_cannot_inherit_live(monkeypatch):
    from forge.venues.alpaca import AlpacaClient
    monkeypatch.setenv('APCA_API_BASE_URL','https://api.alpaca.markets')
    with pytest.raises(ValueError,match='Paper training'):
        AlpacaClient(key_id='dummy',secret='dummy',paper=True)
    with pytest.raises(ValueError):
        AlpacaClient(key_id='dummy',secret='dummy',base_url='https://paper-api.attacker.invalid')


@pytest.mark.asyncio
async def test_alpaca_order_validation_and_global_stop(monkeypatch):
    from forge.venues.alpaca import AlpacaClient
    import forge.opportunities.alpaca_bankroll as bankroll
    monkeypatch.delenv('APCA_API_BASE_URL',raising=False)
    c=AlpacaClient(key_id='dummy',secret='dummy',paper=True)
    with pytest.raises(ValueError):
        await c.submit_order(symbol='SPY',qty=1,notional=1,client_order_id='same')
    monkeypatch.setattr(bankroll,'read_runtime_state',lambda key:{'state':'STOPPED'})
    with pytest.raises(RuntimeError,match='global state'):
        await c.submit_order(symbol='SPY',notional=1,client_order_id='same')
    with pytest.raises(ValueError,match='extended'):
        await c.submit_order(symbol='SPY',notional=1,client_order_id='same',extended_hours=True)
    await c.close()


@pytest.mark.parametrize('size',[0,-1,float('nan'),float('inf')])
def test_bad_training_sizes(size):
    from forge.opportunities.alpaca_bankroll import PaperBankrollPolicy
    p=PaperBankrollPolicy.from_env(treasury_nav=28)
    assert p.bankroll_usd==50
    assert not p.allow_order(notional_usd=size,open_usd=0,n_positions=0)[0]


def test_curriculum_next_open_and_no_fake_earnings():
    from forge.research.alpaca_curriculum import evaluate_residual_momentum
    from datetime import timedelta
    start=datetime(2025,1,1, tzinfo=UTC)
    bars=[{'t':(start+timedelta(days=i)).isoformat(),'o':100+i,'c':100+i} for i in range(150)]
    benchmark=[dict(b,o=100,c=100) for b in bars]
    r=evaluate_residual_momentum(bars,benchmark,50)
    assert r['earned_usd']==0 and r['evidence_verdict']=='INSUFFICIENT_INDEPENDENT_EVIDENCE'
    assert all(t['signal_at']<t['entry_at']<t['exit_at'] for t in r['trades'])


@pytest.mark.asyncio
async def test_deepseek_denied_before_http(db):
    from forge.brain.deepseek import DeepSeekClient
    from forge.config import DeepSeekConfig
    db.kv_set('intelligence.admission',{'enabled':True})
    requests=[]
    transport=httpx.MockTransport(lambda req:requests.append(req) or httpx.Response(200,json={}))
    client=DeepSeekClient(DeepSeekConfig(), 'dummy',db,Ledger(db),'paper',transport=transport)
    with pytest.raises(RuntimeError,match='admission denied'):
        await client.chat([{'role':'user','content':'test'}],agent='critic',purpose='test')
    assert not requests
    await client.close()

@pytest.mark.asyncio
async def test_modal_requires_experiment_even_in_recovery(db):
    from forge.compute.modal_client import ComputeGovernor
    from forge.config import Settings
    f=SimpleNamespace(db=db,s=Settings(),treasury={'regime':{'name':'SURVIVAL'}},
                      reg=SimpleNamespace(counts=lambda:{}))
    governor=ComputeGovernor(f)
    assert not await governor.should_burst(f,3600)
    db.kv_set('modal.experiment',{'status':'APPROVED','objective_id':'objective','experiment_key':'test',
              'evidence_version':'v1','decision':'falsify mechanism','abort_criteria':'no improvement',
              'consumer':'evolution','interval':3600,'ts':time.time(),'containers':1,'timeout_s':30,'max_cost_usd':1})
    assert await governor.should_burst(f,3600)
    assert not await governor.should_burst(f,300)


def test_inference_proxy_auth_and_completion(db):
    from fastapi import FastAPI,HTTPException
    from fastapi.testclient import TestClient
    from forge.api.inference_proxy import mount
    from forge.config import Settings
    async def chat(*a,**kw):
        return SimpleNamespace(call_id='llm_test',model='deepseek-flash',tool_calls=[],
                               usage={'prompt_tokens':2,'completion_tokens':1},raw_message={'content':'OK'})
    f=SimpleNamespace(s=Settings(),brain=SimpleNamespace(c=SimpleNamespace(chat=chat)))
    def check(req):
        if req.headers.get('authorization')!='Bearer test':raise HTTPException(401)
    app=FastAPI();mount(app,f,check)
    with TestClient(app) as client:
        path='/api/agent/inference/v1/chat/completions'
        body={'model':'deepseek-flash','messages':[{'role':'user','content':'[forge-role:critic] test'}]}
        assert client.post(path,json=body).status_code==401
        r=client.post(path,json=body,headers={'Authorization':'Bearer test'})
        assert r.json()['choices'][0]['message']['content']=='OK'
        body['stream']=True
        assert 'data: [DONE]' in client.post(path,json=body,headers={'Authorization':'Bearer test'}).text

@pytest.mark.asyncio
async def test_alpaca_requests_recent_completed_bars(monkeypatch):
    from forge.venues.alpaca import AlpacaClient
    monkeypatch.delenv('APCA_API_BASE_URL',raising=False)
    c=AlpacaClient(key_id='dummy',secret='dummy',paper=True)
    seen={}
    async def req(*a,**kw):
        seen.update(kw);return {'bars':[]}
    c.req=req
    await c.bars('SPY',limit=300)
    assert seen['params']['sort']=='desc'
    assert seen['params']['feed']=='iex'
    assert datetime.fromisoformat(seen['params']['end']).hour==0
    await c.close()
