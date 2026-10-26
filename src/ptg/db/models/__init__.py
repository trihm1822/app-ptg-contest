"""Database entity models registry."""

from ptg.db.models.user import User
from ptg.db.models.project import Project
from ptg.db.models.problem import Problem
from ptg.db.models.problem_revision import ProblemRevision

__all__ = [
    "User",
    "Project",
    "Problem",
    "ProblemRevision",
]
