# Cash In / Cash Out Organiser (basic ML)

Reads a company bank statement CSV and organises it into a bookkeeping-ready
cash in / cash out analysis using a small scikit-learn pipeline.

## Run

```bash
pip install pandas scikit-learn
python cashflow_ml.py                    # finds the CSV automatically
python cashflow_ml.py path/to/other.csv  # or point it at any statement
```

With no argument it looks for `bank_company.csv` first in `data/`, then next to the
script itself — so it works whether or not you keep a `data/` folder. If it finds
nothing it lists where it looked and any CSVs it can see nearby.

On Windows, quote paths that contain spaces:

```powershell
python "cashflow_ml.py" "C:\Users\you\Downloads\bank_company.csv"
```

Expected columns: `date, description, paid in, paid out, counterparty, property, document`
(dates `dd/mm/yyyy`).

## What the ML does

| Step | Model | Purpose |
|---|---|---|
| Stream discovery | TF-IDF + **KMeans** | Groups narratives into recurring payment streams without being told what they are; each cluster is named after its most common narrative |
| Nominal posting | TF-IDF + **Multinomial Naive Bayes** | Keyword rules seed the training labels; the trained classifier then posts *every* line, including narratives the rules never saw. Cross-validated accuracy is printed |
| Review flags | **IsolationForest** | Scores amount, day of month, direction and stream frequency to flag one-off / unusual items for a second look |

The keyword rules in `RULES` are only training seeds — extend them to add
nominal codes (repairs, service charge, VAT, etc.) and the classifier picks up
the new category automatically.

## Output

The run ends by opening a **desktop summary window** with the headline figures, a
**Charts** tab (cash in vs cash out by month, running cash position, cash out by
category, and an income-to-profit bridge), and five table tabs: processes,
accumulated totals by company, profit and loss, month by month, and items flagged
for review. Close the window to end the run, or use the button in
it to open the HTML report in a browser.

Before that it prints a consolidated **summary table** to the terminal: every cash
in / cash out process with its frequency and total, the net profit or loss, and the
accumulated position with each company.

Add `--no-window` to skip the window and just print (useful for scripting):

```bash
python cashflow_ml.py --no-window
```

The window uses tkinter, which ships with Python on Windows and macOS. On Linux you
may need `sudo apt install python3-tk`; without it the script says so and carries on.

## Files (`output/`)

- **`summary.html`** — one-page summary: headline figures, cash-basis profit and loss,
  every cash in / cash out process, accumulated total per company, month by month,
  and the items flagged for review. Open it in any browser; it prints to PDF cleanly.
- `categorised_transactions.csv` — every line with signed amount, stream, category, unusual flag
- `monthly_cashflow.csv` — cash in, cash out, net movement, cumulative balance movement
- `category_summary.csv` — totals and % of direction per nominal category
- `counterparty_summary.csv` — accumulated total, average, share and date range per company
- `process_summary.csv` — each recurring process with its frequency and value
- `profit_and_loss.csv` — the cash-basis income statement
- `charts.png` — the four charts at print resolution

The profit figure is **cash basis** — receipts and payments as they cleared the bank.
It is not a statutory profit: no accruals, prepayments, depreciation or tax.

## Result on `data/bank_company.csv` (01/04/2025 – 05/03/2026, 39 transactions)

- Cash in **£38,400.00** — a single stream: commercial rent on COMM-04, £3,200/month × 12, Kestrel Trading Ltd
- Cash out **£32,922.00** — mortgage interest £17,400 (52.9%), directors' remuneration £9,100 (27.6%),
  managing agent £3,072 (9.3%), accountancy £2,100 (6.4%), insurance £1,250 (3.8%)
- Net cash generated **£5,478.00** — 14.3% of turnover retained, 85.7% cost ratio
- Two deficit months: June 2025 (−£7,606, payroll) and February 2026 (−£606, accountancy fee)
- All 39 transactions carry a document reference
