"""Parser tests."""

import pytest

from purple import ast
from purple.errors import ParseError
from purple.lexer import Lexer
from purple.parser import parse_source


def test_parse_minimal_model_and_query() -> None:
    src = """
    model sprint { driver_a = "VER"; }
    fn ok(gap: seconds) -> bool {
      let m: seconds = seconds(2.0);
      return gap > m;
    }
    query feasible {
      require ok(seconds(3.0));
    }
    """
    program = parse_source(src)
    assert len(program.decls) == 3
    assert isinstance(program.decls[0], ast.ModelDecl)
    assert program.decls[0].name == "sprint"
    assert isinstance(program.decls[1], ast.FunctionDecl)
    assert program.decls[1].name == "ok"


def test_or_and_precedence_requires_and_under_or() -> None:
    """`a or b and c` groups as `a or (b and c)`."""
    program = parse_source("query q { require true or false and false; }")
    req = program.decls[0].stmts[0]
    assert isinstance(req, ast.RequireStmt)
    e = req.expr
    assert isinstance(e, ast.BinaryExpr) and e.op == "or"
    assert isinstance(e.right, ast.BinaryExpr) and e.right.op == "and"


def test_not_binds_tighter_than_and() -> None:
    program = parse_source("query q { require not true and false; }")
    e = program.decls[0].stmts[0].expr
    assert isinstance(e, ast.BinaryExpr) and e.op == "and"
    assert isinstance(e.left, ast.UnaryExpr) and e.left.op == "not"


def test_comparison_non_chain_in_parser() -> None:
    """Each comparison is binary; chaining would be successive binops."""
    program = parse_source("query q { require 1 < 2 < 3; }")
    e = program.decls[0].stmts[0].expr
    assert isinstance(e, ast.BinaryExpr) and e.op == "<"


def test_if_require_only_body() -> None:
    src = """
    query q {
      if true {
        require false;
      }
    }
    """
    program = parse_source(src)
    st = program.decls[0].stmts[0]
    assert isinstance(st, ast.IfStmt)


def test_fn_must_end_with_return() -> None:
    with pytest.raises(ParseError):
        parse_source(
            """
            fn bad() -> int {
              let x: int = 1;
            }
            """
        )


def test_parse_error_unexpected_eof() -> None:
    from purple.parser import Parser

    toks = Lexer('query q { require 1').tokenize()
    with pytest.raises(ParseError):
        Parser(toks).parse()
