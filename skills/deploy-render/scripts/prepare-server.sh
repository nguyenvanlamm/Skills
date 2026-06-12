#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES_DIR="$(cd "$SCRIPT_DIR/../templates" && pwd)"

SERVER_DIR=""
SLUG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --server-dir) SERVER_DIR="$2"; shift 2 ;;
    --slug) SLUG="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [ -z "$SERVER_DIR" ]; then echo "❌ --server-dir required"; exit 1; fi
if [ -z "$SLUG" ]; then echo "❌ --slug required"; exit 1; fi

echo "◆ Preparing server code in $SERVER_DIR..."

cd "$SERVER_DIR"

# --- 1. Update database.py ---
echo "  Updating database.py for PostgreSQL..."
DATABASE_PY="database.py"
if [ ! -f "$DATABASE_PY" ]; then
  echo "  ⚠ database.py not found, skipping PostgreSQL config"
else
  # Check if already has DATABASE_URL support
  if grep -q "DATABASE_URL" "$DATABASE_PY"; then
    echo "  ✓ database.py already supports DATABASE_URL"
  else
    # Read current content
    CURRENT=$(cat "$DATABASE_PY")
    cat > "$DATABASE_PY" <<PYEOF
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Render PostgreSQL uses "postgres://" but SQLAlchemy needs "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Handle SQLite special args
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

# --- 2. Update main.py to auto-create tables on startup ---
echo "  Updating main.py for auto table creation..."
MAIN_PY="main.py"
if [ ! -f "$MAIN_PY" ]; then
  echo "  ⚠ main.py not found, skipping startup config"
else
  if grep -q "startup.*create_all\|create_all.*startup" "$MAIN_PY" 2>/dev/null; then
    echo "  ✓ main.py already has startup table creation"
  else
    # Add startup event after imports
    if grep -q "@app.on_event.*startup\|def startup" "$MAIN_PY" 2>/dev/null; then
      echo "  ✓ main.py already has startup event"
    else
      # Find a good insertion point: after the last import or after app creation
      # Simple approach: add before the first route or before if __name__
      cat >> "$MAIN_PY" <<PYEOF


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
  echo -e "fastapi\nuvicorn\ngunicorn\nsqlalchemy\npydantic\npsycopg2-binary" > "$REQ_FILE"
  echo "  ✅ requirements.txt created"
else
  for pkg in "psycopg2-binary" "gunicorn"; do
    if grep -qi "^${pkg}" "$REQ_FILE" 2>/dev/null; then
      echo "  ✓ $pkg already in requirements.txt"
    else
      echo "$pkg" >> "$REQ_FILE"
      echo "  ✅ Added $pkg to requirements.txt"
    fi
  done
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
# We'll leave gh_user placeholder for now, will be filled by deploy.sh
sed "s/{{slug}}/$SLUG/g; s/{{gh_user}}/PLACEHOLDER_USER/g" "$TEMPLATES_DIR/render.yaml.j2" > render.yaml
echo "  ✅ render.yaml created"

# --- 8. Create .env.production template ---
echo "  Creating .env.production..."
if [ ! -f ".env.production" ]; then
  cat > .env.production <<EOF
# Production environment (Render)
# These will be set via Render Dashboard env vars
# DATABASE_URL is auto-injected by Render PostgreSQL
# FIREBASE_PROJECT_ID=your-project-id
# GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/service-account-key.json
EOF
  echo "  ✅ .env.production created"
else
  echo "  ✓ .env.production already exists"
fi

echo "✅ Server preparation complete."
