"""Exact money arithmetic.

Accounting code must never use floats. Every amount in this package is a
``Money`` built on :class:`decimal.Decimal`, rounded half-up to the minor unit
(pence) only at the point of presentation or statutory rounding -- never
silently mid-calculation.

Rounding policy: ROUND_HALF_UP. This matches HMRC/Companies House convention
for presented figures. Where a statute requires rounding *down* in the
taxpayer's favour (e.g. rounding tax down to the pound), the caller asks for it
explicitly via :func:`round_down_to_pound`.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Iterable, Union

Numeric = Union[int, str, Decimal, "Money"]

PENNY = Decimal("0.01")
POUND = Decimal("1")


class CurrencyMismatch(ValueError):
    """Raised when two amounts in different currencies are combined."""


def _to_decimal(value: Numeric) -> Decimal:
    if isinstance(value, Money):
        return value.amount
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):  # pragma: no cover - defensive
        raise TypeError(
            "float is not accepted in money arithmetic; pass a str or Decimal "
            f"(got {value!r})"
        )
    return Decimal(str(value).strip().replace(",", "").replace("£", ""))


@dataclass(frozen=True, order=False)
class Money:
    """An exact monetary amount in a single currency."""

    amount: Decimal
    currency: str = "GBP"

    def __init__(self, amount: Numeric = 0, currency: str = "GBP") -> None:
        if isinstance(amount, Money):
            currency = amount.currency
        object.__setattr__(self, "amount", _to_decimal(amount))
        object.__setattr__(self, "currency", currency.upper())

    # -- construction ----------------------------------------------------
    @classmethod
    def zero(cls, currency: str = "GBP") -> "Money":
        return cls(Decimal("0"), currency)

    @classmethod
    def parse(cls, raw: str, currency: str = "GBP") -> "Money":
        """Parse a human/bank-export string.

        Handles ``1,234.56``, ``£1234.56``, ``(1,234.56)`` for negatives and
        trailing ``CR``/``DR`` markers used by some bank exports.
        """
        text = str(raw).strip()
        if not text:
            return cls.zero(currency)
        negative = False
        if text.startswith("(") and text.endswith(")"):
            negative, text = True, text[1:-1]
        upper = text.upper()
        if upper.endswith("CR"):
            text = text[:-2].strip()
        elif upper.endswith("DR"):
            negative, text = True, text[:-2].strip()
        value = _to_decimal(text)
        return cls(-value if negative else value, currency)

    # -- guards ----------------------------------------------------------
    def _check(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise CurrencyMismatch(
                f"cannot combine {self.currency} with {other.currency}"
            )

    # -- arithmetic ------------------------------------------------------
    def __add__(self, other: Numeric) -> "Money":
        other = other if isinstance(other, Money) else Money(other, self.currency)
        self._check(other)
        return Money(self.amount + other.amount, self.currency)

    __radd__ = __add__

    def __sub__(self, other: Numeric) -> "Money":
        other = other if isinstance(other, Money) else Money(other, self.currency)
        self._check(other)
        return Money(self.amount - other.amount, self.currency)

    def __rsub__(self, other: Numeric) -> "Money":
        return Money(other, self.currency) - self

    def __mul__(self, factor: Union[int, str, Decimal]) -> "Money":
        return Money(self.amount * _to_decimal(factor), self.currency)

    __rmul__ = __mul__

    def __truediv__(self, divisor: Union[int, str, Decimal]) -> "Money":
        return Money(self.amount / _to_decimal(divisor), self.currency)

    def __neg__(self) -> "Money":
        return Money(-self.amount, self.currency)

    def __abs__(self) -> "Money":
        return Money(abs(self.amount), self.currency)

    # -- comparison ------------------------------------------------------
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Money):
            return self.currency == other.currency and self.amount == other.amount
        if isinstance(other, (int, str, Decimal)):
            return self.amount == _to_decimal(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.amount, self.currency))

    def _cmp_value(self, other: Numeric) -> Decimal:
        if isinstance(other, Money):
            self._check(other)
            return other.amount
        return _to_decimal(other)

    def __lt__(self, other: Numeric) -> bool:
        return self.amount < self._cmp_value(other)

    def __le__(self, other: Numeric) -> bool:
        return self.amount <= self._cmp_value(other)

    def __gt__(self, other: Numeric) -> bool:
        return self.amount > self._cmp_value(other)

    def __ge__(self, other: Numeric) -> bool:
        return self.amount >= self._cmp_value(other)

    # -- state -----------------------------------------------------------
    @property
    def is_zero(self) -> bool:
        return self.amount == 0

    @property
    def is_negative(self) -> bool:
        return self.amount < 0

    # -- rounding --------------------------------------------------------
    def quantize(self) -> "Money":
        """Round to the nearest penny (half-up)."""
        return Money(self.amount.quantize(PENNY, rounding=ROUND_HALF_UP), self.currency)

    def round_down_to_pound(self) -> "Money":
        """Round down to whole pounds.

        Used where legislation or HMRC practice rounds a *liability* down in
        the taxpayer's favour. Never apply this by default.
        """
        return Money(self.amount.quantize(POUND, rounding=ROUND_DOWN), self.currency)

    def apportion(self, numerator: Numeric, denominator: Numeric) -> "Money":
        """Pro-rate this amount, e.g. splitting a cost across days owned."""
        denom = _to_decimal(denominator)
        if denom == 0:
            raise ZeroDivisionError("apportionment denominator is zero")
        return Money(self.amount * _to_decimal(numerator) / denom, self.currency)

    # -- presentation ----------------------------------------------------
    def __str__(self) -> str:
        q = self.quantize().amount
        sign = "-" if q < 0 else ""
        symbol = {"GBP": "£", "EUR": "€", "USD": "$"}.get(self.currency, "")
        body = f"{abs(q):,.2f}"
        return f"{sign}{symbol}{body}" if symbol else f"{sign}{body} {self.currency}"

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Money('{self.quantize().amount}', '{self.currency}')"


def total(items: Iterable[Money], currency: str = "GBP") -> Money:
    """Sum an iterable of Money, returning zero for an empty iterable."""
    result = Money.zero(currency)
    for item in items:
        result = result + item
    return result


def percent_of(base: Money, rate: Union[str, Decimal]) -> Money:
    """Apply a rate expressed as a decimal fraction (``'0.20'`` for 20%)."""
    return base * _to_decimal(rate)
