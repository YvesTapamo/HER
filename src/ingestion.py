"""Country adapters: raw source records -> one harmonised record contract."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

from .xlsx_reader import read_workbook, table_records


@dataclass
class HarmonizedRecord:
    country_code: str
    source_record_id: str
    source_locator: str
    posting_date: str | None
    fiscal_year: str | None
    entity_code: str | None
    entity_name: str | None
    account_code: str | None
    description: str | None
    supplier: str | None
    amount_original: Decimal | None
    currency: str
    payment_method: str | None
    raw: dict[str, Any]
    parent_source_record_id: str | None = None
    issues: list[tuple[str, str, str]] = field(default_factory=list)


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def _date(value: Any, formats: tuple[str, ...]) -> tuple[str | None, list[tuple[str, str, str]]]:
    text = _clean(value)
    if not text:
        return None, [("error", "MISSING_DATE", "Posting date is missing")]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date().isoformat(), []
        except ValueError:
            pass
    return None, [("error", "INVALID_DATE", f"Could not parse date: {text}")]


def _amount(value: Any, decimal_comma: bool = False) -> Decimal | None:
    if value is None or str(value).strip() == "":
        return None
    text = re.sub(r"(?i)\s*(fcfa|xof|kes|rwf|usd)\s*", "", str(value)).strip()
    # Some CSV values contain quote characters as data, not CSV delimiters.
    text = text.strip('"').strip("'")
    text = text.replace("\u00a0", "").replace(" ", "")
    if decimal_comma and re.fullmatch(r"-?\d+,\d{2}", text):
        text = text.replace(",", ".")
    else:
        text = text.replace(",", "")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def country_a(path: Path) -> list[HarmonizedRecord]:
    result = []
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row_number, raw in enumerate(csv.DictReader(stream), start=2):
            date, issues = _date(raw.get("DATE"), ("%d/%m/%Y",))
            amount = _amount(raw.get("AMOUNT_KES"))
            if amount is None:
                issues.append(("error", "MISSING_OR_INVALID_AMOUNT", "Amount is missing or invalid"))
            elif amount < 0:
                issues.append(("warning", "NEGATIVE_AMOUNT", "Negative value may be a reversal or correction"))
            if raw.get("AMOUNT_KES") and ('"' in raw["AMOUNT_KES"] or "," in raw["AMOUNT_KES"]):
                issues.append(("info", "NORMALIZED_AMOUNT_FORMAT", "Removed source quote/thousands formatting"))
            result.append(HarmonizedRecord(
                "CTA", raw.get("TXN_ID", ""), f"CSV row {row_number}", date, "FY2023/24",
                _clean(raw.get("MINISTRY_CODE")), _clean(raw.get("MINISTRY_NAME")),
                _clean(raw.get("ACCOUNT_CODE")), _clean(raw.get("DESCRIPTION")),
                _clean(raw.get("VENDOR")), amount, "KES", _clean(raw.get("PAYMENT_METHOD")), raw,
                issues=issues,
            ))
    _flag_duplicates(result)
    return result


def country_b(path: Path) -> tuple[list[HarmonizedRecord], list[tuple[str, str]]]:
    workbook = read_workbook(path)
    accounts = [(row.get("code_budgetaire", ""), row.get("libelle", ""))
                for row in table_records(workbook["Plan_comptable"], 0)]
    result = []
    for row_number, raw in enumerate(table_records(workbook["Depenses"], 6), start=8):
        date, issues = _date(raw.get("date_ecriture"), ("%d-%m-%Y", "%Y-%m-%d"))
        amount = _amount(raw.get("montant_XOF"), decimal_comma=True)
        if amount is None:
            issues.append(("error", "MISSING_OR_INVALID_AMOUNT", "Amount is missing or invalid"))
        elif amount < 0:
            issues.append(("warning", "NEGATIVE_AMOUNT", "Negative value may be a reversal or correction"))
        result.append(HarmonizedRecord(
            "CTB", raw.get("id_transaction", ""), f"Depenses!row {row_number}", date, "FY2023/24",
            _clean(raw.get("ministere_code")), _clean(raw.get("ministere_nom")),
            _clean(raw.get("code_budgetaire")), _clean(raw.get("libelle")),
            _clean(raw.get("tiers")), amount, "XOF", None, raw, issues=issues,
        ))
    _flag_duplicates(result)
    return result, accounts


def country_c(path: Path) -> list[HarmonizedRecord]:
    document = json.loads(path.read_text(encoding="utf-8"))
    result = []
    for index, raw in enumerate(document["transactions"]):
        base_locator = f"$.transactions[{index}]"
        children = raw.get("subTransactions") or []
        targets: Iterable[tuple[dict[str, Any], str, str | None]]
        if children:
            targets = [(child, f"{base_locator}.subTransactions[{child_index}]", raw.get("transactionId"))
                       for child_index, child in enumerate(children)]
        else:
            targets = [(raw, base_locator, None)]
        split_total = sum((_amount(child.get("amount")) or Decimal(0)) for child in children)
        parent_amount = _amount(raw.get("amount"))
        split_mismatch = bool(children and parent_amount is not None and abs(split_total - parent_amount) > Decimal("0.02"))
        for item, locator, parent_id in targets:
            date, issues = _date(raw.get("postingDate"), ("%Y-%m-%d",))
            amount = _amount(item.get("amount"))
            if amount is None:
                issues.append(("error", "MISSING_OR_INVALID_AMOUNT", "Amount is missing or invalid"))
            if not _clean(item.get("description", raw.get("description"))):
                issues.append(("warning", "MISSING_DESCRIPTION", "Description is missing; account mapping only"))
            if raw.get("currency") != document["metadata"].get("primaryCurrency"):
                issues.append(("warning", "NON_PRIMARY_CURRENCY", "No FX conversion applied; totals stay currency-specific"))
            if split_mismatch:
                issues.append(("warning", "SUBTRANSACTION_MISMATCH", "Children do not sum to parent amount"))
            result.append(HarmonizedRecord(
                "CTC", str(item.get("subId") or raw.get("transactionId") or ""), locator,
                date, _clean(raw.get("fiscalYear")), _clean(raw.get("ministryCode")),
                _clean(raw.get("ministryName")), _clean(raw.get("coaCode")),
                _clean(item.get("description", raw.get("description"))), _clean(raw.get("supplier")),
                amount, _clean(raw.get("currency")) or "RWF", None, raw, parent_id, issues,
            ))
    _flag_duplicates(result)
    return result


def _flag_duplicates(records: list[HarmonizedRecord]) -> None:
    counts: dict[str, int] = {}
    for record in records:
        counts[record.source_record_id] = counts.get(record.source_record_id, 0) + 1
    for record in records:
        if counts.get(record.source_record_id, 0) > 1:
            record.issues.append(("warning", "DUPLICATE_SOURCE_ID", "Source transaction ID is duplicated"))
