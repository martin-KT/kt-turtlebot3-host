# kt-turtlebot3-host Python SDK guide

This project was generated from the Kinematic Trees Python Process SDK boilerplate. It is a normal editable Python project plus KTM metadata for dependency resolution and packaging.

## Project layout

- `src/kt_turtlebot3_host/process.py` — complete raw-byte echo behavior with explicit `setup`, `step`, `close`, and `config_update` callbacks.
- `src/kt_turtlebot3_host/__main__.py` — public SDK entrypoint for the generated process.
- `package.ktm.json` — the only package/process contract, including the echo input and output channels.
- `runtime.json` — sibling deployment-instance configuration for an event-driven HTTP process bound to `127.0.0.1:8080`.
- `scripts/test.py` — fast syntax/import smoke; template conformance tests live in the SDK repository.
- `scripts/build.py` — writes one flat package output under `$KTM_BUILD_OUTPUT`.
- `ktm-pack.json` — editable package-owned pack mode definition.

## Using the SDK

Run through KTM so the `libkt` native dependency is installed and visible:

```bash
ktm project inspect --view health --environment portable
ktm project dev
ktm project test
```

In project code:

```python
from kt_turtlebot3_host import Process

process = Process()
print(type(process).__name__)
```

Run the process through the public SDK entrypoint:

```bash
python3 -m kt_turtlebot3_host \
  --package package.ktm.json \
  --runtime runtime.json
```

Importing and structurally testing `Process` does not load the native library.

The echo intentionally uses `Context.get_raw` and `Context.set_raw` so a plain
HTTP request body can make a complete round trip without a message-specific
client. For application processes that understand a KT datatype, use the
generated typed channel accessors under `_generated` instead.

## Manual Python workflow

Run authored recipes with `ktm project build` and `ktm project test` so they
receive the managed interpreter and verified dependency environment. For diagnosis:

```bash
ktm project inspect --view environment
```

This view is read-only, not a shell export or environment preparation command.
Do not add a manual pip/activation step to the generated workflow.

## Packing modes

- `source` is the default and packages the root contracts, `pyproject.toml`, and Python `src/` tree as one portable application artifact.
- `compiled-source` adds optional project-owned artifacts from `dist/` plus editable development documentation and scripts without duplicating either root contract.

Docs are copied into generated projects for humans/agents, but are intentionally not packaged by default.

## Python project dependencies

Declare ordinary third-party Python dependencies explicitly in
`pyproject.toml` under `[project].dependencies`. For example:

```toml
dependencies = ["opencv-python-headless==4.10.0.84"]
```

KTM installs graph-owned, integrity-verified wheels first. It then installs the
project and resolves the declared Python dependencies into that same managed
environment for `ktm project dev` and `ktm project test`, while preventing replacement of
KTM-owned distributions. KTM does not infer dependencies, run `pip freeze`, or
rewrite `pyproject.toml`. `ktm project pack` preserves the declaration and excludes the
managed environment, so clean installation still needs an accessible Python
package index (or an accessible direct URL declared by the project).

## Dependency ownership / eject review

Both pack modes keep managed Python, the target-projected Python SDK (including its adapter), and portable Messages as direct KTM-managed dependencies. The SDK provides libkt transitively. A normal source or compiled-source package
must not copy KTM store paths, interpreters, wheels, virtual environments,
dependency shared libraries, headers, or metadata into the project payload.

A future eject/self-contained flow should be explicit and separately reviewed because it changes who owns dependency updates, license notices, SBOM evidence, and security patching. Until that flow exists, eject is not a selectable CLI mode; dependencies are never silently vendored.

## Quick payload inspection

After packing, inspect contents with:

```bash
tar -tzf _pack/*/portable/*.tar.gz | sort
```

Expected defaults:

- `source`: root contracts plus `pyproject.toml` and `src/`.
- `compiled-source`: the same portable source plus optional project-owned `dist/` artifacts and `development/`.
- `docs/`: present in the generated project folder, absent from archives by default.
- `deps/`, `.ktrees/`, KTM store paths, and `libkt` dependency libraries: absent from normal pack archives.
