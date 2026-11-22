# Báo cáo Phân tích, Thiết kế và Xây dựng Hệ thống (v1)

Tài liệu báo cáo hoàn chỉnh cho **Đề tài 4: Hệ thống đặt hàng tại quầy và online hợp nhất**, biên soạn theo cấu trúc bốn phần của học phần Phát triển ứng dụng phân tán (`INT1498-20261-01`).

## Cấu trúc tài liệu

| Tệp Markdown | Nội dung chính |
|---|---|
| `00-bia.md` | Trang bìa chuẩn PTIT–RIPT, Bảng phân công nhiệm vụ Nhóm 10, Mục lục tự động, Danh mục từ viết tắt, Quy ước trạng thái và Lời mở đầu |
| `01-khao-sat.md` | Phần I: Hiện trạng đơn vị đa kênh, các điểm nghẽn phân tán, đối chiếu giải pháp thị trường và mục tiêu hệ thống |
| `02-phan-tich-thiet-ke.md` | Phần II: Mô hình kiến trúc tổng quan (`HLD`), Use Case tổng quát, danh sách 16 giao dịch qua 4 module, 16 biểu đồ hoạt động và thiết kế chi tiết 24 bảng trên 4 lược đồ PostgreSQL kèm `5` sơ đồ ERD |
| `03-xay-dung.md` | Phần III: Ngăn xếp công nghệ, danh mục REST API, 5 màn hình giao diện vận hành thực tế và cơ chế cài đặt xử lý phân tán cốt lõi |
| `04-kiem-thu.md` | Phần IV: Kịch bản kiểm thử hợp nhất và chịu lỗi phân tán, kết quả kiểm thử tự động (`273` Pytest + `85` Vitest), đo tải `Apache JMeter 5.6.3` và kết luận |

## Sinh sơ đồ và chụp ảnh màn hình

Toàn bộ `23` sơ đồ phân tích thiết kế và `5` ảnh chụp giao diện trong `report/images/` được kết xuất ở độ phân giải `@2x` bằng Chromium (không dùng Mermaid):

```bash
node report/scripts/render_diagrams.mjs
node report/scripts/capture_ui.mjs
```

## Đóng gói tài liệu Word (`bao-cao.docx`)

Chạy tập lệnh dựng Word để hợp nhất các chương qua Pandoc, áp dụng bộ quy chuẩn kiểu dáng PTIT–RIPT (`polish_docx.ps1`: chèn khung bìa, logo đôi, căn chỉnh bảng theo tỷ lệ nội dung, chống tách dòng qua trang, khung thuật toán) và tự động cập nhật Mục lục trong Microsoft Word:

```bash
bash report/build.sh
```

Tệp kết quả được xuất tại `report/build/bao-cao.docx`.
