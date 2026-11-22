# Bảng tổng hợp dấu hiệu văn AI và lỗi diễn đạt trong báo cáo tiếng Việt

Tài liệu này tổng hợp các mẫu dấu hiệu văn bản do mô hình ngôn ngữ lớn (LLM) tạo ra từ cẩm nang [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing), [Signs of AI writing/Style](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing/Style), [Manual of Style/Lists](https://en.wikipedia.org/wiki/Wikipedia:Manual_of_Style/Lists), danh mục [Tropes](https://tropes.fyi/directory), kết hợp với chuẩn trình bày báo cáo kỹ thuật và biên tập khử dịch máy (*post-editing*) tiếng Việt.

## 1. Dấu hiệu về giọng điệu và nội dung

Các LLM thường được tinh chỉnh để chiều lòng người đọc nên văn phong hay đứng từ bên ngoài bình luận vĩ mô, thổi phồng ý nghĩa và né tránh nêu nhược điểm thật.

| Nhóm dấu hiệu | Biểu hiện thường gặp bằng tiếng Việt | Nguyên nhân gây "mùi AI" | Cách sửa về giọng kỹ thuật khách quan |
| --- | --- | --- | --- |
| **Thổi phồng tầm quan trọng (*Puffery*)** | *"trong kỷ nguyên chuyển đổi số bùng nổ"*, *"đóng vai trò xương sống"*, *"bước chuyển mình mạnh mẽ"*, *"minh chứng rõ nét"*, *"khẳng định tính ưu việt"* | Phóng đại một hệ thống đồ án môn học thành sản phẩm tầm vóc ngành. | Cắt toàn bộ tính từ khen ngợi. Mô tả trực tiếp phạm vi bài toán, số bảng dữ liệu, số vai trò và thao tác xử lý được. |
| **Phân tích hời hợt ở đuôi câu (*Superficial analyses*)** | Kết câu bằng *"...nhằm góp phần nâng cao hiệu quả"*, *"...tạo nền tảng vững chắc cho"*, *"...phản ánh xu hướng hiện đại"*, *"...giải quyết trực diện bài toán"* | Bắt chước đuôi phân từ `-ing` (*highlighting..., underscoring...*) trong tiếng Anh mà không thêm thông tin kỹ thuật nào. | Dừng câu ngay tại kết quả hoặc cơ chế thực tế. Nếu nêu hệ quả, chỉ ra đúng thay đổi kỹ thuật (ví dụ: tránh ghi đè dữ liệu nhờ kiểm tra `revision`). |
| **Dẫn nhập và kết luận rập khuôn (*Preamble / Fractal summaries*)** | Mở đầu mục bằng *"Trong phần này, báo cáo sẽ trình bày..."*; kết bằng *"Tóm lại, qua các bước trên có thể thấy..."*, *"Với cấu trúc chặt chẽ, hệ thống sẵn sàng đáp ứng..."* | Nhắc lại cấu trúc bài theo khuôn mẫu "nói sắp làm gì -> làm -> tổng kết vừa làm gì". | Bắt đầu thẳng vào nội dung kỹ thuật của mục. Đoạn cuối mục nên dẫn sang mục/bảng kế tiếp hoặc nêu hạn chế thực tế nếu là cuối chương. |
| **Công thức "Mặc dù... nhưng..." (*Challenges & Future Prospects*)** | *"Mặc dù đạt được nhiều kết quả khả quan, hệ thống vẫn đối mặt với một số thách thức... Tuy nhiên, với nền tảng hiện có, hệ thống hứa hẹn..."* | Khuôn tổng kết lạc quan giả tạo, tự xóa nhẹ nhược điểm vừa nêu. | Tách rõ phần làm được và phần chưa làm được. Nêu thẳng giới hạn (chưa có Redis, chưa gửi mail thật qua hàng đợi, thiếu kiểm thử tải) và hướng làm tiếp ở bản sau. |
| **Quy kết mơ hồ (*Weasel wording*)** | *"nhiều chuyên gia đánh giá"*, *"các nghiên cứu chỉ ra rằng"*, *"người dùng thường gặp khó khăn"* (không kèm dẫn chứng hoặc khảo sát) | Phóng đại độ phổ quát của nhận định thiếu nguồn kiểm chứng. | Gắn đúng ngữ cảnh khảo sát của đề tài hoặc quy tắc nghiệp vụ cụ thể thay vì mượn danh "nhiều nghiên cứu". |
| **Giọng giảng giải hoặc giao tiếp thừa** | *"Có thể hình dung như một..."*, *"Cần lưu ý rằng..."*, *"Điều thú vị là..."*, hoặc sót lời chat *"Dưới đây là..."*, *"Hy vọng phần này hữu ích"* | Giọng trợ lý đang trò chuyện trực tiếp với người dùng thay vì văn bản lưu trữ. | Xóa toàn bộ lời chào, cụm dẫn cảm tính và ví von phổ thông; dùng câu trần thuật ngắn gọn. |

## 2. Dấu hiệu về cấu trúc câu và nhịp văn

Văn bản do LLM sinh ra thường đều tăm tắp về nhịp điệu, câu nào cũng dài tương đương nhau và lặp lại một số khuôn đối xứng đặc trưng.

| Mẫu câu cần tránh | Ví dụ điển hình | Vì sao dễ nhận ra | Cách viết lại tự nhiên |
| --- | --- | --- | --- |
| **Đối lập phủ định (*Negative parallelism*)** | *"Hệ thống không chỉ lưu trữ CV, mà còn chuẩn hóa luồng phê duyệt."* / *"Đây không phải lỗi giao diện, mà là chốt chặn nghiệp vụ."* | Khung *"Not only... but also..."* và *"Not X, it's Y"* là dấu hiệu tần suất cao nhất của văn AI. | Nêu thẳng cả hai chức năng hoặc nguyên nhân: *"Hệ thống lưu bản chụp CV theo từng đơn và áp dụng quy tắc khóa vòng trước khi phê duyệt."* |
| **Quy tắc bộ ba (*Rule of three*)** | *"nhanh chóng, an toàn và hiệu quả"*, *"rõ ràng, minh bạch, nhất quán"*, *"từ lược đồ dữ liệu, tầng API đến giao diện người dùng"* | Ép ba tính từ hoặc ba cụm song song liên tiếp để tạo cảm giác bao quát. | Chỉ giữ những ý có thật; nếu cần nêu 2 điểm thì dừng ở 2, nếu 4 ý thì tách rõ 4, không gọt hay độn thêm cho đủ 3. |
| **Xoay vòng từ đồng nghĩa (*Synonym cycling*)** | Cùng một đối tượng trong 1 đoạn lúc gọi là *bảng điều khiển*, câu sau đổi thành *cổng thông tin*, câu nữa gọi là *trung tâm phân tích* | Cơ chế tránh lặp từ khiến mô hình đổi tên gọi của cùng một thực thể kỹ thuật. | Giữ cố định một thuật ngữ khớp với `Bảng từ viết tắt` và nhãn trên giao diện trong toàn bộ báo cáo. |
| **Đoạn văn dài đều và liệt kê đội lốt văn xuôi (*Enumerated prose & Compulsive counting*)** | Mở đầu đoạn bằng *"Có ba vấn đề chính..."* rồi các câu nối tiếp nhau đúng khuôn *"Thứ nhất, ... Thứ hai, ... Thứ ba, ..."*; hoặc mọi đoạn đều dài 4–5 dòng | Chỉ là danh sách được kéo thành văn xuôi khi mô hình bị cấm dùng gạch đầu dòng; độ biến thiên độ dài câu/đoạn thấp | Xen câu ngắn 10–15 chữ để chốt ý sau đoạn giải thích dài; gộp ý liên quan theo mạch nhân quả thay vì đếm *"Thứ nhất, Thứ hai, Thứ ba"* máy móc |
| **Động từ làm sang thay cho "là / có" (*Avoidance of copulatives*)** | *đóng vai trò như một*, *đại diện cho một bước tiến*, *sở hữu khả năng*, *cung cấp trải nghiệm* | Né từ đơn giản (*là, có, gồm, dùng*) để câu nghe giống văn tiếp thị. | Dùng lại động từ trực tiếp: *"Bảng `audit_logs` lưu...", "Phân hệ này gồm bốn API..."*. |
| **Khoảng giả (*False ranges*)** | *"từ khâu lên ý tưởng đến triển khai thực tế và định hướng tương lai"* | Cấu trúc *"from X to Y"* ghép các khái niệm không nằm trên một thang đo thống nhất. | Liệt kê đúng trình tự giai đoạn thật hoặc viết thành câu mô tả quy trình rõ ràng. |

## 3. Dấu hiệu định dạng và ký hiệu trình bày

Đây là nhóm lỗi trực quan dễ thấy nhất khi đọc lướt tài liệu Markdown hoặc file Word xuất từ AI.

1. **Danh sách dọc có tiêu đề in đậm (*Inline-header vertical lists*):** Lạm dụng mẫu `- **Tên ý:** giải thích một hai câu.` cho phần lớn nội dung chương. Trong báo cáo kỹ thuật, văn xuôi liền đoạn giúp lập luận nối tiếp mạch lạc hơn; chỉ dùng gạch đầu dòng khi liệt kê các bước tuần tự bắt buộc, danh sách tham số/điều kiện kiểm tra ngắn, hoặc tách sang bảng khi mỗi mục có nhiều thuộc tính so sánh.
2. **Dấu gạch ngang dài (`—`) để chêm câu:** Không dùng `—` nối cụm giải thích giữa câu (ví dụ *"hệ thống — vốn thiết kế theo lớp — cho phép..."*) hay ghép cặp tên trong ô kết quả (`Đạt — 9/9`). Dùng dấu phẩy, dấu hai chấm hoặc ngoặc đơn; riêng dải số viết bằng gạch nối ngắn (`–`), ví dụ `Tuần 1–2` hoặc `1–5`.
3. **In đậm dày đặc giữa đoạn văn:** Chỉ in đậm tên thực thể nhấn mạnh lần đầu, tiêu đề bảng/hình hoặc các cột khóa trong bảng tổng hợp. Không bôi đậm hàng loạt cụm từ khóa ở giữa mỗi câu như bài tóm tắt slide.
4. **Viết hoa tiêu đề kiểu Title Case tiếng Anh:** Không viết hoa chữ cái đầu của mọi từ trong tiểu mục (sai: *`2.1. Thiết Kế Kiến Trúc Tổng Thể Hệ Thống`*). Tiếng Việt chuẩn học thuật chỉ viết hoa chữ đầu tiêu đề và các danh từ riêng hoặc ký hiệu viết tắt (đúng: *`2.1. Thiết kế kiến trúc tổng thể hệ thống RMS`*), không có dấu chấm ở cuối tiêu đề.
5. **Ký hiệu trang trí thừa và lỗi rò cú pháp:** Không đặt emoji ở đầu tiêu đề hoặc đầu dòng trong báo cáo nộp. Chuyển dấu ngoặc kép cong (`“ ”`) hoặc nháy đơn cong về một kiểu thống nhất (trong Markdown ưu tiên `"` thẳng để đồng bộ code block và bảng biểu, trừ khi xuất sang Word tự động chuẩn hóa). Tuyệt đối rà xóa các chỗ trống mẫu còn sót như `[Tên ...]`, `202X-XX-XX`, `example.com/...` hay tham số `?utm_source=...` trong liên kết.

## 4. Lỗi dịch máy tiếng Việt (*Translationese*) trong văn bản kỹ thuật

Ngay cả khi không dùng cụm từ sáo rỗng tiếng Anh, bản nháp tiếng Việt sinh bởi LLM vẫn thường mang cấu trúc ngữ pháp của câu tiếng Anh dịch thẳng:

| Dạng lỗi | Câu còn "mùi dịch" | Câu sửa gọn theo tiếng Việt tự nhiên |
| --- | --- | --- |
| **Lạm dụng *"một cách"* + tính từ** (dịch đuôi `-ly`) | *"Yêu cầu được xử lý một cách nhanh chóng và một cách tuần tự."* | *"Yêu cầu được xử lý tuần tự theo hàng đợi."* hoặc *"Hệ thống xử lý tuần tự từng yêu cầu."* |
| **Lạm dụng *"việc"* trước động từ** (dịch *gerund `-ing`*) | *"Việc phân tách các mô-đun giúp việc bảo trì trở nên dễ dàng hơn."* | *"Tách riêng từng mô-đun giúp mã nguồn dễ bảo trì hơn."* |
| **Bị động máy móc *"được / bị ... bởi"*** | *"Bản ghi lịch sử được tạo bởi hàm dịch vụ sau khi giao dịch được xác nhận."* | *"Hàm dịch vụ tạo bản ghi lịch sử ngay trong cùng giao dịch."* |
| **Định ngữ lồng quá dài trước danh từ** | *"Một cơ chế kiểm soát tính đồng thời ở mức giao dịch cô lập cao có khả năng ngăn chặn tranh chấp dữ liệu..."* | Tách thành hai vế ngắn: *"Cơ chế khóa ở mức cô lập `Serializable` ngăn ghi đè dữ liệu khi nhiều yêu cầu chạy cùng lúc."* |
| **Lạm dụng đại từ và từ nối đầu câu lặp** | Mở 3 câu liên tiếp bằng *"Ngoài ra, ..."*, *"Bên cạnh đó, ..."*, *"Tuy nhiên, ..."*, hoặc lặp *"Điều này giúp..."* | Nối trực tiếp bằng quan hệ nhân quả hoặc chủ ngữ cụ thể thay vì gài từ chuyển ý máy móc ở đầu mọi câu. |
| **Chêm tiếng Anh thừa sau cụm tiếng Việt đã đủ nghĩa** | *"Từ điển dữ liệu (`Data Dictionary`)"*, *"nguồn lưu trữ tập trung (`single source of truth`)"*, *"Điều kiện (`Conditions`)"*, *"Ngăn xếp công nghệ (`Tech Stack`)"*, *"thời gian tuyển trung bình (`Time-to-Hire`)"* | *"Từ điển dữ liệu"*, *"nguồn lưu trữ tập trung"*, *"Điều kiện"*, *"Ngăn xếp công nghệ"*, *"thời gian tuyển dụng trung bình"* (chỉ giữ định danh mã nguồn, mã chuẩn `ERD`/`DFD`/`RBAC`/`REST API` và chú thích thuật ngữ chuyên ngành tối đa một lần lúc giải thích ban đầu). |

## 5. Quy chuẩn hình thức đặc thù của báo cáo đồ án CNTT Việt Nam

- **Vị trí nhãn Bảng và Hình:** Tên bảng luôn đặt **phía trên** bảng (`Bảng 3.1. Mô tả các trường...`); tên hình vẽ, sơ đồ, ảnh chụp màn hình luôn đặt **phía dưới** hình (`Hình 4.5. Giao diện trang tuyển dụng công khai`).
- **Liên kết giữa lời văn và minh họa:** Không đặt bảng hay hình đứng trơ trọi giữa chương. Trong đoạn văn ngay trước (hoặc ngay sau) phải gọi tên rõ ràng, ví dụ: *"Cấu trúc xử lý ba lớp thể hiện ở Hình 3.3."* hoặc *"Kết quả chạy kiểm thử E2E tổng hợp tại Bảng 4.6."*
- **Định lượng hóa nhận xét:** Thay các đánh giá cảm tính (*nhanh, tối ưu, độ tin cậy cao, đầy đủ*) bằng thông số xác thực được từ mã nguồn hoặc kiểm thử (*thời gian đóng gói production `27,99s` với `1.889` module, đạt `40/40` ca E2E trên Chrome, giới hạn tệp CV `≤ 5 MB`*).
- **Ranh giới giữa khách quan kỹ thuật và người thực hiện:** Dùng câu chủ động lấy phân hệ/thuật toán làm chủ ngữ (*"Phân hệ phỏng vấn kiểm tra..."*), hoặc câu khuyết chủ ngữ khi mô tả thao tác triển khai (*"Khởi chạy đồng thời máy chủ API và cơ sở dữ liệu kiểm thử..."*). Tránh *"tôi / chúng tôi / em"* trong toàn bộ thân bài; nếu cần nói về quyết định thiết kế của tập thể, dùng gọn cụm *nhóm thực hiện* với tần suất thấp.
