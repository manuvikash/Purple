"""Interpreter smoke tests."""

import tempfile
from pathlib import Path

from purple.checker import check_program
from purple.interpreter import load_telemetry_json, run_queries
from purple.parser import parse_source
from purple.typesys import TFloatUnit


def run_checked(src: str, telemetry: dict, telemetry_types=None):
    program = parse_source(src)
    check_program(program, telemetry_types or {})
    return run_queries(program, telemetry)


def test_end_to_end_success() -> None:
    src = """
    model sprint { driver = "VER"; }
    fn safe(gap: seconds) -> bool {
      let margin: seconds = seconds(2.0);
      return gap > margin;
    }
    query feasible {
      require safe(seconds(3.0));
    }
    """
    assert run_checked(src, {}) == {"feasible": True}


def test_gap_from_telemetry() -> None:
    src = """
    query q {
      require gap > seconds(2.0);
    }
    """
    specs = {"gap": TFloatUnit("seconds")}
    assert run_checked(src, {"gap": 2.7}, specs)["q"] is True
    assert run_checked(src, {"gap": 1.9}, specs)["q"] is False


def test_if_requires_skipped_when_false() -> None:
    src = """
    query q {
      if false {
        require false;
      }
    }
    """
    assert run_checked(src, {})["q"] is True


def test_load_json_helpers() -> None:
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "telemetry.json"
        path.write_text('{"gap": 3}', encoding="utf-8")
        data = load_telemetry_json(path)
        assert data["gap"] == 3

