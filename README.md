# Regional health expenditure harmonisation prototype

A small, explainable prototype that ingests the three supplied country extracts, harmonises them into one auditable model, classifies expenditures against the supplied SHA/SRHR references, flags uncertainty and gives analysts a review interface.

## Run it

Prerequisites: Python 3.10+.

```bash
cd HER
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.pipeline --data-dir candidate_data --db data/prototype.db
uvicorn src.app:app --reload
```

Open <http://127.0.0.1:8000>. API documentation is at <http://127.0.0.1:8000/docs>.

The assessment environment already contains compatible FastAPI/Uvicorn versions. The XLSX adapter uses Python's standard library, so no Excel installation or `openpyxl` dependency is required.

Run the tests:

```bash
python -m unittest discover -s tests -v
```

## Deploy on a Linux server with Docker Compose

Prerequisites: Docker Engine, the Docker Compose v2 plugin, Git, and OpenSSL. The deployment uses the bundled synthetic assessment data only.

```bash
git clone https://github.com/JanvierAkowo/HER.git
cd HER
./scripts/deploy.sh
```

On first run the script:

1. creates a local `.env` file with a random HTTP Basic Auth password;
2. builds the application image;
3. creates a persistent Docker volume;
4. builds the SQLite database from `candidate_data` when the volume is empty;
5. waits for the application health check; and
6. prints the URL and generated login credentials.

Allow the configured port (8000 by default) through the server firewall or cloud security group. Open `http://SERVER_IP:8000` and enter the generated username and password. For testing over the public internet, put the application behind an HTTPS reverse proxy; Basic Auth must not be sent over unencrypted public networks.

Common server operations:

```bash
./scripts/manage.sh status
./scripts/manage.sh logs
./scripts/manage.sh restart
./scripts/manage.sh update
./scripts/manage.sh backup
./scripts/manage.sh rebuild-data
./scripts/manage.sh stop
```

Configuration lives in the ignored `.env` file. See [.env.example](.env.example) for port, bind address, credentials, database rebuild and trusted-proxy settings. Analyst reviews persist in the named `health_expenditure_data` volume when containers are rebuilt or restarted.

To update the server:

```bash
git pull
./scripts/manage.sh update
```

To intentionally recreate the database from the source files, run `./scripts/manage.sh rebuild-data`. The command stops the application, creates a timestamped backup inside the Docker volume, builds the replacement atomically, and starts the normal service again. This intentionally replaces analyst changes in the active database.

## What is implemented

- CSV, multi-sheet XLSX and nested JSON adapters behind one harmonised record contract.
- A reproducible SQLite build with supplied references, per-country charts of accounts, harmonised transactions, issues, rejected records and classification audit history.
- Configurable country/account rules plus a conservative keyword fallback. Confidence below 85%, ambiguity and unmapped records enter the review queue.
- Lowest-grain handling for JSON sub-transactions without also loading their parents.
- Source traceability through filename, source locator, parent/source IDs, SHA-256 checksum, source metadata and preserved raw JSON.
- Analyst dashboard with totals by currency, search/filtering, rejected-record quarantine, transaction detail, quality issues, original record and auditable confirm/override actions.

The committed `data/prototype.db` is a convenience demo build. Re-running the pipeline replaces it deterministically from the supplied source files.

## Key decisions

The stack is Python + FastAPI + SQLite + plain browser JavaScript. It is small enough to understand during a 15-minute demonstration, runs locally, and cleanly separates adapters, quality checks, classification, storage and presentation. SQLite is appropriate for a single-user assessment prototype; its SQL schema makes a later move to PostgreSQL straightforward.

Classification is deliberately deterministic and reviewable. Country-specific account codes are the strongest supplied signal, so exact mappings live in [classification_rules.json](config/classification_rules.json). Text fallback is lower-confidence and never auto-accepted. Generic salaries, office costs, travel and construction are not forced into a functional category when the simplified reference cannot justify one.

Amounts remain in original currency. No exchange-rate dataset was supplied, so adding KES, XOF, RWF and USD would create a plausible-looking but invalid number.

See [architecture.md](docs/architecture.md), [data_profile.md](docs/data_profile.md), and the executable [schema.sql](schema.sql).

## Demonstration path (about 6 minutes)

1. Show totals by currency and the review queue.
2. Filter to `Unmapped` and explain why uncertainty is retained.
3. Open a transaction to show source locator, checksum, raw JSON and rule rationale.
4. Filter Country C and discuss child expansion / multi-currency handling.
5. Open the rejected-record quarantine and explain why those items do not enter totals.
6. Open a flagged negative or missing-description record.
7. Confirm or override one classification and show its audit history.

## Assumptions

- Country A's July 2023–June 2024 extract and Country B's labelled 2023–2024 extract are represented as `FY2023/24`.
- Country C child records are the analytical grain when present; loading both parent and children would double-count expenditure.
- A maximum child/parent variance of 0.02 is allowed for rounding.
- SHA functional classification and SRHR tagging are independent labels.
- The supplied classification lists are authoritative for this exercise; mappings themselves require subject-matter-expert approval.

## Production hardening

Before production use: PostgreSQL/object storage; immutable landing zone; schema/version registry; orchestrated incremental loads and idempotency keys; reconciliation controls; effective-dated mapping governance with two-person approval; currency/rate policy; authentication and role-based access; encryption and secrets management; structured observability; backups/disaster recovery; accessibility/security testing; and broader automated contract, migration, reconciliation and performance tests. Personally identifiable or sensitive vendor data would require a formal privacy review.

## Repository layout

```text
HER/
├── Dockerfile
├── compose.yaml
├── docker/entrypoint.sh
├── scripts/{deploy.sh,manage.sh}
├── config/classification_rules.json
├── candidate_data/
├── data/prototype.db
├── docs/{architecture.md,data_profile.md}
├── src/{ingestion.py,xlsx_reader.py,classifier.py,pipeline.py,app.py}
├── tests/test_prototype.py
├── schema.sql
└── requirements.txt
```

## AI-assisted development disclosure

I designed the solution and leveraged OpenAI Codex to analyze the synthetic inputs and assist with the implementation