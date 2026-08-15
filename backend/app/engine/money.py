"""Decimal-safe money value object."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.engine.decimal_context import FINANCIAL_DECIMAL_CONTEXT, decimal_from_text
from app.engine.errors import EngineInputError


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise EngineInputError("Money.amount must be a Decimal")
        if not self.amount.is_finite():
            raise EngineInputError("Money.amount must be finite")
        if not isinstance(self.currency, str) or not self.currency.strip():
            raise EngineInputError("Money.currency is required")
        object.__setattr__(self, "currency", self.currency.upper())

    @classmethod
    def from_text(cls, amount: str, currency: str) -> "Money":
        return cls(amount=decimal_from_text(amount), currency=currency)

    @classmethod
    def zero(cls, currency: str) -> "Money":
        return cls.from_text("0", currency)

    def ensure_currency(self, currency: str, field_name: str) -> None:
        if self.currency != currency.upper():
            raise EngineInputError(f"{field_name} currency {self.currency} does not match {currency.upper()}")

    def require_non_negative(self, field_name: str) -> None:
        if self.amount < Decimal("0"):
            raise EngineInputError(f"{field_name} must be non-negative")

    def __add__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(FINANCIAL_DECIMAL_CONTEXT.add(self.amount, other.amount), self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(FINANCIAL_DECIMAL_CONTEXT.subtract(self.amount, other.amount), self.currency)

    def multiply(self, multiplier: Decimal) -> "Money":
        if not isinstance(multiplier, Decimal):
            raise EngineInputError("Money multipliers must be Decimal values")
        return Money(FINANCIAL_DECIMAL_CONTEXT.multiply(self.amount, multiplier), self.currency)

    def ratio_to(self, denominator: "Money") -> Decimal:
        self._require_same_currency(denominator)
        if denominator.amount == Decimal("0"):
            raise EngineInputError("Cannot divide by zero-valued money")
        return FINANCIAL_DECIMAL_CONTEXT.divide(self.amount, denominator.amount)

    def _require_same_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise EngineInputError(f"Currency mismatch: {self.currency} != {other.currency}")
