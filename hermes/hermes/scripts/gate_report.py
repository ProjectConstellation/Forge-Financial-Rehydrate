"""Thin gate wrapper for daily report."""
import sys
from pathlib import Path
sys.argv = ["forge_gate.py", "ops", "0.02", "12"]
import runpy
runpy.run_path(str(Path(__file__).resolve().with_name("forge_gate.py")), run_name="__main__")
