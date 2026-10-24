"""Local filesystem response caching compliant with ADR-001."""

import hashlib
import json
from pathlib import Path
from typing import Optional

from ptg.models.llm import LLMGenerationResult


DEFAULT_CACHE_DIR = Path("temp/cache/llm")


def compute_cache_key(
    provider: str,
    model: str,
    prompt_text: str,
    statement_text: str,
    temperature: float = 0.2,
    seed: int = 42,
) -> str:
    """Compute deterministic SHA-256 cache key per ADR-001.

    Formula:
        SHA256(provider + model + prompt_hash + normalized_statement_hash + temperature + seed)
    """
    normalized_statement = "\n".join(
        line.rstrip() for line in statement_text.strip().splitlines()
    )
    prompt_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
    statement_hash = hashlib.sha256(normalized_statement.encode("utf-8")).hexdigest()

    raw_composite = (
        f"{provider.strip().lower()}:"
        f"{model.strip().lower()}:"
        f"{prompt_hash}:"
        f"{statement_hash}:"
        f"{temperature:.4f}:"
        f"{seed}"
    )
    return hashlib.sha256(raw_composite.encode("utf-8")).hexdigest()


def get_cached_generation(
    cache_key: str,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> Optional[LLMGenerationResult]:
    """Retrieve cached generation result if present on disk."""
    cache_file = cache_dir / f"{cache_key}.json"
    if not cache_file.exists():
        return None

    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        result = LLMGenerationResult.model_validate(data)
        result.is_cached = True
        result.cache_key = cache_key
        return result
    except Exception:
        # If cache file is corrupted or schema version changed, return None to trigger fresh generation
        return None


def save_cached_generation(
    result: LLMGenerationResult,
    cache_key: str,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> Path:
    """Persist generation result to cache directory as JSON."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{cache_key}.json"

    export_data = result.model_dump()
    export_data["is_cached"] = True
    export_data["cache_key"] = cache_key

    cache_file.write_text(
        json.dumps(export_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return cache_file
