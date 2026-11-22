<!--PTIT_COVER_PAGE-->

# BẢNG PHÂN CÔNG NHIỆM VỤ THỰC TẾ TRONG DỰ ÁN

Bảng phân công dưới đây tổng hợp vai trò chuyên môn và các hạng mục kỹ thuật trực tiếp do từng thành viên Nhóm 10 đảm nhiệm từ khâu khảo sát nghiệp vụ, thiết kế kiến trúc phân tán, lập trình dịch vụ, xây dựng giao diện đến kiểm thử chịu lỗi và đo hiệu năng hệ thống.

| Thành viên | Mã SV | Nhiệm vụ chuyên môn chính đã thực hiện |
|---|---|---|
| Nguyễn Xuân Bắc | B23DCCC016 | Thiết kế kiến trúc tổng quan (HLD) và phân mảnh dữ liệu theo dịch vụ; xây dựng dịch vụ Kho trung tâm, cơ chế khóa dòng chống deadlock theo thứ tự nguyên liệu và xử lý chống trùng lặp thông điệp. |
| Đặng Thành Công | B23DCCC024 | Thiết kế và phát triển dịch vụ Bếp trung tâm, cơ chế phân xử tranh chấp hai chiều giữa thao tác bắt đầu nấu và hủy đơn, cảnh báo nguyên liệu kiểm kho và kịch bản kiểm thử chịu lỗi Tầng 2–3. |
| Nguyễn Trung Dân | B23DCCC028 | Xây dựng dịch vụ Kênh đặt hàng hợp nhất cho quầy POS và kênh Online, tiến trình chuyển phát qua hàng chờ gửi cục bộ bảo toàn thứ tự theo đơn hàng, cơ chế khôi phục thực đơn và kịch bản mất mạng. |
| Phạm Xuân Kỳ | B23DCCC092 | Thiết kế luồng nhân bản logic PostgreSQL từ các kênh nguồn về bản sao trung tâm, xây dựng dịch vụ Tổng hợp báo cáo theo mức cô lập nhất quán, cấu hình hạ tầng mạng Docker cô lập và đo tải Apache JMeter. |
| Nguyễn Đức Thành | B23DCCC152 | Xây dựng giao diện vận hành đa màn hình trên React 19 và TypeScript (5 màn hình Chi nhánh, Bếp, Kho, Giám sát, Quản lý), sinh kiểu dữ liệu từ OpenAPI, viết bộ kiểm thử giao diện Vitest và hoàn thiện tài liệu báo cáo. |

<!--PAGEBREAK-->

<!--PTIT_TOC_PLACEHOLDER-->

# DANH MỤC TỪ VIẾT TẮT VÀ QUY ƯỚC TRẠNG THÁI

Hệ thống sử dụng một số thuật ngữ kỹ thuật viết tắt và bộ mã trạng thái chuẩn hóa thống nhất giữa các dịch vụ phân tán và giao diện điều hành như tổng hợp trong Bảng 0.1 và Bảng 0.2.

*Bảng 0.1. Danh mục từ viết tắt và thuật ngữ dùng trong tài liệu*

| Ký hiệu | Tên đầy đủ tiếng Anh / Diễn giải chuyên môn | Vai trò trong hệ thống |
|---|---|---|
| API | *Application Programming Interface* | Giao diện lập trình ứng dụng REST giữa giao diện điều hành và các dịch vụ backend. |
| CSDL | Cơ sở dữ liệu (*Database*) | Bốn cơ sở dữ liệu PostgreSQL tách biệt theo dịch vụ (Chi nhánh/Online, Kho, Bếp, Tổng hợp trung tâm). |
| DLQ | *Dead Letter Queue* | Topic hàng chờ bản tin lỗi lưu thông điệp không hợp lệ sau ngưỡng thử lại cùng cảnh báo. |
| ERD | *Entity-Relationship Diagram* | Sơ đồ thực thể liên kết mô tả cấu trúc 24 bảng vật lý trên bốn cơ sở dữ liệu phân tán. |
| HLD | *High-Level Design* | Sơ đồ thiết kế kiến trúc tổng quan kết nối đa nguồn bán hàng, Kafka và cụm xử lý trung tâm. |
| KDS | *Kitchen Display System* | Màn hình điều phối phiếu chế biến hợp nhất tại Bếp trung tâm theo thời gian gần thực. |
| KRaft | *Kafka Raft Metadata mode* | Cơ chế đồng thuận nội tại của Apache Kafka 4.3.2 vận hành cụm 3 broker không cần ZooKeeper. |
| POS | *Point of Sale* | Điểm bán hàng trực tiếp tại quầy (POS01, POS02) có khả năng nhận đơn khi mất kết nối mạng. |
| REST | *Representational State Transfer* | Giao thức trao đổi HTTP/JSON phục vụ tác vụ truy vấn, lập đơn, điều phối bếp và nhập kho. |
| SPA | *Single-Page Application* | Ứng dụng web đơn trang xây dựng trên React 19, định tuyến 5 màn hình vận hành tập trung. |
| `UUID` | *Universally Unique Identifier* | Định danh duy nhất toàn cầu gắn cho mỗi đơn hàng và sự kiện để chống trùng lặp khi gửi lại. |
| WAL | *Write-Ahead Logging* | Nhật ký ghi trước phục vụ nhân bản logic PostgreSQL từ các nhánh nguồn về bản sao trung tâm. |

*Bảng 0.2. Quy ước nhãn trạng thái nghiệp vụ theo từng dịch vụ*

| Thành phần | Mã trong CSDL | Nhãn giao diện | Ý nghĩa nghiệp vụ và quy tắc chuyển tiếp |
|---|---|---|---|
| **Đơn hàng tại nguồn** (POS/Online) | `CHO_KHO` | Chờ Kho | Đơn đã lưu cục bộ tại nguồn, đang chờ Kho trung tâm phản hồi giữ nguyên liệu. |
| | `DA_GIU` | Đã giữ | Kho đã giữ đủ nguyên liệu; phiếu chế biến đã được lập tại Bếp trung tâm. |
| | `HOAN_TAT` | Hoàn tất | Bếp đã chế biến xong và sẵn sàng bàn giao món ăn cho khách hàng. |
| | `DA_HUY` | Đã hủy | Đơn đã hủy tại điểm bán (trước khi gửi) hoặc được Bếp xác nhận hủy / từ chối. |
| | `THAT_BAI` | Thất bại | Kho từ chối do thiếu nguyên liệu, nguyên liệu đang chờ kiểm kho hoặc đơn quá hạn. |
| **Phiếu tại Bếp trung tâm** | `CHUA_CO` | Chưa có | Bản ghi giữ chỗ nội bộ khi yêu cầu hủy tới Bếp trước thông tin đơn từ Kho. |
| | `HUY_CHO_DON` | Hủy chờ đơn | Bếp đã ghi nhận hủy sớm ("Bếp sẽ không nấu"), chờ khớp thông tin đơn từ Kho. |
| | `CHO_NAU` | Chờ nấu | Phiếu đã lập hoàn chỉnh, chờ nhân viên Bếp bấm bắt đầu chế biến. |
| | `DANG_NAU` | Đang nấu | Đã bắt đầu chế biến; Kho đã chốt tiêu thụ nguyên liệu, không còn thể hủy. |
| **Hồ sơ giữ tại Kho** | `DANG_GIU` | Đang giữ | Đang giữ tạm lượng nguyên liệu tương ứng với đơn hàng hợp lệ. |
| | `DA_DUNG` | Đã dùng | Bếp đã bắt đầu chế biến, nguyên liệu được chốt tiêu thụ hoàn toàn. |
| | `DA_TRA` | Đã trả | Đơn bị hủy hoặc từ chối trước khi nấu; hoàn trả khả dụng hoặc ghi hao hụt. |
| **Trạng thái món ăn** | `CON` | Còn hàng | Đủ toàn bộ nguyên liệu theo công thức và không có nguyên liệu bị cờ kiểm kho. |
| | `HET` | Hết hàng | Thiếu tối thiểu một nguyên liệu hoặc có nguyên liệu đang gắn cờ kiểm kho. |
| | `AN` | Tạm ẩn | Món chưa được khai báo công thức tại Kho, không hiển thị trên giao diện đặt món. |

<!--PAGEBREAK-->

# LỜI MỞ ĐẦU

Trong mô hình chuỗi nhà hàng vận hành song song nhiều quầy thu ngân tại chỗ (POS) và kênh đặt món trực tuyến (Online) nhưng dùng chung một Kho nguyên liệu và một Bếp chế biến trung tâm, bài toán kỹ thuật cốt lõi không chỉ dừng ở giao diện đặt hàng mà nằm ở tính nhất quán của dữ liệu phân tán. Khi mỗi quầy cần duy trì khả năng nhận đơn độc lập kể cả lúc gián đoạn đường truyền ra trung tâm, các thao tác tạo đơn, hủy đơn, điều phối chế biến và trừ tồn kho diễn ra đồng thời dễ kéo theo tranh chấp nguyên liệu, mất đồng bộ trạng thái hoặc sai lệch số liệu báo cáo giữa các bộ phận.

Nhằm giải quyết trọn vẹn bài toán trên trong khuôn khổ học phần Phát triển ứng dụng phân tán (INT1498-20261-01), Nhóm 10 thực hiện Đề tài 4: Hệ thống đặt hàng tại quầy và online hợp nhất. Hệ thống được thiết kế theo kiến trúc hướng sự kiện tách biệt cơ sở dữ liệu từng dịch vụ (Database-per-Service), kết hợp hàng chờ giao dịch cục bộ (Transactional Outbox), cụm truyền tin Apache Kafka 3 broker KRaft bảo đảm xử lý đúng một lần và cơ chế nhân bản logic PostgreSQL phục vụ thống kê tổng hợp gần thời gian thực.

Nội dung báo cáo được tổ chức thành bốn phần chính cùng danh mục tài liệu tham khảo. Phần I khảo sát hiện trạng chuỗi đặt món đa kênh, đối chiếu các giải pháp thương mại hiện hành và xác lập đầy đủ yêu cầu chức năng, phi chức năng cùng ba mục tiêu trọng tâm của đề tài. Phần II trình bày thiết kế hệ thống gồm mô hình kiến trúc tổng quan (HLD), sơ đồ Use Case, đặc tả chi tiết 16 giao dịch nghiệp vụ theo 4 module kèm biểu đồ hoạt động, và thiết kế hoàn chỉnh 4 cơ sở dữ liệu phân tán với 24 bảng vật lý cùng 5 sơ đồ thực thể liên kết. Phần III mô tả ngăn xếp công nghệ triển khai thực tế (Python 3.12, FastAPI, Apache Kafka 4.3.2, PostgreSQL 16.14, React 19, TypeScript), cấu trúc 5 màn hình vận hành hoàn chỉnh và bốn cơ chế xử lý phân tán trọng tâm. Phần IV tổng hợp kịch bản và kết quả kiểm thử tự động đa tầng (273 ca Backend Pytest và 85 ca Frontend Vitest), phép đo chịu tải bằng Apache JMeter 5.6.3, tổng kết kết quả đạt được và hướng phát triển tiếp theo.

Nhóm 10 xin trân trọng cảm ơn giảng viên hướng dẫn ThS. Đặng Anh Tuấn đã định hướng kiến trúc, yêu cầu kiểm thử và góp ý chi tiết giúp nhóm hoàn thiện cả sản phẩm phần mềm lẫn tài liệu kỹ thuật này.

<!--PTIT_SECTION_MAIN-->
