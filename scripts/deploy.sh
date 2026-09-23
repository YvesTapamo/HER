#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is not installed. Install Docker Engine and the Compose plugin first." >&2
    exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
    echo "The Docker Compose plugin is not available." >&2
    exit 1
fi

generated_password=""
if [ ! -f .env ]; then
    if ! command -v openssl >/dev/null 2>&1; then
        echo "OpenSSL is required to generate the initial test password." >&2
        exit 1
    fi
    generated_password=$(openssl rand -hex 18)
    {
        echo "APP_BIND_ADDRESS=0.0.0.0"
        echo "APP_PORT=8000"
        echo "APP_USERNAME=reviewer"
        echo "APP_PASSWORD=$generated_password"
        echo "REBUILD_DATABASE=0"
        echo "FORWARDED_ALLOW_IPS=127.0.0.1"
    } > .env
    chmod 600 .env
fi

if grep -q 'APP_PASSWORD=CHANGE_ME_BEFORE_DEPLOYMENT' .env; then
    echo "Replace APP_PASSWORD in .env before deploying." >&2
    exit 1
fi

echo "Building and starting the prototype..."
docker compose up --detach --build --remove-orphans

container_id=$(docker compose ps --quiet app)
if [ -z "$container_id" ]; then
    echo "The application container did not start." >&2
    docker compose logs app
    exit 1
fi

attempt=0
while [ "$attempt" -lt 30 ]; do
    health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}starting{{end}}' "$container_id")
    if [ "$health" = "healthy" ]; then
        break
    fi
    if [ "$health" = "unhealthy" ]; then
        echo "The application failed its health check." >&2
        docker compose logs app
        exit 1
    fi
    attempt=$((attempt + 1))
    sleep 2
done

health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}unknown{{end}}' "$container_id")
if [ "$health" != "healthy" ]; then
    echo "Timed out waiting for the application to become healthy." >&2
    docker compose logs app
    exit 1
fi

port=$(sed -n 's/^APP_PORT=//p' .env | tail -n 1)
username=$(sed -n 's/^APP_USERNAME=//p' .env | tail -n 1)
server_address=$(hostname -I 2>/dev/null | awk '{print $1}')
server_address=${server_address:-SERVER_IP}

echo
echo "Deployment is healthy."
echo "URL: http://$server_address:${port:-8000}"
echo "Username: ${username:-reviewer}"
if [ -n "$generated_password" ]; then
    echo "Generated password: $generated_password"
    echo "Save it now; it is stored in the local .env file."
fi
echo
echo "For public internet testing, place the service behind HTTPS and restrict access with a firewall."
