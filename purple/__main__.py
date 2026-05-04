"""CLI entry: parse, typecheck, interpret Purple programs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from purple.checker import check_program
from purple.errors import PurpleError
from purple.interpreter import load_telemetry_json, run_queries
from purple.parser import parse_source
from purple.typesys import PurpleType, typename_from_ann


def _telemetry_types(path: Path) -> dict[str, PurpleType]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("--telemetry-types must contain a JSON object")
    specs: dict[str, PurpleType] = {}
    for key, ty in raw.items():
        if not isinstance(key, str) or not isinstance(ty, str):
            raise ValueError("--telemetry-types keys/values must be strings")
        specs[key] = typename_from_ann(ty)
    return specs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Purple DSL runner")
    parser.add_argument("program", type=Path, help="Path to a .pr source file")
    parser.add_argument(
        "--telemetry",
        type=Path,
        help="Telemetry JSON object with numeric/bool/string keys",
    )
    parser.add_argument(
        "--telemetry-types",
        type=Path,
        help='JSON mapping of free variables to Purple type names (example: {"gap":"seconds"})',
    )
    args = parser.parse_args(argv)

    source = args.program.read_text(encoding="utf-8")
    prog = parse_source(source)

    telemetry_vals = {}
    if args.telemetry:
        telemetry_vals = load_telemetry_json(args.telemetry)

    telem_specs: dict[str, PurpleType] = {}

    try:
        if args.telemetry_types:
            telem_specs = _telemetry_types(args.telemetry_types)
    except (ValueError, json.JSONDecodeError) as bad:
        print(bad)
        return 2

    try:
        check_program(prog, telem_specs)
        results = run_queries(prog, telemetry_vals)
    except PurpleError as err:
        print(err)
        return 1

    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
