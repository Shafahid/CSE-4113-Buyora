"""Durable optional-AI dispatch and worker heartbeat, separate from simulation jobs."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.auth import ID
from app.models.simulation import JSON_TYPE


class AIJob(Base):
    __tablename__ = "ai_jobs"
    __table_args__ = (
        UniqueConstraint("kind", "resource_id", name="uq_ai_job_resource"),
        Index("ix_ai_jobs_queue", "status", "lease_until", "created_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    reservation_id: Mapped[str] = mapped_column(
        ForeignKey("buyora.ai_request_reservations.id", ondelete="CASCADE"), unique=True
    )
    seller_id: Mapped[int] = mapped_column(ID, ForeignKey("public.users.id"))
    kind: Mapped[str] = mapped_column(String(32))
    resource_id: Mapped[int] = mapped_column(ID)
    status: Mapped[str] = mapped_column(String(16), default="queued")
    payload: Mapped[dict] = mapped_column(JSON_TYPE)
    configuration: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[str | None] = mapped_column(String(36))
    error_code: Mapped[str | None] = mapped_column(String(64))
    usage: Mapped[dict | None] = mapped_column(JSON_TYPE)


class AIWorkerHeartbeat(Base):
    __tablename__ = "ai_worker_heartbeats"
    __table_args__ = (Index("ix_ai_worker_freshness", "updated_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    configuration: Mapped[str] = mapped_column(String(64))
    capabilities: Mapped[list] = mapped_column(JSON_TYPE)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
