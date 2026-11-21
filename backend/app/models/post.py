from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.db.base import Base
from app.models.auth import ID


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (Index("posts_product_id_idx", "product_id"), {"schema": "public"})

    id: Mapped[int] = mapped_column(ID, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ID, ForeignKey("public.products.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PostVersion(Base):
    __tablename__ = "post_versions"
    __table_args__ = (
        UniqueConstraint(
            "post_id", "version_number", name="post_versions_post_id_version_number_key"
        ),
        CheckConstraint(
            "version_number > 0", name=conv("post_versions_version_number_check")
        ),
        CheckConstraint(
            "btrim(headline) <> ''", name=conv("post_versions_headline_check")
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "btrim(body) <> ''", name=conv("post_versions_body_check")
        ).ddl_if(dialect="postgresql"),
        CheckConstraint(
            "btrim(platform) <> ''", name=conv("post_versions_platform_check")
        ).ddl_if(dialect="postgresql"),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column(ID, primary_key=True)
    post_id: Mapped[int] = mapped_column(
        ID, ForeignKey("public.posts.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    offer: Mapped[str | None] = mapped_column(Text)
    call_to_action: Mapped[str | None] = mapped_column(Text)
    hashtags: Mapped[list[str]] = mapped_column(
        ARRAY(Text).with_variant(JSON, "sqlite"),
        nullable=False,
        default=list,
        server_default=text("'{}'"),
    )
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
