"""Thin gate wrapper for execution — institutional workforce overhaul."""
import sys
from pathlib import Path
sys.argv = ["forge_gate.py", "execution", "0.02", "0.5"]
import runpy
runpy.run_path(str(Path(__file__).resolve().with_name("forge_gate.py")), run_name="__main__")
