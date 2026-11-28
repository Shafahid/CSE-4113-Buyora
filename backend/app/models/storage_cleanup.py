from datetime import datetime

from sqlalchemy import DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.auth import ID


class StorageCleanupTask(Base):
    __tablename__ = "storage_cleanup_tasks"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(ID, primary_key=True)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
