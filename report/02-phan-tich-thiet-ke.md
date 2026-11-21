# PHẦN II. NGHIÊN CỨU, PHÂN TÍCH THIẾT KẾ HỆ THỐNG

## MÔ HÌNH HLD CỦA HỆ THỐNG

Hệ thống gồm các chi nhánh nhận đơn (POS tại quầy, kênh Online), một Kho dùng chung và một Bếp trung tâm. Các bên chỉ trao đổi với nhau qua Kafka; mỗi dịch vụ có CSDL riêng. Báo cáo quản lý đọc một bản sao tập trung của các CSDL đơn hàng ở chi nhánh.

```mermaid
flowchart LR
  subgraph Branches["Chi nhánh (POS01, POS02, ONLINE)"]
    UI1["Màn hình POS / Online"] --> LOS["Local Order Service<br/>(Online Order Service)"]
    LOS --- BDB[("Branch DB<br/>orders, outbox_events")]
  end
  subgraph Kafka["Kafka: 3 broker, RF=3, min.insync=2"]
    OE["order-events.&lt;branch&gt;"]
    CE["cancel-events.&lt;branch&gt;"]
    SE["status-events.&lt;branch&gt;"]
    KO["kitchen-orders"]
    SC["stock-commands"]
    ME["menu-events"]
    DLQ["dlq"]
  end
  subgraph Inventory["Kho"]
    INV["Inventory Service × 2"] --- IDB[("Inventory DB")]
  end
  subgraph Kitchen["Bếp"]
    KUI["Màn hình Bếp"] --> KIT["Kitchen Service"]
    KIT --- KDB[("Kitchen DB")]
  end
  subgraph DC["Trung tâm dữ liệu (báo cáo)"]
    REP[("Central Order Replica")] --- OQS["Order Query Service"]
    MUI["Màn hình Quản lý"] --> OQS
  end
  LOS -->|đơn mới| OE --> INV
  LOS -->|yêu cầu hủy| CE --> KIT
  INV -->|đơn đã giữ / thất bại| KO --> KIT
  KIT -->|hoàn kho / đã dùng| SC --> INV
  INV -->|cờ kiểm kho| ME --> KIT
  INV -->|trạng thái đơn| SE
  KIT -->|trạng thái đơn| SE
  SE --> LOS
  BDB -.->|logical replication| REP
```

| Thành phần | Vai trò |
|---|---|
| Local Order Service (mỗi chi nhánh POS một instance), Online Order Service | Nhận đơn và yêu cầu hủy, kể cả khi mất mạng; ghi đơn và tin cần gửi trong cùng một giao dịch vào Branch DB (outbox), gửi lên Kafka khi có mạng; áp dụng trạng thái nhận về theo thứ hạng |
| Kafka (3 broker) | Truyền mọi tin giữa các bên, at-least-once. Mỗi chi nhánh có topic riêng (`order-events`, `cancel-events`, `status-events`), cộng các topic nội bộ `kitchen-orders`, `stock-commands`, `menu-events`, `dlq` |
| Inventory Service (2 instance) và Inventory DB | Giữ nguyên liệu cho đơn hoặc trả Thất bại; hoàn kho, ghi hao hụt, ghi nhận đã dùng; cờ kiểm kho |
| Kitchen Service và Kitchen DB | Phiếu bếp; nút Bắt đầu nấu, Từ chối, Hoàn tất; bên duy nhất quyết định hủy đơn đã gửi đi |
| Central Order Replica, Order Query Service | Bản sao tập trung các bảng `orders` của chi nhánh (logical replication), phục vụ báo cáo có mốc "dữ liệu tính đến" |
| Các màn hình (`frontend`) | Chỉ gọi API của các dịch vụ, không tự suy ra trạng thái |

Các nguyên tắc chung: mỗi tin có `event_id` để chống trùng (`processed_events`); tin gửi đi được ghi vào `outbox_events` trong cùng giao dịch với thay đổi trạng thái; consumer tắt auto-commit và chỉ commit offset sau khi commit DB; tin hỏng chuyển vào `dlq` mà không chặn các đơn khác.

## I. DANH SÁCH CHỨC NĂNG PHẦN MỀM

| TT | Tên module | Tên usecase | Giao dịch (Transaction) | Tên tác nhân chính |
|---|---|---|---|---|
| | **Đặt món tại chi nhánh** (Local Order Service, Online Order Service) | | | |
| 1 | | Đặt đơn | Xem danh mục món (`GET /dishes`) | Thu ngân, khách hàng online |
| | | | Tạo đơn (`POST /orders`) | |
| 2 | | Hủy đơn | Yêu cầu hủy đơn (`POST /orders/{id}/cancel`) | Thu ngân, khách hàng online |
| 3 | | Theo dõi đơn | Xem danh sách đơn và trạng thái (`GET /orders`, `GET /orders/{id}`) | Thu ngân, khách hàng online |
| 4 | | Giám sát chi nhánh | Xem kết nối, số tin chờ gửi, cảnh báo (`GET /monitor`) | Thu ngân |
| 5 | | Đồng bộ đơn với Kho và Bếp | Gửi hàng chờ (outbox) lên Kafka | Local Order Service (tự động) |
| | | | Áp dụng trạng thái đơn nhận về theo thứ hạng | |
| 6 | | Xem tình trạng món (đợt 2) | Xem menu kèm trạng thái Còn, Hết, Ẩn (`GET /menu`) | Thu ngân, khách hàng online |
| | **Kho** (Inventory Service) | | | |
| 7 | | Giữ nguyên liệu cho đơn | Nhận đơn mới, giữ nguyên liệu hoặc trả Thất bại (`OrderCreated`) | Inventory Service (tự động) |
| 8 | | Xử lý lệnh của Bếp | Hoàn kho hoặc ghi hao hụt (`ReleaseRequested`) | Inventory Service (tự động) |
| | | | Ghi nhận nguyên liệu đã dùng (`StockConsumed`) | |
| 9 | | Quản lý tồn kho | Xem tồn kho (`GET /stock`) | Nhân viên kho |
| | | | Nhập kho (`POST /stock/receipts`) | |
| | | | Xác nhận kiểm kho xong (`POST /ingredients/{id}/clear-check`) | |
| 10 | | Theo dõi cảnh báo kho | Xem cảnh báo (`GET /alerts`), xem độ trễ consumer (`GET /monitor`) | Nhân viên kho |
| 11 | | Công bố tình trạng món (đợt 2) | Gửi `DishStatusChanged`, heartbeat; cung cấp snapshot (`GET /menu/snapshot`) | Inventory Service (tự động) |
| | **Bếp** (Kitchen Service) | | | |
| 12 | | Xử lý phiếu bếp | Xem danh sách phiếu và cảnh báo (`GET /tickets`) | Nhân viên bếp |
| | | | Bắt đầu nấu (`POST /tickets/{order_id}/start`) | |
| | | | Từ chối phiếu (`POST /tickets/{order_id}/reject`) | |
| | | | Hoàn tất (`POST /tickets/{order_id}/complete`) | |
| 13 | | Nhận đơn và yêu cầu hủy | Nhận đơn đã giữ hoặc thất bại từ Kho (`OrderReserved`, `OrderFailed`) | Kitchen Service (tự động) |
| | | | Quyết định yêu cầu hủy (`CancelRequested`) | |
| | | | Nhận cờ kiểm kho (`IngredientCheckChanged`) | |
| 14 | | Theo dõi cảnh báo bếp | Xem cảnh báo (`GET /alerts`), xem độ trễ consumer (`GET /monitor`) | Nhân viên bếp |
| | **Báo cáo quản lý** (Order Query Service) | | | |
| 15 | | Xem báo cáo tổng hợp | Xem số đơn theo trạng thái và lý do, mốc "dữ liệu tính đến" của từng chi nhánh (`GET /reports/summary`) | Quản lý |

## II. THIẾT KẾ CHỨC NĂNG PHẦN MỀM

Mục này có thẻ use case cho các giao dịch đã xây dựng. Các giao dịch còn lại được bổ sung khi bước tương ứng hoàn thành (chi nhánh: bước 6; quyết định yêu cầu hủy: bước 5; cảnh báo và báo cáo: bước 7; tình trạng món: đợt 2).

### 1. Kho - module

#### 1.1. Giữ nguyên liệu cho đơn - use case

##### 1.1.1. Nhận đơn mới, giữ nguyên liệu hoặc trả Thất bại - giao dịch

- **Tên Usecase:** Nhận đơn mới, giữ nguyên liệu hoặc trả Thất bại
- **Mô tả Usecase:** Chức năng cho phép Inventory Service nhận đơn mới từ chi nhánh và giữ đủ nguyên liệu cho cả đơn, hoặc trả Thất bại kèm lý do.
- **Tác nhân chính:** Inventory Service (tự động, khi có tin `OrderCreated` trên `order-events.<branch>`)
- **Tác nhân phụ:** Kitchen Service, chi nhánh gốc (nhận kết quả)
- **Điều kiện bắt đầu (Pre-Condition):** chi nhánh đã gửi đơn lên Kafka; tin chưa từng được xử lý (`event_id` chưa có trong `processed_events`).
- **Điều kiện kết thúc (Post-Condition):** đơn có đúng một bản ghi trong `inventory_orders` (`DANG_GIU` hoặc `THAT_BAI`); kết quả nằm trong `outbox_events` để gửi đi.
- **Trình tự các sự kiện:**
  1. Ghi `event_id` vào `processed_events`; nếu đã có thì bỏ qua tin.
  2. Nếu đơn đã có bản ghi (gửi lại), trả lại kết quả cũ cho chi nhánh gốc và dừng.
  3. Kiểm tra dữ liệu đơn; sai thì ghi Thất bại `INVALID_ORDER_DATA`.
  4. Kiểm tra giờ tạo: quá X giờ thì `ORDER_EXPIRED`, ở tương lai quá dung sai thì `FUTURE_CREATION_TIME`.
  5. Có món không có công thức thì `NO_RECIPE`.
  6. Khóa các dòng `stock` của đơn theo thứ tự mã nguyên liệu; có nguyên liệu đang chờ kiểm kho thì `AWAITING_STOCK_CHECK`, thiếu thì `INSUFFICIENT_INGREDIENTS`.
  7. Đủ thì trừ `available`, cộng `reserved`, ghi từng dòng `inventory_reservations`, chuyển `DANG_GIU`.
  8. Ghi kết quả vào outbox: `OrderReserved` hoặc `OrderFailed` tới `kitchen-orders` và `status-events.<chi nhánh gốc>`; commit, rồi commit offset.
- **Các yêu cầu phi chức năng:** giữ đủ hoặc không giữ gì (BR1); hai instance chạy song song không làm kho âm (kịch bản 42); gửi lại không giữ lần hai (BR12).
- **Biểu đồ hoạt động:**

```mermaid
flowchart TD
  s((Bắt đầu)) --> a{event_id đã xử lý?}
  a -- có --> z((Kết thúc))
  a -- chưa --> b{Đơn đã có bản ghi?}
  b -- có --> b1[Trả lại kết quả cũ cho chi nhánh gốc] --> z
  b -- chưa --> c{Dữ liệu đơn hợp lệ?}
  c -- không --> f[Ghi THAT_BAI với lý do]
  c -- có --> d{Trong giới hạn thời gian?}
  d -- không --> f
  d -- có --> e{Mọi món có công thức?}
  e -- không --> f
  e -- có --> g[Khóa các dòng stock theo thứ tự]
  g --> h{Có nguyên liệu chờ kiểm kho hoặc thiếu?}
  h -- có --> f
  h -- không --> i[Trừ available, cộng reserved, ghi DANG_GIU]
  i --> j[Outbox: OrderReserved tới Bếp và chi nhánh]
  f --> k[Outbox: OrderFailed tới Bếp và chi nhánh]
  j --> z
  k --> z
```

#### 1.2. Xử lý lệnh của Bếp - use case

##### 1.2.1. Hoàn kho hoặc ghi hao hụt - giao dịch

- **Tên Usecase:** Hoàn kho hoặc ghi hao hụt
- **Mô tả Usecase:** Chức năng cho phép Inventory Service hoàn nguyên liệu của một đơn khi Bếp hủy hoặc từ chối, và ghi hao hụt nguyên liệu bị báo hỏng.
- **Tác nhân chính:** Inventory Service (tự động, tin `ReleaseRequested` trên `stock-commands`)
- **Tác nhân phụ:** Kitchen Service (gửi lệnh)
- **Điều kiện bắt đầu:** Bếp đã hủy hoặc từ chối đơn và ghi lệnh hoàn kho vào outbox của Bếp.
- **Điều kiện kết thúc:** nếu bản ghi đang `DANG_GIU`: chuyển `DA_TRA`, mỗi dòng giữ được đóng đúng một lần (`DA_HOAN` hoặc `HAO_HUT`); ngược lại kho không đổi.
- **Trình tự các sự kiện:**
  1. Chuyển bản ghi từ `DANG_GIU` sang `DA_TRA` bằng một câu UPDATE có điều kiện.
  2. Không đổi được: bản ghi đã `DA_TRA` hoặc `DA_DUNG` thì bỏ qua (tin trùng); không có bản ghi hoặc `THAT_BAI` thì ghi cảnh báo `LENH_KHONG_KHOP` và không cộng kho.
  3. Với từng dòng giữ: nếu lý do là `SPOILED_INGREDIENT` và nguyên liệu nằm trong danh sách hỏng thì chuyển lượng giữ sang `wasted` và bật `needs_check`; còn lại thì cộng lại `available`. Lượng hoàn là lượng đã ghi lúc giữ, không tính lại theo công thức.
  4. Mỗi nguyên liệu vừa bị bật cờ: lấy version mới từ `menu_version`, ghi `IngredientCheckChanged` tới `menu-events` cho Bếp.
- **Các yêu cầu phi chức năng:** lệnh tới nhiều lần chỉ cộng kho một lần (kịch bản 5); Kho tắt khi Bếp từ chối thì hoàn đúng một lần khi bật lại (kịch bản 4).
- **Biểu đồ hoạt động:**

```mermaid
flowchart TD
  s((Bắt đầu)) --> a{Bản ghi đang DANG_GIU?}
  a -- DA_TRA hoặc DA_DUNG --> z((Kết thúc))
  a -- không có hoặc THAT_BAI --> w[Ghi cảnh báo LENH_KHONG_KHOP, kho không đổi] --> z
  a -- có --> b[Chuyển DA_TRA]
  b --> c{Từng dòng giữ: lý do hỏng và nguyên liệu bị báo hỏng?}
  c -- có --> d[reserved → wasted, bật needs_check]
  c -- không --> e[reserved → available]
  d --> f[Outbox: IngredientCheckChanged tới Bếp]
  e --> z
  f --> z
```

##### 1.2.2. Ghi nhận nguyên liệu đã dùng - giao dịch

- **Tên Usecase:** Ghi nhận nguyên liệu đã dùng
- **Mô tả Usecase:** Chức năng cho phép Inventory Service chuyển lượng đang giữ của một đơn sang đã dùng khi Bếp bắt đầu nấu.
- **Tác nhân chính:** Inventory Service (tự động, tin `StockConsumed` trên `stock-commands`)
- **Tác nhân phụ:** Kitchen Service
- **Điều kiện bắt đầu:** nhân viên bếp đã bấm Bắt đầu nấu.
- **Điều kiện kết thúc:** bản ghi `DA_DUNG`; `reserved` giảm, `consumed` tăng đúng lượng đã giữ; `available` không đổi.
- **Trình tự các sự kiện:** như giao dịch 1.2.1 bước 1–2 với trạng thái đích `DA_DUNG`; sau đó với từng dòng: `reserved` giảm q, `consumed` tăng q, dòng giữ đóng là `DA_DUNG`.
- **Các yêu cầu phi chức năng:** không trừ kho lần hai (kịch bản 43).
- **Biểu đồ hoạt động:**

```mermaid
flowchart TD
  s((Bắt đầu)) --> a{Bản ghi đang DANG_GIU?}
  a -- DA_TRA hoặc DA_DUNG --> z((Kết thúc))
  a -- không có hoặc THAT_BAI --> w[Ghi cảnh báo LENH_KHONG_KHOP] --> z
  a -- có --> b[Chuyển DA_DUNG]
  b --> c[Từng dòng: reserved → consumed] --> z
```

#### 1.3. Quản lý tồn kho - use case

##### 1.3.1. Xem tồn kho - giao dịch

- **Tên Usecase:** Xem tồn kho
- **Mô tả Usecase:** Chức năng cho phép nhân viên kho xem bốn đại lượng của từng nguyên liệu (`available`, `reserved`, `consumed`, `wasted`) và cờ kiểm kho.
- **Tác nhân chính:** Nhân viên kho. **Tác nhân phụ:** không có.
- **Điều kiện bắt đầu:** Inventory Service đang chạy. **Điều kiện kết thúc:** không có.
- **Trình tự các sự kiện:** 1. Nhân viên mở màn hình Kho. 2. Màn hình gọi `GET /stock`. 3. Hệ thống trả danh sách nguyên liệu theo mã.
- **Các yêu cầu phi chức năng:** không.
- **Biểu đồ hoạt động:**

```mermaid
flowchart TD
  s((Bắt đầu)) --> a[Mở màn hình Kho] --> b[GET /stock] --> c[Hiển thị tồn kho và cờ kiểm kho] --> z((Kết thúc))
```

##### 1.3.2. Nhập kho - giao dịch

- **Tên Usecase:** Nhập kho
- **Mô tả Usecase:** Chức năng cho phép nhân viên kho cộng thêm số lượng vào tồn kho khả dụng của một nguyên liệu.
- **Tác nhân chính:** Nhân viên kho. **Tác nhân phụ:** không có.
- **Điều kiện bắt đầu:** nguyên liệu đã có trong `stock`. **Điều kiện kết thúc:** `available` tăng đúng số lượng nhập; cờ kiểm kho không đổi.
- **Trình tự các sự kiện:** 1. Nhân viên chọn nguyên liệu, nhập số lượng. 2. Màn hình gọi `POST /stock/receipts`. 3. Hệ thống kiểm tra số lượng dương (sai: 422), nguyên liệu tồn tại (không: 404). 4. Cộng `available`, commit, trả dòng tồn kho mới.
- **Các yêu cầu phi chức năng:** không.
- **Biểu đồ hoạt động:**

```mermaid
flowchart TD
  s((Bắt đầu)) --> a[Nhập nguyên liệu và số lượng] --> b{Số lượng > 0?}
  b -- không --> e1[Báo lỗi 422] --> z((Kết thúc))
  b -- có --> c{Nguyên liệu tồn tại?}
  c -- không --> e2[Báo lỗi 404] --> z
  c -- có --> d[available += số lượng] --> f[Trả tồn kho mới] --> z
```

##### 1.3.3. Xác nhận kiểm kho xong - giao dịch

- **Tên Usecase:** Xác nhận kiểm kho xong
- **Mô tả Usecase:** Chức năng cho phép nhân viên kho gỡ cờ kiểm kho của một nguyên liệu sau khi kiểm, và tùy chọn nhập lượng tồn thực tế đếm được.
- **Tác nhân chính:** Nhân viên kho. **Tác nhân phụ:** Kitchen Service (nhận tin gỡ cờ).
- **Điều kiện bắt đầu:** nguyên liệu bị bật cờ sau khi Bếp báo hỏng. **Điều kiện kết thúc:** `needs_check` tắt; nếu có `counted_on_hand` thì `available = counted_on_hand − reserved`; Bếp được báo để gỡ cảnh báo trên phiếu; đơn mới dùng nguyên liệu này lại được giữ.
- **Trình tự các sự kiện:** 1. Nhân viên chọn nguyên liệu, nhập lượng đếm được (nếu có). 2. Màn hình gọi `POST /ingredients/{id}/clear-check`. 3. Hệ thống khóa dòng `stock`; lượng đếm nhỏ hơn lượng đang giữ thì từ chối (409). 4. Gỡ cờ; nếu cờ đang bật thì lấy version mới và ghi `IngredientCheckChanged` (gỡ cờ) vào outbox. 5. Commit, trả tồn kho mới.
- **Các yêu cầu phi chức năng:** tin gỡ cờ mang version lớn hơn tin bật cờ, Bếp không bị đè bởi tin cũ (kịch bản 48).
- **Biểu đồ hoạt động:**

```mermaid
flowchart TD
  s((Bắt đầu)) --> a[Chọn nguyên liệu, nhập lượng đếm được nếu có] --> b{Nguyên liệu tồn tại?}
  b -- không --> e1[Báo lỗi 404] --> z((Kết thúc))
  b -- có --> c{Lượng đếm ≥ lượng đang giữ?}
  c -- không --> e2[Báo lỗi 409, không đổi gì] --> z
  c -- có --> d[Cập nhật available, tắt needs_check]
  d --> f{Cờ trước đó đang bật?}
  f -- có --> g[Outbox: IngredientCheckChanged gỡ cờ tới Bếp] --> h[Trả tồn kho mới]
  f -- không --> h
  h --> z
```

### 2. Bếp - module

#### 2.1. Xử lý phiếu bếp - use case

##### 2.1.1. Xem danh sách phiếu - giao dịch

- **Tên Usecase:** Xem danh sách phiếu
- **Mô tả Usecase:** Chức năng cho phép nhân viên bếp xem các phiếu Chờ nấu và Đang nấu, kèm cảnh báo đỏ trên phiếu Chờ nấu có nguyên liệu đang chờ kiểm kho.
- **Tác nhân chính:** Nhân viên bếp. **Tác nhân phụ:** không có.
- **Điều kiện bắt đầu:** Kitchen Service đang chạy. **Điều kiện kết thúc:** không có.
- **Trình tự các sự kiện:** 1. Nhân viên mở màn hình Bếp. 2. Màn hình gọi `GET /tickets`. 3. Hệ thống trả các phiếu `CHO_NAU`, `DANG_NAU` theo giờ tạo đơn; với phiếu `CHO_NAU`, `warnings` là các nguyên liệu trong `reserved` đang có cờ trong `flagged_ingredients`.
- **Các yêu cầu phi chức năng:** cảnh báo chỉ là cảnh báo, không tự hủy phiếu (Luồng A).
- **Biểu đồ hoạt động:**

```mermaid
flowchart TD
  s((Bắt đầu)) --> a[Mở màn hình Bếp] --> b[GET /tickets] --> c[Ghép reserved với flagged_ingredients] --> d[Hiển thị phiếu và cảnh báo] --> z((Kết thúc))
```

##### 2.1.2. Bắt đầu nấu - giao dịch

- **Tên Usecase:** Bắt đầu nấu
- **Mô tả Usecase:** Chức năng cho phép nhân viên bếp chuyển một phiếu từ Chờ nấu sang Đang nấu.
- **Tác nhân chính:** Nhân viên bếp. **Tác nhân phụ:** Inventory Service (nhận báo đã dùng).
- **Điều kiện bắt đầu:** phiếu đang `CHO_NAU`. **Điều kiện kết thúc:** phiếu `DANG_NAU`; tin `StockConsumed` nằm trong outbox của Bếp.
- **Trình tự các sự kiện:** 1. Nhân viên bấm Bắt đầu nấu. 2. Màn hình gọi `POST /tickets/{order_id}/start`. 3. Hệ thống khóa dòng `kitchen_orders`; không có phiếu thì 404, không còn `CHO_NAU` thì 409 kèm trạng thái hiện tại. 4. Chuyển `DANG_NAU` có điều kiện, ghi `StockConsumed` vào outbox, commit.
- **Các yêu cầu phi chức năng:** bấm đồng thời với Từ chối thì đúng một thao tác thắng (kịch bản 52).
- **Biểu đồ hoạt động:**

```mermaid
flowchart TD
  s((Bắt đầu)) --> a[Bấm Bắt đầu nấu] --> b[Khóa dòng kitchen_orders] --> c{Phiếu đang CHO_NAU?}
  c -- không có phiếu --> e1[404] --> z((Kết thúc))
  c -- trạng thái khác --> e2[409 kèm trạng thái hiện tại] --> z
  c -- có --> d[Chuyển DANG_NAU] --> f[Outbox: StockConsumed tới Kho] --> z
```

##### 2.1.3. Từ chối phiếu - giao dịch

- **Tên Usecase:** Từ chối phiếu
- **Mô tả Usecase:** Chức năng cho phép nhân viên bếp từ chối một phiếu Chờ nấu với lý do cố định; với lý do nguyên liệu hỏng thì phải chọn nguyên liệu hỏng trong phiếu.
- **Tác nhân chính:** Nhân viên bếp. **Tác nhân phụ:** Inventory Service (nhận lệnh hoàn kho), chi nhánh gốc (nhận Đã hủy).
- **Điều kiện bắt đầu:** phiếu đang `CHO_NAU`. **Điều kiện kết thúc:** phiếu `DA_HUY` (`cancelled_by = KITCHEN`); `OrderCancelled` và `ReleaseRequested` nằm trong outbox trong cùng giao dịch.
- **Trình tự các sự kiện:** 1. Nhân viên chọn lý do (`EQUIPMENT_FAILURE`, `SHORT_STAFFED`, `SPOILED_INGREDIENT`) và nguyên liệu hỏng nếu có. 2. Màn hình gọi `POST /tickets/{order_id}/reject`. 3. Hệ thống kiểm tra lý do và nguyên liệu (sai: 400), khóa phiếu (không có: 404; không còn `CHO_NAU`: 409). 4. Chuyển `DA_HUY`, ghi `OrderCancelled` tới chi nhánh gốc và `ReleaseRequested` tới Kho, commit.
- **Các yêu cầu phi chức năng:** phiếu đang nấu không từ chối được và Kho không nhận lệnh hoàn (kịch bản 50); Kho đang tắt thì chi nhánh vẫn thấy Đã hủy ngay (kịch bản 4).
- **Biểu đồ hoạt động:**

```mermaid
flowchart TD
  s((Bắt đầu)) --> a[Chọn lý do, nguyên liệu hỏng nếu có] --> b{Lý do và nguyên liệu hợp lệ?}
  b -- không --> e1[400] --> z((Kết thúc))
  b -- có --> c[Khóa dòng kitchen_orders] --> d{Phiếu đang CHO_NAU?}
  d -- không --> e2[404 hoặc 409] --> z
  d -- có --> f[Chuyển DA_HUY] --> g[Outbox: OrderCancelled tới chi nhánh, ReleaseRequested tới Kho] --> z
```

##### 2.1.4. Hoàn tất - giao dịch

- **Tên Usecase:** Hoàn tất
- **Mô tả Usecase:** Chức năng cho phép nhân viên bếp chuyển một phiếu Đang nấu sang Hoàn tất.
- **Tác nhân chính:** Nhân viên bếp. **Tác nhân phụ:** chi nhánh gốc (nhận Hoàn tất).
- **Điều kiện bắt đầu:** phiếu đang `DANG_NAU`. **Điều kiện kết thúc:** phiếu `HOAN_TAT`; `OrderCompleted` nằm trong outbox.
- **Trình tự các sự kiện:** 1. Nhân viên bấm Hoàn tất. 2. Màn hình gọi `POST /tickets/{order_id}/complete`. 3. Hệ thống khóa phiếu (không có: 404; không còn `DANG_NAU`: 409). 4. Chuyển `HOAN_TAT`, ghi `OrderCompleted` tới chi nhánh gốc, commit.
- **Các yêu cầu phi chức năng:** không.
- **Biểu đồ hoạt động:**

```mermaid
flowchart TD
  s((Bắt đầu)) --> a[Bấm Hoàn tất] --> b[Khóa dòng kitchen_orders] --> c{Phiếu đang DANG_NAU?}
  c -- không --> e[404 hoặc 409] --> z((Kết thúc))
  c -- có --> d[Chuyển HOAN_TAT] --> f[Outbox: OrderCompleted tới chi nhánh] --> z
```

#### 2.2. Nhận đơn và yêu cầu hủy - use case

##### 2.2.1. Nhận đơn đã giữ hoặc thất bại từ Kho - giao dịch

- **Tên Usecase:** Nhận đơn đã giữ hoặc thất bại từ Kho
- **Mô tả Usecase:** Chức năng cho phép Kitchen Service tạo phiếu Chờ nấu cho đơn Kho đã giữ nguyên liệu, và ghi nhận kết quả Thất bại.
- **Tác nhân chính:** Kitchen Service (tự động, tin trên `kitchen-orders`). **Tác nhân phụ:** Inventory Service.
- **Điều kiện bắt đầu:** Kho đã ghi `OrderReserved` hoặc `OrderFailed` vào outbox. **Điều kiện kết thúc:** đơn có đúng một dòng trong `kitchen_orders`.
- **Trình tự các sự kiện:**
  1. Chèn dòng giữ chỗ `CHUA_CO` nếu chưa có, khóa dòng (`SELECT ... FOR UPDATE`).
  2. `OrderReserved`: chưa có bản ghi thì tạo phiếu `CHO_NAU` với `reserved`; bản ghi `HUY_CHO_DON` có chi nhánh gốc trong danh sách yêu cầu hủy thì chuyển `DA_HUY` và gửi lệnh hoàn kho; không có thì bỏ các yêu cầu đó, tạo phiếu và ghi cảnh báo `HUY_SAI_CHI_NHANH`.
  3. `OrderFailed`: chưa có bản ghi hoặc `HUY_CHO_DON` thì ghi `THAT_BAI`.
  4. Đơn đã ở trạng thái kết thúc: trả lại kết quả cũ cho chi nhánh gốc, không gửi lệnh hoàn kho lần hai.
- **Các yêu cầu phi chức năng:** mỗi đơn chỉ một bản ghi (BR8); không bỏ qua tin Thất bại (điều cấm 11).
- **Biểu đồ hoạt động:**

```mermaid
flowchart TD
  s((Bắt đầu)) --> a[Chèn CHUA_CO nếu chưa có, khóa dòng] --> b{Loại tin}
  b -- OrderReserved --> c{Trạng thái hiện tại}
  c -- CHUA_CO --> c1[Tạo phiếu CHO_NAU] --> z((Kết thúc))
  c -- HUY_CHO_DON, chi nhánh gốc có yêu cầu hủy --> c2[DA_HUY, outbox: ReleaseRequested, OrderCancelled] --> z
  c -- HUY_CHO_DON, không có --> c3[Bỏ yêu cầu hủy, tạo CHO_NAU, cảnh báo HUY_SAI_CHI_NHANH] --> z
  c -- CHO_NAU hoặc DANG_NAU --> z
  c -- trạng thái kết thúc --> r[Trả lại kết quả cũ] --> z
  b -- OrderFailed --> d{Trạng thái hiện tại}
  d -- CHUA_CO hoặc HUY_CHO_DON --> d1[Ghi THAT_BAI] --> z
  d -- trạng thái kết thúc --> r
  d -- CHO_NAU hoặc DANG_NAU --> z
```

##### 2.2.2. Nhận cờ kiểm kho - giao dịch

- **Tên Usecase:** Nhận cờ kiểm kho
- **Mô tả Usecase:** Chức năng cho phép Kitchen Service ghi nhận nguyên liệu bị bật hoặc gỡ cờ kiểm kho để hiển thị cảnh báo trên phiếu.
- **Tác nhân chính:** Kitchen Service (tự động, tin `IngredientCheckChanged` trên `menu-events`). **Tác nhân phụ:** Inventory Service.
- **Điều kiện bắt đầu:** Kho bật hoặc gỡ cờ một nguyên liệu. **Điều kiện kết thúc:** `flagged_ingredients` giữ trạng thái có version lớn nhất đã nhận.
- **Trình tự các sự kiện:** 1. Đọc `ingredient_id`, `needs_check`, `epoch`, `seq`. 2. Ghi đè dòng của nguyên liệu chỉ khi (`epoch`, `seq`) mới lớn hơn. 3. Commit; danh sách phiếu lần sau hiển thị cảnh báo theo cờ mới.
- **Các yêu cầu phi chức năng:** tin đến muộn với version nhỏ hơn không đè tin mới hơn.
- **Biểu đồ hoạt động:**

```mermaid
flowchart TD
  s((Bắt đầu)) --> a[Đọc ingredient_id, needs_check, epoch, seq] --> b{Version mới lớn hơn version đang giữ?}
  b -- có --> c[Ghi đè flagged_ingredients] --> z((Kết thúc))
  b -- không --> z
```

## III. THIẾT KẾ CƠ SỞ DỮ LIỆU

### 1. CÁC CƠ SỞ DỮ LIỆU CỦA HỆ THỐNG

Tất cả dùng PostgreSQL 16.14; mỗi dịch vụ chỉ truy cập CSDL của mình.

| TT | Cơ sở dữ liệu | Ghi chú |
|---|---|---|
| 1 | Inventory DB (`inventory-db`, database `inventory`) | Của Inventory Service, dùng chung cho cả chuỗi; hai instance cùng ghi |
| 2 | Kitchen DB (`kitchen-db`, database `kitchen`) | Của Kitchen Service |
| 3 | Branch DB của POS01 (`pos01-db`, database `branch`) | Của Local Order Service POS01; bật logical WAL để nhân bản |
| 4 | Branch DB của POS02 (`pos02-db`) | Cùng cấu trúc với mục 3 |
| 5 | Branch DB của kênh Online (`online-db`) | Cùng cấu trúc với mục 3 |
| 6 | Central Order Replica (`central-db`, database `central`) | Bản sao `orders` và `replication_heartbeat` của mọi chi nhánh, chỉ đọc cho Order Query Service |

### 2. THIẾT KẾ CHI TIẾT CƠ SỞ DỮ LIỆU

#### Sơ đồ CSDL tổng quát

```mermaid
flowchart LR
  subgraph B["Branch DB × 3 (POS01, POS02, ONLINE)"]
    o["orders"] --- ob["outbox_events (hàng chờ gửi)"]
    d["dishes"]
    mc["menu_cache, menu_cache_meta"]
    rh["replication_heartbeat"]
    pb["processed_events"]
  end
  subgraph I["Inventory DB"]
    st["stock"] --- re["recipes"]
    io["inventory_orders"] --- ir["inventory_reservations"]
    st --- ir
    ds["dish_status, menu_version"]
    ia["alerts, processed_events, outbox_events"]
  end
  subgraph K["Kitchen DB"]
    ko["kitchen_orders"]
    fi["flagged_ingredients"]
    ka["alerts, processed_events, outbox_events"]
  end
  subgraph C["Central Order Replica"]
    co["orders (mọi chi nhánh)"]
    ch["replication_heartbeat"]
  end
  o -.->|logical replication| co
  rh -.->|logical replication| ch
  ob ==>|Kafka: OrderCreated| io
  ia ==>|Kafka: OrderReserved, OrderFailed, IngredientCheckChanged| ko
  ka ==>|Kafka: StockConsumed, ReleaseRequested| io
```

Giữa các CSDL không có khóa ngoại: mỗi đơn mang cùng một `order_id` (UUID do chi nhánh sinh) ở cả ba nơi, và dữ liệu đi giữa chúng qua Kafka (nét đôi) hoặc qua logical replication (nét đứt).

#### 2.1. Các bảng trong cơ sở dữ liệu

| STT | CSDL | Tên bảng | Mô tả |
|---|---|---|---|
| 1 | Inventory DB | `stock` | Mỗi nguyên liệu một dòng: tên, đơn vị, bốn đại lượng `available`, `reserved`, `consumed`, `wasted` và cờ `needs_check` |
| 2 | Inventory DB | `recipes` | Công thức: lượng mỗi nguyên liệu cho một suất của món |
| 3 | Inventory DB | `inventory_orders` | Mỗi đơn đúng một bản ghi kết quả (BR12): `DANG_GIU`, `THAT_BAI`, `DA_TRA`, `DA_DUNG`, chi nhánh gốc, lý do |
| 4 | Inventory DB | `inventory_reservations` | Lượng giữ của từng nguyên liệu cho từng đơn, ghi lúc giữ, và kết quả của dòng (`DA_HOAN`, `DA_DUNG`, `HAO_HUT`) |
| 5 | Inventory DB | `dish_status` | Trạng thái món (Còn, Hết, Ẩn) kèm version (đợt 2) |
| 6 | Inventory DB | `menu_version` | Một dòng duy nhất: bộ đếm version (`epoch`, `seq`) bền vững |
| 7 | Inventory DB | `alerts` | Cảnh báo cho người xem: `CAN_KIEM_TRA`, `LENH_KHONG_KHOP` |
| 8 | Inventory DB | `processed_events` | `event_id` đã xử lý, chống xử lý trùng |
| 9 | Inventory DB | `outbox_events` | Tin chờ gửi lên Kafka, ghi trong cùng giao dịch với thay đổi trạng thái |
| 10 | Kitchen DB | `kitchen_orders` | Mỗi đơn đúng một bản ghi (BR8): phiếu, bản ghi Chờ hủy hoặc kết quả Thất bại; chi nhánh gốc, các chi nhánh đã yêu cầu hủy, nguyên liệu đã giữ |
| 11 | Kitchen DB | `flagged_ingredients` | Cờ kiểm kho nhận từ Kho, kèm version |
| 12 | Kitchen DB | `alerts` | Cảnh báo: `CAN_KIEM_TRA`, `HUY_SAI_CHI_NHANH` |
| 13 | Kitchen DB | `processed_events` | Như mục 8 |
| 14 | Kitchen DB | `outbox_events` | Như mục 9 |
| 15 | Branch DB | `orders` | Đơn của chi nhánh: trạng thái theo thứ hạng, cờ "Đang yêu cầu hủy", lý do |
| 16 | Branch DB | `outbox_events` | Hàng chờ gửi của chi nhánh, có cờ "đã thử gửi" (BR9) |
| 17 | Branch DB | `dishes` | Danh mục món nạp từ file seed, phục vụ màn hình đặt món khi mất mạng |
| 18 | Branch DB | `menu_cache` | Trạng thái món nhận từ Kho, gộp theo version (đợt 2) |
| 19 | Branch DB | `menu_cache_meta` | Một dòng: `epoch` hiện tại và lần cuối nghe được từ Kho (đợt 2) |
| 20 | Branch DB | `replication_heartbeat` | Nhịp nhân bản của chi nhánh, cho mốc "dữ liệu tính đến" |
| 21 | Branch DB | `processed_events` | Như mục 8 |
| 22 | Central Order Replica | `orders` | Bản sao `orders` của mọi chi nhánh |
| 23 | Central Order Replica | `replication_heartbeat` | Bản sao nhịp nhân bản của mọi chi nhánh |

#### 2.2. Thiết kế chi tiết các bảng

Sơ đồ quan hệ và bảng chi tiết của từng CSDL dưới đây được sinh từ các CSDL đang chạy (`backend/scripts/report_schema.py`), nên luôn khớp với migration.

<!-- include: generated/csdl.md -->
