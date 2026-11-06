# Python packing checklist for kt-turtlebot3-host

Use this checklist before changing `ktm-pack.json`, `scripts/build.py`, or package modes for this Python SDK project.

## Mode checklist

### `source` (default)

- [ ] `scripts/build.py` writes one flat package tree to `$KTM_BUILD_OUTPUT`.
- [ ] The `contracts` list includes only root `package.ktm.json` and `runtime.json`.
- [ ] The `source` list includes `pyproject.toml` and `src`.
- [ ] Packing preserves `[project].dependencies` byte-for-byte and does not run dependency resolution or `pip freeze`.
- [ ] Python bytecode/cache directories such as `__pycache__/` and `.pytest_cache/` are absent from the archive.
- [ ] The archive contains `src/kt_turtlebot3_host/process.py` and `src/kt_turtlebot3_host/__main__.py`.
- [ ] The archive contains one root `package.ktm.json` and one root `runtime.json`.
- [ ] The archive contains no `runtime/` directory or `node.package.json`.
- [ ] The archive does not contain `docs/` by default.

Run:

```bash
ktm project pack
```

### `compiled-source`

- [ ] The `compiled-source` mode composes `source`, `compiled`, and `development` lists.
- [ ] The `compiled` list contains only optional project-owned artifacts under `dist/`.
- [ ] The `development` list contains optional development documentation and scripts.
- [ ] The `compiled-source` archive adds `dist/` and `development/` without duplicating root contracts.

Run:

The policy retains a `compiled-source` definition for review, but the current v2 CLI does not expose selection of this alternative mode. `ktm project pack` uses the default source workflow.
## Shared package safety checklist

- [ ] Confirm the requested mode is `source` or `compiled-source`.
- [ ] Edit `ktm-pack.json` lists instead of hardcoding paths in KTM.
- [ ] Keep lists composable and reviewable. Repeated paths are allowed, but KTM deduplicates them before packaging.
- [ ] Keep `docs/` out of package payload unless Daniel explicitly asks to package docs.
- [ ] Keep generated caches out of payload.
- [ ] Ensure `scripts/build.py` writes intentional payload roots to `$KTM_BUILD_OUTPUT`.
- [ ] Validate with `ktm project inspect --view health`, `ktm project dev`, `ktm project test`, and the default pack output when changing packaging behavior.
- [ ] Inspect the resulting archive when payload composition changes.
- [ ] Verify managed Python, the SDK, Messages, and `libkt` stay KTM-managed in both normal modes; do not vendor dependency artifacts into the package.
- [ ] Verify `.venv/` and `site-packages/` remain absent even when the project declares third-party Python dependencies.

## Dependency ownership / eject review

The default pack modes keep the declared managed Python runtime, the portable SDK,
portable Messages, and target-projected
`kinematic-trees/libkt@0.1.3` as direct KTM-managed
dependencies. A normal source or compiled-source package must not copy KTM
store paths, interpreters, wheels, virtual environments, dependency shared
libraries, headers, or metadata into the project payload.

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
- `deps/`, `.ktrees/`, KTM store paths, managed interpreters, dependency wheels, and `libkt` libraries: absent from normal pack archives.
