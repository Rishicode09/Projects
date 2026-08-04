"""A local browser interface, built on the standard library only.

Run it with::

    python -m portfolio_accountant.cli web

and a browser opens on http://127.0.0.1:8000.

Two deliberate constraints.

**It binds to 127.0.0.1, never 0.0.0.0.** This serves a complete picture of
someone's finances -- properties, income, bank transactions, tax position -- with
no authentication, because on loopback none is needed. Bound to all interfaces
it would publish that to every device on the network, including the coffee shop
wifi. The bind address is not configurable for this reason.

**The page and the terminal report come from the same run.** The web layer
renders the structured objects that ``run_close`` already returns rather than
recomputing anything. Two views of one computation cannot disagree; two
computations eventually will.

There is no ``pip install`` and no framework here, which keeps the whole thing
runnable on a machine with nothing but Python on it.
"""

from __future__ import annotations

import html
import io
import traceback
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import parse_qs, quote, urlparse

from .compliance import record_retention_note
from .config import CONFIG_DIR, ConfigError, load_jurisdiction
from .money import Money

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PACKAGE_ROOT / "data"

# Loopback only. See the module docstring before changing this.
BIND_HOST = "127.0.0.1"


# ---------------------------------------------------------------------------
# Presentation
# ---------------------------------------------------------------------------

STYLE = """
/* Palette: ledger blue accent with blue-biased neutrals, so the greys read as
   chosen rather than inherited. Semantic colours (ok/warn/bad) are deliberately
   distinct from the accent - severity must not be confusable with emphasis.

   Theming is token-level: components style through the variables and never
   inside a media query, so the OS preference and the viewer's explicit toggle
   can each win in both directions. */
:root {
  --bg: #f3f6f8; --card: #ffffff; --ink: #131a22; --muted: #5a6675;
  --line: #dfe5eb; --accent: #1f5f8b; --ok: #1c7c4a; --warn: #a05f00;
  --bad: #b3261e; --chip: #e9eef3;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #10141a; --card: #181e26; --ink: #e6ebf1; --muted: #97a3b2;
    --line: #29323d; --accent: #6fb3e0; --ok: #5cc98d; --warn: #e0a94a;
    --bad: #f2887f; --chip: #222b35;
  }
}
:root[data-theme="dark"] {
  --bg: #10141a; --card: #181e26; --ink: #e6ebf1; --muted: #97a3b2;
  --line: #29323d; --accent: #6fb3e0; --ok: #5cc98d; --warn: #e0a94a;
  --bad: #f2887f; --chip: #222b35;
}
:root[data-theme="light"] {
  --bg: #f3f6f8; --card: #ffffff; --ink: #131a22; --muted: #5a6675;
  --line: #dfe5eb; --accent: #1f5f8b; --ok: #1c7c4a; --warn: #a05f00;
  --bad: #b3261e; --chip: #e9eef3;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.55 -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
header {
  background: var(--card); border-bottom: 1px solid var(--line);
  padding: 18px 24px; position: sticky; top: 0; z-index: 10;
}
header h1 { margin: 0 0 2px; font-size: 19px; letter-spacing: -0.01em; }
header .sub { color: var(--muted); font-size: 13px; }
nav { margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap; }
nav a {
  padding: 5px 11px; border-radius: 999px; background: var(--chip);
  color: var(--ink); text-decoration: none; font-size: 13px;
}
nav a:hover { background: var(--accent); color: #fff; }
main { max-width: 1080px; margin: 0 auto; padding: 24px; }
.card {
  background: var(--card); border: 1px solid var(--line); border-radius: 10px;
  padding: 20px 22px; margin-bottom: 18px;
}
.card h2 {
  margin: 0 0 14px; font-size: 16px; text-transform: uppercase;
  letter-spacing: 0.06em; color: var(--muted);
}
.card h3 { margin: 18px 0 8px; font-size: 15px; }
.banner { border-left: 4px solid var(--warn); padding: 14px 18px; }
.banner.bad { border-left-color: var(--bad); }
.banner.ok { border-left-color: var(--ok); }
.banner h2 { color: var(--ink); text-transform: none; letter-spacing: 0; font-size: 17px; }
.tablewrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--line); }
th { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; }
td.num, th.num { text-align: right; white-space: nowrap; }
tr.total td { font-weight: 600; border-top: 2px solid var(--line); border-bottom: none; }
.neg { color: var(--bad); }
.pos { color: var(--ok); }
.tag {
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
}
.tag.high { background: var(--bad); color: #fff; }
.tag.medium { background: var(--warn); color: #fff; }
.tag.low, .tag.info { background: var(--chip); color: var(--muted); }
.tag.pass { background: var(--ok); color: #fff; }
.tag.fail { background: var(--bad); color: #fff; }
/* Severity reads as form as well as colour: a left stripe makes the high-risk
   items scannable without relying on hue alone. */
.finding {
  border: 1px solid var(--line); border-left: 4px solid var(--line);
  border-radius: 8px; padding: 14px; margin-bottom: 12px;
}
.finding.high { border-left-color: var(--bad); }
.finding.medium { border-left-color: var(--warn); }
.finding.low, .finding.info { border-left-color: var(--muted); }
a:focus-visible, .btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
.finding .q { margin: 8px 0; }
.finding ul { margin: 6px 0 0; padding-left: 20px; color: var(--muted); font-size: 13px; }
.muted { color: var(--muted); }
.small { font-size: 13px; }
ul.plain { list-style: none; padding: 0; margin: 0; }
ul.plain li { padding: 6px 0; border-bottom: 1px solid var(--line); }
ul.plain li:last-child { border-bottom: none; }
pre {
  background: var(--chip); padding: 14px; border-radius: 8px; overflow-x: auto;
  font: 12.5px/1.5 ui-monospace, "Cascadia Mono", Consolas, monospace;
}
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; }
.stat { background: var(--chip); border-radius: 8px; padding: 13px 15px; }
.stat .label { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
.stat .value { font-size: 21px; font-weight: 600; margin-top: 3px; font-variant-numeric: tabular-nums; }
a.btn {
  display: inline-block; background: var(--accent); color: #fff; text-decoration: none;
  padding: 9px 16px; border-radius: 7px; font-weight: 500; margin: 4px 6px 4px 0;
}
a.btn.sec { background: var(--chip); color: var(--ink); }
footer { color: var(--muted); font-size: 13px; padding: 8px 24px 40px; max-width: 1080px; margin: 0 auto; }
@media print {
  header, nav, a.btn { display: none; }
  .card { break-inside: avoid; border: 1px solid #ccc; }
}
"""


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def money_cell(amount: Money) -> str:
    css = "neg" if amount.is_negative else ""
    return f'<td class="num {css}">{esc(amount)}</td>'


def page(title: str, body: str, subtitle: str = "") -> bytes:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — Portfolio Accountant</title>
<style>{STYLE}</style></head><body>
<header>
  <h1>{esc(title)}</h1>
  <div class="sub">{esc(subtitle) if subtitle else "Prepared workings — not a filing tool, not tax advice"}</div>
  <nav>
    <a href="/">Home</a>
    <a href="/rates">Verify rates</a>
    <a href="/refusals">What it won't do</a>
    <a href="/retention">Record keeping</a>
  </nav>
</header>
<main>{body}</main>
<footer>
  Served locally on {esc(BIND_HOST)} — nothing leaves this machine.
  Close the Command Prompt window to stop the server.
</footer>
</body></html>""".encode("utf-8")


# ---------------------------------------------------------------------------
# Engagement discovery
# ---------------------------------------------------------------------------


def find_engagements() -> List[Path]:
    """Every engagement.json under data/, so the user picks rather than types."""
    if not DATA_DIR.exists():
        return []
    return sorted(DATA_DIR.glob("*/engagement.json"))


def resolve_engagement(name: str) -> Path:
    """Map a folder name to its config, refusing anything outside data/.

    The name comes from a query string, so it is treated as hostile: only an
    exact match against the discovered list is accepted. That rules out
    traversal without relying on getting the escaping right.
    """
    for path in find_engagements():
        if path.parent.name == name:
            return path
    raise ConfigError(f"no engagement folder named '{name}' under data/")


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


def view_home() -> bytes:
    engagements = find_engagements()

    if engagements:
        rows = "".join(
            f'<li><strong>{esc(p.parent.name)}</strong>'
            f'<a class="btn" style="float:right;margin:0" href="/run?config={quote(p.parent.name)}">'
            f'Run close</a>'
            f'<br><span class="muted small">{esc(p.parent)}</span></li>'
            for p in engagements
        )
        listing = f'<ul class="plain">{rows}</ul>'
    else:
        listing = (
            '<p class="muted">No engagement folders found under <code>data\\</code>.</p>'
        )

    setup = """
<div class="card">
  <h2>Set up your own portfolio</h2>
  <p>In Command Prompt, from inside the <code>PortfolioAccountant</code> folder:</p>
  <pre>xcopy /E /I data\\example data\\mine
del data\\mine\\generate_example_data.py</pre>
  <p>Then in <code>data\\mine</code>: replace the two CSVs with your own bank exports,
  edit <code>engagement.json</code> (entities, properties, and the file names under
  <code>sources</code>), and adapt <code>rules.json</code> to match how your bank
  describes transactions.</p>
  <p class="muted small">Keep the config in the same folder as its CSVs — paths inside it
  resolve relative to where it sits, so a config on its own cannot find its data.
  Refresh this page and the folder appears above.</p>
</div>"""

    body = f"""
<div class="card banner">
  <h2>What this is</h2>
  <p>Prepared workings for a portfolio mixing property and business — bookkeeping,
  management reporting, tax computations, controls review and forensic checks,
  with every figure traceable to a source document.</p>
  <p><strong>It is not</strong> a tax return, statutory accounts, an audit opinion,
  or tax advice. Those are regulated acts requiring a qualified person who is
  accountable for them. This is the input to that person's work.</p>
</div>

<div class="card">
  <h2>Portfolios</h2>
  {listing}
  <p class="muted small" style="margin-top:14px">A full close takes a few seconds.
  The page will pause while it runs.</p>
</div>
{setup}"""
    return page("Portfolio Accountant", body)


def _verification_card(jur) -> str:
    stale = jur.staleness_warnings()
    status = jur.raw.get("meta", {}).get("verification_status", "")
    if status == "UNVERIFIED_DRAFT" or stale:
        return f"""
<div class="card banner bad">
  <h2>Rates not verified</h2>
  <p>{len(stale)} tax parameter{'s' if len(stale) != 1 else ''} have no human
  verification date. Every figure below is <strong>indicative only</strong>.</p>
  <p>Before any of it informs a filing, a payment, a lender or a purchase: check
  each rate against current HMRC guidance, set <code>verified_on</code> in
  <code>config\\{esc(jur.raw.get('meta', {}).get('tax_year', '')).replace('/', '_')}</code>,
  and run again. Rates change at Budgets, sometimes retrospectively — a computation
  built on a stale rate is confidently wrong, which is worse than none.</p>
  <a class="btn" href="/rates">See what needs checking</a>
</div>"""
    return (
        '<div class="card banner ok"><h2>Rates verified</h2>'
        f"<p>{len(jur.parameters)} parameters loaded.</p></div>"
    )


def _readiness_card(blockers: List[str]) -> str:
    if not blockers:
        return """
<div class="card banner ok">
  <h2>No blocking issues</h2>
  <p>The automated checks found nothing blocking. A named person must still review
  the workings and take responsibility before anything is filed — the absence of a
  detected problem is not the presence of assurance.</p>
</div>"""
    items = "".join(f"<li>{esc(b)}</li>" for b in blockers)
    return f"""
<div class="card banner bad">
  <h2>Not ready — {len(blockers)} blocking issue{'s' if len(blockers) != 1 else ''}</h2>
  <ul class="plain">{items}</ul>
  <p class="small" style="margin-top:12px">Resolve each before these figures go to a
  filing, a lender or a purchase decision. Do not work around them.</p>
</div>"""


def _properties_card(summary) -> str:
    if not summary.properties:
        return ""
    rows = []
    for p in sorted(summary.properties, key=lambda x: x.property_id):
        rows.append(
            f"<tr><td><strong>{esc(p.property_id)}</strong><br>"
            f'<span class="muted small">{esc(p.address)}</span></td>'
            f"{money_cell(p.gross_rent)}{money_cell(p.operating_costs)}"
            f"{money_cell(p.finance_costs)}{money_cell(p.cash_profit)}"
            f'<td class="num">{p.return_on_equity:.1f}%</td></tr>'
        )
    rows.append(
        f'<tr class="total"><td>TOTAL</td>{money_cell(summary.gross_rent)}'
        f"{money_cell(summary.operating_costs)}{money_cell(summary.finance_costs)}"
        f'{money_cell(summary.cash_profit)}<td class="num"></td></tr>'
    )

    s24 = ""
    if summary.restricted_finance_costs > 0:
        affected = ", ".join(p.property_id for p in summary.s24_properties)
        s24 = f"""
<h3>Section 24 gap</h3>
<p class="small">Affected (personally-held residential): {esc(affected)}</p>
<div class="grid">
  <div class="stat"><div class="label">Taxed on</div>
    <div class="value">{esc(summary.s24_taxable_base)}</div></div>
  <div class="stat"><div class="label">Actually earned</div>
    <div class="value">{esc(summary.s24_cash_profit)}</div></div>
  <div class="stat"><div class="label">Non-deductible interest</div>
    <div class="value">{esc(summary.restricted_finance_costs)}</div></div>
</div>
<p class="small muted" style="margin-top:10px">Finance costs are not deductible on
these properties. Relief returns as a 20% tax reducer, so a higher-rate taxpayer
bears a real cost of 20% of the restricted interest.</p>"""

    queries = ""
    flagged = [p for p in summary.properties if p.flags]
    if flagged:
        items = "".join(
            f"<li><strong>{esc(p.property_id)}</strong> — {esc(p.address)}<ul>"
            + "".join(f"<li>{esc(f)}</li>" for f in p.flags)
            + "</ul></li>"
            for p in flagged
        )
        queries = f'<h3>Queries</h3><ul class="plain">{items}</ul>'

    return f"""
<div class="card">
  <h2>Property performance</h2>
  <div class="tablewrap"><table>
    <tr><th>Property</th><th class="num">Rent</th><th class="num">Costs</th>
        <th class="num">Finance</th><th class="num">Cash</th><th class="num">RoE</th></tr>
    {''.join(rows)}
  </table></div>
  <div class="grid" style="margin-top:16px">
    <div class="stat"><div class="label">Portfolio value</div>
      <div class="value">{esc(summary.total_value)}</div></div>
    <div class="stat"><div class="label">Debt</div>
      <div class="value">{esc(summary.total_debt)}</div></div>
    <div class="stat"><div class="label">Loan to value</div>
      <div class="value">{summary.loan_to_value:.1f}%</div></div>
    <div class="stat"><div class="label">Interest cover</div>
      <div class="value">{summary.interest_cover:.2f}x</div></div>
  </div>
  {s24}
  {queries}
</div>"""


def _statements_card(statements) -> str:
    if not statements:
        return ""
    blocks = []
    for entity, pl, bs in statements:
        income = "".join(
            f"<tr><td>{esc(pl.account_names.get(c, c))}</td>{money_cell(v)}</tr>"
            for c, v in sorted(pl.income.items())
        )
        expenses = "".join(
            f"<tr><td>{esc(pl.account_names.get(c, c))}</td>{money_cell(v)}</tr>"
            for c, v in sorted(pl.expenses.items())
        )
        warn = ""
        if not bs.balances:
            warn = ('<p class="neg"><strong>Balance sheet does not balance. '
                    "Do not issue these figures.</strong></p>")
        blocks.append(f"""
<h3>{esc(entity.name)} <span class="muted small">({esc(entity.id)})</span></h3>
<div class="tablewrap"><table>
  <tr><th>Income</th><th class="num"></th></tr>{income}
  <tr class="total"><td>Total income</td>{money_cell(pl.total_income)}</tr>
  <tr><th style="padding-top:16px">Expenses</th><th class="num"></th></tr>{expenses}
  <tr class="total"><td>Total expenses</td>{money_cell(pl.total_expenses)}</tr>
  <tr class="total"><td>{'PROFIT' if not pl.profit.is_negative else 'LOSS'}</td>
      {money_cell(pl.profit)}</tr>
</table></div>
<div class="grid" style="margin-top:12px">
  <div class="stat"><div class="label">Net assets</div>
    <div class="value">{esc(bs.net_assets)}</div></div>
  <div class="stat"><div class="label">Total equity</div>
    <div class="value">{esc(bs.total_equity)}</div></div>
</div>{warn}""")
    return f'<div class="card"><h2>Statements</h2>{"".join(blocks)}</div>'


def _forensic_card(forensic) -> str:
    if not forensic.findings:
        return ('<div class="card"><h2>Forensic review</h2>'
                "<p>No indicators raised.</p></div>")
    blocks = []
    for f in forensic.sorted_findings():
        evidence = "".join(f"<li>{esc(e)}</li>" for e in f.evidence[:6])
        more = (f'<li class="muted">…and {len(f.evidence) - 6} more</li>'
                if len(f.evidence) > 6 else "")
        value = (f'<span class="muted small"> — {esc(f.value_at_risk)} involved</span>'
                 if not f.value_at_risk.is_zero else "")
        innocent = ""
        if f.innocent_explanations:
            innocent = ('<p class="small muted">Commonly innocent because: '
                        + esc("; ".join(f.innocent_explanations)) + "</p>")
        blocks.append(f"""
<div class="finding {esc(f.severity)}">
  <span class="tag {esc(f.severity)}">{esc(f.severity)}</span>
  <strong> {esc(f.test)}</strong>{value}
  <p>{esc(f.summary)}</p>
  <p class="q"><strong>Question to ask:</strong> {esc(f.explanation_sought)}</p>
  {innocent}
  <ul>{evidence}{more}</ul>
</div>""")
    return f"""
<div class="card">
  <h2>Forensic review</h2>
  <p class="small muted">{forensic.transactions_reviewed} transactions reviewed.
  Evidence hash <code>{esc(forensic.evidence_hash)}</code>.</p>
  {''.join(blocks)}
  <p class="small muted">Every item is an <strong>indicator, not a conclusion</strong>.
  Seek the explanation before drawing any inference. These tests only see what was
  recorded — they cannot detect income that never entered the books.</p>
</div>"""


def _review_card(review) -> str:
    rows = "".join(
        f'<tr><td><span class="tag {"pass" if c.passed else "fail"}">'
        f'{"pass" if c.passed else "fail"}</span></td>'
        f"<td><strong>{esc(c.name)}</strong><br>"
        f'<span class="muted small">{esc(c.detail)}</span>'
        + (f'<br><span class="small neg">Risk: {esc(c.risk_if_failed)}</span>'
           if not c.passed and c.risk_if_failed else "")
        + "</td></tr>"
        for c in review.checks
    )
    return f"""
<div class="card">
  <h2>Controls review <span class="muted small">(not a statutory audit)</span></h2>
  <div class="grid">
    <div class="stat"><div class="label">Materiality</div>
      <div class="value">{esc(review.materiality)}</div></div>
    <div class="stat"><div class="label">Prepared by</div>
      <div class="value" style="font-size:15px">{esc(review.prepared_by or "unrecorded")}</div></div>
    <div class="stat"><div class="label">Reviewed by</div>
      <div class="value" style="font-size:15px">{esc(review.reviewed_by or "NOT YET REVIEWED")}</div></div>
  </div>
  <div class="tablewrap"><table style="margin-top:14px">{rows}</table></div>
  <p class="small muted">{len(review.sample)} item(s) selected for vouching — trace each
  to its invoice and confirm amount, date, payee and business purpose.</p>
</div>"""


def _tax_card(computations) -> str:
    if not computations:
        return ""
    blocks = []
    for comp in computations:
        steps = "".join(
            f"<tr><td>{esc(s.label)}</td>"
            f'<td class="num">{esc(s.amount) if s.amount is not None else ""}</td>'
            f'<td class="num">{f"{s.rate * 100:.4g}%" if s.rate is not None else ""}</td>'
            f'<td class="num">{esc(s.result) if s.result is not None else ""}</td></tr>'
            + (f'<tr><td colspan="4" class="muted small">{esc(s.note)}</td></tr>'
               if s.note else "")
            for s in comp.steps
        )
        totals = "".join(
            f'<tr class="total"><td>{esc(k.replace("_", " ").title())}</td>'
            f'<td class="num" colspan="3">{esc(v)}</td></tr>'
            for k, v in comp.totals.items()
        )
        extras = ""
        for label, items, css in (
            ("Assumptions", comp.assumptions, "muted"),
            ("Warnings", comp.warnings, "neg"),
            ("Refer to a qualified adviser", comp.referrals, ""),
        ):
            if items:
                extras += (f'<h3>{esc(label)}</h3><ul class="{css} small">'
                           + "".join(f"<li>{esc(i)}</li>" for i in items) + "</ul>")
        blocks.append(f"""
<h3>{esc(comp.title)} <span class="muted small">{esc(comp.entity_id)} {esc(comp.period)}</span></h3>
<div class="tablewrap"><table>
  <tr><th>Working</th><th class="num">Amount</th><th class="num">Rate</th><th class="num">Result</th></tr>
  {steps}{totals}
</table></div>{extras}""")
    return f'<div class="card"><h2>Tax computations</h2>{"".join(blocks)}</div>'


def _planning_card(planning) -> str:
    if not planning.opportunities:
        return ""
    order = {"high": 0, "medium": 1, "low": 2}
    blocks = []
    for o in sorted(planning.opportunities, key=lambda x: order.get(x.priority, 9)):
        conditions = ("<strong>Conditions that must genuinely be met:</strong><ul>"
                      + "".join(f"<li>{esc(c)}</li>" for c in o.conditions) + "</ul>"
                      if o.conditions else "")
        risks = ("<strong>Risks:</strong><ul>"
                 + "".join(f"<li>{esc(r)}</li>" for r in o.risks) + "</ul>"
                 if o.risks else "")
        blocks.append(f"""
<div class="finding {esc(o.priority)}">
  <span class="tag {esc(o.priority)}">{esc(o.priority)}</span>
  <strong> {esc(o.title)}</strong>
  <p class="muted small">Basis: {esc(o.statutory_basis)}</p>
  <p>{esc(o.summary)}</p>
  <div class="small">{conditions}{risks}</div>
</div>""")
    return f"""
<div class="card">
  <h2>Planning review</h2>
  <p class="small">Every item is the use of a statutory relief on its own terms.
  None of it depends on HMRC not noticing.</p>
  {''.join(blocks)}
  <p class="small muted">This is a list of questions to put to your adviser, not
  advice. Tax advice is regulated and depends on facts not in these records.</p>
</div>"""


def _calendar_card(calendar) -> str:
    def render(obligations, css=""):
        return "".join(
            f'<li><strong>{esc(o.due)}</strong> — {esc(o.title)} '
            f'<span class="muted small">({esc(o.entity_id)}, {esc(o.authority)})</span>'
            + (f'<br><span class="small {css}">If missed: {esc(o.consequence)}</span>'
               if o.consequence else "")
            + "</li>"
            for o in obligations
        )

    overdue = calendar.overdue
    overdue_block = ""
    if overdue:
        overdue_block = (
            f"<h3 class='neg'>Overdue — {len(overdue)}</h3>"
            f'<ul class="plain">{render(sorted(overdue, key=lambda o: o.due), "neg")}</ul>'
        )
    upcoming = [o for o in calendar.upcoming(365) if o.due >= calendar.as_at]
    return f"""
<div class="card">
  <h2>Compliance calendar</h2>
  {overdue_block}
  <h3>Upcoming</h3>
  <ul class="plain">{render(upcoming[:20])}</ul>
</div>"""


def view_run(name: str) -> bytes:
    from .cli import load_engagement, run_close  # imported late to avoid a cycle

    config_path = resolve_engagement(name)
    engagement = load_engagement(str(config_path))
    out: List[str] = []
    sections = run_close(engagement, out)

    jur = sections["jurisdiction"]
    summary = sections.get("summary")
    imported = sections.get("import")
    classification = sections.get("classification")

    queue = ""
    if classification and classification.unclassified:
        top = sorted(
            classification.unmatched_descriptions.items(), key=lambda kv: -kv[1]
        )[:12]
        rows = "".join(
            f'<tr><td class="num">{count}x</td><td>{esc(desc)}</td></tr>'
            for desc, count in top
        )
        queue = f"""
<h3>Work queue — needs a human decision</h3>
<div class="tablewrap"><table>{rows}</table></div>
<p class="small muted">Nothing here should be guessed. An expense whose purpose
cannot be determined is not a deductible expense. Each of these is either an
expense, a capital item, or drawings — three different tax outcomes.</p>"""

    body = "".join([
        _verification_card(jur),
        _readiness_card(sections.get("blockers", [])),
        f"""
<div class="card">
  <h2>Import and classification</h2>
  <div class="grid">
    <div class="stat"><div class="label">Imported</div>
      <div class="value">{imported.imported_count if imported else 0}</div></div>
    <div class="stat"><div class="label">Duplicates skipped</div>
      <div class="value">{len(imported.duplicates) if imported else 0}</div></div>
    <div class="stat"><div class="label">Classified</div>
      <div class="value">{classification.coverage:.0f}%</div></div>
    <div class="stat"><div class="label">Unclassified</div>
      <div class="value">{len(classification.unclassified)}</div></div>
  </div>
  {queue}
</div>""",
        _statements_card(sections.get("statements", [])),
        _properties_card(summary) if summary else "",
        _tax_card(sections.get("computations", [])),
        _forensic_card(sections["forensic"]) if "forensic" in sections else "",
        _review_card(sections["review"]) if "review" in sections else "",
        _planning_card(sections["planning"]) if "planning" in sections else "",
        _calendar_card(sections["calendar"]) if "calendar" in sections else "",
        f"""
<div class="card">
  <h2>Full text report</h2>
  <p class="small muted">The same run, as the terminal prints it. Use your browser's
  print function to save the whole page as a PDF.</p>
  <pre>{esc(chr(10).join(out))}</pre>
</div>""",
    ])
    return page(f"Close — {name}", body, subtitle=str(sections.get("period_label", "")))


def view_rates() -> bytes:
    jur = load_jurisdiction("uk_2025_26")
    stale = jur.staleness_warnings()
    rows = "".join(f"<li>{esc(w)}</li>" for w in stale)
    unsupported = "".join(f"<li>{esc(u)}</li>" for u in jur.unsupported)
    body = f"""
{_verification_card(jur)}
<div class="card">
  <h2>Parameters needing verification ({len(stale)})</h2>
  <ul class="plain small">{rows}</ul>
</div>
<div class="card">
  <h2>Deliberately not implemented</h2>
  <p class="small">Each is referred to a qualified adviser rather than estimated.</p>
  <ul class="plain small">{unsupported}</ul>
  <p class="small muted">{esc(jur.raw.get('unsupported_note', ''))}</p>
</div>"""
    return page("Verify rates", body, f"{jur.name} — {jur.tax_year}")


def view_refusals() -> bytes:
    from .planning import DISCLOSURE_ROUTES, REFUSED

    refused = "".join(f"<li>{esc(r)}</li>" for r in REFUSED)
    routes = "".join(
        f"<li><strong>{esc(k.replace('_', ' ').title())}</strong><br>"
        f'<span class="small">{esc(v)}</span></li>'
        for k, v in DISCLOSURE_ROUTES.items()
    )
    body = f"""
<div class="card banner bad">
  <h2>This will not assist with</h2>
  <ul class="plain">{refused}</ul>
  <p class="small">These are not preferences. Each describes conduct that is a
  criminal offence, professional misconduct, or both.</p>
</div>
<div class="card">
  <h2>If something is already wrong</h2>
  <p>Discovering a past error is common and usually not sinister. The response is
  what matters, and quietly fixing it forward is the wrong one.</p>
  <ul class="plain">{routes}</ul>
  <p class="small"><strong>Unprompted disclosure attracts substantially lower
  penalties than one made after HMRC opens an enquiry.</strong> Take specialist
  advice on the route before making one.</p>
</div>"""
    return page("What this won't do", body)


def view_retention() -> bytes:
    jur = load_jurisdiction("uk_2025_26")
    body = (f'<div class="card"><h2>Record keeping</h2>'
            f"<pre>{esc(record_retention_note(jur))}</pre></div>")
    return page("Record keeping", body)


# ---------------------------------------------------------------------------
# Static export
# ---------------------------------------------------------------------------

GUIDE = """
<section id="guide" class="card banner">
  <h2>What you are looking at</h2>
  <p>This is one complete run over a portfolio: three flats held personally, one
  commercial unit held through a company, twelve months of bank transactions.
  Every figure below was computed from those transactions and traces back to a
  row in a bank export.</p>
  <p>The example data has deliberate problems in it, because a demo where
  everything is clean teaches nothing. A contractor invoice paid twice, payments
  with no receipt, cash deposits, unexplained transfers. Watch how each is
  surfaced as a <em>question</em> rather than an accusation or a silent fix.</p>

  <h3>The order is the argument</h3>
  <p>Sections run in dependency order, and that is deliberate: the most common way
  to produce confidently wrong accounts is to compute tax on a ledger nobody
  reconciled. So the verification state and the readiness verdict come
  <strong>before</strong> any numbers, not in a footnote after them.</p>

  <div class="tablewrap"><table>
    <tr><th>Section</th><th>Question it answers</th></tr>
    <tr><td><a href="#rates">Rate verification</a></td>
        <td>Can these numbers be trusted at all yet?</td></tr>
    <tr><td><a href="#readiness">Readiness</a></td>
        <td>Is this fit to file, or is something unresolved?</td></tr>
    <tr><td><a href="#import">Import &amp; classify</a></td>
        <td>What came in, and what still needs a human decision?</td></tr>
    <tr><td><a href="#statements">Statements</a></td>
        <td>Profit and loss, balance sheet, per entity.</td></tr>
    <tr><td><a href="#properties">Properties</a></td>
        <td>Which properties actually make money? What does Section 24 cost?</td></tr>
    <tr><td><a href="#tax">Tax</a></td>
        <td>What is legally due, with every step of the working shown?</td></tr>
    <tr><td><a href="#forensics">Forensic review</a></td>
        <td>What does not add up, and what should be asked about it?</td></tr>
    <tr><td><a href="#controls">Controls</a></td>
        <td>Would this survive being checked by someone independent?</td></tr>
    <tr><td><a href="#planning">Planning</a></td>
        <td>Which statutory reliefs do these facts actually engage?</td></tr>
    <tr><td><a href="#calendar">Calendar</a></td>
        <td>What is due, when, and what happens if it is missed?</td></tr>
  </table></div>

  <h3>Three things worth watching for</h3>
  <ul class="plain">
    <li><strong>It refuses to declare itself finished.</strong> The readiness
    verdict below says NOT READY, and one blocking reason is that no human has
    reviewed it. That check cannot be satisfied by the software itself.</li>
    <li><strong>Unknown transactions are not guessed.</strong> Anything no rule
    matches goes to a work queue rather than being swept into a plausible
    category. The queue is the point, not a failure.</li>
    <li><strong>The Section 24 gap.</strong> On personally-held mortgaged
    residential property, tax is charged on profit <em>before</em> finance costs.
    That is why the taxable figure below is far larger than the cash actually
    earned.</li>
  </ul>
</section>"""


def static_page(title: str, body: str, subtitle: str) -> bytes:
    """A single self-contained page, with in-page anchors instead of routes."""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>{STYLE}
html {{ scroll-behavior: smooth; }}
@media (prefers-reduced-motion: reduce) {{ html {{ scroll-behavior: auto; }} }}
section {{ scroll-margin-top: 130px; }}
</style></head><body>
<header>
  <h1>{esc(title)}</h1>
  <div class="sub">{esc(subtitle)}</div>
  <nav>
    <a href="#guide">Guide</a>
    <a href="#readiness">Readiness</a>
    <a href="#import">Import</a>
    <a href="#statements">Statements</a>
    <a href="#properties">Properties</a>
    <a href="#tax">Tax</a>
    <a href="#forensics">Forensics</a>
    <a href="#controls">Controls</a>
    <a href="#planning">Planning</a>
    <a href="#calendar">Calendar</a>
  </nav>
</header>
<main>{body}</main>
<footer>
  Prepared workings only — not a tax return, not statutory accounts, not an audit
  opinion, and not tax advice. A named person must review these workings and take
  responsibility before anything is filed.
</footer>
</body></html>""".encode("utf-8")


def export_static(name: str = "example", include_guide: bool = True) -> bytes:
    """Render one complete run as a self-contained HTML file.

    Useful beyond the demo: it is how you hand a period's workings to an
    accountant or a lender without asking them to run anything.
    """
    from .cli import load_engagement, run_close

    config_path = resolve_engagement(name)
    engagement = load_engagement(str(config_path))
    out: List[str] = []
    sections = run_close(engagement, out)

    jur = sections["jurisdiction"]
    summary = sections.get("summary")
    imported = sections.get("import")
    classification = sections.get("classification")

    queue = ""
    if classification and classification.unclassified:
        top = sorted(
            classification.unmatched_descriptions.items(), key=lambda kv: -kv[1]
        )[:12]
        rows = "".join(
            f'<tr><td class="num">{count}x</td><td>{esc(desc)}</td></tr>'
            for desc, count in top
        )
        queue = f"""
<h3>Work queue — needs a human decision</h3>
<div class="tablewrap"><table>{rows}</table></div>
<p class="small muted">Nothing here is guessed. Each is either an expense, a
capital item, or drawings — three different tax outcomes. An expense whose
purpose cannot be determined is not a deductible expense.</p>"""

    def wrap(anchor: str, markup: str) -> str:
        return f'<section id="{anchor}">{markup}</section>' if markup else ""

    body = "".join([
        GUIDE if include_guide else "",
        wrap("rates", _verification_card(jur)),
        wrap("readiness", _readiness_card(sections.get("blockers", []))),
        wrap("import", f"""
<div class="card">
  <h2>Import and classification</h2>
  <div class="grid">
    <div class="stat"><div class="label">Imported</div>
      <div class="value">{imported.imported_count if imported else 0}</div></div>
    <div class="stat"><div class="label">Duplicates skipped</div>
      <div class="value">{len(imported.duplicates) if imported else 0}</div></div>
    <div class="stat"><div class="label">Classified</div>
      <div class="value">{classification.coverage:.0f}%</div></div>
    <div class="stat"><div class="label">Unclassified</div>
      <div class="value">{len(classification.unclassified)}</div></div>
  </div>
  {queue}
</div>"""),
        wrap("statements", _statements_card(sections.get("statements", []))),
        wrap("properties", _properties_card(summary) if summary else ""),
        wrap("tax", _tax_card(sections.get("computations", []))),
        wrap("forensics", _forensic_card(sections["forensic"])
             if "forensic" in sections else ""),
        wrap("controls", _review_card(sections["review"])
             if "review" in sections else ""),
        wrap("planning", _planning_card(sections["planning"])
             if "planning" in sections else ""),
        wrap("calendar", _calendar_card(sections["calendar"])
             if "calendar" in sections else ""),
        wrap("report", f"""
<div class="card">
  <h2>Full text report</h2>
  <p class="small muted">The identical run as the terminal prints it — the page
  and the text are two views of one computation, never two computations.</p>
  <pre>{esc(chr(10).join(out))}</pre>
</div>"""),
    ])

    return static_page(
        f"Portfolio close — {name}",
        body,
        f"{jur.name} · {jur.tax_year} · {sections.get('period_label', '')}",
    )


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------


class Handler(BaseHTTPRequestHandler):
    server_version = "PortfolioAccountant"

    def log_message(self, fmt, *args):  # quieter console
        return

    def _send(self, body: bytes, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # This page renders financial data; no reason for it to be framed.
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path
        params = parse_qs(parsed.query)

        try:
            if route == "/":
                self._send(view_home())
            elif route == "/run":
                name = (params.get("config") or [""])[0]
                self._send(view_run(name))
            elif route == "/rates":
                self._send(view_rates())
            elif route == "/refusals":
                self._send(view_refusals())
            elif route == "/retention":
                self._send(view_retention())
            elif route == "/favicon.ico":
                self._send(b"", 404)
            else:
                self._send(page("Not found",
                                '<div class="card"><h2>Not found</h2>'
                                '<p><a href="/">Back to the start</a></p></div>'), 404)
        except ConfigError as exc:
            self._send(page("Configuration problem", f"""
<div class="card banner bad">
  <h2>Configuration problem</h2>
  <p>{esc(exc)}</p>
  <p class="small">Check the engagement file and that its CSVs sit in the same
  folder. <a href="/">Back to the start</a></p>
</div>"""), 400)
        except Exception:  # noqa: BLE001 - show the user something actionable
            detail = traceback.format_exc()
            self._send(page("Something went wrong", f"""
<div class="card banner bad">
  <h2>Something went wrong</h2>
  <p class="small">The details below are what to send if you want help
  diagnosing it.</p>
  <pre>{esc(detail)}</pre>
  <p><a href="/">Back to the start</a></p>
</div>"""), 500)


def serve(port: int = 8000, open_browser: bool = True) -> None:
    """Start the local server and hold the console until interrupted."""
    address = (BIND_HOST, port)
    try:
        httpd = ThreadingHTTPServer(address, Handler)
    except OSError as exc:
        print(f"\nCould not start on port {port}: {exc}")
        print(f"Something else is probably using it. Try a different port:\n")
        print(f"    python -m portfolio_accountant.cli web --port {port + 1}\n")
        return

    url = f"http://{BIND_HOST}:{port}/"
    print()
    print("=" * 66)
    print("  Portfolio Accountant is running in your browser")
    print()
    print(f"    {url}")
    print()
    print("  Serving on this machine only - nothing leaves your laptop.")
    print("  Press Ctrl+C (or close this window) to stop.")
    print("=" * 66)
    print()

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:  # pragma: no cover - headless or no default browser
            print("  (Could not open a browser automatically - paste the link above.)")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()
