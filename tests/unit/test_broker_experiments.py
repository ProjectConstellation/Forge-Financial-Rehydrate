import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from types import SimpleNamespace

import pytest

from forge.ledger.ledger import Ledger
from forge.domain.trading import OrderRequest, OrderStatus
from forge.research.experiment_registry import ExperimentContract, ExperimentRegistry
from forge.research.alpaca_broker_engine import BrokerExperimentEngine
from forge.venues.alpaca_paper_adapter import AlpacaPaperAdapter
from forge.venues.base import VenueError


class FakeBroker:
    is_paper=True
    def __init__(self):
        self.orders_data={};self.fill_data=[];self.held=D(0);self.submitted=0;self.open=True
    async def account(self):return {'cash':'100000','equity':'100000','status':'ACTIVE'}
    async def clock(self):return {'is_open':self.open}
    async def asset(self,symbol):return {'tradable':True,'status':'active','fractionable':True}
    async def positions(self):return [{'symbol':'QQQ','qty':str(self.held)}] if self.held else []
    async def orders(self,**kw):return [o for o in self.orders_data.values() if o['status']!='filled']
    async def latest_quote(self,symbol):return {'quote':{'t':datetime.now(UTC).isoformat(),'bp':99.99,'ap':100.,'bs':100,'as':100}}
    async def bars(self,symbol,limit):
        return {'bars':[{'t':(datetime.now(UTC)-timedelta(days=30-i)).isoformat(),'o':80+i*.5,'c':80+i*.5} for i in range(30)]}
    async def submit_order(self,**body):
        self.submitted+=1;cid=body['client_order_id'];qty=D(body['qty']) if body.get('qty') else D(body['notional'])/D(100)
        self.held+=qty if body['side']=='buy' else -qty
        row=dict(id='vid-'+cid,client_order_id=cid,symbol='QQQ',side=body['side'],status='filled',
                 qty=str(qty),filled_qty=str(qty),filled_avg_price='100',created_at=datetime.now(UTC).isoformat())
        self.orders_data[cid]=row
        self.fill_data.append(dict(id='fid-'+cid,order_id=row['id'],price='100',qty=str(qty),side=body['side'],transaction_time=row['created_at']))
        return row
    async def req(self,method,path,**kw):
        if path.endswith('by_client_order_id'):return self.orders_data[kw['params']['client_order_id']]
        if path.endswith('FILL'):return self.fill_data
        raise AssertionError(path)
    async def cancel_order(self,vid):
        for row in self.orders_data.values():
            if row['id']==vid:row['status']='canceled'
    async def close(self):pass


def test_registry_requires_typed_transition_and_future_evidence(db):
    r=ExperimentRegistry(db)
    c=ExperimentContract(rail='alpaca.paper',mechanism='relative_momentum',generation=1,
                         capital_usd=10,max_loss_usd=1,registered_at=1,evidence_after='2026-10-09')
    eid=r.register(c);assert r.register(c)==eid
    assert db.scalar('SELECT COUNT(*) FROM experiment_decisions')==1
    with pytest.raises(ValueError):r.transition(eid,'RETAINED',{})
    r.transition(eid,'PAPER_RUNNING',{})
    with pytest.raises(ValueError):r.measure(eid,trades=[dict(closed_at='2026-10-08',net_usd=1)],benchmark_usd=0)
    result=r.measure(eid,trades=[dict(position_id=str(i),opened_at='2026-10-09',closed_at='2026-10-10',net_usd=1) for i in range(3)],benchmark_usd=1)
    assert result['result']=='RETAINED' and not result['live_eligible'] and result['earned_live_usd']==0


def test_broker_closed_session_no_orders(tmp_path,monkeypatch):
    async def scenario():
        broker=FakeBroker();broker.open=False
        engine=BrokerExperimentEngine(tmp_path/'alpaca-broker',broker)
        monkeypatch.setattr('forge.research.alpaca_broker_engine.read_runtime_state',lambda key: {'state':'RUNNING'})
        report=await engine.tick()
        assert report['status']=='SESSION_CLOSED' and broker.submitted==0
        assert report['paper_cash_usd']<=50 and report['live_income_usd']==0
        await engine.close()
    asyncio.run(scenario())


def test_complete_broker_entry_exit_restart_idempotent(tmp_path,monkeypatch):
    async def scenario():
        broker=FakeBroker();root=tmp_path/'alpaca-broker'
        monkeypatch.setattr('forge.research.alpaca_broker_engine.read_runtime_state',lambda key: {'state':'RUNNING'})
        monkeypatch.setattr('forge.research.alpaca_broker_engine.signal',lambda mechanism,history:True)
        engine=BrokerExperimentEngine(root,broker)
        assert (await engine.tick())['status']=='ORDER_PERSISTED'
        assert broker.submitted==1
        await engine.tick()
        assert engine.db.scalar('SELECT COUNT(*) FROM fills')==1
        assert engine.ledger.check_balanced('paper')==0
        await engine.close()
        engine=BrokerExperimentEngine(root,broker)
        await engine.tick()
        assert broker.submitted==1 and engine.db.scalar('SELECT COUNT(*) FROM fills')==1
        assert engine.db.scalar("SELECT COUNT(*) FROM positions WHERE status='OPEN'")==1
        await engine.gateway.liquidate('TEST_EXIT')
        await engine.tick()
        assert broker.held==0 and broker.submitted==2
        assert engine.db.scalar('SELECT COUNT(*) FROM fills')==2
        assert engine.ledger.check_balanced('paper')==0
        assert engine.ledger.state('paper').cash_usd==engine.ledger.state('paper').contributed_usd-sum(D(row['fee']) for row in engine.db.query('SELECT fee FROM fills'))
        await engine.close()
    asyncio.run(scenario())


def test_global_stop_blocks_entry_but_manages_owned_exit(tmp_path,monkeypatch):
    async def scenario():
        broker=FakeBroker();engine=BrokerExperimentEngine(tmp_path/'alpaca-broker',broker)
        authority={'state':'RUNNING'}
        monkeypatch.setattr('forge.research.alpaca_broker_engine.read_runtime_state',lambda key:authority)
        monkeypatch.setattr('forge.research.alpaca_broker_engine.signal',lambda mechanism,history:True)
        await engine.tick();await engine.tick()
        authority.update(state='STOPPED',safe_stop_policy='flatten_when_safe')
        report=await engine.tick();await engine.tick()
        assert report['status']=='GLOBAL_STOPPED' and broker.held==0 and broker.submitted==2
        await engine.close()
    asyncio.run(scenario())


def test_unowned_inventory_and_orders_prevent_reconciliation(db):
    broker=FakeBroker();broker.held=D(1)
    adapter=AlpacaPaperAdapter(broker,db,Ledger(db))
    report=asyncio.run(adapter.reconcile())
    assert not report.ok and 'unreconciled_inventory:QQQ' in report.issues


def test_unpersisted_or_post_only_order_cannot_bypass_gateway(db):
    adapter=AlpacaPaperAdapter(FakeBroker(),db,Ledger(db))
    request=OrderRequest(client_order_id='random',venue='alpaca',symbol='QQQ-USD',side='buy',order_type='market',quote_size=D(10))
    with pytest.raises(VenueError):asyncio.run(adapter.submit_order(request))
    request=request.model_copy(update={'order_type':'post_only'})
    with pytest.raises(VenueError):asyncio.run(adapter.submit_order(request))


def test_fill_and_ledger_are_one_crash_safe_transaction(tmp_path,monkeypatch):
    async def scenario():
        broker=FakeBroker();engine=BrokerExperimentEngine(tmp_path/'alpaca-broker',broker)
        monkeypatch.setattr('forge.research.alpaca_broker_engine.read_runtime_state',lambda key: {'state':'RUNNING'})
        monkeypatch.setattr('forge.research.alpaca_broker_engine.signal',lambda mechanism,history:True)
        await engine.tick()
        original=engine.ledger.record_fill
        def fail(*args,**kw):raise RuntimeError('injected posting failure')
        monkeypatch.setattr(engine.ledger,'record_fill',fail)
        with pytest.raises(RuntimeError):await engine.tick()
        assert engine.db.scalar('SELECT COUNT(*) FROM fills')==0
        assert engine.ledger.check_balanced('paper')==0
        monkeypatch.setattr(engine.ledger,'record_fill',original)
        await engine.tick()
        assert engine.db.scalar('SELECT COUNT(*) FROM fills')==1
        assert engine.ledger.check_balanced('paper')==0
        await engine.close()
    asyncio.run(scenario())


def test_allocator_discovery_has_no_fabricated_sample_count(db):
    from forge.treasury.reallocator import CapitalReallocator
    db.kv_set('surface.allocation',{'unlock_value':[{'rail':'alpaca.paper','usd_per_day_if_unblocked':24}]})
    allocator=CapitalReallocator(SimpleNamespace(db=db))
    cards=allocator.build_candidates()
    assert cards[0]['n']==cards[0]['n_closed']==0
    plan=allocator.plan()
    assert not plan['ranking'] and len(plan['discovery_opportunities'])==1
    assert not any(a['type']=='PREFER' for a in plan['actions'])


def test_proposals_are_typed_deduplicated_and_cannot_enable_live(db):
    from forge.research.experiment_registry import PaperHypothesis,queue_paper_hypothesis
    from pydantic import ValidationError
    valid=dict(objective_id='test',mechanism='trend_following',symbol='SPY',hypothesis='Trend persistence after costs',lookback_sessions=40)
    spec=PaperHypothesis(**valid)
    first=queue_paper_hypothesis(db,spec,'critic');second=queue_paper_hypothesis(db,spec,'critic')
    assert first['id']==second['id'] and second['state']=='ALREADY_QUEUED'
    assert len(db.kv_get('research.paper_proposals'))==1
    with pytest.raises(ValidationError):PaperHypothesis(**valid,live=True)
    with pytest.raises(ValidationError):PaperHypothesis(**{**valid,'lookback_sessions':5000})


def test_engine_automatically_consumes_typed_agent_proposal_once(tmp_path,monkeypatch):
    from forge.research.experiment_registry import PaperHypothesis,queue_paper_hypothesis
    engine=BrokerExperimentEngine(tmp_path/'alpaca-broker',FakeBroker())
    spec=PaperHypothesis(objective_id='research',mechanism='trend_following',symbol='SPY',lookback_sessions=40,
                         hypothesis='Independent future trend persistence trial')
    queue_paper_hypothesis(engine.db,spec,'alpha_inventor')
    monkeypatch.setattr('forge.research.alpaca_broker_engine.read_runtime_state',lambda key:engine.db.kv_get('research.paper_proposals') if key=='research.paper_proposals' else {'state':'RUNNING'})
    contract=engine.bootstrap(__import__('forge.opportunities.alpaca_bankroll',fromlist=['PaperBankrollPolicy']).PaperBankrollPolicy.from_env(treasury_nav=28))
    trial=engine.experiment(contract)
    assert trial['mechanism']=='trend_following' and trial['symbol']=='SPY-USD' and trial['lookback']==40
    assert len(engine.db.kv_get('broker.consumed_proposals'))==1
    assert engine.experiment(contract)==trial
    asyncio.run(engine.close())


def test_failed_trial_rotates_without_human_action(tmp_path,monkeypatch):
    async def scenario():
        engine=BrokerExperimentEngine(tmp_path/'alpaca-broker',FakeBroker())
        monkeypatch.setattr('forge.research.alpaca_broker_engine.read_runtime_state',lambda key:{'state':'RUNNING'})
        monkeypatch.setattr('forge.research.alpaca_broker_engine.signal',lambda *args:False)
        await engine.tick()
        current=engine.db.kv_get('broker.current_experiment');original=current['id']
        current['sessions']=20;engine.db.kv_set('broker.current_experiment',current)
        await engine.tick()
        nxt=engine.db.kv_get('broker.current_experiment')
        assert nxt['id']!=original and nxt['mechanism']=='dip_reversion'
        assert engine.db.scalar('SELECT state FROM economic_experiments WHERE id=?',(original,))=='RETIRED'
        await engine.close()
    asyncio.run(scenario())


def test_training_stage_growth_is_idempotent_capital_not_income(tmp_path):
    from forge.opportunities.alpaca_bankroll import PaperBankrollPolicy
    engine=BrokerExperimentEngine(tmp_path/'alpaca-broker',FakeBroker())
    engine.bootstrap(PaperBankrollPolicy.from_env(treasury_nav=0))
    assert engine.ledger.state('paper').contributed_usd==25
    policy=PaperBankrollPolicy.from_env(treasury_nav=28)
    engine.bootstrap(policy);engine.bootstrap(policy)
    state=engine.ledger.state('paper')
    assert state.contributed_usd==50 and state.realized_pnl_usd==state.other_income_usd==0
    assert engine.ledger.check_balanced('paper')==0
    asyncio.run(engine.close())
