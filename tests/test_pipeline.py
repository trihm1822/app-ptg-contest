"""Unit tests for EndToEndPipeline connecting CodeGenerator, DifferentialEngine, and Packaging."""

import tempfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

from ptg.core.pipeline import EndToEndPipeline
from ptg.integrations.llm.mock import MockLLMProvider
from ptg.models.runner import CompileResult, ExecutionResult, Verdict


def test_pipeline_mock_execution():
    """Verify EndToEndPipeline runs all phases and produces valid export archive."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)

        # 1. Problem file
        prob_file = base_dir / "01_two_sum.md"
        prob_file.write_text("# Two Sum\nFind two numbers summing to target.", encoding="utf-8")

        target_zip = base_dir / "export.zip"

        # 2. Mock runner for Sandbox
        mock_runner = MagicMock()
        mock_runner.compile.return_value = CompileResult(success=True, exit_code=0)

        def mock_execute(binary_name, args=None, stdin_data=None, workspace_dir=None):
            if binary_name == "generator":
                return ExecutionResult(verdict=Verdict.OK, stdout="2 10\n4 6\n")
            elif binary_name == "validator":
                return ExecutionResult(verdict=Verdict.OK)
            elif binary_name in ["brute", "optimized"]:
                return ExecutionResult(verdict=Verdict.OK, stdout="1 2\n", duration_ms=2.0)
            return ExecutionResult(verdict=Verdict.OK)

        mock_runner.execute.side_effect = mock_execute

        # 3. Instantiate pipeline with MockLLMProvider
        from ptg.core.code_generator import CodeGenerator
        from ptg.core.differential_engine import DifferentialEngine

        code_gen = CodeGenerator(provider=MockLLMProvider())
        diff_engine = DifferentialEngine(runner=mock_runner)

        pipeline = EndToEndPipeline(
            code_generator=code_gen,
            differential_engine=diff_engine,
        )

        summary = pipeline.run(
            problem_path=prob_file,
            output_zip_path=target_zip,
            work_dir=base_dir / "work",
            use_mock=True,
            count=3,
            subtask_id=1,
            start_seed=1000,
        )

        assert summary.success is True
        assert summary.problem_id == "01_two_sum"
        assert summary.diff_result.passed_cases == 3
        assert summary.zip_path.exists()
        assert summary.zip_size_bytes > 0

        # Check files inside generated ZIP
        with zipfile.ZipFile(summary.zip_path, "r") as zf:
            files = zf.namelist()
            assert "problem.md" in files
            assert "solution/brute.cpp" in files
            assert "solution/optimized.cpp" in files
            assert "tests/test01/test01.inp" in files
            assert "tests/test01/test01.out" in files
            assert "tests/test03/test03.inp" in files
            assert "tests/test03/test03.out" in files
            assert "reproducibility.json" in files
