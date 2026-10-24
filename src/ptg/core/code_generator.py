"""Code generation pipeline orchestrating caching, LLM invocation, and artifact output."""

from pathlib import Path
from typing import Dict, Optional, Tuple

from ptg.core.cache import (
    DEFAULT_CACHE_DIR,
    compute_cache_key,
    get_cached_generation,
    save_cached_generation,
)
from ptg.integrations.llm.base import BaseLLMProvider
from ptg.integrations.llm.gemini import GeminiLLMProvider
from ptg.integrations.llm.mock import MockLLMProvider
from ptg.models.llm import LLMGenerationRequest, LLMGenerationResult
from ptg.templates.prompts import SYSTEM_PROMPT_DEFAULT


class CodeGenerator:
    """Coordinates problem ingestion, LLM querying, caching, and artifact dumping."""

    def __init__(
        self,
        provider: Optional[BaseLLMProvider] = None,
        cache_dir: Path = DEFAULT_CACHE_DIR,
    ):
        self.provider = provider
        self.cache_dir = cache_dir

    def generate_from_file(
        self,
        problem_path: Path,
        output_dir: Path,
        model_name: str = "gemini-3.8-flash",
        temperature: float = 0.2,
        use_cache: bool = True,
        use_mock: bool = False,
    ) -> Tuple[LLMGenerationResult, Dict[str, Path]]:
        """Ingest a Markdown problem file, run generation, and write 5 artifacts to disk.

        Returns:
            Tuple of (LLMGenerationResult, Dict of file paths written)
        """
        if not problem_path.exists():
            raise FileNotFoundError(f"Problem file not found: {problem_path}")

        problem_content = problem_path.read_text(encoding="utf-8")
        problem_id = problem_path.stem

        # Choose provider
        active_provider = self.provider
        if active_provider is None:
            if use_mock:
                active_provider = MockLLMProvider()
            else:
                active_provider = GeminiLLMProvider()

        provider_name = active_provider.provider_name

        # Check Cache
        cache_key = compute_cache_key(
            provider=provider_name,
            model=model_name,
            prompt_text=SYSTEM_PROMPT_DEFAULT,
            statement_text=problem_content,
            temperature=temperature,
        )

        result: Optional[LLMGenerationResult] = None
        if use_cache:
            result = get_cached_generation(cache_key, cache_dir=self.cache_dir)

        if result is None:
            # Cache miss: generate fresh
            request = LLMGenerationRequest(
                problem_statement=problem_content,
                problem_id=problem_id,
                model_name=model_name,
                temperature=temperature,
            )
            result = active_provider.generate(request)
            result.cache_key = cache_key
            result.is_cached = False

            if use_cache:
                save_cached_generation(result, cache_key, cache_dir=self.cache_dir)

        # Write 5 artifacts to output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        written_files = {
            "brute.cpp": output_dir / "brute.cpp",
            "optimized.cpp": output_dir / "optimized.cpp",
            "generator.cpp": output_dir / "generator.cpp",
            "validator.cpp": output_dir / "validator.cpp",
            "explanation.md": output_dir / "explanation.md",
        }

        written_files["brute.cpp"].write_text(result.artifacts.brute_code, encoding="utf-8")
        written_files["optimized.cpp"].write_text(result.artifacts.optimized_code, encoding="utf-8")
        written_files["generator.cpp"].write_text(result.artifacts.generator_code, encoding="utf-8")
        written_files["validator.cpp"].write_text(result.artifacts.validator_code, encoding="utf-8")
        written_files["explanation.md"].write_text(result.artifacts.explanation_markdown, encoding="utf-8")

        return result, written_files
