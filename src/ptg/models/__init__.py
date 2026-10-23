"""Data models for PTG."""

from .runner import CompileResult, ExecutionResult, SandboxLimits, Verdict

__all__ = ["Verdict", "SandboxLimits", "CompileResult", "ExecutionResult"]
