# Architecture Decision Records (ADRs)

This directory maintains the architectural decision records for the **Problem-to-Testcase Generator (PTG)** project, following the [Michael Nygard format](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).

## ADR Index

| ADR ID | Title | Status | Date | Target Phase |
|---|---|:---:|---|:---:|
| [ADR-001](ADR-001-llm-provider-abstraction.md) | LLM Provider Abstraction & Google Gemini Integration | **Accepted** | 2026-10-23 | MVP-0 |
| [ADR-002](ADR-002-cpp-generator-contract.md) | C++ Generator Contract & Independent Validator Architecture | **Accepted** | 2026-10-23 | MVP-0 |
| [ADR-003](ADR-003-checker-oracle-policy.md) | Oracle Constraints, Checker Policy & Uncertainty Management | **Accepted** | 2026-10-23 | MVP-0 |
| [ADR-004](ADR-004-sandbox-isolation-boundary.md) | Sandbox Execution Boundary & Compiler Resource Protection | **Accepted** | 2026-10-23 | MVP-0 |
| [ADR-005](ADR-005-reproducibility-record-schema.md) | Reproducibility Metadata Record & Export Manifest Schema | **Accepted** | 2026-10-23 | MVP-0 |
| [ADR-006](ADR-006-phase0-security-hardening-and-prng.md) | Sandbox Security Hardening, Unbiased PRNG Contract & Themis Layout Compatibility | **Accepted** | 2026-10-26 | MVP-0 |
| [ADR-007](ADR-007-database-schema-foundation.md) | Database Architecture, Entity Hierarchy & Problem Versioning Schema | **Accepted** | 2026-10-26 | MVP-1 |

## Decision Rules
1. **Scope Gating:** ADRs in Phase 0 focused on core generation, sandbox execution, validation, and reproducibility contracts. Phase 1 ADRs govern web, multi-user, and distributed infrastructure.
2. **Authority:** Once an ADR is marked `Accepted`, any changes to its technical consequences require a new ADR that supersedes the prior decision.
