# Prototype presentation (10 slides)

## 1. From heterogeneous extracts to reviewable evidence

Regional health expenditure harmonisation prototype  
Technical assessment · September 2026

Speaker note: Frame the goal as trustworthy evidence, not merely file conversion.

## 2. Interpretation and design principles

- Preserve source truth and make every transformation traceable.
- Separate country-specific ingestion from the common analytical model.
- Never hide uncertainty: auto-classify only defensible mappings.
- Keep currencies separate in the absence of governed FX rates.
- Optimize the prototype for explanation, adaptation and analyst review.

## 3. Architecture and data flow

CSV / XLSX / JSON → country adapters → common contract → validation → classification → SQLite → API / analyst UI  
Invalid amounts → quarantine  
Analyst decisions → audit history

## 4. Harmonised data model and lineage

- One transaction fact grain; Country C children replace parents when supplied.
- Original amount/currency, entity, account, description, supplier and fiscal period.
- Source file, checksum, locator, source/parent IDs and preserved raw JSON.
- Separate quality issues, rejected records and classification decision history.
- Country-owned chart of accounts avoids false cross-country code equivalence.

## 5. Country-specific adaptation

- A: CSV, English headers, DD/MM/YYYY, KES, non-standard quoted amounts.
- B: XLSX, seven-row preamble, French headers, DD-MM-YYYY, XOF, embedded CoA sheet.
- C: JSON, nested sub-transactions, null descriptions, RWF + USD.
- Adding a country means one adapter, configuration, references and contract tests.

## 6. Classification with a safe failure mode

- Exact country/account rules are primary, transparent and configurable.
- Conservative normalized-text rules are fallback only.
- SHA and SRHR are independent labels; every result has method, rationale and confidence.
- Confidence ≥85% auto-classifies; everything else enters review.
- Unknown ≠ zero: unsupported assignments remain unmapped.

## 7. What profiling found

- 7,094 usable lowest-grain facts; 31 blank-amount records quarantined.
- 54 negative values retained as possible reversals and flagged.
- 13 recoverable quoted/thousands amounts normalized with audit issues.
- 216 stored Country C facts in USD; no silent FX conversion.
- 26 missing descriptions, two rows with a duplicated source ID, one missing date.

## 8. Analyst workflow demonstration

- Review currency-specific totals and workload.
- Search/filter by country, classification and review status.
- Inspect rule rationale, issues, source checksum/locator and raw record.
- Confirm or override against controlled SHA/SRHR references.
- Retain who, when, before/after values and decision note.

## 9. Technology choices and trade-offs

- Python: strong parsing/data ecosystem and clear adapter code.
- SQLite: zero-operations local demo, relational integrity and portable SQL.
- FastAPI: typed, documented API; plain JavaScript keeps the UI dependency-light.
- Standard-library XLSX reader avoids a heavy dependency for this bounded input.
- Trade-off: rebuild batch and single-user storage, intentionally not production infrastructure.

## 10. Production path and engagement model

- Governed mappings: effective dates, versioning, two-person approval and gold-set evaluation.
- PostgreSQL + immutable object landing, orchestration, idempotency and reconciliation controls.
- RBAC/SSO, encryption, privacy review, observability, backups and disaster recovery.
- Start with country technical teams to document extracts and reconcile totals.
- Work iteratively with SHA/SRHR experts: review queue → validated labels → measured rule/model improvements.

