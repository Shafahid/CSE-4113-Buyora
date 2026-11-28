from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.db.base import Base
from app.models.auth import ID
from app.models.simulation import JSON_TYPE


class ProductImageAnalysis(Base):
    __tablename__ = "product_image_analyses"
    __table_args__ = (
        Index(
            "image_analyses_owner_image_idx",
            "seller_id",
            "product_id",
            "original_image_id",
            "created_at",
            "id",
        ),
        Index("image_analyses_image_id_idx", "image_id"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name=conv("image_analyses_status_check"),
        ),
        CheckConstraint(
            "language IN ('en', 'bn')", name=conv("image_analyses_language_check")
        ),
        CheckConstraint(
            "(status = 'completed' AND analysis_result IS NOT NULL) OR "
            "(status <> 'completed' AND analysis_result IS NULL)",
            name=conv("image_analyses_result_check"),
        ),
        {"schema": "public"},
    )
    id: Mapped[int] = mapped_column(ID, primary_key=True)
    seller_id: Mapped[int] = mapped_column(
        ID, ForeignKey("public.users.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ID, ForeignKey("public.products.id"), nullable=False
    )
    image_id: Mapped[int | None] = mapped_column(
        ID, ForeignKey("public.product_images.id", ondelete="SET NULL")
    )
    original_image_id: Mapped[int] = mapped_column(ID, nullable=False)
    snapshot_storage_key: Mapped[str | None] = mapped_column(Text, index=True)
    language: Mapped[str] = mapped_column(Text, nullable=False, server_default="en")
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    analysis_result: Mapped[dict | None] = mapped_column(JSON_TYPE)
    processing_metadata: Mapped[dict | None] = mapped_column(JSON_TYPE)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
