# AGENTS.md — Kinematic Trees Python or Rust process

## Purpose

Build and maintain this generated KT process without bypassing KTM, changing generated files, or hiding failures from the developer.

## Read before editing

Inspect these files first:

1. `package.ktm.json` — package identity, KT dependencies, channels, and configuration schema.
2. `pyproject.toml` — ordinary Python dependencies and Python project settings.
3. `runtime.json` — settings and channel routing for one running instance.
4. `src/*/process.py` — editable process behavior.
5. `src/*/_generated/` or Rust `src/generated/` — generated channel API; read it when useful, but do not edit it.
6. Existing tests and `scripts/test.py` (Python) or `cargo test` recipe (Rust) — current acceptance checks.

Do not assume channel names, datatypes, paths, or commands. Read them from this project.

## Working rules

- Use KTM from the project directory for development, tests, execution, and packaging.
- Edit Python behavior in `src/<project_module>/process.py` or Rust in `src/main.rs`.
- Keep process state on `self`. Never retain a runtime `ctx` after its callback returns.
- Edit channels and configuration schemas in `package.ktm.json`.
- After a channel-contract change, run `ktm project generate`, then `ktm project test`.
- Never edit files under `_generated/`; KTM replaces them.
- Add ordinary Python packages to the existing `[project]` dependencies in `pyproject.toml`.
- Do not install `kt_process`, KT Messages, managed Python, or `libkt` with `pip`. KTM owns that dependency graph.
- Use generated typed channel accessors for normal Messages work. Use raw bytes only when the task explicitly requires encoded data.
- Do not publish, change release authority, or use private package coordinates unless the developer explicitly authorizes it.
- Do not bypass a failing check with `--no-test`, copied cache state, hand-edited generated output, or an undocumented environment variable.

## Standard workflow

Run the smallest relevant check while editing. Before handing work back, run:

```bash
ktm project check
ktm project test
ktm project run
ktm project pack
```

Use `ktm project build` for one finite development pass. Use `ktm project dev` only when a human wants the continuous watch loop.

If this project was not created successfully from the public selected-language template, stop. Do not reconstruct the template or dependency graph by hand.

## Messages and channels

- Read an input with the accessor generated for that input, for example `inputs.example_input.read(ctx)`.
- Treat `None` as “no value is ready”; do not invent a value.
- Write an output with its generated output accessor.
- Keep structured Message views immutable. Create a new Message when a value must change.
- When an accessor is missing, compare the code with `package.ktm.json`, regenerate, and run the generation check.
- When encoding or decoding fails, report the channel name, declared datatype, received value type, and the complete error.

## Failure handling

Do not report only an error code. Give the developer:

1. what failed;
2. the relevant file, channel, datatype, or command;
3. the likely cause, when evidence supports one;
4. what did not complete or change;
5. one exact safe next action; and
6. the complete original error.

For project or dependency failures, use the relevant diagnostics:

```bash
ktm project test
ktm project inspect --view health
ktm project check
ktm project inspect --view environment
```

Do not claim success from a green build alone. State which commands ran, their result, and which required checks were not run.

## Handoff

Return a short report with:

- files changed and why;
- behavior added or corrected;
- checks run and their results;
- remaining risks or blocked checks; and
- the next action, if work remains.
