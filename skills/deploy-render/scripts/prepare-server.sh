#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES_DIR="$(cd "$SCRIPT_DIR/../templates" && pwd)"

SERVER_DIR=""
SLUG=""
NO_DB=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --server-dir) SERVER_DIR="$2"; shift 2 ;;
    --slug) SLUG="$2"; shift 2 ;;
    --no-db) NO_DB=true; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [ -z "$SERVER_DIR" ]; then echo "❌ --server-dir required"; exit 1; fi
if [ -z "$SLUG" ]; then echo "❌ --slug required"; exit 1; fi

echo "◆ Preparing server code in $SERVER_DIR..."
cd "$SERVER_DIR"

# --- 1. Update database.py (skip if --no-db) ---
if [ "$NO_DB" = true ]; then
  echo "  ⏭  --no-db: skipping database.py update"
else
  echo "  Updating database.py for PostgreSQL..."
  if [ ! -f "database.py" ]; then
    echo "  ⚠ database.py not found, skipping PostgreSQL config"
  else
    if grep -q "DATABASE_URL" "database.py"; then
      echo "  ✓ database.py already supports DATABASE_URL"
    else
      cat > database.py <<PYEOF
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=connect_args if connect_args else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
PYEOF
      echo "  ✅ database.py updated with PostgreSQL support"
    fi
  fi
fi

# --- 2. Update main.py for table creation (skip if --no-db) ---
if [ "$NO_DB" = true ]; then
  echo "  ⏭  --no-db: skipping startup table creation"
else
  echo "  Updating main.py for auto table creation..."
  if [ ! -f "main.py" ]; then
    echo "  ⚠ main.py not found, skipping startup config"
  else
    if grep -q "startup.*create_all\|create_all.*startup\|@app.on_event.*startup\|def startup" "main.py" 2>/dev/null; then
      echo "  ✓ main.py already has startup table creation"
    else
      cat >> main.py <<PYEOF


@app.on_event("startup")
def on_startup():
    from database import engine
    from models import Base
    Base.metadata.create_all(bind=engine)
PYEOF
      echo "  ✅ Added startup table creation to main.py"
    fi
  fi
fi

# --- 3. Update requirements.txt ---
echo "  Updating requirements.txt..."
REQ_FILE="requirements.txt"
if [ ! -f "$REQ_FILE" ]; then
  echo "  ⚠ requirements.txt not found, creating..."
  echo -e "fastapi\nuvicorn\ngunicorn\nsqlalchemy\npydantic" > "$REQ_FILE"
  echo "  ✅ requirements.txt created"
else
  if ! grep -qi "^gunicorn" "$REQ_FILE" 2>/dev/null; then
    echo "gunicorn" >> "$REQ_FILE"
    echo "  ✅ Added gunicorn to requirements.txt"
  else
    echo "  ✓ gunicorn already in requirements.txt"
  fi
  if [ "$NO_DB" = false ] && ! grep -qi "^psycopg2-binary" "$REQ_FILE" 2>/dev/null; then
    echo "psycopg2-binary" >> "$REQ_FILE"
    echo "  ✅ Added psycopg2-binary to requirements.txt"
  elif [ "$NO_DB" = true ]; then
    echo "  ⏭  --no-db: skipping psycopg2-binary"
  else
    echo "  ✓ psycopg2-binary already in requirements.txt"
  fi
fi

# --- 4. Create Dockerfile ---
echo "  Creating Dockerfile..."
if [ -f "Dockerfile" ]; then
  echo "  ⚠ Dockerfile already exists, backing up to Dockerfile.bak"
  cp Dockerfile Dockerfile.bak
fi
cp "$TEMPLATES_DIR/Dockerfile" ./Dockerfile
echo "  ✅ Dockerfile created"

# --- 5. Create entrypoint.sh ---
echo "  Creating entrypoint.sh..."
cp "$TEMPLATES_DIR/entrypoint.sh" ./entrypoint.sh
chmod +x entrypoint.sh
echo "  ✅ entrypoint.sh created"

# --- 6. Create .dockerignore ---
echo "  Creating .dockerignore..."
cp "$TEMPLATES_DIR/.dockerignore" ./.dockerignore
echo "  ✅ .dockerignore created"

# --- 7. Create render.yaml ---
echo "  Creating render.yaml..."
if [ "$NO_DB" = true ]; then
  sed "s/{{slug}}/$SLUG/g; s/{{gh_user}}/PLACEHOLDER_USER/g" "$TEMPLATES_DIR/render.yaml.no-db.j2" > render.yaml
else
  sed "s/{{slug}}/$SLUG/g; s/{{gh_user}}/PLACEHOLDER_USER/g" "$TEMPLATES_DIR/render.yaml.j2" > render.yaml
fi
echo "  ✅ render.yaml created"

# --- 8. Create .env.production template ---
echo "  Creating .env.production..."
if [ ! -f ".env.production" ]; then
  cat > .env.production <<EOF
# Production environment (Render)
# These will be set via Render Dashboard env vars
EOF
  if [ "$NO_DB" = false ]; then
    cat >> .env.production <<EOF
# DATABASE_URL is auto-injected by Render PostgreSQL
EOF
  fi
  cat >> .env.production <<EOF
# FIREBASE_PROJECT_ID=your-project-id
# GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/service-account-key.json
EOF
  echo "  ✅ .env.production created"
else
  echo "  ✓ .env.production already exists"
fi

echo "✅ Server preparation complete."
