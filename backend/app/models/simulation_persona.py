from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.db.base import Base
from app.models.auth import ID
from app.models.simulation import JSON_TYPE


class SimulationPersona(Base):
    __tablename__ = "simulation_personas"
    __table_args__ = (
        Index("simulation_personas_simulation_id_idx", "simulation_id"),
        CheckConstraint(
            "btrim(name) <> ''", name=conv("simulation_personas_name_check")
        ).ddl_if(dialect="postgresql"),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column(ID, primary_key=True)
    simulation_id: Mapped[int] = mapped_column(
        ID, ForeignKey("public.simulations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    characteristics: Mapped[dict] = mapped_column(
        JSON_TYPE, nullable=False, default=dict, server_default=text("'{}'")
    )
    needs: Mapped[list[str]] = mapped_column(
        ARRAY(Text).with_variant(JSON, "sqlite"),
        nullable=False,
        default=list,
        server_default=text("'{}'"),
    )
    preferences: Mapped[list[str]] = mapped_column(
        ARRAY(Text).with_variant(JSON, "sqlite"),
        nullable=False,
        default=list,
        server_default=text("'{}'"),
    )
    budget_sensitivity: Mapped[str | None] = mapped_column(Text)
    is_selected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
