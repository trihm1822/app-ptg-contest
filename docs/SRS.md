# Software Requirements Specification (SRS)

## Problem-to-Testcase Generator (PTG)

**Document ID:** PTG-SRS-001\
**Version:** 1.0 --- MVP Baseline\
**Status:** Baseline draft approved for implementation planning\
**Date:** 2026-10-09\
**Language:** Vietnamese\
**Product type:** Multi-user web application\
**Primary stack:** React + TypeScript + Vite; FastAPI + Python;
PostgreSQL\
**Supporting stack:** SQLAlchemy 2.x, Alembic, Redis, Celery,
S3-compatible object storage, Docker Compose, isolated C++17 execution
workers

------------------------------------------------------------------------

# 1. Purpose and Document Scope

## 1.1 Purpose

Tài liệu này xác định các yêu cầu nghiệp vụ, chức năng, dữ liệu, giao
diện, API, bảo mật, kiến trúc và tiêu chí nghiệm thu của
Problem-to-Testcase Generator (PTG). Đây là baseline để:

-   thiết kế hệ thống;
-   chia module và phân công công việc;
-   lập backlog;
-   triển khai MVP;
-   viết kiểm thử;
-   nghiệm thu và kiểm soát thay đổi.

SRS mô tả **hệ thống cần làm gì và các điều kiện cần đáp ứng**, không
phải toàn bộ chi tiết cài đặt. Các endpoint, bảng dữ liệu và cấu trúc
thư mục trong tài liệu là baseline thiết kế, có thể được tinh chỉnh qua
quyết định kiến trúc có ghi nhận mà không làm thay đổi mục tiêu nghiệp
vụ.

## 1.2 Product Vision

PTG hỗ trợ người dùng chuyển đề bài lập trình từ tài liệu thành một gói
tài nguyên có thể kiểm tra và tái lập, gồm:

1.  đề bài đã chuẩn hóa;
2.  lời giải C++17 vét cạn và tối ưu;
3.  giải thích thuật toán;
4.  bộ input testcase theo cấu hình;
5.  output tham chiếu;
6.  báo cáo kiểm chứng;
7.  gói ZIP để tải về.

AI được dùng để hỗ trợ trích xuất, phân tích và đề xuất lời giải. AI
không được coi là nguồn chân lý duy nhất. Hệ thống phải thực hiện các
bước kiểm tra xác định được và thể hiện rõ các giới hạn xác minh.

## 1.3 Intended Audience

-   Product owner / người phụ trách dự án;
-   lập trình viên frontend;
-   lập trình viên backend;
-   người xây dựng worker và pipeline testcase;
-   người kiểm thử;
-   người đánh giá/nghiệm thu.

## 1.4 Terms and Definitions

  -----------------------------------------------------------------------
  Thuật ngữ                           Định nghĩa
  ----------------------------------- -----------------------------------
  Problem:                             Một bài toán lập trình đã được tách
                                      từ tài liệu hoặc nhập thủ công

  Normalized statement:                Đề bài được chuẩn hóa thành các
                                      trường có cấu trúc

  Brute-force solution:                Lời giải tham chiếu có độ phức tạp
                                      cao hơn, dùng để đối chiếu trên
                                      miền dữ liệu nhỏ phù hợp

  Optimized solution:                  Lời giải tham chiếu dự kiến xử lý
                                      miền dữ liệu mục tiêu

  Test case:                           Một cặp input/output cùng metadata
                                      và trạng thái xác minh

  Test group:                          Nhóm testcase có giới hạn hoặc
                                      chiến lược sinh riêng

  Generator:                           Thành phần tạo input theo cấu hình
                                      và seed

  Validator:                           Thành phần kiểm tra input có tuân
                                      thủ định dạng/ràng buộc hay không

  Oracle:                              Chương trình hoặc cơ chế tạo output
                                      tham chiếu

  Differential testing:                Đối chiếu output của các lời giải
                                      trên cùng input

  Job:                                 Một tác vụ nền có trạng thái, tiến
                                      trình, log và kết quả

  Artifact:                            File được quản lý bởi hệ thống, ví
                                      dụ PDF, mã nguồn, input, output,
                                      ZIP

  Seed:                                Giá trị khởi tạo để tái lập quá
                                      trình sinh dữ liệu ngẫu nhiên

  Sandbox:                             Môi trường cô lập để biên dịch và
                                      chạy mã nguồn không đáng tin cậy

  MVP:                                 Phiên bản đầu tiên với phạm vi chức
                                      năng được giới hạn và có thể nghiệm
                                      thu
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 2. Baseline Product Decisions

## 2.1 Confirmed Decisions

  -----------------------------------------------------------------------
  ID                      Decision                Baseline
  ----------------------- ----------------------- -----------------------
  DEC-01                  Product form            Website

  DEC-02                  Frontend                React + TypeScript +
                                                  Vite

  DEC-03                  Backend                 FastAPI / Python

  DEC-04                  Primary database        PostgreSQL

  DEC-05                  Database access         SQLAlchemy 2.x

  DEC-06                  Schema migration        Alembic

  DEC-07                  Background jobs         Celery

  DEC-08                  Queue/broker            Redis

  DEC-09                  File storage            Storage abstraction;
                                                  local-compatible
                                                  storage in development
                                                  and S3-compatible
                                                  object storage for
                                                  deployment

  DEC-10                  C++ runtime             Dedicated worker,
                                                  isolated sandbox, C++17

  DEC-11                  Initial deployment      Docker Compose

  DEC-12                  Architecture style      Modular monolith
                                                  backend plus
                                                  independently runnable
                                                  workers

  DEC-13                  Target                  Product designed to
                                                  support multiple users
                                                  over time

  DEC-14                  API versioning          `/api/v1`

  DEC-15                  Primary language for    C++17
                          generated solutions     
  -----------------------------------------------------------------------

## 2.2 Architecture Principles

1.  **Modular monolith first:** business modules share one backend
    codebase; heavy/background work runs in separate worker processes or
    containers.
2.  **API is the system boundary:** frontend does not access PostgreSQL,
    Redis, the server shell, or worker workspaces directly.
3.  **PostgreSQL is the source of truth** for business metadata and
    durable job status. Redis is a broker/cache, not the sole durable
    record.
4.  **Files are stored separately from relational metadata.** Database
    records store storage keys, ownership, checksums, content types,
    sizes and lifecycle metadata.
5.  **AI output is untrusted and fallible.** Generated statements, code
    and tests must be validated and their verification status disclosed.
6.  **Untrusted code is isolated.** The API process must never directly
    execute user-supplied or AI-generated C++.
7.  **Reproducibility:** record relevant input versions, configuration,
    seeds, tool versions and checksums.
8.  **Explicit state transitions:** jobs and artifacts have defined
    statuses; errors are visible and cannot be silently treated as
    success.
9.  **Least privilege:** users and workers receive only the access
    needed for their task.
10. **Incremental scaling:** increase worker capacity first; introduce
    microservices or orchestration platforms only when measured needs
    justify them.

## 2.3 Assumptions

-   The system is initially developed and tested by a small team.
-   Users have a modern browser and an Internet connection when external
    AI APIs are used.
-   The deployment environment can run Python, PostgreSQL, Redis, a
    supported C++ compiler and a suitable isolation mechanism.
-   The system supports deterministic-output problems as the initial
    target.
-   Documents may contain selectable text, scanned pages, or images; OCR
    quality varies and may require human review.
-   A configured AI provider may impose rate limits, costs, quotas or
    temporary outages.
-   The product does not guarantee mathematical proof of correctness for
    AI-generated solutions or completeness of generated tests.

## 2.4 Constraints

-   Generated reference solutions use C++17 in the MVP.
-   All external API secrets remain on the backend or in secret
    management, never in frontend bundles.
-   Production execution must not rely on unrestricted shell access or a
    privileged container.
-   No test pack can be marked "verified" merely because generation
    completed successfully.
-   The system must preserve the user's source document and distinguish
    it from the normalized statement.
-   A change to the statement, solution, generator configuration or
    relevant tool version may invalidate previous verification results.

------------------------------------------------------------------------

# 3. Scope

## 3.1 In Scope --- MVP

-   User registration, login and logout.
-   Ownership-based authorization for projects and all subordinate
    resources.
-   Project creation, listing, update and deletion.
-   Upload of PDF, DOCX, Markdown, TXT, PNG and JPG files, subject to
    configured limits.
-   Text extraction and OCR fallback for image-based documents.
-   Document preview and problem extraction/editing.
-   Structured normalized statement, including constraints,
    input/output, samples and metadata.
-   Human confirmation of the normalized statement before official test
    generation.
-   AI-assisted generation of brute-force and optimized C++17 solutions
    plus explanation.
-   Manual editing/upload of reference solutions.
-   Compilation and sample checks.
-   Test configuration with groups, counts, constraints, strategies and
    seeds.
-   Input generation, input validation and reference output generation.
-   Differential testing and basic stress testing where a suitable
    brute-force solution exists.
-   Job progress, logs, errors and validation reports.
-   ZIP export for a problem and/or project, including manifest.
-   Versioning/provenance sufficient to identify which inputs and
    configurations produced an artifact.
-   Automated unit and integration tests for critical flows.

## 3.2 Out of Scope --- MVP

-   Full online judge, public submissions, ranking, contests or live
    leaderboard.
-   Guaranteed formal proof of arbitrary algorithm correctness.
-   Guaranteed automatic interpretation of every document, diagram,
    table or mathematical notation.
-   Languages other than C++17 for generated/reference solutions.
-   Custom checker support for arbitrary non-unique outputs, unless
    separately approved as an extension.
-   Advanced mutation testing and automatic minimization as required
    release features.
-   Real-time collaborative editing.
-   Payments, subscriptions and billing.
-   Native mobile applications.
-   Kubernetes or mandatory microservices.
-   Automatic publishing to third-party contest platforms.
-   Public sharing of projects and artifacts unless added through a
    future access-control requirement.

## 3.3 Future Candidates

-   Google/GitHub OAuth;
-   custom generator, validator and checker code;
-   multiple output checkers;
-   mutation testing and counterexample minimization;
-   project sharing and team workspaces;
-   additional programming languages;
-   external online-judge export profiles;
-   object-storage lifecycle policies and enterprise retention;
-   advanced usage quotas and billing.

Future candidates do not become MVP commitments unless accepted through
change control.

------------------------------------------------------------------------

# 4. Users and Permissions

## 4.1 Actor

**Registered User:** a person with an account who owns projects and can
create, modify, run and export resources they are authorized to access.

System services (AI provider, queue, storage and workers) are technical
components, not interactive actors.

## 4.2 Authorization Rules

-   Every private project belongs to one user in MVP.
-   Every problem, document, solution, configuration, job, report and
    export must be reachable only through a resource owned by the
    requesting user.
-   Backend authorization is mandatory for read, create, update, delete,
    download, execution and export operations.
-   Knowing or guessing a resource ID must not grant access.
-   Workers must validate that a job exists and its input artifacts
    belong to the same authorized project/user scope.
-   Frontend button visibility is not an authorization control.
-   Secrets and credentials must never be returned in ordinary API
    responses or logs.

## 4.3 Authentication Baseline

MVP must provide email/password authentication unless a documented
product decision replaces it with an equivalent supported mechanism.

Requirements: - Passwords are stored using a modern password-hashing
algorithm via a maintained library. - Login failures return safe,
non-revealing errors. - Authentication credentials are transported only
over HTTPS in deployed environments. - Session/token expiration and
logout behavior are defined. - Password reset must use a secure,
expiring, single-use flow if email/password accounts are offered
publicly. - Apply rate limits or equivalent abuse controls to
registration and login endpoints. - OAuth providers are optional future
additions.

The final session mechanism (secure cookie session or access/refresh
tokens) must be selected in the authentication design record before
implementation. If cookies are used, CSRF protections and secure cookie
flags are required.

------------------------------------------------------------------------

# 5. Functional Requirements

Priority levels: - **P0:** required for MVP-0 core pipeline acceptance. - **P1 (MVP-1):**
multi-user web platform requirements. - **P2:** future
enhancement.

## 5.1 Authentication and Account

  -----------------------------------------------------------------------
  ID                      Priority                Requirement
  ----------------------- ----------------------- -----------------------
  FR-AUTH-01              P1 (MVP-1)              The system shall allow
                                                  a user to register an
                                                  account with valid
                                                  required information.

  FR-AUTH-02              P1 (MVP-1)              The system shall
                                                  authenticate registered
                                                  users.

  FR-AUTH-03              P1 (MVP-1)              The system shall allow
                                                  a user to log out.

  FR-AUTH-04              P1 (MVP-1)              The system shall
                                                  prevent access to
                                                  private resources
                                                  without valid
                                                  authorization.

  FR-AUTH-05              P1 (MVP-1)              The system shall apply
                                                  ownership checks to all
                                                  resource operations.

  FR-AUTH-06              P1 (MVP-1)              The system should
                                                  provide secure password
                                                  reset if email/password
                                                  authentication is
                                                  enabled for external
                                                  users.

  FR-AUTH-07              P1 (MVP-1)              The system should
                                                  expose account status
                                                  and allow account
                                                  deactivation/deletion
                                                  under a documented
                                                  retention policy.
  -----------------------------------------------------------------------

## 5.2 Projects

  -----------------------------------------------------------------------
  ID                      Priority                Requirement
  ----------------------- ----------------------- -----------------------
  FR-PROJ-01              P1 (MVP-1)              A user shall create a
                                                  project with a name and
                                                  optional description.

  FR-PROJ-02              P1 (MVP-1)              A user shall list and
                                                  open only projects they
                                                  own or are explicitly
                                                  authorized to access.

  FR-PROJ-03              P1 (MVP-1)              A user shall update
                                                  project metadata.

  FR-PROJ-04              P1 (MVP-1)              A user shall delete a
                                                  project after
                                                  confirmation.

  FR-PROJ-05              P1 (MVP-1)              Project deletion shall
                                                  apply a defined
                                                  cascade/retention
                                                  policy to subordinate
                                                  records and stored
                                                  files.

  FR-PROJ-06              P1 (MVP-1)              The system should
                                                  support search, sorting
                                                  and pagination for
                                                  project lists.
  -----------------------------------------------------------------------

## 5.3 Document Upload and Extraction

  -----------------------------------------------------------------------
  ID                      Priority                Requirement
  ----------------------- ----------------------- -----------------------
  FR-DOC-01               P1 (MVP-1)              A user shall upload
                                                  supported PDF, DOCX,
                                                  Markdown, TXT, PNG and
                                                  JPG files.

  FR-DOC-02               P1 (MVP-1)              The system shall
                                                  validate file size,
                                                  extension, content type
                                                  and actual file
                                                  signature where
                                                  applicable.

  FR-DOC-03               P1 (MVP-1)              The system shall assign
                                                  a unique ID and storage
                                                  key to each uploaded
                                                  file.

  FR-DOC-04               P1 (MVP-1)              The system shall
                                                  extract text from
                                                  text-based PDF, DOCX,
                                                  Markdown and TXT.

  FR-DOC-05               P1 (MVP-1)              The system shall
                                                  support OCR fallback
                                                  for scanned or
                                                  image-based content
                                                  using a configured OCR
                                                  component.

  FR-DOC-06               P1 (MVP-1)              The system shall
                                                  preserve the original
                                                  uploaded document as a
                                                  separate artifact.

  FR-DOC-07               P1 (MVP-1)              The system shall expose
                                                  extraction status,
                                                  errors and review
                                                  flags.

  FR-DOC-08               P1 (MVP-1)              The user shall be able
                                                  to inspect and edit
                                                  extracted text before
                                                  confirming it.

  FR-DOC-09               P1 (MVP-1)              The system shall
                                                  support a document
                                                  containing multiple
                                                  problems and allow
                                                  users to review the
                                                  proposed problem
                                                  boundaries.

  FR-DOC-10               P1 (MVP-1)              The system should show
                                                  page references or OCR
                                                  confidence indicators
                                                  when available.

  FR-DOC-11               P1 (MVP-1)              Failed extraction shall
                                                  not be reported as
                                                  successful; the user
                                                  shall receive an
                                                  actionable error.
  -----------------------------------------------------------------------

Initial configurable limits: 20 MB per file, 20 files per upload batch,
and 50 extracted problems per processing request. These are initial
defaults, not hard-coded product truths.

## 5.4 Problem Normalization and Review

  -----------------------------------------------------------------------
  ID                      Priority                Requirement
  ----------------------- ----------------------- -----------------------
  FR-PRB-01               P0                      Each problem shall have
                                                  a unique ID independent
                                                  of its display name or
                                                  exported folder name.

  FR-PRB-02               P0                      The normalized
                                                  statement shall support
                                                  title, statement, input
                                                  format, output format,
                                                  constraints, examples
                                                  and optional
                                                  time/memory limits.

  FR-PRB-03               P0                      The system shall retain
                                                  a link to the source
                                                  document and extraction
                                                  version.

  FR-PRB-04               P0                      The user shall be able
                                                  to edit normalized
                                                  fields.

  FR-PRB-05               P0                      The user shall
                                                  explicitly confirm the
                                                  normalized statement
                                                  before official
                                                  testcase generation.

  FR-PRB-06               P0                      Missing, contradictory
                                                  or low-confidence
                                                  constraints shall be
                                                  flagged for review.

  FR-PRB-07               P0                      A statement revision
                                                  shall create a new
                                                  version or revision
                                                  record and invalidate
                                                  dependent verification
                                                  status where relevant.
  -----------------------------------------------------------------------

## 5.5 Solution Generation and Management

  -----------------------------------------------------------------------
  ID                      Priority                Requirement
  ----------------------- ----------------------- -----------------------
  FR-SOL-01               P0                      The system shall
                                                  request an AI-generated
                                                  brute-force solution
                                                  where feasible, an
                                                  optimized solution and
                                                  a written explanation.

  FR-SOL-02               P0                      Generated C++ source
                                                  shall target C++17.

  FR-SOL-03               P0                      The explanation shall
                                                  include algorithm idea,
                                                  correctness reasoning
                                                  and time/space
                                                  complexity, where
                                                  applicable.

  FR-SOL-04               P0                      The user shall be able
                                                  to inspect and edit
                                                  generated source code.

  FR-SOL-05               P0                      The user shall be able
                                                  to upload or paste a
                                                  manually authored
                                                  reference solution.

  FR-SOL-06               P0                      Each solution shall
                                                  have a version, source
                                                  type, creation time and
                                                  verification status.

  FR-SOL-07               P0                      The system shall
                                                  compile solutions in
                                                  the isolated execution
                                                  environment.

  FR-SOL-08               P0                      The system shall run
                                                  sample tests when
                                                  examples are available
                                                  and parseable.

  FR-SOL-09               P0                      The system shall report
                                                  compile errors, runtime
                                                  errors, timeouts and
                                                  non-zero exit codes.

  FR-SOL-10               P0                      The system shall not
                                                  label a solution
                                                  "correct" solely
                                                  because it compiles or
                                                  passes examples.

  FR-SOL-11               P0                      If brute force is
                                                  infeasible or cannot be
                                                  derived safely, the
                                                  system shall flag that
                                                  fact rather than
                                                  fabricate a trusted
                                                  oracle.

  FR-SOL-12               P1                      The system should
                                                  support multiple named
                                                  versions and comparison
                                                  of their validation
                                                  results.
  -----------------------------------------------------------------------

The brute-force solution is an oracle candidate only for input ranges it
can feasibly handle. It must not be run against large tests without
explicit safe limits.

## 5.6 Test Configuration

  -----------------------------------------------------------------------
  ID                      Priority                Requirement
  ----------------------- ----------------------- -----------------------
  FR-CFG-01               P0                      The user shall
                                                  configure a target
                                                  number of testcases.

  FR-CFG-02               P0                      The user shall define
                                                  multiple test groups
                                                  with separate counts
                                                  and constraints.

  FR-CFG-03               P0                      Each group shall
                                                  support a strategy
                                                  selected from the
                                                  strategies implemented
                                                  for that problem.

  FR-CFG-04               P0                      The user shall
                                                  configure or accept a
                                                  random seed.

  FR-CFG-05               P0                      The user shall
                                                  configure test
                                                  naming/indexing and
                                                  export layout.

  FR-CFG-06               P0                      The system shall
                                                  validate group counts
                                                  and reject
                                                  configurations whose
                                                  total exceeds
                                                  configured limits.

  FR-CFG-07               P0                      The system shall show
                                                  an estimated workload
                                                  or warn when
                                                  configuration may
                                                  exceed available
                                                  limits.

  FR-CFG-08               P0                      The configuration shall
                                                  be versioned and linked
                                                  to generated tests.

  FR-CFG-09               P0                      The system shall
                                                  distinguish requested
                                                  test count from
                                                  successfully generated
                                                  and accepted test
                                                  count.

  FR-CFG-10               P1                      The system should
                                                  support reproducible
                                                  reruns of an individual
                                                  group.
  -----------------------------------------------------------------------

A test strategy must be compatible with the problem's input schema.
Generic "random integers" are not sufficient for arbitrary structured
problems.

## 5.7 Test Generation and Validation

  -----------------------------------------------------------------------
  ID                      Priority                Requirement
  ----------------------- ----------------------- -----------------------
  FR-TST-01               P0                      The system shall
                                                  generate input
                                                  according to the
                                                  confirmed statement and
                                                  configuration.

  FR-TST-02               P0                      Every generated input
                                                  shall be validated
                                                  before being accepted.

  FR-TST-03               P0                      The system shall
                                                  support applicable
                                                  boundary and edge
                                                  cases.

  FR-TST-04               P0                      The system shall
                                                  support seeded random
                                                  generation when a
                                                  random strategy is
                                                  selected.

  FR-TST-05               P0                      The system shall
                                                  generate output using a
                                                  selected, compiled
                                                  reference solution or
                                                  another explicitly
                                                  approved oracle.

  FR-TST-06               P0                      The system shall
                                                  capture oracle exit
                                                  status, runtime,
                                                  timeout and stderr.

  FR-TST-07               P0                      The system shall
                                                  support differential
                                                  testing between
                                                  suitable reference
                                                  solutions on small
                                                  input domains.

  FR-TST-08               P0                      A detected output
                                                  mismatch shall mark the
                                                  relevant verification
                                                  step as failed and
                                                  block release until
                                                  resolved or explicitly
                                                  reviewed under a
                                                  documented exception
                                                  policy.

  FR-TST-09               P0                      The system shall detect
                                                  duplicate inputs
                                                  according to a
                                                  configurable
                                                  canonicalization policy
                                                  where practical.

  FR-TST-10               P0                      The system shall retain
                                                  enough metadata to
                                                  reproduce accepted
                                                  inputs.

  FR-TST-11               P0                      The system shall not
                                                  claim full correctness
                                                  or complete edge-case
                                                  coverage solely from
                                                  differential testing.

  FR-TST-12               P0                      If no trustworthy
                                                  oracle is available,
                                                  the system shall mark
                                                  output generation or
                                                  verification as
                                                  requiring review and
                                                  shall not imply it is
                                                  verified.

  FR-TST-13               P1                      The system should
                                                  support adversarial
                                                  generators tailored to
                                                  the problem structure.

  FR-TST-14               P2                      The system may support
                                                  mutation testing and
                                                  counterexample
                                                  minimization in a
                                                  future release.
  -----------------------------------------------------------------------

## 5.8 Jobs and Progress

  -----------------------------------------------------------------------
  ID                      Priority                Requirement
  ----------------------- ----------------------- -----------------------
  FR-JOB-01               P0                      Long-running operations
                                                  shall execute as
                                                  background jobs.

  FR-JOB-02               P0                      Every job shall have a
                                                  unique ID, owner, type,
                                                  input version, status
                                                  and timestamps.

  FR-JOB-03               P0                      The user shall view job
                                                  status, progress where
                                                  measurable, logs and
                                                  actionable errors.

  FR-JOB-04               P0                      The system shall
                                                  support `queued`,
                                                  `running`, `succeeded`,
                                                  `failed`, `cancelled`
                                                  and `timed_out`
                                                  terminal/state
                                                  semantics as
                                                  applicable.

  FR-JOB-05               P0                      The system shall not
                                                  expose another user's
                                                  job or logs.

  FR-JOB-06               P0                      Retry shall be limited
                                                  to operations known to
                                                  be safe or protected by
                                                  idempotency controls.

  FR-JOB-07               P1                      The user should be able
                                                  to cancel a queued job
                                                  and request
                                                  cancellation of a
                                                  running job.

  FR-JOB-08               P0                      A worker crash or lost
                                                  task shall not silently
                                                  result in a successful
                                                  job status.
  -----------------------------------------------------------------------

## 5.9 Reports and Export

  -----------------------------------------------------------------------
  ID                      Priority                Requirement
  ----------------------- ----------------------- -----------------------
  FR-EXP-01               P0                      The user shall export
                                                  one problem or a
                                                  project according to
                                                  supported export
                                                  options.

  FR-EXP-02               P0                      The package shall
                                                  contain accepted
                                                  input/output files and
                                                  the selected
                                                  solution/source
                                                  artifacts.

  FR-EXP-03               P0                      The package shall
                                                  include a manifest
                                                  describing problem ID,
                                                  configuration, seeds,
                                                  artifact versions,
                                                  checksums and
                                                  verification status.

  FR-EXP-04               P0                      The package shall
                                                  include a validation
                                                  report or a reference
                                                  to a report included in
                                                  the package.

  FR-EXP-05               P0                      The system shall verify
                                                  that all required files
                                                  exist before marking an
                                                  export successful.

  FR-EXP-06               P0                      The system shall
                                                  compute checksums for
                                                  exported artifacts
                                                  where supported.

  FR-EXP-07               P0                      The system shall not
                                                  overwrite an existing
                                                  released version
                                                  without an explicit
                                                  user action.

  FR-EXP-08               P0                      The user shall download
                                                  only exports they are
                                                  authorized to access.

  FR-EXP-09               P1                      The system should
                                                  support tests-only and
                                                  per-problem ZIP
                                                  layouts.
  -----------------------------------------------------------------------

Suggested default layout:

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

The export layout is configurable in later iterations; the MVP must
implement at least one documented, stable default layout.

------------------------------------------------------------------------

# 6. Quality and Verification Model

## 6.1 Verification Statuses

The system shall use explicit, non-misleading statuses. Suggested
baseline:

-   `NOT_CHECKED`: no verification has been performed.
-   `CHECKING`: verification is in progress.
-   `PASSED_CHECKS`: configured automated checks passed; this is not a
    proof of correctness.
-   `NEEDS_REVIEW`: uncertainty, missing oracle, OCR ambiguity or
    incomplete validation remains.
-   `FAILED`: a required check failed.
-   `STALE`: an input, solution, configuration or tool version changed
    after verification.

The UI may show friendly labels, but must retain precise status
semantics in stored records and API responses.

## 6.2 Required Validation Pipeline

1.  Confirm normalized statement.
2.  Validate configuration against constraints.
3.  Compile required solution/generator programs.
4.  Run sample tests when available.
5.  Generate input.
6.  Validate input format and constraints.
7.  Execute the approved oracle in the sandbox.
8.  Capture output and execution metadata.
9.  Run differential checks where applicable.
10. Check duplicate inputs and expected file count.
11. Create validation report.
12. Mark accepted artifacts and allow export only according to release
    policy.

## 6.3 Oracle Limitations

-   Two programs can share the same bug.
-   A brute-force solution may be correct only for a smaller domain.
-   Passing samples does not establish correctness.
-   Random tests may miss rare edge cases.
-   Some problems permit multiple valid outputs; exact text comparison
    is not sufficient for those problems.
-   If the output is non-unique, a checker/validator is needed;
    otherwise the problem must be marked unsupported or requiring manual
    review for official output verification.

## 6.4 Test Quality Reporting

A report should include: - total requested/generated/accepted tests; -
counts by test group; - seed and generator version; - validator
result; - oracle result and execution errors; - differential result and
mismatch details; - duplicate-input findings; - unverified limitations
and review flags; - timestamps and artifact checksums.

------------------------------------------------------------------------

# 7. Data Model Baseline

This is a logical entity baseline. Physical schema details, column
types, indexes and deletion semantics shall be finalized in an ERD and
migration design.

  -----------------------------------------------------------------------
  Entity                  Purpose                 Important relationships
  ----------------------- ----------------------- -----------------------
  `users`                 Accounts and identity   Owns projects

  `projects`              User workspaces         Belongs to user;
                                                  contains documents and
                                                  problems

  `source_documents`      Uploaded originals and  Belongs to project
                          extraction metadata     

  `problem_revisions`     Versioned normalized    Belongs to problem
                          statements              

  `problems`              Stable problem identity Belongs to project

  `solution_versions`     Brute, optimized and    Belongs to
                          manually provided       problem/revision
                          solutions               

  `test_configurations`   Versioned global test   Belongs to problem
                          setup                   

  `test_groups`           Group counts, limits    Belongs to
                          and strategies          configuration

  `test_runs`             One                     Belongs to problem and
                          generation/validation   configuration
                          run                     

  `test_cases`            Per-test metadata and   Belongs to test
                          status                  run/group

  `artifacts`             File metadata and       Belongs to an
                          storage key             owner/resource

  `jobs`                  Durable background-job  Belongs to user and
                          state                   relevant resource

  `job_events`            Progress and event      Belongs to job
                          history                 

  `validation_reports`    Verification results    Belongs to run/solution
                                                  version

  `exports`               Generated ZIP metadata  Belongs to
                          and status              project/problem

  `audit_events`          Security-relevant       Belongs to
                          actions where needed    actor/resource
  -----------------------------------------------------------------------

## 7.1 Data Rules

-   Use UUIDs or another non-guessable stable identifier strategy for
    public-facing resource IDs.
-   Add foreign keys and indexes for common access paths.
-   Use UTC timestamps in storage and render in the user's local
    timezone.
-   Store checksums for artifacts that must be integrity-checked.
-   Use explicit deletion/retention policies for projects, uploads, test
    runs and exports.
-   Do not store raw passwords, AI provider secrets or credentials in
    business tables.
-   Use migrations for schema changes; do not mutate production schema
    ad hoc.
-   Use database transactions for logically atomic metadata changes.
-   Avoid storing large file contents in relational rows unless a
    specific reviewed requirement justifies it.

## 7.2 Suggested Indexes

Final indexes must be derived from actual query patterns, but likely
candidates include: - `projects(user_id, updated_at)`; -
`problems(project_id, created_at)`; -
`jobs(owner_user_id, status, created_at)`; -
`test_runs(problem_id, created_at)`; -
`artifacts(problem_id, created_at)`; -
`artifacts(test_run_id)`; - unique constraints for user email
and stable per-problem exported identifiers where appropriate.

------------------------------------------------------------------------

# 8. API Baseline

All application endpoints use `/api/v1`. The exact schemas and error
catalogue are to be documented in OpenAPI and the API design document.

## 8.1 Initial Endpoint Inventory

  -----------------------------------------------------------------------------------------------------
  Method                  Endpoint                                              Purpose
  ----------------------- ----------------------------------------------------- -----------------------
  POST                    `/api/v1/auth/register`                               Register

  POST                    `/api/v1/auth/login`                                  Login

  POST                    `/api/v1/auth/logout`                                 Logout

  GET                     `/api/v1/users/me`                                    Current user profile

  GET/POST                `/api/v1/projects`                                    List/create projects

  GET/PATCH/DELETE        `/api/v1/projects/{project_id}`                       Read/update/delete
                                                                                project

  POST                    `/api/v1/projects/{project_id}/documents`             Upload document

  GET                     `/api/v1/documents/{document_id}`                     Read document
                                                                                metadata/status

  POST                    `/api/v1/documents/{document_id}/extract`             Start extraction job

  GET/POST                `/api/v1/projects/{project_id}/problems`              List/create problems

  GET/PATCH               `/api/v1/problems/{problem_id}`                       Read/update normalized
                                                                                problem

  POST                    `/api/v1/problems/{problem_id}/confirm`               Confirm normalized
                                                                                statement

  POST                    `/api/v1/problems/{problem_id}/solutions/generate`    Start solution
                                                                                generation

  GET/POST                `/api/v1/problems/{problem_id}/solutions`             List/create solution
                                                                                versions

  POST                    `/api/v1/solutions/{solution_version_id}/compile`     Start compile/check job

  POST                    `/api/v1/problems/{problem_id}/generators/compile`    Compile & test generator
                                                                                in sandbox

  POST                    `/api/v1/problems/{problem_id}/validators/compile`    Compile & test validator
                                                                                in sandbox

  GET/POST                `/api/v1/problems/{problem_id}/test-configurations`   List/create test
                                                                                configs

  POST                    `/api/v1/problems/{problem_id}/test-runs`             Start test
                                                                                generation/validation

  GET                     `/api/v1/test-runs/{test_run_id}`                     Read run status/results

  GET                     `/api/v1/jobs/{job_id}`                               Read job status

  GET                     `/api/v1/jobs/{job_id}/events`                        Read job events

  GET                     `/api/v1/jobs/{job_id}/report`                        Read validation report

  POST                    `/api/v1/problems/{problem_id}/exports`               Start export

  GET                     `/api/v1/exports/{export_id}`                         Read export status

  GET                     `/api/v1/exports/{export_id}/download`                Download export if
                                                                                authorized
  -----------------------------------------------------------------------------------------------------

## 8.2 API Conventions

-   Use typed request and response schemas.
-   Use consistent error response structure with a stable error code and
    safe message.
-   Validate path IDs, query parameters, payload size and enum values.
-   Apply pagination to list endpoints that may grow.
-   Return `202 Accepted` for operations that start background jobs.
-   Return a job ID and status URL when a background task is accepted.
-   Use idempotency protection for expensive or duplicate-sensitive
    operations where appropriate.
-   Do not return stack traces, local filesystem paths, secrets or
    internal credentials.
-   Enforce authentication and ownership checks at the backend.
-   Keep API versioning explicit.

------------------------------------------------------------------------

# 9. Non-Functional Requirements

## 9.1 Security

  -----------------------------------------------------------------------
  ID                                  Requirement
  ----------------------------------- -----------------------------------
  NFR-SEC-01                          All deployed public traffic shall
                                      use HTTPS.

  NFR-SEC-02                          Authentication and authorization
                                      shall be enforced server-side.

  NFR-SEC-03                          File uploads shall be validated by
                                      size, allowed type and
                                      content/signature where applicable.

  NFR-SEC-04                          Uploaded files shall not be
                                      directly executable from the web
                                      root.

  NFR-SEC-05                          C++ compilation/execution shall
                                      occur in a restricted sandbox with
                                      CPU, memory, time, process,
                                      filesystem and output limits.

  NFR-SEC-06                          Sandbox network access shall be
                                      disabled by default.

  NFR-SEC-07                          The API process shall not run
                                      untrusted code directly.

  NFR-SEC-08                          Secrets shall be stored outside
                                      source control and frontend
                                      bundles.

  NFR-SEC-09                          Logs shall redact credentials,
                                      tokens and sensitive content where
                                      appropriate.

  NFR-SEC-10                          The system shall protect against
                                      cross-user access through
                                      object-level authorization checks.

  NFR-SEC-11                          Dependencies shall be
                                      pinned/reviewed and updated through
                                      a controlled process.

  NFR-SEC-12                          ZIP extraction, file paths and
                                      artifact names shall be protected
                                      against path traversal and unsafe
                                      filenames.
  -----------------------------------------------------------------------

## 9.2 Reliability and Data Integrity

-   Database transactions must protect critical metadata updates.
-   A failed worker must not silently mark a job successful.
-   Retryable jobs must be idempotent or have duplicate-prevention
    controls.
-   Accepted testcases must have complete input/output artifact
    metadata.
-   The export process must verify package contents before declaring
    success.
-   Database backup and restore procedures must be documented before
    production release.
-   Verification statuses must become stale when dependent inputs
    change.

## 9.3 Performance

The following are initial acceptance targets for a small reference
environment, not guarantees for all workloads:

  -----------------------------------------------------------------------
  ID                                  Target
  ----------------------------------- -----------------------------------
  NFR-PERF-01                         Ordinary metadata API requests
                                      should complete within 500 ms at
                                      p95 under a small reference load,
                                      excluding file transfer and
                                      external service latency.

  NFR-PERF-02                         Upload responses should return
                                      after validation and durable job
                                      creation where feasible, not wait
                                      for OCR/AI processing.

  NFR-PERF-03                         Long-running generation and compile
                                      tasks shall be asynchronous.

  NFR-PERF-04                         Worker concurrency shall be
                                      configurable and bounded.

  NFR-PERF-05                         The system shall expose enough
                                      timing and queue metrics to
                                      identify slow stages.

  NFR-PERF-06                         No performance target may override
                                      sandbox resource limits or
                                      correctness checks.
  -----------------------------------------------------------------------

A load-test profile must define the machine, dataset, number of
concurrent users, request mix and measurement period before performance
results are considered acceptance evidence.

## 9.4 Scalability

-   API instances should be stateless where practical.
-   Durable business state shall reside in PostgreSQL and object
    storage, not process memory.
-   Workers shall be independently scalable by task type.
-   Queue length, worker utilization and failure rate shall be
    observable.
-   The storage layer shall permit migration from development storage to
    S3-compatible storage without changing business logic.
-   The architecture shall not require microservices for the initial
    release.

## 9.5 Maintainability

-   Separate API, domain/business rules, persistence, integrations and
    worker execution.
-   Use typed schemas and explicit interfaces for AI, OCR, storage,
    compiler and checker integrations.
-   Use database migrations for schema evolution.
-   Add unit tests for business rules and integration tests for
    database/queue flows.
-   Document configuration, local setup, API conventions and operational
    recovery.
-   Keep configuration outside code and provide `.env.example` without
    secrets.

## 9.6 Observability

-   Structured logs with request/job correlation IDs.
-   Job event history with stage, status and timestamps.
-   Error categories for parse, AI provider, compile, runtime,
    validation, storage and export failures.
-   Metrics for API latency, job duration, queue depth, worker errors,
    compiler outcomes and storage use.
-   Avoid logging full source documents or secret values by default.
-   Provide health/readiness checks for API and required infrastructure
    dependencies.

## 9.7 Accessibility and Usability

-   Main flows shall be usable with keyboard navigation.
-   Forms shall show field-level validation messages.
-   Job status shall be visible without requiring repeated full-page
    reloads.
-   Errors shall explain what failed and what the user can do next.
-   Destructive actions such as project deletion require confirmation.
-   The UI shall clearly distinguish draft, failed, stale, reviewed and
    passed-check states.

------------------------------------------------------------------------

# 10. UI and User Workflow Requirements

## 10.1 Main Screens

1.  **Authentication:** register, login and password recovery if
    enabled.
2.  **Dashboard:** recent projects, job summaries and quick actions.
3.  **Project list/detail:** project metadata, documents, problems and
    recent activity.
4.  **Document import:** upload, progress, extraction errors and review.
5.  **Problem review:** source preview, normalized statement,
    constraints and confirmation.
6.  **Solutions:** brute/optimized source, explanation, compilation
    output and version history.
7.  **Test configuration:** test groups, counts, limits, strategies,
    seed and naming.
8.  **Generation job:** progress, logs, cancellation where supported and
    stage outcomes.
9.  **Validation report:** test counts, mismatches, runtime failures,
    review flags and verification status.
10. **Export:** output layout, selected files, ZIP creation and
    download.

## 10.2 Main User Journey

1.  Register/login.
2.  Create a project.
3.  Upload one or more source documents.
4.  Wait for extraction and review extracted content.
5.  Confirm the normalized problem statement.
6.  Generate or provide reference solutions.
7.  Compile and run sample checks.
8.  Configure test groups and seed.
9.  Start generation and validation.
10. Review warnings, failures and validation results.
11. Resolve blocking failures.
12. Generate ZIP and download it.
13. Reopen the project later and inspect its history.

## 10.3 Failure and Recovery UX

The UI shall distinguish: - validation error in user input; -
unsupported document; - OCR/extraction uncertainty; - AI provider
failure or rate limit; - compile error; - runtime error or timeout; -
input validation failure; - reference output mismatch; - worker/queue
failure; - export failure.

Each failure should preserve completed valid artifacts when possible and
provide a retry or correction path. A retry must not silently replace a
previously released artifact.

------------------------------------------------------------------------

# 11. Job State Model

## 11.1 Job States

-   `PENDING` / `QUEUED`
-   `RUNNING`
-   `SUCCEEDED`
-   `FAILED`
-   `FAILED_INFRASTRUCTURE`
-   `CANCEL_REQUESTED`
-   `CANCELLED`
-   `TIMED_OUT`
-   `APPROVED_FOR_EXPORT`

A job may have stage-level events such as `EXTRACTING`, `NORMALIZING`,
`GENERATING_SOLUTION`, `COMPILING`, `GENERATING_TESTS`, `VALIDATING`,
`RUNNING_ORACLE`, `DIFFERENTIAL_TESTING` and `PACKAGING`.

## 11.2 State Rules

-   Only valid transitions are allowed.
-   Terminal states are not changed to success by a late worker event
    without reconciliation.
-   A retry creates a new attempt or explicitly records the retry
    attempt.
-   Progress percentage is optional where work cannot be measured
    accurately; stage and status must still be available.
-   Cancellation is best-effort for a running subprocess and must
    terminate contained child processes safely.
-   Stale jobs require a recovery policy based on heartbeat/lease or
    worker status.
-   Job events must be associated with the correct job and authorized
    owner.

------------------------------------------------------------------------

# 12. Baseline Repository Structure

``` text
problem-to-testcase-generator/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   ├── projects/
│   │   │   ├── documents/
│   │   │   ├── problems/
│   │   │   ├── solutions/
│   │   │   ├── testcases/
│   │   │   ├── jobs/
│   │   │   └── exports/
│   │   ├── services/
│   │   ├── types/
│   │   └── routes/
│   └── tests/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   ├── core/
│   │   ├── modules/
│   │   │   ├── auth/
│   │   │   ├── users/
│   │   │   ├── projects/
│   │   │   ├── documents/
│   │   │   ├── problems/
│   │   │   ├── solutions/
│   │   │   ├── testcases/
│   │   │   ├── jobs/
│   │   │   └── exports/
│   │   ├── integrations/
│   │   │   ├── ai/
│   │   │   ├── ocr/
│   │   │   └── storage/
│   │   ├── db/
│   │   └── main.py
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

This is a proposed logical structure. It may be simplified during the
first implementation, provided module boundaries and security boundaries
remain intact.

------------------------------------------------------------------------

# 13. Testing Strategy

## 13.1 Unit Tests

Cover: - domain validation rules; - test group count and limit
validation; - state transitions; - authorization policy functions; -
naming and manifest generation; - seed/configuration normalization; -
output status classification.

## 13.2 Integration Tests

Cover: - FastAPI + PostgreSQL persistence; - Alembic migrations from a
clean database; - object storage adapter; - Redis/Celery job enqueue and
completion; - job state recovery; - upload/extraction status flow; -
artifact ownership and download authorization.

## 13.3 End-to-End Tests

At minimum, automate: 1. register/login; 2. create project; 3. upload a
supported text-based problem; 4. confirm normalized statement; 5. save a
reference solution; 6. create test configuration; 7. run a small
generation/validation job; 8. view report; 9. export ZIP; 10. verify ZIP
content and manifest; 11. verify a different user cannot access the
project or download.

## 13.4 C++ Worker Tests

Test: - successful compile and run; - compile error; - runtime error; -
timeout; - memory limit; - excessive stdout/stderr; - child process
handling; - filesystem boundary; - disabled network; - cleanup after
failure; - one job cannot access another job's workspace.

Tests of isolation must be performed in a disposable environment and
reviewed before production use.

------------------------------------------------------------------------

# 14. MVP Acceptance Criteria

MVP is acceptable only when all P0 requirements have been implemented or
an explicit, approved exception is documented.

  -----------------------------------------------------------------------
  ID                      Acceptance criterion    Evidence
  ----------------------- ----------------------- -----------------------
  AC-01                   A user can register,    Automated end-to-end
                          log in and log out      test

  AC-02                   User A cannot access    Authorization tests
                          User B's private        
                          project, document, job, 
                          report or export        

  AC-03                   Supported documents can Integration tests and
                          be uploaded and         UI evidence
                          processed, or fail with 
                          a clear actionable      
                          error                   

  AC-04                   A user can review and   End-to-end test
                          confirm a normalized    
                          problem statement       

  AC-05                   The system can save and Worker integration test
                          compile a C++17         
                          reference solution in   
                          the sandbox             

  AC-06                   A user can configure at UI and API tests
                          least two test groups   
                          with different          
                          constraints/counts      

  AC-07                   Generated inputs pass   Test report
                          the configured          
                          validator before        
                          acceptance              

  AC-08                   Output is generated by  Worker/report evidence
                          an approved oracle and  
                          execution metadata is   
                          captured                

  AC-09                   A detected differential Automated negative test
                          mismatch blocks         
                          ordinary release        

  AC-10                   Job state and errors    Persistence test
                          remain visible after    
                          the frontend reloads    

  AC-11                   A ZIP export contains   ZIP integrity test
                          all required files      
                          listed in its manifest  

  AC-12                   A changed input version Version invalidation
                          marks dependent         test
                          verification stale      

  AC-13                   C++ execution is        Sandbox security test
                          isolated from the API   
                          process and respects    
                          configured resource     
                          limits                  

  AC-14                   Database schema can be  Migration test
                          created from migrations 
                          on a clean environment  

  AC-15                   Setup, configuration,   Documentation review
                          test and recovery       
                          instructions are        
                          documented              
  -----------------------------------------------------------------------

## 14.1 Release Gate

A release candidate must not be declared complete if: - a P0 acceptance
criterion fails; - there is a known cross-user data access issue; -
untrusted code executes with unrestricted host privileges; - the system
reports an unverified test pack as verified; - exported files are
missing or corrupt; - the application cannot recover from an ordinary
worker/job failure without silent data loss.

------------------------------------------------------------------------

# 15. Initial Operational Defaults

The following are initial configurable values for development and first
acceptance tests.

  -----------------------------------------------------------------------
  Setting                                                 Initial default
  ------------------------------ ----------------------------------------
  Maximum upload size                                          20 MB/file

  Files per batch                                                      20

  Problems per processing                                              50
  request                        

  Default testcase count                                       50/problem

  Maximum testcase count                                    1,000/problem

  C++17 compile/run timeout      5 seconds per execution by default, with
                                       separate policies for brute force,
                                         generator and optimized solution

  Maximum background job                                       30 minutes
  duration                       

  API prefix                                                    `/api/v1`

  Initial export format                                               ZIP

  Initial generated-solution                                        C++17
  language                       
  -----------------------------------------------------------------------

These defaults must be enforced by backend configuration, not only by
frontend validation. Limits should be configurable per deployment and
adjusted after benchmarking.

------------------------------------------------------------------------

# 16. Risks and Mitigations

  -----------------------------------------------------------------------
  Risk                    Impact                  Mitigation
  ----------------------- ----------------------- -----------------------
  OCR misreads            Invalid                 Human review,
  constraints or symbols  algorithm/testcases     confidence flags,
                                                  preserve source and
                                                  extraction version

  AI generates incorrect  Wrong reference output  Compile, samples,
  code                                            differential testing,
                                                  review status and
                                                  alternative oracle

  Two solutions share a   False confidence        Edge/adversarial tests,
  bug                                             manual review,
                                                  independent approaches;
                                                  never claim proof

  Invalid generator       Rejected or misleading  Validator before
  output                  tests                   acceptance

  Unsafe C++ execution    Host compromise or data Dedicated sandbox,
                          leakage                 least privilege, no
                                                  network, quotas and
                                                  workspace isolation

  AI provider outage/rate Jobs fail or stall      Timeouts, backoff,
  limits                                          error states, bounded
                                                  retries and provider
                                                  abstraction

  Queue/worker failure    Stuck jobs              Durable job records,
                                                  heartbeats,
                                                  reconciliation and safe
                                                  retries

  Concurrent duplicate    Duplicate               Idempotency keys and
  requests                cost/artifacts          unique job/run
                                                  constraints where
                                                  appropriate

  Storage grows without   Cost and performance    Quotas, retention
  control                 impact                  policy, cleanup jobs
                                                  and usage metrics

  Scope creep             MVP delay               P0/P1/P2 prioritization
                                                  and change control

  Export mismatch with    Package unusable        Stable default layout,
  judge format                                    manifest and optional
                                                  export profiles later
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 17. Delivery Plan

The schedule is a staged delivery baseline reconciled with Amendment Section A.

## Phase 0 (MVP-0) --- Local Core Pipeline (CLI)

Target: 2–3 weeks. Validate the core problem-to-testcase generation and sandbox pipeline before building multi-user web infrastructure.

-   CLI or local script interface (no web UI, no auth, no database needed).
-   One Markdown or plain-text problem statement per run.
-   Generate/review `brute.cpp`, `optimized.cpp`, `generator.cpp`, `validator.cpp`, and `explanation.md`.
-   Compile and run C++17 artifacts in an isolated Docker sandbox.
-   Run sample tests and bounded differential tests against small inputs.
-   Generate seeded test batches with independent C++ validation of every input.
-   Present validation report and representative tests for human review.
-   Export approved result as ZIP with SHA-256 manifest.

**Exit condition:** Local core pipeline satisfies the 10 MVP-0 acceptance criteria in Section A.

## Phase 1 (MVP-1) --- Multi-User Web Platform

Target: 1–2 months after MVP-0.

-   FastAPI backend + React/TypeScript/Vite frontend.
-   Authentication and resource ownership.
-   PostgreSQL database + SQLAlchemy 2.x + Alembic migrations.
-   Redis + Celery asynchronous background jobs.
-   Projects, document upload (PDF/DOCX) and OCR fallback.
-   Local/S3-compatible storage abstraction.

**Exit condition:** authenticated user can create a project and upload a
document.

## Phase 2 --- Problem Pipeline

-   Document parsing/OCR.
-   Problem extraction and normalization.
-   Review/edit/confirm flow.
-   AI integration abstraction.
-   Solution versioning and compile checks.

**Exit condition:** one confirmed problem can be linked to a compiled
reference solution.

## Phase 3 --- Test Engine

-   Test configuration and groups.
-   Generator interface and seed handling.
-   Input validation.
-   Oracle execution and differential testing.
-   Validation report.

**Exit condition:** small, deterministic test run is reproducible and
produces a report.

## Phase 4 --- Export and Hardening

-   ZIP builder and manifest.
-   Ownership checks for downloads.
-   Worker recovery, timeout and cleanup.
-   End-to-end tests.
-   Setup and troubleshooting documentation.

**Exit condition:** acceptance criteria AC-01 through AC-15 pass or have
explicitly approved exceptions.

------------------------------------------------------------------------

# 18. Change Control and Baseline Management

Any change to a confirmed P0 requirement, primary stack or trust
boundary must be recorded in `docs/decisions/` or the project change
log.

Each proposed change should include: - change ID; - current
requirement/decision; - proposed change; - reason and expected
benefit; - affected modules and database/API contracts; - security and
migration implications; - effort estimate; - approval status.

A change is not accepted merely because it is easy to implement. It must
be evaluated against the MVP objective and its effect on existing
requirements.

------------------------------------------------------------------------

# 19. References

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

------------------------------------------------------------------------

# Appendix A. Decisions Still Open Before Production

These decisions do not block the initial SRS baseline, but must be made
before the corresponding implementation/release stage:

1.  AI provider/model and structured-output strategy.
2.  OCR engine and supported language configuration.
3.  Authentication session strategy and email delivery provider.
4.  Object storage provider for production.
5.  Exact sandbox runtime and host hardening profile.
6.  Detailed PostgreSQL schema, indexes, retention and deletion
    policies.
7.  Final API error catalogue and request/response schemas.
8.  Production hosting, backup, monitoring and secret-management
    solution.
9.  Whether non-unique-output problems are rejected, manually checked or
    supported through a custom checker.
10. Final load-test profile and production resource quotas.

# Appendix B. Baseline Summary

PTG MVP is a multi-user web application with React/TypeScript frontend,
FastAPI backend, PostgreSQL persistence, Redis/Celery background jobs,
separate artifact storage and isolated C++17 execution workers.

The MVP's central quality requirement is not merely to generate files.
It must make the origin, configuration, validation status and
limitations of every generated testcase traceable, and it must never
present unverified output as guaranteed correct.

---

# PTG SRS Amendment — Review Reconciliation (2026-10-11)

> **Authority:** This amendment supplements the baseline SRS v1.0. Where baseline requirements conflict with the staged scope and contracts below, this amendment governs the phase in question. Requirements marked P1/P2 are not MVP-0 blockers.

## A. Scope and acceptance gates

### MVP-0 (P0): local core pipeline, target 2–3 weeks

**Included:** one Markdown/TXT problem; generation and manual review of `brute.cpp`, `optimized.cpp`, `generator.cpp`, `explanation.md`; C++17 compilation; bounded sample/differential execution; independently validated generated inputs; reproducible seeded test batches; validation report; review of 3–5 sample cases; approved ZIP export with manifest.

**Excluded:** PDF/DOCX/OCR, authentication, multi-user projects, team workspaces, Celery/Redis, S3/MinIO, production monitoring, advanced special judges, and claims of exhaustive correctness.

**Acceptance criteria**
1. A valid Markdown/TXT statement can be loaded and its normalized input hash recorded.
2. Each generated C++ artifact is compiled in a restricted runner; compile failures are surfaced with a useful error category and diagnostics.
3. The tool runs sample tests and bounded differential tests under configurable time/resource limits.
4. The brute-force input size is selected per problem and algorithmic complexity; `N <= 10` is an example profile, not a global rule.
5. Every generated input is independently parsed/validated before use. Invalid inputs are rejected and recorded.
6. Fixed generator artifact + configuration + seed + subtask + execution environment produces the same input.
7. Mismatches stop the batch and preserve the failing input, outputs, stderr, exit codes, and artifact hashes.
8. A report distinguishes passed tests, mismatch, invalid input, compile/runtime/timeout/resource errors, and `NEEDS_REVIEW`.
9. Export displays the report and 3–5 sample tests, requires explicit user approval, and includes a manifest with statuses and hashes.
10. No state or UI may label a finite test run as a proof of correctness.

### MVP-1 (P1): multi-user web

Indicative scope: React/TypeScript/Vite, FastAPI, PostgreSQL with SQLAlchemy/Alembic, authentication and project-level authorization, asynchronous jobs where needed, PDF/DOCX extraction/OCR, S3-compatible storage abstraction, review history and multi-problem workflow. Re-estimate after MVP-0.

### MVP-2 (P2): hardening and advanced workflows

Indicative scope: stronger sandbox isolation, audit/monitoring, advanced generators, special judges/multiple-valid-output checkers, and team workspace if justified. gVisor/Firecracker and Kubernetes are options to evaluate, not mandatory technologies.

## B. New functional requirements

### B1. Generator contract

- **FR-GEN-01 (P0):** A generator is a standalone C++17 program accepting `argv[1] = seed` and `argv[2] = subtask_id`; it writes one input to stdout and returns exit code 0 only on success.
- **FR-GEN-02 (P0):** The runner treats non-zero exit status, timeout, resource exhaustion, or empty/malformed output as generation failure.
- **FR-GEN-03 (P0):** The generator must be deterministic for the same source/binary, configuration, seed, subtask, and execution environment.
- **FR-GEN-04 (P0):** Generator self-assertions may be used but are not trusted as the sole validation.
- **FR-GEN-05 (P0):** A separate validator must parse generated input and independently verify syntax and constraints before the input is used for differential testing or export.
- **FR-GEN-06 (P0):** Record generator source hash, binary hash where available, version, seed, subtask, configuration hash, compiler/flags, and runner image digest where available.
- **FR-GEN-07 (P1):** Provide reusable templates for common structures only after the core contract is stable.
- **FR-GEN-08 (P1):** Support strategy labels such as `random_uniform`, `random_biased`, `edge_min`, `edge_max`, `all_equal`, `sorted_asc`, `sorted_desc`, `adversarial_<name>`, `structured_tree`, `structured_graph`, and `structured_string`; applicability is problem-specific.

### B2. Oracle, checker and uncertainty

- **FR-CHK-01 (P0):** The run must identify which implementation is treated as oracle and record its artifact hash.
- **FR-CHK-02 (P0):** Default comparison may use exact token comparison and whitespace normalization only when the problem's output semantics permit it.
- **FR-CHK-03 (P0):** A mismatch must be reported as disagreement; the system must not infer automatically which solution is wrong from mismatch alone.
- **FR-CHK-04 (P0):** If output uniqueness or comparison semantics are uncertain, mark the run `NEEDS_REVIEW` and do not describe it as verified.
- **FR-CHK-05 (P0):** The system must not rely solely on LLM analysis to guarantee that output is unique or that a checker is correct.
- **FR-CHK-06 (P1):** Support explicit checker selection/configuration per problem.
- **FR-CHK-07 (P1/P2):** Floating-point tolerance, user-supplied special judges, and multiple-valid-output checking require their own documented contracts, sandboxing and tests before being enabled.

### B3. Validation, review and export

- **FR-EXP-10 (P0):** Before export, show the validation report and its limitations.
- **FR-EXP-11 (P0):** Before export, show 3–5 representative input/output cases where available.
- **FR-EXP-12 (P0):** The user can reject a candidate and request a deliberate regeneration.
- **FR-EXP-13 (P0):** Export requires explicit user approval.
- **FR-EXP-14 (P0):** Approval records the reviewer action but does not turn `NEEDS_REVIEW` into verified status.
- **FR-EXP-15 (P0):** ZIP manifest includes artifact names and hashes, run status, generator/validator/checker metadata, seeds/configuration, compiler/runtime metadata where available, and known limitations.

### B4. Run states and error catalogue

Use stable states where applicable: `PENDING`, `RUNNING`, `PASSED_TESTS`, `MISMATCH_FOUND`, `INVALID_INPUT`, `COMPILE_ERROR`, `RUNTIME_ERROR`, `TIMEOUT`, `RESOURCE_LIMIT`, `NEEDS_REVIEW`, `APPROVED_FOR_EXPORT`, `EXPORTED`, `FAILED_INFRASTRUCTURE`.

Minimum error categories should include `INPUT_FORMAT_INVALID`, `CONSTRAINT_VALIDATION_FAILED`, `GENERATOR_EXIT_NONZERO`, `GENERATOR_TIMEOUT`, `COMPILE_FAILED`, `PROGRAM_EXIT_NONZERO`, `PROGRAM_TIMEOUT`, `MEMORY_LIMIT`, `OUTPUT_LIMIT`, `DIFFERENTIAL_MISMATCH`, `CHECKER_UNCERTAIN`, `LLM_TIMEOUT`, `LLM_RATE_LIMIT`, `LLM_BUDGET_EXCEEDED`, `EXPORT_FAILED`, and `INFRASTRUCTURE_ERROR`. Each user-facing error should explain what failed and a safe next step without claiming an unverified root cause.

### B5. Retry and idempotency

- **FR-JOB-09 (P0):** Each job type must declare retry eligibility, maximum retry count, backoff and idempotency inputs.
- **FR-JOB-10 (P0):** Duplicate submissions must be deduplicated where feasible using a key containing all result-affecting inputs.
- LLM solution generation: no automatic retry by default because retries may incur cost and produce different code; at most one deliberate user-triggered retry in MVP-0.
- Compile/run: retry only transient infrastructure failures, not deterministic compile errors, runtime errors or mismatches.
- Test generation: retain seed and artifact/config hashes; retry infrastructure failure only.
- Export: retry transient filesystem/storage failures only.
- Future document extraction: up to three transient retries with exponential backoff may be used after that feature exists.

### B6. Health and progress

- **FR-OPS-01 (P0):** Local CLI reports a clear success/failure exit code and preserves a run log.
- **FR-OPS-02 (P1):** Web API exposes separate liveness and readiness endpoints, for example `/api/v1/health/live` and `/api/v1/health/ready`.
- **FR-OPS-03 (P1):** `/api/v1/metrics` may be exposed only when metrics are implemented and access is appropriately controlled.
- **FR-OPS-04 (P0):** Progress is `null` when it cannot be meaningfully measured; otherwise it is an estimate from 0–100 and must not imply exact completion.
- **FR-OPS-05 (P0):** Logs include `run_id` or `job_id`, elapsed time, artifact identifiers/hashes where relevant, exit status and cleanup outcome. Do not log secrets.

## C. Non-functional requirements

### C1. Reproducibility

- **NFR-REP-01 (P0):** Each test run stores a reproducibility record.
- **NFR-REP-02 (P0):** The record includes run ID/timestamp, normalized problem/input hash, LLM provider/model identifier if available, prompt version/hash, parameters/seed if supported, token usage/cost/latency if reported, compiler version/flags, runner image digest, generator/validator versions and hashes, seed/subtask/config hash, oracle artifact ID/hash, checker configuration, test hashes, and final status.
- **NFR-REP-03 (P0):** Records must not contain API keys, credentials, or other secrets.
- **NFR-REP-04 (P0):** Reproduction claims are limited to what is actually pinned and recorded. Hosted LLM output may not be perfectly reproducible even with a seed.
- **NFR-REP-05 (P1):** Warn when an artifact depends on a runtime/tool version that is no longer available or has changed incompatibly.

### C2. Cost control

- **NFR-COST-01 (P0):** Log token usage and cost/latency when reported by the LLM provider, associated with the run/job.
- **NFR-COST-02 (P0):** Cache eligible LLM responses using a key that includes model/version, prompt hash, normalized input hash and all generation parameters that can affect output.
- **NFR-COST-03 (P0):** Apply bounded timeout and retry policies; do not automatically repeat paid solution-generation calls by default.
- **NFR-COST-04 (P0):** MVP-0 exposes a simple local usage/cost log or summary if provider usage data is available.
- **NFR-COST-05 (P1):** Per-user quotas, model selection and cost dashboard may be added with multi-user support.
- **NFR-COST-06 (P0):** If provider usage/cost is unavailable, represent it as unknown/null rather than inventing a precise value.

### C3. Sandbox and execution isolation

- **NFR-SEC-13 (P0):** Run untrusted generated/submitted C++ outside the API process in a disposable, non-root environment.
- **NFR-SEC-14 (P0):** Enforce wall-clock, CPU, memory/swap, PID, output-size and file-size limits; verify that the selected host/runtime actually applies the limits.
- **NFR-SEC-15 (P0):** Disable network access for untrusted code and avoid privileged containers, Docker socket mounts, unrestricted host mounts and secret propagation.
- **NFR-SEC-16 (P0):** Use a read-only base filesystem, per-job writable workspace, dropped capabilities, `no-new-privileges`, and seccomp where supported.
- **NFR-SEC-17 (P0):** Clean up workspace and processes after success, failure, timeout or cancellation.
- **NFR-SEC-18 (P0):** Document Docker as a defense-in-depth boundary, not a complete security guarantee; `--network=none` alone is insufficient to establish complete host isolation.
- **NFR-SEC-19 (P1):** Evaluate `nsjail` or `isolate` for web deployment. Evaluate gVisor/Firecracker only after threat-model review.

### C4. Performance and load targets

- **NFR-PERF-01:** Do not set unmeasured targets such as “10 concurrent users, 100 requests/s, 1 GB dataset” as accepted requirements without a workload model and benchmark. MVP-0 acceptance is functional and bounded local execution. Before MVP-1, define representative problem sizes, job mix, concurrency, latency percentiles, and resource limits, then benchmark and set measurable targets.
- **NFR-PERF-02 (P0):** Every compile/run/generation process has explicit time and output limits even before global throughput targets are known.

### C5. Logging and observability

- **NFR-OBS-01 (P0):** Logs are structured enough to correlate events by `run_id`/`job_id`.
- **NFR-OBS-02 (P1):** Expose metrics for queue depth, job duration, error rate, runner timeouts and LLM usage when a web/worker deployment exists.
- **NFR-OBS-03 (P1):** Centralized logging, dashboards, tracing and error tracking are phased in according to operational needs; they are not MVP-0 prerequisites.

## D. Data model and authorization clarifications

- **FR-AUTH-05 clarification (P1):** A child resource's access is checked through its parent project/problem relationship. Do not trust a child-supplied `user_id`; derive authorization from the parent and verify it on every operation.
- Use database foreign keys for ownership relationships. MVP-1 can use `projects.user_id` and child resources referencing their parent. If teams are implemented, introduce explicit `teams` and `team_members` tables and define membership/role rules. Do not mandate a polymorphic `owner_type + owner_id` pair for every table.
- UUIDv4 remains acceptable; UUIDv7 is optional pending library/database compatibility and a concrete need. ID format is not an MVP-0 blocker.
- Persist a reproducibility record as JSON where supported. PostgreSQL JSONB is appropriate in MVP-1; MVP-0 may use a JSON file or SQLite JSON/text field.

## E. Architectural and deployment notes

- MVP-0 may use CLI + local filesystem and need not include a database, frontend, event bus, queue or object store unless implementation evidence justifies them.
- MVP-1 may use React + TypeScript + Vite, FastAPI, PostgreSQL/SQLAlchemy/Alembic, Celery + Redis, and S3-compatible storage behind interfaces.
- Use direct function calls within a module and application-service interfaces across modules. Introduce a small in-process event mechanism only when real decoupling is needed; Kafka is not planned by default.
- MVP-0 logging can use Python's standard logging with run IDs. Prometheus, Grafana, Loki, Sentry and OpenTelemetry are later options, not initial blockers.
- Development/staging/production deployment choices must be documented when those environments are actually introduced. A single-host Compose deployment behind a reverse proxy and HTTPS can be a pragmatic MVP-1 starting point; Kubernetes is optional.

## F. Risk register

| Risk | Owner | Mitigation / acceptance guard |
|---|---|---|
| AI-generated solution is incorrect | Developer/operator | Compile, run samples, differential tests, review; do not claim proof |
| Oracle is incorrect or too slow | Developer/operator | Validate oracle assumptions and constrain brute-force tests per problem |
| Generator creates invalid tests | Developer/operator | Independent validator; reject invalid cases |
| Checker semantics are uncertain | Developer/operator | `NEEDS_REVIEW`; no verified export claim |
| Untrusted code escapes limits or harms host | Developer/operator | Disposable non-root sandbox, no secrets/network, resource controls, cleanup |
| LLM cost spikes or provider fails | Developer/operator | Usage log, complete cache key, bounded timeouts/retries and budget |
| Toolchain changes prevent reproduction | Developer/operator | Record versions/hashes and pin runner images where feasible |
| Scope creep | Project owner | MVP acceptance gates; defer non-core features |

## G. Glossary

- **Generator:** creates candidate problem inputs.
- **Validator:** independently parses and verifies input format and constraints.
- **Oracle:** reference implementation used to compute expected output.
- **Checker:** determines whether output satisfies problem-specific acceptance semantics.
- **Differential testing:** compares implementations on the same inputs.
- **Seed:** value controlling pseudorandom test generation.
- **Subtask:** constraint profile or test family.
- **Reproducibility record:** metadata to understand and repeat a run in a recorded environment.
- **Idempotency key:** identifier derived from all inputs that determine the intended operation.
- **`NEEDS_REVIEW`:** state indicating automated verification is insufficient or semantics are uncertain.

## H. Decisions and ADR sequencing

Before MVP-0, record concise decisions for: (1) LLM provider abstraction and initial model, (2) generator contract, (3) checker/oracle policy, (4) sandbox boundary, and (5) reproducibility/cost record. These can be short ADRs; they do not need a week-long process. Defer OCR, auth/session, object storage, team workspace, event bus, and full observability ADRs until their respective phase. A `docs/decisions/README.md` index should list each ADR, status, owner and phase.

## I. Change log

- **2026-10-11 — Review reconciliation:** added staged scope and acceptance gates; formal generator/validator/oracle/checker contracts; reproducibility and cost requirements; retry/idempotency; human review before export; run states/error catalogue; sandbox constraints; phased observability/deployment; corrected performance targets, authorization inheritance, and data-model assumptions.
