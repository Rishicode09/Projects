"""Import bank and transaction data from CSV exports.

Bank exports are inconsistent: some use one signed amount column, some use
separate paid-in and paid-out columns, some put the balance first. This module
normalises them into :class:`Transaction` objects and, critically, refuses to
silently import the same statement twice.

Double-counting income through a repeated import is one of the most common
causes of an overstated tax bill. The fingerprint check makes it structurally
impossible rather than something to remember.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from .model import Transaction, _parse_date
from .money import Money

# Column aliases seen across common UK bank and accounting exports.
COLUMN_ALIASES: Dict[str, List[str]] = {
    "date": ["date", "transaction date", "txn date", "posted", "value date", "date posted"],
    "description": [
        "description", "narrative", "details", "reference", "transaction description",
        "memo", "particulars",
    ],
    "amount": ["amount", "value", "transaction amount", "amt"],
    "paid_in": ["paid in", "credit", "money in", "receipts", "in", "credit amount"],
    "paid_out": ["paid out", "debit", "money out", "payments", "out", "debit amount"],
    "counterparty": ["counterparty", "payee", "merchant", "name", "supplier", "customer"],
    "account": ["account", "account name", "account number", "bank account"],
    "balance": ["balance", "running balance"],
    "property": ["property", "property id", "property_ref", "unit"],
    "document": ["document", "invoice", "invoice number", "receipt", "document_ref"],
    "vat": ["vat", "vat amount", "tax"],
}


@dataclass
class ImportResult:
    """What an import actually did -- including what it refused to do."""

    transactions: List[Transaction] = field(default_factory=list)
    duplicates: List[Transaction] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    source_file: str = ""
    rows_read: int = 0

    @property
    def imported_count(self) -> int:
        return len(self.transactions)

    def summary(self) -> str:
        lines = [
            f"Import: {self.source_file}",
            f"  rows read:  {self.rows_read}",
            f"  imported:   {self.imported_count}",
            f"  duplicates: {len(self.duplicates)} (skipped)",
            f"  errors:     {len(self.errors)}",
        ]
        if self.duplicates:
            lines.append(
                "  Duplicates were skipped because an identical date, account, "
                "amount and description already exists. If a genuine repeat "
                "payment was skipped, add a distinguishing reference and re-import."
            )
        for err in self.errors[:10]:
            lines.append(f"    ! {err}")
        if len(self.errors) > 10:
            lines.append(f"    ... and {len(self.errors) - 10} more")
        return "\n".join(lines)


def _normalise_header(header: Iterable[str]) -> Dict[str, int]:
    """Map a CSV header row onto known field names."""
    mapping: Dict[str, int] = {}
    for index, raw in enumerate(header):
        key = raw.strip().lower().replace("_", " ")
        for field_name, aliases in COLUMN_ALIASES.items():
            if key in aliases and field_name not in mapping:
                mapping[field_name] = index
    return mapping


def import_csv(
    path: str,
    entity_id: str,
    account: str = "",
    known_fingerprints: Optional[Set[str]] = None,
    currency: str = "GBP",
) -> ImportResult:
    """Import one CSV file of bank or transaction data.

    ``known_fingerprints`` lets the caller carry forward everything already in
    the books, so re-importing an overlapping statement is safe.
    """
    result = ImportResult(source_file=str(path))
    seen: Set[str] = set(known_fingerprints or set())
    file_path = Path(path)

    if not file_path.exists():
        result.errors.append(f"file not found: {path}")
        return result

    with file_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            result.errors.append("file is empty")
            return result

        columns = _normalise_header(header)
        missing = [f for f in ("date", "description") if f not in columns]
        if missing:
            result.errors.append(
                f"could not find column(s) {missing} in header {header}. "
                f"Recognised columns: {sorted(columns)}"
            )
            return result
        if "amount" not in columns and not (
            "paid_in" in columns or "paid_out" in columns
        ):
            result.errors.append(
                "no amount column found; expected either 'amount' or "
                "'paid in'/'paid out'"
            )
            return result

        for row_number, row in enumerate(reader, start=2):
            if not any(cell.strip() for cell in row):
                continue
            result.rows_read += 1
            try:
                txn = _build_transaction(
                    row, columns, entity_id, account, currency,
                    source_ref=f"{file_path.name}:{row_number}",
                )
            except Exception as exc:  # noqa: BLE001 - report, do not abort the file
                result.errors.append(f"row {row_number}: {exc}")
                continue

            fingerprint = txn.fingerprint()
            if fingerprint in seen:
                result.duplicates.append(txn)
                continue
            seen.add(fingerprint)
            result.transactions.append(txn)

    return result


def _cell(row: List[str], columns: Dict[str, int], key: str) -> str:
    index = columns.get(key)
    if index is None or index >= len(row):
        return ""
    return row[index].strip()


def _build_transaction(
    row: List[str],
    columns: Dict[str, int],
    entity_id: str,
    account: str,
    currency: str,
    source_ref: str,
) -> Transaction:
    txn_date = _parse_date(_cell(row, columns, "date"))
    if txn_date is None:
        raise ValueError("missing date")

    description = _cell(row, columns, "description")
    if not description:
        raise ValueError("missing description - an unlabelled entry cannot be evidenced")

    if "amount" in columns:
        amount = Money.parse(_cell(row, columns, "amount"), currency)
    else:
        paid_in = Money.parse(_cell(row, columns, "paid_in") or "0", currency)
        paid_out = Money.parse(_cell(row, columns, "paid_out") or "0", currency)
        if not paid_in.is_zero and not paid_out.is_zero:
            raise ValueError("row has both a paid-in and a paid-out amount")
        amount = paid_in - abs(paid_out)

    if amount.is_zero:
        raise ValueError("zero amount")

    return Transaction(
        date=txn_date,
        description=description,
        amount=amount,
        entity_id=entity_id,
        account=_cell(row, columns, "account") or account,
        counterparty=_cell(row, columns, "counterparty"),
        property_id=_cell(row, columns, "property") or None,
        document_ref=_cell(row, columns, "document"),
        vat_amount=Money.parse(_cell(row, columns, "vat") or "0", currency),
        source_ref=source_ref,
    )


def import_many(
    specs: List[Dict],
    currency: str = "GBP",
) -> ImportResult:
    """Import several files, carrying fingerprints across all of them.

    Each spec is ``{"path": ..., "entity_id": ..., "account": ...}``. Running
    them together means a payment appearing in two overlapping exports is
    imported once.
    """
    combined = ImportResult(source_file=f"{len(specs)} file(s)")
    seen: Set[str] = set()
    for spec in specs:
        result = import_csv(
            spec["path"],
            entity_id=spec["entity_id"],
            account=spec.get("account", ""),
            known_fingerprints=seen,
            currency=currency,
        )
        combined.transactions.extend(result.transactions)
        combined.duplicates.extend(result.duplicates)
        combined.errors.extend(f"{Path(spec['path']).name}: {e}" for e in result.errors)
        combined.rows_read += result.rows_read
        seen.update(t.fingerprint() for t in result.transactions)
    return combined
