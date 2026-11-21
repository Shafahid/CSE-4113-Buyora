from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.db.base import Base
from app.models.auth import ID

JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


class Simulation(Base):
    __tablename__ = "simulations"
    __table_args__ = (
        Index("simulations_post_version_id_idx", "post_version_id"),
        CheckConstraint(
            "language IN ('en', 'bn')", name=conv("simulations_language_check")
        ),
        CheckConstraint(
            "status IN ('draft', 'queued', 'running', 'completed', "
            "'partially_failed', 'failed')",
            name=conv("simulations_status_check"),
        ),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column(ID, primary_key=True)
    post_version_id: Mapped[int] = mapped_column(
        ID, ForeignKey("public.post_versions.id"), nullable=False
    )
    language: Mapped[str] = mapped_column(Text, nullable=False, server_default="en")
    audience_settings: Mapped[dict] = mapped_column(
        JSON_TYPE, nullable=False, default=dict, server_default=text("'{}'")
    )
    product_snapshot: Mapped[dict | None] = mapped_column(JSON_TYPE)
    evaluation_rules_version: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    analysis: Mapped[dict | None] = mapped_column(JSON_TYPE)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
