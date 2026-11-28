"""Owned, durable execution records, separate from unmanaged evaluation tables."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.auth import ID
from app.models.simulation import JSON_TYPE


class SimulationRun(Base):
    __tablename__ = "simulation_runs"
    __table_args__ = (
        UniqueConstraint("seller_id", "request_id"),
        Index("ix_simulation_runs_queue", "status", "lease_until"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    simulation_id: Mapped[int] = mapped_column(
        ID, ForeignKey("public.simulations.id", ondelete="CASCADE"), unique=True
    )
    seller_id: Mapped[int] = mapped_column(
        ID, ForeignKey("public.users.id", ondelete="CASCADE"), index=True
    )
    request_id: Mapped[str] = mapped_column(String(36))
    fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="queued")
    stage: Mapped[str] = mapped_column(
<<<<<<< HEAD
        String(32), default="queued", server_default="queued"
    )
    expected_personas: Mapped[int] = mapped_column(Integer)
=======
        String(32), nullable=False, default="queued", server_default="queued"
    )
    expected_personas: Mapped[int] = mapped_column(Integer, nullable=False)
>>>>>>> 7c316b1109eba01b8e367b41828175e3b27b24e5
    inputs: Mapped[dict] = mapped_column(JSON_TYPE)
    model: Mapped[str] = mapped_column(String(200))
    rules_version: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[str | None] = mapped_column(String(36))
    report: Mapped[dict | None] = mapped_column(JSON_TYPE)


class PersonaEvaluation(Base):
    __tablename__ = "simulation_run_evaluations"
    __table_args__ = (UniqueConstraint("run_id", "persona_id"),)

    id: Mapped[int] = mapped_column(ID, primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("buyora.simulation_runs.id", ondelete="CASCADE"), index=True
    )
    persona_id: Mapped[int] = mapped_column(
        ID, ForeignKey("public.simulation_personas.id", ondelete="CASCADE")
    )
    profile: Mapped[dict] = mapped_column(JSON_TYPE)
    status: Mapped[str] = mapped_column(String(16), default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    output: Mapped[dict | None] = mapped_column(JSON_TYPE)
    error_code: Mapped[str | None] = mapped_column(String(40))
    history: Mapped[list] = mapped_column(JSON_TYPE, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SimulationCache(Base):
    __tablename__ = "simulation_cache"

    seller_id: Mapped[int] = mapped_column(
        ID, ForeignKey("public.users.id", ondelete="CASCADE"), primary_key=True
    )
    fingerprint: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("buyora.simulation_runs.id", ondelete="CASCADE")
    )
