#!/usr/bin/env python3
"""Bounded, read-only evidence recorder for Forge's existing PAPER loops."""
from __future__ import annotations
import json, os, sqlite3, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path('/srv/forge/var')
DB = ROOT / 'state/forge.sqlite'
OUTROOT = ROOT / 'research/paper_trial_4h'
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 300.0

def utc(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec='seconds')

def connect():
    c = sqlite3.connect(f'file:{DB}?mode=ro', uri=True, timeout=10)
    c.row_factory = sqlite3.Row
    return c

def rows(c, sql, args=()):
    return [dict(x) for x in c.execute(sql, args)]

def json_file(path):
    try: return json.loads(path.read_text())
    except Exception: return None

def snapshot(c, started):
    start_iso = utc(started)
    out = {'ts': time.time(), 'ts_utc': utc(time.time())}
    out['strategy_populations'] = rows(c, 'SELECT population,COUNT(*) n,COUNT(DISTINCT genome_hash) unique_dna FROM strategies GROUP BY population')
    out['strategy_new_since_start'] = rows(c, 'SELECT COUNT(*) n,COUNT(DISTINCT genome_hash) unique_dna FROM strategies WHERE created_at >= ?', (start_iso,))[0]
    out['strategy_transitions_since_start'] = rows(c, 'SELECT to_population,reason,COUNT(*) n FROM strategy_events WHERE ts >= ? GROUP BY to_population,reason ORDER BY n DESC LIMIT 25', (start_iso,))
    out['research_trials_since_start'] = rows(c, 'SELECT COUNT(*) n,COUNT(DISTINCT genome_id) unique_genomes,SUM(passed_validation) passed,SUM(promoted) promoted,SUM(sealed_exam) sealed FROM research_trials WHERE ts >= ?', (start_iso,))[0]
    out['paper_positions'] = rows(c, "SELECT book,status,COUNT(*) n,ROUND(SUM(CAST(realized_pnl_usd AS REAL)-CAST(fees_usd AS REAL)),6) net_usd FROM positions GROUP BY book,status")
    out['paper_positions_since_start'] = rows(c, "SELECT status,COUNT(*) n,ROUND(SUM(CAST(realized_pnl_usd AS REAL)-CAST(fees_usd AS REAL)),6) net_usd FROM positions WHERE book='paper' AND opened_at >= ? GROUP BY status", (start_iso,))
    out['shadow_trades_since_start'] = rows(c, 'SELECT rail,COUNT(*) n,ROUND(SUM(CAST(pnl_usd AS REAL)-CAST(fee_usd AS REAL)),6) net_usd FROM shadow_trades WHERE CAST(ts AS REAL)>=? GROUP BY rail ORDER BY n DESC', (started,))
    out['crossrail_since_start'] = rows(c, 'SELECT kind,status,COUNT(*) n FROM crossrail_signals WHERE CAST(ts AS REAL)>=? GROUP BY kind,status ORDER BY kind,status', (started,))
    out['sports_paper_bets'] = rows(c, "SELECT status,COUNT(*) n,ROUND(SUM(COALESCE(CAST(pnl_usd AS REAL),0)),6) pnl_usd FROM paper_bets GROUP BY status")
    out['kalshi_live_orders'] = rows(c, 'SELECT status,COUNT(*) n FROM kalshi_live_orders GROUP BY status')
    out['live_position_rows'] = rows(c, "SELECT COUNT(*) n FROM positions WHERE book='live'")[0]['n']
    out['research_experiments'] = rows(c, 'SELECT kind,status,COUNT(*) n,ROUND(SUM(CAST(cost_usd AS REAL)),6) cost_usd FROM experiments WHERE started_at >= ? GROUP BY kind,status', (start_iso,))
    out['alpaca_broker'] = json_file(ROOT/'alpaca_broker_trials.json')
    out['alpaca_forward'] = json_file(ROOT/'alpaca_forward_trials.json')
    out['alpaca_status'] = json_file(ROOT/'alpaca_paper_status.json')
    # Avoid dumping broad KV/strategy payloads; persist only small economic evidence fields.
    kv = {r['key']: json.loads(r['value']) for r in c.execute("SELECT key,value FROM kv_state WHERE key IN ('econ.treasury_board','lab.paper_bets','kalshi.live','trial.8h')")}
    board = kv.get('econ.treasury_board') or {}
    pnl = board.get('paper_pnl') or {}
    out['economic_snapshot'] = {'mode': (board.get('paper_bets') or {}).get('mode'), 'nav': board.get('nav'),
        'settled_income_usd': pnl.get('settled_income_usd'), 'true_net_usd_24h': pnl.get('true_net_usd'),
        'true_net_usd_per_h_24h': pnl.get('usd_per_h'), 'inference_cost_usd': pnl.get('intelligence'),
        'compute_cost_usd': pnl.get('compute'), 'paper_edges_found': (board.get('paper_bets') or {}).get('edges_found'),
        'kalshi_live_block_reason': (kv.get('kalshi.live') or {}).get('why'),
        'existing_8h_trial': {k:(kv.get('trial.8h') or {}).get(k) for k in ('status','started_ts','ends_ts')}}
    desk = kv.get('lab.paper_bets') or {}
    out['sports_feed_snapshot'] = {'status':desk.get('status'),'ts':desk.get('ts'),'open':desk.get('open'),
        'edges_found':desk.get('edges_found'),'placed_count':len(desk.get('placed') or []),'settled_count':len(desk.get('settled') or [])}
    return out

def main():
    started = time.time(); ends = started + HOURS*3600
    run_id = datetime.fromtimestamp(started,timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    dest = OUTROOT/run_id
    dest.mkdir(parents=True, exist_ok=False)
    os.chmod(dest,0o700)
    meta = {'run_id':run_id,'mode':'PAPER_ONLY','started_ts':started,'started_utc':utc(started),'ends_ts':ends,
        'ends_utc':utc(ends),'hours':HOURS,'sampling_seconds':INTERVAL,
        'coverage':['Coinbase crypto paper book and strategy research','Kalshi shadow signals and PAPER live-order gate',
                    'Alpaca broker-paper account','Alpaca local forward-paper simulator','sports paper desk (feed health monitored)'],
        'scope':'Observe existing bounded Forge paper loops; no live order, capital transfer, or strategy/runtime configuration mutation.'}
    (dest/'run.json').write_text(json.dumps(meta,indent=2)+'\n')
    c=connect(); log=dest/'snapshots.jsonl'
    print(json.dumps({'event':'started','run':meta,'output':str(dest)}),flush=True)
    while True:
        snap=snapshot(c,started)
        with log.open('a') as f: f.write(json.dumps(snap,separators=(',',':'))+'\n')
        (dest/'latest.json').write_text(json.dumps(snap,indent=2)+'\n')
        if snap['ts']>=ends:
            break
        time.sleep(min(INTERVAL,max(1,ends-time.time())))
    c.close()
    entries=[json.loads(x) for x in log.read_text().splitlines() if x.strip()]
    initial,final=entries[0],entries[-1]
    summary={'run':meta,'samples':len(entries),'first':initial,'final':final,
        'notes':['PAPER only: this run observes existing engines and does not send LIVE orders.',
        'Strategy creation/evaluation counts are not trades or independent profitable evidence.',
        'Paper earnings remain simulated; actual income is zero unless separately reconciled LIVE.']}
    (dest/'final.json').write_text(json.dumps(summary,indent=2)+'\n')
    report=['# Four-hour Forge paper trial', '',f"- Started: {meta['started_utc']}",f"- Ended: {utc(time.time())}",
        f"- Samples: {len(entries)} at {INTERVAL:g}-second cadence",'- Mode: PAPER_ONLY',
        '- Scope: existing Coinbase, Kalshi shadow, Alpaca paper, equity-forward, and sports paper loops.',
        '- This trial does not submit live orders, add real funds, or change strategy risk settings.',
        '- Strategy counts/evaluations are not profitable trades. See final.json for complete snapshots.',
        '- Paper results are not income. Actual income requires reconciled LIVE records.','']
    (dest/'final.md').write_text('\n'.join(report))
    print(json.dumps({'event':'completed','run_id':run_id,'ended_utc':utc(time.time()),'samples':len(entries),'output':str(dest)}),flush=True)

if __name__=='__main__': main()
