# PHẦN III. XÂY DỰNG, PHÁT TRIỂN HỆ THỐNG

## I. MÔ TẢ CÔNG NGHỆ SỬ DỤNG

- **Kiến trúc hệ thống:** microservices hướng sự kiện, toàn bộ là phần mềm nguồn mở. Các dịch vụ chỉ trao đổi qua Kafka theo mô hình at-least-once; mỗi dịch vụ có CSDL riêng; tin gửi đi qua outbox; consumer chống trùng bằng `processed_events`. Báo cáo quản lý đọc Central Order Replica được nhân bản bằng PostgreSQL logical replication. Toàn bộ hệ thống (21 container) chạy bằng Docker Compose.
- **Nền tảng phát triển back-end:** Python 3.12, FastAPI và Uvicorn cho API; psycopg 3 với SQL viết tay, không dùng ORM, vì các quy tắc tranh chấp dựa trực tiếp vào `SELECT ... FOR UPDATE`, `ON CONFLICT`, `SAVEPOINT` và UPDATE có điều kiện; `confluent-kafka` với vòng lặp consumer tự viết theo 5 bước (ghi `processed_events`, áp dụng bảng trạng thái, ghi outbox, commit DB, rồi mới commit offset).
- **Message broker:** Apache Kafka 4.3.2, chế độ KRaft, 3 broker; mọi topic có 3 bản sao, `min.insync.replicas=2`; producer dùng `acks=all` và `enable.idempotence=true`.
- **Hệ quản trị cơ sở dữ liệu:** PostgreSQL 16.14, mỗi CSDL một container; các CSDL chi nhánh bật `wal_level=logical` để nhân bản về Central Order Replica.
- **Nền tảng phát triển web application:** TypeScript 5.9, React 19 với Vite, React Router, Mantine (bộ component giao diện), TanStack Query (làm mới trạng thái định kỳ); kiểu dữ liệu API sinh từ tài liệu OpenAPI của từng dịch vụ.
- **Nền tảng phát triển mobile application:** không có. Kênh Online là một màn hình web dùng chung luồng với POS.
- **Công cụ chất lượng mã nguồn:** Ruff, Pyright (chế độ strict) cho Python; Biome, `tsc` cho TypeScript; GitHub Actions chạy kiểm tra tự động.

## II. MÔ TẢ GIAO DIỆN HỆ THỐNG

> TODO(bước 6b): mỗi màn hình một mục, kèm ảnh chụp từ skill `/screen`: Đặt món (POS, Online), Bếp, Kho, Giám sát, Quản lý, trang Demo.
