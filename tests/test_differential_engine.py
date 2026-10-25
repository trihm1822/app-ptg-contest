"""Unit tests for DifferentialEngine testing compilation, execution, validation, and mismatch logic."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from ptg.core.differential_engine import DifferentialEngine
from ptg.models.runner import CompileResult, ExecutionResult, Verdict
from ptg.models.testcase import TestcaseStatus


def setup_mock_problem_dir(tmp_path: Path):
    """Create a dummy problem directory with 4 C++ files."""
    prob_dir = tmp_path / "mock_problem"
    prob_dir.mkdir(parents=True, exist_ok=True)
    (prob_dir / "brute.cpp").write_text("// brute", encoding="utf-8")
    (prob_dir / "optimized.cpp").write_text("// opt", encoding="utf-8")
    (prob_dir / "generator.cpp").write_text("// gen", encoding="utf-8")
    (prob_dir / "validator.cpp").write_text("// val", encoding="utf-8")
    return prob_dir


def test_differential_engine_missing_files():
    """Verify engine flags missing required files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        empty_dir = Path(tmp_dir) / "empty_problem"
        empty_dir.mkdir()
        engine = DifferentialEngine()
        result = engine.run_differential_suite(problem_dir=empty_dir)
        assert result.overall_status == "COMPILATION_FAILED"
        assert "Missing required file" in result.error_message


def test_differential_engine_compilation_failure():
    """Verify engine handles compilation failure properly."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        prob_dir = setup_mock_problem_dir(Path(tmp_dir))

        mock_runner = MagicMock()
        mock_runner.compile.return_value = CompileResult(
            success=False,
            exit_code=1,
            error_message="g++ syntax error: expected ';'",
        )

        engine = DifferentialEngine(runner=mock_runner)
        result = engine.run_differential_suite(problem_dir=prob_dir)

        assert result.overall_status == "COMPILATION_FAILED"
        assert "Compilation failed" in result.error_message


def test_differential_engine_all_passed():
    """Verify engine passes when generator, validator, brute, and optimized all succeed and match."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        prob_dir = setup_mock_problem_dir(Path(tmp_dir))
        save_dir = Path(tmp_dir) / "saved_tests"

        mock_runner = MagicMock()
        # Compile always succeeds
        mock_runner.compile.return_value = CompileResult(success=True, exit_code=0)

        # Execution mock based on binary name
        def mock_execute(binary_name, args=None, stdin_data=None, workspace_dir=None):
            if binary_name == "generator":
                return ExecutionResult(verdict=Verdict.OK, exit_code=0, stdout="10 20\n1 2 3\n")
            elif binary_name == "validator":
                return ExecutionResult(verdict=Verdict.OK, exit_code=0, stdout="")
            elif binary_name == "brute":
                return ExecutionResult(verdict=Verdict.OK, exit_code=0, stdout="42\n", duration_ms=5.0)
            elif binary_name == "optimized":
                return ExecutionResult(verdict=Verdict.OK, exit_code=0, stdout="42\n", duration_ms=2.0)
            return ExecutionResult(verdict=Verdict.RE, exit_code=1)

        mock_runner.execute.side_effect = mock_execute

        engine = DifferentialEngine(runner=mock_runner)
        result = engine.run_differential_suite(
            problem_dir=prob_dir,
            count=3,
            subtask_id=1,
            start_seed=1000,
            save_dir=save_dir,
        )

        assert result.overall_status == "VERIFIED"
        assert result.total_cases == 3
        assert result.passed_cases == 3
        assert result.failed_cases == 0

        # Check saved testcase files (.inp and .out)
        assert (save_dir / "test_01.inp").exists()
        assert (save_dir / "test_01.out").exists()
        assert (save_dir / "test_03.inp").exists()
        assert (save_dir / "test_03.out").read_text(encoding="utf-8") == "42\n"


def test_differential_engine_validator_failed():
    """Verify engine halts when validator rejects generator input."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        prob_dir = setup_mock_problem_dir(Path(tmp_dir))

        mock_runner = MagicMock()
        mock_runner.compile.return_value = CompileResult(success=True, exit_code=0)

        def mock_execute(binary_name, args=None, stdin_data=None, workspace_dir=None):
            if binary_name == "generator":
                return ExecutionResult(verdict=Verdict.OK, exit_code=0, stdout="BAD INPUT")
            elif binary_name == "validator":
                return ExecutionResult(verdict=Verdict.RUNTIME_ERROR, exit_code=1, stderr="N out of bounds")
            return ExecutionResult(verdict=Verdict.OK, exit_code=0)

        mock_runner.execute.side_effect = mock_execute

        engine = DifferentialEngine(runner=mock_runner)
        result = engine.run_differential_suite(problem_dir=prob_dir, count=3, stop_on_mismatch=True)

        assert result.overall_status == "VALIDATION_FAILED"
        assert result.failed_cases == 1
        assert result.testcases[0].status == TestcaseStatus.VALIDATION_FAILED
        assert "Validator rejected input" in result.testcases[0].error_message


def test_differential_engine_mismatch_detected():
    """Verify engine detects disagreement between brute and optimized outputs per ADR-003."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        prob_dir = setup_mock_problem_dir(Path(tmp_dir))

        mock_runner = MagicMock()
        mock_runner.compile.return_value = CompileResult(success=True, exit_code=0)

        def mock_execute(binary_name, args=None, stdin_data=None, workspace_dir=None):
            if binary_name == "generator":
                return ExecutionResult(verdict=Verdict.OK, exit_code=0, stdout="input data")
            elif binary_name == "validator":
                return ExecutionResult(verdict=Verdict.OK, exit_code=0)
            elif binary_name == "brute":
                return ExecutionResult(verdict=Verdict.OK, exit_code=0, stdout="100\n", duration_ms=4.0)
            elif binary_name == "optimized":
                # Returns 999 instead of 100!
                return ExecutionResult(verdict=Verdict.OK, exit_code=0, stdout="999\n", duration_ms=1.0)
            return ExecutionResult(verdict=Verdict.OK)

        mock_runner.execute.side_effect = mock_execute

        engine = DifferentialEngine(runner=mock_runner)
        result = engine.run_differential_suite(problem_dir=prob_dir, count=5, stop_on_mismatch=True)

        assert result.overall_status == "MISMATCH_FOUND"
        assert result.failed_cases == 1
        assert result.total_cases == 1  # Halted on first mismatch
        assert result.testcases[0].status == TestcaseStatus.MISMATCH
        assert "Token mismatch at token #1" in result.testcases[0].mismatch_detail
