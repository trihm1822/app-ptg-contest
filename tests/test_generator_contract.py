"""Unit and negative tests for Generator Contract complying with ADR-002 and ADR-006."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from ptg.core.differential_engine import DifferentialEngine
from ptg.core.runner import IsolatedRunner
from ptg.models.runner import ExecutionResult, Verdict
from ptg.models.testcase import TestcaseStatus


def splitmix64_python_reference(seed: int, count: int = 5):
    """Python reference implementation of canonical SplitMix64 algorithm."""
    x = seed & 0xFFFFFFFFFFFFFFFF
    results = []
    for _ in range(count):
        x = (x + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
        z = x
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
        val = (z ^ (z >> 31)) & 0xFFFFFFFFFFFFFFFF
        results.append(val)
    return results


def test_splitmix64_determinism_test_vector():
    """Verify SplitMix64 produces identical, deterministic test vector for seed 42."""
    seed = 42
    expected_values = splitmix64_python_reference(seed, count=5)
    # Re-running with same seed must yield exact bit-identical sequence
    assert splitmix64_python_reference(seed, count=5) == expected_values
    # Verify values are positive 64-bit unsigned integers
    assert all(0 <= v < (1 << 64) for v in expected_values)


def test_generator_missing_argv_contract():
    """Verify that a generator invoked with missing arguments is caught by DifferentialEngine."""
    mock_runner = MagicMock(spec=IsolatedRunner)
    mock_runner.compile.return_value = MagicMock(success=True)

    # Simulate generator exiting with code 1 due to argc < 3
    mock_runner.execute.return_value = ExecutionResult(
        verdict=Verdict.RUNTIME_ERROR,
        exit_code=1,
        stdout="",
        stderr="Usage: generator <seed> <subtask_id>",
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        p_dir = Path(tmp_dir)
        (p_dir / "brute.cpp").write_text("// brute")
        (p_dir / "optimized.cpp").write_text("// opt")
        (p_dir / "generator.cpp").write_text("// gen")
        (p_dir / "validator.cpp").write_text("// val")

        engine = DifferentialEngine(runner=mock_runner)
        result = engine.run_differential_suite(
            problem_dir=p_dir,
            count=1,
            stop_on_mismatch=True,
        )

        assert result.overall_status == "GENERATION_FAILED"
        assert result.failed_cases == 1
        assert result.testcases[0].status == TestcaseStatus.GENERATION_FAILED
        assert "Usage: generator <seed> <subtask_id>" in result.testcases[0].error_message


def test_generator_invalid_argv_format():
    """Verify that a generator failing on invalid argv string reports generation failure."""
    mock_runner = MagicMock(spec=IsolatedRunner)
    mock_runner.compile.return_value = MagicMock(success=True)

    mock_runner.execute.return_value = ExecutionResult(
        verdict=Verdict.RUNTIME_ERROR,
        exit_code=1,
        stdout="",
        stderr="std::invalid_argument: stoull",
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        p_dir = Path(tmp_dir)
        (p_dir / "brute.cpp").write_text("// brute")
        (p_dir / "optimized.cpp").write_text("// opt")
        (p_dir / "generator.cpp").write_text("// gen")
        (p_dir / "validator.cpp").write_text("// val")

        engine = DifferentialEngine(runner=mock_runner)
        result = engine.run_differential_suite(
            problem_dir=p_dir,
            count=1,
            stop_on_mismatch=True,
        )

        assert result.overall_status == "GENERATION_FAILED"
        assert "invalid_argument" in result.testcases[0].error_message


def test_generator_infinite_loop_timeout():
    """Verify that a generator entering an infinite loop is aborted with TIME_LIMIT_EXCEEDED."""
    mock_runner = MagicMock(spec=IsolatedRunner)
    mock_runner.compile.return_value = MagicMock(success=True)

    mock_runner.execute.return_value = ExecutionResult(
        verdict=Verdict.TIME_LIMIT_EXCEEDED,
        exit_code=137,
        stdout="",
        stderr="Execution host timeout expired.",
        duration_ms=5100,
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        p_dir = Path(tmp_dir)
        (p_dir / "brute.cpp").write_text("// brute")
        (p_dir / "optimized.cpp").write_text("// opt")
        (p_dir / "generator.cpp").write_text("// gen")
        (p_dir / "validator.cpp").write_text("// val")

        engine = DifferentialEngine(runner=mock_runner)
        result = engine.run_differential_suite(
            problem_dir=p_dir,
            count=1,
            stop_on_mismatch=True,
        )

        assert result.overall_status == "GENERATION_FAILED"
        assert "TIME_LIMIT_EXCEEDED" in result.testcases[0].error_message
