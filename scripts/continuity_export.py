#!/usr/bin/env python3
"""Narrow read-only runtime continuity export; no prompts, keys or arbitrary report text."""
import json
import sqlite3
import time
from pathlib import Path

ROOT = Path('/srv/forge')

def export(root=ROOT):
    db = root / 'var/state/forge.sqlite'
    out = root / 'docs/continuity/runtime'
    out.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(f'file:{db}?mode=ro', uri=True, timeout=5) as c:
        c.row_factory = sqlite3.Row
        reports = [dict(r) for r in c.execute('SELECT id,ts,role,status,prompt_id,session_id FROM role_reports ORDER BY ts DESC LIMIT 100')]
        workflows = [dict(r) for r in c.execute('SELECT workflow_id,type,stage,owner,status,created_at,completed_at,result_type FROM agent_workflows ORDER BY created_at DESC LIMIT 50')]
        costs = [dict(r) for r in c.execute('SELECT agent,COUNT(*) calls,SUM(CAST(cost_usd AS REAL)) cost_usd FROM inference_calls WHERE ts>=? GROUP BY agent', (time.strftime('%Y-%m-%dT%H:%M:%S+00:00',time.gmtime(time.time()-86400)),))]
        reservations = [dict(r) for r in c.execute("SELECT provider,owner,state,COUNT(*) n,SUM(max_cost_usd) reserved_bound_usd FROM spend_reservations WHERE state IN ('RESERVED','UNCERTAIN') GROUP BY provider,owner,state")]
    data = dict(ts=time.time(),roles=reports,workflows=workflows,costs_24h=costs,reservations=reservations,
                note='Artifact metadata only; detailed typed evidence remains in authenticated Forge tools. Snapshot is not an engineering completion receipt.')
    dest = out / 'latest.json'
    tmp = out / '.latest.tmp'
    tmp.write_text(json.dumps(data,indent=2)+'\n')
    tmp.replace(dest)
    return dict(ts=data['ts'],reports=len(reports),workflows=len(workflows),path=str(dest))

if __name__=='__main__':
    print(json.dumps(export()))
