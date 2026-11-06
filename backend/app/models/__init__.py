"""Import each ORM model here so Alembic discovers it through Base.metadata."""

from app.db.base import Base

__all__ = ["Base"]
