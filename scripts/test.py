#!/usr/bin/env python3
"""Source/import smoke and package tests using the KTM-prepared Python environment."""
import importlib
import runpy
import sys
from pathlib import Path

# Match the former python3 -B smoke: validation must not alter project inputs.
sys.dont_write_bytecode = True

project_root = Path(__file__).resolve().parents[1]
source_root = project_root / "src"
sys.path.insert(0, str(source_root))
for path in sorted(source_root.rglob("*.py")):
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
module = importlib.import_module("kt_turtlebot3_host")
assert hasattr(module, "Process"), "Project module does not export Process"
print("Python process source/import smoke passed")

tests_dir = project_root / "tests"
sys.path.insert(0, str(tests_dir))
for path in sorted(tests_dir.glob("test_*.py")):
    print(f"Running {path.relative_to(project_root)} ...")
    runpy.run_path(str(path), run_name="__main__")
