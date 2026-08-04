"""Tax computation tests, checked against figures worked by hand.

Each test states the manual working in its docstring. That is the point: a tax
engine whose expected values were produced by the engine itself proves only
that it is self-consistent. These numbers were computed independently and can
be re-derived by a reader with the rates in front of them.

If a rate in the config changes, some of these will fail. That is correct
behaviour -- a rate change SHOULD break the tests and force someone to re-derive
the expected figures rather than silently accept new output.
"""

import unittest
from datetime import date
from decimal import Decimal

from portfolio_accountant.config import ConfigError, load_jurisdiction
from portfolio_accountant.money import Money
from portfolio_accountant.tax.cgt import Disposal, compute_cgt
from portfolio_accountant.tax.corporation_tax import CompanyProfits, compute_corporation_tax
from portfolio_accountant.tax.income_tax import IncomeSources, compute_income_tax
from portfolio_accountant.tax.sdlt import Acquisition, compute_sdlt


class TaxTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jur = load_jurisdiction("uk_2025_26")

    def assertMoney(self, actual, expected, msg=""):
        self.assertEqual(actual.quantize(), Money(expected).quantize(), msg)


class TestIncomeTax(TaxTestCase):
    def test_basic_rate_employee(self):
        """£50,000 employment.

        Taxable = 50,000 - 12,570 = 37,430, all within the 37,700 basic band.
        Tax = 37,430 x 20% = 7,486.
        """
        comp = compute_income_tax(IncomeSources(employment=Money(50000)), self.jur)
        self.assertMoney(comp.totals["income_tax"], "7486.00")

    def test_higher_rate_with_section_24_restriction(self):
        """Employment 50,000; property profit 20,000; finance costs 10,000.

        Non-savings = 70,000; taxable = 57,430.
        Basic:  37,700 x 20% =  7,540.00
        Higher: 19,730 x 40% =  7,892.00
        Before reducers      = 15,432.00
        s.24 reducer = min(10,000, 20,000, 57,430) x 20% = 2,000.00
        Liability            = 13,432.00
        """
        comp = compute_income_tax(
            IncomeSources(
                employment=Money(50000),
                property_profit=Money(20000),
                residential_finance_costs=Money(10000),
            ),
            self.jur,
        )
        self.assertMoney(comp.totals["income_tax"], "13432.00")

    def test_section_24_is_not_a_deduction(self):
        """The restriction must cost a higher-rate taxpayer real money.

        Were finance costs deductible, profit would be 10,000 lower and the tax
        4,000 lower. The reducer only returns 2,000, so the restriction costs
        2,000 -- 20% of the interest. This test would pass trivially if the
        engine wrongly treated interest as an expense, so it asserts the gap.
        """
        restricted = compute_income_tax(
            IncomeSources(
                employment=Money(50000),
                property_profit=Money(20000),
                residential_finance_costs=Money(10000),
            ),
            self.jur,
        )
        # The same taxpayer if interest were deductible (company or commercial).
        deductible = compute_income_tax(
            IncomeSources(employment=Money(50000), property_profit=Money(10000)),
            self.jur,
        )
        gap = restricted.totals["income_tax"] - deductible.totals["income_tax"]
        self.assertMoney(gap, "2000.00")

    def test_finance_costs_capped_by_property_profit(self):
        """Finance costs of 30,000 against profits of only 5,000.

        The reducer is capped at 5,000 x 20% = 1,000 and the unrelieved
        25,000 is carried forward, not lost.
        """
        comp = compute_income_tax(
            IncomeSources(
                employment=Money(60000),
                property_profit=Money(5000),
                residential_finance_costs=Money(30000),
            ),
            self.jur,
        )
        self.assertMoney(comp.carried_forward["unrelieved_finance_costs"], "25000.00")

    def test_personal_allowance_taper(self):
        """£110,000 employment.

        Allowance = 12,570 - (10,000 / 2) = 7,570. Taxable = 102,430.
        Basic:  37,700 x 20% =  7,540.00
        Higher: 64,730 x 40% = 25,892.00
        Total                = 33,432.00
        """
        comp = compute_income_tax(IncomeSources(employment=Money(110000)), self.jur)
        self.assertMoney(comp.totals["income_tax"], "33432.00")

    def test_pension_contribution_reverses_the_taper(self):
        """A 10,000 gross contribution at 110,000 restores the full allowance."""
        comp = compute_income_tax(
            IncomeSources(
                employment=Money(110000), gross_pension_contributions=Money(10000)
            ),
            self.jur,
        )
        # PA restored in full, and the basic rate band extended by 10,000.
        # Taxable = 110,000 - 12,570 = 97,430.
        # Basic:  47,700 x 20% =  9,540.00
        # Higher: 49,730 x 40% = 19,892.00  => 29,432.00
        self.assertMoney(comp.totals["income_tax"], "29432.00")

    def test_dividend_allowance_is_a_nil_rate_band(self):
        """Employment 12,570 (exactly the allowance) plus 3,000 dividends.

        Dividends: 500 at 0%, then 2,500 x 8.75% = 218.75.
        """
        comp = compute_income_tax(
            IncomeSources(employment=Money(12570), dividends=Money(3000)), self.jur
        )
        self.assertMoney(comp.totals["income_tax"], "218.75")

    def test_class_4_nic_on_trade_not_on_property(self):
        """Property income must not attract Class 4 NIC."""
        property_only = compute_income_tax(
            IncomeSources(property_profit=Money(40000)), self.jur
        )
        self.assertMoney(property_only.totals["class_4_nic"], "0.00")

        # The same profit from a trade does attract it:
        # (40,000 - 12,570) x 6% = 1,645.80
        trade = compute_income_tax(
            IncomeSources(self_employment_profit=Money(40000)), self.jur
        )
        self.assertMoney(trade.totals["class_4_nic"], "1645.80")

    def test_reducer_cannot_create_a_repayment(self):
        comp = compute_income_tax(
            IncomeSources(
                property_profit=Money(13000), residential_finance_costs=Money(12000)
            ),
            self.jur,
        )
        self.assertFalse(comp.totals["income_tax"].is_negative)

    def test_scotland_is_refused_rather_than_approximated(self):
        with self.assertRaises(ConfigError) as ctx:
            compute_income_tax(
                IncomeSources(employment=Money(50000)), self.jur, country="Scotland"
            )
        self.assertIn("not implemented", str(ctx.exception))

    def test_missing_finance_costs_raises_a_query(self):
        comp = compute_income_tax(
            IncomeSources(employment=Money(50000), property_profit=Money(20000)),
            self.jur,
        )
        self.assertTrue(
            any("finance costs" in w for w in comp.warnings),
            "should query property profit with no finance costs",
        )


class TestCorporationTax(TaxTestCase):
    def test_small_profits_rate(self):
        """40,000 profit, below the 50,000 lower limit: 19% = 7,600."""
        comp = compute_corporation_tax(
            CompanyProfits(trading_profit=Money(40000)), self.jur
        )
        self.assertMoney(comp.totals["corporation_tax"], "7600.00")

    def test_main_rate(self):
        """300,000 profit, above the 250,000 upper limit: 25% = 75,000."""
        comp = compute_corporation_tax(
            CompanyProfits(trading_profit=Money(300000)), self.jur
        )
        self.assertMoney(comp.totals["corporation_tax"], "75000.00")

    def test_marginal_relief(self):
        """100,000 profit.

        Main rate: 100,000 x 25%              = 25,000.00
        Relief:    3/200 x (250,000 - 100,000) =  2,250.00
        Payable                                = 22,750.00  (22.75% effective)
        """
        comp = compute_corporation_tax(
            CompanyProfits(trading_profit=Money(100000)), self.jur
        )
        self.assertMoney(comp.totals["corporation_tax"], "22750.00")

    def test_associated_companies_divide_the_limits(self):
        """40,000 profit is below the limit alone, but not with three associates.

        Limits become 50,000/4 = 12,500 and 250,000/4 = 62,500, so the company
        falls into marginal relief instead of the small profits rate.
        """
        alone = compute_corporation_tax(
            CompanyProfits(trading_profit=Money(40000)), self.jur
        )
        with_associates = compute_corporation_tax(
            CompanyProfits(trading_profit=Money(40000), associated_companies=3),
            self.jur,
        )
        self.assertGreater(
            with_associates.totals["corporation_tax"].amount,
            alone.totals["corporation_tax"].amount,
        )
        # 40,000 x 25% - 3/200 x (62,500 - 40,000) = 10,000 - 337.50 = 9,662.50
        self.assertMoney(with_associates.totals["corporation_tax"], "9662.50")

    def test_depreciation_is_added_back(self):
        comp = compute_corporation_tax(
            CompanyProfits(
                trading_profit=Money(40000), depreciation_addback=Money(10000)
            ),
            self.jur,
        )
        # 50,000 taxable, exactly at the lower limit: 19% = 9,500
        self.assertMoney(comp.totals["corporation_tax"], "9500.00")

    def test_nil_profit_still_requires_a_return(self):
        comp = compute_corporation_tax(CompanyProfits(), self.jur)
        self.assertMoney(comp.totals["corporation_tax"], "0.00")
        self.assertTrue(any("nil return" in w for w in comp.warnings))


class TestSDLT(TaxTestCase):
    def test_standard_residential(self):
        """£300,000: 0 on the first 125,000; 2% on 125,000; 5% on 50,000.

        = 0 + 2,500 + 2,500 = 5,000.
        """
        comp = compute_sdlt(
            Acquisition(description="Home", price=Money(300000)), self.jur
        )
        self.assertMoney(comp.totals["sdlt"], "5000.00")

    def test_additional_dwelling_surcharge_applies_from_the_first_pound(self):
        """£300,000 second property, every band plus 5 points.

        125,000 x 5% = 6,250; 125,000 x 7% = 8,750; 50,000 x 10% = 5,000
        = 20,000.
        """
        comp = compute_sdlt(
            Acquisition(
                description="Buy to let",
                price=Money(300000),
                is_additional_dwelling=True,
            ),
            self.jur,
        )
        self.assertMoney(comp.totals["sdlt"], "20000.00")

    def test_first_time_buyer_relief(self):
        comp = compute_sdlt(
            Acquisition(
                description="First home",
                price=Money(300000),
                is_first_time_buyer=True,
            ),
            self.jur,
        )
        self.assertMoney(comp.totals["sdlt"], "0.00")

    def test_first_time_buyer_relief_is_a_cliff_edge(self):
        """Above 500,000 the relief is withdrawn entirely, not tapered."""
        comp = compute_sdlt(
            Acquisition(
                description="Expensive first home",
                price=Money(600000),
                is_first_time_buyer=True,
            ),
            self.jur,
        )
        # Standard rates: 2,500 + 33,750 = ... 125k@0 + 125k@2% (2,500)
        # + 350k@5% (17,500) = 20,000
        self.assertMoney(comp.totals["sdlt"], "20000.00")

    def test_company_purchase_uses_the_flat_rate(self):
        """£600,000 to a company: 17% flat = 102,000, unless relief is claimed."""
        comp = compute_sdlt(
            Acquisition(
                description="SPV purchase",
                price=Money(600000),
                buyer_is_company=True,
            ),
            self.jur,
        )
        self.assertMoney(comp.totals["sdlt"], "102000.00")
        self.assertTrue(
            any("rental business relief" in r for r in comp.referrals),
            "must flag the relief that avoids the flat rate",
        )

    def test_non_residential_rates(self):
        """£300,000 commercial: 150k@0 + 100k@2% + 50k@5% = 2,000 + 2,500 = 4,500."""
        comp = compute_sdlt(
            Acquisition(
                description="Unit", price=Money(300000), is_residential=False
            ),
            self.jur,
        )
        self.assertMoney(comp.totals["sdlt"], "4500.00")

    def test_filing_deadline_is_flagged(self):
        comp = compute_sdlt(
            Acquisition(
                description="Home",
                price=Money(300000),
                effective_date=date(2025, 9, 1),
            ),
            self.jur,
        )
        self.assertTrue(any("2025-09-15" in w for w in comp.warnings))


class TestCGT(TaxTestCase):
    def test_residential_gain_for_a_higher_rate_taxpayer(self):
        """Gain 100,000, AEA 3,000, no basic band left: 97,000 x 24% = 23,280."""
        disposal = Disposal(
            description="Flat",
            disposal_date=date(2025, 8, 1),
            proceeds=Money(300000),
            acquisition_cost=Money(200000),
        )
        comp = compute_cgt(
            [disposal], self.jur, taxable_income=Money(45000)
        )
        self.assertMoney(comp.totals["capital_gains_tax"], "23280.00")

    def test_basic_rate_band_is_used_first(self):
        """Taxable income 20,000 leaves 17,700 of basic band.

        Gain 100,000 - 3,000 AEA = 97,000.
        17,700 x 18% =  3,186.00
        79,300 x 24% = 19,032.00
        Total        = 22,218.00
        """
        disposal = Disposal(
            description="Flat",
            disposal_date=date(2025, 8, 1),
            proceeds=Money(300000),
            acquisition_cost=Money(200000),
        )
        comp = compute_cgt([disposal], self.jur, taxable_income=Money(20000))
        self.assertMoney(comp.totals["capital_gains_tax"], "22218.00")

    def test_improvements_reduce_the_gain(self):
        """This is why improvement spending must be tracked from day one."""
        without = Disposal(
            description="Flat",
            disposal_date=date(2025, 8, 1),
            proceeds=Money(300000),
            acquisition_cost=Money(200000),
        )
        with_improvements = Disposal(
            description="Flat",
            disposal_date=date(2025, 8, 1),
            proceeds=Money(300000),
            acquisition_cost=Money(200000),
            improvement_costs=Money(25000),
        )
        a = compute_cgt([without], self.jur, Money(45000))
        b = compute_cgt([with_improvements], self.jur, Money(45000))
        # 25,000 less gain at 24% = 6,000 less tax.
        self.assertMoney(
            a.totals["capital_gains_tax"] - b.totals["capital_gains_tax"], "6000.00"
        )

    def test_sixty_day_deadline_is_warned(self):
        disposal = Disposal(
            description="Flat",
            disposal_date=date(2025, 8, 1),
            proceeds=Money(300000),
            acquisition_cost=Money(200000),
        )
        comp = compute_cgt([disposal], self.jur, Money(45000))
        self.assertTrue(
            any("2025-09-30" in w for w in comp.warnings),
            "the 60-day return deadline must be stated explicitly",
        )

    def test_gain_within_the_exemption_is_not_taxed(self):
        disposal = Disposal(
            description="Small gain",
            disposal_date=date(2025, 8, 1),
            proceeds=Money(102000),
            acquisition_cost=Money(100000),
        )
        comp = compute_cgt([disposal], self.jur, Money(45000))
        self.assertMoney(comp.totals["capital_gains_tax"], "0.00")
        self.assertTrue(
            any("60-day return" in w for w in comp.warnings),
            "nil tax does not mean nil reporting",
        )

    def test_losses_are_offset_before_the_exemption(self):
        gain = Disposal(
            description="Winner",
            disposal_date=date(2025, 8, 1),
            proceeds=Money(300000),
            acquisition_cost=Money(200000),
        )
        loss = Disposal(
            description="Loser",
            disposal_date=date(2025, 9, 1),
            proceeds=Money(80000),
            acquisition_cost=Money(100000),
        )
        comp = compute_cgt([gain, loss], self.jur, Money(45000))
        # (100,000 - 20,000 - 3,000) x 24% = 18,480
        self.assertMoney(comp.totals["capital_gains_tax"], "18480.00")


class TestVAT(TaxTestCase):
    def _months(self, amount, count=12, start_year=2025, start_month=4):
        from portfolio_accountant.tax.vat import TurnoverMonth

        out = []
        for i in range(count):
            year = start_year + (start_month - 1 + i) // 12
            month = (start_month - 1 + i) % 12 + 1
            out.append(TurnoverMonth(year, month, Money(amount)))
        return out

    def test_below_threshold_is_quiet(self):
        from portfolio_accountant.tax.vat import check_vat_registration

        comp = check_vat_registration(self._months(3000), self.jur)
        self.assertMoney(comp.totals["peak_rolling_turnover"], "36000.00")
        self.assertEqual(comp.warnings, [])

    def test_crossing_the_threshold_is_escalated(self):
        from portfolio_accountant.tax.vat import check_vat_registration

        comp = check_vat_registration(self._months(9000), self.jur)
        self.assertMoney(comp.totals["peak_rolling_turnover"], "108000.00")
        self.assertTrue(any("exceeded the registration threshold" in w
                            for w in comp.warnings))
        self.assertTrue(any("Late VAT registration" in r for r in comp.referrals))

    def test_already_registered_is_not_warned(self):
        from portfolio_accountant.tax.vat import check_vat_registration

        comp = check_vat_registration(
            self._months(9000), self.jur, already_registered=True
        )
        self.assertFalse(any("exceeded the registration threshold" in w
                             for w in comp.warnings))

    def test_residential_rent_is_excluded_from_taxable_supplies(self):
        """Exempt rent must not push a landlord over a threshold that
        does not apply to them."""
        from portfolio_accountant.model import Transaction
        from portfolio_accountant.tax.vat import monthly_taxable_turnover

        transactions = [
            Transaction(
                date=date(2025, m, 1),
                description="RENT",
                amount=Money(9000),
                entity_id="E1",
                category="4000",  # residential rent, an exempt supply
            )
            for m in range(1, 13)
        ]
        self.assertEqual(monthly_taxable_turnover(transactions, ["4010"]), [])


class TestConfigGovernance(TaxTestCase):
    def test_unverified_rates_are_reported_as_such(self):
        warnings = self.jur.staleness_warnings()
        self.assertTrue(
            warnings, "an unverified config must report every parameter as stale"
        )

    def test_unknown_parameter_raises_rather_than_defaulting(self):
        with self.assertRaises(ConfigError):
            self.jur.decimal("income_tax.invented_relief")

    def test_unsupported_areas_are_refused(self):
        for feature in ("inheritance_tax", "trusts", "vat_partial_exemption"):
            with self.assertRaises(ConfigError):
                self.jur.assert_supported(feature)

    def test_every_parameter_records_its_basis(self):
        """A rate with no source cannot be checked, so it should not exist."""
        undocumented = [
            key
            for key, param in self.jur.parameters.items()
            if not param.source and not param.legislation and not param.note
        ]
        self.assertEqual(undocumented, [], f"parameters lacking provenance: {undocumented}")


if __name__ == "__main__":
    unittest.main()
