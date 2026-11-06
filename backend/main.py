"""Compatibility entry point: uv run uvicorn main:app --reload."""

from app.main import create_app

app = create_app()
