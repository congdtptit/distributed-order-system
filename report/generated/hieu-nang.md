<!-- Sinh tự động bởi backend/scripts/report_perf.py từ perf/results/ (bin/perf). Không sửa tay. -->

Lần chạy: 22/11/2026 12:11, Apache JMeter 5.6.3, Docker với 4 CPU và 5.8 GiB bộ nhớ, thuộc tính: mặc định (users=250, rampup=1, loops=1).

##### Thời gian đáp ứng theo chức năng

| Chức năng (API) | Số yêu cầu | Lỗi | Trung bình (ms) | Nhỏ nhất (ms) | Trung vị (ms) | 95% (ms) | Lớn nhất (ms) | Thông lượng (yêu cầu/giây) |
|---|---|---|---|---|---|---|---|---|
| `POST /orders` | 250 | 0 (0,00 %) | 1.603 | 286 | 1.603 | 2.981 | 3.069 | 66,0 |
| `GET /dishes` | 250 | 0 (0,00 %) | 613 | 25 | 788 | 884 | 918 | 113,7 |
| `GET /orders` | 250 | 0 (0,00 %) | 1.684 | 65 | 1.652 | 2.971 | 3.079 | 61,7 |
| `GET /tickets` | 250 | 0 (0,00 %) | 4.603 | 141 | 4.744 | 8.278 | 8.485 | 26,4 |
| `GET /stock` | 250 | 0 (0,00 %) | 262 | 36 | 244 | 362 | 380 | 193,2 |
| `GET /reports/summary` | 250 | 0 (0,00 %) | 476 | 47 | 567 | 613 | 627 | 160,1 |
| **Tổng** | 1500 | 0 (0,00 %) | 1.540 | 25 | 824 | 6.397 | 8.485 | 66,9 |

Một yêu cầu bị tính là lỗi khi dịch vụ trả mã HTTP 4xx, 5xx hoặc không trả lời trong 60 giây. Cột 95 % là thời gian mà 95 % số yêu cầu không vượt quá.

##### Thời gian từ lúc tạo đơn tới khi chi nhánh thấy Đã giữ

30 đơn tạo lần lượt ở POS01 sau khi chạy tải (`DA_GIU` 30); mỗi đơn được hỏi lại mỗi 20 ms. Đơn đi trọn đường: hàng chờ gửi, Kafka, Kho, rồi `status-events.POS01` về chi nhánh.

| Nhỏ nhất (ms) | Trung bình (ms) | Trung vị (ms) | 95% (ms) | Lớn nhất (ms) |
|---|---|---|---|---|
| 136 | 218 | 206 | 229 | 382 |

##### Tài nguyên trong lúc chạy tải

Giá trị cao nhất mà `docker stats` ghi được trong lúc chạy tải. CPU 100 % là trọn một nhân.

| Container | CPU cao nhất (%) | Bộ nhớ cao nhất (MiB) |
|---|---|---|
| `jmeter (bộ tạo tải)` | 171,4 | 318 |
| `pos01-db` | 138,8 | 51 |
| `kitchen` | 119,7 | 108 |
| `pos01` | 74,7 | 106 |
| `query` | 54,1 | 92 |
| `inventory-2` | 49,9 | 89 |
| `kafka1` | 34,5 | 401 |
| `kafka2` | 32,4 | 398 |
| `kafka3` | 29,7 | 401 |
| `inventory-1` | 27,9 | 95 |
| `inventory-db` | 25,0 | 48 |
| `pos02` | 20,4 | 95 |
| `online` | 18,4 | 86 |
| `kitchen-db` | 15,4 | 37 |
| `frontend` | 14,9 | 234 |
| `central-db` | 10,1 | 40 |
| `test-db` | 7,7 | 136 |
| `online-db` | 7,6 | 15 |
| `pos02-db` | 7,1 | 25 |
| `kafka-ui` | 0,1 | 320 |
| `tools` | 0,0 | 53 |
| `adminer` | 0,0 | 1 |
| **Cả cụm** (tổng bộ nhớ tại một thời điểm) | | 3.090 |
