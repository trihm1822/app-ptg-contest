"""End-to-end pipeline orchestrator connecting CodeGenerator, DifferentialEngine, and PackagingEngine."""

import time
from pathlib import Path
from typing import Callable, Optional
from pydantic import BaseModel

from ptg.core.code_generator import CodeGenerator
from ptg.core.differential_engine import DifferentialEngine
from ptg.core.packaging import PackagingEngine
from ptg.models.llm import LLMGenerationResult
from ptg.models.manifest import ReproducibilityManifest
from ptg.models.testcase import DifferentialRunResult, TestCaseRecord


class PipelineExecutionSummary(BaseModel):
    """Encapsulates the end-to-end outcome of a full PTG run-all pipeline execution."""

    problem_id: str
    zip_path: Path
    zip_size_bytes: int
    manifest: ReproducibilityManifest
    llm_result: Optional[LLMGenerationResult]
    diff_result: DifferentialRunResult
    total_duration_ms: float
    success: bool
    error_message: Optional[str] = None


class EndToEndPipeline:
    """Master orchestrator executing the entire Phase 0 lifecycle in a single call."""

    def __init__(
        self,
        code_generator: Optional[CodeGenerator] = None,
        differential_engine: Optional[DifferentialEngine] = None,
        packaging_engine: Optional[PackagingEngine] = None,
    ):
        self.code_generator = code_generator or CodeGenerator()
        self.differential_engine = differential_engine or DifferentialEngine()
        self.packaging_engine = packaging_engine or PackagingEngine()

    def run(
        self,
        problem_path: Path,
        output_zip_path: Path,
        work_dir: Optional[Path] = None,
        model_name: str = "gemini-3.8-flash",
        temperature: float = 0.2,
        use_cache: bool = True,
        use_mock: bool = False,
        count: int = 5,
        subtask_id: int = 1,
        start_seed: int = 1000,
        strict_whitespace: bool = False,
        themis_classic: bool = False,
        progress_callback: Optional[Callable[[str, Optional[TestCaseRecord]], None]] = None,
    ) -> PipelineExecutionSummary:
        """Execute full pipeline: Problem MD -> LLM Generation -> Sandbox Diff Testing -> Package ZIP.

        Returns:
            PipelineExecutionSummary with all metrics, manifest, and archive location.
        """
        start_time = time.perf_counter()
        problem_id = problem_path.stem

        if not problem_path.exists():
            raise FileNotFoundError(f"Problem file not found: {problem_path}")

        # Workspace directory setup
        base_work_dir = work_dir or (Path("output") / problem_id)
        artifacts_dir = base_work_dir
        tests_dir = base_work_dir / "tests"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        tests_dir.mkdir(parents=True, exist_ok=True)

        # -------------------------------------------------------------
        # Phase A: LLM Code Generation (Stage 2)
        # -------------------------------------------------------------
        if progress_callback:
            progress_callback("generating_code", None)

        llm_res, files = self.code_generator.generate_from_file(
            problem_path=problem_path,
            output_dir=artifacts_dir,
            model_name=model_name,
            temperature=temperature,
            use_cache=use_cache,
            use_mock=use_mock,
        )

        # -------------------------------------------------------------
        # Phase B: Differential Testing Suite (Stage 3)
        # -------------------------------------------------------------
        if progress_callback:
            progress_callback("running_differential", None)

        def on_diff_progress(rec, current, total):
            if progress_callback:
                progress_callback(f"test_{current}_{total}", rec)

        diff_res = self.differential_engine.run_differential_suite(
            problem_dir=artifacts_dir,
            subtask_id=subtask_id,
            count=count,
            start_seed=start_seed,
            save_dir=tests_dir,
            stop_on_mismatch=True,
            strict_whitespace=strict_whitespace,
            themis_classic=themis_classic,
            progress_callback=on_diff_progress,
        )

        if diff_res.overall_status != "VERIFIED":
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return PipelineExecutionSummary(
                problem_id=problem_id,
                zip_path=output_zip_path,
                zip_size_bytes=0,
                manifest=ReproducibilityManifest(
                    problem_id=problem_id,
                    problem_revision_hash="",
                    toolchain=self.packaging_engine.build_manifest(
                        problem_id=problem_id,
                        problem_statement_path=problem_path,
                        source_dir=artifacts_dir,
                        diff_result=diff_res,
                        llm_result=llm_res,
                    ).toolchain,
                    generator=self.packaging_engine.build_manifest(
                        problem_id=problem_id,
                        problem_statement_path=problem_path,
                        source_dir=artifacts_dir,
                        diff_result=diff_res,
                        llm_result=llm_res,
                    ).generator,
                ),
                llm_result=llm_res,
                diff_result=diff_res,
                total_duration_ms=round(elapsed_ms, 2),
                success=False,
                error_message=f"Pipeline halted during differential testing: {diff_res.overall_status} ({diff_res.error_message})",
            )

        # -------------------------------------------------------------
        # Phase C: Manifest Construction & Packaging (Stage 4)
        # -------------------------------------------------------------
        if progress_callback:
            progress_callback("packaging_zip", None)

        manifest = self.packaging_engine.build_manifest(
            problem_id=problem_id,
            problem_statement_path=problem_path,
            source_dir=artifacts_dir,
            diff_result=diff_res,
            llm_result=llm_res,
            start_seed=start_seed,
            subtask_id=subtask_id,
            themis_classic=themis_classic,
        )

        # Write manifest locally in output directory for inspection
        (artifacts_dir / "reproducibility.json").write_text(
            manifest.model_dump_json(indent=2),
            encoding="utf-8",
        )

        # Package into final ZIP
        final_zip = self.packaging_engine.package_export_zip(
            problem_statement_path=problem_path,
            source_dir=artifacts_dir,
            tests_dir=tests_dir,
            manifest=manifest,
            output_zip_path=output_zip_path,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return PipelineExecutionSummary(
            problem_id=problem_id,
            zip_path=final_zip,
            zip_size_bytes=final_zip.stat().st_size,
            manifest=manifest,
            llm_result=llm_res,
            diff_result=diff_res,
            total_duration_ms=round(elapsed_ms, 2),
            success=True,
        )
