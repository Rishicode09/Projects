"""Tests for import, classification, forensics, controls and the whole pipeline.

The behaviours asserted here are the safety properties -- the ones that stop
the tool producing something that looks finished but is wrong. A duplicate
import that silently doubles income, a rule that quietly sweeps unknown
payments into a category, a review that passes itself: each of those is a
plausible failure that would be invisible in the output.
"""

import csv
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from portfolio_accountant.audit import (
    calculate_materiality,
    check_bank_reconciliation,
    check_segregation_of_duties,
    select_sample,
)
from portfolio_accountant.classify import (
    AWAITING_EVIDENCE,
    SUSPENSE_ACCOUNT,
    Rule,
    classify,
    load_rules,
)
from portfolio_accountant.config import load_jurisdiction
from portfolio_accountant.forensics import (
    duplicate_payments,
    missing_evidence,
    related_party_flows,
    run_forensic_review,
)
from portfolio_accountant.ingest import import_csv, import_many
from portfolio_accountant.model import Transaction
from portfolio_accountant.money import Money

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def txn(when, description, amount, **kwargs):
    return Transaction(
        date=when,
        description=description,
        amount=Money(amount),
        entity_id=kwargs.pop("entity_id", "E1"),
        **kwargs,
    )


class TestIngest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "bank.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, rows, header=("date", "description", "amount")):
        with self.path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)

    def test_imports_signed_amount_column(self):
        self._write([["2025-05-01", "RENT FLAT-01", "1250.00"],
                     ["2025-05-02", "AGENT FEE", "-125.00"]])
        result = import_csv(str(self.path), entity_id="E1")
        self.assertEqual(result.imported_count, 2)
        self.assertEqual(result.transactions[0].amount, Money("1250.00"))
        self.assertTrue(result.transactions[1].amount.is_negative)

    def test_imports_paid_in_paid_out_columns(self):
        with self.path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Date", "Narrative", "Paid In", "Paid Out"])
            writer.writerow(["01/05/2025", "RENT", "1250.00", ""])
            writer.writerow(["02/05/2025", "AGENT FEE", "", "125.00"])
        result = import_csv(str(self.path), entity_id="E1")
        self.assertEqual(result.imported_count, 2)
        self.assertEqual(result.transactions[0].amount, Money("1250.00"))
        self.assertEqual(result.transactions[1].amount, Money("-125.00"))

    def test_reimporting_the_same_file_does_not_double_count(self):
        """The failure this prevents overstates income and the tax on it."""
        self._write([["2025-05-01", "RENT FLAT-01", "1250.00"]])
        first = import_csv(str(self.path), entity_id="E1")
        seen = {t.fingerprint() for t in first.transactions}
        second = import_csv(str(self.path), entity_id="E1", known_fingerprints=seen)
        self.assertEqual(second.imported_count, 0)
        self.assertEqual(len(second.duplicates), 1)

    def test_overlapping_statements_import_once(self):
        self._write([["2025-05-01", "RENT", "1250.00"],
                     ["2025-05-02", "FEE", "-125.00"]])
        other = Path(self.tmp.name) / "bank2.csv"
        with other.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "description", "amount"])
            writer.writerow(["2025-05-02", "FEE", "-125.00"])  # overlaps
            writer.writerow(["2025-05-03", "REPAIR", "-300.00"])
        combined = import_many(
            [
                {"path": str(self.path), "entity_id": "E1"},
                {"path": str(other), "entity_id": "E1"},
            ]
        )
        self.assertEqual(combined.imported_count, 3)
        self.assertEqual(len(combined.duplicates), 1)

    def test_a_genuine_repeat_payment_is_distinguishable(self):
        """Two real payments of the same amount on the same day must both import."""
        self._write([["2025-05-01", "REPAIR INV-100", "-500.00"],
                     ["2025-05-01", "REPAIR INV-101", "-500.00"]])
        result = import_csv(str(self.path), entity_id="E1")
        self.assertEqual(result.imported_count, 2)

    def test_bad_rows_are_reported_not_skipped_silently(self):
        self._write([["2025-05-01", "GOOD", "100.00"],
                     ["not-a-date", "BAD", "100.00"],
                     ["2025-05-03", "", "100.00"]])
        result = import_csv(str(self.path), entity_id="E1")
        self.assertEqual(result.imported_count, 1)
        self.assertEqual(len(result.errors), 2)

    def test_unrecognised_header_fails_loudly(self):
        self._write([["x"]], header=("alpha", "beta", "gamma"))
        result = import_csv(str(self.path), entity_id="E1")
        self.assertEqual(result.imported_count, 0)
        self.assertTrue(result.errors)


class TestClassification(unittest.TestCase):
    def test_first_matching_rule_wins_so_order_matters(self):
        """The exact bug the example rules file warns about.

        'COMMERCIAL MORTGAGE INTEREST' also contains 'MORTGAGE INTEREST'. With
        the general rule first, commercial interest is posted to the restricted
        s.24 account and the tax is overstated.
        """
        specific_first = [
            Rule(id="commercial", account="5110",
                 description_pattern="COMMERCIAL MORTGAGE INTEREST"),
            Rule(id="residential", account="5100",
                 description_pattern="MORTGAGE INTEREST"),
        ]
        t = txn(date(2025, 5, 1), "COMMERCIAL MORTGAGE INTEREST COMM-04", "-1450")
        classify([t], specific_first)
        self.assertEqual(t.category, "5110")
        self.assertEqual(t.classification_rule, "commercial")

        t2 = txn(date(2025, 5, 1), "COMMERCIAL MORTGAGE INTEREST COMM-04", "-1450")
        classify([t2], list(reversed(specific_first)))
        self.assertEqual(t2.category, "5100", "general rule first mis-classifies")

    def test_unmatched_goes_to_suspense_not_a_guess(self):
        t = txn(date(2025, 5, 1), "TRANSFER TO J SMITH", "-800")
        report = classify([t], [Rule(id="rent", account="4000",
                                     description_pattern="^RENT")])
        self.assertEqual(t.category, SUSPENSE_ACCOUNT)
        self.assertEqual(t.confidence, "unclassified")
        self.assertEqual(len(report.unclassified), 1)

    def test_rule_requiring_evidence_holds_the_item(self):
        rules = [Rule(id="repairs", account="5000",
                      description_pattern="REPAIR", requires_evidence=True)]
        with_doc = txn(date(2025, 5, 1), "REPAIR BOILER", "-300",
                       document_ref="INV-1")
        without_doc = txn(date(2025, 5, 2), "REPAIR ROOF", "-300")
        report = classify([with_doc, without_doc], rules)
        self.assertEqual(with_doc.category, "5000")
        self.assertEqual(without_doc.category, AWAITING_EVIDENCE)
        self.assertEqual(len(report.awaiting_evidence), 1)

    def test_direction_filter(self):
        rules = [Rule(id="rent-in", account="4000",
                      description_pattern="RENT", direction="in")]
        payment = txn(date(2025, 5, 1), "RENT REFUND", "-500")
        classify([payment], rules)
        self.assertEqual(payment.category, SUSPENSE_ACCOUNT)

    def test_duplicate_rule_ids_are_refused(self):
        with self.assertRaises(ValueError):
            load_rules([
                {"id": "R1", "account": "4000"},
                {"id": "R1", "account": "5000"},
            ])

    def test_work_queue_groups_similar_narratives(self):
        transactions = [
            txn(date(2025, 5, i + 1), f"CARD PAYMENT 1234 REF {9000 + i} ACME", "-50")
            for i in range(4)
        ]
        report = classify(transactions, [])
        self.assertEqual(
            len(report.unmatched_descriptions), 1,
            "card references and digits should not fragment the queue",
        )


class TestForensics(unittest.TestCase):
    def test_finds_a_genuine_duplicate(self):
        transactions = [
            txn(date(2025, 9, 14), "ROOF REPAIR", "-2450",
                counterparty="NORTHGATE", document_ref="INV-8871"),
            txn(date(2025, 9, 27), "ROOF REPAIR", "-2450",
                counterparty="NORTHGATE", document_ref="INV-8871"),
        ]
        finding = duplicate_payments(transactions)
        self.assertIsNotNone(finding)
        self.assertEqual(finding.value_at_risk, Money("2450"))
        self.assertIn("BOTH quote document", finding.evidence[0])

    def test_ignores_a_recurring_monthly_series(self):
        """Without this the test fires on every standing order and is useless."""
        transactions = [
            txn(date(2025, m, 7), "MANAGEMENT FEE", "-125", counterparty="AGENT")
            for m in range(1, 13)
        ]
        self.assertIsNone(duplicate_payments(transactions))

    def test_ignores_same_day_payments_with_different_invoices(self):
        """Three safety certificates for three flats are not a duplicate."""
        transactions = [
            txn(date(2025, 7, 18), "GAS SAFETY", "-92",
                counterparty="CITY GAS", document_ref=f"CP12-{i}")
            for i in range(3)
        ]
        self.assertIsNone(duplicate_payments(transactions))

    def test_missing_evidence_ignores_small_items(self):
        transactions = [txn(date(2025, 5, 1), "COFFEE", "-4.50")]
        self.assertIsNone(missing_evidence(transactions))

    def test_related_party_detection(self):
        transactions = [
            txn(date(2025, 5, 1), "PAYMENT", "-1500", counterparty="R MEHRA"),
            txn(date(2025, 5, 2), "RENT", "1200", counterparty="A TENANT"),
        ]
        finding = related_party_flows(transactions, ["R MEHRA"])
        self.assertIsNotNone(finding)
        self.assertEqual(len(finding.evidence), 1)

    def test_no_related_names_means_no_finding(self):
        transactions = [txn(date(2025, 5, 1), "PAYMENT", "-1500")]
        self.assertIsNone(related_party_flows(transactions, []))

    def test_benford_is_skipped_on_a_small_sample(self):
        """A confident answer from 20 data points would be worse than none."""
        transactions = [
            txn(date(2025, 5, 1), f"ITEM {i}", f"-{100 + i * 37}") for i in range(20)
        ]
        report = run_forensic_review(transactions)
        benford = [f for f in report.findings if f.test == "Benford first-digit"]
        self.assertEqual(len(benford), 1)
        self.assertEqual(benford[0].severity, "info")
        self.assertIn("not run", benford[0].summary)

    def test_findings_are_phrased_as_questions_not_conclusions(self):
        transactions = [
            txn(date(2025, 9, 14), "ROOF", "-2450", counterparty="N", document_ref="I1"),
            txn(date(2025, 9, 20), "ROOF", "-2450", counterparty="N", document_ref="I1"),
        ]
        report = run_forensic_review(transactions)
        for finding in report.findings:
            self.assertTrue(
                finding.explanation_sought,
                f"{finding.test} must ask for an explanation, not assert a conclusion",
            )

    def test_evidence_hash_is_stable_and_data_dependent(self):
        a = [txn(date(2025, 5, 1), "ONE", "-100")]
        b = [txn(date(2025, 5, 1), "ONE", "-100")]
        c = [txn(date(2025, 5, 1), "ONE", "-101")]
        self.assertEqual(
            run_forensic_review(a).evidence_hash, run_forensic_review(b).evidence_hash
        )
        self.assertNotEqual(
            run_forensic_review(a).evidence_hash, run_forensic_review(c).evidence_hash
        )


class TestAuditControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jur = load_jurisdiction("uk_2025_26")

    def test_self_review_fails(self):
        check = check_segregation_of_duties("agent", "agent")
        self.assertFalse(check.passed)
        self.assertIn("self-review", check.risk_if_failed)

    def test_missing_reviewer_fails(self):
        self.assertFalse(check_segregation_of_duties("agent", "").passed)

    def test_distinct_reviewer_passes(self):
        self.assertTrue(check_segregation_of_duties("agent", "A Person").passed)

    def test_bank_reconciliation_must_be_exact(self):
        self.assertTrue(
            check_bank_reconciliation(Money("1000"), Money("1000")).passed
        )
        self.assertFalse(
            check_bank_reconciliation(Money("1000"), Money("999.99")).passed,
            "a penny out is still out",
        )

    def test_materiality_scales_with_revenue_and_risk(self):
        normal, _ = calculate_materiality(Money("100000"), self.jur)
        elevated, _ = calculate_materiality(
            Money("100000"), self.jur, risk_factor=Decimal("0.5")
        )
        self.assertEqual(normal, Money("500.00"))
        self.assertLess(elevated.amount, normal.amount)

    def test_sample_includes_everything_above_materiality(self):
        transactions = [
            txn(date(2025, 5, 1), "BIG", "-5000"),
            txn(date(2025, 5, 2), "SMALL", "-10"),
        ]
        sample = select_sample(transactions, Money("1000"), sample_size=1)
        self.assertIn(transactions[0], sample)

    def test_sample_is_reproducible(self):
        transactions = [
            txn(date(2025, 5, 1) + timedelta(days=i), f"ITEM {i}", f"-{10 + i}")
            for i in range(50)
        ]
        first = select_sample(transactions, Money("1000"), 10, seed="abc")
        second = select_sample(transactions, Money("1000"), 10, seed="abc")
        self.assertEqual(
            [t.fingerprint() for t in first], [t.fingerprint() for t in second]
        )
        different = select_sample(transactions, Money("1000"), 10, seed="xyz")
        self.assertNotEqual(
            [t.fingerprint() for t in first], [t.fingerprint() for t in different]
        )


class TestEndToEnd(unittest.TestCase):
    """The demo must run and must refuse to declare itself ready."""

    @classmethod
    def setUpClass(cls):
        result = subprocess.run(
            [sys.executable, "-m", "portfolio_accountant.cli", "demo"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=180,
        )
        cls.result = result
        cls.output = result.stdout

    def test_demo_runs_cleanly(self):
        self.assertEqual(self.result.returncode, 0, self.result.stderr[-2000:])

    def test_unverified_rates_are_announced_first(self):
        self.assertIn("RATES NOT VERIFIED", self.output[:1500])

    def test_ledger_balances(self):
        self.assertIn("trial balance difference: £0.00", self.output)

    def test_statements_balance(self):
        self.assertNotIn("DOES NOT BALANCE", self.output)

    def test_section_24_gap_is_shown(self):
        self.assertIn("Section 24 gap", self.output)

    def test_planted_duplicate_is_found(self):
        self.assertIn("NORTHGATE ROOFING 2450.00", self.output)

    def test_unclassified_items_are_not_guessed(self):
        self.assertIn("TRANSFER MAINTENANCE SERVICES", self.output)
        self.assertIn("SUSPENSE", self.output)

    def test_it_refuses_to_declare_itself_ready(self):
        self.assertIn("NOT READY", self.output)
        self.assertIn("Segregation of duties", self.output)

    def test_scope_limitation_is_stated(self):
        self.assertIn("It is not:", self.output)
        self.assertIn("a named human must review", self.output.lower())


if __name__ == "__main__":
    unittest.main()
