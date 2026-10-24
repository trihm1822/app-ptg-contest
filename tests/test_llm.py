"""Automated unit tests for Stage 2 LLM Integration, schemas, caching, and generation pipeline."""

import tempfile
from pathlib import Path

import pytest
from ptg.core.cache import (
    compute_cache_key,
    get_cached_generation,
    save_cached_generation,
)
from ptg.core.code_generator import CodeGenerator
from ptg.integrations.llm.gemini import estimate_gemini_cost, strip_code_fences
from ptg.integrations.llm.mock import MockLLMProvider
from ptg.models.llm import (
    GeneratedArtifacts,
    LLMGenerationRequest,
    LLMGenerationResult,
    LLMUsageRecord,
)


def test_generated_artifacts_schema():
    """Verify GeneratedArtifacts schema enforces all 5 fields."""
    data = {
        "brute_code": "int main() {}",
        "optimized_code": "int main() {}",
        "generator_code": "int main() {}",
        "validator_code": "int main() {}",
        "explanation_markdown": "# Explanation",
    }
    artifacts = GeneratedArtifacts.model_validate(data)
    assert artifacts.brute_code == "int main() {}"
    assert artifacts.explanation_markdown == "# Explanation"

    # Missing a required field must raise ValidationError
    incomplete = data.copy()
    del incomplete["brute_code"]
    with pytest.raises(Exception):
        GeneratedArtifacts.model_validate(incomplete)


def test_cache_key_determinism():
    """Verify cache key produces consistent SHA-256 for identical inputs."""
    key1 = compute_cache_key(
        provider="gemini",
        model="gemini-3.8-flash",
        prompt_text="System instructions",
        statement_text="# Problem 1\nInput: N\n",
        temperature=0.2,
    )
    key2 = compute_cache_key(
        provider="gemini",
        model="gemini-3.8-flash",
        prompt_text="System instructions",
        statement_text="# Problem 1\nInput: N\n",
        temperature=0.2,
    )
    key_different_model = compute_cache_key(
        provider="gemini",
        model="gemini-2.5-flash",
        prompt_text="System instructions",
        statement_text="# Problem 1\nInput: N\n",
        temperature=0.2,
    )

    assert key1 == key2
    assert key1 != key_different_model
    assert len(key1) == 64  # SHA-256 hex length


def test_cache_save_and_retrieve():
    """Verify local cache saving and loading round-trip."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        cache_dir = Path(tmp_dir)
        cache_key = "test_hash_12345"

        artifacts = GeneratedArtifacts(
            brute_code="// brute",
            optimized_code="// opt",
            generator_code="// gen",
            validator_code="// val",
            explanation_markdown="# doc",
        )
        result = LLMGenerationResult(
            problem_id="test_prob",
            model_name="mock-model",
            artifacts=artifacts,
            usage=LLMUsageRecord(prompt_tokens=100, candidates_tokens=200, total_tokens=300),
        )

        # Before saving, should return None
        assert get_cached_generation(cache_key, cache_dir=cache_dir) is None

        # Save to disk
        save_path = save_cached_generation(result, cache_key=cache_key, cache_dir=cache_dir)
        assert save_path.exists()

        # Retrieve from disk
        cached_result = get_cached_generation(cache_key, cache_dir=cache_dir)
        assert cached_result is not None
        assert cached_result.is_cached is True
        assert cached_result.cache_key == cache_key
        assert cached_result.artifacts.brute_code == "// brute"
        assert cached_result.usage.total_tokens == 300


def test_mock_provider_generation():
    """Verify MockLLMProvider outputs valid artifacts and usage."""
    provider = MockLLMProvider()
    request = LLMGenerationRequest(
        problem_statement="# Two Sum Problem",
        problem_id="01_two_sum",
        model_name="mock-model",
    )
    result = provider.generate(request)

    assert result.problem_id == "01_two_sum"
    assert "std::vector" in result.artifacts.brute_code
    assert "unordered_map" in result.artifacts.optimized_code
    assert "mt19937_64" in result.artifacts.generator_code
    assert "std::cin" in result.artifacts.validator_code
    assert result.usage.total_tokens > 0


def test_code_generator_mock_pipeline():
    """Verify full CodeGenerator pipeline writes all 5 files to destination directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_path = Path(tmp_dir)
        problem_file = temp_path / "sample_problem.md"
        problem_file.write_text("# Sample Problem\nFind sum of two numbers.", encoding="utf-8")

        output_dir = temp_path / "artifacts_out"
        cache_dir = temp_path / "test_cache"

        generator = CodeGenerator(provider=MockLLMProvider(), cache_dir=cache_dir)

        # 1st run: Cache Miss
        res1, files1 = generator.generate_from_file(
            problem_path=problem_file,
            output_dir=output_dir,
            use_cache=True,
            use_mock=True,
        )
        assert res1.is_cached is False
        assert len(files1) == 5
        for fname in ["brute.cpp", "optimized.cpp", "generator.cpp", "validator.cpp", "explanation.md"]:
            assert (output_dir / fname).exists()
            assert (output_dir / fname).stat().st_size > 0

        # 2nd run: Cache Hit
        res2, files2 = generator.generate_from_file(
            problem_path=problem_file,
            output_dir=output_dir,
            use_cache=True,
            use_mock=True,
        )
        assert res2.is_cached is True
        assert res2.cache_key == res1.cache_key


def test_gemini_cost_estimation():
    """Verify Gemini cost formula according to published token pricing tiers."""
    cost_flash = estimate_gemini_cost("gemini-3.8-flash", prompt_tokens=1_000_000, candidates_tokens=1_000_000)
    assert pytest.approx(cost_flash, 0.001) == 0.375  # 0.075 + 0.30

    cost_pro = estimate_gemini_cost("gemini-1.5-pro", prompt_tokens=1_000_000, candidates_tokens=1_000_000)
    assert pytest.approx(cost_pro, 0.001) == 6.25  # 1.25 + 5.00


def test_strip_code_fences():
    """Verify markdown code fences are stripped cleanly."""
    fenced = "```cpp\n#include <iostream>\nint main() {}\n```"
    unfenced = strip_code_fences(fenced)
    assert unfenced == "#include <iostream>\nint main() {}"

    plain = "#include <iostream>\nint main() {}"
    assert strip_code_fences(plain) == plain
