# Purple: A DSL for Formula 1 Race Strategy

This report summarizes the Purple language and the interpreter implemented in `purple/`.

## Introduction

Purple is a small domain-specific language for expressing race-strategy predicates over telemetry data. It trades generality for static guarantees: programs are checked before execution so unit mistakes and arity errors surface early.

## Language Design

Programs are modeled as immutable declarations: a sequence of models, functions, and queries. Models capture static literals, functions encapsulate reused logic ending in `return`, and queries accumulate `require` statements that must all succeed for the query to evaluate to **true**.

The surface syntax aligns with the project PRD: typed `let`, boolean connectives, unary `not`, standard arithmetic precedence, relational operators, guard-style `if` blocks that expand to nested `require` checks, and first-class literals for tyre compounds (`SOFT`, `MEDIUM`, `HARD`, `INTER`, `WET`). No loops, recursion, or user-defined types are supported.

## Type System

The checker models plain `int`/`float` plus domain units lifted from telemetry (`seconds`, `percent`, `fuel`, `distance`, `lap`, `position`). Operators follow the documented rules:

- homogeneous unit arithmetic stays in-band (e.g. `float<seconds>` + `float<seconds>`)
- multiplying or dividing measurable floats by scalars preserves the measurable unit unless both operands carry the same float unit—in which case division yields plain `float`
- cross-unit mixing is rejected
- `lap`/`position` constructors require plain integers
- `let` binds must match annotated types modulo the PRD-promotion case (`int` can satisfy an annotated `float`)
- Queries may reference telemetry variables supplied through an auxiliary schema dictionary passed into `check_program`

Recursion graphs are statically rejected whenever a cyclic call dependency exists among declarations.

## Implementation

The pipeline mirrors the PRD architecture:

1. `lexer.py` tokenizes source with line/column tracking and `//` comments.
2. `parser.py` builds a structured AST with explicit precedence for boolean, relational, and arithmetic layers.
3. `typesys.py` centralizes internal type constants and operator typing helpers.
4. `checker.py` wires scope models, functions, queries, call graphs, and telemetry assumptions together.
5. `interpreter.py` evaluates checked programs; JSON helpers load telemetry maps that merge with model literals.

The CLI (`python -m purple`) accepts a program file plus optional telemetry value and type JSON blobs for quick experiments.

## Evaluation

The automated suite (`pytest`) covers:

- lexer tokenization and comment handling
- parser grammar edge cases (precedence, malformed functions)
- representative type errors (unit mismatch, bad constructors, recursion)
- interpreter happy paths, telemetry wiring, and optional query control flow

These tests align with the PRD goal of catching domain errors before execution.

## Comparison with Python

Python offers rich escape hatches (implicit truthiness, duck typing, heavy operator overloading) that reduce boilerplate but make domain mistakes easy. Purple constrains the surface: only the exposed operators exist, unit tags are first-class in the type checker, and programs cannot mutate state beyond `let` bindings. The trade-off is expressiveness—anything outside the grammar requires changing the host implementation—but the resulting programs are short, reviewable, and mechanically verifiable.

## Limitations & Future Work

- Telemetry typing is provided out-of-band through `check_program(..., telemetry=...)` rather than schema declarations in-source.
- There is no IDE integration or pretty printer yet.
- Error messages could carry richer suggestions (e.g., expected unit names).
- Unit conversions remain intentionally unimplemented; future work could add explicit conversion functions while keeping the language non-Turing-complete.

