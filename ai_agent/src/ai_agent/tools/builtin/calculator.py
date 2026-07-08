"""Arithmetic evaluator restricted to a safe AST subset — no eval()."""

from __future__ import annotations

import ast
import math
import operator
from typing import Any

from ..base import Tool, ToolError

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "floor": math.floor,
    "ceil": math.ceil,
}
_CONSTANTS = {"pi": math.pi, "e": math.e, "tau": math.tau}

_MAX_POW_EXPONENT = 10_000


def _evaluate(node: ast.AST) -> float:
    match node:
        case ast.Expression(body=body):
            return _evaluate(body)
        case ast.Constant(value=value) if isinstance(value, int | float):
            return value
        case ast.Name(id=name) if name in _CONSTANTS:
            return _CONSTANTS[name]
        case ast.BinOp(left=left, op=op, right=right) if type(op) in _BIN_OPS:
            lhs, rhs = _evaluate(left), _evaluate(right)
            if isinstance(op, ast.Pow) and abs(rhs) > _MAX_POW_EXPONENT:
                raise ToolError(f"Exponent too large (limit {_MAX_POW_EXPONENT})")
            return _BIN_OPS[type(op)](lhs, rhs)
        case ast.UnaryOp(op=op, operand=operand) if type(op) in _UNARY_OPS:
            return _UNARY_OPS[type(op)](_evaluate(operand))
        case ast.Call(func=ast.Name(id=name), args=args, keywords=[]) if name in _FUNCTIONS:
            return _FUNCTIONS[name](*[_evaluate(arg) for arg in args])
        case _:
            raise ToolError(f"Unsupported expression element: {ast.dump(node)[:80]}")


class CalculatorTool(Tool):
    name = "calculator"
    description = (
        "Evaluate an arithmetic expression exactly. Supports + - * / // % **, "
        "parentheses, the constants pi/e/tau, and the functions "
        + ", ".join(sorted(_FUNCTIONS))
        + ". Use this for any nontrivial arithmetic instead of computing mentally."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The expression to evaluate, e.g. 'sqrt(2) * (3 + 4) ** 2'",
            }
        },
        "required": ["expression"],
    }

    def run(self, tool_input: dict[str, Any]) -> str:
        expression = tool_input.get("expression", "")
        if not isinstance(expression, str) or not expression.strip():
            raise ToolError("Provide a non-empty 'expression' string")
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            raise ToolError(f"Invalid expression: {exc}") from exc
        try:
            result = _evaluate(tree)
        except ZeroDivisionError as exc:
            raise ToolError("Division by zero") from exc
        except (ValueError, OverflowError, TypeError) as exc:
            raise ToolError(f"Math error: {exc}") from exc
        return repr(result)
