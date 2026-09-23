#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"

case "${1:-}" in
    start)   docker compose up --detach ;;
    stop)    docker compose stop ;;
    restart) docker compose restart app ;;
    status)  docker compose ps ;;
    logs)    docker compose logs --follow --tail=200 app ;;
    update)  docker compose up --detach --build --remove-orphans ;;
    backup)
        destination="${2:-backup-$(date -u +%Y%m%dT%H%M%SZ).db}"
        container_id=$(docker compose ps --all --quiet app)
        [ -n "$container_id" ] || { echo "Application container does not exist" >&2; exit 1; }
        docker cp "$container_id:/app/data/prototype.db" "$destination"
        echo "Database copied to $destination"
        ;;
    rebuild-data)
        echo "Stopping the application for an atomic database rebuild..."
        docker compose stop app
        if docker compose run --rm --no-deps \
            -e REBUILD_DATABASE=1 \
            -e INITIALIZE_ONLY=1 \
            app; then
            docker compose up --detach app
            echo "Database rebuilt; the previous database remains backed up in the Docker volume."
        else
            echo "Database rebuild failed; restarting with the previous database." >&2
            docker compose up --detach app
            exit 1
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|update|backup [FILE]|rebuild-data}" >&2
        exit 1
        ;;
esac
