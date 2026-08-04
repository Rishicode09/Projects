# Portfolio Accountant

An accounting agent for someone holding property and a business together —
covering the bookkeeping, the management reporting, the review, the tax
computations, and the forensic checks, in one place and with a visible trail
between them.

It is built on a single principle: **the computer does the arithmetic, a person
takes the decisions, and every figure traces back to a document.**

Nothing here files a return, signs off accounts, or gives tax advice. Those are
regulated acts requiring a qualified, accountable human. What this does is
prepare the work to the point where that person's time goes on judgement
instead of data entry.

## Why it is built this way

Most accounting mistakes are not arithmetic. They are a rate that changed last
April, a transaction nobody could explain that got filed under "repairs", an
overlapping bank export imported twice, or a review performed by whoever
prepared the figures. Each produces output that looks completely finished.

So the design pushes back in specific places:

| Failure | Structural defence |
|---|---|
| Rates go stale | Every rate carries its legislation reference and a verification date. Unverified rates trigger a banner before any figure is shown. |
| Re-importing doubles income | Transactions are fingerprinted; a duplicate import is refused, not merged. |
| Guessed categories | Classification is rule-based and records the rule ID. No rule, no category — it goes to suspense for a person. |
| Silent edits | The ledger is append-only. Corrections are reversals that reference the original. |
| Self-review | Preparer and reviewer are checked and must differ. It fails until a named human reviews. |
| Plausible wrong answers | Areas the engine cannot do properly (Scotland, IHT, trusts, ATED, partial exemption…) are refused, not approximated. |
| Output used prematurely | A readiness gate blocks on unresolved control failures and reports NOT READY. |

## Running it

Python 3.9+. **No dependencies** — standard library only.

```bash
cd PortfolioAccountant

python3 -m portfolio_accountant.cli demo          # full worked example
python3 -m portfolio_accountant.cli verify-rates  # what needs human checking
python3 -m portfolio_accountant.cli refusals      # what it will not do
python3 -m unittest discover -s tests             # 91 tests
```

For a real portfolio:

```bash
cp data/example/engagement.json my-portfolio.json
# edit entities, properties, and point `sources` at your bank CSV exports
python3 -m portfolio_accountant.cli close --config my-portfolio.json --output report.txt
python3 -m portfolio_accountant.cli calendar --config my-portfolio.json
```

**Before the first real use**, work through `config/uk_2025_26.json` and check
each rate against current HMRC guidance, setting `verified_on` as you go. Until
then every output is banner-flagged as unverified. That friction is deliberate.

## What it produces

Running `close` gives, in order: import summary, classification with the
unclassified work queue, ledger and trial balance, profit and loss and balance
sheet per entity, per-property performance with the Section 24 gap, forensic
indicators, a controls review with a sampling plan, tax computations with full
workings, planning points, the compliance calendar, and a readiness verdict.

The Section 24 output is the part most portfolio owners have never seen laid
out. For personally-held geared residential property, tax is charged on profit
*before* finance costs, with relief returning as a 20% tax reducer. The demo
portfolio earns £13,262 in cash on those properties and is taxed on £32,962.

## As an agent

Two agent definitions live in `.claude/agents/`:

- **`portfolio-accountant`** — the working agent, covering all five roles
  (financial, management, audit, tax, forensic) with the hard rules encoded.
- **`books-auditor`** — independent review, deliberately read-only, and
  required to refuse reviewing its own preparation.

Plus `.claude/skills/portfolio-close/` for the end-to-end workflow.

The agent runs the engine rather than doing arithmetic in prose. A tax figure
asserted without a computation behind it is a guess that reads like a fact.

## Layout

```
portfolio_accountant/
  money.py        exact decimal arithmetic; floats are rejected outright
  config.py       tax parameters with provenance and staleness checks
  model.py        entities, properties, transactions
  ingest.py       CSV import, duplicate protection
  classify.py     deterministic rules, suspense for the unknown
  ledger.py       double entry, append-only, integrity hash
  posting.py      transactions into balanced journals
  statements.py   P&L, balance sheet, accounting-to-taxable bridge
  properties.py   per-property performance, the Section 24 gap
  audit.py        materiality, controls, seeded sampling, independence
  forensics.py    anomaly indicators phrased as questions
  planning.py     statutory reliefs, with the evasion line drawn explicitly
  compliance.py   the deadline calendar
  tax/            income tax, corporation tax, CGT, SDLT, VAT
config/           jurisdiction parameters, chart of accounts
data/example/     worked example with planted anomalies
tests/            91 tests; tax expectations worked by hand
```

## Scope

Covers England & Northern Ireland, tax year 2025/26 as configured. Deliberately
excluded and refused rather than estimated: Scottish and Welsh income tax and
land transaction taxes, inheritance tax, trusts, the non-dom/FIG regime, ATED,
VAT partial exemption and the option to tax, R&D relief, IR35, share schemes,
furnished holiday lets, CIS, and pension allowances. The full list is in
`config/uk_2025_26.json` under `unsupported`.

The figures in `config/` were populated from general knowledge and **have not
been independently verified**. Verify before use.

See [COMPLIANCE.md](COMPLIANCE.md) for the legal boundaries this operates
within, including the distinction between evasion, avoidance and planning.
