# Báo cáo môn học theo mẫu PTTK

Thư mục này là báo cáo nộp giảng viên, viết theo mẫu "Mẫu PTTK" của Học viện (yêu cầu của mẫu và mức độ đáp ứng: `docs/04-course-report.md`).

- **Ngôn ngữ:** tiếng Việt. Tên kỹ thuật giữ nguyên tiếng Anh, không dịch: tên thành phần kiến trúc (Inventory Service, Kitchen Service, Kafka, outbox…), tên CSDL, bảng, cột, topic, event, API, mã trạng thái (`DANG_GIU`, `CHO_NAU`…) và mã lý do (`INSUFFICIENT_INGREDIENTS`…).
- **Nguồn sự thật** vẫn là `docs/01`–`03` (tiếng Anh). Báo cáo trích từ đó; khi hai bên lệch nhau, sửa báo cáo.
- **Cập nhật cùng code:** xong mỗi bước trong mục 4 của `docs/03-implementation-plan.md` thì cập nhật luôn các mục báo cáo của bước đó (bảng chức năng, thẻ use case và biểu đồ hoạt động, CSDL, kịch bản và kết quả kiểm thử), trong cùng commit.

## Cấu trúc

| File | Mục của mẫu |
|---|---|
| `00-bia.md` | Bìa |
| `01-khao-sat.md` | Phần I. Nghiên cứu, khảo sát yêu cầu |
| `02-phan-tich-thiet-ke.md` | Phần II. Mô hình HLD; I. Danh sách chức năng; II. Thiết kế chức năng; III. Thiết kế CSDL (mục 2.2 lấy từ `generated/csdl.md`) |
| `03-xay-dung.md` | Phần III. Công nghệ, giao diện |
| `04-kiem-thu.md` | Phần IV. Kịch bản kiểm thử (lấy từ `generated/kiem-thu.md`), mô hình kiểm thử phân tán, công cụ, môi trường, kết quả |
| `generated/` | Sinh tự động, không sửa tay (xem dưới) |

Sơ đồ viết bằng Mermaid ngay trong Markdown: VS Code và GitHub hiển thị trực tiếp; khi xuất Word, `build.sh` vẽ chúng thành ảnh.

## Sinh lại phần tự động

Cần cluster đang chạy (`docker compose --profile full up -d --wait`):

```bash
docker compose exec -T tools python scripts/report_schema.py > report/generated/csdl.md
docker compose exec -T tools sh -c 'pytest -p no:cacheprovider --junitxml=/tmp/junit.xml; \
  python scripts/report_tests.py /tmp/junit.xml > /report/generated/kiem-thu.md'
```

## Xuất file Word

```bash
report/build.sh        # → report/build/bao-cao.docx (không commit)
```

Script ghép các file theo thứ tự, thay các dòng `<!-- include: … -->` bằng nội dung file được chỉ tới, vẽ sơ đồ Mermaid thành PNG bằng `minlag/mermaid-cli`, rồi xuất `.docx` bằng `pandoc/core`, đều chạy trong Docker. Định dạng trang theo mẫu (font, lề) sẽ làm bằng một `reference.docx` ở bước 8.

## Trạng thái các mục

| Mục | Trạng thái |
|---|---|
| Bìa | Khung; chờ @Naul điền thông tin |
| Phần I | Chưa viết; chờ quyết định ai viết |
| Mô hình HLD | Có |
| Danh sách chức năng | Có đủ các chức năng của đợt 1 và đợt 2 |
| Thiết kế chức năng | Có cho các giao dịch đã làm: Kho, Bếp và chi nhánh (19 giao dịch); cảnh báo của Kho, Bếp và báo cáo ở bước 7 |
| Thiết kế CSDL | Có: danh sách CSDL, sơ đồ tổng quát, danh sách bảng; sơ đồ ER và bảng chi tiết sinh từ CSDL đang chạy |
| Công nghệ | Có |
| Giao diện | Có màn Chi nhánh, Bếp, Kho, Giám sát và trang Demo; màn Quản lý ở bước 7, ảnh chụp ở bước 8 |
| Kịch bản kiểm thử | Có; trạng thái sinh từ lần chạy test gần nhất |
| Mô hình kiểm thử phân tán | Có, gồm cắt mạng chi nhánh thật (kịch bản 10, 36); bổ sung kịch bản 55 và hai instance thật ở bước 7 |
| Kiểm thử hiệu năng | Chờ bước 7 (JMeter) |
| Môi trường, công cụ | Có; bổ sung JMeter ở bước 7 |
