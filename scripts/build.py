#!/usr/bin/env python3
"""Assemble the same package payload using managed Python's standard library."""
import os
from pathlib import Path
import shutil

# Compile source before accepting a development candidate or replacing output.
# This checks syntax using the managed interpreter without importing application
# code or writing bytecode into the captured source.
root = Path(__file__).resolve().parents[1]
for path in sorted((root / "src").rglob("*.py")):
    compile(path.read_bytes(), str(path), "exec")

# Dev executes the captured source through the prepared interpreter.
# Keep portable payload assembly for explicit build/test/pack operations.
if os.environ.get("KTM_PROJECT_OPERATION") == "dev":
    print("Using captured Python source; no portable package assembly during dev")
    raise SystemExit(0)

output = Path(os.environ.get("KTM_BUILD_OUTPUT", "build/ktm-output"))
if not output.is_absolute():
    output = root / output
output = output.resolve()
if output == root or output in root.parents:
    raise SystemExit("Build output must not replace project source")
if output.exists():
    shutil.rmtree(output)
output.mkdir(parents=True)
ignore = shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc", "*.pyo")
def copy(name, target):
    source = root / name
    if source.is_dir():
        shutil.copytree(source, target, ignore=ignore)
    else:
        shutil.copy2(source, target)
for name in ("README.md", "package.ktm.json", "runtime.json", "pyproject.toml", "src"):
    copy(name, output / name)
(output / "dist").mkdir()
(output / "development").mkdir()
for name in ("README.md", "docs", "scripts"):
    copy(name, output / "development" / name)
print(f"Built kt-turtlebot3-host portable Python source package into {output}")
