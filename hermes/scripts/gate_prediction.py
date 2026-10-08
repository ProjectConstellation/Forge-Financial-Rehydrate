"""Thin gate wrapper for prediction."""
import sys
from pathlib import Path
sys.argv = ["forge_gate.py", "prediction", "0.05", "0.5"]
import runpy
runpy.run_path(str(Path(__file__).resolve().with_name("forge_gate.py")), run_name="__main__")
