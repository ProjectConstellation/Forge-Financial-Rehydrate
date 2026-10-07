"""FORGE Modal app (environment `forge`, app `forge-research`) — parallel computational muscle (DOSSIER §4, §25).

`search` runs the exact same evolutionary search + promotion gate as the local worker, reading market history from
the `forge-market` Volume. Bursts fan out over many containers with different seeds/parent subsets; containers scale
to zero when idle (no permanent warm worker unless measured worth it — DIRECTIVE §4). Every call has a timeout.
Deploy:  modal deploy modal_apps/forge_research.py --env forge
"""

import modal

app = modal.App("forge-research")
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("numpy>=2.1", "pyarrow>=17", "pydantic>=2.8", "pyyaml>=6.0")
         .add_local_python_source("forge"))
market = modal.Volume.from_name("forge-market", create_if_missing=True)


@app.function(image=image, cpu=2.0, memory=3072, timeout=900, volumes={"/market": market}, max_containers=16,
              scaledown_window=60, retries=0)
def search(interval: int, parents: list, fees: dict, budget_s: float, seed: int, must_eval: list | None = None) -> dict:
    import time
    t0 = time.time()
    from forge.evolution.worker import local_search
    out = local_search("/market", interval, parents, fees, budget_s, seed, must_eval)
    out["where"] = "modal"
    out["container_seconds"] = time.time() - t0
    return out


@app.function(image=image, cpu=0.25, memory=256, timeout=60)
def ping() -> dict:
    import platform
    import time
    import hashlib
    import pathlib

    import forge
    src = pathlib.Path(forge.__file__).parent
    h = hashlib.sha256(b"".join(p.read_bytes() for p in sorted(src.rglob("*.py")))).hexdigest()[:12]
    return {"ok": True, "python": platform.python_version(), "ts": time.time(), "forge_src_hash": h}
