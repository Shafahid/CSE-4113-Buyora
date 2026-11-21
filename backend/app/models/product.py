from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.db.base import Base
from app.models.auth import ID


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        Index("products_seller_id_idx", "seller_id"),
        CheckConstraint("btrim(name) <> ''", name=conv("products_name_check")).ddl_if(
            dialect="postgresql"
        ),
        CheckConstraint(
            "btrim(category) <> ''", name=conv("products_category_check")
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "price >= 0 AND price <> 'NaN'::numeric", name=conv("products_price_check")
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "currency ~ '^[A-Z]{3}$'", name=conv("products_currency_check")
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "status IN ('active', 'archived')", name=conv("products_status_check")
        ).ddl_if(dialect="postgresql"),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column(ID, primary_key=True)
    seller_id: Mapped[int] = mapped_column(
        ID, ForeignKey("public.users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False, server_default="BDT")
    category: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    features: Mapped[list[str]] = mapped_column(
        ARRAY(Text).with_variant(JSON, "sqlite"),
        nullable=False,
        default=list,
        server_default=text("'{}'"),
    )
    warranty: Mapped[str | None] = mapped_column(Text)
    delivery_info: Mapped[str | None] = mapped_column(Text)
    return_policy: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
