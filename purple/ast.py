"""Abstract syntax trees for Purple (with source locations)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Union


# --- Types (surface syntax) ---


@dataclass(frozen=True, slots=True)
class NamedType:
    """Primitive or unit type spelled in source."""

    name: str  # int, float, bool, string, compound, seconds, ...
    line: int
    column: int


# --- Expressions ---


@dataclass(frozen=True, slots=True)
class LiteralExpr:
    """int, float, bool, string literal, or compound constant (SOFT, ...)."""

    value: Union[int, float, bool, str]
    line: int = 0
    column: int = 0


@dataclass(frozen=True, slots=True)
class VarExpr:
    name: str
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class UnaryExpr:
    op: Literal["not", "-"]
    operand: Expr
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class BinaryExpr:
    op: str
    left: Expr
    right: Expr
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class CallExpr:
    """User function call."""

    name: str
    args: tuple[Expr, ...]
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class UnitCtorExpr:
    """Built-in unit constructor: seconds(expr), lap(expr), ..."""

    unit: str  # seconds, percent, fuel, distance, lap, position
    arg: Expr
    line: int
    column: int


Expr = Union[LiteralExpr, VarExpr, UnaryExpr, BinaryExpr, CallExpr, UnitCtorExpr]


# --- Statements ---


@dataclass(frozen=True, slots=True)
class LetStmt:
    name: str
    type_ann: NamedType
    expr: Expr
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class RequireStmt:
    expr: Expr
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class ReturnStmt:
    expr: Expr
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class IfStmt:
    condition: Expr
    requires: tuple[RequireStmt, ...]
    line: int
    column: int


FunctionStmt = LetStmt


@dataclass(frozen=True, slots=True)
class Parameter:
    name: str
    type_ann: NamedType


@dataclass(frozen=True, slots=True)
class FunctionDecl:
    name: str
    params: tuple[Parameter, ...]
    return_type: NamedType
    body_lets: tuple[LetStmt, ...]
    return_stmt: ReturnStmt
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class ModelField:
    name: str
    value: LiteralExpr
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class ModelDecl:
    name: str
    fields: tuple[ModelField, ...]
    line: int
    column: int


QueryStmt = Union[LetStmt, RequireStmt, IfStmt]


@dataclass(frozen=True, slots=True)
class QueryDecl:
    name: str
    stmts: tuple[QueryStmt, ...]
    line: int
    column: int


Decl = Union[ModelDecl, FunctionDecl, QueryDecl]


@dataclass(frozen=True, slots=True)
class Program:
    decls: tuple[Decl, ...] = field(default_factory=tuple)
