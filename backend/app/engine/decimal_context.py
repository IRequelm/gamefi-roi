"""Decimal policy for future financial calculations."""

from __future__ import annotations

from decimal import Context, Decimal, FloatOperation, ROUND_HALF_EVEN

FINANCIAL_DECIMAL_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)
FINANCIAL_DECIMAL_CONTEXT.traps[FloatOperation] = True


def decimal_from_text(value: str) -> Decimal:
    """Create a Decimal from text under the project financial context."""
    return FINANCIAL_DECIMAL_CONTEXT.create_decimal(value)
