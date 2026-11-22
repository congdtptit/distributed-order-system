<!-- Sinh tự động bởi backend/scripts/report_tests.py từ một lần chạy pytest đầy đủ. Không sửa tay. -->

| STT | Kịch bản | Kết quả mong đợi | Quy tắc | Tầng | Số test | Kết quả |
|---|---|---|---|---|---|---|
| 1 | Yêu cầu hủy tới Bếp trước đơn; sau đó Kho giữ được và chuyển đơn sang Bếp | Không có phiếu; đơn Đã hủy; Kho hoàn đủ một lần | BR7 | Tầng 1 | 3 | Đạt |
| 2 | Như kịch bản 1, rồi Kho gửi lại đơn lần hai | Không lập phiếu, không gửi lệnh hoàn lần hai | BR8 | Tầng 1 | 1 | Đạt |
| 3 | Thu ngân bấm hủy và Bếp bấm Bắt đầu nấu cùng lúc | Đúng một thao tác thắng; trạng thái Bếp, Kho và chi nhánh khớp nhau | BR7 | Tầng 2 | 4 | Đạt |
| 4 | Bếp từ chối phiếu khi Kho đang dừng, rồi Kho chạy lại | Chi nhánh thấy Đã hủy ngay; Kho hoàn đúng một lần khi chạy lại | BR4 | Tầng 3 | 2 | Đạt |
| 5 | Lệnh hoàn của cùng một đơn tới Kho ba lần | Tồn tăng đúng một lần | BR12 | Tầng 1 | 1 | Đạt |
| 6 | Bếp từ chối với lý do nguyên liệu hỏng (thịt) | Thịt ghi hao hụt, nguyên liệu khác được hoàn; món dùng thịt sang Hết; phiếu Chờ nấu có thịt hiện cảnh báo | BR6 | Tầng 1 | 2 | Đạt (Phần đợt 1 đạt; phần món chuyển sang Hết thuộc đợt 2) |
| 7 | Tin Đã hủy tới chi nhánh trước tin Đã giữ | Chi nhánh giữ Đã hủy, bỏ qua Đã giữ | BR3 | Tầng 1 | 1 | Đạt |
| 8 | Đơn có Hủy chờ đơn bị Kho từ chối | Chi nhánh thấy Thất bại, cờ hủy tắt; bản ghi Bếp sang Thất bại | BR7 | Tầng 1 | 4 | Đạt |
| 9 | Kho trả Thất bại vì thiếu hàng, nhập thêm hàng, rồi đơn bị gửi lặp | Kho trả lại Thất bại, không giữ | BR12 | Tầng 2 | 1 | Đạt |
| 10 | POS mất mạng nên bộ gửi không ghi cờ; thu ngân tạo đơn rồi hủy khi gói tạo đơn chưa từng thử gửi, sau đó có mạng lại | POS khép Đã hủy ngay, bỏ gói, không gửi gì; Kho và Bếp không có bản ghi; đơn không bao giờ được nấu | BR5, BR9 | Tầng 3 | 3 | Đạt |
| 12 | Mạng chập chờn lâu: các gói đã thử gửi gặp nhiều lần gửi thất bại | Không gói nào bị bỏ; khi có mạng lại mọi gói được gửi, đúng thứ tự theo từng mã đơn | BR9 | Tầng 3 | 2 | Đạt |
| 15 | POS mất mạng lâu hơn X rồi gửi đơn cũ | Kho trả Thất bại (đơn quá hạn), không giữ nguyên liệu | BR11 | Tầng 2 | 1 | Đạt |
| 16 | Đơn có thời điểm tạo ở tương lai 1 giờ | Kho trả Thất bại | BR11 | Tầng 2 | 1 | Đạt |
| 18 | Kho khởi động lại, sau đó một món đổi trạng thái | Phiên bản tiếp tục tăng; POS nhận cập nhật ngay | BR10 | Tầng 3 |  | Chưa kiểm thử |
| 19 | POS nhận tin Hết (v6) rồi snapshot có Còn (v5) tới sau | POS giữ Hết (v6) | BR10 | Tầng 1 |  | Chưa kiểm thử |
| 20 | Kho khôi phục từ bản sao lưu và tăng epoch; món A đang Hết ở đời cũ, món B không có trong snapshot mới | A theo snapshot mới; B chuyển Ẩn | BR10 | Tầng 1 |  | Chưa kiểm thử |
| 21 | Kho không đổi tồn trong 10 phút, heartbeat đều | POS không hiện "Có thể đã hết" | BR10 | Tầng 1 |  | Chưa kiểm thử |
| 22 | Kho nhận lệnh hoàn cho đơn không có bản ghi giữ | Tồn không đổi, có dòng nhật ký | BR12 | Tầng 1 | 1 | Đạt |
| 23 | Yêu cầu hủy tới khi phiếu Đang nấu | Chi nhánh thấy "Không hủy được: bếp đã bắt đầu nấu", trạng thái giữ nguyên | BR7 | Tầng 1 | 3 | Đạt |
| 24 | Inventory giữ được một đơn của POS01 | Kitchen nhận đơn qua kitchen-orders; POS01 nhận Đã giữ qua status-events của mình; chi nhánh khác không nhận gì | Mục 13 | Tầng 2 | 3 | Đạt |
| 25 | Tắt Kitchen 2 giờ trong khi vẫn có đơn và yêu cầu hủy, rồi bật lại | Kitchen xử lý đủ mọi tin còn trong Kafka, không mất, không trùng | Mục 13 | Tầng 3 | 1 | Đạt |
| 26 | Dừng tiến trình consumer sau khi commit DB nhưng trước khi commit offset | Kafka gửi lại tin; processed_events chặn bản trùng, không có hiệu ứng thứ hai | BR4 | Tầng 1 | 2 | Đạt |
| 27 | POS01 gửi yêu cầu hủy cho đơn của POS02 đã có phiếu ở Bếp | Kitchen bỏ qua yêu cầu và cảnh báo; đơn của POS02 không đổi trạng thái | Mục 13.2 | Tầng 1 | 1 | Đạt |
| 28 | Chạy hai instance Kitchen; cả hai cùng lúc nhận đơn và yêu cầu hủy của một mã đơn | Chỉ có một bản ghi; kết quả khớp bảng 3.2 dù tin nào đến trước | BR7 | Tầng 2 | 1 | Đạt |
| 29 | Inventory nhận tin có event_type lạ | Tin vào dlq, đơn được đánh dấu cần kiểm tra, các đơn khác vẫn được xử lý | Mục 9 | Tầng 1 | 3 | Đạt |
| 30 | Kho thiếu một nguyên liệu khi giữ đơn, rồi tin đơn đó bị gửi lại | Tồn không đổi; bản ghi Thất bại, dòng processed_events và tin Failed đều được lưu; lần gửi lại nhận đúng kết quả cũ | BR12 | Tầng 2 | 1 | Đạt |
| 31 | Tắt một broker Kafka trong lúc các chi nhánh đang gửi đơn | Không mất tin nào đã được Kafka xác nhận; việc gửi vẫn tiếp tục | Mục 13 | Tầng 1 | 2 | Đạt |
| 33 | Kho báo Thất bại tới Bếp trước, yêu cầu hủy của đơn đó tới sau | Bếp có bản ghi Thất bại; không tạo Hủy chờ đơn; chi nhánh thấy Thất bại | BR8 | Tầng 1 | 2 | Đạt |
| 34 | POS02 gửi yêu cầu hủy cho mã đơn của POS01 trước khi đơn tới Bếp | Đơn của POS01 vẫn được lập phiếu Chờ nấu; yêu cầu của POS02 bị bác; có cảnh báo | Mục 13.2 | Tầng 1 | 1 | Đạt |
| 35 | Như kịch bản 34, nhưng POS01 cũng gửi yêu cầu hủy trước khi đơn tới | Đơn Đã hủy; Kho hoàn đúng một lần | BR7 | Tầng 1 | 1 | Đạt |
| 36 | POS gửi đơn rồi mất mạng, thu ngân bấm hủy; khi có mạng lại, Bếp đã bấm Bắt đầu nấu trước khi nhận yêu cầu hủy | Chi nhánh thấy "Không hủy được: bếp đã bắt đầu nấu"; đơn đi tiếp tới Hoàn tất; nguyên liệu không bị hoàn | BR5, BR7 | Tầng 3 | 1 | Đạt |
| 37 | Thu ngân bấm hủy đúng lúc bộ gửi lấy gói tạo đơn chưa từng thử gửi | Đúng một bên thắng: hoặc đơn bị hủy cục bộ và không gói nào được gửi, hoặc gói được gửi và yêu cầu hủy đi qua Bếp | BR9 | Tầng 2 | 1 | Đạt |
| 39 | Inventory nhận đơn đọc được nhưng có số lượng âm | Kho ghi bản ghi Thất bại (dữ liệu đơn không hợp lệ), không giữ; chi nhánh thấy Thất bại; tin không vào dlq | BR12 | Tầng 2 | 1 | Đạt |
| 42 | Hai đơn tới cùng lúc ở hai instance Inventory, cùng cần một nguyên liệu, tổng nhu cầu vượt tồn khả dụng | Đúng một đơn Đã giữ, đơn kia Thất bại; tồn khả dụng không âm; không đơn nào được giữ một phần | BR1 | Tầng 2 | 2 | Đạt |
| 43 | Kho có 10 kg thịt; một đơn giữ 2 kg rồi Bếp bấm Bắt đầu nấu | Tồn khả dụng là 8 kg trước và sau khi nấu; đang giữ về 0; đã dùng tăng 2 kg | Mục 3.3 | Tầng 1 | 1 | Đạt |
| 44 | Thịt đang bị đánh dấu cần kiểm kho, tồn khả dụng còn đủ; POS mất mạng vẫn nhận đơn có món dùng thịt rồi gửi đi | Kho trả Thất bại (nguyên liệu đang chờ kiểm kho); không nguyên liệu nào của đơn bị giữ | BR6 | Tầng 2 | 1 | Đạt |
| 48 | Thịt đang bị đánh dấu cần kiểm kho, một phiếu Chờ nấu có thịt đang hiện cảnh báo; Kho xác nhận kiểm kho xong | Cờ được gỡ; cảnh báo trên phiếu mất; đơn mới dùng thịt được giữ; món dùng thịt về Còn | BR6 | Tầng 1 | 2 | Đạt (Phần đợt 1 đạt; phần món trở lại Còn thuộc đợt 2) |
| 49 | Một đơn giữ 2 kg thịt; công thức của món đổi thành 3 kg; rồi Bếp hủy hoặc từ chối đơn | Kho hoàn đúng 2 kg đã ghi lúc giữ; tồn khả dụng trở lại như trước khi giữ | BR6 | Tầng 1 | 1 | Đạt |
| 50 | Nhân viên bấm Từ chối trên phiếu đã Đang nấu | Thao tác bị từ chối; phiếu vẫn Đang nấu; Kho không nhận lệnh hoàn nào | Luồng A | Tầng 1 | 1 | Đạt |
| 51 | Nhân viên bấm Từ chối với lý do nguyên liệu hỏng đúng lúc yêu cầu hủy của chi nhánh gốc tới phiếu Chờ nấu | Đúng một thao tác thắng; Kho xử lý đúng một lệnh hoàn theo lý do của bên thắng: hoặc hoàn toàn bộ, hoặc hao hụt và đánh dấu kiểm kho | BR6, BR7 | Tầng 2 | 1 | Đạt |
| 52 | Hai nhân viên bấm Từ chối và Bắt đầu nấu trên cùng một phiếu Chờ nấu cùng lúc | Đúng một thao tác thắng; lần giữ rời Đang giữ đúng một lần, tới đã dùng hoặc tới hoàn | BR7, BR12 | Tầng 2 | 1 | Đạt |
| 53 | Kho đang dừng; một đơn nằm ở Chờ Kho quá N phút | Chi nhánh hiện cảnh báo kèm nút Yêu cầu hủy; đơn không tự đổi trạng thái | Luồng D | Tầng 1 | 1 | Đạt |
| 54 | POS mất mạng; một đơn trong hàng chờ gửi còn chưa tới 1 giờ là quá hạn X | Chi nhánh hiện mất kết nối, số gói đang chờ gửi và cảnh báo đơn sắp quá hạn | Luồng D | Tầng 1 | 1 | Đạt |
| 55 | Ngắt nhân bản từ POS01 về Central Order Replica trong khi POS01 và POS02 vẫn nhận đơn, rồi nối lại | Trong lúc ngắt, báo cáo vẫn xem được, mốc "dữ liệu tính đến" của POS01 dừng lại còn của POS02 vẫn chạy; khi nối lại, số liệu của POS01 khớp với DB của chi nhánh | Luồng D, mục 13.5 | Tầng 3 | 1 | Đạt |

| Tổng hợp kết quả kiểm thử | Số lượng |
|---|---|
| Kịch bản đạt | 40 |
| Kịch bản lỗi | 0 |
| Kịch bản chưa kiểm thử (thuộc các bước sau) | 4 |
| Tổng số kịch bản | 44 |
| Tổng số test tự động đã chạy (kể cả test không gắn kịch bản) | 250 |
| Trong đó test lỗi | 0 |
