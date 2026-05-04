"""Static type checking for Purple."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping

from purple import ast
from purple.errors import TypeError_
from purple.typesys import (
    FLOAT_UNITS,
    TInt,
    TFloat,
    TBool,
    TString,
    TCompound,
    TIntUnit,
    TFloatUnit,
    PurpleType,
    binary_arith_type,
    comparison_compatible,
    fmt_type,
    is_numeric,
    plain_numeric,
    typename_from_ann,
)

COMPOUND_NAMES = frozenset({"SOFT", "MEDIUM", "HARD", "INTER", "WET"})


def check_program(program: ast.Program, telemetry: Mapping[str, PurpleType] | None = None):
    telemetry = telemetry or {}
    chk = _Checker(program, telemetry)
    chk.check_program()
    return chk


class _Checker:
    def __init__(self, program: ast.Program, telemetry: Mapping[str, PurpleType]) -> None:
        self._program = program
        self._telemetry = dict(telemetry)
        self._models: MutableMapping[str, PurpleType] = {}
        self._functions: dict[str, ast.FunctionDecl] = {}

    def check_program(self) -> None:
        for d in self._program.decls:
            if isinstance(d, ast.ModelDecl):
                self._index_model(d)
            elif isinstance(d, ast.FunctionDecl):
                self._functions[d.name] = d

        self._reject_recursive_calls()

        for d in self._program.decls:
            if isinstance(d, ast.FunctionDecl):
                self._check_function(d)
            elif isinstance(d, ast.QueryDecl):
                self._check_query(d)

    def _reject_recursive_calls(self) -> None:
        edges: dict[str, set[str]] = {
            name: {c for c in self._calls_in_function(decl) if c in self._functions}
            for name, decl in self._functions.items()
        }

        grey: set[str] = set()
        black: set[str] = set()

        def visit(u: str) -> None:
            if u in black:
                return
            if u in grey:
                fd = self._functions[u]
                raise TypeError_(f"cyclic recursion involving '{u}'", fd.line, fd.column)
            grey.add(u)
            for v in sorted(edges.get(u, ())):
                if v in self._functions:
                    visit(v)
            grey.discard(u)
            black.add(u)

        for name in sorted(self._functions):
            if name not in black:
                visit(name)

    def _calls_in_function(self, decl: ast.FunctionDecl) -> set[str]:
        found: set[str] = set()
        stack = [decl.return_stmt.expr, *[s.expr for s in decl.body_lets]]
        while stack:
            e = stack.pop()
            self._walk_expr_calls(e, found, stack)
        return found

    def _walk_expr_calls(self, e: ast.Expr, found: set[str], stack: list) -> None:
        if isinstance(e, ast.CallExpr):
            found.add(e.name)
            stack.extend(e.args)
            return
        if isinstance(e, ast.BinaryExpr):
            stack.extend((e.right, e.left))
            return
        if isinstance(e, ast.UnaryExpr):
            stack.append(e.operand)
            return
        if isinstance(e, ast.UnitCtorExpr):
            stack.append(e.arg)

    def _index_model(self, decl: ast.ModelDecl) -> None:
        for f in decl.fields:
            self._models[f.name] = literal_type_static(f.value)

    def _check_query(self, q: ast.QueryDecl) -> None:
        scopes: MutableMapping[str, PurpleType] = {}
        scopes.update(self._models)
        scopes.update(self._telemetry)

        for st in q.stmts:
            if isinstance(st, ast.LetStmt):
                declared = typename_from_ann(st.type_ann.name)
                inferred = self._expr_type(st.expr, scopes)
                if not assigns_compatible(declared, inferred):
                    raise TypeError_(
                        f'expected type {fmt_type(declared)}, got {fmt_type(inferred)}',
                        st.line,
                        st.column,
                    )
                scopes[st.name] = declared
            elif isinstance(st, ast.RequireStmt):
                rt = self._expr_type(st.expr, scopes)
                if type(rt) is not TBool:
                    raise TypeError_("require expects bool", st.line, st.column)
            elif isinstance(st, ast.IfStmt):
                ct = self._expr_type(st.condition, scopes)
                if type(ct) is not TBool:
                    raise TypeError_("if condition must be bool", st.line, st.column)
                for r in st.requires:
                    rt = self._expr_type(r.expr, scopes)
                    if type(rt) is not TBool:
                        raise TypeError_("require expects bool", r.line, r.column)

    def _check_function(self, decl: ast.FunctionDecl) -> None:
        scopes = {p.name: typename_from_ann(p.type_ann.name) for p in decl.params}
        for st in decl.body_lets:
            declared = typename_from_ann(st.type_ann.name)
            inferred = self._expr_type(st.expr, scopes)
            if not assigns_compatible(declared, inferred):
                raise TypeError_(
                    f'expected type {fmt_type(declared)}, got {fmt_type(inferred)}',
                    st.line,
                    st.column,
                )
            scopes[st.name] = declared
        ret_expected = typename_from_ann(decl.return_type.name)
        ret_got = self._expr_type(decl.return_stmt.expr, scopes)
        if not assigns_compatible(ret_expected, ret_got):
            raise TypeError_(
                f'expected return type {fmt_type(ret_expected)}, got {fmt_type(ret_got)}',
                decl.return_stmt.line,
                decl.return_stmt.column,
            )

    def _expr_type(self, e: ast.Expr, scopes: Mapping[str, PurpleType]) -> PurpleType:
        if isinstance(e, ast.LiteralExpr):
            return literal_type_static(e)
        if isinstance(e, ast.VarExpr):
            if e.name not in scopes:
                raise TypeError_("undefined variable {!r}".format(e.name), e.line, e.column)
            return scopes[e.name]
        if isinstance(e, ast.UnaryExpr):
            inn = self._expr_type(e.operand, scopes)
            if e.op == "not":
                if type(inn) is not TBool:
                    raise TypeError_("operator not expects bool", e.line, e.column)
                return TBool()
            if e.op == "-":
                if not is_numeric(inn):
                    raise TypeError_("unary '-' expects numeric type", e.line, e.column)
                return inn
            raise TypeError_("internal unary", e.line, e.column)
        if isinstance(e, ast.BinaryExpr):
            tl = self._expr_type(e.left, scopes)
            tr = self._expr_type(e.right, scopes)

            if e.op in "+-*/":
                res = binary_arith_type(e.op, tl, tr)
                if res is None:
                    raise TypeError_(
                        f"invalid arithmetic for {fmt_type(tl)} and {fmt_type(tr)}",
                        e.line,
                        e.column,
                    )
                return res

            if e.op in ("==", "!=", "<", ">", "<=", ">="):
                if not comparison_compatible(tl, tr):
                    raise TypeError_(
                        f"cannot compare {fmt_type(tl)} with {fmt_type(tr)}",
                        e.line,
                        e.column,
                    )

                tl2, tr2 = maybe_promote_numeric_cmp(tl, tr)
                if relational_op(e.op) and not relational_operands_ordered(tl2, tr2):
                    raise TypeError_(
                        f"comparison not supported for {fmt_type(tl)} and {fmt_type(tr)}",
                        e.line,
                        e.column,
                    )

                return TBool()

            if e.op in ("and", "or"):
                if type(tl) is not TBool or type(tr) is not TBool:
                    raise TypeError_("boolean operators require bool operands", e.line, e.column)
                return TBool()

            raise TypeError_(f"unknown operator {e.op!r}", e.line, e.column)

        if isinstance(e, ast.UnitCtorExpr):
            inn = self._expr_type(e.arg, scopes)
            return unit_ctor_result(e.unit, inn, e.line, e.column)

        if isinstance(e, ast.CallExpr):
            return self._call_type(e, scopes)

        raise TypeError_("internal AST node not handled", 1, 1)

    def _call_type(self, e: ast.CallExpr, scopes: Mapping[str, PurpleType]) -> PurpleType:
        if e.name not in self._functions:
            raise TypeError_("undefined function {!r}".format(e.name), e.line, e.column)
        fb = self._functions[e.name]
        if len(fb.params) != len(e.args):
            raise TypeError_("wrong arity for {!r}".format(e.name), e.line, e.column)

        for pdecl, arg in zip(fb.params, e.args):
            pt = typename_from_ann(pdecl.type_ann.name)
            gt = self._expr_type(arg, scopes)
            if not assigns_compatible(pt, gt):
                raise TypeError_(
                    f"type mismatch for argument {pdecl.name!r}: "
                    f"expected {fmt_type(pt)}, got {fmt_type(gt)}",
                    e.line,
                    e.column,
                )

        return typename_from_ann(fb.return_type.name)


def assigns_compatible(declared: PurpleType, inferred: PurpleType) -> bool:
    if isinstance(declared, TInt) and isinstance(inferred, TInt):
        return True
    if isinstance(declared, TFloat) and isinstance(inferred, (TInt, TFloat)):
        return True
    if isinstance(declared, TBool) and isinstance(inferred, TBool):
        return True
    if isinstance(declared, TString) and isinstance(inferred, TString):
        return True
    if isinstance(declared, TCompound) and isinstance(inferred, TCompound):
        return True
    if isinstance(declared, TIntUnit) and isinstance(inferred, TIntUnit):
        return declared.unit == inferred.unit
    if isinstance(declared, TFloatUnit) and isinstance(inferred, TFloatUnit):
        return declared.unit == inferred.unit
    return False


def maybe_promote_numeric_cmp(tl: PurpleType, tr: PurpleType) -> tuple[PurpleType, PurpleType]:
    if plain_numeric(tl) and plain_numeric(tr):
        if isinstance(tl, TInt) and isinstance(tr, TFloat):
            return TFloat(), tr
        if isinstance(tl, TFloat) and isinstance(tr, TInt):
            return tl, TFloat()
    return tl, tr


def relational_op(op: str) -> bool:
    return op in ("<", ">", "<=", ">=")


def relational_operands_ordered(left: PurpleType, right: PurpleType) -> bool:
    if isinstance(left, TBool):
        return False
    if isinstance(left, (TString, TCompound)) or isinstance(right, (TString, TCompound)):
        return False
    return comparison_compatible(left, right)


def unit_ctor_result(
    unit_name: str, arg_ty: PurpleType, line: int, column: int
) -> PurpleType:
    if unit_name in FLOAT_UNITS:
        if not isinstance(arg_ty, (TInt, TFloat)):
            raise TypeError_(
                f"{unit_name}() expects plain int/float operand", line, column
            )
        return TFloatUnit(unit_name)

    if unit_name == "lap" or unit_name == "position":
        if type(arg_ty) is not TInt:
            raise TypeError_(
                f"{unit_name}() requires plain int operand", line, column
            )
        return TIntUnit(unit_name)

    raise TypeError_("unknown unit constructor", line, column)


def literal_type_static(lit: ast.LiteralExpr) -> PurpleType:
    val = lit.value
    if isinstance(val, bool):
        return TBool()
    if isinstance(val, str):
        if val in COMPOUND_NAMES:
            return TCompound()
        return TString()
    if isinstance(val, int):
        return TInt()
    if isinstance(val, float):
        return TFloat()
    raise TypeError_("invalid literal", lit.line, lit.column)
