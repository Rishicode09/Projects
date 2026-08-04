---
name: portfolio-close
description: Run a period close, year-end, or tax review for a property and business portfolio - importing bank data, classifying transactions, producing statements and tax computations, and reviewing controls. Use when asked to "do the books", "close the year", "work out my tax", "check the accounts", or investigate discrepancies in a portfolio's records.
---

# Portfolio close

The order below is not arbitrary. Each step depends on the one before it, and
the most common way to produce confidently wrong accounts is to compute tax on
a ledger that has not been reconciled.

Work in `PortfolioAccountant/`.

## 1. Establish the facts before touching the data

- **Which jurisdiction?** The config ships England & NI. Scotland and Wales
  have different income tax and different land transaction taxes. Ask; do not
  infer from an address that might be a correspondence address.
- **Which entities, and who owns what?** Personally-held, jointly-held and
  company-held property are taxed under entirely different regimes. Getting
  this wrong invalidates everything downstream.
- **What period?** A tax year (6 April to 5 April) and a company accounting
  period rarely coincide. Both may be needed.
- **What is already filed?** Do not restate a period that has been reported
  without saying so explicitly.

## 2. Import

```bash
python3 -m portfolio_accountant.cli close --config <engagement.json>
```

Check the import summary before reading anything else. Duplicates skipped is
normal when statements overlap. Errors are not — read every one. A row that
failed to import is missing from the accounts entirely, and nothing downstream
will tell you it is gone.

## 3. Classify, and resist the urge to finish

Coverage below about 95% means the rules need work. But **do not write rules to
empty the suspense queue.** The queue is the actual work: each item is a
decision only a person with knowledge of the business can make. Sweeping
"TRANSFER TO J SMITH" into repairs produces books that look complete and are
wrong, and the error is then invisible.

Take the queue back to the client grouped by pattern, not line by line. "These
seven £800 monthly payments to Premier Maintenance — what are they, and is
there an invoice?" is one question that clears seven items.

Rules are ordered, first match wins. **Specific before general.**

## 4. Ledger and statements

Trial balance must be nil. The balance sheet must balance. If either fails,
stop and fix it — every figure after this point inherits the error.

Opening balances come from last period's closing figures. If they are absent
the bank shows an overdraft that does not exist.

## 5. Property performance

This is where the management accounting earns its keep. Look for:

- **Return on equity per property.** The portfolio average hides the one
  returning 2%. Say so plainly when a property is not working.
- **Missing rent months.** Void, arrears, or income banked elsewhere — these
  look identical in the ledger and need completely different responses.
- **Cost ratios above about 45% of rent** — usually capital items misposted as
  repairs.
- **The Section 24 gap.** For personally-held geared residential property, tax
  is charged on profit *before* finance costs. Show the cash profit and the
  taxable profit side by side. This is the number people most need to see and
  least expect.

## 6. Forensic review

Every finding is an indicator, never a conclusion. Present each as a question
with the evidence attached, and include the innocent explanations — they are
usually the right ones. The value is in directing attention, not in being
suspicious.

If something is not explained after being asked, escalate to a qualified
forensic accountant. Do not investigate further yourself and do not confront
anyone. If money laundering is suspected, note that regulated professionals
have reporting obligations with criminal consequences for tipping off, and that
this is a point to take advice on immediately rather than to handle informally.

## 7. Controls review

Read the failures, not the passes. Two matter most:

- **Bank reconciliation** — the only check tied to a document nobody in the
  business produced.
- **Segregation of duties** — it will fail until a named person reviews. That
  failure is correct and must not be worked around. Do not review your own
  preparation and call it assured.

## 8. Tax computations

Only now, on a ledger that reconciles. Present the workings, not just the
total. State which parameters are unverified.

Watch for:
- Personal computations must use only personally-held property.
- Company property goes through corporation tax, never the personal
  computation.
- Property income does not attract Class 4 NIC unless it is genuinely a trade.
- Anything in the `unsupported` list is referred out, not estimated.

## 9. Planning

Statutory reliefs the facts actually engage, each with its conditions and its
risks. Never a scheme. If it only works when nobody looks at the whole picture,
it does not go in the report.

Be honest about incorporation: it is the obvious answer to Section 24 and
frequently the wrong one once SDLT at company rates, CGT on the transfer, and
refinancing costs are counted.

## 10. Calendar and readiness

Surface anything due within 60 days. The 60-day CGT return and 14-day SDLT
return are missed constantly because people assume they follow the annual
cycle.

The readiness gate blocks on unresolved control failures and material
unclassified items. When it says NOT READY, report that as the headline. Do not
bury it under a tidy set of statements — the whole purpose of the gate is to
stop plausible-looking output being relied on.

## Closing the loop

Finish by stating:
1. the headline numbers and what they mean for the decision at hand;
2. the open queries, with the specific question for each;
3. what a qualified person must do before anything is filed.

Then lock the period once it has been reported, so corrections are posted as
reversals rather than silently rewriting history.
