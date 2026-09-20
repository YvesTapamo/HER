"""Idempotent-ish rebuild pipeline for all supplied country files."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .classifier import Classifier
from .ingestion import HarmonizedRecord, country_a, country_b, country_c


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_reference_data(connection: sqlite3.Connection, data_dir: Path) -> None:
    with (data_dir / "ref_countries.csv").open(newline="", encoding="utf-8-sig") as stream:
        connection.executemany(
            "INSERT INTO countries VALUES (:country_code,:country_name,:primary_currency,:language)",
            csv.DictReader(stream),
        )
    for scheme, filename, code_key, description_key in (
        ("SHA", "ref_sha_classification.csv", "sha_code", "sha_description"),
        ("SRHR", "ref_srhr_classification.csv", "srhr_code", "srhr_description"),
    ):
        with (data_dir / filename).open(newline="", encoding="utf-8-sig") as stream:
            connection.executemany(
                "INSERT INTO classifications(scheme,code,description,notes) VALUES (?,?,?,?)",
                [(scheme, row[code_key], row[description_key], row.get("notes")) for row in csv.DictReader(stream)],
            )


def add_source(connection: sqlite3.Connection, country: str, path: Path, metadata: dict) -> int:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    cursor = connection.execute(
        "INSERT INTO source_files(country_code,source_path,source_format,sha256,metadata_json,ingested_at) VALUES (?,?,?,?,?,?)",
        (country, path.name, path.suffix.lstrip("."), digest, json.dumps(metadata, ensure_ascii=False), utc_now()),
    )
    return cursor.lastrowid


def load_records(connection: sqlite3.Connection, source_id: int, records: list[HarmonizedRecord], classifier: Classifier) -> None:
    for record in records:
        raw_json = json.dumps(record.raw, ensure_ascii=False, default=str)
        if record.amount_original is None:
            connection.execute(
                "INSERT INTO rejected_records(source_file_id,source_locator,source_record_id,reason_code,reason,raw_json,rejected_at) VALUES (?,?,?,?,?,?,?)",
                (source_id, record.source_locator, record.source_record_id, "MISSING_OR_INVALID_AMOUNT",
                 "A transaction cannot be aggregated without a valid amount", raw_json, utc_now()),
            )
            continue
        classification = classifier.classify(record.country_code, record.account_code or "", record.description)
        cursor = connection.execute(
            """INSERT INTO transactions(
            country_code,source_file_id,source_record_id,parent_source_record_id,source_locator,
            posting_date,fiscal_year,entity_code,entity_name,account_code,description,supplier,
            amount_original,currency,payment_method,sha_code,srhr_code,classification_confidence,
            classification_method,classification_rationale,review_status,raw_json,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (record.country_code, source_id, record.source_record_id, record.parent_source_record_id,
             record.source_locator, record.posting_date, record.fiscal_year, record.entity_code,
             record.entity_name, record.account_code, record.description, record.supplier,
             str(record.amount_original), record.currency, record.payment_method, classification.sha_code,
             classification.srhr_code, classification.confidence, classification.method,
             classification.rationale, classification.review_status, raw_json, utc_now()),
        )
        for severity, issue_code, message in record.issues:
            connection.execute(
                "INSERT INTO quality_issues(transaction_id,source_file_id,source_locator,severity,issue_code,message) VALUES (?,?,?,?,?,?)",
                (cursor.lastrowid, source_id, record.source_locator, severity, issue_code, message),
            )


def build_database(data_dir: Path, db_path: Path) -> dict[str, int]:
    project_root = Path(__file__).resolve().parents[1]
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    connection = sqlite3.connect(db_path)
    try:
        connection.executescript((project_root / "schema.sql").read_text(encoding="utf-8"))
        load_reference_data(connection, data_dir)
        classifier = Classifier(project_root / "config" / "classification_rules.json")

        a_path = data_dir / "country_a_expenditure.csv"
        a_id = add_source(connection, "CTA", a_path, {"adapter": "country_a_csv", "fiscalYear": "FY2023/24"})
        a_records = country_a(a_path)
        load_records(connection, a_id, a_records, classifier)

        b_path = data_dir / "country_b_depenses.xlsx"
        b_id = add_source(connection, "CTB", b_path, {"adapter": "country_b_xlsx", "sheet": "Depenses", "fiscalYear": "FY2023/24"})
        b_records, b_accounts = country_b(b_path)
        connection.executemany("INSERT INTO chart_of_accounts VALUES ('CTB',?,?,?)",
                               [(code, description, "Plan_comptable sheet") for code, description in b_accounts])
        load_records(connection, b_id, b_records, classifier)

        c_path = data_dir / "country_c_expenditure.json"
        c_doc = json.loads(c_path.read_text(encoding="utf-8"))
        c_id = add_source(connection, "CTC", c_path, c_doc.get("metadata", {}))
        c_records = country_c(c_path)
        load_records(connection, c_id, c_records, classifier)

        for country, records in (("CTA", a_records), ("CTB", b_records), ("CTC", c_records)):
            accounts = {}
            for record in records:
                if record.account_code and record.account_code not in accounts:
                    accounts[record.account_code] = record.description
            connection.executemany(
                "INSERT OR IGNORE INTO chart_of_accounts VALUES (?,?,?,?)",
                [(country, code, description, "observed in expenditure extract") for code, description in accounts.items()],
            )
        connection.commit()
        return {
            "transactions": connection.execute("SELECT count(*) FROM transactions").fetchone()[0],
            "rejected": connection.execute("SELECT count(*) FROM rejected_records").fetchone()[0],
            "issues": connection.execute("SELECT count(*) FROM quality_issues").fetchone()[0],
            "review_required": connection.execute("SELECT count(*) FROM transactions WHERE review_status='review_required'").fetchone()[0],
        }
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the harmonised expenditure database")
    parser.add_argument("--data-dir", type=Path, default=Path("../candidate_data"))
    parser.add_argument("--db", type=Path, default=Path("data/prototype.db"))
    args = parser.parse_args()
    print(json.dumps(build_database(args.data_dir.resolve(), args.db.resolve()), indent=2))


if __name__ == "__main__":
    main()
