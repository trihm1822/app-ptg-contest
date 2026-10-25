"""Differential testing engine coordinating generator, validator, brute, and optimized binaries."""

import time
from pathlib import Path
from typing import Callable, Optional

from ptg.core.comparator import compare_outputs
from ptg.core.runner import IsolatedRunner
from ptg.models.runner import Verdict
from ptg.models.testcase import DifferentialRunResult, TestCaseRecord, TestcaseStatus


class DifferentialEngine:
    """Orchestrates batch test generation, validation, and differential oracle execution in Sandbox."""

    def __init__(self, runner: Optional[IsolatedRunner] = None):
        self.runner = runner or IsolatedRunner()

    def run_differential_suite(
        self,
        problem_dir: Path,
        subtask_id: int = 1,
        count: int = 5,
        start_seed: int = 1000,
        save_dir: Optional[Path] = None,
        stop_on_mismatch: bool = True,
        input_ext: str = ".inp",
        output_ext: str = ".out",
        progress_callback: Optional[Callable[[TestCaseRecord, int, int], None]] = None,
    ) -> DifferentialRunResult:
        """Execute differential testing on a problem directory containing the 4 C++ artifacts.

        Args:
            problem_dir: Directory containing brute.cpp, optimized.cpp, generator.cpp, validator.cpp.
            subtask_id: Subtask / test group identifier (passed to generator as argv[2]).
            count: Number of testcases to generate and evaluate.
            start_seed: Base random seed.
            save_dir: Optional directory to store verified .in and .out files.
            stop_on_mismatch: If True, aborts the run upon first mismatch per ADR-003.
            progress_callback: Optional callback(record, current_idx, total_count) for UI updates.

        Returns:
            DifferentialRunResult summarizing all evaluated testcases and overall verdict.
        """
        start_time = time.perf_counter()
        problem_id = problem_dir.name

        # 1. Check all required C++ files exist
        required_files = {
            "brute": problem_dir / "brute.cpp",
            "optimized": problem_dir / "optimized.cpp",
            "generator": problem_dir / "generator.cpp",
            "validator": problem_dir / "validator.cpp",
        }
        for name, path in required_files.items():
            if not path.exists():
                return DifferentialRunResult(
                    problem_id=problem_id,
                    overall_status="COMPILATION_FAILED",
                    error_message=f"Missing required file: {name}.cpp in {problem_dir}",
                )

        # 2. Compile all 4 binaries inside Docker Sandbox
        import tempfile
        workspace_tmp = Path(tempfile.mkdtemp(prefix=f"ptg_diff_{problem_id}_", dir="temp"))

        try:
            for name, path in required_files.items():
                code = path.read_text(encoding="utf-8")
                comp_res = self.runner.compile(code, binary_name=name, workspace_dir=workspace_tmp)
                if not comp_res.success:
                    return DifferentialRunResult(
                        problem_id=problem_id,
                        overall_status="COMPILATION_FAILED",
                        error_message=f"Compilation failed for {name}.cpp: {comp_res.error_message}",
                        duration_ms=(time.perf_counter() - start_time) * 1000.0,
                    )

            # 3. Batch generation and differential evaluation
            records = []
            passed_count = 0
            failed_count = 0
            overall_status = "VERIFIED"
            fatal_error = None

            if save_dir:
                save_dir.mkdir(parents=True, exist_ok=True)

            for i in range(1, count + 1):
                seed = start_seed + i

                # Step A: Run generator <seed> <subtask_id>
                gen_res = self.runner.execute(
                    "generator",
                    args=[str(seed), str(subtask_id)],
                    workspace_dir=workspace_tmp,
                )
                if gen_res.verdict != Verdict.OK:
                    rec = TestCaseRecord(
                        test_id=i,
                        subtask_id=subtask_id,
                        seed=seed,
                        status=TestcaseStatus.GENERATION_FAILED,
                        input_text="",
                        error_message=f"Generator failed with verdict {gen_res.verdict}: {gen_res.stderr}",
                    )
                    records.append(rec)
                    failed_count += 1
                    if progress_callback:
                        progress_callback(rec, i, count)
                    if stop_on_mismatch:
                        overall_status = "GENERATION_FAILED"
                        break
                    continue

                input_data = gen_res.stdout

                # Step B: Run validator on input
                val_res = self.runner.execute(
                    "validator",
                    stdin_data=input_data,
                    workspace_dir=workspace_tmp,
                )
                if val_res.verdict != Verdict.OK:
                    rec = TestCaseRecord(
                        test_id=i,
                        subtask_id=subtask_id,
                        seed=seed,
                        status=TestcaseStatus.VALIDATION_FAILED,
                        input_text=input_data,
                        error_message=f"Validator rejected input: {val_res.stderr or 'Non-zero exit'}",
                    )
                    records.append(rec)
                    failed_count += 1
                    if progress_callback:
                        progress_callback(rec, i, count)
                    if stop_on_mismatch:
                        overall_status = "VALIDATION_FAILED"
                        fatal_error = f"Validator failed on test #{i} (seed={seed})"
                        break
                    continue

                # Step C: Run brute solution (Oracle)
                brute_res = self.runner.execute(
                    "brute",
                    stdin_data=input_data,
                    workspace_dir=workspace_tmp,
                )
                if brute_res.verdict != Verdict.OK:
                    rec = TestCaseRecord(
                        test_id=i,
                        subtask_id=subtask_id,
                        seed=seed,
                        status=TestcaseStatus.TIMEOUT if brute_res.verdict == Verdict.TLE else TestcaseStatus.RUNTIME_ERROR,
                        input_text=input_data,
                        brute_duration_ms=brute_res.duration_ms,
                        error_message=f"Brute failed with verdict {brute_res.verdict}: {brute_res.stderr}",
                    )
                    records.append(rec)
                    failed_count += 1
                    if progress_callback:
                        progress_callback(rec, i, count)
                    if stop_on_mismatch:
                        overall_status = "RUNTIME_ERROR"
                        break
                    continue

                # Step D: Run optimized solution
                opt_res = self.runner.execute(
                    "optimized",
                    stdin_data=input_data,
                    workspace_dir=workspace_tmp,
                )
                if opt_res.verdict != Verdict.OK:
                    rec = TestCaseRecord(
                        test_id=i,
                        subtask_id=subtask_id,
                        seed=seed,
                        status=TestcaseStatus.TIMEOUT if opt_res.verdict == Verdict.TLE else TestcaseStatus.RUNTIME_ERROR,
                        input_text=input_data,
                        brute_output=brute_res.stdout,
                        brute_duration_ms=brute_res.duration_ms,
                        optimized_duration_ms=opt_res.duration_ms,
                        error_message=f"Optimized failed with verdict {opt_res.verdict}: {opt_res.stderr}",
                    )
                    records.append(rec)
                    failed_count += 1
                    if progress_callback:
                        progress_callback(rec, i, count)
                    if stop_on_mismatch:
                        overall_status = "RUNTIME_ERROR"
                        break
                    continue

                # Step E: Compare outputs (ADR-003)
                is_match, diff_detail = compare_outputs(brute_res.stdout, opt_res.stdout)
                if not is_match:
                    rec = TestCaseRecord(
                        test_id=i,
                        subtask_id=subtask_id,
                        seed=seed,
                        status=TestcaseStatus.MISMATCH,
                        input_text=input_data,
                        brute_output=brute_res.stdout,
                        optimized_output=opt_res.stdout,
                        brute_duration_ms=brute_res.duration_ms,
                        optimized_duration_ms=opt_res.duration_ms,
                        mismatch_detail=diff_detail,
                    )
                    records.append(rec)
                    failed_count += 1
                    if progress_callback:
                        progress_callback(rec, i, count)
                    if stop_on_mismatch:
                        overall_status = "MISMATCH_FOUND"
                        fatal_error = f"Mismatch found on test #{i} (seed={seed}): {diff_detail}"
                        break
                else:
                    # Verified match!
                    rec = TestCaseRecord(
                        test_id=i,
                        subtask_id=subtask_id,
                        seed=seed,
                        status=TestcaseStatus.PASSED,
                        input_text=input_data,
                        brute_output=brute_res.stdout,
                        optimized_output=opt_res.stdout,
                        brute_duration_ms=brute_res.duration_ms,
                        optimized_duration_ms=opt_res.duration_ms,
                    )
                    records.append(rec)
                    passed_count += 1

                    # Save verified testcase files if requested in dedicated testXX/ folders
                    if save_dir:
                        case_folder = save_dir / f"test{i:02d}"
                        case_folder.mkdir(parents=True, exist_ok=True)
                        in_file = case_folder / f"test{i:02d}{input_ext}"
                        out_file = case_folder / f"test{i:02d}{output_ext}"
                        in_file.write_text(input_data, encoding="utf-8")
                        out_file.write_text(opt_res.stdout, encoding="utf-8")

                    if progress_callback:
                        progress_callback(rec, i, count)

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            return DifferentialRunResult(
                problem_id=problem_id,
                total_cases=len(records),
                passed_cases=passed_count,
                failed_cases=failed_count,
                overall_status=overall_status,
                testcases=records,
                duration_ms=round(elapsed_ms, 2),
                error_message=fatal_error,
            )

        finally:
            # Clean up temp workspace
            import shutil
            shutil.rmtree(workspace_tmp, ignore_errors=True)
