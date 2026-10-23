# Problem-to-Testcase Generator (PTG)

> **Mục tiêu:** Chuyển đề bài lập trình thành lời giải C++17, bộ
> testcase có thể kiểm tra, báo cáo xác minh và gói ZIP có khả năng tái
> lập.

**Baseline:** MVP 1.0\
**Ngày:** 2026-10-09\
**Trạng thái:** Kiến trúc baseline đã được xác nhận để bắt đầu thiết kế
và triển khai.

------------------------------------------------------------------------

## 1. PTG là gì?

Problem-to-Testcase Generator (PTG) là ứng dụng web hỗ trợ người dùng:

1.  Tải lên một hoặc nhiều đề bài từ PDF, DOCX, Markdown, TXT hoặc ảnh.
2.  Trích xuất nội dung, tách bài và chuẩn hóa đề.
3.  Tạo lời giải C++17 vét cạn, lời giải tối ưu và giải thích thuật toán
    bằng AI.
4.  Cấu hình số lượng testcase, nhóm dữ liệu, giới hạn, chiến lược sinh
    và seed.
5.  Sinh input, kiểm tra input, chạy chương trình tham chiếu để tạo
    output.
6.  Đối chiếu lời giải, ghi nhận lỗi và tạo báo cáo xác minh.
7.  Xuất tài nguyên thành ZIP có manifest để tải về.

**Nguyên tắc quan trọng:** AI đề xuất nội dung; hệ thống kiểm tra những
gì có thể kiểm tra và công khai phần còn chưa chắc chắn. Biên dịch thành
công hoặc vượt qua sample không chứng minh lời giải đúng hoàn toàn.

## 2. Mục tiêu MVP

### Trong phạm vi

-   Website nhiều người dùng với xác thực và kiểm tra quyền sở hữu tài
    nguyên.
-   Quản lý project, tài liệu và bài toán.
-   Trích xuất văn bản và OCR fallback.
-   Chuẩn hóa đề và yêu cầu người dùng xác nhận trước khi phát hành
    testcase.
-   Quản lý phiên bản lời giải.
-   Cấu hình test theo nhóm, giới hạn và seed.
-   Sinh input, validate input, tạo output tham chiếu và differential
    testing khi khả thi.
-   Tác vụ nền có trạng thái, log, retry có kiểm soát và báo cáo.
-   Xuất ZIP cùng manifest, checksum và trạng thái xác minh.
-   C++17 được thực thi trong môi trường cô lập.

### Chưa thuộc MVP

-   Online Judge hoàn chỉnh, bảng xếp hạng hoặc thi đấu trực tuyến.
-   Đảm bảo chứng minh hình thức cho mọi lời giải AI.
-   Hỗ trợ mọi loại checker và output không duy nhất.
-   Nhiều ngôn ngữ lời giải ngoài C++17.
-   Mutation testing nâng cao, cộng tác thời gian thực, thanh toán.
-   Microservices/Kubernetes bắt buộc từ ngày đầu.

## 3. Kiến trúc công nghệ đã chốt

  -----------------------------------------------------------------------
  Thành phần              Công nghệ baseline      Vai trò
  ----------------------- ----------------------- -----------------------
  Frontend                React + TypeScript +    Website và trải nghiệm
                          Vite                    người dùng

  UI                      Tailwind CSS + thư viện Thiết kế giao diện nhất
                          component phù hợp       quán

  Backend                 FastAPI / Python        REST API, nghiệp vụ và
                                                  điều phối

  Validation              Pydantic                Kiểm tra
                                                  request/response

  ORM                     SQLAlchemy 2.x          Truy cập dữ liệu

  Migration               Alembic                 Quản lý phiên bản
                                                  schema

  Database                PostgreSQL              Nguồn dữ liệu nghiệp vụ
                                                  chính

  Job queue               Celery                  Xử lý tác vụ nền

  Broker                  Redis                   Chuyển task tới worker

  File storage            Storage abstraction;    Lưu file gốc, artifacts
                          S3-compatible khi triển và ZIP
                          khai                    

  C++ runtime             GCC hoặc Clang hỗ trợ   Biên dịch và thực thi
                          C++17                   

  Isolation               Docker hoặc sandbox     Cô lập mã nguồn không
                          tương đương             đáng tin cậy

  Development deployment  Docker Compose          Khởi chạy môi trường
                                                  phát triển

  Testing                 pytest và công cụ       Unit, integration và
                          frontend phù hợp        end-to-end tests
  -----------------------------------------------------------------------

### Kiểu kiến trúc

**Modular Monolith + Background Workers**

Backend chính được chia thành module nghiệp vụ. Các tác vụ nặng như OCR,
gọi AI, sinh test, biên dịch và đóng gói chạy trong worker riêng. Không
cần bắt đầu bằng microservices.

``` mermaid
flowchart TB
    U["User"] --> FE["React + TypeScript"]
    FE --> API["FastAPI"]
    API --> DB[("PostgreSQL")]
    API --> Q["Redis / Celery"]
    API --> ST["Object Storage"]
    Q --> DW["Document / AI Worker"]
    Q --> TW["Test Generation Worker"]
    TW --> CW["Isolated C++ Runner (Sandbox)"]
    DW --> DB
    TW --> DB
    DW --> ST
    TW --> ST
```

## 4. Nguyên tắc thiết kế quan trọng

1.  **PostgreSQL là nguồn dữ liệu nghiệp vụ chính.** Redis không phải
    nơi duy nhất lưu trạng thái job.
2.  **File tách khỏi database.** Database lưu metadata, storage key,
    checksum, trạng thái và quan hệ.
3.  **Không chạy C++ trong process API.** Mã do AI tạo và mã do người
    dùng tải lên đều là mã không đáng tin cậy.
4.  **Không phát hành test chưa được xác minh.** Mỗi bộ test phải có
    trạng thái rõ ràng.
5.  **Tái lập được kết quả.** Lưu seed, phiên bản cấu hình, phiên bản
    code, phiên bản tool và checksum cần thiết.
6.  **Kiểm tra quyền ở backend.** Không dựa vào việc ẩn nút trên
    frontend.
7.  **Không báo thành công giả.** Lỗi parse, compile, runtime, timeout,
    validation hoặc export phải được ghi nhận.
8.  **Mở rộng theo số liệu.** Tăng worker và đo queue/resource trước khi
    cân nhắc microservices hoặc Kubernetes.

## 5. Pipeline nghiệp vụ chính

1.  Người dùng đăng nhập và tạo project.
2.  Upload tài liệu.
3.  Trích xuất nội dung/OCR và tách bài.
4.  Người dùng xem, chỉnh sửa và xác nhận đề chuẩn hóa.
5.  Tạo hoặc nhập lời giải tham chiếu.
6.  Biên dịch và kiểm tra sample.
7.  Cấu hình test groups và seed.
8.  Sinh input.
9.  Validate input.
10. Chạy oracle trong sandbox để tạo output.
11. Differential testing và kiểm tra chất lượng phù hợp.
12. Tạo báo cáo.
13. Đóng gói ZIP và tải xuống.

Nếu không có oracle đáng tin cậy hoặc output của bài không duy nhất mà
chưa có checker, hệ thống phải báo cần review thay vì khẳng định output
đã được xác minh.

## 6. Cấu trúc thư mục dự kiến

``` text
problem-to-testcase-generator/
├── frontend/
│   ├── src/
│   └── tests/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   ├── core/
│   │   ├── modules/
│   │   ├── integrations/
│   │   └── db/
│   ├── migrations/
│   └── tests/
├── workers/
│   ├── document_worker/
│   ├── test_worker/
│   └── cpp_worker/
├── shared/
│   └── contracts/
├── infrastructure/
│   ├── docker/
│   ├── compose/
│   └── scripts/
├── docs/
│   ├── srs/
│   ├── architecture/
│   ├── api/
│   └── decisions/
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

Đây là cấu trúc logic baseline. Có thể bắt đầu với ít module/file hơn,
nhưng không được làm mờ ranh giới giữa API, persistence, worker và
sandbox.

## 7. Dữ liệu cốt lõi

Các thực thể chính dự kiến:

-   `users`
-   `projects`
-   `source_documents`
-   `problems`
-   `problem_revisions`
-   `solution_versions`
-   `test_configurations`
-   `test_groups`
-   `test_runs`
-   `test_cases`
-   `artifacts`
-   `jobs`
-   `job_events`
-   `validation_reports`
-   `exports`
-   `audit_events` khi cần

Schema vật lý, khóa ngoại, chỉ mục, quy tắc xóa và retention cần được
xác định trong tài liệu ERD/schema trước khi triển khai production.

## 8. Trạng thái cần phân biệt

### Job

-   `QUEUED`
-   `RUNNING`
-   `SUCCEEDED`
-   `FAILED`
-   `CANCEL_REQUESTED`
-   `CANCELLED`
-   `TIMED_OUT`

### Trạng thái xác minh

-   `NOT_CHECKED`
-   `CHECKING`
-   `PASSED_CHECKS`
-   `NEEDS_REVIEW`
-   `FAILED`
-   `STALE`

`PASSED_CHECKS` chỉ có nghĩa các kiểm tra đã cấu hình đều vượt qua. Nó
không đồng nghĩa với bằng chứng toán học rằng code hoặc bộ testcase hoàn
toàn đúng.

## 9. Đóng gói kết quả

Cấu trúc ZIP mặc định đề xuất:

``` text
PTG-EXPORT/
├── manifest.json
├── README.md
└── PROBLEM_ID/
    ├── problem.md
    ├── solutions/
    │   ├── brute.cpp
    │   ├── optimized.cpp
    │   └── explanation.md
    ├── tests/
    │   ├── test01.inp
    │   ├── test01.out
    │   └── ...
    └── reports/
        └── validation-report.json
```

Manifest nên ghi problem ID, revision, test count, test groups, seed,
phiên bản generator/solution, checksum, trạng thái xác minh và thời điểm
tạo.

## 10. Bảo mật

-   Xác thực và phân quyền ở backend.
-   File upload phải kiểm tra kích thước, loại file và chữ ký nội dung
    khi phù hợp.
-   Không lưu secret trong Git hoặc frontend bundle.
-   C++ worker phải có giới hạn CPU, RAM, thời gian, process, filesystem
    và output.
-   Tắt mạng trong sandbox theo mặc định.
-   Tách workspace của từng job.
-   Không chạy mã không đáng tin cậy với quyền quản trị.
-   Kiểm tra quyền trước khi tải artifact hoặc ZIP.
-   Có timeout, cleanup và xử lý tiến trình con.
-   Có chính sách backup/restore và retention trước khi triển khai
    production.

## 11. Các mặc định khởi đầu

  -----------------------------------------------------------------------
  Tham số                                                Mặc định đề xuất
  ------------------------------ ----------------------------------------
  Dung lượng mỗi file                                               20 MB

  File mỗi batch                                                       20

  Bài mỗi request xử lý                                                50

  Testcase mặc định mỗi bài                                            50

  Testcase tối đa mỗi bài                                           1.000

  Timeout C++ mặc định              5 giây/lần chạy, điều chỉnh theo loại
                                                             chương trình

  Thời gian tối đa một job                                        30 phút

  API prefix                                                    `/api/v1`

  Ngôn ngữ lời giải                                                 C++17
  -----------------------------------------------------------------------

Đây là cấu hình ban đầu để kiểm thử, không phải giới hạn tối ưu đã được
benchmark. Các giá trị phải được cấu hình ở backend.

## 12. Kế hoạch triển khai

> **Lưu ý phân kỳ:** Kế hoạch triển khai đã được điều chỉnh theo nguyên tắc tránh over-engineering (xem chi tiết tại phần Amendment bên dưới). Dự án ưu tiên làm chủ core pipeline trước khi xây dựng hạ tầng web.

### Phase 0 (MVP-0) --- Local Core Pipeline (CLI)

-   Mục tiêu: Hoàn thiện quy trình sinh lời giải, sinh test, compile, validate và export trên máy cục bộ trong 2–3 tuần.
-   Giao diện CLI / script Python cục bộ (chưa cần Web UI, Database, Redis/Celery).
-   Nhận 1 bài toán định dạng Markdown / Text.
-   Tích hợp LLM client sinh `brute.cpp`, `optimized.cpp`, `generator.cpp`, `validator.cpp`, `explanation.md`.
-   Sandbox C++17 bằng Docker container dùng 1 lần (cgroups limits, `--network=none`, compile timeout).
-   Kiểm tra sample, differential testing và chạy validator độc lập trên từng testcase.
-   Xuất file ZIP hoàn chỉnh kèm `manifest.json` chứa SHA-256 checksums.

### Phase 1 (MVP-1) --- Multi-User Web Platform

-   Phát triển giao diện React + TypeScript + Vite.
-   FastAPI backend kết nối PostgreSQL (SQLAlchemy 2.x, Alembic).
-   Authentication & Authorization (phân quyền theo project).
-   Xử lý tác vụ nền bất đồng bộ với Redis + Celery.
-   Trích xuất tài liệu (PDF, DOCX) và OCR fallback.
-   Lưu trữ file trừu tượng hóa (Local / S3-compatible).

### Phase 2 (MVP-2) --- Hardening & Tính năng nâng cao

-   Gia cố an ninh sandbox chuyên sâu (`nsjail` / `isolate` / `gVisor`).
-   Hỗ trợ checker đặc biệt (Special Judge, sai số số thực, output nhiều đáp án đúng).
-   Adversarial test generation và mutation testing.
-   Team workspaces và observability đầy đủ.

## 13. Tiêu chí hoàn thành MVP

MVP chỉ được nghiệm thu khi: - Đăng ký/đăng nhập hoạt động. - Người dùng
không truy cập được tài nguyên riêng của người khác. - Tài liệu được xử
lý hoặc trả lỗi rõ ràng. - Đề chuẩn hóa phải được xác nhận trước khi
phát hành test. - C++17 chạy trong sandbox. - Có thể cấu hình nhiều test
group. - Input được validate trước khi chấp nhận. - Output tham chiếu có
thông tin thực thi và trạng thái xác minh. - Mismatch bắt buộc chặn phát
hành thông thường. - Job state còn tồn tại sau khi tải lại trang. - ZIP
chứa đủ file theo manifest. - Thay đổi đầu vào làm trạng thái xác minh
phụ thuộc chuyển thành `STALE`. - Migration chạy được từ database
sạch. - Có tài liệu thiết lập và phục hồi.

## 14. Tài liệu tham chiếu

-   FastAPI: https://fastapi.tiangolo.com/
-   React: https://react.dev/
-   TypeScript: https://www.typescriptlang.org/docs/
-   PostgreSQL: https://www.postgresql.org/docs/
-   SQLAlchemy: https://docs.sqlalchemy.org/
-   Alembic: https://alembic.sqlalchemy.org/
-   Celery: https://docs.celeryq.dev/
-   Redis: https://redis.io/docs/latest/
-   Docker: https://docs.docker.com/
-   OWASP File Upload Cheat Sheet:
    https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html
-   OWASP Authorization Cheat Sheet:
    https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html

## 15. Liên kết tài liệu

-   `SRS.md`: đặc tả yêu cầu phần mềm chi tiết, baseline MVP,
    functional/non-functional requirements, API, dữ liệu, testing và
    acceptance criteria.
-   `README.md`: tổng quan hệ thống, kiến trúc, pipeline, bảo mật và kế
    hoạch triển khai.

---

# PTG Review Reconciliation — Scope, Architecture & Delivery Decisions

> **Revision note — 2026-10-11.** This section reconciles the baseline with `PTG-REVIEW-001`.
> It is authoritative where the original baseline conflicts with the staged delivery plan below.
> The baseline's broader product vision remains a future-state direction, not a Phase 0 commitment.

## 1. Delivery strategy and explicit scope

### MVP-0 — Local personal tool (target: 2–3 weeks)

**Goal:** demonstrate the core problem-to-testcase workflow before investing in multi-user infrastructure.

**In scope**
- CLI or minimal local interface; no authentication and no multi-user features.
- One Markdown or plain-text problem statement per run.
- Generate/review `brute.cpp`, `optimized.cpp`, `generator.cpp`, and `explanation.md`.
- Compile all C++17 artifacts in an isolated runner.
- Run sample tests and differential tests against small inputs. The input domain is problem-specific; `N <= 10` is only a possible brute-force profile, not a universal constraint.
- Generate a configurable test batch with explicit seeds and validate every generated input independently.
- Present a validation report and 3–5 representative tests for human review.
- Export an approved result as ZIP with a manifest and artifact hashes.
- Record available LLM usage, compiler/runtime versions, seeds, configuration hashes, and result status.

**Out of scope:** PDF/DOCX extraction and OCR; authentication; teams; multi-user projects; Celery/Redis; PostgreSQL migration; object storage; hosted production deployment; special judges; claims of automatic proof that a generated test suite is exhaustive.

**Suggested MVP-0 stack:** Python CLI or FastAPI local service, local filesystem, SQLite only if persistence is useful, C++17 compiler in a restricted Docker runner, and a provider-neutral LLM client. Do not add Docker Compose, a database, or a web frontend merely for architectural symmetry if a CLI is enough to validate the core workflow.

### MVP-1 — Multi-user web application (indicative target: 1–2 months after MVP-0)

Add React + TypeScript + Vite, FastAPI, PostgreSQL/SQLAlchemy/Alembic, authentication, project ownership, asynchronous jobs with Celery + Redis where workload requires them, PDF/DOCX extraction and OCR, local/S3-compatible storage abstraction, and a review workflow. Re-estimate this phase after MVP-0; the timeline is a planning hypothesis, not a commitment.

### MVP-2 — Hardening and advanced features (indicative target: 2–3 months after MVP-1)

Harden the sandbox and operational controls; add advanced/adversarial generators, trustworthy special-judge support, audit/monitoring, and team workspaces only if validated needs justify them. Consider gVisor or Firecracker only after a threat model and operational budget support the added complexity.

## 2. Architecture decisions: avoid premature infrastructure

- Keep a **modular monolith** with clear application-service boundaries. In-process direct calls are acceptable inside MVP-0; do not build a generic event bus before a real use case needs one.
- Introduce Celery + Redis when asynchronous multi-user workloads are introduced, not as a prerequisite for the local MVP.
- Use interfaces at genuine boundaries (LLM provider, compiler/runner, storage, checker); avoid forbidding every cross-module import if that creates ceremony without improving isolation.
- Keep local filesystem storage behind a small storage interface. MinIO/S3 is a later deployment decision.
- Use a normal foreign-key-backed `user_id`/project relationship initially. Do **not** adopt polymorphic `owner_type + owner_id` across every table by default: it weakens referential integrity. If team workspaces become real scope, model `teams` and `team_members` explicitly and define authorization inheritance through project membership.
- UUIDv4 is acceptable. UUIDv7 may be adopted if ordered IDs provide a measured benefit and the chosen libraries/database support it consistently; it is not a blocker for MVP-0.
- Do not require PostgreSQL, Redis, MinIO, CI/CD, Prometheus, Grafana, Sentry, OpenTelemetry, and 12 accepted ADRs before starting the local core pipeline.

## 3. C++ generator contract

The initial contract is deliberately small and stable:

```text
generator <seed> <subtask_id>
stdout: exactly one generated problem input
exit code 0: generation succeeded
non-zero exit: generation failed; stderr may contain diagnostics
```

- Seed and subtask ID are required integer arguments. The generator writes input to stdout; an optional output-file argument is deferred unless a concrete integration needs it.
- Given the same generator source/binary, configuration, seed, subtask, and execution environment, output must be deterministic.
- The generator may assert its own invariants, but this is supplementary only.
- A **separate validator** must parse the emitted input and verify syntax and problem constraints. It must not rely on the generator's assertions or internal data structures.
- Record the generator source hash, binary hash where applicable, version, seed, subtask, configuration hash, compiler, and runtime image digest when available.
- A strategy is selected for a problem, not blindly applied to all problems. Candidate taxonomy: `random_uniform`, `random_biased`, `edge_min`, `edge_max`, `all_equal`, `sorted_asc`, `sorted_desc`, `adversarial_<name>`, `structured_tree`, `structured_graph`, and `structured_string`.

## 4. Oracle, checker, and result states

- **Oracle** means the reference implementation used to obtain expected output; it is not automatically correct merely because it is labelled `brute.cpp`.
- MVP-0 defaults to exact token/output comparison with whitespace normalization only when the problem's output semantics permit it.
- Floating-point tolerance, special judges, and multiple-valid-answer checkers require explicit, problem-appropriate rules and are later-phase features unless a concrete MVP-0 problem needs them.
- A mismatch proves that the compared executions disagree; it does **not** identify which solution is wrong. Passing a finite test batch is evidence, not proof of correctness.
- Automated analysis cannot reliably determine in every case whether output is unique. If output semantics or the checker are uncertain, mark the run `NEEDS_REVIEW`; do not present it as verified.
- Suggested states: `PENDING`, `RUNNING`, `PASSED_TESTS`, `MISMATCH_FOUND`, `INVALID_INPUT`, `COMPILE_ERROR`, `RUNTIME_ERROR`, `TIMEOUT`, `RESOURCE_LIMIT`, `NEEDS_REVIEW`, `APPROVED_FOR_EXPORT`, `EXPORTED`. A human approval state must not upgrade uncertain verification into a claim of proven correctness.

## 5. Reproducibility and cost control

Store a per-run JSON record with: run ID and timestamp; input/problem revision hash; LLM provider/model and model identifier if exposed; prompt/template version and hash; request parameters and seed if supported; token usage/cost/latency when reported; compiler version/flags; runner image digest; generator/validator versions and hashes; generator seed/subtask/config hash; oracle solution ID/hash; checker configuration; test artifact hashes; and final status. Never store API secrets in the record.

The record should support reproduction in the same pinned environment where possible. Hosted LLM calls may not be perfectly deterministic even when a seed parameter is supplied; do not promise bit-for-bit regeneration of model output unless the provider guarantees it.

- Log token usage and estimated cost per LLM job when the provider reports it.
- Cache only when the key includes all inputs that can change the result, including model/version, prompt hash, normalized input hash, and generation parameters. A cache key based only on `(model, prompt_hash)` is insufficient.
- Bound request timeouts and retries. Do not automatically retry paid solution-generation calls by default; offer at most one deliberate retry in MVP-0.
- Add per-user quotas and a cost dashboard in MVP-1 only if multi-user usage warrants them. Keep a simple local run/cost log in MVP-0.

## 6. Retry and idempotency policy

Retry only transient infrastructure failures, not deterministic user/code errors.

| Job type | MVP policy | Idempotency inputs |
|---|---|---|
| Document extraction | Later phase: up to 3 transient retries with exponential backoff | document ID, document version, extractor version |
| LLM solution generation | No automatic retry by default; user may request one new attempt | problem revision hash, model/version, prompt hash, parameters |
| Compile/run | Retry infrastructure failure only; do not retry compile errors as if transient | source hash, compiler/flags, runner image |
| Test generation | Repeatable for a fixed artifact/config/seed; retry infrastructure failure only | generator hash, config hash, seed, subtask |
| ZIP export | Retry transient filesystem/storage failures | run ID, approval version, export layout/version |

Persist a job/run ID and deduplicate repeated submissions where feasible. A key must include every input that can affect the result.

## 7. Human review and export

Before export, show the validation report, status and limitations, plus 3–5 representative test inputs/outputs. Let the user reject the result or request regeneration. Export requires explicit approval, but approval means “accepted by the user for this workflow,” not “mathematically proven correct.” Runs in `NEEDS_REVIEW` must retain that label in the manifest and must not be described as verified.

## 8. Sandbox boundary and operational safety

Docker is an MVP-0 isolation layer, **not a security proof**. Run untrusted C++ in a disposable, non-root container with no network, read-only base filesystem, only a per-job workspace mounted, dropped Linux capabilities, `no-new-privileges`, seccomp, CPU/memory/swap/PID limits, wall-clock timeout, file-size/output limits, and workspace cleanup. Avoid privileged containers, Docker socket mounts, unrestricted host mounts, host networking, and secret/environment leakage. Apply kernel/cgroup limits on a Linux host and verify effective limits.

A sample runner configuration is illustrative and must be tested on the target host. `--network=none` alone does not block every possible local/host attack vector. MVP-1 should evaluate `nsjail` or `isolate` for a competitive-programming execution boundary; evaluate gVisor/Firecracker only if the threat model warrants it. Do not run untrusted binaries inside the API process.

## 9. Observability and deployment, staged

- MVP-0: structured Python logs with `run_id`/`job_id`, actionable error codes, elapsed time, exit code, timeout/resource-limit outcomes, and cleanup status.
- MVP-1: health and readiness endpoints; metrics such as queue depth, job duration, failure rate, and LLM cost; optionally Prometheus/Sentry after operational needs are confirmed.
- MVP-2: dashboards, tracing, centralized logs, alerting, and audit events as justified by usage and risk.
- Development may use Docker Compose when the selected services are needed. MVP-0 may remain a local CLI and should not require PostgreSQL/Redis/MinIO.
- MVP-1 deployment can begin with a hardened single-host Compose setup behind a reverse proxy and HTTPS. Kubernetes is not a default requirement; adopt it only for demonstrated scaling/operational needs.

## 10. Risks and owners

| Risk | Initial owner | Mitigation |
|---|---|---|
| AI produces incorrect or incompatible code | Developer/operator | Compile, sample tests, differential testing, visible status and human review |
| Brute solution is too slow or not a valid oracle | Developer/operator | Problem-specific brute domain, time limits, hand-check samples and small cases |
| Generator emits invalid input | Developer/operator | Independent parser/validator; reject invalid cases; preserve seed and logs |
| False confidence from finite tests | Developer/operator | Explicitly state tests are evidence, not proof; keep uncertain cases `NEEDS_REVIEW` |
| Malicious or runaway submitted code | Developer/operator | Disposable sandbox, resource limits, no network, non-root, no secrets, cleanup |
| Unexpected LLM cost or outage | Developer/operator | Usage logging, bounded retries/timeouts, complete cache keys, configurable budget |
| Provider/model behavior changes | Developer/operator | Record model identifier and prompt/config hashes; retain generated artifacts |
| Scope expansion delays delivery | Project owner | MVP acceptance gate; defer web/OCR/team features until core workflow works |

## 11. Glossary

- **Generator:** program that creates candidate input data.
- **Validator:** independent program/component that parses and checks input syntax and constraints.
- **Oracle:** reference implementation used to produce expected output.
- **Checker:** component that decides whether an output is acceptable under the problem's output semantics.
- **Differential testing:** compare outputs from two implementations on the same generated inputs.
- **Seed:** recorded value controlling pseudorandom generation.
- **Subtask:** a problem constraint profile used to generate a particular family of tests.
- **Reproducibility record:** metadata needed to understand and, where possible, repeat a run in a pinned environment.
- **Idempotency key:** key used to recognize duplicate requests that represent the same intended operation.
- **`NEEDS_REVIEW`:** the system cannot safely claim automated verification.

## 12. ADR policy

Use ADRs for consequential decisions, but do not block MVP-0 on decisions belonging to later phases. Before MVP-0, document at minimum: LLM client/provider abstraction, generator/checker contract, sandbox threat boundary, and reproducibility/cost record. Defer OCR, authentication/session, object storage, team workspace, event bus, and production observability ADRs until their phase begins. Maintain `docs/decisions/README.md` as an index when the first ADRs are created.

## 13. Change log

- **2026-10-11 — Review reconciliation:** staged scope into MVP-0/1/2; clarified generator/validator/oracle/checker semantics; added reproducibility and cost controls, retry policy, human approval, sandbox limitations, staged observability/deployment, risks and glossary. Rejected premature polymorphic ownership and blanket infrastructure/ADR prerequisites.
