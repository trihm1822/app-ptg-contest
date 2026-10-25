"""Unit tests for PackagingEngine, SHA-256 calculation, and ADR-005 manifest generation."""

import tempfile
import zipfile
from pathlib import Path

from ptg.core.packaging import (
    PackagingEngine,
    compute_file_sha256,
    compute_text_sha256,
)
from ptg.models.manifest import (
    GeneratorMetadata,
    ReproducibilityManifest,
    ToolchainMetadata,
)
from ptg.models.testcase import DifferentialRunResult, TestCaseRecord, TestcaseStatus


def test_sha256_helpers():
    """Verify SHA-256 hashing functions produce correct hex strings."""
    text = "hello competitive programming"
    hash_str = compute_text_sha256(text)
    assert len(hash_str) == 64

    with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as tmp:
        tmp.write(text)
        tmp.flush()
        tmp_path = Path(tmp.name)

    try:
        file_hash = compute_file_sha256(tmp_path)
        assert file_hash == hash_str
    finally:
        tmp_path.unlink()


def test_reproducibility_manifest_validation():
    """Verify ReproducibilityManifest validates according to ADR-005 specification."""
    manifest = ReproducibilityManifest(
        problem_id="01_two_sum",
        problem_revision_hash="a1b2c3d4e5f6",
        status="APPROVED_FOR_EXPORT",
        verification_status="PASSED_CHECKS",
        toolchain=ToolchainMetadata(ptg_version="0.1.0"),
        generator=GeneratorMetadata(
            source_hash="sha256:12345",
            global_seed=1000,
            test_count=5,
        ),
    )
    assert manifest.manifest_version == "1.0"
    assert manifest.problem_id == "01_two_sum"
    assert manifest.toolchain.compiler_flags == ["-O3", "-std=c++17"]


def test_packaging_engine_export_zip_creation():
    """Verify PackagingEngine creates a standard ZIP archive with all expected paths."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)

        # 1. Setup problem statement
        prob_file = base_dir / "problem.md"
        prob_file.write_text("# Two Sum\nFind two numbers.", encoding="utf-8")

        # 2. Setup source directory
        src_dir = base_dir / "sources"
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
                    optimized_output="30\n",
                    optimized_duration_ms=1.5,
                )
            ],
        )

        engine = PackagingEngine()
        manifest = engine.build_manifest(
            problem_id="two_sum",
            problem_statement_path=prob_file,
            source_dir=src_dir,
            diff_result=diff_res,
            start_seed=1000,
        )

        zip_out = base_dir / "output.zip"
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
