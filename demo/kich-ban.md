# Kịch bản demo

Hướng dẫn trình diễn hệ thống đặt món phân tán, khoảng 20–25 phút. Mọi bước đã được diễn tập trên cụm sạch ngày 22/11/2026; thời gian chờ ghi trong ngoặc là số đo của lần diễn tập đó. Tên kỹ thuật (dịch vụ, topic, trạng thái) giữ nguyên như trong code.

## Chuẩn bị (trước giờ demo 10 phút)

1. Bật Docker Desktop. Chạy:

   ```bash
   bin/demo reset
   ```

   Lệnh này dọn sạch cụm, khởi động đủ 21 container ở **chế độ demo** (dữ liệu món coi là cũ sau 1 phút thay vì 5, Kho gửi heartbeat 20 giây một lần thay vì 60), tạo dữ liệu mẫu qua chính API của hệ thống, rồi kiểm tra. Mọi dòng phải là `ok` (mất khoảng 2–3 phút).

2. Mở sẵn các tab trình duyệt:
   - Trang Demo: http://localhost:5173/demo/POS01 (chi nhánh và Bếp cạnh nhau, có hướng dẫn kịch bản ở trên).
   - Màn Kho, Giám sát, Quản lý: chọn ở menu bên trái của http://localhost:5173.
   - Kafka UI (tùy chọn, để chỉ các topic và consumer group): http://localhost:8080.
3. Mở một terminal ở thư mục dự án cho các lệnh `bin/chaos`. Lệnh `bin/chaos start …` in nhiều dòng của Docker Compose; chỉ cần chờ nó kết thúc.
4. Trạng thái ban đầu sau `bin/demo reset`: đơn ở cả ba chi nhánh, phiếu Chờ nấu, Đang nấu, Hoàn tất; Sườn đang chờ kiểm kho nên **Cơm tấm sườn bị khóa "Hết"** trên form đặt món và phiếu Cơm tấm còn lại ở Bếp có cảnh báo đỏ.

## Trình tự trình diễn

### 1. Kiến trúc (2 phút)

Mở hình HLD trong báo cáo (`report/images/hld.png`). Ý chính: các chi nhánh, Kho và Bếp là dịch vụ riêng, mỗi dịch vụ một CSDL, chỉ trao đổi qua Kafka (3 broker, mỗi topic 3 bản sao); tin gửi đi qua outbox; tin nhận về chống trùng bằng `processed_events`; báo cáo đọc bản sao trung tâm được nhân bản bằng PostgreSQL logical replication.

### 2. Luồng chính (2 phút)

Trên trang Demo: nhập 1 Phở bò, bấm **Tạo đơn**.
- Chỉ: đơn hiện Chờ Kho, cột Gửi đi đổi sang "Đã gửi đi", rồi đơn lên **Đã giữ** (dưới 1 giây); phiếu hiện ở cột Chờ nấu của Bếp.
- Ở Bếp bấm **Bắt đầu nấu**, rồi **Hoàn tất**: đơn ở chi nhánh lên Hoàn tất.
- Mở màn **Quản lý**: số đơn đã đổi, mỗi chi nhánh có mốc "dữ liệu tính đến" cách đây vài giây.

### 3. Kịch bản 3: Hủy và Bắt đầu nấu cùng lúc (2 phút)

1. Tạo đơn Phở bò, chờ phiếu ở cột Chờ nấu.
2. Bấm **Hủy đơn** ở chi nhánh (chọn lý do, xác nhận) và **Bắt đầu nấu** ở Bếp gần như cùng lúc.
   - Thường Bắt đầu nấu thắng, vì yêu cầu hủy còn phải đi qua Kafka: chi nhánh hiện "Không hủy được: bếp đã bắt đầu nấu", đơn vẫn Đã giữ.
3. Làm lại với đơn mới: bấm **Hủy đơn** trước, khoảng nửa giây sau mới bấm **Bắt đầu nấu**: hủy thắng, Bếp báo "Phiếu vừa đổi trạng thái", đơn Đã hủy.
- Ý chính: Bếp là bên duy nhất quyết định hủy (BR7); ai được Bếp ghi nhận trước thì thắng; cả ba bên luôn cùng một kết cục.

### 4. Kịch bản 1: yêu cầu hủy tới Bếp trước đơn (3 phút)

1. Tắt Kho:

   ```bash
   bin/chaos stop inventory-1
   bin/chaos stop inventory-2
   ```

2. Tạo đơn Phở bò. Chờ cột Gửi đi báo "Đã gửi đi" (dưới 1 giây). Đơn đứng ở Chờ Kho vì Kho đang tắt.
3. Bấm **Hủy đơn**. Chi nhánh hiện "Bếp sẽ không nấu" (dưới 1 giây): Bếp đã ghi bản ghi Hủy chờ đơn dù chưa thấy đơn.
4. Bật lại Kho:

   ```bash
   bin/chaos start inventory-1
   bin/chaos start inventory-2
   ```

5. Đơn chuyển **Đã hủy** (khoảng 3 giây). Bếp không có phiếu nào. Màn Kho: lượng "Đang giữ" của Bánh phở, Thịt bò, Rau sống trở về như trước, tức Kho đã giữ rồi hoàn đúng một lần.

### 5. Kịch bản 4: Bếp từ chối phiếu khi Kho đang tắt (2 phút)

1. Tạo đơn, chờ phiếu ở cột Chờ nấu.
2. Tắt Kho (hai lệnh `bin/chaos stop` như trên).
3. Ở Bếp bấm **Từ chối**, chọn lý do Hỏng thiết bị. Chi nhánh thấy **Đã hủy** ngay (dưới 1 giây): Bếp báo thẳng cho chi nhánh, không cần Kho.
4. Bật lại Kho. Vài giây sau, màn Kho: lượng "Đang giữ" về 0, tức lệnh hoàn kho nằm chờ trong Kafka và được xử lý đúng một lần khi Kho chạy lại.

### 6. Kịch bản 10 và 36: mất mạng ở chi nhánh (6 phút)

Hai kịch bản đi thành cặp để chỉ ranh giới của cam kết khi hủy lúc mất mạng.

**Kịch bản 10: đơn chưa từng gửi đi.**
1. Cắt mạng:

   ```bash
   bin/chaos offline pos01
   ```

   Thanh trên của chi nhánh báo **Mất kết nối Kafka** (khoảng 5 giây). Chi nhánh vẫn nhận đơn.
2. Tạo đơn: cột Gửi đi báo "Chưa gửi, bếp chưa nhận". Bấm **Hủy đơn**: đơn **Đã hủy ngay** tại chi nhánh. Đơn này chắc chắn không bao giờ được nấu.
3. Chờ khoảng 1 phút (đo được 52 giây): form đặt món hiện "Tình trạng món có thể đã thay đổi.", Cơm tấm đổi từ "Hết" bị khóa sang **"Có thể đã hết"** và vẫn đặt được (Luồng C: dữ liệu đã cũ thì chỉ cảnh báo, Kho vẫn quyết định).
4. Nối mạng:

   ```bash
   bin/chaos online pos01
   ```

   Thanh trên báo đã kết nối (khoảng 4 giây); chi nhánh lấy lại tình trạng món, Cơm tấm lại bị khóa. Bếp không có phiếu của đơn đã hủy.

**Kịch bản 36: đơn đã gửi đi rồi mới mất mạng.**
1. Tạo đơn, chờ **Đã giữ** và phiếu ở cột Chờ nấu.
2. `bin/chaos offline pos01`, chờ Mất kết nối Kafka (khoảng 5–7 giây).
3. Bấm **Hủy đơn**: lần này không hủy tại chỗ được, đơn hiện "Đang yêu cầu hủy", "Chưa gửi yêu cầu hủy, chưa chắc hủy được".
4. Ở Bếp bấm **Bắt đầu nấu** (Bếp không biết có yêu cầu hủy).
5. `bin/chaos online pos01`. Khoảng 6 giây sau chi nhánh hiện **"Không hủy được: bếp đã bắt đầu nấu"**. Ở Bếp bấm Hoàn tất: đơn Hoàn tất; Kho ghi nguyên liệu đã dùng, không hoàn kho.
- Ý chính: chi nhánh chỉ tự quyết hủy với đơn chưa từng được gửi; đã gửi thì chỉ Bếp quyết.

### 7. Luồng C trên cụm thật (2 phút, tùy chọn)

1. Màn Kho: dòng Sườn có nhãn "Chờ kiểm kho". Bấm **Kiểm kho xong**.
2. Trang Demo: Cơm tấm sườn hết bị khóa (vài giây); cảnh báo đỏ trên phiếu Cơm tấm ở Bếp biến mất.

### 8. Kịch bản 55: cắt nhân bản về trung tâm (2 phút, tùy chọn)

1. `bin/chaos cut-replication pos01`, tạo một đơn ở POS01.
2. Màn **Quản lý**: báo cáo vẫn xem được; mốc "dữ liệu tính đến" của POS01 đứng yên, "cách đây" tăng dần, POS02 và ONLINE vẫn mới; đơn vừa tạo chưa được tính.
3. `bin/chaos restore-replication pos01`: vài giây sau POS01 mới lại và số liệu khớp.

### 9. Giám sát (1 phút)

Màn **Giám sát**: mỗi dịch vụ một dòng (trả lời hay không, kết nối Kafka, số mục chờ gửi); consumer chậm; cảnh báo lọc theo loại. Có thể chạy `bin/chaos offline pos02` để dòng POS02 báo Mất kết nối Kafka, rồi `bin/chaos online pos02`.

## Sau mỗi phần, nếu có gì lệch

- Kiểm nhanh cả cụm: `bin/demo check`.
- Quên bật lại Kho hoặc nối lại mạng: `bin/chaos status` cho biết container nào đang dừng và chi nhánh nào thiếu mạng.
- Muốn bắt đầu lại từ đầu: `bin/demo reset` (2–3 phút).
- Nếu một kịch bản không chạy được trên sân khấu, chạy test tự động của nó (khoảng 10–70 giây mỗi test), ví dụ:

  ```bash
  docker compose exec tools pytest -m tier3 -v order-service/tests/test_branch_e2e.py
  ```

  Test tự cắt mạng, tắt Kho và kiểm đúng kết quả mong đợi, nên vẫn chứng minh được hành vi.
