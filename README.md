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
| `examples/` | Sample `.pr` program plus telemetry JSON files |
| `scripts/run_all_usecases.py` | Demo script covering many language and error paths |

## Run a program

Programs are plain text (`.pr` used in examples). Use the module entrypoint with optional telemetry **values** and **type** maps for free variables (e.g. gaps loaded from JSON):

```bash
python -m purple examples/monza_strategy.pr --telemetry examples/telemetry.json --telemetry-types examples/telemetry_types.json
```

Output is JSON mapping each `query` name to `true` or `false` depending on whether all `require` statements in that query succeeded.

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
