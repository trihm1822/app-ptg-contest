"""Unit and integration tests for Database schema, models, relationships, and integrity."""

import uuid
from datetime import datetime, timezone
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ptg.db.base import Base
from ptg.db.models import Problem, ProblemRevision, Project, User


@pytest_asyncio.fixture
async def db_session():
    """Create in-memory SQLite async database engine and yield clean session."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    async with engine.begin() as conn:
        # Enable foreign keys in SQLite
        await conn.exec_driver_sql("PRAGMA foreign_keys = ON;")
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_user_and_project_creation(db_session: AsyncSession):
    """Verify creating User and associated Project with Foreign Key."""
    user = User(
        email="judge@ptg.io",
        hashed_password="argon2_hashed_secret",
        full_name="Judge Master",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.email == "judge@ptg.io"
    assert user.is_active is True
    assert user.is_superuser is False
    assert user.created_at is not None

    project = Project(
        user_id=user.id,
        title="National Contest 2026",
        description="Official high-school CP problems.",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    assert project.id is not None
    assert project.user_id == user.id
    assert project.deleted_at is None
    assert project.is_deleted is False


@pytest.mark.asyncio
async def test_user_delete_restrict_policy(db_session: AsyncSession):
    """Verify that deleting a User with active projects is blocked by ON DELETE RESTRICT."""
    user = User(email="author@ptg.io", hashed_password="hashed_pass")
    db_session.add(user)
    await db_session.commit()

    project = Project(user_id=user.id, title="Protected Workspace")
    db_session.add(project)
    await db_session.commit()

    # Attempting to delete the user must raise IntegrityError
    await db_session.delete(user)
    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_problem_and_revision_versioning(db_session: AsyncSession):
    """Verify Problem creation, circular revision FK handling, and revision versioning."""
    user = User(email="setter@ptg.io", hashed_password="pwd")
    db_session.add(user)
    await db_session.commit()

    project = Project(user_id=user.id, title="Algorithm Set")
    db_session.add(project)
    await db_session.commit()

    # 1. Create Problem without current_revision
    problem = Problem(
        project_id=project.id,
        title="Sum of Two Numbers",
        slug="sum-of-two-numbers",
    )
    db_session.add(problem)
    await db_session.commit()
    await db_session.refresh(problem)

    # 2. Create Revision 1
    sample_data = [{"input": "2 3", "output": "5"}]
    rev1 = ProblemRevision(
        problem_id=problem.id,
        revision_number=1,
        statement_md="# Sum of Two Numbers\nGiven a and b, compute a + b.",
        time_limit_ms=1000,
        memory_limit_mb=256,
        samples=sample_data,
        is_confirmed=True,
    )
    db_session.add(rev1)
    await db_session.flush()

    # Point problem to revision 1
    problem.current_revision = rev1
    await db_session.commit()

    # 3. Create Revision 2 (Increased time limit & updated constraints)
    rev2 = ProblemRevision(
        problem_id=problem.id,
        revision_number=2,
        statement_md="# Sum of Two Numbers v2\nNow with larger limits.",
        time_limit_ms=2000,
        memory_limit_mb=512,
        samples=sample_data,
    )
    db_session.add(rev2)
    await db_session.flush()
    problem.current_revision = rev2
    await db_session.commit()

    # Query back Problem and revisions
    result = await db_session.execute(
        select(Problem).where(Problem.id == problem.id)
    )
    fetched_problem = result.scalar_one()
    assert fetched_problem.current_revision_id == rev2.id
    assert fetched_problem.current_revision.revision_number == 2

    rev_result = await db_session.execute(
        select(ProblemRevision).where(ProblemRevision.problem_id == problem.id).order_by(ProblemRevision.revision_number)
    )
    all_revisions = rev_result.scalars().all()
    assert len(all_revisions) == 2
    assert all_revisions[0].revision_number == 1
    assert all_revisions[1].revision_number == 2
    assert all_revisions[0].samples == sample_data


@pytest.mark.asyncio
async def test_soft_delete_and_slug_recycling(db_session: AsyncSession):
    """Verify partial unique index allows recycling slugs after soft deletion."""
    user = User(email="admin@ptg.io", hashed_password="pwd")
    db_session.add(user)
    await db_session.commit()

    project = Project(user_id=user.id, title="Round 1")
    db_session.add(project)
    await db_session.commit()

    # Problem A with slug 'matrix-mult'
    p1 = Problem(project_id=project.id, title="Matrix Mult A", slug="matrix-mult")
    db_session.add(p1)
    await db_session.commit()

    # Duplicate active slug in same project must fail
    p_dup = Problem(project_id=project.id, title="Matrix Mult B", slug="matrix-mult")
    db_session.add(p_dup)
    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()

    # Soft-delete p1
    res = await db_session.execute(select(Problem).where(Problem.slug == "matrix-mult"))
    active_p1 = res.scalar_one()
    active_p1.deleted_at = datetime.now(timezone.utc)
    await db_session.commit()

    # Now creating a new Problem with recycled slug 'matrix-mult' must succeed
    p_recycled = Problem(project_id=project.id, title="Matrix Mult C", slug="matrix-mult")
    db_session.add(p_recycled)
    await db_session.commit()

    # Both records exist, one soft-deleted, one active
    all_p = await db_session.execute(select(Problem).where(Problem.slug == "matrix-mult"))
    problems_list = all_p.scalars().all()
    assert len(problems_list) == 2
    assert sum(1 for p in problems_list if p.deleted_at is None) == 1
