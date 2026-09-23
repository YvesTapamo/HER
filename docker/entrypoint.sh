#!/bin/sh
set -eu

database_path="${HEALTH_EXPENDITURE_DB:-/app/data/prototype.db}"
source_data_dir="${SOURCE_DATA_DIR:-/app/candidate_data}"
rebuild_database="${REBUILD_DATABASE:-0}"

mkdir -p "$(dirname "$database_path")"

if [ "$rebuild_database" = "1" ] || [ ! -s "$database_path" ]; then
    if [ -s "$database_path" ]; then
        backup_path="${database_path}.backup-$(date -u +%Y%m%dT%H%M%SZ)"
        cp "$database_path" "$backup_path"
        echo "Existing database backed up to $backup_path"
    fi

    building_path="${database_path}.building"
    rm -f "$building_path"
    echo "Building harmonised database from $source_data_dir"
    python -m src.pipeline --data-dir "$source_data_dir" --db "$building_path"
    mv "$building_path" "$database_path"
fi

if [ "${INITIALIZE_ONLY:-0}" = "1" ]; then
    echo "Database initialization complete"
    exit 0
fi

exec uvicorn src.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --proxy-headers \
    --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}"
