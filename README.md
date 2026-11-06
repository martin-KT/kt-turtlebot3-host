# kt-turtlebot3-host

**kt-turtlebot3-host** is a [Kinematic Trees](https://kinematictrees.com) (KT) **Python process** that runs on a development machine or host and exchanges data with a TurtleBot3-oriented stack over **kt_lan**. It subscribes to lidar, IMU, battery, joints, sensor state, and camera streams, exposes a browser-based lidar visualization and telemetry UI over HTTP/WebSocket, and publishes wheel velocity commands (`cmd_vel`) from that UI back to the network. Pair it with a compatible gateway or driver (for example **kt-turtlebot3-driver**) publishing those topics on kt_lan.

## Requirements

- **Python** `>=3.9.0` (see `package.ktm.json` / `pyproject.toml`).
- **[KTM](https://app.kinematictrees.com/documentation/)** — the Kinematic Trees CLI. Use it from this project directory for build, test, run, and pack; the docs site covers installation and project commands.
- **Network / robot context** — `runtime.json` routes kt_lan channels to a gateway address (default `192.168.0.101:48110`). Adjust to match your robot or simulator deployment. This package does not declare ROS nodes; it speaks KT transports and datatypes used in TurtleBot3-style bring-ups.

## Quick start

Clone the repository and enter the project root:

```bash
git clone <repository-url>
cd kt-turtlebot3-host
```

Typical workflow (all commands use the **`ktm project`** noun):

```bash
ktm project run
```

For iterative development, use a watched dev loop or a single build pass:

```bash
ktm project dev        # optional: watch and rebuild/run until Ctrl-C
# or
ktm project build      # one finite build pass
```

After you change channels or the package contract in `package.ktm.json`, regenerate typed accessors and verify:

```bash
ktm project generate
ktm project check
ktm project test
```

Before sharing changes or packaging:

```bash
ktm project check
ktm project test
ktm project run
ktm project pack
```

## Configuration

| File | Role |
|------|------|
| **`package.ktm.json`** | Package identity, KT dependencies (`kt-python-sdk`), dataflow (channel names and datatypes), configuration **schema** and defaults, and build/test/run recipes. Edit here when adding, removing, or renaming channels or documenting process settings. |
| **`runtime.json`** | **Instance** wiring: link to `./package.ktm.json`, kt_lan **routes** (subscriber/client addresses per channel), execution scheduling (e.g. fixed rate), channel buffer defaults, and **concrete** `config` values (HTTP bind host/port, plot limits, telemetry rate, etc.). |

Port **8765** (TCP) is declared for the HTTP/WebSocket visualization; override `http_bind_host` and `http_port` in `runtime.json` `config` as needed.

## Developing and testing

- Regenerate channel code after manifest changes: `ktm project generate`.
- Run project tests: `ktm project test`.
- Run consistency checks: `ktm project check`.

Application logic lives under `src/` (see layout). Do not hand-edit `src/kt_turtlebot3_host/_generated/`; KTM owns those files.

## Project layout

- **`src/kt_turtlebot3_host/`** — Process implementation (`process.py`), web UI helpers, static assets, and generated `_generated/` channel API.
- **`tests/`** — Test modules.
- **`scripts/`** — `build.py` and `test.py` invoked by KTM recipes.
- **`docs/`** — Supplementary project documentation.
- **`package.ktm.json`** — KT package manifest (v4 schema).
- **`runtime.json`** — Runtime document for this deployment instance.
- **`pyproject.toml`** — Python packaging and third-party dependencies (e.g. Starlette, Uvicorn).
- **`AGENTS.md`** — Maintainer workflow and conventions for this repo.

## License

This package is released under the **MIT** License (see `package.ktm.json` metadata).
