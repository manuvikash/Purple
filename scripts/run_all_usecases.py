#!/usr/bin/env python3
"""Run a matrix of Purple snippets (happy paths + expected failures) and print outcomes."""

from __future__ import annotations

import sys
import traceback
from collections.abc import Mapping
from pathlib import Path
from dataclasses import dataclass
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

from purple.checker import check_program
from purple.errors import LexerError, ParseError, PurpleError, RuntimeError_, TypeError_
from purple.interpreter import run_queries
from purple.lexer import Lexer
from purple.parser import parse_source
from purple.typesys import TFloatUnit, TIntUnit, PurpleType


@dataclass(frozen=True)
class Case:
    title: str
    source: str
    telemetry_values: Mapping[str, Any]
    telemetry_types: Mapping[str, PurpleType]
    expect: str  # "ok" | "lexer" | "parse" | "type" | "runtime"


def _divider(n: int = 72) -> None:
    print("-" * n)


def _run_case(case: Case) -> bool:
    print(f"\n== {case.title} ==")
    print(f"EXPECT: {case.expect}")
    _divider()

    # 1) Lex
    try:
        tokens = Lexer(case.source).tokenize()
        tok_summary = f"{len(tokens)} tokens ending in {tokens[-1].type.name}"
    except LexerError as err:
        print("STAGE: lexer")
        print(f"RESULT: REJECTED ({err.__class__.__name__})")
        print(f"        {err}")
        ok = case.expect == "lexer"
        print("STATUS:", "PASS" if ok else "FAIL (unexpected lexer error)")
        return ok

    # 2) Parse
    try:
        program = parse_source(case.source)
    except ParseError as err:
        print(f"LEX:    {tok_summary}")
        print("STAGE: parser")
        print(f"RESULT: REJECTED ({err.__class__.__name__})")
        print(f"        {err}")
        ok = case.expect == "parse"
        print("STATUS:", "PASS" if ok else "FAIL (unexpected parse error)")
        return ok

    # 3+4) Typecheck + interpret (only when parsing succeeded)
    print(f"LEX:    {tok_summary}")
    print("PARSE:  ok")
    try:
        check_program(program, case.telemetry_types)
        query_out = run_queries(program, case.telemetry_values)
    except TypeError_ as err:
        print("STAGE: type checker")
        print(f"RESULT: REJECTED ({err.__class__.__name__})")
        print(f"        {err}")
        ok = case.expect == "type"
        print("STATUS:", "PASS" if ok else "FAIL (unexpected type error)")
        return ok
    except RuntimeError_ as err:
        print("STAGE: interpreter")
        print(f"RESULT: REJECTED ({err.__class__.__name__})")
        print(f"        {err}")
        ok = case.expect == "runtime"
        print("STATUS:", "PASS" if ok else "FAIL (unexpected runtime error)")
        return ok
    except PurpleError as err:
        print("STAGE: unexpected PurpleError")
        print(f"RESULT: {err}")
        print("STATUS:", "FAIL")
        return False

    print("TYPE:   ok")
    print("RUN:   ", query_out)
    ok = case.expect == "ok"
    print("STATUS:", "PASS" if ok else "FAIL (expected failure but pipeline succeeded)")
    return ok


def main() -> None:
    secs = TFloatUnit("seconds")
    pct = TFloatUnit("percent")

    cases: list[Case] = [
        Case(
            title="Model literals (string) + empty query",
            source="""
model cfg { track = "Monza"; }
query q { }
""",
            telemetry_values={},
            telemetry_types={},
            expect="ok",
        ),
        Case(
            title="Compound tyre constant in model + query reference",
            source="""
model cfg { tyre = SOFT; }
query q {
  require tyre == SOFT;
}
""",
            telemetry_values={},
            telemetry_types={},
            expect="ok",
        ),
        Case(
            title="Function + call + unit constructors (seconds)",
            source="""
fn margin() -> seconds { return seconds(1.5); }
query q {
  let g: seconds = seconds(3.0);
  require g > margin();
}
""",
            telemetry_values={},
            telemetry_types={},
            expect="ok",
        ),
        Case(
            title="Telemetry variable (typed) drives require",
            source="""
query q {
  require gap > seconds(2.0);
}
""",
            telemetry_values={"gap": 4.0},
            telemetry_types={"gap": secs},
            expect="ok",
        ),
        Case(
            title="Boolean connectives (or / and / not)",
            source="""
query q {
  require (true or false) and not false;
}
""",
            telemetry_values={},
            telemetry_types={},
            expect="ok",
        ),
        Case(
            title="Arithmetic: seconds * scalar, comparison",
            source="""
query q {
  require seconds(3.0) * 2 > seconds(5.0);
}
""",
            telemetry_values={},
            telemetry_types={},
            expect="ok",
        ),
        Case(
            title="Division of same float unit to plain float, compared to float literal",
            source="""
query q {
  require seconds(10.0) / seconds(4.0) > 2.0;
}
""",
            telemetry_values={},
            telemetry_types={},
            expect="ok",
        ),
        Case(
            title="lap and position constructors + int comparison",
            source="""
query q {
  let l: lap = lap(10);
  let p: position = position(3);
  require l < lap(50) and p == position(3);
}
""",
            telemetry_values={},
            telemetry_types={},
            expect="ok",
        ),
        Case(
            title="if false: inner require skipped",
            source="""
query q {
  if false { require false; }
}
""",
            telemetry_values={},
            telemetry_types={},
            expect="ok",
        ),
        Case(
            title="if true: inner require must pass",
            source="""
query q {
  if true { require true; }
}
""",
            telemetry_values={},
            telemetry_types={},
            expect="ok",
        ),
        Case(
            title="Mixed telemetry: gap (seconds), fuel_pct (percent)",
            source="""
query q {
  require gap > seconds(1.0);
  require fuel_pct < percent(90.0);
}
""",
            telemetry_values={"gap": 3.0, "fuel_pct": 40.0},
            telemetry_types={"gap": secs, "fuel_pct": pct},
            expect="ok",
        ),
        Case(
            title="NEGATIVE - lexer rejects unknown character",
            source='query broken { let x: int = `; }',
            telemetry_values={},
            telemetry_types={},
            expect="lexer",
        ),
        Case(
            title="NEGATIVE - parser rejects function without final return",
            source="""
fn oops() -> int { let x: int = 1; }
""",
            telemetry_values={},
            telemetry_types={},
            expect="parse",
        ),
        Case(
            title="NEGATIVE - type checker: seconds compared to percent",
            source="""
query q { require seconds(3.0) > percent(50.0); }
""",
            telemetry_values={},
            telemetry_types={},
            expect="type",
        ),
        Case(
            title="NEGATIVE - type checker: lap() needs int, not seconds()",
            source="""
query q { let x: lap = lap(seconds(2.0)); }
""",
            telemetry_values={},
            telemetry_types={},
            expect="type",
        ),
        Case(
            title="NEGATIVE - type checker: recursion cycle",
            source="""
fn a() -> bool { return b(); }
fn b() -> bool { return a(); }
query q { require true; }
""",
            telemetry_values={},
            telemetry_types={},
            expect="type",
        ),
        Case(
            title="NEGATIVE - type checker: undefined telemetry variable",
            source="""
query q { require mystery > seconds(0.0); }
""",
            telemetry_values={},
            telemetry_types={},
            expect="type",
        ),
        Case(
            title="NEGATIVE - query finishes with logical failure (require false)",
            source="""
query q { require false; }
""",
            telemetry_values={},
            telemetry_types={},
            expect="ok",
        ),
    ]

    print("Purple sample matrix - running all cases")
    mismatches = 0
    for c in cases:
        try:
            if not _run_case(c):
                mismatches += 1
        except Exception:  # noqa: BLE001
            print("\nSYSTEM ERROR while running case:")
            traceback.print_exc()
            mismatches += 1

    _divider()
    passed = len(cases) - mismatches
    print(f"\nSUMMARY: {passed}/{len(cases)} cases matched expectations")
    if mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
