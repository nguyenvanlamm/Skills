#!/usr/bin/env bash
set -euo pipefail

# Wait for PostgreSQL to be ready (if DATABASE_URL is set)
if [ -n "${DATABASE_URL:-}" ]; then
    echo "Waiting for PostgreSQL..."
    RETRIES=30
    until pg_isready --dbname="$DATABASE_URL" 2>/dev/null || [ "$RETRIES" -eq 0 ]; do
        sleep 2
        RETRIES=$((RETRIES - 1))
    done
    if [ "$RETRIES" -eq 0 ]; then
        echo "Warning: PostgreSQL not reachable, continuing anyway..."
    fi
fi

# Auto-create database tables (if models/Base exists)
if python -c "from models import Base" 2>/dev/null; then
    echo "Creating database tables..."
    python -c "
from database import engine
from models import Base
Base.metadata.create_all(bind=engine)
print('Tables created successfully')
"
fi

# Start server
echo "Starting server..."
exec gunicorn -k uvicorn.workers.UvicornWorker \
    -b "0.0.0.0:${PORT:-8000}" \
    --workers 4 \
    --max-requests 1200 \
    --access-logfile - \
    main:app
