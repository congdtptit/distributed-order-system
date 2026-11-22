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

Màn hình chỉ hiển thị điều các dịch vụ trả về và không tự quyết định trạng thái nào. Mọi màn hình làm mới dữ liệu 2 giây một lần trong lúc đang mở. Khi một dịch vụ không trả lời, màn hình hiện băng cảnh báo và giữ dữ liệu cũ. Ảnh chụp các màn được thêm ở bước 8.

### 1. Màn hình Chi nhánh (POS và Online)

Đường dẫn `/branch/POS01`, `/branch/POS02`, `/branch/ONLINE`; người dùng là thu ngân hoặc khách hàng online. Màn hình gồm:

- **Thanh trên:** trạng thái kết nối Kafka của chi nhánh (kết quả lần thăm dò gần nhất) và số mục chờ gửi, lấy từ `GET /monitor`; nút chọn chi nhánh.
- **Cảnh báo Luồng D:** đơn chờ Kho quá N phút kèm nút Yêu cầu hủy; đơn còn trong hàng chờ sắp quá hạn X giờ; đơn đang yêu cầu hủy kèm thời gian đã chờ; tin trạng thái không đọc được.
- **Tạo đơn:** danh mục món của chi nhánh (`GET /dishes`, dùng được khi mất mạng), nhập số lượng, bấm Tạo đơn. Đơn hiện ở Chờ kho cho tới khi có tin trạng thái.
- **Danh sách đơn:** mã đơn rút gọn (bấm để chép mã đầy đủ), giờ tạo, món, trạng thái dạng nhãn có màu và biểu tượng, cờ yêu cầu hủy, lý do, thông báo "Không hủy được: bếp đã bắt đầu nấu", tình trạng gửi theo BR5 ("Chưa gửi, bếp chưa nhận", "Đang gửi, chưa biết bếp đã nhận chưa"), và nút Hủy đơn. Đơn đã kết thúc hoặc đang có yêu cầu hủy thì không có nút này.
- **Hộp thoại hủy:** bắt buộc chọn lý do thuộc nhóm khách hủy, kèm lời giải thích: đơn chưa gửi đi thì hủy ngay, đơn đã gửi thì Bếp quyết định. Kết quả 200 báo đã hủy tại chi nhánh; 202 báo đã gửi yêu cầu tới Bếp và chưa chắc hủy được; 409 báo đơn vừa đổi trạng thái rồi tải lại.

### 2. Màn hình Bếp

Đường dẫn `/kitchen`; người dùng là nhân viên bếp, trên máy tính bảng (1024×768) hoặc màn hình treo tường (1920×1080). Màn hình gồm:

- **Cảnh báo của Bếp** (`GET /alerts`), đặt trên cùng: yêu cầu hủy từ chi nhánh không phải chi nhánh gốc (`HUY_SAI_CHI_NHANH`, kèm chi nhánh gốc và các chi nhánh bị bỏ qua, để kiểm tra cấu hình chi nhánh gửi) và đơn cần kiểm tra (`CAN_KIEM_TRA`).
- **Hai cột Chờ nấu và Đang nấu** (`GET /tickets`). Phiếu đã kết thúc không hiện ở đây. Mỗi phiếu có mã đơn, chi nhánh gốc, giờ đặt, món, nguyên liệu đã giữ kèm lượng. Phiếu Chờ nấu có nguyên liệu đang chờ kiểm kho thì hiện cảnh báo đỏ nêu tên nguyên liệu (Luồng A, bước 6); đây chỉ là cảnh báo, hệ thống không tự hủy phiếu.
- **Nút theo trạng thái:** phiếu Chờ nấu có Bắt đầu nấu và Từ chối; phiếu Đang nấu chỉ có Hoàn tất. Nút cao ít nhất 44px, cách nhau 8px, để bấm nhanh khi đang đeo găng. Trả 409 nghĩa là phiếu vừa đổi trạng thái (thua trong tranh chấp với một yêu cầu hủy, BR7): màn hình báo ngắn rồi tải lại, không coi là lỗi.
- **Hộp thoại từ chối:** bắt buộc chọn lý do thuộc nhóm Bếp từ chối; với lý do Nguyên liệu hỏng phải chọn ít nhất một nguyên liệu trong danh sách đã giữ của phiếu. Bếp kiểm tra lại và trả 400 nếu không nhận, lỗi hiện ngay trong hộp thoại.

> TODO(bước 6b): các màn Kho, Giám sát, trang Demo; màn Quản lý ở bước 7.
