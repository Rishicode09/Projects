"""Command line interface.

    python3 -m portfolio_accountant.cli demo
    python3 -m portfolio_accountant.cli close --config portfolio.json
    python3 -m portfolio_accountant.cli calendar --config portfolio.json
    python3 -m portfolio_accountant.cli verify-rates

Every command that produces figures prints the verification banner first. That
is deliberate and it is not configurable: a number presented without its
provenance is the failure mode this whole package exists to prevent.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

from . import __version__
from .audit import run_review
from .classify import classify, load_rules, unclassified_value
from .compliance import build_calendar, record_retention_note
from .config import CONFIG_DIR, ConfigError, Jurisdiction, load_jurisdiction, load_json
from .forensics import run_forensic_review
from .ingest import import_many
from .ledger import Ledger
from .model import EntityType, OwnershipBasis, Portfolio, Transaction
from .money import Money, total
from .planning import REFUSED, run_planning_review
from .posting import post_accrual, post_transactions
from .properties import PortfolioSummary, analyse_properties
from .statements import build_balance_sheet, build_profit_and_loss, build_tax_bridge
from .tax.cgt import Disposal, compute_cgt
from .tax.corporation_tax import CompanyProfits, compute_corporation_tax
from .tax.income_tax import IncomeSources, compute_income_tax
from .tax.vat import check_vat_registration, monthly_taxable_turnover

PACKAGE_ROOT = Path(__file__).resolve().parent.parent

# Income accounts that represent taxable supplies for VAT. Residential rent
# (4000) is an exempt supply and is deliberately absent: including it would
# push landlords over a threshold that does not apply to them.
TAXABLE_SUPPLY_ACCOUNTS = ["4010", "4020", "4100", "4110"]


# ---------------------------------------------------------------------------
# Banners
# ---------------------------------------------------------------------------


def verification_banner(jur: Jurisdiction) -> str:
    status = jur.raw.get("meta", {}).get("verification_status", "")
    stale = jur.staleness_warnings()
    lines = [
        "=" * 74,
        f"  {jur.name} -- {jur.tax_year}",
    ]
    if status == "UNVERIFIED_DRAFT" or stale:
        lines.extend(
            [
                "",
                "  RATES NOT VERIFIED.",
                f"  {len(stale)} parameter(s) have no recent human verification date.",
                "",
                "  Figures produced from this file are indicative only. Before any",
                "  of them informs a filing, a payment, a lender or a purchase:",
                "    1. check each rate against the current HMRC guidance,",
                "    2. set verified_on for that parameter in the config file,",
                "    3. re-run.",
                "",
                "  Tax rates change at Budgets and occasionally with retrospective",
                "  effect. A computation built on a stale rate is confidently wrong,",
                "  which is worse than no computation at all.",
            ]
        )
    else:
        lines.append(f"  Rates verified. {len(jur.parameters)} parameters loaded.")
    lines.append("=" * 74)
    return "\n".join(lines)


def scope_banner() -> str:
    return "\n".join(
        [
            "",
            "-" * 74,
            "WHAT THIS OUTPUT IS AND IS NOT",
            "",
            "  It is:     prepared workings, with every figure traceable to a source",
            "             document and every rate traceable to a config parameter.",
            "",
            "  It is not: a tax return, statutory accounts, an audit opinion, or",
            "             tax advice. Preparing and filing those are regulated acts",
            "             that require a qualified person who is accountable for",
            "             them. This output is the input to that person's work.",
            "",
            "  Before anything is filed, a named human must review the workings,",
            "  resolve every query raised, and take responsibility for the result.",
            "-" * 74,
        ]
    )


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def load_engagement(path: str) -> Dict:
    """Load the engagement config that describes one portfolio."""
    data = load_json(path)
    base = Path(path).resolve().parent

    def resolve(value: str) -> str:
        candidate = Path(value)
        return str(candidate if candidate.is_absolute() else base / candidate)

    for source in data.get("sources", []):
        source["path"] = resolve(source["path"])
    for key in ("rules_file", "chart_of_accounts"):
        if key in data:
            data[key] = resolve(data[key])
    return data


def build_portfolio(engagement: Dict) -> Portfolio:
    return Portfolio.from_dict(engagement)


# ---------------------------------------------------------------------------
# The pipeline
# ---------------------------------------------------------------------------


def run_close(engagement: Dict, out: List[str]) -> Dict:
    """Run the full period-close pipeline and collect the report sections."""
    jur = load_jurisdiction(engagement.get("jurisdiction", "uk_2025_26"))
    out.append(verification_banner(jur))

    start = _parse_date(engagement.get("period_start")) or jur.year_start
    end = _parse_date(engagement.get("period_end")) or jur.year_end
    period_label = f"{start} to {end}"

    portfolio = build_portfolio(engagement)

    # -- 1. Import ------------------------------------------------------
    out.append("\n1. IMPORT")
    result = import_many(engagement.get("sources", []))
    out.append(result.summary())
    portfolio.transactions = result.transactions

    # -- 2. Classify ----------------------------------------------------
    out.append("\n2. CLASSIFY")
    rules_path = engagement.get("rules_file")
    rules = load_rules(load_json(rules_path)["rules"]) if rules_path else []
    report = classify(portfolio.transactions, rules)
    out.append(report.summary())

    # -- 3. Post to the ledger -------------------------------------------
    out.append("\n3. LEDGER")
    ledger = Ledger()
    chart_path = engagement.get("chart_of_accounts") or str(
        CONFIG_DIR / "chart_of_accounts.json"
    )
    ledger.load_chart(load_json(chart_path)["accounts"])
    _post_opening_balances(ledger, engagement, start)
    journals = post_transactions(ledger, portfolio.transactions)
    difference = ledger.trial_balance_check()
    out.append(f"  {len(journals)} journals posted")
    out.append(f"  trial balance difference: {difference.quantize()}")
    out.append(f"  ledger integrity hash: {ledger.integrity_hash()[:24]}")

    sections: Dict[str, object] = {
        "jurisdiction": jur,
        "portfolio": portfolio,
        "ledger": ledger,
        "period": (start, end),
    }

    # -- 4. Statements per entity ----------------------------------------
    out.append("\n4. STATEMENTS")
    for entity in portfolio.entities.values():
        pl = build_profit_and_loss(ledger, entity.id, start, end)
        if pl.total_income.is_zero and pl.total_expenses.is_zero:
            continue
        out.append("")
        out.append(pl.render())
        out.append("")
        out.append(build_balance_sheet(ledger, entity.id, end, start).render())

    # -- 5. Property performance -----------------------------------------
    out.append("\n5. PROPERTY PERFORMANCE")
    performances = analyse_properties(portfolio, start, end)
    summary = PortfolioSummary(properties=performances, period_label=period_label)
    out.append(summary.render())
    sections["summary"] = summary

    # -- 6. Forensic review ----------------------------------------------
    out.append("\n6. FORENSIC REVIEW")
    related = []
    for entity in portfolio.entities.values():
        related.extend(entity.related_parties)
    forensic = run_forensic_review(
        portfolio.transactions,
        related_names=related,
        period_end=end,
        period_label=period_label,
    )
    out.append(forensic.render())

    # -- 7. Controls review ----------------------------------------------
    out.append("\n7. CONTROLS REVIEW")
    revenue = summary.gross_rent + Money(engagement.get("trading_income", 0))
    review = run_review(
        ledger=ledger,
        transactions=portfolio.transactions,
        jur=jur,
        entity_id="",
        period=period_label,
        revenue=revenue,
        statement_balances={
            k: Money(v) for k, v in (engagement.get("statement_balances") or {}).items()
        },
        prepared_by=engagement.get("prepared_by", "portfolio-accountant (automated)"),
        reviewed_by=engagement.get("reviewed_by", ""),
    )
    out.append(review.render())

    # -- 8. Tax computations ---------------------------------------------
    out.append("\n8. TAX COMPUTATIONS")
    computations = _run_tax(engagement, portfolio, summary, jur, out)
    sections["computations"] = computations

    # -- 9. Planning ------------------------------------------------------
    out.append("\n9. PLANNING REVIEW")
    personal = engagement.get("personal_income", {})
    ani = Money(personal.get("adjusted_net_income", 0)) if personal else None
    planning = run_planning_review(
        summary=summary,
        jur=jur,
        entity_id=engagement.get("primary_entity", ""),
        adjusted_net_income=ani,
        trading_income=Money(engagement.get("trading_income", 0)),
    )
    out.append(planning.render())

    # -- 10. Calendar -----------------------------------------------------
    out.append("\n10. COMPLIANCE CALENDAR")
    calendar = build_calendar(portfolio, jur, as_at=end)
    out.append(calendar.render())
    out.append("")
    out.append(record_retention_note(jur))

    # -- 11. Gate ---------------------------------------------------------
    out.append("\n11. READINESS")
    out.append(_readiness_gate(review, report, portfolio.transactions, forensic))
    out.append(scope_banner())
    return sections


def _post_opening_balances(ledger: Ledger, engagement: Dict, start: date) -> None:
    """Post brought-forward balances as at the day before the period starts.

    Without these the balance sheet starts from nothing and shows an overdrawn
    bank account that does not exist. Opening balances should come from the
    prior period's closing figures, and should have been reviewed as part of
    that period rather than re-derived here.
    """
    from datetime import timedelta

    openings = engagement.get("opening_balances") or {}
    for entity_id, accounts in openings.items():
        for account, amount_raw in accounts.items():
            amount = Money(amount_raw)
            if amount.is_zero:
                continue
            post_accrual(
                ledger,
                start - timedelta(days=1),
                f"Opening balance brought forward for {account} at {start}",
                debit_account=account if not amount.is_negative else "3000",
                credit_account="3000" if not amount.is_negative else account,
                amount=abs(amount),
                entity_id=entity_id,
                prepared_by="opening balance (from prior period)",
                source_ref="engagement.opening_balances",
            )


def _run_tax(
    engagement: Dict,
    portfolio: Portfolio,
    summary: PortfolioSummary,
    jur: Jurisdiction,
    out: List[str],
) -> List:
    computations = []

    personal = engagement.get("personal_income")
    if personal:
        # Only personally-held property belongs in a personal computation.
        # Company-held property is taxed under corporation tax and must not be
        # double-counted here.
        personal_summary = summary.filtered(
            [OwnershipBasis.PERSONAL, OwnershipBasis.JOINT]
        )
        sources = IncomeSources(
            employment=Money(personal.get("employment", 0)),
            self_employment_profit=Money(personal.get("self_employment_profit", 0)),
            property_profit=personal_summary.net_operating_income,
            savings_interest=Money(personal.get("savings_interest", 0)),
            dividends=Money(personal.get("dividends", 0)),
            residential_finance_costs=personal_summary.restricted_finance_costs,
            finance_costs_brought_forward=Money(
                personal.get("finance_costs_brought_forward", 0)
            ),
            gross_pension_contributions=Money(
                personal.get("gross_pension_contributions", 0)
            ),
            paye_deducted=Money(personal.get("paye_deducted", 0)),
        )
        comp = compute_income_tax(
            sources, jur, entity_id=engagement.get("primary_entity", "")
        )
        out.append("")
        out.append(comp.render())
        computations.append(comp)

    for company in engagement.get("companies", []):
        profits = CompanyProfits(
            trading_profit=Money(company.get("trading_profit", 0)),
            property_profit=Money(company.get("property_profit", 0)),
            depreciation_addback=Money(company.get("depreciation", 0)),
            capital_allowances=Money(company.get("capital_allowances", 0)),
            associated_companies=int(company.get("associated_companies", 0)),
            period_end=_parse_date(company.get("period_end")),
        )
        comp = compute_corporation_tax(profits, jur, entity_id=company.get("id", ""))
        out.append("")
        out.append(comp.render())
        computations.append(comp)

    # VAT registration monitoring, per entity. Residential rent is exempt and
    # is excluded from the threshold test; commercial rent and serviced
    # accommodation are not.
    for entity in portfolio.entities.values():
        entity_txns = portfolio.transactions_for(entity_id=entity.id)
        months = monthly_taxable_turnover(entity_txns, TAXABLE_SUPPLY_ACCOUNTS)
        if not months:
            continue
        comp = check_vat_registration(
            months, jur, entity_id=entity.id, already_registered=entity.vat_registered
        )
        out.append("")
        out.append(comp.render())
        computations.append(comp)

    disposals = [
        Disposal.from_property(p)
        for p in portfolio.properties.values()
        if p.is_disposed
    ]
    if disposals:
        taxable_income = Money(
            (engagement.get("personal_income") or {}).get("taxable_income_for_cgt", 0)
        )
        comp = compute_cgt(
            disposals, jur, taxable_income, entity_id=engagement.get("primary_entity", "")
        )
        out.append("")
        out.append(comp.render())
        computations.append(comp)

    return computations


def _readiness_gate(review, classification, transactions, forensic) -> str:
    """State plainly whether this work is fit to be used."""
    blockers = []

    for check in review.failures:
        if check.severity == "high":
            blockers.append(f"control failure: {check.name} - {check.detail}")

    unclassified = unclassified_value(transactions)
    if unclassified > review.materiality:
        blockers.append(
            f"{unclassified} unclassified, above materiality of {review.materiality}"
        )

    high_findings = [f for f in forensic.findings if f.severity == "high"]
    for finding in high_findings:
        blockers.append(f"unexplained indicator: {finding.summary}")

    if not blockers:
        return (
            "  No blocking issues found by the automated checks.\n"
            "  A named person must still review the workings and take "
            "responsibility before anything is filed. The absence of a detected "
            "problem is not the presence of assurance."
        )

    lines = [
        f"  NOT READY. {len(blockers)} blocking issue(s):",
        "",
    ]
    lines.extend(f"    - {b}" for b in blockers)
    lines.append("")
    lines.append(
        "  Resolve each of these before these figures are used for a filing, a "
        "lender, or a purchase decision. Do not work around them."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_close(args) -> int:
    engagement = load_engagement(args.config)
    out: List[str] = []
    try:
        run_close(engagement, out)
    finally:
        text = "\n".join(out)
        print(text)
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
            print(f"\nWritten to {args.output}")
    return 0


def cmd_calendar(args) -> int:
    engagement = load_engagement(args.config)
    jur = load_jurisdiction(engagement.get("jurisdiction", "uk_2025_26"))
    portfolio = build_portfolio(engagement)
    calendar = build_calendar(portfolio, jur)
    print(verification_banner(jur))
    print(calendar.render(within_days=args.days))
    print()
    print(record_retention_note(jur))
    return 0


def cmd_verify_rates(args) -> int:
    jur = load_jurisdiction(args.jurisdiction)
    print(verification_banner(jur))
    print()
    print(f"Parameters requiring verification ({len(jur.staleness_warnings())}):")
    for warning in jur.staleness_warnings():
        print(f"  - {warning}")
    print()
    print("Deliberately NOT implemented (each is referred to a qualified adviser):")
    for item in jur.unsupported:
        print(f"  - {item}")
    print()
    print(f"  {jur.raw.get('unsupported_note', '')}")
    return 0


def cmd_refusals(args) -> int:
    print("This package will not assist with any of the following:")
    print()
    for item in REFUSED:
        print(f"  - {item}")
    print()
    print(
        "These are not preferences. Each describes conduct that is a criminal\n"
        "offence, professional misconduct, or both. Where a past problem is\n"
        "discovered in the records, the response is disclosure through the\n"
        "proper route, which carries materially lower penalties than discovery."
    )
    return 0


def cmd_demo(args) -> int:
    config_path = PACKAGE_ROOT / "data" / "example" / "engagement.json"
    if not config_path.exists():
        print(f"example engagement not found at {config_path}", file=sys.stderr)
        return 1
    engagement = load_engagement(str(config_path))
    out: List[str] = []
    run_close(engagement, out)
    text = "\n".join(out)
    print(text)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="portfolio-accountant",
        description="Prepared workings for a mixed property and business portfolio. "
                    "Not a filing tool and not tax advice.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_close = subparsers.add_parser(
        "close", help="run the full period-close pipeline"
    )
    p_close.add_argument("--config", required=True, help="engagement JSON file")
    p_close.add_argument("--output", help="also write the report to this file")
    p_close.set_defaults(func=cmd_close)

    p_cal = subparsers.add_parser("calendar", help="show the compliance calendar")
    p_cal.add_argument("--config", required=True)
    p_cal.add_argument("--days", type=int, default=365)
    p_cal.set_defaults(func=cmd_calendar)

    p_ver = subparsers.add_parser(
        "verify-rates", help="show which tax parameters still need human verification"
    )
    p_ver.add_argument("--jurisdiction", default="uk_2025_26")
    p_ver.set_defaults(func=cmd_verify_rates)

    p_ref = subparsers.add_parser(
        "refusals", help="show what this package will not do"
    )
    p_ref.set_defaults(func=cmd_refusals)

    p_demo = subparsers.add_parser("demo", help="run against the bundled example data")
    p_demo.add_argument("--output")
    p_demo.set_defaults(func=cmd_demo)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
