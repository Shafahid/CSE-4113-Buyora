"""Admission contract for future durable AI processing integrations.

The default has no installed processor. An integration may override the FastAPI
provider only after implementing worker-health verification and transactional
enqueue with crash recovery. A configuration flag or provider callable alone
must never enable admission.
"""

from abc import ABC, abstractmethod
from typing import Literal

from sqlalchemy.orm import Session

JobKind = Literal["image_analysis", "platform_generation"]


class DurableProcessingAdmission(ABC):
    @abstractmethod
    def verify_ready(self, db: Session, kind: JobKind) -> None:
        """Raise unless a healthy worker and recoverable durable queue are available."""

    @abstractmethod
    def enqueue(self, db: Session, kind: JobKind, resource_id: int) -> None:
        """Persist a dispatch in the same DB transaction; raise if not accepted."""


def get_processing_admission() -> DurableProcessingAdmission | None:
    """No production admission is installed until the worker integration exists."""
    return None


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
