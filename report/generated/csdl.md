<!-- Sinh tự động bởi backend/scripts/report_schema.py từ các CSDL đang chạy. Không sửa tay: chạy lại script sau mỗi migration. -->

##### 4.2.2.1. Inventory DB

Lược đồ thực thể và các ràng buộc bảng của `inventory-db` thể hiện trên Hình 2.20; chi tiết cấu trúc 9 bảng dữ liệu được trình bày từ Bảng 2.6 đến Bảng 2.14.

![Hình 2.20. Sơ đồ thực thể - quan hệ của cơ sở dữ liệu Inventory DB](images/er-inventory-db.png)

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| id | BIGINT | NO | PRI |  | auto_increment |
| kind | TEXT | NO | UNI (tổ hợp) |  | CHECK (kind IN ('CAN_KIEM_TRA', 'LENH_KHONG_KHOP', 'HUY_SAI_CHI_NHANH')) |
| order_id | UUID | YES |  |  |  |
| event_id | UUID | YES |  |  |  |
| source_topic | TEXT | NO | UNI (tổ hợp) |  |  |
| source_partition | INT | NO | UNI (tổ hợp) |  |  |
| source_offset | BIGINT | NO | UNI (tổ hợp) |  |  |
| detail | JSONB | NO |  | '{}' |  |
| created_at | TIMESTAMPTZ | NO |  | now() |  |

*Bảng 2.6. Cấu trúc bảng `alerts` (Inventory DB)*

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| dish_id | TEXT | NO | PRI |  |  |
| status | TEXT | NO |  |  | CHECK (status IN ('CON', 'HET', 'AN')) |
| epoch | INT | NO |  |  |  |
| seq | BIGINT | NO |  |  |  |

*Bảng 2.7. Cấu trúc bảng `dish_status` (Inventory DB)*

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| order_id | UUID | NO | PRI |  |  |
| origin_branch | TEXT | NO |  |  |  |
| status | TEXT | NO |  |  | CHECK (status IN ('DANG_GIU', 'THAT_BAI', 'DA_TRA', 'DA_DUNG')) |
| reason | TEXT | YES |  |  |  |
| order_created_at | TIMESTAMPTZ | YES |  |  |  |
| updated_at | TIMESTAMPTZ | NO |  | now() |  |

*Bảng 2.8. Cấu trúc bảng `inventory_orders` (Inventory DB)*

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| order_id | UUID | NO | PRI, FK → inventory_orders.order_id |  |  |
| ingredient_id | TEXT | NO | PRI, FK → stock.ingredient_id |  |  |
| quantity | NUMERIC(12,3) | NO |  |  | CHECK (quantity > 0) |
| outcome | TEXT | YES |  |  | CHECK (outcome IN ('DA_HOAN', 'DA_DUNG', 'HAO_HUT')) |

*Bảng 2.9. Cấu trúc bảng `inventory_reservations` (Inventory DB)*

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| id | BOOLEAN | NO | PRI | true | CHECK (id) |
| epoch | INT | NO |  |  |  |
| seq | BIGINT | NO |  |  |  |

*Bảng 2.10. Cấu trúc bảng `menu_version` (Inventory DB)*

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| id | BIGINT | NO | PRI |  | auto_increment |
| event_id | UUID | NO | UNI |  |  |
| topic | TEXT | NO |  |  |  |
| msg_key | TEXT | NO |  |  |  |
| payload | JSONB | NO |  |  |  |
| created_at | TIMESTAMPTZ | NO |  | now() |  |
| sent_at | TIMESTAMPTZ | YES |  |  |  |

*Bảng 2.11. Cấu trúc bảng `outbox_events` (Inventory DB)*

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| event_id | UUID | NO | PRI |  |  |
| processed_at | TIMESTAMPTZ | NO |  | now() |  |

*Bảng 2.12. Cấu trúc bảng `processed_events` (Inventory DB)*

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| dish_id | TEXT | NO | PRI |  |  |
| ingredient_id | TEXT | NO | PRI, FK → stock.ingredient_id |  |  |
| quantity | NUMERIC(12,3) | NO |  |  | CHECK (quantity > 0) |

*Bảng 2.13. Cấu trúc bảng `recipes` (Inventory DB)*

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| ingredient_id | TEXT | NO | PRI |  |  |
| unit | TEXT | NO |  |  |  |
| available | NUMERIC(12,3) | NO |  |  | CHECK (available >= 0) |
| reserved | NUMERIC(12,3) | NO |  | 0 | CHECK (reserved >= 0) |
| consumed | NUMERIC(12,3) | NO |  | 0 |  |
| wasted | NUMERIC(12,3) | NO |  | 0 |  |
| needs_check | BOOLEAN | NO |  | false |  |
| name | TEXT | NO |  | '' |  |

*Bảng 2.14. Cấu trúc bảng `stock` (Inventory DB)*

##### 4.2.2.2. Kitchen DB

Lược đồ thực thể và các ràng buộc bảng của `kitchen-db` thể hiện trên Hình 2.21; chi tiết cấu trúc 5 bảng dữ liệu được trình bày từ Bảng 2.15 đến Bảng 2.19.

![Hình 2.21. Sơ đồ thực thể - quan hệ của cơ sở dữ liệu Kitchen DB](images/er-kitchen-db.png)

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| id | BIGINT | NO | PRI |  | auto_increment |
| kind | TEXT | NO | UNI (tổ hợp) |  | CHECK (kind IN ('CAN_KIEM_TRA', 'LENH_KHONG_KHOP', 'HUY_SAI_CHI_NHANH')) |
| order_id | UUID | YES |  |  |  |
| event_id | UUID | YES |  |  |  |
| source_topic | TEXT | NO | UNI (tổ hợp) |  |  |
| source_partition | INT | NO | UNI (tổ hợp) |  |  |
| source_offset | BIGINT | NO | UNI (tổ hợp) |  |  |
| detail | JSONB | NO |  | '{}' |  |
| created_at | TIMESTAMPTZ | NO |  | now() |  |

*Bảng 2.15. Cấu trúc bảng `alerts` (Kitchen DB)*

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| ingredient_id | TEXT | NO | PRI |  |  |
| needs_check | BOOLEAN | NO |  |  |  |
| epoch | INT | NO |  |  |  |
| seq | BIGINT | NO |  |  |  |

*Bảng 2.16. Cấu trúc bảng `flagged_ingredients` (Kitchen DB)*

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| order_id | UUID | NO | PRI |  |  |
| status | TEXT | NO |  |  | CHECK (status IN ('CHUA_CO', 'HUY_CHO_DON', 'CHO_NAU', 'DANG_NAU', 'HOAN_TAT', 'DA_HUY', 'THAT_BAI')) |
| origin_branch | TEXT | YES |  |  |  |
| cancel_branches | TEXT[] | NO |  | '{}' |  |
| cancel_reasons | JSONB | NO |  | '{}' |  |
| cancelled_by | TEXT | YES |  |  | CHECK (cancelled_by IN ('CUSTOMER', 'KITCHEN')) |
| close_reason | TEXT | YES |  |  |  |
| items | JSONB | YES |  |  |  |
| reserved | JSONB | YES |  |  |  |
| spoiled | JSONB | YES |  |  |  |
| order_created_at | TIMESTAMPTZ | YES |  |  |  |
| updated_at | TIMESTAMPTZ | NO |  | now() |  |

*Bảng 2.17. Cấu trúc bảng `kitchen_orders` (Kitchen DB)*

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| id | BIGINT | NO | PRI |  | auto_increment |
| event_id | UUID | NO | UNI |  |  |
| topic | TEXT | NO |  |  |  |
| msg_key | TEXT | NO |  |  |  |
| payload | JSONB | NO |  |  |  |
| created_at | TIMESTAMPTZ | NO |  | now() |  |
| sent_at | TIMESTAMPTZ | YES |  |  |  |

*Bảng 2.18. Cấu trúc bảng `outbox_events` (Kitchen DB)*

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| event_id | UUID | NO | PRI |  |  |
| processed_at | TIMESTAMPTZ | NO |  | now() |  |

*Bảng 2.19. Cấu trúc bảng `processed_events` (Kitchen DB)*

##### 4.2.2.3. Branch DB (POS01, POS02, ONLINE)

Lược đồ thực thể và các ràng buộc bảng của `pos01-db` thể hiện trên Hình 2.22; chi tiết cấu trúc 8 bảng dữ liệu được trình bày từ Bảng 2.20 đến Bảng 2.27.

![Hình 2.22. Sơ đồ thực thể - quan hệ của cơ sở dữ liệu Branch DB](images/er-branch-db.png)

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| id | BIGINT | NO | PRI |  | auto_increment |
| kind | TEXT | NO | UNI (tổ hợp) |  | CHECK ((kind = 'CAN_KIEM_TRA')) |
| order_id | UUID | YES |  |  |  |
| event_id | UUID | YES |  |  |  |
| source_topic | TEXT | NO | UNI (tổ hợp) |  |  |
| source_partition | INT | NO | UNI (tổ hợp) |  |  |
| source_offset | BIGINT | NO | UNI (tổ hợp) |  |  |
| detail | JSONB | NO |  | '{}' |  |
| created_at | TIMESTAMPTZ | NO |  | now() |  |

*Bảng 2.20. Cấu trúc bảng `alerts` (Branch DB (POS01, POS02, ONLINE))*

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| dish_id | TEXT | NO | PRI |  |  |
| name | TEXT | NO |  |  |  |

*Bảng 2.21. Cấu trúc bảng `dishes` (Branch DB (POS01, POS02, ONLINE))*

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| dish_id | TEXT | NO | PRI |  |  |
| status | TEXT | NO |  |  | CHECK (status IN ('CON', 'HET', 'AN')) |
| epoch | INT | NO |  |  |  |
| seq | BIGINT | NO |  |  |  |

*Bảng 2.22. Cấu trúc bảng `menu_cache` (Branch DB (POS01, POS02, ONLINE))*

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| id | BOOLEAN | NO | PRI | true | CHECK (id) |
| epoch | INT | NO |  |  |  |
| last_heard_at | TIMESTAMPTZ | YES |  |  |  |
| newest_epoch | INT | NO |  | 0 |  |

*Bảng 2.23. Cấu trúc bảng `menu_cache_meta` (Branch DB (POS01, POS02, ONLINE))*

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| order_id | UUID | NO | PRI |  |  |
| branch_id | TEXT | NO |  |  |  |
| status | TEXT | NO |  |  | CHECK (status IN ('CHO_KHO', 'DA_GIU', 'HOAN_TAT', 'DA_HUY', 'THAT_BAI')) |
| status_rank | SMALLINT | NO |  | 0 |  |
| close_reason | TEXT | YES |  |  |  |
| cancel_flag | TEXT | NO |  | 'KHONG' | CHECK (cancel_flag IN ('KHONG', 'DANG_YEU_CAU', 'BEP_KHONG_NAU')) |
| cancel_requested_at | TIMESTAMPTZ | YES |  |  |  |
| cancel_message | TEXT | YES |  |  |  |
| items | JSONB | NO |  |  |  |
| created_at | TIMESTAMPTZ | NO |  |  |  |

*Bảng 2.24. Cấu trúc bảng `orders` (Branch DB (POS01, POS02, ONLINE))*

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| id | BIGINT | NO | PRI |  | auto_increment |
| event_id | UUID | NO | UNI |  |  |
| order_id | UUID | NO | FK → orders.order_id |  |  |
| kind | TEXT | NO |  |  | CHECK (kind IN ('TAO_DON', 'HUY')) |
| topic | TEXT | NO |  |  |  |
| payload | JSONB | NO |  |  |  |
| attempted | BOOLEAN | NO |  | false |  |
| sent_at | TIMESTAMPTZ | YES |  |  |  |

*Bảng 2.25. Cấu trúc bảng `outbox_events` (Branch DB (POS01, POS02, ONLINE))*

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| event_id | UUID | NO | PRI |  |  |
| processed_at | TIMESTAMPTZ | NO |  | now() |  |

*Bảng 2.26. Cấu trúc bảng `processed_events` (Branch DB (POS01, POS02, ONLINE))*

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| branch_id | TEXT | NO | PRI |  |  |
| beat_at | TIMESTAMPTZ | NO |  |  |  |

*Bảng 2.27. Cấu trúc bảng `replication_heartbeat` (Branch DB (POS01, POS02, ONLINE))*

##### 4.2.2.4. Central Order Replica

Lược đồ thực thể và các ràng buộc bảng của `central-db` thể hiện trên Hình 2.23; chi tiết cấu trúc 2 bảng dữ liệu được trình bày từ Bảng 2.28 đến Bảng 2.29.

![Hình 2.23. Sơ đồ thực thể - quan hệ của cơ sở dữ liệu Central Order Replica](images/er-central-db.png)

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| order_id | UUID | NO | PRI |  |  |
| branch_id | TEXT | NO |  |  |  |
| status | TEXT | NO |  |  | CHECK (status IN ('CHO_KHO', 'DA_GIU', 'HOAN_TAT', 'DA_HUY', 'THAT_BAI')) |
| status_rank | SMALLINT | NO |  | 0 |  |
| close_reason | TEXT | YES |  |  |  |
| cancel_flag | TEXT | NO |  | 'KHONG' | CHECK (cancel_flag IN ('KHONG', 'DANG_YEU_CAU', 'BEP_KHONG_NAU')) |
| cancel_requested_at | TIMESTAMPTZ | YES |  |  |  |
| cancel_message | TEXT | YES |  |  |  |
| items | JSONB | NO |  |  |  |
| created_at | TIMESTAMPTZ | NO |  |  |  |

*Bảng 2.28. Cấu trúc bảng `orders` (Central Order Replica)*

| Field | Type | Null | Key | Default | Extra |
|---|---|---|---|---|---|
| branch_id | TEXT | NO | PRI |  |  |
| beat_at | TIMESTAMPTZ | NO |  |  |  |

*Bảng 2.29. Cấu trúc bảng `replication_heartbeat` (Central Order Replica)*

