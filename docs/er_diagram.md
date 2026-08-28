# Thiết kế cơ sở dữ liệu (Database Design)

## Sơ đồ quan hệ thực thể (ERD)

```
┌───────────────────┐        ┌───────────────────────┐        ┌───────────────────┐
│       stops         │        │      route_stops        │        │       routes         │
├───────────────────┤        ├───────────────────────┤        ├───────────────────┤
│ stop_id      PK      │◄──────┤ stop_id        FK        │      ┌►│ route_id      PK      │
│ stop_name             │       │ route_id       FK ───────┼──────┘ │ route_short_name       │
│ lat                     │       │ stop_sequence            │        │ route_long_name         │
│ lon                     │       │ offset_min               │        │ fare_regular             │
│ is_hub                  │       │ id             PK (auto)   │        │ fare_student             │
└───────────────────┘        └───────────────────────┘        │ headway_min              │
                                                                    │ first_departure          │
                                                                    │ last_departure           │
                                                                    └───────────────────┘

┌─────────────────────────────┐
│          search_logs            │
├─────────────────────────────┤
│ id                 PK (auto)     │
│ origin_stop_id                    │
│ origin_stop_name                  │
│ dest_stop_id                       │
│ dest_stop_name                     │
│ fare_type                            │
│ n_results                            │
│ searched_at                          │
└─────────────────────────────┘
(khong co khoa ngoai bat buoc - chi de thong ke, van giu duoc du lieu
 ngay ca khi tram/tuyen lien quan bi xoa sau nay)
```

- **1 tuyến (routes) — N dòng route_stops** — 1 tuyến đi qua nhiều trạm theo thứ tự (`stop_sequence`).
- **1 trạm (stops) — N dòng route_stops** — 1 trạm có thể được nhiều tuyến đi qua (đây chính là cơ chế phát hiện *điểm trung chuyển* trong thuật toán tìm tuyến).
- `offset_min`: số phút tích luỹ từ điểm xuất phát của tuyến đến trạm đó (dùng để tính thời gian di chuyển giữa 2 trạm bất kỳ trên cùng 1 tuyến bằng phép trừ).
- `is_hub`: đánh dấu các trạm là bến xe/điểm trung tâm lớn (dùng cho thống kê "top trạm trung chuyển nhiều tuyến nhất").

## Từ điển dữ liệu (Data Dictionary)

### `stops`
| Cột | Kiểu | Mô tả |
|---|---|---|
| stop_id | text (PK) | Mã trạm, duy nhất |
| stop_name | text | Tên trạm hiển thị |
| lat, lon | double | Toạ độ (dùng vẽ bản đồ) |
| is_hub | boolean | Có phải bến/điểm trung tâm không |

### `routes`
| Cột | Kiểu | Mô tả |
|---|---|---|
| route_id | text (PK) | Mã tuyến |
| route_short_name | text | Số hiệu tuyến (vd "19") |
| route_long_name | text | Tên đầy đủ (điểm đầu - điểm cuối) |
| fare_regular | integer | Giá vé phổ thông (VND) |
| fare_student | integer | Giá vé sinh viên (VND) |
| headway_min | integer | Giãn cách giữa 2 chuyến (phút) |
| first_departure, last_departure | text | Khung giờ hoạt động 'HH:MM' |

### `route_stops`
| Cột | Kiểu | Mô tả |
|---|---|---|
| id | bigint (PK) | Khoá tự tăng |
| route_id | text (FK -> routes) | |
| stop_id | text (FK -> stops) | |
| stop_sequence | integer | Thứ tự trạm trên tuyến |
| offset_min | integer | Phút tích luỹ từ đầu tuyến |

### `search_logs`
| Cột | Kiểu | Mô tả |
|---|---|---|
| id | bigint (PK) | Khoá tự tăng |
| origin_stop_id/name | text | Điểm đi người dùng chọn |
| dest_stop_id/name | text | Điểm đến người dùng chọn |
| fare_type | text | 'student' hoặc 'regular' |
| n_results | integer | Số phương án tìm được |
| searched_at | timestamptz | Thời điểm tìm kiếm |
