"""Conservative admission reservations shared by all optional AI endpoints."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.auth import ID
from app.models.simulation import JSON_TYPE


class AIRequestReservation(Base):
    __tablename__ = "ai_request_reservations"
    __table_args__ = (
        UniqueConstraint("kind", "resource_id", name="uq_ai_reservation_resource"),
        Index("ix_ai_reservations_seller_created", "seller_id", "created_at"),
        CheckConstraint("reserved_tokens > 0", name="ai_reserved_tokens_positive"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    seller_id: Mapped[int] = mapped_column(
        ID, ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    resource_id: Mapped[int] = mapped_column(ID, nullable=False)
    reserved_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    policy: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
