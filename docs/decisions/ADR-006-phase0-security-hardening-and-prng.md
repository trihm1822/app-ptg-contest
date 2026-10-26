# ADR-006: Sandbox Security Hardening, Unbiased PRNG Contract & Themis Layout Compatibility

* **Status:** Accepted  
* **Date:** 2026-10-26  
* **Deciders:** Principal Architect, Core Developer  
* **Context:** Phase 0 Hardening & Security Remediation (Pre-Phase 1 Hardening)  

---

## 1. Context and Problem Statement
During an extensive security and mathematical audit of Phase 0, five key vulnerabilities and operational risks were identified:
1. **Mount Permission Leak (SANDBOX-01):** Although the container rootfs had `--read-only`, the host volume mounted at `/workspace` lacked an explicit `:ro` flag during binary execution, allowing untrusted code to mutate files in the workspace.
2. **Container State & Zombie Leakage (SANDBOX-02 & 03):** Using `--rm` prevented post-mortem inspection via `docker inspect` to distinguish between OOM kills and timeouts. Furthermore, unexpected host process crashes could leave orphaned containers running indefinitely.
3. **PRNG Discrepancies & Modulo Bias (GEN-01 & 02):** `std::uniform_int_distribution` is not standardized across C++ standard libraries (libstdc++, libc++, MSVC STL), leading to different sequences for the same seed. Naive modulo reduction `seed % range` introduced statistical modulo bias.
4. **Whitespace False Positives (DIFF-01):** Moving whitespace trimming to the packaging stage would violate fail-safe differential gating. Competitive programming requires token-based equivalence by default while allowing strict byte-level matching for formatted text problems.
5. **Layout Compatibility (PKG-01):** Competitive programming platforms require flexible casing conventions (`test01/test01.inp` vs classic Themis `Test01/Test01.INP`).

---

## 2. Decision

### 2.1. Strict Mount Permission Separation
- **Compilation:** Mounts `/workspace:rw` to allow `g++` to generate the output binary.
- **Execution:** Mounts `/workspace:ro` (read-only volume). Untrusted programs are forbidden from modifying or creating files in the workspace. Any attempt to write to `/workspace` fails immediately with `EACCES` (Permission Denied). Scratch files must use the temporary, non-executable in-memory mount `--tmpfs /tmp:rw,noexec,nosuid,size=64m`.

### 2.2. Three-Layer Container Lifecycle & Accurate OOM Classification
- **Layer 1 (Startup Reconciliation):** `IsolatedRunner` prunes all orphaned containers labeled with `--label managed-by=ptg` on instantiation.
- **Layer 2 (Post-Mortem Inspection):** Containers run without `--rm` under deterministic names `ptg-exec-<uuid>`. If a container exits with non-zero status or code 137, `IsolatedRunner` inspects `{{.State.OOMKilled}}` via `docker inspect`:
  - `OOMKilled == true` -> Classified definitively as `Verdict.MEMORY_LIMIT_EXCEEDED`.
  - `stderr` contains `Resource temporarily unavailable` or `EAGAIN` -> Classified as `Verdict.RESOURCE_LIMIT_EXCEEDED` (Fork bomb).
  - Code 137 with wall-clock time matching timeout limit -> Classified as `Verdict.TIME_LIMIT_EXCEEDED`.
- **Layer 3 (Guaranteed Deletion):** Containers are tracked in memory and forcefully deleted (`docker rm -f`) in a `finally` block, with fallback handlers registered on `atexit` and `signal.SIGINT`.

### 2.3. Unbiased Cross-Platform Deterministic PRNG (`SplitMix64`)
- Generators must not rely on `std::uniform_int_distribution`.
- Generators must embed and use an exact, self-contained `SplitMix64` struct featuring **Unbiased Rejection Sampling**:
```cpp
struct SplitMix64 {
    uint64_t x;
    SplitMix64(uint64_t seed) : x(seed) {}
    uint64_t next() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    long long next_range(long long l, long long r) {
        if (l >= r) return l;
        uint64_t range = (uint64_t)(r - l + 1);
        uint64_t threshold = (-range) % range;
        uint64_t val;
        do { val = next(); } while (val < threshold);
        return l + (long long)(val % range);
    }
};
```

### 2.4. Differential Output Comparison & Layout Modes
- **Comparison:** Default remains `token_mode = True` (standard ICPC/IOI/Themis behavior). A new `--strict-whitespace` / `strict_bytes` flag is provided for strict byte-for-byte evaluation.
- **Export Layout:** The pipeline supports both `themis_modern` (`tests/test01/test01.inp`) and `themis_classic` (`tests/Test01/Test01.INP` and `.OUT`) via `--themis-classic`.

---

## 3. Consequences

### Positive
- Prevents container escapes or host filesystem tampering via write-blocked volumes.
- Eliminates guesswork between OOM kills, fork bombs, and infinite loops.
- Eliminates zombie container leaks across development sessions and CI runs.
- Eliminates statistical bias in generated test vectors and guarantees 100% bit-exact reproducibility regardless of whether the generator was compiled with GCC, Clang, or MSVC.
- Maintains full compatibility with classic Vietnamese contest infrastructure (Themis).

### Neutral / Operational
- `docker inspect` adds a 10-30ms post-mortem overhead solely for failed or non-zero executions (does not impact successful runs).
- Generator prompts are slightly longer due to embedding the canonical `SplitMix64` struct.
