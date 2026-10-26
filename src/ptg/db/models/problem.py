"""Problem entity model maintaining stable identity across revisions."""

import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ptg.db.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from ptg.db.models.problem_revision import ProblemRevision
    from ptg.db.models.project import Project


class Problem(Base, TimestampMixin, SoftDeleteMixin):
    """Competitive programming problem entity maintaining stable identity across revisions."""

    __tablename__ = "problems"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    current_revision_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey(
            "problem_revisions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_problems_current_revision_id",
        ),
        nullable=True,
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="problems",
        lazy="selectin",
    )
    revisions: Mapped[List["ProblemRevision"]] = relationship(
        "ProblemRevision",
        back_populates="problem",
        foreign_keys="ProblemRevision.problem_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    current_revision: Mapped[Optional["ProblemRevision"]] = relationship(
        "ProblemRevision",
        foreign_keys=[current_revision_id],
        post_update=True,
        lazy="selectin",
    )

    __table_args__ = (
        # Partial unique index allows recycling slugs for soft-deleted problems
        Index(
            "uq_problems_project_slug_active",
            "project_id",
            "slug",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
    )
