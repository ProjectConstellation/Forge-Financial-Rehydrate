import json

from forge.audit.journal import AuditJournal


def test_hash_chain_and_tamper(tmp_path):
    j = AuditJournal(tmp_path)
    for i in range(5):
        j.append("test", {"i": i, "api_key": "should-not-appear"})
    ok, n, _ = j.verify()
    assert ok and n == 5
    assert "should-not-appear" not in "".join(p.read_text() for p in tmp_path.glob("*.jsonl"))
    j2 = AuditJournal(tmp_path)          # reopen continues the chain
    j2.append("test", {"i": 5})
    assert j2.verify()[0]
    f = next(tmp_path.glob("*.jsonl"))
    lines = f.read_text().splitlines()
    rec = json.loads(lines[2]); rec["data"]["i"] = 999
    lines[2] = json.dumps(rec, separators=(",", ":"), sort_keys=True)
    f.write_text("\n".join(lines) + "\n")
    assert not AuditJournal(tmp_path).verify()[0]
