"""Execution and compilation models for the isolated C++ runner."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Verdict(str, Enum):
    """Execution outcome verdicts according to competitive programming standards."""
    OK = "OK"
    COMPILE_ERROR = "COMPILE_ERROR"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    TIME_LIMIT_EXCEEDED = "TIME_LIMIT_EXCEEDED"
    MEMORY_LIMIT_EXCEEDED = "MEMORY_LIMIT_EXCEEDED"
    OUTPUT_LIMIT_EXCEEDED = "OUTPUT_LIMIT_EXCEEDED"
    INFRASTRUCTURE_ERROR = "INFRASTRUCTURE_ERROR"


class SandboxLimits(BaseModel):
    """Resource constraints enforced on containerized compilation and execution."""
    cpu_limit: float = Field(default=1.0, description="Max CPU cores allocated to container")
    memory_limit: str = Field(default="256m", description="Max RAM allocated for execution")
    compile_memory_limit: str = Field(default="512m", description="Max RAM for g++ compiler")
    compile_timeout_sec: int = Field(default=10, description="Max wall-clock seconds for compilation")
    exec_timeout_sec: int = Field(default=5, description="Max wall-clock seconds for execution")
    pids_limit: int = Field(default=32, description="Max processes/threads to prevent fork bombs")
    max_output_bytes: int = Field(default=10 * 1024 * 1024, description="Max stdout/stderr bytes captured (10MB)")


class CompileResult(BaseModel):
    """Detailed result of compiling C++ source code inside the sandbox."""
    success: bool
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    binary_name: Optional[str] = None
    error_message: Optional[str] = None


class ExecutionResult(BaseModel):
    """Detailed result of executing a compiled binary inside the sandbox."""
    verdict: Verdict = Verdict.OK
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    memory_kb: Optional[int] = None
