# Buyora backend

Minimal FastAPI project managed with uv.

## Setup

```powershell
uv sync
```

## Run locally

FastAPI is the only direct dependency. Run with a temporary Uvicorn dependency:

```powershell
uv run --with uvicorn uvicorn main:app --reload
```

API: http://127.0.0.1:8000

Interactive documentation: http://127.0.0.1:8000/docs

## Add dependencies

```powershell
uv add <package-name>
```
