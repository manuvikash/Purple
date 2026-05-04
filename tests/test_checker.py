"""Type checker tests."""

import pytest

from purple.checker import check_program
from purple.errors import TypeError_
from purple.parser import parse_source
from purple.typesys import TFloatUnit


def _check(src: str, telemetry=None):
    prog = parse_source(src)
    check_program(prog, telemetry)


def test_valid_gap_query() -> None:
    _check(
        """
        fn safe(gap: seconds) -> bool {
          let min_gap: seconds = seconds(2.0);
          return gap > min_gap;
        }
        query q {
          require safe(seconds(3.0));
        }
        """
    )


def test_reject_seconds_vs_percent_cmp() -> None:
    src = """
    query bad {
      require seconds(3.0) > percent(50.0);
    }
    """
    with pytest.raises(TypeError_) as exc:
        _check(src)
    assert "compare" in str(exc.value).lower()


def test_reject_assignment_type_mismatch() -> None:
    src = """
    query bad {
      let x: seconds = percent(10.0);
    }
    """
    with pytest.raises(TypeError_) as exc:
        _check(src)
    assert "expected type" in str(exc.value)


def test_lap_ctor_requires_plain_int() -> None:
    with pytest.raises(TypeError_):
        _check(
            """
            query q {
              let l: lap = lap(seconds(3.0));
            }
            """
        )


def test_telemetry_bindings() -> None:
    _check(
        """
        query q {
          require gap > seconds(2.0);
        }
        """,
        telemetry={"gap": TFloatUnit("seconds")},
    )


def test_recursion_rejected() -> None:
    src = """
    fn a() -> bool { return b(); }
    fn b() -> bool { return a(); }
    query q { require false; }
    """
    with pytest.raises(TypeError_):
        _check(src)


def test_equality_requires_compatible_units() -> None:
    with pytest.raises(TypeError_):
        _check(
            """
            query q {
              require seconds(2.0) == percent(2.0);
            }
            """
        )
