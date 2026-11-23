from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.auth import ID
from app.models.simulation import JSON_TYPE


class PersonaAdaptation(Base):
    __tablename__ = "persona_adaptations"
    __table_args__ = (
        UniqueConstraint("seller_id", "request_id"),
        Index("ix_persona_adaptations_cache", "seller_id", "fingerprint"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    seller_id: Mapped[int] = mapped_column(
        ID, ForeignKey("public.users.id", ondelete="CASCADE")
    )
    product_id: Mapped[int] = mapped_column(
        ID, ForeignKey("public.products.id", ondelete="CASCADE")
    )
    request_id: Mapped[str] = mapped_column(String(36))
    fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24))
    inputs: Mapped[dict] = mapped_column(JSON_TYPE)
    result: Mapped[list | None] = mapped_column(JSON_TYPE)
    usage: Mapped[dict] = mapped_column(JSON_TYPE, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[str | None] = mapped_column(String(36))
