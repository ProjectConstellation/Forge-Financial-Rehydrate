"""Thin gate wrapper for intelligence — institutional workforce overhaul."""
import sys
from pathlib import Path
sys.argv = ["forge_gate.py", "intelligence", "0.03", "3"]
import runpy
runpy.run_path(str(Path(__file__).resolve().with_name("forge_gate.py")), run_name="__main__")
