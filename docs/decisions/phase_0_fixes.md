# PTG Phase 0 Hardening Plan (Cập nhật từ phản biện)

## P0 — An toàn & Tính đúng đắn (Bắt buộc trước Phase 1)

- [ ] **SANDBOX-01 (Sửa):** Tách biệt compile và execute. 
  - Compile: mount `rw` thư mục chứa source.
  - Execute: mount `ro` thư mục chứa binary + input.
  - Nghiệm thu: Code cố tình ghi đè file phải bị lỗi `Permission Denied`.
- [ ] **SANDBOX-03 & DIFF-02 (Sửa):** Quản lý Timeout và Orphaned Container.
  - Bọc mọi lệnh Docker bằng `subprocess.run(timeout=...)`.
  - Bắt tín hiệu `SIGINT` (Ctrl+C) để gọi `docker kill <container_id>`.
  - Nghiệm thu: Không còn container nào ở trạng thái `Up` sau khi chạy xong test suite (kể cả khi test fail).
- [ ] **SANDBOX-02 (Sửa tiêu chí):** Fork Bomb & OOM.
  - Không check exit code 137 đơn thuần. Dùng `docker inspect` để xem `OOMKilled` hoặc log lỗi `Resource temporarily unavailable` (fork bomb).
  - Nghiệm thu: Phân loại đúng `RESOURCE_LIMIT` hoặc `RUNTIME_ERROR`.
- [ ] **GEN-01/02 (Sửa):** Đặc tả PRNG & Test Vector.
  - Đóng băng thuật toán SplitMix64 trong prompt.
  - Viết test: Seed=42, Subtask=1 phải ra đúng chuỗi bit đã biết.
  - Nghiệm thu: Kết quả giống nhau 100% trên 2 môi trường compile khác nhau.

## P1 — Độ tin cậy của đầu ra (Nên làm trước Phase 1)

- [ ] **PKG-01 (Sửa):** Layout Themis.
  - Sửa code xuất ZIP thành `tests/Test01/Test01.INP`.
  - Viết Integration Test: Giải nén file ZIP và assert lại đường dẫn.
- [ ] **DIFF-01 (Sửa):** Normalization output.
  - Chuyển logic trim whitespace từ Comparator sang Packaging Engine.
  - Nghiệm thu: Comparator vẫn báo Mismatch nếu 1 bên in `1 2 3` và bên kia in `1 2 3 ` (có dấu cách cuối).
- [ ] **GEN-03 (Bổ sung):** Negative Test cho Generator Contract.
  - Test truyền thiếu argv, sai argv. Test generator chạy quá thời gian (timeout).

## P2 — Tài liệu (Làm sau)

- [ ] **DOC-01 (Sửa):** Tránh trùng lặp ADR. Tạo `ADR-007-phase0-lessons-learned.md` (sau khi check lại index ADR thực tế).