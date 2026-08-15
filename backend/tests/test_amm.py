from __future__ import annotations

from decimal import Decimal

import pytest

from app.sources.amm import ConstantProductPool, quote_exact_input, spot_price


def test_constant_product_quote_is_decimal_safe() -> None:
    pool = ConstantProductPool(
        token0_id="USDC",
        token1_id="JEWEL",
        reserve0=Decimal("1000"),
        reserve1=Decimal("5000"),
        fee_bps=30,
    )

    assert spot_price(pool, base_token_id="JEWEL") == Decimal("0.2")
    assert quote_exact_input(pool, input_token_id="JEWEL", input_amount=Decimal("5")) == Decimal(
        "0.9960069810399032164931563231"
    )


def test_constant_product_quote_rejects_unknown_token() -> None:
    pool = ConstantProductPool(
        token0_id="USDC",
        token1_id="JEWEL",
        reserve0=Decimal("1000"),
        reserve1=Decimal("5000"),
        fee_bps=30,
    )

    with pytest.raises(ValueError, match="not in the pool"):
        quote_exact_input(pool, input_token_id="CRYSTAL", input_amount=Decimal("1"))
