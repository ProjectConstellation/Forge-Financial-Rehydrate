"""Normalized broker-paper execution. Only reconciled Forge-owned inventory may be sold.

Official contracts: docs.alpaca.markets/us/docs/orders-at-alpaca and
us/reference/getaccountactivities-2. No LIVE endpoint, transfer or leverage path.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx

from forge.domain.market import Balance, MarketRules
from forge.domain.trading import FillReport, OrderAck, OrderRequest, OrderState, OrderStatus
from forge.venues.base import Capability, FeeSchedule, ReconciliationReport, VenueError
from forge.venues.alpaca import AlpacaAPIError

D = Decimal
STATUSES = {'new': OrderStatus.OPEN, 'accepted': OrderStatus.OPEN,
            'pending_new': OrderStatus.PENDING, 'partially_filled': OrderStatus.PARTIAL,
            'filled': OrderStatus.FILLED, 'canceled': OrderStatus.CANCELLED,
            'expired': OrderStatus.EXPIRED, 'rejected': OrderStatus.REJECTED,
            'done_for_day': OrderStatus.OPEN, 'pending_cancel': OrderStatus.OPEN,
            'pending_replace': OrderStatus.OPEN, 'stopped': OrderStatus.OPEN,
            'suspended': OrderStatus.UNKNOWN, 'replaced': OrderStatus.CANCELLED}


class AlpacaPaperAdapter:
    name = 'alpaca'
    orders_persist_remotely = True

    def __init__(self, client: Any, db: Any, ledger: Any):
        if not client.is_paper:
            raise ValueError('broker training requires paper endpoint')
        self.client, self.db, self.ledger = client, db, ledger
        self.fee_rate = D('.0005')  # conservative research cost when fee not supplied
        self.rules: dict[str, MarketRules] = {}

    def capabilities(self):
        return {Capability.MARKET_DATA, Capability.VIEW, Capability.TRADE}

    @staticmethod
    def ticker(symbol):
        if not symbol.endswith('-USD') or not symbol[:-4].isalpha():
            raise VenueError('invalid normalized equity symbol')
        return symbol[:-4]

    async def list_products(self):
        return []

    async def get_market_rules(self, symbol):
        asset = await self.client.asset(self.ticker(symbol))
        active = asset.get('tradable') and asset.get('status') == 'active' and asset.get('fractionable')
        rules = MarketRules(self.name, symbol, self.ticker(symbol), 'USD', D('.000000001'), D('.01'),
                            D('.000000001'), D('1'), D('.01'), trading_enabled=bool(active))
        self.rules[symbol] = rules
        return rules

    async def get_fees(self):
        return FeeSchedule(self.fee_rate, self.fee_rate, 'research_cost_assumption', 'conservative_5bps_per_leg')

    async def get_balances(self):
        cash = D(str((await self.client.account()).get('cash') or 0))
        holdings = await self.client.positions()
        return [Balance('USD', cash)] + [Balance(p['symbol'], D(str(p['qty']))) for p in holdings]

    @staticmethod
    def state(raw):
        return OrderState(client_order_id=raw['client_order_id'], venue_order_id=raw['id'],
                          symbol=raw['symbol']+'-USD', side=raw['side'],
                          status=STATUSES.get(raw.get('status'), OrderStatus.UNKNOWN),
                          filled_size=D(str(raw.get('filled_qty') or 0)),
                          avg_fill_price=D(str(raw['filled_avg_price'])) if raw.get('filled_avg_price') else None,
                          raw=raw)

    async def get_order(self, client_order_id, venue_order_id=None):
        try:
            raw = await self.client.req('GET', '/v2/orders:by_client_order_id',
                                        params={'client_order_id': client_order_id})
            return self.state(raw)
        except AlpacaAPIError as exc:
            if exc.status_code == 404:
                return None
            raise VenueError('broker order reconciliation unavailable', retryable=True, ambiguous=True) from exc
        except (httpx.HTTPError, RuntimeError) as exc:
            # A network failure is UNKNOWN, never an absent in-memory paper order.
            raise VenueError('broker order reconciliation unavailable', retryable=True, ambiguous=True) from exc

    async def list_open_orders(self):
        return [self.state(o) for o in await self.client.orders(status='open', limit=500)]

    async def submit_order(self, req: OrderRequest):
        ticker = self.ticker(req.symbol)
        if req.order_type == 'post_only':
            raise VenueError('Alpaca equities do not support post-only; maker execution is unavailable')
        known = self.db.query_one('SELECT * FROM orders WHERE client_order_id=?', (req.client_order_id,))
        if not known or known['venue'] != self.name or known['book'] != 'paper':
            raise VenueError('order must be persisted by Forge gateway before submit')
        clock, account = await self.client.clock(), await self.client.account()
        if not clock.get('is_open'):
            raise VenueError('regular equity session closed; no queued market order')
        if account.get('trading_blocked') or account.get('account_blocked'):
            raise VenueError('account trading unavailable')
        if req.side == 'buy':
            state = self.ledger.state('paper')
            amount = req.quote_size or ((req.base_size or D(0)) * (req.limit_price or D(0)))
            import json
            exposure = sum(max(D(p['cost_usd']), D(str(json.loads(p['meta']).get('notional', 0))) if p['status']=='OPENING' else D(0))
                           for p in self.db.query("SELECT cost_usd,meta,status FROM positions WHERE status!='CLOSED'"))
            contract = self.db.kv_get('broker.contract') or {}
            if (amount <= 0 or amount > D(str(contract.get('max_order_usd', 0)))
                    or exposure > D(str(contract.get('max_open_usd', 0)))
                    or amount * (1+self.fee_rate) > min(state.cash_usd, D(str(account.get('cash') or 0)))):
                raise VenueError('training cash or exposure cap exceeded')
        else:
            if req.base_size is None or req.base_size <= 0:
                raise VenueError('protective sell requires exact owned quantity')
            own = sum(D(p['qty']) for p in self.db.query("SELECT qty FROM positions WHERE symbol=? AND status!='CLOSED'", (req.symbol,)))
            broker = {p['symbol']: D(str(p['qty'])) for p in await self.client.positions()}
            open_orders = await self.list_open_orders()
            reserved = sum(max(D(0), D(str(o.raw.get('qty') or 0))-o.filled_size)
                           for o in open_orders if o.symbol==req.symbol and o.side=='sell'
                           and o.client_order_id!=req.client_order_id)
            if req.base_size > min(own, broker.get(ticker, D(0))) - reserved:
                raise VenueError('sell would exceed unreserved Forge-owned broker inventory')
        try:
            raw = await self.client.submit_order(symbol=ticker, side=req.side, order_type=req.order_type,
                                                 notional=str(req.quote_size) if req.quote_size else None,
                                                 qty=str(req.base_size) if req.base_size else None,
                                                 limit_price=str(req.limit_price) if req.limit_price else None,
                                                 client_order_id=req.client_order_id, _risk_reducing=req.side=='sell')
        except AlpacaAPIError as exc:
            if exc.status_code in (400,401,403,404,422):
                raise VenueError('broker rejected order', status=exc.status_code) from exc
            raise VenueError('broker submit outcome requires reconciliation', ambiguous=True) from exc
        except (httpx.HTTPError, RuntimeError) as exc:
            raise VenueError('broker submit outcome requires reconciliation', ambiguous=True) from exc
        st = self.state(raw)
        return OrderAck(client_order_id=st.client_order_id, venue_order_id=st.venue_order_id, status=st.status)

    async def cancel_order(self, client_order_id, venue_order_id=None):
        if not self.db.scalar('SELECT 1 FROM orders WHERE client_order_id=? AND venue=?', (client_order_id,self.name)):
            raise VenueError('cannot cancel an order not owned by Forge')
        state = await self.get_order(client_order_id, venue_order_id)
        if state is None:
            raise VenueError('cannot confirm broker order for cancellation', ambiguous=True)
        if state.status in (OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.EXPIRED, OrderStatus.REJECTED):
            return True
        await self.client.cancel_order(state.venue_order_id)
        return True  # accepted cancellation; gateway must re-read broker terminal state

    async def list_fills(self, client_order_id, venue_order_id=None):
        order = await self.get_order(client_order_id, venue_order_id)
        if order is None:
            raise VenueError('cannot confirm broker order for fills', ambiguous=True)
        raw = order.raw
        if order.filled_size <= 0:
            return []
        after = (datetime.fromisoformat(raw['created_at'].replace('Z','+00:00'))-timedelta(seconds=1)).isoformat()
        rows, token = [], None
        for _ in range(10):
            params = {'after':after, 'direction':'asc', 'page_size':100}
            if token: params['page_token'] = token
            page = await self.client.req('GET','/v2/account/activities/FILL',params=params)
            if not isinstance(page,list):
                raise VenueError('invalid broker fill response', ambiguous=True)
            rows.extend(r for r in page if r.get('order_id')==order.venue_order_id)
            if len(page)<100: break
            next_token = page[-1]['id']
            if next_token == token: raise VenueError('fill pagination stalled', ambiguous=True)
            token = next_token
        else:
            raise VenueError('fill pagination bound reached; reconciliation required', ambiguous=True)
        fills = []
        for row in rows:
            px,qty = D(str(row['price'])), D(str(row['qty']))
            if not px.is_finite() or not qty.is_finite() or min(px,qty)<=0 or row['side']!=order.side:
                raise VenueError('invalid broker fill', ambiguous=True)
            ts = datetime.fromisoformat(row['transaction_time'].replace('Z','+00:00')).timestamp()
            fills.append(FillReport(venue=self.name,trade_id='alpaca:'+row['id'],client_order_id=client_order_id,
                                    venue_order_id=order.venue_order_id,symbol=order.symbol,side=row['side'],
                                    price=px,size=qty,fee=D(str(row['fee'])) if row.get('fee') is not None else px*qty*self.fee_rate,
                                    ts_ns=int(ts*1e9),liquidity='unknown'))
        if sum(f.size for f in fills) != order.filled_size:
            raise VenueError('broker fill activities lag order quantity; retry reconciliation', ambiguous=True)
        return fills

    async def reconcile(self):
        balances, orders = await self.get_balances(), await self.list_open_orders()
        broker = {b.asset:b.total for b in balances}
        own = {}
        for p in self.db.query("SELECT symbol,qty FROM positions WHERE status!='CLOSED'"):
            ticker = self.ticker(p['symbol']);own[ticker]=own.get(ticker,D(0))+D(p['qty'])
        issues = []
        for ticker in set(broker)-{'USD'} | set(own):
            if abs(broker.get(ticker,D(0))-own.get(ticker,D(0))) > D('.000000001'):
                issues.append('unreconciled_inventory:'+ticker)
        known = {r['client_order_id'] for r in self.db.query('SELECT client_order_id FROM orders')}
        if any(o.client_order_id not in known for o in orders):issues.append('unowned_broker_orders')
        if self.ledger.check_balanced('paper') != 0:issues.append('ledger_unbalanced')
        return ReconciliationReport(not issues,balances,orders,issues)

    async def close(self):
        await self.client.close()
