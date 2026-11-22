# Kế hoạch và Dàn bài chi tiết Báo cáo PTTK Hệ thống (v1)

Tài liệu này là khung thống nhất trước khi biên tập từng phần trong `report/` trên nhánh `report/v1`, bám sát mẫu báo cáo môn học và ba yêu cầu cốt lõi của **Đề tài 4 — Hệ thống đặt hàng tại quầy và online hợp nhất**.

---

## 1. Thông tin hành chính & Quy chuẩn biên tập

| Hạng mục | Thông tin chốt |
|---|---|
| **Đơn vị đào tạo** | Học viện Công nghệ Bưu chính Viễn thông — Viện Khoa học Kỹ thuật Bưu điện |
| **Học phần** | Phát triển ứng dụng phân tán (`INT1498-20261-01`) |
| **Giảng viên hướng dẫn** | ThS. Đặng Anh Tuấn |
| **Đề tài (Số 4)** | Hệ thống đặt hàng tại quầy và online hợp nhất |
| **Nhóm thực hiện** | Nhóm 10 |
| **Thành viên** | Nguyễn Xuân Bắc (`B23DCCC016`), Đặng Thành Công (`B23DCCC024`), Nguyễn Trung Dân (`B23DCCC028`), Phạm Xuân Kỳ (`B23DCCC092`), Nguyễn Đức Thành (`B23DCCC152`) |

### Quy ước trình bày áp dụng cho toàn bộ `report/`

1. **Văn phong và chống văn AI:** Tuân thủ `.claude/skills/vietnamese-tech-report-writing/SKILL.md`: văn xuôi kỹ thuật khách quan, giữ nguyên tên thành phần/DB/bảng/cột/topic/event/API và mã trạng thái bằng tiếng Anh hoặc dạng định danh không dấu (`DANG_GIU`, `CHO_NAU`...), không dùng gạch ngang dài `—` chêm câu, không lạm dụng danh sách gạch đầu dòng in đậm.
2. **Nguyên tắc thuyết phục (không tự khai điểm yếu):** Chỉ trình bày giải pháp kỹ thuật, cơ chế hoạt động, kiến trúc đã xây dựng và kiểm chứng được; không đưa các mục "hạn chế/thiếu sót" ngoài phạm vi mẫu yêu cầu, không đưa nhật ký sửa lỗi hay thông số chưa tối ưu vào báo cáo.
3. **Sơ đồ và hình ảnh (không dùng Mermaid):** Toàn bộ sơ đồ (quy trình nghiệp vụ, HLD, Use Case, Biểu đồ hoạt động, Sơ đồ CSDL tổng quát, Mô hình kiểm thử phân tán) được thiết kế bằng HTML/SVG xuất ra PNG độ phân giải cao (cùng phong cách sạch, rõ của báo cáo mẫu hệ thống tuyển dụng). Các ảnh chụp giao diện ở Phần III chụp mới hoàn toàn trên phiên bản UI mới.
4. **Đánh số đồng bộ:** Đánh số đề mục thống nhất theo `1.1`, `2.1`, `3.1`, `4.1` bên dưới các `PHẦN I–IV` của mẫu thầy. Chú thích bảng đặt **phía trên** (`*Bảng X.Y. ...*`); chú thích hình đặt **phía dưới** (`*Hình X.Y. ...*`); mọi bảng và hình đều có câu dẫn trong văn bản.

---

## 2. Dàn bài chi tiết theo từng tệp

### Tệp `00-bia.md` — Trang bìa, Phân công và Danh mục

- **Trang bìa:** Khẩu hiệu Học viện & Viện Khoa học Kỹ thuật Bưu điện, tên tài liệu *Tài liệu Phân tích Thiết kế Phần mềm — Hệ thống đặt hàng tại quầy và online hợp nhất*, thông tin học phần `INT1498-20261-01`, GVHD `ThS. Đặng Anh Tuấn`, Nhóm 10 + bảng danh sách 5 sinh viên, Hà Nội – 2026. Ngắt trang bằng `<!--PAGEBREAK-->`.
- **Bảng phân công nhiệm vụ (tùy chọn bổ sung gọn):** Bảng tóm tắt vai trò từng thành viên trong thiết kế kiến trúc, phát triển dịch vụ, giao diện và kiểm thử, theo sau bởi `<!--PAGEBREAK-->`.
- **Mục lục tự động** (Pandoc `--toc`) và **Danh mục từ viết tắt / ký hiệu nghiệp vụ** (`POS`, `KDS`, `HLD`, `WAL`, `DLQ`, `KRaft`, bảng mã trạng thái đơn/phiếu/kho), kết thúc bằng `<!--PAGEBREAK-->`.

---

### Tệp `01-khao-sat.md` — PHẦN I. NGHIÊN CỨU, KHẢO SÁT YÊU CẦU

- **I. HIỆN TRẠNG ĐƠN VỊ**
  - **1.1. Bối cảnh vận hành đa kênh của chuỗi nhà hàng:** Bài toán giả định tổng quát một chuỗi ẩm thực vận hành song song các điểm bán tại quầy (`POS01`, `POS02`) và kênh đặt món trực tuyến (`Online`), sử dụng chung một Bếp trung tâm và một Kho nguyên liệu tập trung.
  - **1.2. Quy trình nghiệp vụ tổng quát và các điểm nghẽn phân tán:** Mô tả 5 vấn đề kỹ thuật cốt lõi phát sinh khi tách kênh nhận đơn khỏi Bếp và Kho trung tâm (mất kết nối tại quầy, hủy đơn song song lúc Bếp chuẩn bị nấu, tranh chấp nguyên liệu dùng chung, trùng lặp/sai thứ tự thông điệp mạng, độ trễ số liệu quản lý). Kèm *Hình 1.1. Sơ đồ bài toán và các điểm nghẽn trong vận hành chuỗi đặt món đa kênh* (PNG vẽ riêng).
- **II. HIỆN TRẠNG THỊ TRƯỜNG VỀ GIẢI PHÁP TRONG VÀ NGOÀI NƯỚC** *(giữ gọn ~1 trang A4)*
  - **2.1. Tổng quan các giải pháp hiện có:** Phân tích súc tích nhóm giải pháp trong nước (`KiotViet`, `Sapo FnB`, `MISA CukCuk`, `iPOS`) và ngoài nước (`Toast`, `Square for Restaurants`, `Lightspeed Restaurant`), kiểm chứng lại nguồn trích dẫn thực tế.
  - **2.2. Đối chiếu theo yêu cầu chuỗi bếp/kho trung tâm:** *Bảng 1.1. So sánh các giải pháp thị trường theo tiêu chí bài toán chuỗi đa kênh* (bán khi mất mạng, điều phối bếp/kho dùng chung qua mạng, xử lý hủy đơn bất đồng bộ, tổng hợp dữ liệu gần thời gian thực).
- **III. KẾT LUẬN**
  - Tổng hợp ưu điểm của giải pháp thương mại sẵn có và các khoảng trống chưa đáp ứng mô hình nhiều nguồn đặt hàng hợp nhất về một Bếp/Kho trung tâm, làm cơ sở xác lập tính cần thiết và 3 mục tiêu trọng tâm của đề tài (hai kênh phát sinh đơn độc lập, dịch vụ tổng hợp gần thời gian thực, kiểm soát xung đột tài nguyên).
- **Tài liệu tham khảo Phần I:** Danh mục nguồn đã kiểm tra tính hợp lệ.

---

### Tệp `02-phan-tich-thiet-ke.md` — PHẦN II. NGHIÊN CỨU, PHÂN TÍCH THIẾT KẾ HỆ THỐNG

- **I. MÔ HÌNH KIẾN TRÚC TỔNG QUAN (HLD)**
  - **1.1. Kiến trúc tổng thể và nguyên tắc giao tiếp bất đồng bộ:** Giải thích vai trò 2 nhóm tiến trình phát sinh đơn độc lập (`Local Order Service` tại `POS01/POS02` và `Online Order Service` cho kênh Online), cụm xử lý trung tâm (`Inventory Service × 2`, `Kitchen Service`), lớp truyền thông `Apache Kafka 3 broker` (Outbox + chống trùng `processed_events`), và luồng tổng hợp gần thời gian thực (`PostgreSQL Logical Replication` sang `Central Order Replica` cho `Order Query Service`).
  - *Hình 2.1. Mô hình kiến trúc tổng quan (HLD) hệ thống đặt hàng tại quầy và online hợp nhất* (PNG vẽ sạch, phân tầng rõ kênh nguồn – Kafka/Replication – dịch vụ trung tâm – giao diện).
  - *Bảng 2.1. Thành phần dịch vụ và kho dữ liệu trong kiến trúc hệ thống*.
  - *Bảng 2.2. Quy hoạch các topic Kafka và thông điệp trao đổi liên dịch vụ*.
- **II. DANH SÁCH CHỨC NĂNG PHẦN MỀM**
  - **2.1. Sơ đồ Use Case tổng quát:** Giới thiệu 5 nhóm tác nhân (Thu ngân quầy, Khách hàng Online, Nhân viên Kho, Nhân viên Bếp, Quản lý/Giám sát vận hành) và ranh giới hệ thống. Kèm *Hình 2.2. Sơ đồ Use Case tổng quát hệ thống đặt hàng đa kênh hợp nhất* (PNG chuẩn UML).
  - **2.2. Bảng danh sách chức năng phần mềm:** *Bảng 2.3. Danh sách chức năng phần mềm theo module, use case và giao dịch* (đúng 5 cột của mẫu thầy), tổ chức gọn thành **4 module – 14 giao dịch trọng tâm** (kết nối chặt chẽ thao tác người dùng và xử lý phân tán cốt lõi, bỏ phân mảnh trùng lặp):
    1. *Module 1: Tiếp nhận và theo dõi đơn hàng đa kênh (`POS` & `Online`)* — (1) Xem thực đơn kèm trạng thái món theo thời gian thực; (2) Tạo đơn đặt món tại quầy/Online; (3) Yêu cầu hủy đơn đặt món; (4) Theo dõi danh sách đơn, trạng thái gửi và cảnh báo quá hạn.
    2. *Module 2: Quản lý kho và giữ nguyên liệu trung tâm (`Inventory`)* — (5) Kiểm tra và giữ nguyên liệu cho đơn hàng hợp nhất; (6) Hoàn trả hoặc ghi nhận hao hụt nguyên liệu theo lệnh Bếp; (7) Nhập kho nguyên liệu; (8) Xác nhận kiểm kho xong; (9) Cập nhật và công bố trạng thái món ăn (`CON`/`HET`/`AN`).
    3. *Module 3: Điều phối chế biến tại Bếp trung tâm (`Kitchen`)* — (10) Tiếp nhận phiếu bếp hợp nhất từ các kênh và đồng bộ lệnh hủy; (11) Bắt đầu nấu (phân xử tranh chấp với yêu cầu hủy); (12) Từ chối phiếu chế biến (bao gồm báo hỏng nguyên liệu); (13) Hoàn tất chế biến món.
    4. *Module 4: Tổng hợp dữ liệu trung tâm và giám sát vận hành (`Query & Monitor`)* — (14) Xem báo cáo tổng hợp đơn hàng toàn chuỗi gần thời gian thực kèm mốc dữ liệu; (15) Giám sát trạng thái kết nối dịch vụ, độ trễ hàng chờ và cảnh báo hệ thống.
- **III. THIẾT KẾ CHỨC NĂNG PHẦN MỀM**
  - Trình bày lần lượt theo cấu trúc `Module → Use Case → Giao dịch` đúng chuẩn các trường của mẫu thầy (*Tên Usecase, Mô tả Usecase, Tác nhân chính, Tác nhân phụ, Điều kiện bắt đầu, Điều kiện kết thúc, Trình tự các sự kiện, Yêu cầu phi chức năng, Biểu đồ hoạt động*).
  - **Thiết kế hình ảnh (không dùng Mermaid):** Vẽ **10–12 Biểu đồ hoạt động (Activity Diagram) bằng HTML/SVG → PNG** cho các giao dịch nghiệp vụ và xử lý phân tán cốt lõi (*Hình 2.3* trở đi), làm rõ các điểm chốt chặn phân tán: Outbox khi mất mạng, khóa dòng nguyên liệu chống xung đột giữa `Inventory × 2`, tranh chấp `Hủy đơn vs. Bắt đầu nấu`, phản hồi trạng thái theo thứ hạng, và đọc báo cáo trên bản sao `Central Order Replica`. Các giao dịch tra cứu/cảnh báo tương đồng có thể gom gọn dùng chung mô hình tra cứu nhất quán.
- **IV. THIẾT KẾ CƠ SỞ DỮ LIỆU**
  - **4.1. Các cơ sở dữ liệu của hệ thống:** *Bảng 2.x. Danh mục các cơ sở dữ liệu trong kiến trúc Database-per-Service* (`Inventory DB`, `Kitchen DB`, 3 `Branch DB` cho `POS01`, `POS02`, `ONLINE`, và `Central Order Replica`).
  - **4.2. Thiết kế chi tiết cơ sở dữ liệu:**
    - *Hình 2.x. Sơ đồ cơ sở dữ liệu tổng quát và luồng đồng bộ liên dịch vụ* (PNG vẽ sạch, thể hiện rõ khóa định danh `order_id`, truyền thông Kafka và Logical Replication).
    - *4.2.1. Danh mục các bảng trong cơ sở dữ liệu:* *Bảng 2.x* liệt kê đủ 24 bảng thuộc 4 lược đồ DB.
    - *4.2.2. Thiết kế chi tiết các bảng:* Cập nhật [report_schema.py](file:///d:/distributed-order-system-1/backend/scripts/report_schema.py) để xuất bảng gọn cột (`NO`/`YES`, rút gọn điều kiện `CHECK`, đánh số bảng tuần tự) kèm sơ đồ ER từng DB bằng PNG rõ nét thay cho Mermaid `erDiagram`.

---

### Tệp `03-xay-dung.md` — PHẦN III. XÂY DỰNG, PHÁT TRIỂN HỆ THỐNG

- **I. MÔ TẢ CÔNG NGHỆ SỬ DỤNG**
  - Trình bày 5 nhóm đúng theo mẫu thầy (dạng bảng hoặc đoạn văn ngắn gọn kết hợp bảng *Bảng 3.1. Công nghệ và nền tảng xây dựng hệ thống*):
    - Kiến trúc hệ thống (Microservices hướng sự kiện, nguồn mở, `Docker Compose`)
    - Nền tảng Back-end (`Python 3.12`, `FastAPI`, `Uvicorn`, `psycopg 3`, `confluent-kafka`) & Message Broker (`Apache Kafka 4.3.2 KRaft`)
    - Hệ quản trị cơ sở dữ liệu (`PostgreSQL 16.14`, Logical Replication)
    - Nền tảng Web Application (theo **frontend mới**: `TypeScript`, `React 19`, `Vite`, `React Router`, `Tailwind CSS 4`, `Radix UI`, `TanStack Query 5`, `Lucide React`)
    - Nền tảng Mobile Application (kiến trúc giao diện web đáp ứng cho kênh đặt món trực tuyến trên thiết bị di động, dùng chung API với điểm bán)
- **II. MÔ TẢ GIAO DIỆN HỆ THỐNG**
  - Giới thiệu chung bố cục hệ thống điều hành và cơ chế cập nhật trạng thái từ dịch vụ API.
  - Mô tả chi tiết **5 màn hình mới** kèm ảnh chụp mới (chụp sau khi hoàn thiện frontend mới):
    1. Màn hình Chi nhánh Quầy & Online (`/branch/POS01`, `/branch/ONLINE`) — *Hình 3.1*
    2. Màn hình Bếp trung tâm (`/kitchen`) — *Hình 3.2*
    3. Màn hình Kho nguyên liệu (`/inventory`) — *Hình 3.3*
    4. Màn hình Giám sát vận hành (`/monitor`) — *Hình 3.4*
    5. Màn hình Quản lý báo cáo tổng hợp (`/reports`) — *Hình 3.5*

---

### Tệp `04-kiem-thu.md` — PHẦN IV. THỬ NGHIỆM VÀ ĐÁNH GIÁ HỆ THỐNG

- **I. KỊCH BẢN KIỂM THỬ**
  - Trình bày gọn **~10 ca kiểm thử tiêu biểu** (không đổ 44 test log và không phải kịch bản demo), chia thành 2 bảng nhỏ đúng trọng tâm Đề tài 4:
    1. *Bảng 4.1. Kịch bản kiểm thử chức năng hợp nhất đa kênh* (~4 ca: tạo đơn từ POS và Online cùng lúc, hủy đơn hợp lệ khi chưa nấu, cập nhật trạng thái món `CON`/`HET`, tổng hợp số liệu trên Central Replica).
    2. *Bảng 4.2. Kịch bản kiểm thử tính phân tán, xung đột tài nguyên và phục hồi* (~6 ca: xung đột giữ nguyên liệu giữa 2 instance Kho, tranh chấp `Hủy đơn` và `Bắt đầu nấu`, mất mạng chi nhánh với Outbox, tắt/bật lại dịch vụ Kho/Bếp không mất đơn, xử lý tin trùng lặp/sai thứ tự, ngắt nhân bản trung tâm rồi nối lại).
- **II. BÁO CÁO TỔNG HỢP KẾT QUẢ KIỂM THỬ**
  - **2.1. Mục đích kiểm thử:** Nêu rõ mục tiêu kiểm chứng tính đúng đắn nghiệp vụ, tính phân tán/chịu lỗi/phục hồi và khả năng đáp ứng hiệu năng theo mẫu. Kèm *Hình 4.1. Sơ đồ mô hình kiểm thử tính phân tán* (PNG vẽ sạch, chỉ rõ các nút dịch vụ và điểm kiểm chứng lỗi mạng/dịch vụ).
  - **2.2. Công cụ kiểm thử:** *Bảng 4.3. Công cụ sử dụng trong quá trình kiểm thử* (`Pytest`, `Vitest / MSW`, `Docker Engine API`, `Google Chrome / Microsoft Edge`, `Apache JMeter 5.6.3`).
  - **2.3. Môi trường kiểm thử:** *Bảng 4.4. Thông số môi trường triển khai và kiểm thử* (ghi đúng thông số máy chạy thật và cụm `Docker Compose` của nhóm).
  - **2.4. Kết quả kiểm thử, đánh giá:**
    - *2.4.1. Đánh giá chức năng:* *Bảng 4.5. Tổng hợp kết quả kiểm thử chức năng* đúng mẫu thầy (Thành công / Lỗi / Không kiểm thử được / Tổng số) và tóm tắt kết quả các ca chịu lỗi/phục hồi phân tán (bỏ hoàn toàn nhật ký lỗi debug cũ).
    - *2.4.2. Kết quả kiểm thử hiệu năng:* Chạy đo lại thực tế trên môi trường hoàn chỉnh của nhóm trước khi chốt số liệu; trình bày đúng **3 bảng theo mẫu thầy** (*Bảng 4.6. Các chức năng kiểm thử hiệu năng*, *Bảng 4.7. Trường hợp kiểm thử tải đồng thời*, *Bảng 4.8. Kết quả kiểm thử hiệu năng tổng hợp*), kèm tóm tắt độ trễ đồng bộ gần thời gian thực từ chi nhánh tới Kho/Bếp.

---

## 3. Lộ trình thực hiện cuốn chiếu trên nhánh `report/v1`

1. **Chốt dàn bài** (`OUTLINE.md`) theo phản hồi của bạn.
2. **Xây dựng bộ script sinh sơ đồ PNG** (`report/scripts/render_diagrams.mjs` dùng Chromium/Playwright có sẵn trên máy) thay thế hoàn toàn Mermaid.
3. **Viết & xuất thử từng phần:**
   - Đợt 1: `01-khao-sat.md` + `Hình 1.1` (xong Phần I).
   - Đợt 2: `02-phan-tich-thiet-ke.md` + bộ sơ đồ HLD, Use Case, Activity, CSDL tổng quát/ER + chỉnh `report_schema.py` (xong Phần II).
   - Đợt 3: `03-xay-dung.md` + chụp lại 5 ảnh giao diện mới (khi frontend mới xong).
   - Đợt 4: `04-kiem-thu.md` + `Hình 4.1` + chạy lại bộ kiểm thử & đo hiệu năng sạch trên máy nhóm.
   - Đợt 5: Hoàn thiện `00-bia.md`, rà lại toàn bộ văn phong bằng skill `vietnamese-tech-report-writing`, chạy `report/build.sh` và kiểm tra trực tiếp `report/build/bao-cao.docx`.
