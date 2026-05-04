"""Purple DSL error types."""


class PurpleError(Exception):
    """Base class for Purple errors with source location."""

    def __init__(self, message: str, line: int = 0, column: int = 0) -> None:
        self.message = message
        self.line = line
        self.column = column
        loc = f"Line {line}, column {column}: " if line else ""
        super().__init__(f"{loc}{message}")


class LexerError(PurpleError):
    """Invalid token or unexpected character."""


class ParseError(PurpleError):
    """Syntax error."""


class TypeError_(PurpleError):
    """Static type error (named with underscore to avoid shadowing builtin)."""


class RuntimeError_(PurpleError):
    """Runtime evaluation error (named with underscore to avoid shadowing builtin)."""
