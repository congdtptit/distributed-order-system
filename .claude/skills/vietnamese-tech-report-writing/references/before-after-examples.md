# Ví dụ đối chiếu Trước và Sau cho báo cáo kỹ thuật tiếng Việt

Tài liệu này minh họa cách viết lại các đoạn văn thường gặp trong đồ án CNTT để loại bỏ dấu hiệu văn AI (đứng ngoài bình luận, thổi phồng, chia ý vụn bằng gạch đầu dòng in đậm, lỗi dịch máy và nhịp câu đều nhau) nhưng vẫn giữ giọng khách quan kỹ thuật và đủ toàn bộ thông số gốc.

---

## Mẫu 1. Mở đầu chương và bối cảnh bài toán

### Trước (mắc lỗi giọng đứng ngoài, thổi phồng và "không chỉ... mà là...")

> Tuyển dụng nhân sự là quy trình nghiệp vụ đầu vào có tính liên phòng ban cao nhất trong khối quản trị nguồn nhân lực. Một chu kỳ tuyển dụng chuẩn không chỉ dừng lại ở thao tác đăng tin và thu nhận CV, mà là chuỗi phối hợp nối tiếp qua nhiều trạng thái dữ liệu giữa năm nhóm chủ thể. Tại các doanh nghiệp công nghệ quy mô vừa và đang mở rộng, việc sử dụng công cụ văn phòng rời rạc như hộp thư điện tử cá nhân, Google Forms và bảng tính Excel bộc lộ những đứt gãy nghiêm trọng về mặt quản trị thông tin, từ đó khẳng định sự cấp thiết của việc xây dựng hệ thống quản lý tuyển dụng toàn diện.

**Các điểm cần sửa:** Cụm phóng đại thiếu kiểm chứng (*"cao nhất"*, *"đứt gãy nghiêm trọng"*), khuôn câu *"không chỉ... mà là..."*, lặp chữ *"việc"* thừa, câu kết phô trương (*"khẳng định sự cấp thiết... toàn diện"*).

### Sau (giọng kỹ thuật khách quan, đi thẳng vào vấn đề)

> Quy trình tuyển dụng tại doanh nghiệp nhỏ và vừa thường phân tán qua email cá nhân, Google Forms, file Excel dùng chung và các nhóm chat nội bộ. Khi lượng hồ sơ lên tới vài trăm đơn mỗi tháng, cách làm thủ công rất dễ làm lệch dữ liệu: nhiều nhân sự cùng sửa bảng tính dẫn đến ghi đè trạng thái, còn tệp CV hay nhận xét phỏng vấn nằm rải rác qua các luồng chat nên khó đối chiếu khi cần xem lại. Để giải quyết tình trạng này, đề tài xây dựng hệ thống `RMS` lưu trữ tập trung trên một nền tảng web thống nhất cho năm vai trò: Ứng viên, HR, Người phỏng vấn, Hiring Manager và Admin.

---

## Mẫu 2. Lựa chọn kiến trúc kỹ thuật (từ bullet in đậm sang văn xuôi)

### Trước (chia gạch đầu dòng in đậm vụn, nhịp các ý đều nhau)

> Hệ thống lựa chọn kiến trúc Khối đơn thể mô-đun hóa (`Modular Monolith`) thay cho Microservices (`ADR-001`):
>
> - **Đảm bảo tính nguyên tử ACID tuyệt đối:** Toàn bộ các phép ghi liên phân hệ được thực hiện một cách an toàn trong một khối giao dịch PostgreSQL duy nhất (`Serializable`), giúp loại bỏ hoàn toàn rủi ro sai lệch dữ liệu phân tán.
> - **Ranh giới mô-đun tường minh:** Mã nguồn Backend được phân tách theo 9 mô-đun nghiệp vụ độc lập, qua đó nâng cao tính dễ bảo trì và mở rộng của hệ thống.
> - **Tách lớp trạng thái ở Frontend:** Phía trình duyệt sử dụng React 19 kết hợp Zustand và TanStack Query nhằm tối ưu hóa hiệu năng và mang lại trải nghiệm mượt mà cho người dùng.

**Các điểm cần sửa:** Ba gạch đầu dòng có đầu mục in đậm đóng khuôn, bị động máy móc (*"được thực hiện..."*, *"được phân tách..."*), cụm *"một cách an toàn"*, *"mang lại trải nghiệm mượt mà"* sáo rỗng, đuôi *"qua đó nâng cao..."*.

### Sau (viết thành văn xuôi liền mạch, giải thích đánh đổi rõ ràng)

> Theo quyết định kiến trúc `ADR-001`, Backend chọn mô hình khối đơn thể mô-đun hóa (`Modular Monolith`) thay vì tách thành nhiều dịch vụ nhỏ (`Microservices`). Lý do chính nằm ở đặc thù giao dịch chéo bảng của bài toán tuyển dụng. Một thao tác chấp nhận Offer phải đồng thời đổi trạng thái Offer sang `ACCEPTED`, chốt hồ sơ thành `HIRED` và ghi bản ghi vào `audit_logs`; đặt toàn bộ trong một tiến trình `Node.js / Express 5` dùng chung giao dịch `Serializable` của PostgreSQL giúp tránh độ phức tạp của giao dịch phân tán hai pha.
>
> Bên trong tiến trình đơn thể đó, mã nguồn vẫn chia thành 9 mô-đun độc lập tại `backend/src/modules/` theo cấu trúc kiểm định đầu vào, dịch vụ nghiệp vụ và truy vấn dữ liệu. Ở phía trình duyệt, ứng dụng đơn trang `React 19` dùng `Zustand` cho trạng thái xác thực và `TanStack Query` để đồng bộ bộ nhớ đệm API qua chuẩn `/api`.

---

## Mẫu 3. Mô tả cơ chế nghiệp vụ và xử lý đồng thời (khử dịch máy)

### Trước (nặng cấu trúc dịch từ tiếng Anh, nhiều "việc" và "được")

> Việc ngăn chặn ghi đè dữ liệu trong quá trình chuyển vòng được thực hiện bởi cơ chế khóa lạc quan (`Optimistic Concurrency`) thông qua trường `revision`. Khi yêu cầu chuyển vòng được gửi lên máy chủ một cách đồng thời bởi hai nhân sự HR cùng đang giữ phiên bản `revision = 0`, giao dịch đầu tiên sẽ được xác nhận thành công và tăng giá trị phiên bản lên `1`. Trong khi đó, yêu cầu thứ hai sẽ bị hệ thống từ chối với mã lỗi `409 Conflict`, góp phần bảo vệ tính toàn vẹn dữ liệu một cách tối ưu.

**Các điểm cần sửa:** Mở đầu bằng *"Việc..."*, lặp chuỗi *"được thực hiện bởi"*, *"được gửi lên... bởi"*, hai cụm *"một cách"*, kết câu rỗng *"góp phần bảo vệ... tối ưu"*.

### Sau (chủ động theo chủ thể kỹ thuật, câu ngắn gọn, đúng cơ chế)

> Mỗi hồ sơ ứng tuyển lưu thêm cột `revision` để kiểm soát tranh chấp khi hai nhân sự HR cùng thao tác trên bảng Kanban. Giả sử cả hai phiên làm việc cùng đọc hồ sơ tại `revision = 0` rồi bấm chuyển vòng gần như cùng lúc, yêu cầu đến trước khớp điều kiện cập nhật và đẩy `revision` lên `1`. Yêu cầu đến sau vẫn gửi kèm `expected_revision = 0` nên truy vấn cập nhật không khớp bản ghi nào, máy chủ trả về `409 Conflict` để giao diện tải lại trạng thái mới nhất.

---

## Mẫu 4. Dẫn bảng biểu và hình vẽ trong văn bản

### Trước (dùng dấu `—`, thiếu liên kết rõ với hình và viết hoa tiêu đề kiểu tiếng Anh)

> ### 4.3.1. Kết Quả Kiểm Chứng Hệ Thống Giao Diện Và Minh Họa Thực Tế
>
> Dưới đây là các hình ảnh vận hành thực tế của hệ thống — bao gồm bảng điều khiển KPI vận hành theo múi giờ Việt Nam và trình xem nhật ký hệ thống dành cho quản trị viên.
>
> ![Hình 4.9a. Dashboard KPI](/path/to/img.png)
>
> *Bảng thống kê ca kiểm thử*
>
> | Hạng mục | Kết quả |
> | --- | --- |
> | Dashboard KPI | Đạt — 9/9 ca E2E |

**Các điểm cần sửa:** Viết hoa đầu mọi từ ở tiêu đề (`Title Case`), dấu `—` chêm giữa câu và trong ô bảng, tên bảng đặt không đúng chuẩn đánh số (`Bảng X.Y. ...`), đoạn văn không nhắc đích danh `Hình 4.9a`.

### Sau (đúng quy chuẩn tiếng Việt, có câu dẫn và không dùng `—`)

> ### 4.3.1. Kết quả kiểm chứng giao diện và minh họa vận hành thực tế
>
> `Hình 4.9a` minh họa bảng điều khiển KPI tại đường dẫn `/dashboards/home`, thống kê năm chỉ số theo múi giờ `Asia/Ho_Chi_Minh` và tách dữ liệu theo phạm vi từng vai trò. Kết quả thực thi bộ kiểm thử E2E trên trình duyệt Chrome cho phân hệ này và các phân hệ còn lại được tổng hợp trong `Bảng 4.6`.
>
> ![Hình 4.9a. Bảng điều khiển KPI vận hành theo múi giờ Asia/Ho_Chi_Minh](../screenshots/bao-cao/hinh-4-9a-dashboard-kpi.png)
>
> *Hình 4.9a. Bảng điều khiển KPI vận hành theo múi giờ `Asia/Ho_Chi_Minh`.*
>
> *Bảng 4.6. Tổng hợp kết quả chạy kiểm thử tự động*
>
> | Hạng mục kiểm thử | Kết quả ghi nhận |
> | --- | --- |
> | Playwright E2E: Dashboard KPI | Đạt `9/9` ca (`1,2 phút`) |

---

## Mẫu 5. Đánh giá kết quả, hạn chế và hướng phát triển

### Trước (chỉ khen một chiều, 4 ý liệt kê dài đều nhau kiểu tài liệu quảng cáo)

> Hệ thống RMS đã đạt được những kết quả nổi bật:
>
> - **Tính nhất quán xuyên suốt:** Đảm bảo sự đồng bộ chặt chẽ từ phân tích thiết kế đến mã nguồn cài đặt và kiểm thử tự động trên cơ sở dữ liệu thật.
> - **Bảo vệ tính đúng đắn dữ liệu ở mức cao:** Giải quyết trực diện các tình huống tranh chấp điển hình trong nghiệp vụ tuyển dụng.
> - **Giao diện tối giản hiện đại:** Đáp ứng chuẩn tiếp cận và tách rõ luồng nghiệp vụ theo từng vai trò.
>
> **Hướng phát triển:**
> 1. **Thư viện mẫu quy trình chuẩn:** Cho phép HR lưu trữ và áp dụng nhanh bộ tiêu chí đánh giá, giúp tiết kiệm thời gian vận hành.
> 2. **Trung tâm thông báo đa kênh:** Tích hợp gửi thông báo email và đồng bộ lịch Google Calendar để nâng cao trải nghiệm hội đồng phỏng vấn.
> 3. **Phân tích dữ liệu nâng cao:** Bổ sung biểu đồ xu hướng dài hạn nhằm hỗ trợ Ban lãnh đạo ra quyết định chiến lược.

**Các điểm cần sửa:** Chỉ có khen mà thiếu phần hạn chế thật của đồ án; ba gạch đầu dòng đánh giá mở đầu bằng khung in đậm giống hệt nhau; phần hướng phát triển lặp mô típ "tên tính năng -> giúp/nhằm nâng cao/hỗ trợ..." rất đặc trưng của LLM.

### Sau (viết liền mạch, nêu rõ phần đạt được, điểm còn thiếu và việc cần làm tiếp)

> So với bốn mục tiêu đặt ra ở Chương 1 (`Bảng 4.8`), bản cài đặt hiện tại đáp ứng trọn vẹn luồng nghiệp vụ từ tạo đợt tuyển, nhận hồ sơ, điều phối Kanban, chấm điểm phỏng vấn đến phát hành Offer và ghi vết kiểm toán. Toàn bộ 11 bộ kiểm thử tích hợp API với PostgreSQL 16 và 40 ca Playwright E2E đều chạy qua trên môi trường cục bộ mà không bỏ qua khẳng định nào.
>
> Dù vậy, bản cài đặt vẫn còn những giới hạn rõ rệt khi xét khả năng vận hành ở quy mô lớn hơn. Tệp CV hiện lưu trực tiếp trên ổ đĩa máy chủ ứng dụng (`uploads/cvs/`) và thư xác minh được gửi đồng bộ ngay trong request chính qua SMTP; cách làm này gọn khi chạy trên một máy chủ đơn lẻ nhưng sẽ thành điểm nghẽn nếu mở rộng nhiều thực thể Backend hoặc khi máy chủ mail phản hồi chậm. Ngoài ra, giao diện Dashboard mới dừng ở thống kê trong ngày và tổng định biên, chưa tính được các chỉ số theo chuỗi thời gian như thời gian tuyển trung bình theo phòng ban hay tỷ lệ chuyển đổi qua từng vòng.
>
> Vì thế, hướng mở rộng tiếp theo tập trung trước hết vào hạ tầng lưu trữ và tác vụ nền: tách tệp CV sang kho đối tượng tương thích S3 (`MinIO`) kèm liên kết tải có thời hạn, đồng thời đưa tác vụ gửi email vào hàng đợi bất đồng bộ để có thể thử lại khi lỗi mạng. Khi lượng dữ liệu lịch sử đủ lớn, phân hệ Dashboard sẽ bổ sung biểu đồ xu hướng và bộ mẫu quy trình vòng tuyển dùng lại cho các đợt tương tự.
