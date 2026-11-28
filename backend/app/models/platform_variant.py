from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.db.base import Base
from app.models.auth import ID
from app.models.simulation import JSON_TYPE


class PlatformVariant(Base):
    __tablename__ = "platform_variants"
    __table_args__ = (
        Index("platform_variants_source_idx", "source_version_id", "id"),
        CheckConstraint(
            "platform IN ('facebook', 'instagram', 'tiktok', 'whatsapp')",
            name=conv("platform_variants_platform_check"),
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'ready', 'failed')",
            name=conv("platform_variants_status_check"),
        ),
        CheckConstraint(
            "language IN ('en', 'bn')", name=conv("platform_variants_language_check")
        ),
        {"schema": "public"},
    )
    id: Mapped[int] = mapped_column(ID, primary_key=True)
    source_version_id: Mapped[int] = mapped_column(
        ID, ForeignKey("public.post_versions.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(Text, nullable=False, server_default="en")
    preferences: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    processing_metadata: Mapped[dict | None] = mapped_column(JSON_TYPE)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PlatformVariantRevision(Base):
    __tablename__ = "platform_variant_revisions"
    __table_args__ = (
        UniqueConstraint(
            "variant_id", "revision_number", name="platform_variant_revision_number_key"
        ),
        CheckConstraint(
            "revision_number > 0", name=conv("platform_variant_revision_number_check")
        ),
        CheckConstraint(
            "origin IN ('seller', 'ai', 'fallback')",
            name=conv("platform_variant_revision_origin_check"),
        ),
        {"schema": "public"},
    )
    id: Mapped[int] = mapped_column(ID, primary_key=True)
    variant_id: Mapped[int] = mapped_column(
        ID,
        ForeignKey("public.platform_variants.id", ondelete="CASCADE"),
        nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    offer: Mapped[str | None] = mapped_column(Text)
    call_to_action: Mapped[str | None] = mapped_column(Text)
    hashtags: Mapped[list] = mapped_column(JSON_TYPE, nullable=False)
    origin: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
