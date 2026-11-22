---
name: vietnamese-tech-report-writing
description: >-
  Guides drafting, reviewing, and rewriting Vietnamese IT project reports,
  graduation theses, and technical documentation in an objective, natural
  engineering tone. Use when writing or polishing Vietnamese report chapters
  (such as `report/` or `docs/bao-cao/`), stripping AI writing tells (bulleted bold-header
  lists, em dashes, negative parallelisms, puffery, translationese, uniform
  paragraph cadence), or checking thesis formatting conventions.
---

# Hướng dẫn văn phong báo cáo kỹ thuật CNTT tiếng Việt

Kỹ năng này chuẩn hóa cách viết và biên tập lại báo cáo bài tập lớn, đồ án môn học, khóa luận tốt nghiệp và tài liệu kỹ thuật bằng tiếng Việt. Mục tiêu là thay thế giọng văn AI (đứng ngoài phân tích, sáo rỗng, chia ý vụn bằng dấu gạch đầu dòng và nhịp câu đều nhau) bằng văn phong kỹ thuật khách quan, gọn chữ và sát với quá trình xây dựng hệ thống thật.

## 1. Giọng văn và ngôi xưng chuẩn

- **Ưu tiên diễn đạt khách quan, tránh đại từ cá nhân:** Không dùng *tôi, chúng tôi, em, bọn em, mình*. Thay bằng chủ thể kỹ thuật gắn trực tiếp với đối tượng xử lý (*hệ thống, phân hệ, lược đồ, API, bộ kiểm thử, tài liệu*) hoặc câu khuyết chủ ngữ tự nhiên trong tiếng Việt (*"Tách dữ liệu vị trí khỏi đợt tuyển...", "Khóa cấu trúc vòng ngay khi đợt chuyển sang trạng thái mở..."*).
- **Giữ góc nhìn của người làm thực tế:** Trình bày bài toán gặp phải, lý do chọn giải pháp kỹ thuật, cơ chế vận hành trong mã nguồn và bằng chứng kiểm chứng thực tế đáp ứng yêu cầu đề bài. Không đứng từ bên ngoài bình luận vĩ mô, không ca ngợi sáo rỗng, và không tự liệt kê nhược điểm hay thiếu sót ngoài phạm vi mẫu báo cáo yêu cầu.
- **Tránh lặp tên nhóm thực hiện:** Chỉ dùng cụm trung tính như *nhóm thực hiện* hoặc *báo cáo* ở những chỗ bắt buộc nêu bối cảnh khảo sát hoặc phân công công việc, không mở đầu đoạn nào cũng bằng *"Nhóm chúng tôi đã..."* hay *"Nhóm tiến hành..."*.

## 2. Sáu nguyên tắc bắt buộc khi viết và sửa

1. **Bảo toàn sự thật kỹ thuật:** Giữ nguyên toàn bộ số liệu đo được, mã quy tắc (`FR`, `BR`, `ADR`, `TC`), tên bảng, tên cột, tên đường dẫn, kết quả chạy lệnh và các đường dẫn ảnh/tệp. Không tự thêm định lượng kiểu *"giảm 80% thời gian"* nếu báo cáo không có phép đo thật.
2. **Viết thành đoạn văn xuôi, bỏ danh sách in đậm vụn:** Các đoạn phân tích nguyên nhân, giải thích kiến trúc, nhận xét kết quả và hạn chế phải viết liền mạch thành đoạn văn. Hạn chế tối đa dạng `- **Tiêu đề in đậm:** một hai câu giải thích`. Chỉ dùng danh sách gạch đầu dòng hoặc đánh số khi liệt kê các bước tuần tự bắt buộc hoặc tập tham số ngắn khó ghép vào câu văn; nếu mỗi mục có từ hai chiều thông tin trở lên thì lập bảng.
3. **Bỏ dấu gạch ngang dài (`—`) và cấu trúc đối xứng sáo:** Không dùng `—` trong câu văn xuôi để chêm giải thích; thay bằng dấu phẩy, dấu hai chấm, ngoặc đơn hoặc tách câu. Tránh lặp các khuôn câu kiểu *"không chỉ X, mà còn Y"*, *"không phải X, mà là Y"*, và không cố ép các ý thành bộ ba (*A, B và C*) khi thực tế chỉ có hai hoặc bốn ý.
4. **Phá nhịp đoạn văn đều tăm tắp:** Xen kẽ câu dài (diễn giải cơ chế, điều kiện rẽ nhánh) với câu ngắn (chốt nhận định hoặc chuyển sang bảng, hình vẽ). Độ dài các đoạn văn trong cùng một mục cần biến thiên tự nhiên theo lượng thông tin, không ép mỗi mục con hay mỗi đoạn dài đúng 3–4 dòng giống nhau.
5. **Khử lỗi dịch máy (*translationese*) tiếng Việt:**
   - Bỏ *"một cách"* đứng trước tính từ/trạng từ (*xử lý một cách tự động* sửa thành *xử lý tự động*).
   - Bỏ *"việc"* thừa ở đầu cụm động từ (*Việc lưu trữ riêng giúp...* sửa thành *Lưu riêng bản chụp CV giúp...*).
   - Hạn chế *"được / bị ... bởi"* theo bị động tiếng Anh (*Dữ liệu được kiểm tra bởi tầng Service* sửa thành *Tầng Service kiểm tra dữ liệu* hoặc *Dữ liệu qua bước kiểm tra tại tầng Service*).
   - Giữ nguyên định danh mã nguồn (`expected_revision`, tên bảng/API), mã quy tắc (`FR`, `BR`, `ADR`, `TC`) và thuật ngữ CNTT quen thuộc khi dịch gây tối nghĩa (`Pipeline`, `Offer`, `Snapshot`, `Rollback`, `Middleware`, `ERD`, `DFD`, `RBAC`), nhưng thống nhất một cách gọi xuyên suốt tài liệu. Tuyệt đối **không chêm tiếng Anh thừa trong ngoặc đơn** sau cụm tiếng Việt đã đủ rõ nghĩa (ví dụ không viết `Từ điển dữ liệu (Data Dictionary)`, `Ngăn xếp công nghệ (Tech Stack)`, `nguồn lưu trữ tập trung (single source of truth)` hay `Điều kiện (Conditions)`). Nếu cần dẫn thuật ngữ tiếng Anh gốc cho khái niệm học thuật cốt lõi, chỉ chú thích tối đa **một lần** tại chỗ giới thiệu đầu tiên, không lặp ở tiêu đề mục hay các bảng biểu về sau.
6. **Tuân thủ hình thức đồ án kỹ thuật Việt Nam:**
   - Tiêu đề cấp chương có thể viết hoa toàn bộ (`CHƯƠNG 1. ...`), nhưng tiêu đề tiểu mục từ cấp 2 trở xuống viết hoa chữ cái đầu câu (*Sentence case*, chỉ viết hoa thêm danh từ riêng hoặc ký hiệu viết tắt) và không có dấu chấm ở cuối tiêu đề.
   - Chú thích bảng đặt **phía trên** bảng (`Bảng X.Y. ...`); chú thích hình/sơ đồ đặt **phía dưới** hình (`Hình X.Y. ...`). Mọi bảng và hình đều phải được nhắc trực tiếp trong đoạn văn bản liền kề.
   - Phần kết luận hoặc đánh giá kết quả tập trung đối chiếu trực tiếp những gì hệ thống đã giải quyết với mục tiêu và yêu cầu đặt ra, dẫn chứng bằng cơ chế hoặc kết quả đo kiểm thực tế thay vì viết "tóm lại qua chương này" hay tự nhận thêm điểm yếu không liên quan.

## 3. Tài liệu tham chiếu chuyên sâu

Trước khi biên tập một chương dài hoặc rà soát toàn bộ báo cáo, đọc hai tài liệu tham chiếu đi kèm:

- [Bảng nhận diện dấu hiệu AI và lỗi dịch máy tiếng Việt](./references/anti-ai-patterns-vi.md): Phân loại đầy đủ các dấu hiệu nội dung, cấu trúc câu, định dạng Markdown và từ vựng dịch máy cần loại bỏ khi viết báo cáo tiếng Việt.
- [Ví dụ đối chiếu Trước và Sau cho báo cáo CNTT](./references/before-after-examples.md): Các mẫu sửa thực tế cho từng phần của đồ án (mở đầu chương, khảo sát hiện trạng, phân tích chức năng, lựa chọn kiến trúc, dẫn bảng/hình, đánh giá và đối chiếu mục tiêu).

## 4. Quy trình làm việc 4 bước

1. **Đọc khung ngữ cảnh trước khi sửa:** Kiểm tra mục tiêu chương, bảng ký hiệu viết tắt và các đoạn kề cận để giữ đồng nhất thuật ngữ và thứ tự đánh số `Hình`/`Bảng`. Nếu sửa báo cáo của một mã nguồn có sẵn, đối chiếu nhanh để chắc chắn tên tệp, thông số và chức năng nêu trong văn bản khớp với thực tế.
2. **Quét các lỗi cấu trúc lớn trước:** Xử lý ở cấp đoạn và tiểu mục trước khi sửa từng câu. Gộp các danh sách `- **...**:` không cần thiết thành đoạn văn, xóa bỏ các đoạn mở bài/kết chương rào đón kiểu sáo ngữ, kiểm tra xem phần đánh giá đã bám sát yêu cầu đối chiếu kết quả chưa.
3. **Biên tập từng câu về giọng kỹ thuật khách quan:** Loại bỏ đại từ chủ quan, xóa dấu `—`, cắt *"một cách"* / *"việc"* / bị động thừa, thay động từ mang màu sắc quảng cáo (*tối ưu vượt trội, bộc lộ đứt gãy nghiêm trọng, giải quyết trực diện*) bằng mô tả cơ chế cụ thể.
4. **Kiểm tra lại trước khi hoàn tất:** Rà nhanh theo danh sách chốt ở mục 5. Không tạo thêm ghi chú bình luận của trợ lý hay phần giải thích thừa vào nội dung tệp báo cáo.

## 5. Danh sách tự kiểm tra trước khi xuất bản

- Văn bản không còn đại từ *tôi, chúng tôi, em, mình, bạn*.
- Không còn dấu gạch ngang dài (`—`) dùng để chêm vế trong câu văn xuôi.
- Không còn chuỗi danh sách gạch đầu dòng có tiêu đề in đậm ở đầu mỗi ý dùng thay cho đoạn văn giải thích.
- Không lặp khuôn câu *"không chỉ ... mà còn ..."*, *"không phải ... mà là ..."*, và không ép liệt kê 3 vế cho mọi nhận định.
- Tiêu đề mục từ cấp 2 trở xuống viết theo chuẩn chữ cái đầu câu (*Sentence case*), tên bảng ở trên bảng, tên hình ở dưới hình và đều được dẫn tên trong bài.
- Các cụm dịch máy (*một cách + tính từ*, *việc + động từ* đầu câu, *được ... bởi*) đã được gọt gọn.
- Toàn bộ mã `FR`, `BR`, `ADR`, `TC`, số liệu kiểm thử, tên tệp và đường dẫn ảnh giữ nguyên chính xác so với bản gốc.
