# ADR-007: Database Architecture, Entity Hierarchy & Problem Versioning Schema

* **Status:** Accepted  
* **Date:** 2026-10-26  
* **Deciders:** Principal Architect, Core Developer  
* **Context:** Phase 1 (MVP-1 Multi-User Web Platform) — Milestone 1.1 Foundation  

---

## 1. Context and Problem Statement
Phase 0 established a self-contained local CLI engine. In Phase 1, PTG transitions to a multi-tenant web platform supporting users, project workspaces, and problem versioning. 

Key design challenges addressed:
1. **Scope Gating (YAGNI):** Introducing background worker tables (`jobs`, `test_cases`) or distributed broker dependencies (`celery`, `redis`) prematurely in Milestone 1.1 complicates database migrations and CI pipelines before worker architectures are finalized.
2. **Problem Statement Versioning:** In competitive programming, modifying problem constraints (e.g. changing $N \le 10^5$ to $N \le 10^6$) must not overwrite historical problem statements, which would invalidate previously generated and verified testcase packages.
3. **Soft Deletion vs. Unique Constraints:** Soft-deleted records (`deleted_at IS NOT NULL`) collide with standard `UNIQUE(project_id, slug)` constraints if a user attempts to recreate a problem with the same slug.
4. **Fast Developer Ergonomics:** The database layer must support full PostgreSQL capabilities in production while running zero-dependency in-memory SQLite tests for rapid test execution.

---

## 2. Decision

### 2.1. YAGNI Scope Contract
- Milestone 1.1 defines strictly the foundational entities: `users`, `projects`, `problems`, and `problem_revisions`.
- Background execution tables (`jobs`, `test_cases`) and message broker dependencies (`celery`, `redis`) are deferred to Milestone 1.3 (Task Queue Integration).

### 2.2. Entity Hierarchy & Referential Integrity
- **`users`:** Core account entity using UUIDv4 primary keys and unique lowercase email addresses.
- **`projects`:** Workspaces belonging to users via `user_id` with `ON DELETE RESTRICT` (preventing accidental mass deletion of user data).
- **`problems`:** Stable problem identity belonging to projects via `project_id` with `ON DELETE CASCADE`.
- **`problem_revisions`:** Immutable revision snapshots belonging to problems via `problem_id` with `ON DELETE CASCADE`, tracking `revision_number` (unique per problem), markdown statement, resource limits, and sample I/O.

### 2.3. Circular Foreign Key Resolution
- `problems` references its active snapshot via `current_revision_id` (`nullable=True`).
- `problem_revisions` references parent problem via `problem_id`.
- The circular reference is resolved in SQLAlchemy and Alembic via `use_alter=True, name="fk_problems_current_revision_id"`, allowing tables to be instantiated independently before linking.

### 2.4. Soft Delete with Partial Unique Index
- `projects` and `problems` implement `SoftDeleteMixin` (`deleted_at: Optional[datetime]`).
- Slugs are constrained via a **Partial Unique Index**:
  ```sql
  CREATE UNIQUE INDEX uq_problems_project_slug_active 
  ON problems (project_id, slug) 
  WHERE deleted_at IS NULL;
  ```
  This guarantees slug uniqueness among active problems while permitting slug reuse if an older problem is soft-deleted.

### 2.5. Async ORM & Cross-Dialect Portability
- All relationships explicitly specify `lazy="selectin"` to prevent `MissingGreenlet` errors under async I/O.
- The `samples` field uses `JSON().with_variant(JSONB, "postgresql")`, allowing native PostgreSQL JSONB indexing in production while remaining fully testable on SQLite in-memory.

### 2.6. Migration Runner: Async Driver Wrapper (`connection.run_sync`) vs. Pure Sync Driver
- **Context:** The team evaluated using a purely synchronous Alembic configuration (`alembic init`) vs. the async engine template (`alembic init -t async`). Pure sync Alembic avoids event loop constructs, but mandates installing and maintaining a second, synchronous PostgreSQL driver (e.g., `psycopg2-binary` or `psycopg`) alongside `asyncpg`, as well as managing separate synchronous connection strings.
- **Decision:** We use the standard SQLAlchemy 2.0 async Alembic pattern:
  - `alembic/env.py` instantiates an async connection via `create_async_engine(url, poolclass=pool.NullPool)` using the application's unified `asyncpg` / `aiosqlite` connection string.
  - The actual schema inspection and DDL execution inside `do_run_migrations` are run via `await connection.run_sync(do_run_migrations)`.
  - This provides the best of both worlds: zero redundant synchronous driver dependencies, zero connection URL duplication, and strictly sequential, synchronous execution of DDL operations inside the `run_sync` context without event loop collision risks.

---

## 3. Consequences

### Positive
- Enforces strict problem version control, ensuring testcase provenance remains immutable across statement updates.
- Prevents database deadlocks and migration failures through `use_alter=True`.
- Eliminates unique constraint collisions on soft-deleted resources.
- Provides immediate unit test execution (< 1s) with zero external database dependencies.

### Neutral / Operational
- Creating a new problem with an initial revision requires a two-step transaction (insert problem -> insert revision -> update `current_revision_id`).
- Migration `001_initial_schema.py` establishes the baseline; future tables (`jobs`, `test_cases`) will be introduced in migration `002` during Milestone 1.3.
