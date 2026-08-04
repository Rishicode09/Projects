"""Stamp Duty Land Tax on acquisitions (England & Northern Ireland).

SDLT is charged in slices, not at a single rate on the whole price. The
surcharges stack: a non-resident company buying a second dwelling can face the
standard rates plus 5% plus 2%, or a 17% flat rate, depending on facts the
purchaser controls.

Three points worth knowing before any purchase:

* The 14-day filing window runs from the *effective date*, normally
  completion. It is short and the penalty is automatic.
* The higher rates for additional dwellings can be refunded if a previous main
  residence sells within three years -- but only if a claim is made.
* Multiple Dwellings Relief was abolished for transactions from 1 June 2024.
  Anyone still recommending it on a current purchase is working from stale
  material.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Optional

from ..config import Jurisdiction
from ..money import Money
from .base import Computation


@dataclass
class Acquisition:
    """A land transaction."""

    description: str
    price: Money
    effective_date: Optional[date] = None
    is_residential: bool = True
    is_additional_dwelling: bool = False
    buyer_is_company: bool = False
    buyer_is_non_resident: bool = False
    is_first_time_buyer: bool = False
    replacing_main_residence: bool = False
    is_mixed_use: bool = False


def compute_sdlt(
    acq: Acquisition, jur: Jurisdiction, entity_id: str = ""
) -> Computation:
    """Compute SDLT on a single acquisition, showing every slice."""
    comp = Computation(
        title=f"SDLT computation: {acq.description}",
        entity_id=entity_id,
        period=str(acq.effective_date) if acq.effective_date else jur.tax_year,
    )
    comp.step("Chargeable consideration", result=acq.price)

    if acq.effective_date:
        comp.warn(
            "SDLT depends on the rates in force at the effective date "
            f"({acq.effective_date}), usually completion rather than exchange. "
            "Confirm the loaded rate table covers that date."
        )

    # -- Non-residential and mixed use ------------------------------------
    if not acq.is_residential or acq.is_mixed_use:
        comp.uses("sdlt.non_residential_bands")
        bands = jur.bands("sdlt.non_residential_bands")
        tax = _charge_bands(acq.price, bands, comp)
        if acq.is_mixed_use:
            comp.refer(
                "Mixed-use treatment claimed. HMRC challenges weak mixed-use claims "
                "hard, and a failed claim brings interest and penalties on top of "
                "the difference. The non-residential element must be genuine, "
                "substantial and evidenced at the effective date - not created for "
                "the purpose of the claim."
            )
        comp.totals = {"sdlt": tax.quantize(), "total": tax.quantize()}
        _add_filing_note(comp, jur, acq)
        return comp

    # -- Corporate flat rate ----------------------------------------------
    if acq.buyer_is_company:
        comp.uses("sdlt.corporate_flat_rate", "sdlt.corporate_flat_rate_threshold")
        threshold = jur.money("sdlt.corporate_flat_rate_threshold")
        if acq.price > threshold:
            flat_rate = jur.decimal("sdlt.corporate_flat_rate")
            flat_tax = acq.price * flat_rate
            comp.step(
                "Flat rate for a non-natural person",
                amount=acq.price,
                rate=flat_rate,
                result=flat_tax,
                note=f"Applies to a single dwelling above {threshold} bought by a "
                     "company, UNLESS a relief applies and is claimed.",
            )
            comp.refer(
                "A property rental business relief from the flat rate is available "
                "where the dwelling is acquired for a genuine qualifying letting "
                "business. It must be claimed on the return, and it is clawed back "
                "if the conditions fail within three years. Have an adviser confirm "
                "eligibility before completion - the difference here is large."
            )
            comp.warn(
                "ATED may also apply annually to a company-held dwelling above the "
                "value threshold. ATED is not computed by this engine."
            )
            comp.totals = {"sdlt": flat_tax.quantize(), "total": flat_tax.quantize()}
            _add_filing_note(comp, jur, acq)
            return comp
        comp.step(
            "Corporate purchase below the flat rate threshold",
            note="Standard rates apply, but the higher rates for additional "
                 "dwellings apply from the first pound for a company.",
        )

    # -- Standard residential ---------------------------------------------
    comp.uses("sdlt.residential_standard_bands")
    bands = list(jur.bands("sdlt.residential_standard_bands"))

    # First-time buyer relief.
    if acq.is_first_time_buyer and not acq.is_additional_dwelling and not acq.buyer_is_company:
        comp.uses(
            "sdlt.first_time_buyer_relief.nil_band",
            "sdlt.first_time_buyer_relief.max_price",
        )
        max_price = jur.money("sdlt.first_time_buyer_relief.max_price")
        if acq.price <= max_price:
            bands = [
                {
                    "upper": jur.value("sdlt.first_time_buyer_relief.nil_band"),
                    "rate": "0.00",
                },
                {
                    "upper": jur.value("sdlt.first_time_buyer_relief.second_band_upper"),
                    "rate": jur.value("sdlt.first_time_buyer_relief.second_band_rate"),
                },
            ]
            comp.step(
                "First-time buyer relief applied",
                note="Every purchaser must be a first-time buyer. If one is not, "
                     "no relief is available at all.",
            )
        else:
            comp.step(
                "First-time buyer relief not available",
                note=f"Price exceeds {max_price}; relief is withdrawn entirely "
                     "rather than tapered.",
            )

    # Additional dwelling surcharge, added to every band including the nil band.
    surcharge = Decimal("0")
    surcharge_labels: List[str] = []
    if acq.is_additional_dwelling or acq.buyer_is_company:
        comp.uses("sdlt.additional_dwelling_surcharge")
        surcharge += jur.decimal("sdlt.additional_dwelling_surcharge")
        surcharge_labels.append("additional dwelling")
    if acq.buyer_is_non_resident:
        comp.uses("sdlt.non_resident_surcharge")
        surcharge += jur.decimal("sdlt.non_resident_surcharge")
        surcharge_labels.append("non-resident")

    if surcharge > 0:
        comp.step(
            f"Surcharge added to every band ({', '.join(surcharge_labels)})",
            rate=surcharge,
            note="The surcharge applies from the first pound, including what would "
                 "otherwise be the nil rate band.",
        )
        bands = [
            {"upper": b["upper"], "rate": str(Decimal(str(b["rate"])) + surcharge)}
            for b in bands
        ]

    tax = _charge_bands(acq.price, bands, comp)
    comp.totals = {"sdlt": tax.quantize(), "total": tax.quantize()}

    if acq.replacing_main_residence and acq.is_additional_dwelling:
        comp.refer(
            "Higher rates have been charged, but this purchase replaces a main "
            "residence. If the previous main residence is sold within three years, "
            "the surcharge is refundable - the claim must be made within 12 months "
            "of the sale or of the SDLT filing date, whichever is later. Diarise it: "
            "unclaimed refunds are common and the money is simply lost."
        )

    _add_filing_note(comp, jur, acq)
    if jur.has("sdlt.mdr_abolished") and jur.value("sdlt.mdr_abolished"):
        comp.warn(
            "Multiple Dwellings Relief was abolished for transactions from "
            "1 June 2024 and has not been applied."
        )
    comp.assume(
        "England or Northern Ireland. Scotland charges LBTT and Wales charges LTT, "
        "with different bands and surcharges; neither is computed here."
    )
    return comp


def _charge_bands(price: Money, bands: List[dict], comp: Computation) -> Money:
    """Charge a price across slice bands, showing each slice."""
    tax = Money.zero()
    lower = Money.zero()
    for band in bands:
        upper_raw = band.get("upper")
        rate = Decimal(str(band["rate"]))
        upper = Money(upper_raw) if upper_raw is not None else None
        if upper is not None and price <= lower:
            break
        top = price if (upper is None or price < upper) else upper
        slice_amount = top - lower
        if slice_amount > 0:
            slice_tax = slice_amount * rate
            label = (
                f"  {lower} to {upper}" if upper is not None else f"  above {lower}"
            )
            comp.step(label, amount=slice_amount, rate=rate, result=slice_tax)
            tax = tax + slice_tax
        if upper is None:
            break
        lower = upper
    comp.step("SDLT payable", result=tax.quantize())
    return tax


def _add_filing_note(comp: Computation, jur: Jurisdiction, acq: Acquisition) -> None:
    comp.uses("sdlt.filing_days")
    days = jur.value("sdlt.filing_days")
    note = f"The SDLT return and payment are due within {days} days of the effective date."
    if acq.effective_date:
        from datetime import timedelta

        note += f" On this transaction that is {acq.effective_date + timedelta(days=int(days))}."
    comp.warn(note)
    comp.step(
        "Memo: SDLT is capital expenditure",
        note="It is not deductible against rental profit. It forms part of the CGT "
             "base cost, so it must be recorded against the property now to be "
             "usable on an eventual disposal.",
    )
