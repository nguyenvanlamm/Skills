# Tech Stack Reference

## Backend: FastAPI + SQLAlchemy + SQLite

### Entry Point (`backend/main.py`)

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

### Database (`backend/database.py`)

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

### Models (`backend/models.py`)

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base

# Define models per architecture.md
```

### Requirements (`backend/requirements.txt`)

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
cd backend && uvicorn main:app --reload --port 8000
```

---

## Frontend: React + Vite + Tailwind + shadcn/ui

### Vite Config (`frontend/vite.config.ts`)

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

### API Client (`frontend/src/api/client.ts`)

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

## Project Structure Convention

```
product-name/
├── backend/
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
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts
│   │   ├── pages/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── tests/
│   ├── test_backend/
│   └── test_frontend/
├── Makefile
├── README.md
└── .gitignore
```
