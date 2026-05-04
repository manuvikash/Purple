"""Internal type representations and typing helpers for Purple."""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet


@dataclass(frozen=True, slots=True)
class TInt:
    """Plain int (dimensionless integer)."""


@dataclass(frozen=True, slots=True)
class TFloat:
    """Plain float (dimensionless float)."""


@dataclass(frozen=True, slots=True)
class TIntUnit:
    """int<lap> or int<position>."""

    unit: str  # lap | position


@dataclass(frozen=True, slots=True)
class TFloatUnit:
    """float with a domain unit."""

    unit: str  # seconds | percent | fuel | distance


@dataclass(frozen=True, slots=True)
class TBool:
    pass


@dataclass(frozen=True, slots=True)
class TString:
    pass


@dataclass(frozen=True, slots=True)
class TCompound:
    pass


PurpleType = TInt | TFloat | TIntUnit | TFloatUnit | TBool | TString | TCompound

INT_UNITS: FrozenSet[str] = frozenset({"lap", "position"})
FLOAT_UNITS: FrozenSet[str] = frozenset({"seconds", "percent", "fuel", "distance"})


def plain_numeric(t: PurpleType) -> bool:
    return isinstance(t, (TInt, TFloat))


def is_numeric(t: PurpleType) -> bool:
    return isinstance(t, (TInt, TFloat, TIntUnit, TFloatUnit))


def fmt_type(t: PurpleType) -> str:
    if isinstance(t, TInt):
        return "int"
    if isinstance(t, TFloat):
        return "float"
    if isinstance(t, TIntUnit):
        return f"int<{t.unit}>"
    if isinstance(t, TFloatUnit):
        return f"float<{t.unit}>"
    if isinstance(t, TBool):
        return "bool"
    if isinstance(t, TString):
        return "string"
    if isinstance(t, TCompound):
        return "compound"
    raise TypeError(repr(t))


def unify_plain_additive(left: PurpleType, right: PurpleType) -> PurpleType | None:
    """+ / - for plain ints/floats with int→float promotion."""
    if isinstance(left, TInt) and isinstance(right, TInt):
        return TInt()
    if plain_numeric(left) and plain_numeric(right):
        if isinstance(left, TFloat) or isinstance(right, TFloat):
            return TFloat()
    return None


def unify_plain_times(left: PurpleType, right: PurpleType) -> PurpleType | None:
    if isinstance(left, TInt) and isinstance(right, TInt):
        return TInt()
    if plain_numeric(left) and plain_numeric(right):
        if isinstance(left, TFloat) or isinstance(right, TFloat):
            return TFloat()
        return TInt()
    return None


def unify_plain_div(left: PurpleType, right: PurpleType) -> PurpleType | None:
    if plain_numeric(left) and plain_numeric(right):
        return TFloat()
    return None


def binary_arith_type(op: str, left: PurpleType, right: PurpleType) -> PurpleType | None:
    """Return result type or None when invalid."""

    if op in "+-":
        if isinstance(left, TIntUnit) and isinstance(right, TIntUnit):
            return TIntUnit(left.unit) if left.unit == right.unit else None
        if isinstance(left, TFloatUnit) and isinstance(right, TFloatUnit):
            return TFloatUnit(left.unit) if left.unit == right.unit else None
        if plain_numeric(left) and plain_numeric(right):
            return unify_plain_additive(left, right)
        return None

    if op == "*":
        if isinstance(left, TFloatUnit) and plain_numeric(right):
            return TFloatUnit(left.unit)
        if isinstance(right, TFloatUnit) and plain_numeric(left):
            return TFloatUnit(right.unit)
        return unify_plain_times(left, right)

    if op == "/":
        if isinstance(left, TFloatUnit) and plain_numeric(right):
            return TFloatUnit(left.unit)
        if isinstance(left, TFloatUnit) and isinstance(right, TFloatUnit):
            return TFloat() if left.unit == right.unit else None
        return unify_plain_div(left, right)

    raise AssertionError(f"unknown arithmetic op {op!r}")  # noqa: TRY004


def comparison_compatible(left: PurpleType, right: PurpleType) -> bool:
    """Whether ==, !=, relational ops accept these operand types."""

    if isinstance(left, TIntUnit) and isinstance(right, TIntUnit):
        return left.unit == right.unit
    if isinstance(left, TFloatUnit) and isinstance(right, TFloatUnit):
        return left.unit == right.unit
    if isinstance(left, TInt) and isinstance(right, TInt):
        return True
    if plain_numeric(left) and plain_numeric(right):
        return isinstance(left, (TInt, TFloat)) and isinstance(right, (TInt, TFloat))

    if isinstance(left, TBool) and isinstance(right, TBool):
        return True
    if isinstance(left, TString) and isinstance(right, TString):
        return True
    if isinstance(left, TCompound) and isinstance(right, TCompound):
        return True
    return False


def typename_from_ann(name: str) -> PurpleType:
    basic_map = {
        "int": TInt(),
        "float": TFloat(),
        "bool": TBool(),
        "string": TString(),
        "compound": TCompound(),
    }
    if name in basic_map:
        return basic_map[name]
    if name in INT_UNITS:
        return TIntUnit(name)
    if name in FLOAT_UNITS:
        return TFloatUnit(name)
    raise ValueError(f"unknown type annotation {name!r}")
