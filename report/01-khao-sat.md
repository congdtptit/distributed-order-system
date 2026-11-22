# PHẦN I. NGHIÊN CỨU, KHẢO SÁT YÊU CẦU

> Ghi chú cho người duyệt (xóa trước khi nộp): bản nháp do Claude soạn ngày 22/11/2026 theo yêu cầu của @Naul. Mục II dựa trên tài liệu công khai của các nhà cung cấp và một số bài đánh giá, liệt kê ở cuối phần; nên đọc lại các nguồn và chỉnh câu chữ trước khi nộp.

## I. HIỆN TRẠNG ĐƠN VỊ

Đơn vị là một chuỗi nhà hàng gồm nhiều chi nhánh bán tại quầy (POS01, POS02) và một kênh đặt món online (ONLINE). Khác với nhà hàng đơn lẻ, chuỗi chỉ có **một Bếp trung tâm** và **một Kho dùng chung**: chi nhánh chỉ là nơi nhận đơn, món được nấu ở Bếp, nguyên liệu được giữ và trừ ở Kho cho toàn chuỗi. Quản lý theo dõi số liệu tổng hợp của cả chuỗi.

Quy trình một đơn hàng đi qua nhiều bên ở những nơi khác nhau:

1. Thu ngân (hoặc khách online) tạo đơn ở chi nhánh.
2. Kho kiểm tra và giữ đủ nguyên liệu cho cả đơn, hoặc từ chối nếu thiếu.
3. Bếp nhận phiếu, bắt đầu nấu, hoàn tất; hoặc từ chối phiếu khi hỏng thiết bị, thiếu người hay nguyên liệu bị hỏng.
4. Chi nhánh nhận lại trạng thái để báo cho khách.

Vì các bên nằm ở các nơi khác nhau và nối với nhau qua mạng, chuỗi gặp những vấn đề sau trong vận hành hằng ngày:

- **Chi nhánh mất mạng.** Thu ngân vẫn phải nhận đơn, nhưng Bếp ở trung tâm không nhận được đơn cho tới khi có mạng lại. Thu ngân cần biết rõ đơn đã tới Bếp hay chưa để trả lời khách.
- **Khách hủy đơn khi Bếp có thể đã nấu.** Chi nhánh không biết chắc Bếp đã bắt đầu nấu hay chưa; nếu hủy nhầm một đơn đã nấu thì mất nguyên liệu, nếu không hủy được một đơn chưa nấu thì khách phàn nàn. Thao tác Hủy ở chi nhánh và Bắt đầu nấu ở Bếp có thể xảy ra gần như cùng lúc.
- **Nguyên liệu.** Kho phải giữ đủ nguyên liệu cho cả đơn hoặc không giữ gì; nguyên liệu bị phát hiện hỏng phải được loại ra và kiểm kho lại trước khi dùng cho đơn mới; nguyên liệu đã giữ cho một đơn bị hủy phải được trả lại kho đúng một lần.
- **Tin nhắn bị gửi lặp hoặc đến sai thứ tự.** Khi mạng chập chờn, một đơn hoặc một yêu cầu hủy có thể được gửi lại nhiều lần, hoặc yêu cầu hủy tới Bếp trước cả đơn. Hệ thống không được giữ nguyên liệu hai lần hay tạo hai phiếu cho một đơn.
- **Số liệu quản lý chậm.** Số liệu tổng hợp được gom từ các chi nhánh nên có độ trễ; quản lý cần biết số liệu của mỗi chi nhánh được tính đến thời điểm nào, nhất là khi một chi nhánh bị mất kết nối.

Toàn bộ các quy tắc nghiệp vụ, trạng thái và 44 kịch bản kiểm thử rút ra từ những vấn đề này được mô tả trong đặc tả nghiệp vụ của dự án (`docs/01-business-spec.md`).

## II. HIỆN TRẠNG THỊ TRƯỜNG VỀ GIẢI PHÁP TRONG VÀ NGOÀI NƯỚC

Trên thị trường có nhiều phần mềm quản lý bán hàng cho ngành F&B. Phần này chỉ xét các khía cạnh liên quan trực tiếp tới vấn đề của đơn vị: hoạt động khi mất mạng, gửi đơn và hủy đơn với bếp, đồng bộ dữ liệu.

**Trong nước.**

- **KiotViet** là phần mềm quản lý bán hàng phổ biến, có phiên bản cho nhà hàng. Theo các bài đánh giá, KiotViet cho phép tiếp tục bán khi mất internet và đồng bộ dữ liệu lên hệ thống khi có kết nối lại [1], [2]. Một bài đánh giá nhận xét đây là công cụ đa ngành nên chưa đáp ứng một số quy trình chuyên biệt của nhà hàng [1].
- **Sapo FnB** có tính năng Auto Offline: khi mạng gặp sự cố, phần mềm tự chuyển sang chế độ offline để nhà hàng tiếp tục vận hành, và tự đồng bộ dữ liệu khi có mạng trở lại [3].
- **MISA CukCuk** có chế độ làm việc offline: nhà hàng vẫn bán hàng khi internet gián đoạn, dữ liệu được đồng bộ lên máy chủ khi có mạng lại [4]. Chế độ này cần một máy tính cài CUKCUK Server đặt địa chỉ IP cố định, và các thiết bị bán hàng phải nằm trong cùng mạng nội bộ với máy đó [5].
- **iPOS (FABi POS)** là phần mềm bán hàng cho các mô hình F&B, kể cả chuỗi thương hiệu lớn, kèm các phân hệ kho và quản lý từ xa [6]. Các nguồn tìm được không mô tả chế độ offline của sản phẩm này.

**Ngoài nước.**

- **Toast** (Mỹ) có Offline Mode khi mất internet hoặc mất kết nối tới đám mây của Toast: thiết bị vẫn nhận đơn mới, phiếu vẫn tới màn hình bếp (KDS) nối dây qua một thiết bị làm "local hub" trong mạng của nhà hàng; đặt món online không hoạt động, không đóng được hóa đơn cho tới khi có mạng lại [7], [8]. Khi chính mạng nội bộ của nhà hàng bị mất, các thiết bị không còn trao đổi đơn với nhau được [9].
- **Square for Restaurants** (Mỹ) cho phép nhận thanh toán thẻ khi offline; các giao dịch này phải được tải lên trong vòng 24 giờ (tối đa 72 giờ tùy thiết bị) nếu không sẽ hết hạn, và đơn online mới có thể không hiện trên máy POS trong lúc mất kết nối [10].
- **Lightspeed Restaurant** (Canada) cho phép các thiết bị POS tại chỗ tiếp tục hoạt động và trao đổi với máy in và màn hình bếp tại chỗ khi mất kết nối internet tới hệ thống của Lightspeed [11].

**Nhận xét chung.** Các sản phẩm trên đều coi trọng việc bán hàng không bị gián đoạn khi mất internet, và đều theo cùng một cách: cửa hàng tiếp tục hoạt động nhờ mạng nội bộ (máy chủ hoặc thiết bị trung tâm đặt tại cửa hàng), dữ liệu được đồng bộ lên đám mây sau. Mô hình này giả định quầy thu ngân và bếp nằm **trong cùng một cửa hàng**. Các tài liệu tìm được không mô tả trường hợp một bếp trung tâm và một kho dùng chung phục vụ nhiều chi nhánh qua mạng, cũng không mô tả hệ thống cam kết gì với thu ngân khi khách hủy một đơn đã gửi đi trước lúc mất mạng.

## III. KẾT LUẬN

Các giải pháp sẵn có có nhiều ưu điểm: sản phẩm trưởng thành, đủ chức năng bán hàng, thanh toán, quản lý kho và báo cáo; có chế độ offline để cửa hàng không phải ngừng bán khi mất internet; dữ liệu tự đồng bộ khi có mạng lại.

So với nhu cầu của đơn vị, các tài liệu công khai của những giải pháp này chưa cho thấy cách đáp ứng các điểm sau:

- **Bếp và Kho ở trung tâm, chi nhánh ở xa.** Khi một chi nhánh mất mạng, Bếp không nhận được đơn của chi nhánh đó; chế độ offline trong phạm vi một cửa hàng không giải quyết được việc này. Thu ngân cần thấy rõ từng đơn đang ở đâu: "Chưa gửi, bếp chưa nhận" hay "Đang gửi, chưa biết bếp đã nhận chưa".
- **Cam kết rõ ràng khi hủy đơn.** Đơn chưa từng được gửi đi thì hủy ngay tại chi nhánh và chắc chắn không được nấu; đơn đã gửi thì chỉ Bếp quyết định, và khi Hủy với Bắt đầu nấu xảy ra cùng lúc thì đúng một thao tác thắng, mọi bên thấy cùng một kết cục.
- **Không giữ hay trả nguyên liệu hai lần** dù tin bị gửi lặp hoặc đến sai thứ tự; không dùng nguyên liệu đang chờ kiểm kho cho đơn mới.
- **Báo cáo có mốc "dữ liệu tính đến"** cho từng chi nhánh, để quản lý biết số liệu nào đã cũ khi một chi nhánh mất kết nối.

Vì vậy cần một giải pháp riêng, thiết kế theo kiến trúc phân tán ngay từ đầu: các chi nhánh, Kho và Bếp là các dịch vụ độc lập, mỗi dịch vụ có CSDL riêng, trao đổi qua hàng đợi tin nhắn (Apache Kafka) với cơ chế chống trùng, và chịu được việc một bên ngừng hoạt động hay mất mạng. Đây là đối tượng của đề tài; các phần sau trình bày phân tích thiết kế, xây dựng và kiểm thử giải pháp đó.

## Tài liệu tham khảo của Phần I

Các trang được truy cập ngày 22/11/2026.

1. Tinh tế, "Review top 7 phần mềm quản lý nhà hàng tốt nhất". https://tinhte.vn/thread/review-top-7-phan-mem-quan-ly-nha-hang-tot-nhat.3557916/
2. G2, "KiotViet". https://www.g2.com/products/kiotviet/discuss
3. Sapo, "Ra mắt tính năng Auto Offline – Vận hành nhà hàng, quán ăn ổn định khi internet gặp sự cố". https://www.sapo.vn/cap-nhat-tinh-nang/tinh-nang-auto-offline
4. MISA CukCuk, trang trợ giúp về chế độ offline. https://helpv2.cukcuk.com/en/?p=22858
5. MISA CukCuk, "Hướng dẫn thiết lập hệ thống CUKCUK.VN khi làm việc offline". https://gettingstarted.cukcuk.com/huong_dan_thiet_lap_he_thong_cukcuk_vn_khi_lam_viec_offline.htm
6. iPOS.vn, trang sản phẩm. https://ipos.vn/en/san-pham/
7. Toast, "Use Toast in Offline Mode". https://support.toasttab.com/en/article/Using-Toast-in-Offline-Mode
8. Toast, "KDS devices" (Offline mode). https://doc.toasttab.com/doc/platformguide/platformOfflineKDSDevices.html
9. Toast, "Use Toast in Offline Mode" (mất mạng nội bộ). https://support.toasttab.com/en/article/Offline-Mode-Using-Toast-During-a-Local-Network-Outage
10. Square, "Offline payments time limits". https://squareup.com/help/us/en/article/8106-offline-payments-time-limits
11. Lightspeed, "Offline POS functionality" (K-Series). https://k-series-support.lightspeedhq.com/hc/en-us/articles/53028167251867-Offline-POS-functionality
