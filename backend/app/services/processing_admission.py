"""Admission contract for database-backed optional-AI processing.

The default implementation verifies a matching worker heartbeat and persists
dispatch transactionally. A configuration flag or provider callable alone never
enables admission. Dependency overrides remain available for isolated tests.
"""

from abc import ABC, abstractmethod
from typing import Literal

from fastapi import Request
from sqlalchemy.orm import Session

JobKind = Literal["image_analysis", "market_analysis", "platform_generation"]


class DurableProcessingAdmission(ABC):
    @abstractmethod
    def verify_ready(self, db: Session, kind: JobKind) -> None:
        """Raise unless a healthy worker and recoverable durable queue are available."""

    @abstractmethod
    def enqueue(self, db: Session, kind: JobKind, resource_id: int) -> None:
        """Persist a dispatch in the same DB transaction; raise if not accepted."""


def get_processing_admission(request: Request) -> DurableProcessingAdmission | None:
    """Admission still requires a fresh, matching database worker heartbeat."""
    from app.services.ai.jobs import DatabaseAdmission

    settings = request.app.state.settings
    return DatabaseAdmission(settings) if settings.phase2_ai_enabled else None


def processing_is_ready(admission, db: Session, kind: JobKind) -> bool:
    """Report readiness without treating a flag or arbitrary callable as a worker."""
    if not isinstance(admission, DurableProcessingAdmission):
        return False
    try:
        admission.verify_ready(db, kind)
        return True
    except Exception:
        db.rollback()
        return False
