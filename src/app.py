"""FastAPI analyst interface and JSON API."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("HEALTH_EXPENDITURE_DB", PROJECT_ROOT / "data" / "prototype.db"))

app = FastAPI(title="Health Expenditure Review", version="0.1.0")
app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "src" / "static"), name="static")


def db() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise HTTPException(503, "Database not built. Run: python -m src.pipeline")
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def rows(cursor: sqlite3.Cursor) -> list[dict]:
    return [dict(row) for row in cursor.fetchall()]


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "src" / "static" / "index.html")


@app.get("/api/summary")
def summary() -> dict:
    with db() as connection:
        totals = rows(connection.execute(
            "SELECT currency, count(*) records, round(sum(amount_original),2) total FROM transactions GROUP BY currency ORDER BY currency"
        ))
        countries = rows(connection.execute(
            """SELECT c.country_code,c.country_name,count(t.id) records,
            sum(CASE WHEN t.review_status='review_required' THEN 1 ELSE 0 END) review_required
            FROM countries c LEFT JOIN transactions t USING(country_code) GROUP BY c.country_code ORDER BY c.country_code"""
        ))
        statuses = rows(connection.execute(
            "SELECT review_status,count(*) records FROM transactions GROUP BY review_status ORDER BY review_status"
        ))
        issues = rows(connection.execute(
            "SELECT issue_code,severity,count(*) records FROM quality_issues GROUP BY issue_code,severity ORDER BY records DESC"
        ))
        rejected = connection.execute("SELECT count(*) FROM rejected_records").fetchone()[0]
        return {"totals_by_currency": totals, "countries": countries, "statuses": statuses,
                "quality_issues": issues, "rejected_records": rejected}


@app.get("/api/reference")
def reference() -> dict:
    with db() as connection:
        return {
            "countries": rows(connection.execute("SELECT * FROM countries ORDER BY country_code")),
            "sha": rows(connection.execute("SELECT code,description FROM classifications WHERE scheme='SHA' ORDER BY code")),
            "srhr": rows(connection.execute("SELECT code,description FROM classifications WHERE scheme='SRHR' ORDER BY code")),
        }


@app.get("/api/transactions")
def transactions(
    country: str | None = None,
    status: str | None = None,
    sha: str | None = None,
    srhr: str | None = None,
    issue: str | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> dict:
    clauses, parameters = [], []
    if country:
        clauses.append("t.country_code=?"); parameters.append(country)
    if status:
        clauses.append("t.review_status=?"); parameters.append(status)
    if sha == "UNMAPPED":
        clauses.append("t.sha_code IS NULL")
    elif sha:
        clauses.append("t.sha_code=?"); parameters.append(sha)
    if srhr:
        clauses.append("t.srhr_code=?"); parameters.append(srhr)
    if issue:
        clauses.append("EXISTS (SELECT 1 FROM quality_issues qi WHERE qi.transaction_id=t.id AND qi.issue_code=?)")
        parameters.append(issue)
    if q:
        clauses.append("(t.source_record_id LIKE ? OR t.description LIKE ? OR t.supplier LIKE ? OR t.account_code LIKE ?)")
        pattern = f"%{q}%"; parameters.extend([pattern] * 4)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with db() as connection:
        total = connection.execute("SELECT count(*) FROM transactions t" + where, parameters).fetchone()[0]
        records = rows(connection.execute(
            """SELECT t.id,t.country_code,t.source_record_id,t.posting_date,t.entity_name,t.account_code,
            t.description,t.amount_original,t.currency,t.sha_code,t.srhr_code,t.classification_confidence,
            t.classification_method,t.review_status,
            (SELECT count(*) FROM quality_issues qi WHERE qi.transaction_id=t.id) issue_count
            FROM transactions t""" + where + " ORDER BY t.posting_date DESC,t.id DESC LIMIT ? OFFSET ?",
            [*parameters, page_size, (page - 1) * page_size],
        ))
    return {"items": records, "total": total, "page": page, "page_size": page_size}


@app.get("/api/transactions/{transaction_id}")
def transaction_detail(transaction_id: int) -> dict:
    with db() as connection:
        record = connection.execute(
            """SELECT t.*,sf.source_path,sf.sha256,sf.metadata_json,c.country_name
            FROM transactions t JOIN source_files sf ON sf.id=t.source_file_id
            JOIN countries c ON c.country_code=t.country_code WHERE t.id=?""", (transaction_id,)
        ).fetchone()
        if not record:
            raise HTTPException(404, "Transaction not found")
        item = dict(record)
        item["raw"] = json.loads(item.pop("raw_json"))
        item["source_metadata"] = json.loads(item.pop("metadata_json"))
        item["quality_issues"] = rows(connection.execute(
            "SELECT severity,issue_code,message FROM quality_issues WHERE transaction_id=? ORDER BY id", (transaction_id,)
        ))
        item["classification_history"] = rows(connection.execute(
            "SELECT * FROM classification_history WHERE transaction_id=? ORDER BY id DESC", (transaction_id,)
        ))
        return item


class Review(BaseModel):
    sha_code: str | None = None
    srhr_code: str | None = None
    action: Literal["confirm", "override"]
    analyst: str = Field(min_length=2, max_length=80)
    note: str = Field(min_length=3, max_length=500)


@app.post("/api/transactions/{transaction_id}/classification")
def review_classification(transaction_id: int, review: Review) -> dict:
    with db() as connection:
        current = connection.execute(
            "SELECT sha_code,srhr_code,review_status FROM transactions WHERE id=?", (transaction_id,)
        ).fetchone()
        if not current:
            raise HTTPException(404, "Transaction not found")
        for scheme, code in (("SHA", review.sha_code), ("SRHR", review.srhr_code)):
            if code and not connection.execute(
                "SELECT 1 FROM classifications WHERE scheme=? AND code=?", (scheme, code)
            ).fetchone():
                raise HTTPException(422, f"Unknown {scheme} code: {code}")
        status = "analyst_confirmed" if review.action == "confirm" else "analyst_overridden"
        connection.execute(
            """INSERT INTO classification_history(transaction_id,previous_sha_code,previous_srhr_code,
            new_sha_code,new_srhr_code,previous_status,new_status,analyst,note,changed_at)
            VALUES (?,?,?,?,?,?,?,?,?,datetime('now'))""",
            (transaction_id, current["sha_code"], current["srhr_code"], review.sha_code, review.srhr_code,
             current["review_status"], status, review.analyst, review.note),
        )
        connection.execute(
            """UPDATE transactions SET sha_code=?,srhr_code=?,classification_confidence=1.0,
            classification_method='analyst_review',classification_rationale=?,review_status=? WHERE id=?""",
            (review.sha_code, review.srhr_code, review.note, status, transaction_id),
        )
        connection.commit()
    return {"id": transaction_id, "review_status": status}


@app.get("/api/rejected")
def rejected(limit: int = Query(100, ge=1, le=500)) -> list[dict]:
    with db() as connection:
        return rows(connection.execute(
            """SELECT r.id,sf.country_code,sf.source_path,r.source_locator,r.source_record_id,
            r.reason_code,r.reason FROM rejected_records r JOIN source_files sf ON sf.id=r.source_file_id
            ORDER BY r.id LIMIT ?""", (limit,)
        ))
