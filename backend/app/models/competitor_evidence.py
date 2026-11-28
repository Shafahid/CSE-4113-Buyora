from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.db.base import Base
from app.models.auth import ID


class CompetitorEvidence(Base):
    __tablename__ = "competitor_evidence"
    __table_args__ = (
        Index(
            "competitor_evidence_seller_observed_idx", "seller_id", "observed_at", "id"
        ),
        Index("competitor_evidence_product_id_idx", "product_id"),
        Index("competitor_evidence_seller_platform_idx", "seller_id", "platform"),
        CheckConstraint(
            "btrim(competitor_name) <> ''", name=conv("competitor_evidence_name_check")
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "btrim(product_name) <> ''",
            name=conv("competitor_evidence_product_name_check"),
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "price IS NULL OR (price >= 0 AND price <> 'NaN'::numeric)",
            name=conv("competitor_evidence_price_check"),
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "(price IS NULL AND currency IS NULL) OR "
            "(price IS NOT NULL AND currency IS NOT NULL AND currency ~ '^[A-Z]{3}$')",
            name=conv("competitor_evidence_currency_check"),
        ).ddl_if(dialect="postgresql"),
        {"schema": "public"},
    )
    id: Mapped[int] = mapped_column(ID, primary_key=True)
    seller_id: Mapped[int] = mapped_column(
        ID, ForeignKey("public.users.id"), nullable=False
    )
    product_id: Mapped[int | None] = mapped_column(ID, ForeignKey("public.products.id"))
    competitor_name: Mapped[str] = mapped_column(Text, nullable=False)
    product_name: Mapped[str] = mapped_column(Text, nullable=False)
    competitor_description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(Text)
    offer: Mapped[str | None] = mapped_column(Text)
    platform: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_note: Mapped[str | None] = mapped_column(Text)
    observed_at: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
