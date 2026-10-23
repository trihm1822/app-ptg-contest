# ADR-001: LLM Provider Abstraction & Google Gemini Integration

* **Status:** Accepted  
* **Date:** 2026-10-23  
* **Deciders:** Principal Architect, Core Developer  
* **Context:** MVP-0 (Phase 0)  

## Context and Problem Statement
PTG requires an LLM to generate C++17 brute-force solutions, optimized solutions, input generators, independent validators, and problem explanations from a standardized Markdown problem statement. Directly coupling business logic to a single proprietary SDK creates vendor lock-in, complicates automated testing, and makes cost tracking difficult. Furthermore, LLM API calls incur monetary costs, latency, and occasional non-deterministic output.

## Decision
1. **Abstract Interface:** Define an abstract base class `LLMProviderInterface` in Python specifying `generate_solution(prompt_payload) -> LLMResponse`.
2. **Default Provider:** Adopt **Google Gemini** as the primary default provider for MVP-0, utilizing the `gemini-2.5-flash` model (with fallback to `gemini-1.5-pro` for complex algorithms) via the official Google GenAI SDK.
3. **Response Caching:** Implement local filesystem-based response caching. The cache key MUST be computed as:
   $$\text{CacheKey} = \text{SHA256}(\text{provider} + \text{model} + \text{prompt\_hash} + \text{normalized\_statement\_hash} + \text{temperature} + \text{seed})$$
4. **Usage & Cost Tracking:** Every response must capture `prompt_tokens`, `completion_tokens`, `total_tokens`, and estimated cost in USD (calculated from published pricing tiers) and record them into the run's metadata.
5. **Retry Policy:** Do NOT perform automatic repeated retries on semantic code failures. Allow at most **1 deliberate user-triggered retry** for transient network/rate-limit errors with exponential backoff.

## Consequences
### Positive
- Vendor independence: Switching to OpenAI, DeepSeek, or local models requires only implementing a new adapter class without touching orchestrator logic.
- Cost control: Exact response caching prevents paying repeatedly for the same problem statement during development and testing.
- Testability: Enables a lightweight `MockLLMProvider` returning deterministic C++ templates for CI/CD integration tests without requiring live API keys.

### Negative / Trade-offs
- Added abstraction layer: Requires maintaining adapter classes and translating provider-specific usage schemas into a unified PTG usage record.
- Non-deterministic code generation: Even with a fixed temperature or seed, cloud-hosted LLM outputs may exhibit minor token variations across provider updates.
