"""Recursive-descent parser for Purple."""

from __future__ import annotations

from purple import ast
from purple.errors import ParseError
from purple.token import Token, TokenType

UNIT_CTORS = frozenset(
    {
        TokenType.SECONDS,
        TokenType.PERCENT,
        TokenType.FUEL,
        TokenType.DISTANCE,
        TokenType.LAP,
        TokenType.POSITION,
    }
)

COMPOUND_TOKENS = frozenset(
    {
        TokenType.SOFT,
        TokenType.MEDIUM,
        TokenType.HARD,
        TokenType.INTER,
        TokenType.WET,
    }
)

COMPOUND_NAME: dict[TokenType, str] = {
    TokenType.SOFT: "SOFT",
    TokenType.MEDIUM: "MEDIUM",
    TokenType.HARD: "HARD",
    TokenType.INTER: "INTER",
    TokenType.WET: "WET",
}

TYPE_TOKENS = frozenset(
    {
        TokenType.INT,
        TokenType.FLOAT_KW,
        TokenType.BOOL,
        TokenType.STRING_KW,
        TokenType.COMPOUND,
        TokenType.SECONDS,
        TokenType.PERCENT,
        TokenType.FUEL,
        TokenType.DISTANCE,
        TokenType.LAP,
        TokenType.POSITION,
    }
)

TYPE_SPELLING: dict[TokenType, str] = {
    TokenType.INT: "int",
    TokenType.FLOAT_KW: "float",
    TokenType.BOOL: "bool",
    TokenType.STRING_KW: "string",
    TokenType.COMPOUND: "compound",
    TokenType.SECONDS: "seconds",
    TokenType.PERCENT: "percent",
    TokenType.FUEL: "fuel",
    TokenType.DISTANCE: "distance",
    TokenType.LAP: "lap",
    TokenType.POSITION: "position",
}


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self._t = tokens
        self._i = 0

    def parse(self) -> ast.Program:
        decls: list[ast.Decl] = []
        while not self._at(TokenType.EOF):
            decls.append(self._declaration())
        return ast.Program(tuple(decls))

    def _declaration(self) -> ast.Decl:
        tok = self._peek()
        if tok.type == TokenType.MODEL:
            return self._model_decl()
        if tok.type == TokenType.FN:
            return self._function_decl()
        if tok.type == TokenType.QUERY:
            return self._query_decl()
        raise ParseError(
            f"expected model, fn, or query, got {tok.type.name}",
            tok.line,
            tok.column,
        )

    def _model_decl(self) -> ast.ModelDecl:
        start = self._consume(TokenType.MODEL)
        name_tok = self._consume(TokenType.IDENT)
        self._consume(TokenType.LBRACE)
        fields: list[ast.ModelField] = []
        while not self._at(TokenType.RBRACE):
            fields.append(self._model_field())
        self._consume(TokenType.RBRACE)
        return ast.ModelDecl(
            name=name_tok.value,
            fields=tuple(fields),
            line=start.line,
            column=start.column,
        )

    def _model_field(self) -> ast.ModelField:
        field_name = self._consume(TokenType.IDENT)
        self._consume(TokenType.ASSIGN)
        lit = self._literal_expr()
        self._consume(TokenType.SEMICOLON)
        return ast.ModelField(
            name=field_name.value,
            value=lit,
            line=field_name.line,
            column=field_name.column,
        )

    def _literal_expr(self) -> ast.LiteralExpr:
        """Literal for model fields (no unit constructors)."""
        tok = self._peek()
        if tok.type == TokenType.INTEGER:
            self._advance()
            return ast.LiteralExpr(tok.value, tok.line, tok.column)
        if tok.type == TokenType.FLOAT:
            self._advance()
            return ast.LiteralExpr(tok.value, tok.line, tok.column)
        if tok.type == TokenType.TRUE:
            self._advance()
            return ast.LiteralExpr(True, tok.line, tok.column)
        if tok.type == TokenType.FALSE:
            self._advance()
            return ast.LiteralExpr(False, tok.line, tok.column)
        if tok.type == TokenType.STRING:
            self._advance()
            return ast.LiteralExpr(tok.value, tok.line, tok.column)
        if tok.type in COMPOUND_TOKENS:
            self._advance()
            return ast.LiteralExpr(COMPOUND_NAME[tok.type], tok.line, tok.column)
        raise ParseError(
            f"expected literal, got {tok.type.name}",
            tok.line,
            tok.column,
        )

    def _function_decl(self) -> ast.FunctionDecl:
        start = self._consume(TokenType.FN)
        name_tok = self._consume(TokenType.IDENT)
        self._consume(TokenType.LPAREN)
        params: list[ast.Parameter] = []
        if not self._at(TokenType.RPAREN):
            params.append(self._parameter())
            while self._at(TokenType.COMMA):
                self._advance()
                params.append(self._parameter())
        self._consume(TokenType.RPAREN)
        self._consume(TokenType.ARROW)
        ret = self._parse_type()
        self._consume(TokenType.LBRACE)
        lets: list[ast.LetStmt] = []
        while self._peek().type == TokenType.LET:
            lets.append(self._let_stmt())
        ret_stmt = self._return_stmt()
        self._consume(TokenType.RBRACE)
        return ast.FunctionDecl(
            name=name_tok.value,
            params=tuple(params),
            return_type=ret,
            body_lets=tuple(lets),
            return_stmt=ret_stmt,
            line=start.line,
            column=start.column,
        )

    def _parameter(self) -> ast.Parameter:
        ident = self._consume(TokenType.IDENT)
        self._consume(TokenType.COLON)
        ty = self._parse_type()
        return ast.Parameter(ident.value, ty)

    def _query_decl(self) -> ast.QueryDecl:
        start = self._consume(TokenType.QUERY)
        name_tok = self._consume(TokenType.IDENT)
        self._consume(TokenType.LBRACE)
        stmts: list[ast.QueryStmt] = []
        while not self._at(TokenType.RBRACE):
            stmts.append(self._query_stmt())
        self._consume(TokenType.RBRACE)
        return ast.QueryDecl(
            name=name_tok.value,
            stmts=tuple(stmts),
            line=start.line,
            column=start.column,
        )

    def _query_stmt(self) -> ast.QueryStmt:
        tok = self._peek()
        if tok.type == TokenType.LET:
            return self._let_stmt()
        if tok.type == TokenType.REQUIRE:
            return self._require_stmt()
        if tok.type == TokenType.IF:
            return self._if_stmt()
        raise ParseError(
            "expected let, require, or if inside query",
            tok.line,
            tok.column,
        )

    def _let_stmt(self) -> ast.LetStmt:
        start = self._consume(TokenType.LET)
        name_tok = self._consume(TokenType.IDENT)
        self._consume(TokenType.COLON)
        ty = self._parse_type()
        self._consume(TokenType.ASSIGN)
        e = self._expr()
        self._consume(TokenType.SEMICOLON)
        return ast.LetStmt(name_tok.value, ty, e, start.line, start.column)

    def _require_stmt(self) -> ast.RequireStmt:
        start = self._consume(TokenType.REQUIRE)
        e = self._expr()
        self._consume(TokenType.SEMICOLON)
        return ast.RequireStmt(e, start.line, start.column)

    def _return_stmt(self) -> ast.ReturnStmt:
        start = self._consume(TokenType.RETURN)
        e = self._expr()
        self._consume(TokenType.SEMICOLON)
        return ast.ReturnStmt(e, start.line, start.column)

    def _if_stmt(self) -> ast.IfStmt:
        start = self._consume(TokenType.IF)
        cond = self._expr()
        self._consume(TokenType.LBRACE)
        reqs: list[ast.RequireStmt] = []
        while self._peek().type == TokenType.REQUIRE:
            reqs.append(self._require_stmt())
        self._consume(TokenType.RBRACE)
        return ast.IfStmt(cond, tuple(reqs), start.line, start.column)

    def _parse_type(self) -> ast.NamedType:
        tok = self._peek()
        if tok.type not in TYPE_TOKENS:
            raise ParseError(f"expected type, got {tok.type.name}", tok.line, tok.column)
        self._advance()
        return ast.NamedType(TYPE_SPELLING[tok.type], tok.line, tok.column)

    # ---- expressions (precedence) ----

    def _expr(self) -> ast.Expr:
        return self._or_expr()

    def _or_expr(self) -> ast.Expr:
        left = self._and_expr()
        while self._at(TokenType.OR):
            op_tok = self._advance()
            right = self._and_expr()
            left = ast.BinaryExpr("or", left, right, op_tok.line, op_tok.column)
        return left

    def _and_expr(self) -> ast.Expr:
        left = self._eq_expr()
        while self._at(TokenType.AND):
            op_tok = self._advance()
            right = self._eq_expr()
            left = ast.BinaryExpr("and", left, right, op_tok.line, op_tok.column)
        return left

    def _eq_expr(self) -> ast.Expr:
        left = self._relational_expr()
        while self._at(TokenType.EQ) or self._at(TokenType.NE):
            op_tok = self._advance()
            op = "==" if op_tok.type == TokenType.EQ else "!="
            right = self._relational_expr()
            left = ast.BinaryExpr(op, left, right, op_tok.line, op_tok.column)
        return left

    def _relational_expr(self) -> ast.Expr:
        left = self._additive_expr()
        while True:
            if self._at(TokenType.LT):
                op_tok = self._advance()
                left = ast.BinaryExpr(
                    "<", left, self._additive_expr(), op_tok.line, op_tok.column
                )
            elif self._at(TokenType.GT):
                op_tok = self._advance()
                left = ast.BinaryExpr(
                    ">", left, self._additive_expr(), op_tok.line, op_tok.column
                )
            elif self._at(TokenType.LE):
                op_tok = self._advance()
                left = ast.BinaryExpr(
                    "<=", left, self._additive_expr(), op_tok.line, op_tok.column
                )
            elif self._at(TokenType.GE):
                op_tok = self._advance()
                left = ast.BinaryExpr(
                    ">=", left, self._additive_expr(), op_tok.line, op_tok.column
                )
            else:
                break
        return left

    def _additive_expr(self) -> ast.Expr:
        left = self._multiplicative_expr()
        while self._at(TokenType.PLUS) or self._at(TokenType.MINUS):
            op_tok = self._advance()
            op = "+" if op_tok.type == TokenType.PLUS else "-"
            right = self._multiplicative_expr()
            left = ast.BinaryExpr(op, left, right, op_tok.line, op_tok.column)
        return left

    def _multiplicative_expr(self) -> ast.Expr:
        left = self._unary_expr()
        while self._at(TokenType.STAR) or self._at(TokenType.SLASH):
            op_tok = self._advance()
            op = "*" if op_tok.type == TokenType.STAR else "/"
            right = self._unary_expr()
            left = ast.BinaryExpr(op, left, right, op_tok.line, op_tok.column)
        return left

    def _unary_expr(self) -> ast.Expr:
        if self._at(TokenType.NOT):
            op_tok = self._advance()
            inner = self._unary_expr()
            return ast.UnaryExpr("not", inner, op_tok.line, op_tok.column)
        if self._at(TokenType.MINUS):
            op_tok = self._advance()
            inner = self._unary_expr()
            return ast.UnaryExpr("-", inner, op_tok.line, op_tok.column)
        return self._call_expr()

    def _call_expr(self) -> ast.Expr:
        tok = self._peek()
        if tok.type == TokenType.IDENT and self._next_is(TokenType.LPAREN):
            return self._function_call()

        # unit constructor: keywords like seconds (expr)
        if tok.type in UNIT_CTORS:
            unit_name = TYPE_SPELLING[tok.type]
            line, col = tok.line, tok.column
            self._advance()
            self._consume(TokenType.LPAREN)
            arg = self._expr()
            self._consume(TokenType.RPAREN)
            return ast.UnitCtorExpr(unit_name, arg, line, col)

        return self._primary()

    def _function_call(self) -> ast.Expr:
        name_tok = self._consume(TokenType.IDENT)
        self._consume(TokenType.LPAREN)
        args: list[ast.Expr] = []
        if not self._at(TokenType.RPAREN):
            args.append(self._expr())
            while self._at(TokenType.COMMA):
                self._advance()
                args.append(self._expr())
        self._consume(TokenType.RPAREN)
        return ast.CallExpr(name_tok.value, tuple(args), name_tok.line, name_tok.column)

    def _primary(self) -> ast.Expr:
        tok = self._peek()

        if tok.type == TokenType.INTEGER:
            self._advance()
            return ast.LiteralExpr(tok.value, tok.line, tok.column)
        if tok.type == TokenType.FLOAT:
            self._advance()
            return ast.LiteralExpr(tok.value, tok.line, tok.column)
        if tok.type == TokenType.TRUE:
            self._advance()
            return ast.LiteralExpr(True, tok.line, tok.column)
        if tok.type == TokenType.FALSE:
            self._advance()
            return ast.LiteralExpr(False, tok.line, tok.column)
        if tok.type == TokenType.STRING:
            self._advance()
            return ast.LiteralExpr(tok.value, tok.line, tok.column)
        if tok.type in COMPOUND_TOKENS:
            self._advance()
            return ast.LiteralExpr(COMPOUND_NAME[tok.type], tok.line, tok.column)

        if tok.type == TokenType.IDENT:
            self._advance()
            return ast.VarExpr(tok.value, tok.line, tok.column)

        if tok.type == TokenType.LPAREN:
            self._advance()
            e = self._expr()
            self._consume(TokenType.RPAREN)
            return e

        raise ParseError(f"expected expression, got {tok.type.name}", tok.line, tok.column)

    def _next_is(self, typ: TokenType) -> bool:
        j = self._i + 1
        return j < len(self._t) and self._t[j].type == typ

    def _peek(self) -> Token:
        return self._t[self._i]

    def _at(self, typ: TokenType) -> bool:
        return self._peek().type == typ

    def _advance(self) -> Token:
        t = self._peek()
        if t.type != TokenType.EOF:
            self._i += 1
        return t

    def _consume(self, typ: TokenType) -> Token:
        t = self._peek()
        if t.type != typ:
            raise ParseError(f"expected {typ.name}, got {t.type.name}", t.line, t.column)
        return self._advance()


def parse_tokens(tokens: list[Token]) -> ast.Program:
    return Parser(tokens).parse()


def parse_source(source: str) -> ast.Program:
    from purple.lexer import Lexer

    return parse_tokens(Lexer(source).tokenize())
