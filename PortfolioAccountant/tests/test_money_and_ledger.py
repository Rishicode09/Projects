"""Tests for the arithmetic and bookkeeping foundations.

These matter more than they look. If money arithmetic drifts by a penny or a
journal can be posted unbalanced, every figure built on top is unreliable and
no amount of care further up compensates.
"""

import unittest
from datetime import date
from decimal import Decimal

from portfolio_accountant.ledger import (
    Account,
    AccountType,
    Journal,
    Ledger,
    LedgerLocked,
    Posting,
    UnbalancedJournal,
)
from portfolio_accountant.money import CurrencyMismatch, Money, total


class TestMoney(unittest.TestCase):
    def test_no_float_drift(self):
        """The canonical float failure must not occur."""
        result = Money("0.1") + Money("0.2")
        self.assertEqual(result.amount, Decimal("0.3"))
        self.assertEqual(str(result), "£0.30")

    def test_floats_are_rejected(self):
        with self.assertRaises(TypeError):
            Money(0.1 + 0.2)

    def test_parses_bank_export_formats(self):
        self.assertEqual(Money.parse("1,234.56"), Money("1234.56"))
        self.assertEqual(Money.parse("£1,234.56"), Money("1234.56"))
        self.assertEqual(Money.parse("(1,234.56)"), Money("-1234.56"))
        self.assertEqual(Money.parse("500.00 DR"), Money("-500.00"))
        self.assertEqual(Money.parse("500.00 CR"), Money("500.00"))
        self.assertEqual(Money.parse(""), Money.zero())

    def test_currency_mismatch_is_refused(self):
        with self.assertRaises(CurrencyMismatch):
            Money("100", "GBP") + Money("100", "EUR")

    def test_rounding_is_half_up_not_bankers(self):
        # Python's default round() would give 2 here; accounting convention is 3.
        self.assertEqual(Money("2.5").quantize().amount, Decimal("2.50"))
        self.assertEqual(Money("0.125").quantize().amount, Decimal("0.13"))
        self.assertEqual(Money("0.135").quantize().amount, Decimal("0.14"))

    def test_round_down_to_pound_only_when_asked(self):
        self.assertEqual(Money("99.99").round_down_to_pound().amount, Decimal("99"))
        self.assertEqual(Money("99.99").quantize().amount, Decimal("99.99"))

    def test_apportionment_is_exact(self):
        rent = Money("1000")
        third = rent.apportion(1, 3)
        self.assertEqual((third * 3).quantize(), Money("1000.00"))

    def test_total_of_empty_is_zero(self):
        self.assertEqual(total([]), Money.zero())


class TestLedger(unittest.TestCase):
    def setUp(self):
        self.ledger = Ledger()
        for code, name, kind in (
            ("1000", "Bank", AccountType.ASSET),
            ("4000", "Rent", AccountType.INCOME),
            ("5000", "Repairs", AccountType.EXPENSE),
        ):
            self.ledger.add_account(Account(code=code, name=name, type=kind))

    def _rent_journal(self, amount="1000", when=date(2025, 5, 1)):
        return Journal(
            date=when,
            narrative=f"Rent received {when}",
            postings=[
                Posting(account="1000", debit=Money(amount)),
                Posting(account="4000", credit=Money(amount)),
            ],
            entity_id="IND-001",
        )

    def test_unbalanced_journal_is_refused(self):
        with self.assertRaises(UnbalancedJournal) as ctx:
            Journal(
                date=date(2025, 5, 1),
                narrative="Broken",
                postings=[
                    Posting(account="1000", debit=Money("1000")),
                    Posting(account="4000", credit=Money("900")),
                ],
            )
        self.assertIn("does not balance", str(ctx.exception))

    def test_posting_cannot_be_both_debit_and_credit(self):
        with self.assertRaises(ValueError):
            Posting(account="1000", debit=Money("10"), credit=Money("10"))

    def test_negative_posting_is_refused(self):
        with self.assertRaises(ValueError):
            Posting(account="1000", debit=Money("-10"))

    def test_unknown_account_is_refused(self):
        journal = Journal(
            date=date(2025, 5, 1),
            narrative="To a made-up account",
            postings=[
                Posting(account="1000", debit=Money("100")),
                Posting(account="9999", credit=Money("100")),
            ],
        )
        with self.assertRaises(KeyError):
            self.ledger.post(journal)

    def test_duplicate_journal_is_refused(self):
        """Re-importing the same statement must not double-count income."""
        self.ledger.post(self._rent_journal())
        with self.assertRaises(ValueError) as ctx:
            self.ledger.post(self._rent_journal())
        self.assertIn("already been posted", str(ctx.exception))

    def test_trial_balance_is_zero(self):
        self.ledger.post(self._rent_journal())
        self.ledger.post(self._rent_journal(when=date(2025, 6, 1)))
        self.assertTrue(self.ledger.trial_balance_check().is_zero)

    def test_balances_are_natural_signed(self):
        self.ledger.post(self._rent_journal("1500"))
        self.assertEqual(self.ledger.balance("1000"), Money("1500"))
        # Income is credit-natural, so a credit balance reads positive.
        self.assertEqual(self.ledger.balance("4000"), Money("1500"))

    def test_closed_period_rejects_posting(self):
        self.ledger.close_period(date(2025, 4, 6), date(2026, 4, 5), "reported")
        with self.assertRaises(LedgerLocked) as ctx:
            self.ledger.post(self._rent_journal())
        self.assertIn("closed period", str(ctx.exception))

    def test_correction_is_a_reversal_not_a_deletion(self):
        original = self.ledger.post(self._rent_journal("1000"))
        self.ledger.reverse(original.id, "posted to the wrong property")

        # Both entries survive; the net effect is nil.
        self.assertEqual(len(self.ledger.journals), 2)
        self.assertEqual(self.ledger.balance("1000"), Money.zero())
        trail = self.ledger.audit_trail()
        self.assertEqual(len(trail), 4)
        self.assertTrue(any(row["reverses"] == original.id for row in trail))

    def test_integrity_hash_changes_when_ledger_changes(self):
        before = self.ledger.integrity_hash()
        self.ledger.post(self._rent_journal())
        self.assertNotEqual(before, self.ledger.integrity_hash())

    def test_integrity_hash_is_order_independent(self):
        """The same journals in a different sequence hash identically."""
        self.ledger.post(self._rent_journal(when=date(2025, 5, 1)))
        self.ledger.post(self._rent_journal(when=date(2025, 6, 1)))
        first = self.ledger.integrity_hash()

        other = Ledger()
        for code, name, kind in (
            ("1000", "Bank", AccountType.ASSET),
            ("4000", "Rent", AccountType.INCOME),
        ):
            other.add_account(Account(code=code, name=name, type=kind))
        other.post(self._rent_journal(when=date(2025, 6, 1)))
        other.post(self._rent_journal(when=date(2025, 5, 1)))
        self.assertEqual(first, other.integrity_hash())


if __name__ == "__main__":
    unittest.main()
