"""Packaging engine for assembling standard competitive programming ZIP archives and ADR-005 manifests."""

import hashlib
import json
import os
import platform
import subprocess
import zipfile
from pathlib import Path
from typing import List, Optional

from ptg import __version__
from ptg.models.llm import LLMGenerationResult
from ptg.models.manifest import (
    ArtifactRecord,
    GeneratorMetadata,
    LLMMetadata,
    ReproducibilityManifest,
    ToolchainMetadata,
)
from ptg.models.testcase import DifferentialRunResult


def compute_file_sha256(path: Path) -> str:
    """Compute cryptographic SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_text_sha256(text: str) -> str:
    """Compute cryptographic SHA-256 hash of a UTF-8 string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_current_git_commit() -> Optional[str]:
    """Retrieve current Git commit hash if in a Git repository."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=3,
        )
        return res.stdout.strip()
    except Exception:
        return None


class PackagingEngine:
    """Coordinates manifest building and ZIP packaging for export."""

    def __init__(self):
        pass

    def build_manifest(
        self,
        problem_id: str,
        problem_statement_path: Path,
        source_dir: Path,
        diff_result: DifferentialRunResult,
        llm_result: Optional[LLMGenerationResult] = None,
        start_seed: int = 1000,
        subtask_id: int = 1,
    ) -> ReproducibilityManifest:
        """Construct the ReproducibilityManifest adhering strictly to ADR-005."""
        statement_content = problem_statement_path.read_text(encoding="utf-8")
        statement_hash = compute_text_sha256(statement_content)

        # Toolchain
        toolchain = ToolchainMetadata(
            ptg_version=__version__,
            git_commit=get_current_git_commit(),
            compiler="g++ (Debian 12.2.0-14) 12.2.0",
            compiler_flags=["-O3", "-std=c++17"],
            runner_image="ptg-cpp-runner:latest",
            platform=f"{platform.system()} {platform.release()} ({platform.machine()})",
        )

        # LLM Metadata
        llm_meta = None
        if llm_result:
            llm_meta = LLMMetadata(
                provider="gemini" if "gemini" in llm_result.model_name.lower() else "mock",
                model=llm_result.model_name,
                prompt_template_version="1.0",
                total_tokens=llm_result.usage.total_tokens,
                estimated_cost_usd=llm_result.usage.estimated_cost_usd,
            )

        # Generator & Validator
        gen_path = source_dir / "generator.cpp"
        val_path = source_dir / "validator.cpp"
        gen_hash = compute_file_sha256(gen_path) if gen_path.exists() else ""
        val_hash = compute_file_sha256(val_path) if val_path.exists() else None

        generator_meta = GeneratorMetadata(
            source_hash=gen_hash,
            validator_source_hash=val_hash,
            global_seed=start_seed,
            test_count=diff_result.passed_cases,
        )

        # Artifacts list
        artifacts: List[ArtifactRecord] = []

        # Add Source Artifacts
        source_files = {
            "solution/brute.cpp": source_dir / "brute.cpp",
            "solution/optimized.cpp": source_dir / "optimized.cpp",
            "generator/generator.cpp": gen_path,
            "generator/validator.cpp": val_path,
            "explanation.md": source_dir / "explanation.md",
        }
        for rel_path, fpath in source_files.items():
            if fpath.exists():
                artifacts.append(
                    ArtifactRecord(
                        file=rel_path,
                        sha256=compute_file_sha256(fpath),
                        size_bytes=fpath.stat().st_size,
                    )
                )

        # Add Testcase Artifacts
        for rec in diff_result.testcases:
            in_file_name = f"tests/test_{rec.test_id:02d}.inp"
            out_file_name = f"tests/test_{rec.test_id:02d}.out"

            # Input artifact
            artifacts.append(
                ArtifactRecord(
                    file=in_file_name,
                    sha256=compute_text_sha256(rec.input_text),
                    size_bytes=len(rec.input_text.encode("utf-8")),
                    seed=rec.seed,
                    subtask_id=rec.subtask_id,
                )
            )

            # Output artifact
            if rec.optimized_output is not None:
                artifacts.append(
                    ArtifactRecord(
                        file=out_file_name,
                        sha256=compute_text_sha256(rec.optimized_output),
                        size_bytes=len(rec.optimized_output.encode("utf-8")),
                        execution_time_ms=rec.optimized_duration_ms,
                    )
                )

        return ReproducibilityManifest(
            manifest_version="1.0",
            problem_id=problem_id,
            problem_revision_hash=statement_hash,
            status="APPROVED_FOR_EXPORT" if diff_result.overall_status == "VERIFIED" else "NEEDS_REVIEW",
            verification_status="PASSED_CHECKS" if diff_result.overall_status == "VERIFIED" else diff_result.overall_status,
            toolchain=toolchain,
            llm_metadata=llm_meta,
            generator=generator_meta,
            artifacts=artifacts,
        )

    def package_export_zip(
        self,
        problem_statement_path: Path,
        source_dir: Path,
        tests_dir: Path,
        manifest: ReproducibilityManifest,
        output_zip_path: Path,
    ) -> Path:
        """Create a clean, standardized ZIP archive containing all artifacts and manifest."""
        output_zip_path.parent.mkdir(parents=True, exist_ok=True)

        manifest_json_bytes = json.dumps(
            manifest.model_dump(),
            indent=2,
            ensure_ascii=False,
        ).encode("utf-8")

        with zipfile.ZipFile(output_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # 1. Problem statement
            zf.write(problem_statement_path, arcname="problem.md")

            # 2. Explanation
            exp_file = source_dir / "explanation.md"
            if exp_file.exists():
                zf.write(exp_file, arcname="explanation.md")

            # 3. Solutions
            if (source_dir / "brute.cpp").exists():
                zf.write(source_dir / "brute.cpp", arcname="solution/brute.cpp")
            if (source_dir / "optimized.cpp").exists():
                zf.write(source_dir / "optimized.cpp", arcname="solution/optimized.cpp")

            # 4. Generator & Validator
            if (source_dir / "generator.cpp").exists():
                zf.write(source_dir / "generator.cpp", arcname="generator/generator.cpp")
            if (source_dir / "validator.cpp").exists():
                zf.write(source_dir / "validator.cpp", arcname="generator/validator.cpp")

            # 5. Verified Tests (.inp and .out)
            if tests_dir.exists():
                for test_file in sorted(tests_dir.iterdir()):
                    if test_file.is_file() and test_file.suffix in [".inp", ".out", ".in"]:
                        zf.write(test_file, arcname=f"tests/{test_file.name}")

            # 6. Manifest files (both reproducibility.json and manifest.json for compatibility)
            zf.writestr("reproducibility.json", manifest_json_bytes)
            zf.writestr("manifest.json", manifest_json_bytes)

        return output_zip_path
