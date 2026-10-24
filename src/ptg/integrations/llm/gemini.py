"""Google Gemini provider implementation using unified google-genai SDK."""

import json
import os
import re
import time
from typing import Optional

from dotenv import load_dotenv

from ptg.integrations.llm.base import BaseLLMProvider
from ptg.models.llm import (
    GeneratedArtifacts,
    LLMGenerationRequest,
    LLMGenerationResult,
    LLMUsageRecord,
)
from ptg.templates.prompts import SYSTEM_PROMPT_DEFAULT, build_user_prompt

# Load .env file automatically
load_dotenv()


# Pricing per 1M tokens (USD)
PRICING_TABLE = {
    "gemini-3.8-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-3.1-pro": {"input": 1.25, "output": 5.00},
}


def estimate_gemini_cost(model_name: str, prompt_tokens: int, candidates_tokens: int) -> float:
    """Estimate request cost in USD based on model pricing."""
    rate = PRICING_TABLE.get(model_name.lower(), {"input": 0.10, "output": 0.40})
    cost = (prompt_tokens * rate["input"] + candidates_tokens * rate["output"]) / 1_000_000.0
    return round(cost, 6)


def strip_code_fences(code_str: str) -> str:
    """Strip unnecessary markdown code block fences if present in raw string."""
    cleaned = code_str.strip()
    match = re.match(r"^```[a-zA-Z0-9_-]*\s*\n(.*)\n```$", cleaned, re.DOTALL)
    if match:
        return match.group(1).strip()
    return cleaned


class GeminiLLMProvider(BaseLLMProvider):
    """Production provider using Google GenAI SDK with structured output enforcement."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        provider_name: str = "gemini",
    ):
        super().__init__(provider_name=provider_name)
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please set it in your .env file or environment variables."
            )

        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
        except ImportError as e:
            raise ImportError(
                "Package 'google-genai' is required. Run 'pip install google-genai'."
            ) from e

    def generate(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        """Call Gemini API with structured JSON Schema."""
        from google.genai import types

        system_instruction = request.system_prompt or SYSTEM_PROMPT_DEFAULT
        user_prompt = build_user_prompt(request.problem_statement)

        start_time = time.perf_counter()

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=request.temperature,
            response_mime_type="application/json",
            response_schema=GeneratedArtifacts,
        )

        try:
            response = self.client.models.generate_content(
                model=request.model_name,
                contents=user_prompt,
                config=config,
            )
        except Exception as e:
            raise RuntimeError(f"Gemini API generation failed: {e}") from e

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        # Parse structured artifacts
        raw_text = response.text or "{}"
        try:
            parsed_data = json.loads(raw_text)
            artifacts = GeneratedArtifacts.model_validate(parsed_data)
        except Exception as parse_err:
            # Fallback if markdown json fence wrapped
            fence_match = re.search(r"```json\s*(.*?)\s*```", raw_text, re.DOTALL)
            if fence_match:
                parsed_data = json.loads(fence_match.group(1))
                artifacts = GeneratedArtifacts.model_validate(parsed_data)
            else:
                raise ValueError(
                    f"Failed to validate response against GeneratedArtifacts schema: {parse_err}"
                ) from parse_err

        # Clean code fields if any code fences sneaked into string values
        artifacts.brute_code = strip_code_fences(artifacts.brute_code)
        artifacts.optimized_code = strip_code_fences(artifacts.optimized_code)
        artifacts.generator_code = strip_code_fences(artifacts.generator_code)
        artifacts.validator_code = strip_code_fences(artifacts.validator_code)

        # Token usage
        prompt_tokens = 0
        candidates_tokens = 0
        total_tokens = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
            candidates_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
            total_tokens = getattr(response.usage_metadata, "total_token_count", 0) or (prompt_tokens + candidates_tokens)

        cost_usd = estimate_gemini_cost(request.model_name, prompt_tokens, candidates_tokens)

        usage = LLMUsageRecord(
            prompt_tokens=prompt_tokens,
            candidates_tokens=candidates_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost_usd,
            latency_ms=round(latency_ms, 2),
        )

        return LLMGenerationResult(
            problem_id=request.problem_id,
            model_name=request.model_name,
            artifacts=artifacts,
            usage=usage,
            is_cached=False,
        )
