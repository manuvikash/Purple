"""Evaluate Purple queries over telemetry after successful typechecking."""

from __future__ import annotations

import json
from collections.abc import Mapping, MutableMapping
from pathlib import Path

from purple import ast
from purple.errors import RuntimeError_

Value = float | int | bool | str


class _EvalError(Exception):
    pass


def load_telemetry_json(path: str | Path) -> dict[str, Value]:
    raw = Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise RuntimeError_("telemetry JSON must be an object", 0, 0)
    out: dict[str, Value] = {}
    for k, v in data.items():
        if isinstance(v, (int, float, str, bool)):
            out[str(k)] = v
        else:
            raise RuntimeError_("unsupported telemetry JSON value type", 0, 0)
    return out


def run_queries(program: ast.Program, telemetry: Mapping[str, Value]) -> dict[str, bool]:
    interp = Interpreter(program)
    interp.merge_globals(telemetry)
    return interp.run_all_queries()


def literal_py_value(lit: ast.LiteralExpr) -> Value:
    v = lit.value
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float, str)):
        return v
    raise RuntimeError_("invalid literal at runtime", lit.line, lit.column)


def eval_binary(op: str, left: Value, right: Value) -> Value:
    if op == "==":
        return bool(left == right)
    if op == "!=":
        return bool(left != right)

    if op in {"<", ">", "<=", ">="}:
        cmp = relational_compare(left, right)
        if cmp is None:
            raise _EvalError()
        if op == "<":
            return cmp < 0
        if op == ">":
            return cmp > 0
        if op == "<=":
            return cmp <= 0
        if op == ">=":
            return cmp >= 0

    if op in {"+", "-", "*"}:
        if isinstance(left, str) or isinstance(right, str):
            raise _EvalError()
        if isinstance(left, bool) or isinstance(right, bool):
            raise _EvalError()
        if isinstance(left, float) or isinstance(right, float):
            a, b = float(left), float(right)
            if op == "+":
                return a + b
            if op == "-":
                return a - b
            if op == "*":
                return a * b
        if isinstance(left, int) and isinstance(right, int):
            if op == "+":
                return left + right
            if op == "-":
                return left - right
            if op == "*":
                return left * right

    if op == "/":
        if isinstance(left, bool) or isinstance(right, bool):
            raise _EvalError()
        if float(right) == 0.0:
            raise RuntimeError_("division by zero", 1, 1)
        return float(left) / float(right)

    if op == "and":
        if isinstance(left, bool) and isinstance(right, bool):
            return left and right

    if op == "or":
        if isinstance(left, bool) and isinstance(right, bool):
            return left or right

    raise _EvalError()


def relational_compare(left: Value, right: Value) -> int | None:
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        if isinstance(left, bool) or isinstance(right, bool):
            return None
        a, b = float(left), float(right)
        if a < b:
            return -1
        if a > b:
            return 1
        return 0
    if isinstance(left, str) and isinstance(right, str):
        if left < right:
            return -1
        if left > right:
            return 1
        return 0
    return None


class Interpreter:
    """Runtime evaluation (assumes the program passes `check_program`)."""

    def __init__(self, program: ast.Program) -> None:
        self._program = program
        self._funcs: dict[str, ast.FunctionDecl] = {}
        env: MutableMapping[str, Value] = {}

        for d in program.decls:
            if isinstance(d, ast.FunctionDecl):
                self._funcs[d.name] = d
            elif isinstance(d, ast.ModelDecl):
                for f in d.fields:
                    env[f.name] = literal_py_value(f.value)

        self._globals: MutableMapping[str, Value] = env

    def merge_globals(self, telemetry: Mapping[str, Value]) -> None:
        self._globals = {**dict(self._globals), **dict(telemetry)}

    def run_all_queries(self) -> dict[str, bool]:
        out: dict[str, bool] = {}
        for d in self._program.decls:
            if isinstance(d, ast.QueryDecl):
                out[d.name] = self._run_query(d)
        return out

    def _run_query(self, q: ast.QueryDecl) -> bool:
        env: MutableMapping[str, Value] = dict(self._globals)
        for st in q.stmts:
            if isinstance(st, ast.LetStmt):
                env[st.name] = self.eval_expr(st.expr, env)
            elif isinstance(st, ast.RequireStmt):
                v = self.eval_expr(st.expr, env)
                if v is False:
                    return False
                if v is True:
                    continue
                raise RuntimeError_("require needs bool value", st.line, st.column)
            elif isinstance(st, ast.IfStmt):
                cond = self.eval_expr(st.condition, env)
                if cond is True:
                    for r in st.requires:
                        rv = self.eval_expr(r.expr, env)
                        if rv is False:
                            return False
                        if rv is not True:
                            raise RuntimeError_("require needs bool", r.line, r.column)
                elif cond is not False:
                    raise RuntimeError_("if expects bool condition", st.line, st.column)
            else:
                raise RuntimeError_("unsupported stmt", q.line, q.column)
        return True

    def eval_expr(self, expr: ast.Expr, env: Mapping[str, Value]) -> Value:
        if isinstance(expr, ast.LiteralExpr):
            return literal_py_value(expr)
        if isinstance(expr, ast.VarExpr):
            if expr.name not in env:
                raise RuntimeError_("undefined {!r}".format(expr.name), expr.line, expr.column)
            return env[expr.name]
        if isinstance(expr, ast.UnaryExpr):
            inner = self.eval_expr(expr.operand, env)
            if expr.op == "not":
                if not isinstance(inner, bool):
                    raise RuntimeError_("not expects bool", expr.line, expr.column)
                return not inner
            if expr.op == "-":
                if isinstance(inner, bool):
                    raise RuntimeError_("bad '-' operand", expr.line, expr.column)
                if isinstance(inner, int):
                    return -inner
                if isinstance(inner, float):
                    return -inner
                raise RuntimeError_("bad '-' operand", expr.line, expr.column)
            raise RuntimeError_("unknown unary", expr.line, expr.column)

        if isinstance(expr, ast.BinaryExpr):
            lv = self.eval_expr(expr.left, env)
            rv = self.eval_expr(expr.right, env)
            try:
                result = eval_binary(expr.op, lv, rv)
            except _EvalError:
                raise RuntimeError_("illegal operands", expr.line, expr.column)
            return result

        if isinstance(expr, ast.UnitCtorExpr):
            inner = self.eval_expr(expr.arg, env)
            if expr.unit == "lap" or expr.unit == "position":
                if isinstance(inner, bool):
                    raise RuntimeError_("lap/position need ints", expr.line, expr.column)
                if isinstance(inner, int):
                    return inner
                raise RuntimeError_("lap/position need ints", expr.line, expr.column)
            if expr.unit in ("seconds", "percent", "fuel", "distance"):
                if isinstance(inner, bool) or isinstance(inner, str):
                    raise RuntimeError_("invalid ctor operand", expr.line, expr.column)
                return float(inner)
            raise RuntimeError_("unknown ctor", expr.line, expr.column)

        if isinstance(expr, ast.CallExpr):
            callee = self._funcs.get(expr.name)
            if callee is None or len(callee.params) != len(expr.args):
                raise RuntimeError_("bad call {!r}".format(expr.name), expr.line, expr.column)
            inner_env = dict(env)
            for pa, ae in zip(callee.params, expr.args):
                inner_env[pa.name] = self.eval_expr(ae, env)
            for lt in callee.body_lets:
                inner_env[lt.name] = self.eval_expr(lt.expr, inner_env)
            return self.eval_expr(callee.return_stmt.expr, inner_env)

        raise RuntimeError_("unsupported expr", 1, 1)
