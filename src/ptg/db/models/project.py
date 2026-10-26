"""Project workspace entity model."""

import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ptg.db.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from ptg.db.models.problem import Problem
    from ptg.db.models.user import User


class Project(Base, TimestampMixin, SoftDeleteMixin):
    """User project workspace containing competitive programming problems."""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="projects",
        lazy="selectin",
    )
    problems: Mapped[List["Problem"]] = relationship(
        "Problem",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
