# ADR-002: C++ Generator Contract & Independent Validator Architecture

* **Status:** Accepted  
* **Date:** 2026-10-23  
* **Deciders:** Principal Architect, Core Developer  
* **Context:** MVP-0 (Phase 0)  

## Context and Problem Statement
To generate high-quality test inputs for competitive programming problems, relying on generic Python random number scripts is inadequate for structured constraints (graphs, trees, formatted strings). However, executing AI-generated C++ code to produce testcases introduces two major failure modes:
1. Non-deterministic generation that cannot be reproduced across platforms.
2. Silent constraint violations where the generator emits data that breaks the problem's own stated limits (e.g., $N > 10^5$ or negative weights where prohibited).

## Decision
1. **Strict Generator CLI Contract:** Every generator must be a standalone C++17 binary complying with the exact signature:
   ```bash
   generator <seed> <subtask_id>
   ```
   - `argv[1]` (`seed`): 64-bit unsigned integer controlling pseudorandom state (using `std::mt19937_64`).
   - `argv[2]` (`subtask_id`): Integer identifying the subtask/constraint profile.
   - `stdout`: Emits exactly one complete, valid problem input ending with a newline.
   - `exit code 0`: Indicates successful generation. Any non-zero exit or stderr diagnostic indicates generation failure.
2. **Determinism Guarantee:** Given identical generator binary, configuration, seed, and subtask ID, the output on stdout MUST be bit-for-bit identical across executions.
3. **Mandatory Independent Validator:** Never trust the generator to validate its own output. A separate C++17 program (`validator.cpp`) MUST be generated or supplied:
   - Reads the candidate input from `stdin`.
   - Parses the exact syntax according to problem specifications (token counts, line breaks).
   - Validates all mathematical boundary constraints (e.g., $1 \le N \le 10^5$).
   - Returns exit code `0` if valid; returns non-zero and prints constraint violation to `stderr` if invalid.
   - Only inputs that pass the independent validator with exit code `0` are accepted for differential testing and export.

## Consequences
### Positive
- Robust quality gate: Prevents corrupted or invalid testcases from polluting the export package.
- High reproducibility: Any testcase can be recreated on-demand knowing only the seed, subtask ID, and generator source hash.
- Industry alignment: Conforms to competitive programming standards (Codeforces / Polygon testlib methodology).

### Negative / Trade-offs
- Double compilation overhead: Both `generator.cpp` and `validator.cpp` must be compiled in the sandbox before test generation begins.
- Risk of validator bugs: If the LLM produces a flawed validator, valid generated tests might be falsely rejected. In such cases, human review is required.
