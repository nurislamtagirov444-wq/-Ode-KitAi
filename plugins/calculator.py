"""Безопасный калькулятор для local_agent.py."""

from __future__ import annotations

import ast
import operator
from typing import Any

COMMAND = "calc"
HELP = "/calc выражение — посчитать безопасное математическое выражение, пример: /calc 2 + 2 * 10"

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_ALLOWED_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

MAX_ABS_VALUE = 10**12
MAX_POWER = 10


def _check_number(value: Any) -> float | int:
    if not isinstance(value, (int, float)):
        raise ValueError("разрешены только числа")
    if abs(value) > MAX_ABS_VALUE:
        raise ValueError(f"слишком большое число; максимум по модулю {MAX_ABS_VALUE}")
    return value


def _eval(node: ast.AST) -> float | int:
    if isinstance(node, ast.Expression):
        return _eval(node.body)

    if isinstance(node, ast.Constant):
        return _check_number(node.value)

    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARYOPS:
        value = _check_number(_eval(node.operand))
        return _check_number(_ALLOWED_UNARYOPS[type(node.op)](value))

    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        left = _check_number(_eval(node.left))
        right = _check_number(_eval(node.right))
        if isinstance(node.op, ast.Pow) and abs(right) > MAX_POWER:
            raise ValueError(f"степень слишком большая; максимум {MAX_POWER}")
        return _check_number(_ALLOWED_BINOPS[type(node.op)](left, right))

    raise ValueError("разрешены только числа и операции + - * / // % ** со скобками")


def handle(args: str, context: dict) -> str:  # noqa: ARG001 - единый интерфейс плагинов
    if not args:
        return "Использование: /calc 2 + 2 * 10"
    if len(args) > 200:
        return "Выражение слишком длинное."

    tree = ast.parse(args, mode="eval")
    return str(_eval(tree))
