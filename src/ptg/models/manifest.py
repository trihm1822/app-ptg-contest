"""Reproducibility manifest models complying with ADR-005."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolchainMetadata(BaseModel):
    """Execution toolchain and compiler environment specifications."""

    ptg_version: str = Field(description="PTG package version.")
    git_commit: Optional[str] = Field(default=None, description="Git commit hash of repository.")
    compiler: str = Field(default="g++ (Debian 12.2.0-14) 12.2.0", description="Compiler binary and version.")
    compiler_flags: List[str] = Field(
        default_factory=lambda: ["-O3", "-std=c++17"],
        description="Flags passed to g++ during compilation."
    )
    runner_image: str = Field(
        default="ptg-cpp-runner:latest",
        description="Docker image identifier used for isolation."
    )
    platform: Optional[str] = Field(default=None, description="Host operating system / architecture.")


class LLMMetadata(BaseModel):
    """Metadata detailing the LLM inference parameters and resource consumption."""

    provider: str = Field(description="Provider name (e.g. gemini, mock).")
    model: str = Field(description="Model identifier (e.g. gemini-3.8-flash).")
    prompt_template_version: str = Field(default="1.0", description="Prompt template version.")
    prompt_hash: Optional[str] = Field(default=None, description="SHA-256 hash of system prompt.")
    total_tokens: int = Field(default=0, description="Total tokens consumed.")
    estimated_cost_usd: float = Field(default=0.0, description="Estimated inference cost in USD.")


class GeneratorMetadata(BaseModel):
    """Generator source information and global seeding parameters."""

    source_hash: str = Field(description="SHA-256 hash of generator.cpp source.")
    validator_source_hash: Optional[str] = Field(default=None, description="SHA-256 hash of validator.cpp source.")
    global_seed: int = Field(description="Base / starting random seed.")
    test_count: int = Field(description="Total number of generated testcases.")


class ArtifactRecord(BaseModel):
    """Cryptographic hash and runtime metrics for an individual test or source artifact."""

    file: str = Field(description="Relative archive path of the artifact.")
    sha256: str = Field(description="SHA-256 cryptographic digest.")
    size_bytes: int = Field(default=0, description="File size in bytes.")
    seed: Optional[int] = Field(default=None, description="Random seed used (for input files).")
    subtask_id: Optional[int] = Field(default=None, description="Subtask identifier.")
    execution_time_ms: Optional[float] = Field(default=None, description="Runtime duration in milliseconds.")


class ReproducibilityManifest(BaseModel):
    """Complete reproducibility manifest packaged as manifest.json / reproducibility.json."""

    manifest_version: str = Field(default="1.0", description="Schema specification version.")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp of manifest generation in UTC ISO 8601."
    )
    problem_id: str = Field(description="Problem identifier.")
    problem_revision_hash: str = Field(description="SHA-256 hash of the problem statement.")
    status: str = Field(default="APPROVED_FOR_EXPORT", description="Lifecycle gate status.")
    verification_status: str = Field(default="PASSED_CHECKS", description="Differential verification status.")
    toolchain: ToolchainMetadata
    llm_metadata: Optional[LLMMetadata] = None
    generator: GeneratorMetadata
    artifacts: List[ArtifactRecord] = Field(default_factory=list)
    custom_properties: Dict[str, Any] = Field(default_factory=dict)
