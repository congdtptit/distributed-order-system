<!-- Sinh tự động bởi backend/scripts/report_perf.py từ perf/results/ (bin/perf). Không sửa tay. -->

Lần chạy: 22/11/2026 12:39, Apache JMeter 5.6.3, Docker với 4 CPU và 5.8 GiB bộ nhớ, thuộc tính: mặc định (users=250, rampup=1, loops=1).

##### Thời gian đáp ứng theo chức năng

| Chức năng (API) | Số yêu cầu | Lỗi | Trung bình (ms) | Nhỏ nhất (ms) | Trung vị (ms) | 95% (ms) | Lớn nhất (ms) | Thông lượng (yêu cầu/giây) |
|---|---|---|---|---|---|---|---|---|
| `POST /orders` | 250 | 0 (0,00 %) | 2.499 | 281 | 2.989 | 3.240 | 3.337 | 54,8 |
| `GET /dishes` | 250 | 0 (0,00 %) | 182 | 10 | 110 | 359 | 381 | 92,8 |
| `GET /orders` | 250 | 0 (0,00 %) | 736 | 29 | 754 | 1.432 | 1.465 | 78,4 |
| `GET /tickets` | 250 | 0 (0,00 %) | 1.191 | 64 | 1.282 | 1.495 | 1.527 | 96,4 |
| `GET /stock` | 250 | 0 (0,00 %) | 243 | 34 | 266 | 353 | 375 | 195,2 |
| `GET /reports/summary` | 250 | 0 (0,00 %) | 124 | 7 | 116 | 221 | 236 | 207,6 |
| **Tổng** | 1500 | 0 (0,00 %) | 829 | 7 | 318 | 3.177 | 3.337 | 96,3 |

Một yêu cầu bị tính là lỗi khi dịch vụ trả mã HTTP 4xx, 5xx hoặc không trả lời trong 60 giây. Cột 95 % là thời gian mà 95 % số yêu cầu không vượt quá.

##### Thời gian từ lúc tạo đơn tới khi chi nhánh thấy Đã giữ

30 đơn tạo lần lượt ở POS01 sau khi chạy tải (`DA_GIU` 30); mỗi đơn được hỏi lại mỗi 20 ms. Đơn đi trọn đường: hàng chờ gửi, Kafka, Kho, rồi `status-events.POS01` về chi nhánh.

| Nhỏ nhất (ms) | Trung bình (ms) | Trung vị (ms) | 95% (ms) | Lớn nhất (ms) |
|---|---|---|---|---|
| 189 | 264 | 224 | 410 | 434 |

##### Tài nguyên trong lúc chạy tải

Giá trị cao nhất mà `docker stats` ghi được trong lúc chạy tải. CPU 100 % là trọn một nhân.

| Container | CPU cao nhất (%) | Bộ nhớ cao nhất (MiB) |
|---|---|---|
| `jmeter (bộ tạo tải)` | 200,2 | 239 |
| `inventory-2` | 82,7 | 90 |
| `kafka2` | 75,3 | 408 |
| `kafka1` | 63,4 | 382 |
| `kafka3` | 58,3 | 372 |
| `query` | 54,8 | 87 |
| `kitchen` | 42,7 | 95 |
| `pos01` | 42,6 | 93 |
| `pos02` | 18,0 | 87 |
| `inventory-1` | 17,3 | 94 |
| `inventory-db` | 16,1 | 53 |
| `pos01-db` | 16,1 | 56 |
| `online` | 15,8 | 89 |
| `frontend` | 15,5 | 947 |
| `kitchen-db` | 15,2 | 50 |
| `online-db` | 10,8 | 31 |
| `pos02-db` | 9,9 | 35 |
| `kafka-ui` | 9,6 | 361 |
| `test-db` | 9,6 | 69 |
| `central-db` | 7,5 | 50 |
| `tools` | 0,0 | 1 |
| `adminer` | 0,0 | 18 |
| **Cả cụm** (tổng bộ nhớ tại một thời điểm) | | 3.599 |
