# ADR-003: Oracle Constraints, Checker Policy & Uncertainty Management

* **Status:** Accepted  
* **Date:** 2026-10-23  
* **Deciders:** Principal Architect, Core Developer  
* **Context:** MVP-0 (Phase 0)  

## Context and Problem Statement
When generating test outputs, the system must execute a reference solution (an "oracle") to produce expected results. In competitive programming:
1. Brute-force solutions (`brute.cpp`) are simpler to prove correct but fail on large inputs due to time limit exceeded (TLE).
2. Optimized solutions (`optimized.cpp`) scale to large inputs but may harbor subtle edge-case logic bugs.
3. Automated differential testing on a finite number of testcases can detect disagreements, but **it cannot mathematically prove which solution is correct**, nor can it prove that passing tests imply complete solution correctness.
4. Some problems have non-unique valid outputs (e.g., "output any spanning tree" or floating-point values with precision epsilon).

## Decision
1. **Explicit Oracle Designations:**
   - In MVP-0, `brute.cpp` serves as the primary verification oracle ONLY on small, constrained input domains (e.g., $N \le 10$ or $N \le 50$ depending on algorithmic complexity).
   - `optimized.cpp` generates official testcase outputs only after passing sample testcases and small differential tests against `brute.cpp`.
2. **Checker Strategy for MVP-0:**
   - The default comparison checker performs **token-by-token comparison with whitespace and trailing newline normalization**.
   - Special judges, interactive problem protocols, and custom floating-point tolerances are deferred to MVP-1/MVP-2.
3. **Handling Disagreements (Mismatch):**
   - If `brute.cpp` and `optimized.cpp` produce different outputs on the same validated input, the batch run MUST immediately halt.
   - Status transitions to `MISMATCH_FOUND`. The failing input, both outputs, execution logs, and exit codes are preserved for developer inspection. The system MUST NOT guess which solution is faulty.
4. **Uncertainty & Human Approval:**
   - If the problem has multiple valid solutions or if output comparison semantics are uncertain, the run status MUST be explicitly set to `NEEDS_REVIEW`.
   - The user must inspect 3–5 representative sample cases and provide explicit approval before export. Approval represents developer acceptance for the workflow, NOT mathematical proof of perfection.

## Consequences
### Positive
- Prevents false claims: The system never misleadingly certifies a generated test package as "mathematically proven".
- Fails safe: Disagreements stop the pipeline before corrupt data is packaged.
- Simplifies MVP-0: Avoiding custom special judges keeps the core engine lean and testable.

### Negative / Trade-offs
- Manual developer review is required when problems deviate from deterministic, single-valid-output semantics.
- Small input limitation: Differential testing is constrained by the execution time of the brute-force algorithm.
