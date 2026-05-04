"""Lexer tests."""

import pytest

from purple.errors import LexerError
from purple.lexer import Lexer
from purple.token import TokenType


def types(source: str) -> list[TokenType]:
    return [t.type for t in Lexer(source).tokenize()]


def test_keywords_and_literals() -> None:
    src = '''
    model m { track = "Monza"; }
    fn f(x: int) -> bool { return true; }
    '''
    tokens = Lexer(src).tokenize()
    assert TokenType.MODEL in [t.type for t in tokens]
    assert TokenType.STRING in [t.type for t in tokens]
    assert any(t.type == TokenType.STRING and t.value == "Monza" for t in tokens)


def test_numbers_and_operators() -> None:
    t = types("42 3.14 + - * / == != < <= > >=")
    expect = [
        TokenType.INTEGER,
        TokenType.FLOAT,
        TokenType.PLUS,
        TokenType.MINUS,
        TokenType.STAR,
        TokenType.SLASH,
        TokenType.EQ,
        TokenType.NE,
        TokenType.LT,
        TokenType.LE,
        TokenType.GT,
        TokenType.GE,
        TokenType.EOF,
    ]
    assert t == expect


def test_arrow_minus() -> None:
    t = types("fn g() -> int {")
    assert t[:5] == [TokenType.FN, TokenType.IDENT, TokenType.LPAREN, TokenType.RPAREN, TokenType.ARROW]


def test_compounds_and_boolean() -> None:
    t = Lexer("SOFT MEDIUM HARD true false").tokenize()
    assert [x.type for x in t][:5] == [
        TokenType.SOFT,
        TokenType.MEDIUM,
        TokenType.HARD,
        TokenType.TRUE,
        TokenType.FALSE,
    ]


def test_comment_skip() -> None:
    t = types("let // comment\n x")
    assert t == [TokenType.LET, TokenType.IDENT, TokenType.EOF]
    toks = Lexer("// hi\nmodel").tokenize()
    assert toks[0].type == TokenType.MODEL


def test_lexer_error_bad_char() -> None:
    with pytest.raises(LexerError):
        Lexer("`").tokenize()
