#!/usr/bin/env bash
set -euo pipefail

# Wait for PostgreSQL to accept connections (only when a DATABASE_URL is set).
# pg_isready comes from postgresql-client in the Dockerfile; if it is somehow
# missing, say so instead of silently burning the whole retry budget.
if [ -n "${DATABASE_URL:-}" ]; then
    if command -v pg_isready >/dev/null; then
        echo "Waiting for PostgreSQL..."
        RETRIES=30
        until pg_isready --dbname="$DATABASE_URL" >/dev/null 2>&1 || [ "$RETRIES" -eq 0 ]; do
            sleep 2
            RETRIES=$((RETRIES - 1))
        done
        if [ "$RETRIES" -eq 0 ]; then
            echo "Warning: PostgreSQL not reachable after 60s, starting anyway..."
        fi
    else
        echo "Warning: pg_isready not installed; skipping the DB readiness wait"
    fi
fi

# Create tables if the project exposes SQLAlchemy metadata (MVP-style schema management).
if python -c "from models import Base" 2>/dev/null; then
    echo "Creating database tables..."
    python -c "
from database import engine
from models import Base
Base.metadata.create_all(bind=engine)
print('Tables ready')
"
fi

# Worker count: Render's free/starter instances have 512 MB; four Python workers
# each holding SQLAlchemy + Pydantic comfortably exceed that. Default to 2 and
# let WEB_CONCURRENCY (the gunicorn convention) override.
echo "Starting server..."
exec gunicorn -k uvicorn.workers.UvicornWorker \
    -b "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --max-requests 1200 --max-requests-jitter 100 \
    --access-logfile - \
    main:app
