"""Problem revision entity model tracking immutable statement history."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ptg.db.base import Base

if TYPE_CHECKING:
    from ptg.db.models.problem import Problem


class ProblemRevision(Base):
    """Immutable versioned revision of a problem statement and constraints."""

    __tablename__ = "problem_revisions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("problems.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    statement_md: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    time_limit_ms: Mapped[int] = mapped_column(
        Integer,
        default=1000,
        nullable=False,
    )
    memory_limit_mb: Mapped[int] = mapped_column(
        Integer,
        default=256,
        nullable=False,
    )
    samples: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    is_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    problem: Mapped["Problem"] = relationship(
        "Problem",
        back_populates="revisions",
        foreign_keys=[problem_id],
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "problem_id",
            "revision_number",
            name="uq_problem_revisions_problem_revision",
        ),
    )
