"""Shared result types for every tax computation.

A computation is only useful if a reviewer can follow it. Every engine in this
package returns a :class:`Computation` whose ``steps`` reproduce the working a
qualified preparer would show on paper -- so that a reviewer can disagree with
a specific line rather than with a black box.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Union

from ..money import Money


@dataclass
class Step:
    """One line of the working."""

    label: str
    amount: Optional[Money] = None
    rate: Optional[Decimal] = None
    result: Optional[Money] = None
    note: str = ""

    def render(self) -> str:
        parts = [self.label]
        if self.amount is not None:
            parts.append(str(self.amount))
        if self.rate is not None:
            parts.append(f"@ {self.rate * 100:.4g}%")
        if self.result is not None:
            parts.append(f"= {self.result}")
        line = "  ".join(parts)
        if self.note:
            line += f"\n      note: {self.note}"
        return line


@dataclass
class Computation:
    """The output of a tax engine: a figure, its workings, and its caveats."""

    title: str
    entity_id: str = ""
    period: str = ""
    steps: List[Step] = field(default_factory=list)
    totals: Dict[str, Money] = field(default_factory=dict)
    parameters_used: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    referrals: List[str] = field(default_factory=list)
    carried_forward: Dict[str, Money] = field(default_factory=dict)

    # -- building --------------------------------------------------------
    def step(
        self,
        label: str,
        amount: Optional[Money] = None,
        rate: Optional[Union[str, Decimal]] = None,
        result: Optional[Money] = None,
        note: str = "",
    ) -> "Computation":
        self.steps.append(
            Step(
                label=label,
                amount=amount,
                rate=Decimal(str(rate)) if rate is not None else None,
                result=result,
                note=note,
            )
        )
        return self

    def uses(self, *keys: str) -> "Computation":
        for key in keys:
            if key not in self.parameters_used:
                self.parameters_used.append(key)
        return self

    def assume(self, text: str) -> "Computation":
        self.assumptions.append(text)
        return self

    def warn(self, text: str) -> "Computation":
        self.warnings.append(text)
        return self

    def refer(self, text: str) -> "Computation":
        """Flag something that needs a qualified human, not more computation."""
        self.referrals.append(text)
        return self

    # -- output ----------------------------------------------------------
    @property
    def total(self) -> Money:
        return self.totals.get("total", Money.zero())

    def render(self) -> str:
        lines = [self.title]
        if self.entity_id or self.period:
            lines.append(f"  {self.entity_id}  {self.period}".rstrip())
        lines.append("-" * max(48, len(self.title)))
        for step in self.steps:
            lines.append("  " + step.render())
        if self.totals:
            lines.append("-" * 48)
            for key, value in self.totals.items():
                lines.append(f"  {key.replace('_', ' ').upper():<38} {value}")
        if self.carried_forward:
            lines.append("")
            lines.append("  Carried forward:")
            for key, value in self.carried_forward.items():
                lines.append(f"    {key.replace('_', ' ')}: {value}")
        if self.assumptions:
            lines.append("")
            lines.append("  Assumptions (check each one):")
            lines.extend(f"    - {a}" for a in self.assumptions)
        if self.warnings:
            lines.append("")
            lines.append("  Warnings:")
            lines.extend(f"    ! {w}" for w in self.warnings)
        if self.referrals:
            lines.append("")
            lines.append("  Refer to a qualified adviser:")
            lines.extend(f"    > {r}" for r in self.referrals)
        return "\n".join(lines)

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "entity_id": self.entity_id,
            "period": self.period,
            "steps": [
                {
                    "label": s.label,
                    "amount": str(s.amount.quantize().amount) if s.amount else None,
                    "rate": str(s.rate) if s.rate is not None else None,
                    "result": str(s.result.quantize().amount) if s.result else None,
                    "note": s.note,
                }
                for s in self.steps
            ],
            "totals": {k: str(v.quantize().amount) for k, v in self.totals.items()},
            "carried_forward": {
                k: str(v.quantize().amount) for k, v in self.carried_forward.items()
            },
            "parameters_used": self.parameters_used,
            "assumptions": self.assumptions,
            "warnings": self.warnings,
            "referrals": self.referrals,
        }


@dataclass
class BandSlice:
    """A portion of income falling in one rate band."""

    band: str
    amount: Money
    rate: Decimal

    @property
    def tax(self) -> Money:
        return self.amount * self.rate


def slice_into_bands(
    amount: Money,
    bands: List[Dict],
    already_used: Money,
    extension: Optional[Money] = None,
) -> List[BandSlice]:
    """Allocate ``amount`` across cumulative rate bands.

    ``already_used`` is income already stacked below this slice (the UK stacks
    non-savings, then savings, then dividends). ``extension`` widens the
    non-additional bands, as gross pension contributions and Gift Aid do.
    """
    extension = extension or Money.zero()
    slices: List[BandSlice] = []
    remaining = amount
    cursor = already_used

    for band in bands:
        if remaining <= 0:
            break
        upper_raw = band.get("upper")
        rate = Decimal(str(band["rate"]))
        if upper_raw is None:
            slices.append(BandSlice(band["name"], remaining, rate))
            remaining = Money.zero()
            break
        # The additional-rate threshold is also extended by relief at source.
        upper = Money(upper_raw) + extension
        headroom = upper - cursor
        if headroom <= 0:
            continue
        take = remaining if remaining < headroom else headroom
        slices.append(BandSlice(band["name"], take, rate))
        remaining = remaining - take
        cursor = cursor + take

    if remaining > 0:  # pragma: no cover - open-ended band should absorb this
        slices.append(BandSlice(bands[-1]["name"], remaining, Decimal(str(bands[-1]["rate"]))))
    return slices


def apply_nil_rate(slices: List[BandSlice], allowance: Money) -> List[BandSlice]:
    """Re-rate the first ``allowance`` of income to 0%, keeping band position.

    This is how the dividend allowance and the personal savings allowance
    actually work: they are nil-rate bands, so the income still occupies band
    space and still pushes other income upwards. Treating them as deductions
    understates the liability -- a common error in spreadsheet models.
    """
    if allowance <= 0:
        return slices
    out: List[BandSlice] = []
    remaining = allowance
    for sl in slices:
        if remaining <= 0:
            out.append(sl)
            continue
        covered = sl.amount if sl.amount < remaining else remaining
        if covered > 0:
            out.append(BandSlice(f"{sl.band} (nil rate)", covered, Decimal("0")))
        leftover = sl.amount - covered
        if leftover > 0:
            out.append(BandSlice(sl.band, leftover, sl.rate))
        remaining = remaining - covered
    return out
