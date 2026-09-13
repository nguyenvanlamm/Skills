#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES_DIR="$(cd "$SCRIPT_DIR/../templates" && pwd)"

SERVER_DIR=""
SLUG=""
NO_DB=false
REGION="oregon"
HEALTH_PATH="/docs"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --server-dir) SERVER_DIR="$2"; shift 2 ;;
    --slug) SLUG="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --health-path) HEALTH_PATH="$2"; shift 2 ;;
    --no-db) NO_DB=true; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

[ -n "$SERVER_DIR" ] || { echo "❌ --server-dir required"; exit 1; }
[ -n "$SLUG" ]       || { echo "❌ --slug required"; exit 1; }

echo "◆ Preparing server code in $SERVER_DIR..."
cd "$SERVER_DIR"

[ -f main.py ] || { echo "❌ No main.py in $SERVER_DIR — the Dockerfile starts 'main:app'. Not a FastAPI server root?"; exit 1; }

# --- 1. database.py ---------------------------------------------------------
# Only rewrite when the file truly hardcodes its URL. The old check was
# `grep DATABASE_URL`, which matched `SQLALCHEMY_DATABASE_URL = "sqlite:///…"`
# and left a hardcoded SQLite path in production. Look for the env read itself.
if [ "$NO_DB" = true ]; then
  echo "  ⏭  --no-db: leaving database.py untouched"
elif [ ! -f database.py ]; then
  echo "  ⚠ database.py not found — skipping PostgreSQL wiring (set DATABASE_URL handling yourself)"
elif grep -qE 'getenv\(["'\'']DATABASE_URL|environ(\.get)?\[?\(?["'\'']DATABASE_URL' database.py; then
  echo "  ✓ database.py already reads DATABASE_URL from the environment"
else
  cp database.py database.py.bak
  echo "  ⚠ database.py hardcodes its URL — rewriting (original kept at database.py.bak)"
  # Preserve the project's Base style: SQLAlchemy 2.0 DeclarativeBase vs legacy declarative_base().
  if grep -q 'DeclarativeBase' database.py.bak; then
    BASE_IMPORT="from sqlalchemy.orm import DeclarativeBase, sessionmaker"
    BASE_DEF=$'class Base(DeclarativeBase):\n    pass'
  else
    BASE_IMPORT="from sqlalchemy.orm import declarative_base, sessionmaker"
    BASE_DEF="Base = declarative_base()"
  fi
  cat > database.py <<PYEOF
import os

from sqlalchemy import create_engine
${BASE_IMPORT}

# Render injects DATABASE_URL for the linked PostgreSQL; local dev falls back to SQLite.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

${BASE_DEF}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
PYEOF
  echo "  ✅ database.py rewritten with DATABASE_URL support"
fi

# --- 2. Table creation -------------------------------------------------------
# entrypoint.sh runs Base.metadata.create_all before starting the server, so
# main.py does not need a startup hook. The old version appended a deprecated
# @app.on_event("startup") block that duplicated that work. Just report.
if [ "$NO_DB" = false ]; then
  if grep -qE 'create_all' main.py; then
    echo "  ✓ main.py already creates tables on startup (entrypoint will also run create_all — harmless)"
  else
    echo "  ✓ Tables will be created by entrypoint.sh (Base.metadata.create_all) before the server starts"
  fi
fi

# --- 3. requirements.txt ----------------------------------------------------
REQ_FILE="requirements.txt"
if [ ! -f "$REQ_FILE" ]; then
  echo "  ⚠ requirements.txt not found — creating a minimal one"
  printf 'fastapi\nuvicorn[standard]\ngunicorn\nsqlalchemy\npydantic\n' > "$REQ_FILE"
fi
add_req() {  # add_req <package> — idempotent, matches with or without version pins/extras
  if grep -qiE "^$1([[:space:]]*(\[|[=<>~!;])|[[:space:]]*$)" "$REQ_FILE"; then
    echo "  ✓ $1 already in requirements.txt"
  else
    echo "$1" >> "$REQ_FILE"; echo "  ✅ Added $1 to requirements.txt"
  fi
}
add_req gunicorn
add_req uvicorn
if [ "$NO_DB" = false ]; then add_req psycopg2-binary; else echo "  ⏭  --no-db: skipping psycopg2-binary"; fi

# --- 4. Dockerfile, entrypoint, .dockerignore -------------------------------
for f in Dockerfile entrypoint.sh .dockerignore; do
  if [ -f "$f" ] && ! cmp -s "$f" "$TEMPLATES_DIR/$f"; then
    cp "$f" "$f.bak"; echo "  ⚠ $f differs from template — backed up to $f.bak"
  fi
  cp "$TEMPLATES_DIR/$f" "./$f"
done
chmod +x entrypoint.sh
echo "  ✅ Dockerfile, entrypoint.sh, .dockerignore in place"

# --- 5. render.yaml ----------------------------------------------------------
TEMPLATE="render.yaml.j2"; [ "$NO_DB" = true ] && TEMPLATE="render.yaml.no-db.j2"
sed -e "s|{{slug}}|$SLUG|g" -e "s|{{gh_user}}|PLACEHOLDER_USER|g" \
    -e "s|{{region}}|$REGION|g" -e "s|{{health_path}}|$HEALTH_PATH|g" \
    "$TEMPLATES_DIR/$TEMPLATE" > render.yaml
echo "  ✅ render.yaml created (region $REGION, healthCheckPath $HEALTH_PATH)"

# --- 6. .env.production template --------------------------------------------
if [ ! -f .env.production ]; then
  {
    echo "# Production environment (Render) — values are set in the Render Dashboard, this file is documentation"
    [ "$NO_DB" = true ] || echo "# DATABASE_URL is injected by the linked Render PostgreSQL"
    echo "# ALLOWED_ORIGINS=https://<client>.netlify.app"
    echo "# FIREBASE_PROJECT_ID=your-project-id"
    echo "# GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/service-account-key.json"
  } > .env.production
  echo "  ✅ .env.production created"
else
  echo "  ✓ .env.production already exists"
fi

echo "✅ Server preparation complete."
