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

Sơ đồ viết bằng Mermaid ngay trong Markdown: VS Code và GitHub hiển thị trực tiếp; khi xuất Word, `build.sh` vẽ chúng thành ảnh. Riêng sơ đồ HLD nằm ở `diagrams/hld.mmd` (dàn trang ELK) và được `build.sh` vẽ thành `images/hld.png` trước. Ảnh chụp màn hình nằm ở `images/`, chụp từ hệ thống đang chạy sau khi dọn cụm và chạy `docker compose exec -T tools python scripts/demo_data.py`.

## Sinh lại phần tự động

Cần cluster đang chạy (`docker compose --profile full up -d --wait`):

```bash
docker compose exec -T tools python scripts/report_schema.py > report/generated/csdl.md
docker compose exec -T tools sh -c 'pytest -p no:cacheprovider --junitxml=/tmp/junit.xml; \
  python scripts/report_tests.py /tmp/junit.xml > /report/generated/kiem-thu.md'
bin/perf               # kiểm thử hiệu năng → perf/results/ và report/generated/hieu-nang.md
```

## Xuất file Word

```bash
report/build.sh        # → report/build/bao-cao.docx (không commit)
```

Script vẽ các sơ đồ trong `diagrams/` vào `images/`, ghép các file theo thứ tự, thay các dòng `<!-- include: … -->` bằng nội dung file được chỉ tới, tách từng sơ đồ Mermaid ra và vẽ mỗi sơ đồ một lần bằng `minlag/mermaid-cli` (vẽ chung một lần thì trình duyệt của công cụ thỉnh thoảng bị treo), rồi xuất `.docx` bằng `pandoc/core`, đều chạy trong Docker. Bộ lọc `fit-images.lua` giới hạn sơ đồ quá dài ở 21 cm để không bị cắt cuối trang. Định dạng trang theo mẫu (font, lề) cần một `reference.docx` lấy từ file mẫu của giảng viên.

## Trạng thái các mục

| Mục | Trạng thái |
|---|---|
| Bìa | Khung; chờ @Naul điền thông tin |
| Phần I | Chưa viết; chờ quyết định ai viết |
| Mô hình HLD | Có |
| Danh sách chức năng | Có đủ các chức năng của đợt 1 và đợt 2 |
| Thiết kế chức năng | Có cho mọi giao dịch đợt 1: Kho, Bếp, chi nhánh và báo cáo quản lý (24 giao dịch); tình trạng món ở đợt 2 |
| Thiết kế CSDL | Có: danh sách CSDL, sơ đồ tổng quát, danh sách bảng; sơ đồ ER và bảng chi tiết sinh từ CSDL đang chạy |
| Công nghệ | Có |
| Giao diện | Có đủ sáu màn: Chi nhánh, Bếp, Kho, Giám sát, Quản lý và trang Demo, mỗi màn có ảnh chụp (`images/`, dữ liệu từ `backend/scripts/demo_data.py`) |
| Kịch bản kiểm thử | Có; trạng thái sinh từ lần chạy test gần nhất |
| Mô hình kiểm thử phân tán | Có, gồm cắt mạng chi nhánh thật (kịch bản 10, 36), cắt nhân bản về trung tâm (kịch bản 55), hai instance Inventory thật (kịch bản 42) và các kịch bản demo 1, 3, 4 chạy trên cụm thật |
| Kiểm thử hiệu năng | Có: JMeter 5.6.3, 250 người dùng đồng thời cho 6 chức năng, tài nguyên từ `docker stats`, thời gian tạo đơn tới Đã giữ (`generated/hieu-nang.md`) |
| Môi trường, công cụ | Có |
