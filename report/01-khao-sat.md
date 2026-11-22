# PHẦN I. NGHIÊN CỨU, KHẢO SÁT YÊU CẦU

## I. HIỆN TRẠNG ĐƠN VỊ

### 1.1. Bối cảnh vận hành và mô hình chuỗi bếp trung tâm

Đối tượng nghiên cứu là chuỗi nhà hàng kinh doanh đồ ăn nhanh phục vụ song song nhiều điểm bán trực tiếp tại quầy (POS01, POS02) kết hợp một kênh đặt món trực tuyến (Online). Để tối ưu chi phí mặt bằng mặt tiền tại từng điểm bán, bảo đảm đồng nhất chất lượng chế biến và tập trung kiểm soát nguồn cung đầu vào, chuỗi tổ chức theo mô hình một Bếp trung tâm và một Kho nguyên liệu dùng chung phục vụ cho toàn bộ các kênh bán hàng qua hạ tầng mạng phân tán.

Trong mô hình vận hành này, danh mục phục vụ gồm các món ăn chủ lực theo công thức định lượng thống nhất (như Phở bò, Bún chả, Cơm tấm sườn, Bánh mì thịt, Gỏi cuốn, Trà đá sử dụng chung 12 nhóm nguyên liệu cơ bản). Công việc hằng ngày phân tách rõ theo năm vai trò phối hợp liên thông như tổng hợp trong Bảng 1.1.

*Bảng 1.1. Phân công vai trò vận hành giữa các bộ phận trong chuỗi*

| Bộ phận / Vai trò | Kênh làm việc | Nhiệm vụ nghiệp vụ chính và nhu cầu thông tin |
|---|---|---|
| Thu ngân tại quầy | Máy bán hàng tại từng quầy (POS01, POS02) | Tra cứu tình trạng còn hoặc hết món, tiếp nhận đơn tại chỗ kể cả khi mất internet, theo dõi tiến độ giữ kho, xử lý yêu cầu hủy khi khách đổi ý. |
| Khách hàng trực tuyến | Kênh đặt hàng từ xa (Online) | Xem thực đơn theo thời gian gần thực, lập đơn trực tuyến, theo dõi trạng thái xử lý và gửi yêu cầu hủy khi đơn chưa chế biến. |
| Nhân viên Kho trung tâm | Kho nguyên liệu dùng chung | Nhập bổ sung nguyên liệu, đối chiếu bốn chỉ số tồn kho (khả dụng, đang giữ, đã dùng, hao hụt) và thực hiện kiểm đếm khi phát sinh báo hỏng. |
| Nhân viên Bếp trung tâm | Màn hình điều phối phiếu chế biến hợp nhất | Tiếp nhận toàn bộ đơn đủ nguyên liệu từ mọi kênh vào một hàng đợi chung, kiểm tra cảnh báo nguyên liệu, chế biến hoặc từ chối khi gặp sự cố. |
| Quản lý chuỗi / Giám sát | Màn hình giám sát và báo cáo hợp nhất | Theo dõi sức khỏe dịch vụ, cảnh báo bất thường và tổng hợp số liệu đơn hàng, nguyên nhân hủy/thất bại kèm độ mới dữ liệu của từng kênh. |

### 1.2. Quy trình nghiệp vụ hiện trạng và bốn nhóm vấn đề phân tán cốt lõi

Trong chu trình xử lý tiêu chuẩn, đơn hàng phát sinh từ thu ngân tại quầy hoặc từ khách đặt trực tuyến được chuyển tới Kho để kiểm tra định lượng công thức và giữ đủ nguyên liệu cho toàn bộ các món trong đơn, hoặc từ chối toàn bộ nếu thiếu dù chỉ một thành phần. Chỉ những đơn đã giữ nguyên liệu thành công mới chuyển tiếp thành phiếu chế biến tại Bếp trung tâm để nhân viên bếp bắt đầu nấu và hoàn tất, hoặc từ chối nếu gặp sự cố thiết bị, thiếu nhân lực hay phát hiện nguyên liệu hỏng. Kết quả giữ kho, chế biến hoặc từ chối được phản hồi về đúng điểm bán đã tạo đơn để thông báo cho khách hàng, đồng thời được tổng hợp phục vụ công tác điều hành của cấp quản lý.

Khi tách các kênh bán hàng, Kho nguyên liệu và Bếp chế biến thành những nút xử lý độc lập giao tiếp qua mạng diện rộng, quá trình vận hành phát sinh bốn nhóm vấn đề kỹ thuật cốt lõi như minh họa trên Hình 1.1.

![Hình 1.1. Bài toán hợp nhất đặt hàng đa kênh và các điểm nghẽn phân tán](images/hinh-1-1-bai-toan-da-kenh.png)

Thứ nhất là tình huống mất kết nối mạng tạm thời tại từng điểm bán. Khi quầy thu ngân mất đường truyền tới cụm trung tâm, quầy vẫn phải duy trì bán hàng liên tục bằng cách lưu đơn cục bộ thay vì ngừng phục vụ. Tuy nhiên, nếu khách hàng yêu cầu hủy một đơn vừa lập trong giai đoạn mạng chập chờn, thu ngân cần phân biệt chắc chắn đơn đó chưa từng rời khỏi máy quầy (có thể hủy dứt điểm ngay tại chỗ) hay đã bắt đầu được đẩy lên mạng (phải gửi yêu cầu sang Bếp trung tâm làm trọng tài phân xử để tránh tình trạng quầy báo đã hủy nhưng Bếp vẫn nấu).

Thứ hai là xung đột tài nguyên đồng thời trên Kho và Bếp dùng chung. Hai đơn đặt món phát sinh cùng lúc tại POS01, POS02 hoặc Online có thể cạnh tranh lượng tồn kho khả dụng cuối cùng của cùng một nguyên liệu, dễ dẫn đến trừ âm tồn kho hoặc khóa chéo tài nguyên nếu kiểm tra và cập nhật không nguyên tử. Tương tự, tại Bếp, thao tác hủy đơn từ quầy có thể diễn ra gần như đồng thời với thao tác xác nhận bắt đầu nấu của đầu bếp trên cùng một phiếu chế biến, đòi hỏi một điểm phân xử duy nhất bảo đảm hai bên luôn thống nhất đúng một trạng thái cuối.

Thứ ba là truyền thông bất đồng bộ gặp gói tin lặp hoặc lệch thứ tự. Trong môi trường mạng phân tán, việc gửi lại tự động khi đứt kết nối dễ tạo ra thông điệp trùng lặp làm trừ tồn kho hai lần hoặc hoàn kho nhiều lần cho cùng một đơn. Bên cạnh đó, yêu cầu hủy đơn từ điểm bán đi thẳng tới Bếp có thể đến nơi trước cả thông điệp giữ nguyên liệu thành công chuyển qua từ Kho; nếu Bếp bỏ qua thông điệp hủy chưa thấy đơn, món ăn vẫn bị nấu sai quy trình.

Thứ tư là độ trễ và tính nhất quán của báo cáo tổng hợp đa nguồn. Khi tổng hợp doanh thu và tỷ lệ đơn hủy từ nhiều cơ sở dữ liệu nguồn tách biệt, việc truy vấn trực tiếp sang từng quầy sẽ làm chậm giao dịch đặt món và bị gián đoạn ngay khi một điểm bán mất mạng. Ngược lại, nếu chỉ cộng dồn bản sao tập trung mà không đi kèm mốc thời gian cập nhật thực tế của từng nguồn trong cùng một lát cắt nhất quán, người quản lý dễ hiểu nhầm số liệu trễ là số liệu mới nhất của toàn chuỗi.

## II. HIỆN TRẠNG THỊ TRƯỜNG VỀ GIẢI PHÁP TRONG VÀ NGOÀI NƯỚC

### 2.1. Các giải pháp quản lý bán hàng và nhà hàng phổ biến

Trên thị trường phần mềm quản lý F&B tại Việt Nam, các sản phẩm phổ biến gồm KiotViet, Sapo FnB, MISA CukCuk và iPOS đều đáp ứng tương đối đầy đủ nghiệp vụ thu ngân tại quầy, tính định lượng kho theo công thức và đồng bộ kênh bán hàng trực tuyến. Nhằm xử lý tình huống mất kết nối internet tại cửa hàng, KiotViet [1], Sapo FnB [2] và MISA CukCuk [3] đều trang bị chế độ vận hành ngoại tuyến cho phép thu ngân lập hóa đơn cục bộ và tự động tải dữ liệu lên đám mây khi mạng khôi phục; riêng MISA CukCuk hỗ trợ mô hình máy chủ nội bộ cố định để các máy trạm trao đổi đơn trực tiếp với màn hình bếp trong cùng mạng LAN tại quán [4]. Nền tảng iPOS chú trọng bài toán quản trị chuỗi cửa hàng và kiểm soát kho tập trung [5], tuy nhiên các tài liệu công khai không công bố chi tiết cam kết xử lý khi từng điểm bán mất kết nối độc lập trong lúc chia sẻ chung một bếp trung tâm.

Ở phân khúc giải pháp quốc tế, các hệ thống chuyên nghiệp như Toast [6], [7], Square for Restaurants [8] và Lightspeed Restaurant [9] cũng tập trung cao vào khả năng bán hàng liên tục khi đường truyền gặp sự cố. Toast chỉ định một thiết bị cố định trong mạng nội bộ cửa hàng làm trạm trung chuyển cục bộ để thu ngân tiếp tục gửi phiếu xuống màn hình bếp tại chỗ khi mất internet, trong khi kênh đặt hàng trực tuyến tạm thời ngừng nhận đơn [6], [7]. Square hỗ trợ lưu tạm giao dịch thẻ ngoại tuyến tối đa 24 giờ chờ tải lên đám mây khi có mạng [8], còn Lightspeed duy trì liên lạc giữa máy tính tiền và khu vực chế biến qua bộ định tuyến nội bộ tại từng cửa hàng [9].

### 2.2. Đối chiếu theo bài toán chuỗi bếp và kho trung tâm

Mối tương quan giữa các giải pháp thị trường hiện hành với bốn yêu cầu kỹ thuật đặc thù của chuỗi đặt hàng đa kênh dùng chung Bếp và Kho trung tâm được tổng hợp trong Bảng 1.2.

*Bảng 1.2. Đối chiếu các giải pháp thị trường theo yêu cầu chuỗi đặt hàng đa kênh hợp nhất*

| Giải pháp | Nguồn tham chiếu | Bán khi mất internet | Điều phối Bếp/Kho chung qua mạng | Cam kết hủy đơn khi lệch mạng | Mốc độ mới dữ liệu báo cáo |
|---|---|---|---|---|---|
| KiotViet | [1] | Có (lưu cục bộ, đồng bộ sau) | Thiết kế theo cửa hàng đơn lẻ hoặc đồng bộ đám mây | Không công bố | Không công bố |
| Sapo FnB | [2] | Có (Auto Offline tại quầy) | Đồng bộ dữ liệu khi mạng khôi phục | Không công bố | Không công bố |
| MISA CukCuk | [3], [4] | Có (qua máy chủ LAN tại quán) | Phụ thuộc mạng nội bộ cùng lớp IP tại quán | Không công bố | Không công bố |
| iPOS | [5] | Không có trong tài liệu công khai | Có phân hệ kho và quản lý chuỗi | Không công bố | Không công bố |
| Toast | [6], [7] | Có (trạm chuyển tiếp trong mạng nội bộ quán) | Dừng đơn trực tuyến khi mất internet ra ngoài | Không công bố | Không công bố |
| Square | [8] | Có (giao dịch ngoại tuyến 24h) | Màn hình bếp phụ thuộc đồng bộ đám mây | Không công bố | Không công bố |
| Lightspeed | [9] | Có (chỉ trong LAN cửa hàng) | Dừng trao đổi nếu mất kết nối từ xa | Không công bố | Không công bố |

Qua đối chiếu trên Bảng 1.2 có thể thấy các giải pháp thương mại hiện hành có thế mạnh về độ hoàn thiện nghiệp vụ bán hàng và thanh toán tại từng cửa hàng đơn lẻ, song kiến trúc ngoại tuyến của chúng mặc định thu ngân và bếp nấu cùng nằm chung trong một mạng cục bộ (LAN). Khi chuyển sang bài toán nhiều điểm bán quầy và kênh trực tuyến dùng chung một Bếp và một Kho trung tâm qua mạng phân tán diện rộng, những sản phẩm sẵn có không công bố cơ chế bảo đảm đồng thời ba tính chất: phân định chắc chắn ranh giới hủy cục bộ hay hủy tại Bếp khi đứt mạng, khóa giữ nguyên liệu nguyên tử không âm kho và tổng hợp báo cáo có chỉ báo độ trễ riêng theo từng kênh.

## III. XÁC ĐỊNH YÊU CẦU HỆ THỐNG VÀ PHẠM VI GIẢI PHÁP

### 3.1. Yêu cầu chức năng theo bốn phân hệ nghiệp vụ

Từ khảo sát thực tế quy trình vận hành và các khoảng trống kỹ thuật ở mục I và II, hệ thống mới được xác lập yêu cầu chức năng bám sát bốn phân hệ liên thông:

1. Phân hệ tiếp nhận và theo dõi đơn hàng đa kênh (POS và Online): cho phép tra cứu danh mục món kèm trạng thái phục vụ theo độ mới thực đơn (cảnh báo khi dữ liệu quá 5 phút hoặc mất kết nối), tạo đơn hợp lệ lưu bền vững ngay cả khi mất mạng, gửi yêu cầu hủy kèm danh mục lý do chuẩn hóa của khách hàng (khách đổi ý, đợi quá lâu, nhập nhầm đơn) và theo dõi tiến độ chuyển phát từng đơn theo thứ hạng trạng thái không thụt lùi.
2. Phân hệ quản lý kho và giữ nguyên liệu trung tâm: xử lý giữ trọn vẹn toàn bộ nguyên liệu của một đơn hàng hoặc từ chối toàn phần nếu thiếu hàng hay có nguyên liệu đang chờ kiểm kho; từ chối đơn quá hạn 4 giờ hoặc sai lệch đồng hồ vượt quá 5 phút tương lai; hỗ trợ nhập bổ sung tồn kho chính xác ba chữ số thập phân, xác nhận kiểm đếm thực tế gỡ cờ kiểm kho và công bố tự động trạng thái món ăn theo số phiên bản tăng đơn điệu.
3. Phân hệ điều phối chế biến tại Bếp trung tâm: hợp nhất phiếu chế biến từ tất cả nguồn bán hàng vào hàng đợi chung phân rõ chờ nấu và đang nấu; hiển thị cảnh báo trực tiếp trên phiếu có nguyên liệu đang cần kiểm kho; thực thi thao tác bắt đầu nấu (chốt tiêu thụ nguyên liệu và chặn hủy đơn), hoàn tất chế biến hoặc từ chối phiếu theo lý do cố định (hỏng thiết bị, thiếu nhân lực, nguyên liệu hỏng kèm chỉ định đích danh nguyên liệu hao hụt), đồng thời đóng vai trò trọng tài lưu giữ yêu cầu hủy đến sớm.
4. Phân hệ tổng hợp báo cáo và giám sát vận hành toàn chuỗi: thống kê tức thời tổng số đơn theo năm trạng thái và cơ cấu lý do đóng đơn của từng kênh kèm nhãn thời gian dữ liệu tính đến và độ trễ tính bằng giây; cung cấp màn hình giám sát sức khỏe kết nối của toàn bộ dịch vụ, bộ đếm tin chưa gửi tại điểm bán, cảnh báo chậm đọc tin trên ngưỡng 5 phút và nhật ký cảnh báo nghiệp vụ bất thường.

### 3.2. Yêu cầu phi chức năng và các chỉ tiêu kiểm chứng

Để bảo đảm hệ thống vận hành tin cậy trong điều kiện lỗi mạng, dừng tiến trình đột ngột và tranh chấp tải đồng thời, các yêu cầu phi chức năng cốt lõi được lượng hóa cụ thể tại Bảng 1.3.

*Bảng 1.3. Bộ yêu cầu phi chức năng trọng tâm của hệ thống phân tán*

| Nhóm yêu cầu | Nội dung yêu cầu cụ thể | Chỉ tiêu đánh giá và cơ chế đáp ứng |
|---|---|---|
| Tính sẵn sàng cục bộ | Điểm bán vẫn nhận đơn mới và hủy được đơn chưa rời quầy khi mất mạng tới cụm trung tâm. | Cơ sở dữ liệu và hàng chờ gửi tách riêng cho từng kênh; thăm dò kết nối ngưỡng 2 giây trước lần thử gửi đầu tiên. |
| Toàn vẹn tài nguyên | Hai luồng giữ nguyên liệu đồng thời không gây âm kho và không phát sinh khóa chéo; tranh chấp hủy với bắt đầu nấu cho đúng một kết quả cuối. | Khóa dòng tuần tự theo thứ tự mã tăng dần khi giữ kho; khóa hàng đơn điểm tại Bếp; giữ đúng một hồ sơ kết quả cho mỗi mã đơn. |
| Tin cậy truyền thông | Bản tin gửi lại nhiều lần không làm trừ kho hay hoàn kho lặp lại; gói tin hỏng không chặn các đơn hợp lệ khác. | Cụm truyền tin 3 node đồng thuận, lưu nhật ký 7 ngày; kiểm tra mã sự kiện chống trùng trong cùng giao dịch CSDL; tách tin lỗi sau 5 lần thử. |
| Nhất quán báo cáo | Số liệu tổng hợp và mốc thời gian cập nhật từng nguồn khớp nhau tuyệt đối trong một thời điểm đọc, không chặn giao dịch bán hàng. | Nhân bản logic bất đồng bộ về bản sao trung tâm; đọc nhất quán theo lát cắt thời gian; cảnh báo chậm khi độ trễ vượt ngưỡng 30 giây. |
| Hiệu năng đáp ứng | Đáp ứng ổn định dưới tải đồng thời nhiều người dùng và đồng bộ trạng thái đơn gần thời gian thực. | Đạt tỷ lệ lỗi 0% dưới tải đồng thời các API trọng tâm; độ trễ trọn vòng từ tạo đơn tới giữ kho thành công ở mức dưới 1 giây trong mạng nội bộ. |

### 3.3. Mục tiêu và phạm vi giải pháp

Từ yêu cầu chức năng và phi chức năng nêu trên, đề tài xác lập ba mục tiêu trọng tâm xuyên suốt toàn bộ quá trình phân tích, xây dựng và kiểm thử:

1. Duy trì nhận đơn độc lập tại từng quầy POS và kênh Online, bảo đảm bán hàng thông suốt khi gián đoạn đường truyền ra trung tâm.
2. Điều phối Kho và Bếp trung tâm không xung đột tài nguyên, phân xử chính xác mọi tình huống tranh chấp lệnh hủy, hoàn trả nguyên liệu hỏng và sự cố mạng/tiến trình.
3. Tổng hợp báo cáo điều hành toàn chuỗi gần thời gian thực đi kèm chỉ báo độ trễ từng nguồn và giám sát vận hành phân tán tập trung.

Về phạm vi triển khai, hệ thống tập trung giải quyết trọn vẹn bài toán kiến trúc hướng sự kiện phân tán, hàng chờ giao dịch cục bộ, khóa chống tranh chấp dữ liệu, nhân bản logic PostgreSQL, giao diện web 5 màn hình vận hành đáp ứng đa kích thước thiết bị và bộ kiểm thử tích hợp/tiêm lỗi/chịu tải thực tế trên cụm container. Các phần nghiệp vụ bổ trợ như kết nối cổng thanh toán trực tuyến, điều khiển máy in hóa đơn vật lý tại quầy và mở rộng mô hình đa kho theo vùng địa lý nằm ngoài phạm vi triển khai đợt đầu và được đề xuất ở hướng phát triển tiếp theo.

## IV. KẾT LUẬN

Khảo sát hiện trạng vận hành và đối chiếu bảy giải pháp thương mại trong và ngoài nước cho thấy bài toán hợp nhất đa kênh dùng chung một Bếp và Kho trung tâm đặt ra những đòi hỏi khắt khe về tính nhất quán phân tán mà các giải pháp đóng gói cho mô hình cửa hàng đơn lẻ chưa giải quyết triệt để. Việc thiết lập đầy đủ bộ yêu cầu chức năng theo bốn phân hệ cùng các chỉ tiêu phi chức năng định lượng tại Phần I là cơ sở trực tiếp để thiết kế kiến trúc tổng quan, đặc tả 16 giao dịch nghiệp vụ và tổ chức bốn cơ sở dữ liệu tách biệt theo dịch vụ trong Phần II.
