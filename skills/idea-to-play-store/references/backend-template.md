# Backend template (FastAPI + Firebase Admin)

Used by Phase 3c when the PRD needs a server. Generate into `$PRODUCT_DIR/backend/`, then hand the directory to `deploy-render` (which adds Dockerfile, `render.yaml`, PostgreSQL wiring — do **not** create those here).

## Layout

If backend needed, generate FastAPI project:

```
$PRODUCT_DIR/backend/
├── main.py                # FastAPI entry + CORS + Firebase verify
├── database.py            # SQLAlchemy + PostgreSQL (or SQLite local)
├── requirements.txt       # fastapi, uvicorn, firebase-admin, sqlalchemy, psycopg2
├── Dockerfile
├── render.yaml
├── app/
│   ├── __init__.py
│   ├── config.py          # Firebase creds, DB URL
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py        # User model
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py         # POST /api/auth/verify — verify Firebase token
│   │   └── users.py        # GET/PUT /api/users/me
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── auth_service.py  # Firebase Admin verification
│   └── middleware/
│       ├── __init__.py
│       └── firebase_auth.py  # Dependency: get_current_user
└── .env.example
```

**Key backend code (main.py):**

```python
import firebase_admin
from firebase_admin import credentials, auth
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware

import os

# GOOGLE_APPLICATION_CREDENTIALS points at the service account key from firebase-auth-setup.
# On Render, upload the key as a Secret File and set the env var to its path.
firebase_admin.initialize_app(credentials.Certificate(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]))

# Comma-separated. Mobile clients send no Origin header, so this only matters for a web client / Swagger UI.
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()]

app = FastAPI(title="$APP_NAME API")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=["*"], allow_headers=["*"])

security = HTTPBearer(auto_error=False)

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    try:
        decoded = auth.verify_id_token(credentials.credentials)
        return decoded
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/api/users/me")
async def get_me(user: dict = Depends(verify_token)):
    return {"uid": user["uid"], "email": user.get("email"), "name": user.get("name")}
```

## Rules

- `database.py` reads `DATABASE_URL` from env with a SQLite default (same template as `idea-to-product/references/tech-stack.md`). `deploy-render` keeps the file when it sees `os.getenv("DATABASE_URL"`; otherwise it overwrites it.
- No `allow_origins=["*"]` together with `allow_credentials=True` — browsers reject that combination and it is a needless exposure on a token-protected API.
- Never commit `service-account.json` / the key path; `.gitignore` it before the first commit.
- Health at `GET /api/health` is what `deploy-render --health-path /api/health` verifies.
