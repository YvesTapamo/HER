PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS countries (
    country_code TEXT PRIMARY KEY,
    country_name TEXT NOT NULL,
    primary_currency TEXT NOT NULL,
    language TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS classifications (
    scheme TEXT NOT NULL CHECK (scheme IN ('SHA', 'SRHR')),
    code TEXT NOT NULL,
    description TEXT NOT NULL,
    notes TEXT,
    PRIMARY KEY (scheme, code)
);

CREATE TABLE IF NOT EXISTS source_files (
    id INTEGER PRIMARY KEY,
    country_code TEXT NOT NULL REFERENCES countries(country_code),
    source_path TEXT NOT NULL,
    source_format TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    UNIQUE(country_code, sha256)
);

CREATE TABLE IF NOT EXISTS chart_of_accounts (
    country_code TEXT NOT NULL REFERENCES countries(country_code),
    account_code TEXT NOT NULL,
    account_description TEXT,
    source TEXT NOT NULL,
    PRIMARY KEY (country_code, account_code)
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,
    country_code TEXT NOT NULL REFERENCES countries(country_code),
    source_file_id INTEGER NOT NULL REFERENCES source_files(id),
    source_record_id TEXT NOT NULL,
    parent_source_record_id TEXT,
    source_locator TEXT NOT NULL,
    posting_date TEXT,
    fiscal_year TEXT,
    entity_code TEXT,
    entity_name TEXT,
    account_code TEXT,
    description TEXT,
    supplier TEXT,
    amount_original NUMERIC NOT NULL,
    currency TEXT NOT NULL,
    payment_method TEXT,
    sha_code TEXT,
    srhr_code TEXT,
    classification_confidence REAL NOT NULL,
    classification_method TEXT NOT NULL,
    classification_rationale TEXT NOT NULL,
    review_status TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_transactions_country ON transactions(country_code);
CREATE INDEX IF NOT EXISTS ix_transactions_review ON transactions(review_status);
CREATE INDEX IF NOT EXISTS ix_transactions_sha ON transactions(sha_code);
CREATE INDEX IF NOT EXISTS ix_transactions_srhr ON transactions(srhr_code);
CREATE INDEX IF NOT EXISTS ix_transactions_source_id ON transactions(source_record_id);

CREATE TABLE IF NOT EXISTS quality_issues (
    id INTEGER PRIMARY KEY,
    transaction_id INTEGER REFERENCES transactions(id),
    source_file_id INTEGER NOT NULL REFERENCES source_files(id),
    source_locator TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'error')),
    issue_code TEXT NOT NULL,
    message TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_quality_transaction ON quality_issues(transaction_id);
CREATE INDEX IF NOT EXISTS ix_quality_code ON quality_issues(issue_code);

CREATE TABLE IF NOT EXISTS rejected_records (
    id INTEGER PRIMARY KEY,
    source_file_id INTEGER NOT NULL REFERENCES source_files(id),
    source_locator TEXT NOT NULL,
    source_record_id TEXT,
    reason_code TEXT NOT NULL,
    reason TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    rejected_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS classification_history (
    id INTEGER PRIMARY KEY,
    transaction_id INTEGER NOT NULL REFERENCES transactions(id),
    previous_sha_code TEXT,
    previous_srhr_code TEXT,
    new_sha_code TEXT,
    new_srhr_code TEXT,
    previous_status TEXT NOT NULL,
    new_status TEXT NOT NULL,
    analyst TEXT NOT NULL,
    note TEXT NOT NULL,
    changed_at TEXT NOT NULL
);

