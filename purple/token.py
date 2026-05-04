"""Token definitions for the Purple lexer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class TokenType(Enum):
    # Literals
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()
    # Identifiers
    IDENT = auto()
    # Keywords / reserved
    MODEL = auto()
    FN = auto()
    QUERY = auto()
    LET = auto()
    REQUIRE = auto()
    RETURN = auto()
    IF = auto()
    OR = auto()
    AND = auto()
    NOT = auto()
    TRUE = auto()
    FALSE = auto()
    # Types (also unit constructor keywords)
    INT = auto()
    FLOAT_KW = auto()  # float type keyword
    BOOL = auto()
    STRING_KW = auto()
    COMPOUND = auto()
    SECONDS = auto()
    PERCENT = auto()
    FUEL = auto()
    DISTANCE = auto()
    LAP = auto()
    POSITION = auto()
    # Compound constants
    SOFT = auto()
    MEDIUM = auto()
    HARD = auto()
    INTER = auto()
    WET = auto()
    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    EQ = auto()
    NE = auto()
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    COMMA = auto()
    SEMICOLON = auto()
    COLON = auto()
    ARROW = auto()
    ASSIGN = auto()
    # Special
    EOF = auto()


KEYWORDS: dict[str, TokenType] = {
    "model": TokenType.MODEL,
    "fn": TokenType.FN,
    "query": TokenType.QUERY,
    "let": TokenType.LET,
    "require": TokenType.REQUIRE,
    "return": TokenType.RETURN,
    "if": TokenType.IF,
    "or": TokenType.OR,
    "and": TokenType.AND,
    "not": TokenType.NOT,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "int": TokenType.INT,
    "float": TokenType.FLOAT_KW,
    "bool": TokenType.BOOL,
    "string": TokenType.STRING_KW,
    "compound": TokenType.COMPOUND,
    "seconds": TokenType.SECONDS,
    "percent": TokenType.PERCENT,
    "fuel": TokenType.FUEL,
    "distance": TokenType.DISTANCE,
    "lap": TokenType.LAP,
    "position": TokenType.POSITION,
    "SOFT": TokenType.SOFT,
    "MEDIUM": TokenType.MEDIUM,
    "HARD": TokenType.HARD,
    "INTER": TokenType.INTER,
    "WET": TokenType.WET,
}


@dataclass(frozen=True, slots=True)
class Token:
    type: TokenType
    value: Any
    line: int
    column: int
