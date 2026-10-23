# PTG Documentation Review — Decision Summary

Date: 2026-10-23  
Version: 1.0-reconciled  
Reconciliation Tag: REC-002  

This package preserves the baseline README and SRS and applies an authoritative reconciliation to synchronize priorities, execution stages, and architectural boundaries across all documents.

## Authoritative Scope & Deliverables
- **MVP-0 (Phase 0) Deliverable Contract:** Local Python CLI tool + Disposable Docker C++ Sandbox Runner + Reproducible JSON Manifest export (`PTG-EXPORT.zip`). No database, no web UI, and no Redis/Celery required in Phase 0.
- **MVP-1 (Phase 1):** Multi-user web platform (React + TypeScript + FastAPI + PostgreSQL + Celery/Redis + PDF/OCR extraction).
- **MVP-2 (Phase 2):** Sandbox hardening (`nsjail`/`isolate`), special judges, floating-point tolerance, and adversarial generation.

## Accepted Architectural Decisions
- Stage scope into MVP-0, MVP-1 and MVP-2; keep MVP-0 focused strictly on the local core pipeline.
- Specify standalone C++17 generator and independent C++ validator contracts.
- Define oracle limits, differential testing, and mark uncertain checker semantics as `NEEDS_REVIEW`.
- Enforce layered sandbox controls (cgroups CPU/RAM/PIDs limits, `--network=none`, `--read-only`, compiler timeout of 10s) without claiming Docker alone is a mathematical security guarantee.
- Isolate the C++ execution runner from direct database and external network access.
- Record reproducibility metadata and available LLM usage/cost.
- Define retry/idempotency rules and mandatory human review before export.
- Reject premature infrastructure (Kafka, Event Bus, UUIDv7, full observability) as Phase 0 blockers.
- Reject polymorphic table keys (`owner_type + owner_id`) to safeguard referential integrity with standard foreign keys.

## Synchronized Files
- `README.md`: Architecture overview, isolated runner pipeline, and synchronized staged roadmap.
- `SRS.md`: Reconciled functional requirements (P0 for MVP-0 core engine; P1 for MVP-1 web platform), data model indexes, and state machine.
- `docs/decisions/`: ADR-001 through ADR-005 establishing foundational architecture contracts.
