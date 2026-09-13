# Changelog

## v2.1.0 — 2026-09-13

### Fixed
- **`database.py` detection**: `grep DATABASE_URL` matched `SQLALCHEMY_DATABASE_URL = "sqlite:///…"`, so a hardcoded file was reported as "already supports DATABASE_URL" and production ran SQLite inside the container. Now checks for the actual env read (`os.getenv("DATABASE_URL"` / `os.environ[...]`).
- **`pg_isready` was never installed** in the image, so the DB readiness loop failed silently for 60 s on every boot. Dockerfile now installs `postgresql-client`; entrypoint says so if the binary is missing instead of spinning.
- **`--region` and `--health-path` were accepted by `render-client.sh` but not by `deploy.sh`** — user values were silently dropped and `render.yaml` always hardcoded `oregon` with no `healthCheckPath`. Both flags now flow through all three scripts and into the blueprint.
- **`gh repo create --source=. --push` on a repo with zero commits fails** ("src refspec main does not match any"). `push-to-github.sh` now commits first, then creates the remote, then pushes.
- `render.yaml` said `branch: main` regardless of the branch actually pushed; the blueprint then deployed nothing. Branch is now written from `git rev-parse`.
- `render.yaml` database block used `version:` — the blueprint key is `postgresMajorVersion`.
- `@app.on_event("startup")` (deprecated) is no longer appended to `main.py`; `entrypoint.sh` already runs `create_all`.
- JSON bodies built with `jq -n --arg` instead of string interpolation.
- `docs/README.md` claimed free PostgreSQL expires after 90 days (it is 30 + 14 grace) and showed an output shape without `verified`.

### Changed
- When `database.py` must be rewritten, the original is kept at `database.py.bak` and the project's `Base` style (`DeclarativeBase` vs `declarative_base()`) is preserved. Dockerfile/entrypoint/.dockerignore are backed up only when they differ from the template.
- Gunicorn workers default to `WEB_CONCURRENCY=2` (was 4 — exceeds the 512 MB free instance), `--timeout 60`, jitter on max-requests.
- Base image `python:3.12-slim`.
- `.gitignore` additions include `*.bak` and `service-account*.json`; tracked secret-looking files are removed from the index with a rotate warning.

### Added
- `--public`, `--output`, `--region`, `--health-path` on `deploy.sh`; `--help`.
- Up-front checks in `deploy.sh`: required CLIs, `main.py` present, slug charset, API key present — before any step runs.
- Verification retries 3× (10 s apart) to survive the router's post-"live" 502 window; on failure suggests `--health-path` when the route may not exist.
- `render.yaml` carries `healthCheckPath`, `region`, `WEB_CONCURRENCY`.

### Breaking Changes
- None for callers. Servers whose `database.py` was previously (wrongly) left hardcoded will now be rewritten on the next run — with a `.bak` and a log line saying so.

## v2.0.0
- Verified `/docs` before reporting success, stopped inventing URLs, blueprint fallback by name.
