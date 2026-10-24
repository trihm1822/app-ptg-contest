"""Deterministic Mock LLM Provider for unit testing and offline CI/CD."""

import time
from ptg.integrations.llm.base import BaseLLMProvider
from ptg.models.llm import (
    GeneratedArtifacts,
    LLMGenerationRequest,
    LLMGenerationResult,
    LLMUsageRecord,
)

SAMPLE_BRUTE_CPP = """#include <iostream>
#include <vector>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    long long target;
    if (!(std::cin >> n >> target)) return 0;

    std::vector<long long> a(n);
    for (int i = 0; i < n; ++i) {
        std::cin >> a[i];
    }

    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            if (a[i] + a[j] == target) {
                std::cout << (i + 1) << " " << (j + 1) << "\\n";
                return 0;
            }
        }
    }

    std::cout << "-1\\n";
    return 0;
}
"""

SAMPLE_OPTIMIZED_CPP = """#include <iostream>
#include <vector>
#include <unordered_map>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    long long target;
    if (!(std::cin >> n >> target)) return 0;

    std::vector<long long> a(n);
    std::unordered_map<long long, int> seen;

    for (int i = 0; i < n; ++i) {
        std::cin >> a[i];
        long long needed = target - a[i];
        if (seen.find(needed) != seen.end()) {
            std::cout << seen[needed] << " " << (i + 1) << "\\n";
            return 0;
        }
        seen[a[i]] = i + 1;
    }

    std::cout << "-1\\n";
    return 0;
}
"""

SAMPLE_GENERATOR_CPP = """#include <iostream>
#include <vector>
#include <random>
#include <string>

int main(int argc, char* argv[]) {
    if (argc < 3) {
        std::cerr << "Usage: generator <seed> <subtask_id>\\n";
        return 1;
    }

    unsigned long long seed = std::stoull(argv[1]);
    int subtask = std::stoi(argv[2]);
    std::mt19937_64 rng(seed);

    int n = 10;
    long long max_val = 100;
    if (subtask == 2) {
        n = 1000;
        max_val = 1000000;
    }

    std::uniform_int_distribution<long long> dist(1, max_val);
    long long target = dist(rng) + dist(rng);

    std::cout << n << " " << target << "\\n";
    for (int i = 0; i < n; ++i) {
        std::cout << dist(rng) << (i + 1 == n ? "" : " ");
    }
    std::cout << "\\n";

    return 0;
}
"""

SAMPLE_VALIDATOR_CPP = """#include <iostream>
#include <vector>
#include <cassert>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    long long target;
    if (!(std::cin >> n >> target)) {
        std::cerr << "Validation failed: Could not read N and target\\n";
        return 1;
    }

    if (n < 2 || n > 200000) {
        std::cerr << "Validation failed: N out of bounds: " << n << "\\n";
        return 1;
    }

    int count = 0;
    long long x;
    while (std::cin >> x) {
        count++;
    }

    if (count != n) {
        std::cerr << "Validation failed: Expected " << n << " elements, got " << count << "\\n";
        return 1;
    }

    return 0;
}
"""

SAMPLE_EXPLANATION_MD = """# Two Sum Solution & Complexity Analysis

## Approach
We are given an array of $N$ integers and a target sum $X$. We must find two distinct 1-based indices $i < j$ such that $A_i + A_j = X$.

### 1. Brute-force
Iterate over all pairs $(i, j)$ where $0 \le i < j < N$ and check if $A_i + A_j = X$.
- **Time Complexity:** $O(N^2)$
- **Space Complexity:** $O(1)$

### 2. Optimized Hash Map
Maintain a hash table mapping each element's value to its 1-based index. For each element $A_i$, check if $X - A_i$ has already been recorded.
- **Time Complexity:** $O(N)$ average
- **Space Complexity:** $O(N)$
"""


class MockLLMProvider(BaseLLMProvider):
    """Mock provider returning deterministic C++ code and metadata for testing."""

    def __init__(self, provider_name: str = "mock"):
        super().__init__(provider_name=provider_name)

    def generate(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        start_time = time.perf_counter()

        artifacts = GeneratedArtifacts(
            brute_code=SAMPLE_BRUTE_CPP,
            optimized_code=SAMPLE_OPTIMIZED_CPP,
            generator_code=SAMPLE_GENERATOR_CPP,
            validator_code=SAMPLE_VALIDATOR_CPP,
            explanation_markdown=SAMPLE_EXPLANATION_MD,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        usage = LLMUsageRecord(
            prompt_tokens=350,
            candidates_tokens=720,
            total_tokens=1070,
            estimated_cost_usd=0.0,
            latency_ms=round(latency_ms, 2),
        )

        return LLMGenerationResult(
            problem_id=request.problem_id,
            model_name="mock-model",
            artifacts=artifacts,
            usage=usage,
            is_cached=False,
        )
