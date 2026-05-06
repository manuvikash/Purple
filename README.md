# Purple

Purple is a small domain-specific language (DSL) for expressing Formula 1–style race-strategy conditions over telemetry. Programs are **statically typed** (including unit-tagged numerics), **interpreted** over JSON telemetry, and designed to stay simpler than a general-purpose scripting layer.

See [REPORT.md](REPORT.md) for language design, type rules, and implementation notes.

## Requirements

- Python 3.10+ (tested on 3.13)
- No runtime dependencies; development uses pytest.

## Setup

```bash
pip install -r requirements-dev.txt
```

## Project layout

| Path | Role |
|------|------|
| `purple/` | Lexer, parser, AST, type checker, interpreter, CLI (`python -m purple`) |
| `tests/` | Pytest suite (lexer, parser, checker, interpreter) |
| `examples/` | End-to-end CLI sample (`monza_strategy.pr` + JSON) |
| `examples/programs/` | Progressive `.pr` tutorials (01–12); some pair with `*.values.json` / `*.types.json` |
| `scripts/run_all_usecases.py` | Demo script covering many language and error paths |
| `editors/vscode-purple/` | VS Code / Cursor: TextMate highlighting for `.pr` — build `.vsix` and install (see `editors/vscode-purple/README.md`) |

## Run a program

Programs are plain text (`.pr` used in examples). Use the module entrypoint with optional telemetry **values** and **type** maps for free variables (e.g. gaps loaded from JSON):

```bash
python -m purple examples/monza_strategy.pr --telemetry examples/telemetry.json --telemetry-types examples/telemetry_types.json
```

Output is JSON mapping each `query` name to `true` or `false` depending on whether all `require` statements in that query succeeded.

## Example programs (simple → complex)

| File | What it shows |
|------|----------------|
| `examples/programs/01_minimal.pr` | Model + trivial `query` |
| `examples/programs/02_dimensionless_compare.pr` | Plain float comparison |
| `examples/programs/03_let_seconds.pr` | `seconds(...)` and `let` |
| `examples/programs/04_boolean_logic.pr` | `and` / `or` / `not` |
| `examples/programs/05_function.pr` | `fn` + call from `query` |
| `examples/programs/06_if_guard.pr` | `if { require ... }` |
| `examples/programs/07_compound_model.pr` | `model` + tyre compound (`SOFT`…`WET`) |
| `examples/programs/08_two_queries.pr` | Two `query` blocks |
| `examples/programs/09_telemetry.pr` | Free variables + `--telemetry` + `--telemetry-types` (see `09_telemetry.*.json`) |
| `examples/programs/10_lap_position.pr` | `lap(...)` and `position(...)` |
| `examples/programs/11_fuel_distance.pr` | `fuel` / `distance` units and scaling |
| `examples/programs/12_race_strategy.pr` | Multiple helpers, `if`, two queries + `12_race.*.json` |

Each `.pr` file starts with `//` comments showing the `python -m purple ...` invocation.

## Tests

```bash
python -m pytest tests -q
```

## Demo matrix

```bash
python scripts/run_all_usecases.py
```

Runs a batch of positive and negative cases (lexer, parser, type errors, and query outcomes) and prints a summary line at the end.

## License

No license is set in this repository; add one if you plan to distribute the code.
