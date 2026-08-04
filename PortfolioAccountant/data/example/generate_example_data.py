"""Generate the worked example dataset.

The data is deterministic (fixed seed) so the demo output is reproducible and
the test suite can assert on it.

It deliberately contains problems, because a demo where everything is clean
teaches nothing. Planted in the data are: a duplicated contractor payment, a
run of payments with no invoice reference, cash deposits, payments to a related
party, a property with missing rent months, and a supplier paid repeatedly in
identical round sums with no documentation. Each is the kind of thing that is
usually innocent and occasionally is not -- which is exactly why they have to
be asked about rather than assumed either way.

    python3 data/example/generate_example_data.py
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = 20260406

PROPERTIES = [
    # id,      rent,  agent%, mortgage interest/month, insurance/yr
    ("FLAT-01", 1250, 0.10, 520, 340),
    ("FLAT-02", 975, 0.10, 410, 295),
    ("HOUSE-03", 1850, 0.12, 780, 520),
]

COMPANY_PROPERTY = ("COMM-04", 3200, 0.08, 1450, 1250)

REPAIR_SUPPLIERS = [
    "PARKSIDE PLUMBING LTD",
    "J HARLAND ELECTRICAL",
    "NORTHGATE ROOFING",
    "CITY GAS SAFETY",
    "BRIGHTON DECOR CO",
]


def month_range(start: date, months: int):
    for i in range(months):
        year = start.year + (start.month - 1 + i) // 12
        month = (start.month - 1 + i) % 12 + 1
        yield date(year, month, min(start.day, 28))


def build_personal_rows(rng: random.Random):
    rows = []
    start = date(2025, 4, 6)

    for prop_id, rent, agent_rate, interest, insurance in PROPERTIES:
        # FLAT-02 has two void months -- a genuine gap the review should query.
        void_months = {6, 7} if prop_id == "FLAT-02" else set()

        for index, when in enumerate(month_range(start, 12)):
            if when.month in void_months:
                continue

            rows.append(
                {
                    "date": when.isoformat(),
                    "description": f"RENT {prop_id} TENANT PAYMENT",
                    "paid in": f"{rent:.2f}",
                    "paid out": "",
                    "counterparty": "LETTINGS CLIENT ACCOUNT",
                    "property": prop_id,
                    "document": f"RENT-{prop_id}-{when:%Y%m}",
                }
            )
            rows.append(
                {
                    "date": (when + timedelta(days=1)).isoformat(),
                    "description": f"MANAGEMENT FEE {prop_id}",
                    "paid in": "",
                    "paid out": f"{rent * agent_rate:.2f}",
                    "counterparty": "HORIZON LETTINGS LTD",
                    "property": prop_id,
                    "document": f"INV-HL-{when:%Y%m}-{prop_id}",
                }
            )
            rows.append(
                {
                    "date": (when + timedelta(days=3)).isoformat(),
                    "description": f"MORTGAGE INTEREST {prop_id}",
                    "paid in": "",
                    "paid out": f"{interest:.2f}",
                    "counterparty": "MERIDIAN BANK PLC",
                    "property": prop_id,
                    "document": f"MTG-{prop_id}-{when:%Y%m}",
                }
            )

        rows.append(
            {
                "date": date(2025, 5, 12).isoformat(),
                "description": f"BUILDINGS INSURANCE {prop_id}",
                "paid in": "",
                "paid out": f"{insurance:.2f}",
                "counterparty": "ALBION INSURANCE",
                "property": prop_id,
                "document": f"POL-{prop_id}-2025",
            }
        )

        for _ in range(rng.randint(2, 4)):
            when = date(2025, 4, 6) + timedelta(days=rng.randint(10, 350))
            supplier = rng.choice(REPAIR_SUPPLIERS)
            amount = rng.choice([87.50, 142.00, 235.75, 318.40, 76.20, 495.00, 168.90])
            rows.append(
                {
                    "date": when.isoformat(),
                    "description": f"REPAIR {prop_id} {supplier}",
                    "paid in": "",
                    "paid out": f"{amount:.2f}",
                    "counterparty": supplier,
                    "property": prop_id,
                    "document": f"INV-{rng.randint(10000, 99999)}",
                }
            )

        for month in (7, 11):
            rows.append(
                {
                    "date": date(2025, month, 18).isoformat(),
                    "description": f"GAS SAFETY CERTIFICATE {prop_id}",
                    "paid in": "",
                    "paid out": "92.00",
                    "counterparty": "CITY GAS SAFETY",
                    "property": prop_id,
                    "document": f"CP12-{prop_id}-{month}",
                }
            )

    # ---- Planted issue 1: a duplicate payment ---------------------------
    for when in (date(2025, 9, 14), date(2025, 9, 27)):
        rows.append(
            {
                "date": when.isoformat(),
                "description": "NORTHGATE ROOFING HOUSE-03 ROOF REPAIR",
                "paid in": "",
                "paid out": "2450.00",
                "counterparty": "NORTHGATE ROOFING",
                "property": "HOUSE-03",
                "document": "INV-NR-8871",
            }
        )

    # ---- Planted issue 2: round sums, no invoice reference --------------
    for month in range(5, 12):
        rows.append(
            {
                "date": date(2025, month, 22).isoformat(),
                "description": "TRANSFER MAINTENANCE SERVICES",
                "paid in": "",
                "paid out": "800.00",
                "counterparty": "PREMIER MAINTENANCE",
                "property": "",
                "document": "",
            }
        )

    # ---- Planted issue 3: cash deposits ---------------------------------
    for when, amount in (
        (date(2025, 6, 3), 450.00),
        (date(2025, 8, 19), 620.00),
        (date(2025, 11, 7), 380.00),
    ):
        rows.append(
            {
                "date": when.isoformat(),
                "description": "COUNTER CREDIT CASH",
                "paid in": f"{amount:.2f}",
                "paid out": "",
                "counterparty": "",
                "property": "",
                "document": "",
            }
        )

    # ---- Planted issue 4: related party payments ------------------------
    for month in (5, 8, 11):
        rows.append(
            {
                "date": date(2025, month, 28).isoformat(),
                "description": "PAYMENT R MEHRA CONSULTANCY",
                "paid in": "",
                "paid out": "1500.00",
                "counterparty": "R MEHRA",
                "property": "",
                "document": "",
            }
        )

    # ---- Planted issue 5: capital work described as a repair ------------
    rows.append(
        {
            "date": date(2025, 10, 9).isoformat(),
            "description": "LOFT CONVERSION HOUSE-03 STAGE 1",
            "paid in": "",
            "paid out": "18500.00",
            "counterparty": "NORTHGATE ROOFING",
            "property": "HOUSE-03",
            "document": "INV-NR-9004",
        }
    )

    # ---- Ordinary running costs -----------------------------------------
    for when in month_range(date(2025, 4, 15), 12):
        rows.append(
            {
                "date": when.isoformat(),
                "description": "ACCOUNTING SOFTWARE SUBSCRIPTION",
                "paid in": "",
                "paid out": "29.99",
                "counterparty": "LEDGERWORKS",
                "property": "",
                "document": f"SUB-{when:%Y%m}",
            }
        )

    rows.append(
        {
            "date": date(2026, 1, 20).isoformat(),
            "description": "ACCOUNTANCY FEES YEAR END",
            "paid in": "",
            "paid out": "1450.00",
            "counterparty": "WHITFIELD & CO",
            "property": "",
            "document": "INV-WC-2291",
        }
    )

    return rows


def build_company_rows(rng: random.Random):
    rows = []
    prop_id, rent, agent_rate, interest, insurance = COMPANY_PROPERTY

    for when in month_range(date(2025, 4, 1), 12):
        rows.append(
            {
                "date": when.isoformat(),
                "description": f"COMMERCIAL RENT {prop_id}",
                "paid in": f"{rent:.2f}",
                "paid out": "",
                "counterparty": "TENANT - KESTREL TRADING LTD",
                "property": prop_id,
                "document": f"RENT-{prop_id}-{when:%Y%m}",
            }
        )
        rows.append(
            {
                "date": (when + timedelta(days=2)).isoformat(),
                "description": f"COMMERCIAL MORTGAGE INTEREST {prop_id}",
                "paid in": "",
                "paid out": f"{interest:.2f}",
                "counterparty": "MERIDIAN COMMERCIAL",
                "property": prop_id,
                "document": f"CMTG-{when:%Y%m}",
            }
        )
        rows.append(
            {
                "date": (when + timedelta(days=4)).isoformat(),
                "description": f"MANAGING AGENT {prop_id}",
                "paid in": "",
                "paid out": f"{rent * agent_rate:.2f}",
                "counterparty": "HORIZON COMMERCIAL",
                "property": prop_id,
                "document": f"INV-HC-{when:%Y%m}",
            }
        )

    rows.append(
        {
            "date": date(2025, 6, 30).isoformat(),
            "description": "DIRECTORS REMUNERATION",
            "paid in": "",
            "paid out": "9100.00",
            "counterparty": "R MEHRA",
            "property": "",
            "document": "PAYROLL-2025-06",
        }
    )
    rows.append(
        {
            "date": date(2025, 7, 15).isoformat(),
            "description": "BUILDINGS INSURANCE COMMERCIAL",
            "paid in": "",
            "paid out": f"{insurance:.2f}",
            "counterparty": "ALBION INSURANCE",
            "property": prop_id,
            "document": "POL-COMM-2025",
        }
    )
    rows.append(
        {
            "date": date(2026, 2, 10).isoformat(),
            "description": "ACCOUNTANCY FEES",
            "paid in": "",
            "paid out": "2100.00",
            "counterparty": "WHITFIELD & CO",
            "property": "",
            "document": "INV-WC-2310",
        }
    )
    return rows


def write_csv(path: Path, rows) -> None:
    fieldnames = [
        "date", "description", "paid in", "paid out",
        "counterparty", "property", "document",
    ]
    rows = sorted(rows, key=lambda r: r["date"])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {path.name}")


def main() -> None:
    rng = random.Random(SEED)
    write_csv(HERE / "bank_personal.csv", build_personal_rows(rng))
    write_csv(HERE / "bank_company.csv", build_company_rows(rng))


if __name__ == "__main__":
    main()
