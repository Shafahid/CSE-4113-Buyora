from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.db.base import Base
from app.models.auth import ID


class ProductImage(Base):
    __tablename__ = "product_images"
    __table_args__ = (
        Index("product_images_product_id_idx", "product_id"),
        CheckConstraint(
            "sort_order >= 0", name=conv("product_images_sort_order_check")
        ),
        CheckConstraint(
            "btrim(storage_key) <> ''", name=conv("product_images_storage_key_check")
        ).ddl_if(dialect="postgresql"),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column(ID, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ID, ForeignKey("public.products.id", ondelete="CASCADE"), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
