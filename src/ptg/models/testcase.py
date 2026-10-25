"""Data models for testcase records, status, and differential testing results."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class TestcaseStatus(str, Enum):
    """Execution status of an individual testcase in differential testing."""

    __test__ = False

    PASSED = "PASSED"
    MISMATCH = "MISMATCH"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    GENERATION_FAILED = "GENERATION_FAILED"
    TIMEOUT = "TIMEOUT"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    COMPILE_ERROR = "COMPILE_ERROR"


class TestCaseRecord(BaseModel):
    """Detailed outcome of a single generated testcase."""

    __test__ = False

    test_id: int = Field(description="Sequential 1-based testcase index.")
    subtask_id: int = Field(default=1, description="Subtask identifier.")
    seed: int = Field(description="64-bit random seed passed to generator.")
    status: TestcaseStatus = Field(description="Final testcase verification status.")
    input_text: str = Field(description="The complete problem input string.")
    brute_output: Optional[str] = Field(
        default=None, description="Output emitted by brute-force oracle."
    )
    optimized_output: Optional[str] = Field(
        default=None, description="Output emitted by optimized solution."
    )
    brute_duration_ms: float = Field(default=0.0, description="Brute-force run duration in ms.")
    optimized_duration_ms: float = Field(default=0.0, description="Optimized run duration in ms.")
    mismatch_detail: Optional[str] = Field(
        default=None, description="Detailed explanation of token mismatch if outputs differed."
    )
    error_message: Optional[str] = Field(
        default=None, description="Diagnostic error message (e.g. validator failure or crash log)."
    )


class DifferentialRunResult(BaseModel):
    """Summary of a complete differential testing run across multiple testcases."""

    problem_id: str = Field(description="Identifier or name of the problem.")
    total_cases: int = Field(default=0, description="Total number of testcases scheduled.")
    passed_cases: int = Field(default=0, description="Count of verified passing testcases.")
    failed_cases: int = Field(default=0, description="Count of failing testcases.")
    overall_status: str = Field(
        default="VERIFIED",
        description="Overall batch status: VERIFIED, MISMATCH_FOUND, VALIDATION_FAILED, COMPILATION_FAILED.",
    )
    testcases: List[TestCaseRecord] = Field(
        default_factory=list, description="List of all evaluated testcase records."
    )
    duration_ms: float = Field(default=0.0, description="Total elapsed time for the batch in ms.")
    error_message: Optional[str] = Field(
        default=None, description="Fatal batch error message if run was aborted."
    )
