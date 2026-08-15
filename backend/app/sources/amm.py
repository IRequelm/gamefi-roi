"""Provider-neutral AMM helpers for constant-product pools."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.engine.decimal_context import FINANCIAL_DECIMAL_CONTEXT, decimal_from_int


@dataclass(frozen=True)
class ConstantProductPool:
    token0_id: str
    token1_id: str
    reserve0: Decimal
    reserve1: Decimal
    fee_bps: int

    def __post_init__(self) -> None:
        if self.reserve0 <= Decimal("0") or self.reserve1 <= Decimal("0"):
            raise ValueError("AMM reserves must be positive")
        if self.fee_bps < 0 or self.fee_bps >= 10_000:
            raise ValueError("fee_bps must be between 0 and 9999")


def quote_exact_input(pool: ConstantProductPool, *, input_token_id: str, input_amount: Decimal) -> Decimal:
    if not isinstance(input_amount, Decimal):
        raise TypeError("input_amount must be Decimal")
    if input_amount <= Decimal("0"):
        raise ValueError("input_amount must be positive")

    if input_token_id == pool.token0_id:
        input_reserve = pool.reserve0
        output_reserve = pool.reserve1
    elif input_token_id == pool.token1_id:
        input_reserve = pool.reserve1
        output_reserve = pool.reserve0
    else:
        raise ValueError(f"input token {input_token_id} is not in the pool")

    fee_multiplier = FINANCIAL_DECIMAL_CONTEXT.divide(
        decimal_from_int(10_000 - pool.fee_bps),
        decimal_from_int(10_000),
    )
    amount_in_after_fee = FINANCIAL_DECIMAL_CONTEXT.multiply(input_amount, fee_multiplier)
    numerator = FINANCIAL_DECIMAL_CONTEXT.multiply(amount_in_after_fee, output_reserve)
    denominator = FINANCIAL_DECIMAL_CONTEXT.add(input_reserve, amount_in_after_fee)
    return FINANCIAL_DECIMAL_CONTEXT.divide(numerator, denominator)


def spot_price(pool: ConstantProductPool, *, base_token_id: str) -> Decimal:
    if base_token_id == pool.token0_id:
        return FINANCIAL_DECIMAL_CONTEXT.divide(pool.reserve1, pool.reserve0)
    if base_token_id == pool.token1_id:
        return FINANCIAL_DECIMAL_CONTEXT.divide(pool.reserve0, pool.reserve1)
    raise ValueError(f"base token {base_token_id} is not in the pool")
