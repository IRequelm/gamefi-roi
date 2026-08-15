from __future__ import annotations

from decimal import Decimal

from app.engine.decimal_context import FINANCIAL_DECIMAL_CONTEXT, decimal_from_text


def test_decimal_from_text_uses_decimal_not_float() -> None:
    value = decimal_from_text("0.10")

    assert value == Decimal("0.10")


def test_financial_decimal_context_uses_bankers_rounding() -> None:
    value = FINANCIAL_DECIMAL_CONTEXT.create_decimal("2.5").quantize(Decimal("1"))

    assert value == Decimal("2")
