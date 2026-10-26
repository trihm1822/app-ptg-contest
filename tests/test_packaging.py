"""Unit tests for packaging engine, manifest creation, and ZIP archive integrity."""

import tempfile
import zipfile
from pathlib import Path

from ptg.core.packaging import PackagingEngine, compute_file_sha256, compute_text_sha256
from ptg.models.testcase import DifferentialRunResult, TestCaseRecord, TestcaseStatus


def test_sha256_computation():
    """Verify compute_file_sha256 matches expected hash for known text."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        sample_file = Path(tmp_dir) / "sample.txt"
        sample_file.write_text("Hello PTG World", encoding="utf-8")

        expected_hash = compute_text_sha256("Hello PTG World")
        actual_hash = compute_file_sha256(sample_file)

        assert actual_hash == expected_hash
        assert len(actual_hash) == 64


def test_packaging_engine_export_zip_creation():
    """Verify that PackagingEngine builds valid reproducibility manifest and ZIP structure."""
    with tempfile.TemporaryDirectory(prefix="ptg_pkg_test_") as tmp_dir:
        base_dir = Path(tmp_dir)

        # 1. Setup problem.md
        prob_file = base_dir / "problem.md"
        prob_file.write_text("# Two Sum\nFind two indices.", encoding="utf-8")

        # 2. Setup source directory with mock C++ files
        src_dir = base_dir / "src"
        src_dir.mkdir()
        (src_dir / "brute.cpp").write_text("// brute", encoding="utf-8")
        (src_dir / "optimized.cpp").write_text("// opt", encoding="utf-8")
        (src_dir / "generator.cpp").write_text("// gen", encoding="utf-8")
        (src_dir / "validator.cpp").write_text("// val", encoding="utf-8")
        (src_dir / "explanation.md").write_text("# Explanation", encoding="utf-8")

        # 3. Setup tests directory with subfolder
        tests_dir = base_dir / "tests"
        case_01 = tests_dir / "test01"
        case_01.mkdir(parents=True, exist_ok=True)
        (case_01 / "test01.inp").write_text("10 20\n", encoding="utf-8")
        (case_01 / "test01.out").write_text("30\n", encoding="utf-8")

        # 4. Construct mock diff result
        diff_res = DifferentialRunResult(
            problem_id="two_sum",
            total_cases=1,
            passed_cases=1,
            failed_cases=0,
            overall_status="VERIFIED",
            testcases=[
                TestCaseRecord(
                    test_id=1,
                    subtask_id=1,
                    seed=1001,
                    status=TestcaseStatus.PASSED,
                    input_text="10 20\n",
                    brute_output="30\n",
                    optimized_output="30\n",
                    brute_duration_ms=12.0,
                    optimized_duration_ms=4.0,
                )
            ],
            duration_ms=100.0,
        )

        engine = PackagingEngine()

        # Build manifest
        manifest = engine.build_manifest(
            problem_id="two_sum",
            problem_statement_path=prob_file,
            source_dir=src_dir,
            diff_result=diff_res,
            start_seed=1000,
            subtask_id=1,
        )

        assert manifest.problem_id == "two_sum"
        assert manifest.status == "APPROVED_FOR_EXPORT"
        assert manifest.verification_status == "PASSED_CHECKS"
        assert manifest.generator.global_seed == 1000
        assert len(manifest.artifacts) >= 6  # 5 sources + 2 test artifacts

        # Export ZIP
        zip_out = base_dir / "output" / "two_sum_export.zip"
        engine.package_export_zip(
            problem_statement_path=prob_file,
            source_dir=src_dir,
            tests_dir=tests_dir,
            manifest=manifest,
            output_zip_path=zip_out,
        )

        assert zip_out.exists()
        assert zip_out.stat().st_size > 0

        # Inspect ZIP archive contents
        with zipfile.ZipFile(zip_out, "r") as zf:
            namelist = zf.namelist()
            assert "problem.md" in namelist
            assert "explanation.md" in namelist
            assert "solution/brute.cpp" in namelist
            assert "solution/optimized.cpp" in namelist
            assert "generator/generator.cpp" in namelist
            assert "generator/validator.cpp" in namelist
            assert "tests/test01/test01.inp" in namelist
            assert "tests/test01/test01.out" in namelist
            assert "reproducibility.json" in namelist
            assert "manifest.json" in namelist

            # Verify manifest content inside archive
            manifest_data = zf.read("reproducibility.json").decode("utf-8")
            assert "two_sum" in manifest_data
            assert "APPROVED_FOR_EXPORT" in manifest_data


def test_packaging_engine_themis_classic_layout():
    """Verify that PackagingEngine correctly produces Test01/Test01.INP in classic mode."""
    with tempfile.TemporaryDirectory(prefix="ptg_themis_test_") as tmp_dir:
        base_dir = Path(tmp_dir)

        prob_file = base_dir / "problem.md"
        prob_file.write_text("# Problem", encoding="utf-8")

        src_dir = base_dir / "src"
        src_dir.mkdir()
        (src_dir / "brute.cpp").write_text("// brute", encoding="utf-8")

        tests_dir = base_dir / "tests"
        case_01 = tests_dir / "Test01"
        case_01.mkdir(parents=True, exist_ok=True)
        (case_01 / "Test01.INP").write_text("10 20\n", encoding="utf-8")
        (case_01 / "Test01.OUT").write_text("30\n", encoding="utf-8")

        diff_res = DifferentialRunResult(
            problem_id="problem",
            total_cases=1,
            passed_cases=1,
            failed_cases=0,
            overall_status="VERIFIED",
            testcases=[
                TestCaseRecord(
                    test_id=1,
                    subtask_id=1,
                    seed=1001,
                    status=TestcaseStatus.PASSED,
                    input_text="10 20\n",
                    optimized_output="30\n",
                )
            ],
            duration_ms=50.0,
        )

        engine = PackagingEngine()
        manifest = engine.build_manifest(
            problem_id="problem",
            problem_statement_path=prob_file,
            source_dir=src_dir,
            diff_result=diff_res,
            themis_classic=True,
        )

        zip_out = base_dir / "problem_themis.zip"
        engine.package_export_zip(
            problem_statement_path=prob_file,
            source_dir=src_dir,
            tests_dir=tests_dir,
            manifest=manifest,
            output_zip_path=zip_out,
        )

        with zipfile.ZipFile(zip_out, "r") as zf:
            namelist = zf.namelist()
            assert "tests/Test01/Test01.INP" in namelist
            assert "tests/Test01/Test01.OUT" in namelist
