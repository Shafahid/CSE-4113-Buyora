from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.db.base import Base
from app.models.auth import ID
from app.models.simulation import JSON_TYPE


class MarketAnalysis(Base):
    __tablename__ = "market_analyses"
    __table_args__ = (
        Index(
            "market_analyses_owner_product_created_idx",
            "seller_id",
            "product_id",
            "created_at",
            "id",
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name=conv("market_analyses_status_check"),
        ),
        CheckConstraint(
            "language IN ('en', 'bn')", name=conv("market_analyses_language_check")
        ),
        CheckConstraint(
            "(status = 'completed' AND analysis_result IS NOT NULL) OR "
            "(status <> 'completed' AND analysis_result IS NULL)",
            name=conv("market_analyses_result_check"),
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
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    language: Mapped[str] = mapped_column(Text, nullable=False, server_default="en")
    input_snapshot: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)
    analysis_result: Mapped[dict | None] = mapped_column(JSON_TYPE)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
