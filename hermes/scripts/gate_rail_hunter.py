"""Thin gate wrapper for rail_hunter — institutional workforce overhaul."""
import sys
from pathlib import Path
sys.argv = ["forge_gate.py", "rail_hunter", "0.02", "2"]
import runpy
runpy.run_path(str(Path(__file__).resolve().with_name("forge_gate.py")), run_name="__main__")
