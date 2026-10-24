"""Base abstract LLM provider interface adhering to ADR-001."""

from abc import ABC, abstractmethod
from ptg.models.llm import LLMGenerationRequest, LLMGenerationResult


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers in PTG."""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    @abstractmethod
    def generate(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        """Send generation request to provider and return structured result.

        Args:
            request: The generation request with problem statement and parameters.

        Returns:
            LLMGenerationResult containing the 5 artifacts and usage statistics.
        """
        pass
