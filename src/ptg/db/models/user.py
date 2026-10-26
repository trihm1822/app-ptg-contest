"""User entity model for identity and authentication."""

import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ptg.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from ptg.db.models.project import Project


class User(Base, TimestampMixin):
    """User account model managing credentials and ownership."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships: user has projects; ON DELETE RESTRICT prevents deleting active user with projects
    projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="user",
        lazy="selectin",
    )
