"""Decimal policy for financial calculations."""

from __future__ import annotations

from decimal import Context, Decimal, FloatOperation, InvalidOperation, ROUND_HALF_EVEN

FINANCIAL_DECIMAL_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)
FINANCIAL_DECIMAL_CONTEXT.traps[FloatOperation] = True


def decimal_from_text(value: str) -> Decimal:
    """Create a finite Decimal from text under the project financial context."""
    if not isinstance(value, str):
        raise TypeError("Decimal values must be provided as text")
    try:
        decimal = FINANCIAL_DECIMAL_CONTEXT.create_decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid decimal text: {value}") from exc
    if not decimal.is_finite():
        raise ValueError("Decimal value must be finite")
    return decimal


def decimal_from_int(value: int) -> Decimal:
    """Create a Decimal from an integer without passing binary floats around."""
    if not isinstance(value, int):
        raise TypeError("Integer decimal conversion requires an int")
    return FINANCIAL_DECIMAL_CONTEXT.create_decimal(value)
