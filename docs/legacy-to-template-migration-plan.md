# Legacy `kt-turtlebot3-host` → new template migration plan

This document continues from **§3** (legacy inventory). Context: legacy tree is `legacy_kt_packages/kt-turtlebot3-host` (folder name **`kt-turtlebot3-host`**, not `kt-turtlebot-host`); target template is the sibling checkout `kt-turtlebot3-host/` at repo root.

---

## 3. Legacy inventory

### 3.1 Full file tree

The listing below is a complete `find` of `/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host` with the **`.git/`** directory pruned (VCS metadata only; do not pack). A **`.git/`** directory exists at the legacy root but is omitted here.

```
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/AGENTS.md
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/docs
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/docs/ejection-checklist.md
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/docs/ktm_package_v4.schema
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/docs/ktm_runtime.schema
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/docs/packing-checklist.md
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/docs/sdk.md
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/.gitignore
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/.ktm
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/ktm-pack.json
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/.kt-test-project.ktm-create
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/.kt-test-project.ktm-create/resource-locks
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/.kt-test-project.ktm-create/resource-locks/8570d5c5c69a5959afca9d540bdd3dd6f4e88c687ae9c6aaa02f40184bbff703.lock
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/.kt-test-project.ktm-create/sdk-scratch
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/.kt-test-project.ktm-create/sdk-scratch/project-caller
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/_pack
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/_pack/0.1.0
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/_pack/0.1.0/package.ktm.json
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/_pack/0.1.0/pack-evidence.json
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/_pack/0.1.0/portable
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/_pack/0.1.0/portable/common
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/_pack/0.1.0/portable/common/kt-turtlebot3-host-0.1.0-portable-common.tar.gz
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/_pack/0.1.0/portable/common/package-inventory.json
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/package.ktm.json
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/pyproject.toml
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/README.md
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/runtime.json
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/scripts
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/scripts/build.sh
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/scripts/test.sh
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/camera_view.py
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/command.py
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host.egg-info
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host.egg-info/dependency_links.txt
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host.egg-info/PKG-INFO
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host.egg-info/requires.txt
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host.egg-info/SOURCES.txt
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host.egg-info/top_level.txt
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/_generated
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/_generated/channels.py
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/_generated/channels.receipt.json
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/_generated/__init__.py
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/__init__.py
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/__main__.py
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/process.py
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/__pycache__
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/__pycache__/camera_view.cpython-311.pyc
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/__pycache__/command.cpython-311.pyc
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/__pycache__/__init__.cpython-311.pyc
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/__pycache__/process.cpython-311.pyc
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/__pycache__/report.cpython-311.pyc
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/__pycache__/scan_geometry.cpython-311.pyc
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/__pycache__/telemetry.cpython-311.pyc
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/__pycache__/web_viz.cpython-311.pyc
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/report.py
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/scan_geometry.py
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/static
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/static/index.html
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/static/viz.js
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/telemetry.py
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/src/kt_turtlebot3_host/web_viz.py
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/tests
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/tests/test_camera.py
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/tests/test_command.py
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/tests/test_report.py
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/tests/test_scan_geometry.py
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/tests/test_telemetry.py
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/tests/test_web_gating.py
/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host/tests/test_web_viz.py
```

### 3.2 Brief purpose (where non-obvious)

Paths are relative to the **legacy** package root.

| Path | Purpose |
|------|---------|
| `package.ktm.json` | KTM v4 package contract: metadata, `dataflow` (scan, imu, battery, joints, sensor_state, camera → cmd_vel), `config` schema (HTTP port, plot limits, cmd_vel clamps, telemetry push rate, etc.), `resources`, `dependencies` (pinned KT packages with `+build.*`), portable `runEnvironments` recipes pointing at shell scripts. |
| `ktm-pack.json` | Pack policy v3 (`ktm.pack.v3`): lists, modes, assertions, forbidden globs. |
| `runtime.json` | v4 runtime document: `kt_lan` routes to gateway (`192.168.0.101:48110`), `execution` fixed 50 Hz, `channelDefaults` / `channelOverrides` (camera codec passthrough), instance `config` values. |
| `pyproject.toml` | setuptools project; `starlette`, `uvicorn[standard]`; Python ≥ 3.9. |
| `README.md` | Operator docs: robot vs host PC, addressing, `ktm run`, editing `runtime.json`. |
| `AGENTS.md` | Contributor rules (older CLI names in places: `ktm generate`, `scripts/test.sh`). |
| `docs/ejection-checklist.md`, `docs/packing-checklist.md`, `docs/sdk.md` | Packing and SDK guidance (may duplicate template). |
| `docs/ktm_package_v4.schema`, `docs/ktm_runtime.schema` | Local JSON Schema copies for authoring. |
| `.gitignore` | Git ignore rules. |
| `.ktm/` | Local KTM metadata directory (empty or workspace-specific; not part of published source). |
| `.kt-test-project.ktm-create/` | KTM test-project lock and scratch (local store). |
| `_pack/0.1.0/**` | Pack output: tarball, `pack-evidence.json`, frozen inventory — generated. |
| `scripts/build.sh` | Bash build recipe: stage README, manifests, `pyproject.toml`, `src`, copy `docs`/`scripts` into `development/` under `KTM_BUILD_OUTPUT`. |
| `scripts/test.sh` | Bash test: compile all `.py`, import smoke, run each `tests/test_*.py` serially. |
| `src/kt_turtlebot3_host/process.py` | `KT.Process` implementation: lidar + telemetry + browser viz + H.264 camera path + cmd_vel loop. |
| `src/kt_turtlebot3_host/__main__.py` | Module CLI (`--package`, `--runtime`). |
| `src/kt_turtlebot3_host/command.py` | Builds motor / cmd_vel messages for output channel. |
| `src/kt_turtlebot3_host/report.py` | IMU / sidebar reporting helpers. |
| `src/kt_turtlebot3_host/scan_geometry.py` | Lidar revolution detection and geometry for the web plot. |
| `src/kt_turtlebot3_host/telemetry.py` | Aggregates non-scan channels for the UI. |
| `src/kt_turtlebot3_host/web_viz.py` | Starlette/uvicorn HTTP + WebSocket server for visualization and cmd_vel UI. |
| `src/kt_turtlebot3_host/camera_view.py` | H.264 access-unit handling and JPEG decode path (libav-related). |
| `src/kt_turtlebot3_host/static/index.html`, `viz.js` | Browser UI assets. |
| `src/kt_turtlebot3_host/_generated/*` | KTM-generated channel API and receipt — regenerated, not hand-edited. |
| `src/kt_turtlebot3_host.egg-info/*` | Setuptools egg metadata (build artifact). |
| `src/kt_turtlebot3_host/__pycache__/*` | Bytecode cache. |
| `tests/test_*.py` | Unit-style tests for report, geometry, web gating, viz, camera, command, telemetry. |

---

## 4. Copy plan (legacy → new template)

All **Source** paths are relative to **legacy** root `legacy_kt_packages/kt-turtlebot3-host/`. **Target** is the **new** template project root `kt-turtlebot3-host/` (same relative paths unless noted).

| Source | Target | Action | Changes for new KTM |
|--------|--------|--------|---------------------|
| `package.ktm.json` | `package.ktm.json` | **Adapt** | Merge legacy **dataflow**, **config**, **resources** (TCP 8765), and **dependencies** into template shape. Prefer **template-style** dependency minimalism where possible: direct `kinematic-trees/kt-python-sdk` and let KTM resolve adapter/messages/libkt (per root `AGENTS.md`); reconcile pinned `+build.N` pins with current resolver. Replace **recipes** so **build** → `scripts/build.py`, **test** → `scripts/test.py`, **run** → `python -m kt_turtlebot3_host` with `${KTM_PACKAGE_MANIFEST}` / `${KTM_RUNTIME_DOCUMENT}`. Keep `schemaVersion: "4"` and `runtime.adapterOutputs.generated` → `src/kt_turtlebot3_host/_generated`. Refresh **metadata.readme** if README narrative changes. |
| `runtime.json` | `runtime.json` | **Adapt** | Replace template HTTP echo routing with legacy **kt_lan** routes, gateway **addr**, **execution** (50 Hz fixed rate), **channelDefaults** / **channelOverrides** (camera passthrough), and **config** defaults. Keep `schemaVersion: "4"` and `package: "./package.ktm.json"`. |
| `ktm-pack.json` | `ktm-pack.json` | **Copy or merge** | Likely matches template already; verify **assertions.required** if **`tests/`** is added to published lists; keep **forbidden** patterns (no `.venv`, no vendored wheels). |
| `pyproject.toml` | `pyproject.toml` | **Adapt** | Merge legacy `[build-system]` / `setuptools` and dependencies (`starlette`, `uvicorn[standard]`) into template file; align `requires-python` with `package.ktm.json` `runtime.languageVersion`. |
| `README.md` | `README.md` | **Adapt** | Keep TurtleBot3 operational content; align command examples with **`ktm project run`** / **`ktm project test`** per template `README`/`AGENTS.md`. |
| `AGENTS.md` | `AGENTS.md` | **Adapt** | Take **new template** as canonical; fix legacy references to `ktm generate` → **`ktm project generate`**, `scripts/test.sh` → **`scripts/test.py`** where applicable. |
| `docs/ejection-checklist.md`, `docs/packing-checklist.md`, `docs/sdk.md` | same names under `docs/` | **Diff then copy or skip** | Avoid churn if byte-identical to template; merge only deltas. |
| `docs/ktm_package_v4.schema`, `docs/ktm_runtime.schema` | same | **Skip** | Already shipped with new template unless legacy has newer schema revision worth cherry-picking. |
| `.gitignore` | `.gitignore` | **Merge** | Combine ignore rules if legacy has TurtleBot-specific entries not in template. |
| `scripts/build.sh` | — | **Skip** | Replaced by template **`scripts/build.py`**. |
| `scripts/test.sh` | — | **Skip** | Replaced by **`scripts/test.py`**; extend test runner to invoke full **`tests/`** suite if needed. |
| `src/kt_turtlebot3_host/process.py` | `src/kt_turtlebot3_host/process.py` | **Adapt** | Merge application logic; align imports to regenerated `_generated.channels` after **`ktm project generate`**. |
| `src/kt_turtlebot3_host/__main__.py` | same | **Adapt** | Preserve legacy CLI behavior if richer than template. |
| `src/kt_turtlebot3_host/__init__.py` | same | **Adapt** | Export surface as needed. |
| `src/kt_turtlebot3_host/command.py`, `report.py`, `scan_geometry.py`, `telemetry.py`, `web_viz.py`, `camera_view.py` | same | **Copy + adapt** | Match any import / typing changes from codegen. |
| `src/kt_turtlebot3_host/static/index.html`, `static/viz.js` | same | **Copy as-is** | Static assets. |
| `src/kt_turtlebot3_host/_generated/**` | — | **Skip** | Run **`ktm project generate`** after manifest merge. |
| `tests/test_*.py` | `tests/` (create under template) | **Copy + adapt** | Ensure **`ktm project test`** runs them (extend **`scripts/test.py`** or add pytest + recipe). |

---

## 5. Do not copy

| Item | Reason |
|------|--------|
| `src/kt_turtlebot3_host/_generated/*` (including `channels.receipt.json`) | Regenerated by **`ktm project generate`** from `package.ktm.json`. |
| `_pack/**` (tarballs, `pack-evidence.json`, packaged `package.ktm.json`, `package-inventory.json`) | Pack / release artifacts. |
| `src/kt_turtlebot3_host.egg-info/**` | setuptools metadata; rebuilt on install. |
| `**/__pycache__/**`, `*.pyc`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/` | Caches; also match `ktm-pack.json` **forbidden** / **globalExclude**. |
| `.git/**` | Version control; not package content. |
| `.kt-test-project.ktm-create/**` | Local KTM test-project store / locks. |
| `.ktm/**` (if only local workspace state) | Local KTM metadata; not part of portable source. |
| Monolithic or deprecated **package root `files`** lists for v4 | File selection belongs in **`ktm-pack.json`** (see `docs/ktm_package_v4.schema` source-package description). |
| Old lockfiles or vendored wheels under forbidden globs | Policy forbids `**/kt_python_sdk-*.whl`, `**/kt_messages-*.whl`, `**/libkt.so*`, `**/.ktrees/**`, `**/deps/**`, etc. |

---

## 6. Risk and order of work

### 6.1 Order of work

1. **`package.ktm.json`** — Lock channels, datatypes, config schema, resources, KT dependencies, and portable recipes (`build`/`test`/`run` → `scripts/build.py`, `scripts/test.py`, `python -m …`).
2. **`ktm-pack.json`** — Confirm pack lists and assertions; decide whether **`tests/`** is included in shipped artifacts.
3. **`runtime.json`** — Wire **`kt_lan`** addresses, execution scheduler, channel policies, and concrete **config** values.
4. **`ktm project generate`** — Regenerate **`src/kt_turtlebot3_host/_generated/`**; fix Python imports against `inputs` / `outputs`.
5. **Application code** — Merge `process.py` and helpers; update **`pyproject.toml`** third-party dependencies.
6. **Tests** — Land `tests/` and hook **`ktm project test`** (extend **`scripts/test.py`** or adopt pytest in the test recipe).
7. **Verification** — `ktm project check`, `ktm project test`, `ktm project run`, `ktm project pack` (per root **`AGENTS.md`**).

### 6.2 Risks

- **Dependency pins:** Legacy lists multiple explicit `kinematic-trees/*` packages with `+build.N` pins; modern flow may prefer a minimal declaration and resolver closure—verify with **`ktm project inspect --view environment`** after edits.
- **CLI / AGENTS drift:** Legacy **`AGENTS.md`** references `ktm generate` and **`scripts/test.sh`**; template uses **`ktm project generate`** and **`scripts/test.py`**—keep documentation consistent to avoid mistaken workflows.
- **Camera / H.264 path:** Depends on KTM-managed libav and codec policy; validate **`channelOverrides`** and runtime after integration.
- **Test harness:** Legacy tests were invoked by a shell loop; template expects **`ktm project test`** to drive **`scripts/test.py`**—plan an explicit mapping so CI does not silently skip tests.

---

*Generated for migration planning; legacy path: `/home/martin/kt_packs/legacy_kt_packages/kt-turtlebot3-host`.*
