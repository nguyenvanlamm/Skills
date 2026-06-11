# Tech Stack Reference

## Backend: FastAPI + SQLAlchemy + SQLite

### Entry Point (`main.py` — server root)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Product API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
```

### Database (`database.py` — server root)

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Models (`models.py` — server root)

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base

# Define models per architecture.md
```

### Requirements (`requirements.txt` — server root)

```
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-multipart>=0.0.9
pytest>=8.0.0
httpx>=0.27.0
ruff>=0.3.0
```

### Run Command

```bash
cd <product-slug>-server && uvicorn main:app --reload --port 8000
# Or: make dev
```

---

## Frontend: React + Vite + Tailwind + shadcn/ui

### Vite Config (`vite.config.ts` — client root)

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
```

### API Client (`src/api/client.ts` — client root)

```typescript
const BASE = '/api/v1'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}
```

---

## Project Structure Convention (2 Repos Riêng)

```
YYYY_MM_DD_<product-slug>/
├── <product-slug>-server/           # FastAPI backend — riêng 1 GitHub repo
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── routes/
│   │   ├── __init__.py
│   │   └── ...
│   ├── services/
│   │   ├── __init__.py
│   │   └── ...
│   ├── requirements.txt
│   ├── Makefile
│   ├── README.md                    # Ghi rõ URL của client repo
│   └── .gitignore
│
└── <product-slug>-client/           # React frontend — riêng 1 GitHub repo
    ├── src/
    │   ├── api/
    │   │   └── client.ts
    │   ├── pages/
    │   ├── components/
    │   ├── hooks/
    │   ├── App.tsx
    │   └── main.tsx
    ├── index.html
    ├── package.json
    ├── vite.config.ts               # Proxy /api → http://localhost:8000
    ├── tailwind.config.js
    ├── tsconfig.json
    ├── Makefile
    ├── README.md                    # Ghi rõ URL của server repo
    └── .gitignore

```

### Cách chạy fullstack

```bash
# Terminal 1 — Server
cd <product-slug>-server && make dev
# → http://localhost:8000/docs

# Terminal 2 — Client
cd <product-slug>-client && make dev
# → http://localhost:5173
```
