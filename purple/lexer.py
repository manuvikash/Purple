"""Lexical analysis for Purple."""

from __future__ import annotations

from purple.errors import LexerError
from purple.token import KEYWORDS, Token, TokenType


class Lexer:
    def __init__(self, source: str) -> None:
        self._src = source
        self._i = 0
        self._line = 1
        self._col = 1

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while True:
            t = self._next_token()
            tokens.append(t)
            if t.type == TokenType.EOF:
                break
        return tokens

    def _peek(self) -> str | None:
        return self._src[self._i] if self._i < len(self._src) else None

    def _advance(self) -> str | None:
        ch = self._peek()
        if ch is None:
            return None
        if ch == "\n":
            self._line += 1
            self._col = 1
        else:
            self._col += 1
        self._i += 1
        return ch

    def _skip_ws_and_comments(self) -> None:
        while True:
            ch = self._peek()
            if ch is None:
                return
            if ch in " \t\r":
                self._advance()
            elif ch == "\n":
                self._advance()
            elif ch == "/" and self._peek_next() == "/":
                self._advance()
                self._advance()
                while (c := self._peek()) is not None and c != "\n":
                    self._advance()
            else:
                return

    def _peek_next(self) -> str | None:
        j = self._i + 1
        return self._src[j] if j < len(self._src) else None

    def _make_token(self, typ: TokenType, value, start_col: int) -> Token:
        return Token(typ, value, self._line, start_col)

    def _next_token(self) -> Token:
        self._skip_ws_and_comments()
        start_col = self._col
        ch = self._peek()
        if ch is None:
            return self._make_token(TokenType.EOF, None, start_col)

        if ch.isalpha() or ch == "_":
            return self._ident_or_kw(start_col)

        if ch.isdigit():
            return self._number(start_col)

        if ch == '"':
            return self._string(start_col)

        self._advance()

        match ch:
            case "+":
                return self._make_token(TokenType.PLUS, None, start_col)
            case "-":
                if self._peek() == ">":
                    self._advance()
                    return self._make_token(TokenType.ARROW, None, start_col)
                return self._make_token(TokenType.MINUS, None, start_col)
            case "*":
                return self._make_token(TokenType.STAR, None, start_col)
            case "(":
                return self._make_token(TokenType.LPAREN, None, start_col)
            case ")":
                return self._make_token(TokenType.RPAREN, None, start_col)
            case "{":
                return self._make_token(TokenType.LBRACE, None, start_col)
            case "}":
                return self._make_token(TokenType.RBRACE, None, start_col)
            case ",":
                return self._make_token(TokenType.COMMA, None, start_col)
            case ";":
                return self._make_token(TokenType.SEMICOLON, None, start_col)
            case ":":
                return self._make_token(TokenType.COLON, None, start_col)
            case "=":
                n = self._peek()
                if n == "=":
                    self._advance()
                    return self._make_token(TokenType.EQ, None, start_col)
                return self._make_token(TokenType.ASSIGN, None, start_col)
            case "!":
                if self._peek() != "=":
                    raise LexerError("expected '=' after '!'", self._line, start_col)
                self._advance()
                return self._make_token(TokenType.NE, None, start_col)
            case "<":
                if self._peek() == "=":
                    self._advance()
                    return self._make_token(TokenType.LE, None, start_col)
                return self._make_token(TokenType.LT, None, start_col)
            case ">":
                if self._peek() == "=":
                    self._advance()
                    return self._make_token(TokenType.GE, None, start_col)
                return self._make_token(TokenType.GT, None, start_col)
            case "/":
                return self._make_token(TokenType.SLASH, None, start_col)
            case _:
                raise LexerError(f"unexpected character {ch!r}", self._line, start_col)

    def _ident_or_kw(self, start_col: int) -> Token:
        buf: list[str] = []
        while True:
            ch = self._peek()
            if ch is None:
                break
            if ch.isalnum() or ch == "_":
                buf.append(ch)
                self._advance()
            else:
                break
        word = "".join(buf)
        typ = KEYWORDS.get(word, TokenType.IDENT)
        val = word if typ == TokenType.IDENT else None
        return self._make_token(typ, val, start_col)

    def _number(self, start_col: int) -> Token:
        buf: list[str] = []
        while True:
            ch = self._peek()
            if ch is not None and ch.isdigit():
                buf.append(ch)
                self._advance()
            else:
                break

        if self._peek() == "." and self._peek_next() and self._peek_next().isdigit():
            buf.append(".")
            self._advance()
            while True:
                ch = self._peek()
                if ch is not None and ch.isdigit():
                    buf.append(ch)
                    self._advance()
                else:
                    break
            return self._make_token(TokenType.FLOAT, float("".join(buf)), start_col)

        return self._make_token(TokenType.INTEGER, int("".join(buf)), start_col)

    def _string(self, start_col: int) -> Token:
        self._advance()  # opening quote
        buf: list[str] = []
        while True:
            ch = self._peek()
            if ch is None:
                raise LexerError("unterminated string", self._line, start_col)
            if ch == "\n":
                raise LexerError("newline in string", self._line, self._col)
            if ch == '"':
                self._advance()
                return self._make_token(TokenType.STRING, "".join(buf), start_col)
            buf.append(ch)
            self._advance()
