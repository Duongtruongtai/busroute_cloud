# Kiến trúc hệ thống & Kiến trúc Cloud

## 1. Sơ đồ kiến trúc Cloud

```
                         ┌─────────────────────────┐
                         │          USER            │
                         │ (Sinh vien / nguoi dung)  │
                         └────────────┬─────────────┘
                                      │ HTTPS
                                      ▼
                     ┌───────────────────────────────┐
                     │   STREAMLIT WEB APPLICATION     │
                     │   (Frontend + Backend chung     │
                     │    1 tien trinh Python)          │
                     │   -> trien khai tren:            │
                     │      CLOUD HOSTING               │
                     │      (Streamlit Community Cloud) │
                     └───────────────┬───────────────┘
                                     │ supabase-py client
                                     ▼
                     ┌───────────────────────────────┐
                     │           SUPABASE                │
                     │  ┌─────────────────────────────┐  │
                     │  │  CLOUD DATABASE (PostgreSQL)  │  │
                     │  │  - stops                       │  │
                     │  │  - routes                       │  │
                     │  │  - route_stops                   │  │
                     │  │  - search_logs                    │  │
                     │  └───────────────┬─────────────────┘  │
                     │                  │ tu dong sinh          │
                     │                  ▼                        │
                     │  ┌─────────────────────────────┐         │
                     │  │  CLOUD API (PostgREST)          │      │
                     │  │  REST endpoint cho moi bang,     │      │
                     │  │  goi qua thu vien supabase-py     │      │
                     │  └─────────────────────────────┘         │
                     │  ┌─────────────────────────────┐         │
                     │  │  CLOUD STORAGE                    │      │
                     │  │  Bucket "datasets" - sao luu       │      │
                     │  │  cac file CSV goc (stops/routes/   │      │
                     │  │  route_stops) phuc vu doi soat       │      │
                     │  │  va nap lai du lieu khi can          │      │
                     │  └─────────────────────────────┘         │
                     └───────────────────────────────┘
```

**4 thành phần Cloud có vai trò thực sự** (đạt "Mức tốt" theo yêu cầu học phần:
*Cloud Compute + Database + Storage + API*):

| # | Thành phần | Dịch vụ | Vai trò |
|---|---|---|---|
| 1 | Cloud Hosting / Compute | Streamlit Community Cloud | Chạy ứng dụng, cấp URL public, tự khởi động lại khi có commit mới |
| 2 | Cloud Database | Supabase (PostgreSQL) | Lưu trữ toàn bộ dữ liệu tuyến/trạm và ghi nhận log tìm kiếm của người dùng |
| 3 | Cloud API | Supabase PostgREST (qua `supabase-py`) | API REST tự sinh trên từng bảng, ứng dụng gọi qua HTTPS thay vì kết nối DB trực tiếp |
| 4 | Cloud Storage | Supabase Storage | Sao lưu/versioning bộ dataset CSV gốc |

## 2. Vì sao phải dùng Cloud (không chạy Local)?

- **Truy cập từ nhiều thiết bị**: sinh viên tra cứu từ điện thoại, không cần cài đặt gì, dữ liệu luôn đồng bộ.
- **Không phụ thuộc máy cá nhân**: nếu chạy Local, ứng dụng chỉ hoạt động khi máy của người tạo đang bật và cùng mạng — không thể dùng thực tế.
- **Dữ liệu tập trung, dễ cập nhật**: khi có tuyến mới/đổi giá vé, chỉ cần cập nhật 1 lần trên Supabase, mọi người dùng thấy ngay (không cần deploy lại app).
- **Khả năng mở rộng**: Supabase và Streamlit Cloud đều có thể nâng cấp gói khi lượng người dùng tăng, trong khi máy cá nhân bị giới hạn tài nguyên và băng thông.
- **Nếu bỏ Cloud**: ứng dụng vẫn "chạy được" nhờ cơ chế fallback đọc CSV cục bộ (`backend/datastore.py`), nhưng khi đó **mất khả năng nhiều người truy cập đồng thời, mất khả năng ghi log thống kê, và không có URL public** — tức là không còn là một sản phẩm Cloud Computing đúng nghĩa, chỉ là ứng dụng desktop chạy tạm.

## 3. Sơ đồ hệ thống (System Architecture)

```
USER
  │ nhap diem di / diem den
  ▼
[Streamlit UI - frontend/app.py]
  │ goi ham xu ly
  ▼
[RouteFinder - backend/route_finder.py]
  │ can du lieu tuyen/tram
  ▼
[DataStore - backend/datastore.py] ───(cloud)───► [Supabase: stops, routes, route_stops]
  │                                    │
  │ (fallback neu Supabase loi)        └─(ghi log)──► [Supabase: search_logs]
  ▼
[dataset/*.csv]
```

## 4. Thiết kế cơ sở dữ liệu (Database Design)

Xem chi tiết bảng/khoá tại [`er_diagram.md`](er_diagram.md) và schema thực thi tại
[`../database/schema.sql`](../database/schema.sql).

## 5. Chi phí vận hành dự kiến (Cost Estimation)

| Dịch vụ | Gói | Chi phí |
|---|---|---|
| Streamlit Community Cloud | Free tier | 0đ (giới hạn tài nguyên, đủ cho demo học phần) |
| Supabase | Free tier | 0đ (500MB database, 1GB storage, 2GB băng thông/tháng) |
| Tên miền / domain riêng | Không dùng | 0đ (dùng subdomain `*.streamlit.app` mặc định) |
| **Tổng** | | **0đ/tháng** ở quy mô demo; nếu mở rộng thực tế, Supabase Pro ~25 USD/tháng |

## 6. Bảo mật (Security Consideration)

- API key dùng phía client là **anon public key** của Supabase, chỉ có quyền theo Row Level Security (RLS) đã khai báo trong `schema.sql` (đọc công khai 4 bảng, ghi công khai riêng bảng `search_logs`) — không thể xoá/sửa dữ liệu tuyến.
- Không lưu bất kỳ thông tin cá nhân nhận dạng được (PII) của người dùng — `search_logs` chỉ lưu điểm đi/đến và thời điểm tìm kiếm, không lưu IP hay tài khoản.
- File `secrets.toml` chứa key thật **không** được commit lên GitHub (`.gitignore`); khi deploy, key được nhập trực tiếp vào mục Secrets của Streamlit Cloud (mã hoá phía nền tảng).
- Rủi ro còn tồn tại: anon key vẫn cho phép ghi vào `search_logs` từ bất kỳ client nào (có thể bị spam) — hướng khắc phục trong tương lai là thêm rate-limiting hoặc chuyển ghi log qua một Edge Function riêng thay vì gọi thẳng từ client.

## 7. Giới hạn hiện tại (Limitations)

1. Dữ liệu tuyến/trạm là **bộ mẫu biên soạn thủ công** theo cấu trúc GTFS (không phải dữ liệu GTFS chính thức của Sở GTVT/Trung tâm Quản lý GTCC TP.HCM).
2. Giờ xe đến trạm là **ước tính theo biểu đồ chạy chuẩn** (first/last departure + headway), chưa tích hợp GPS thời gian thực.
3. Thuật toán tìm tuyến giới hạn **tối đa 1 lần chuyển tuyến** để giữ đơn giản và dễ giải thích; mạng lưới thực tế lớn hơn có thể cần thuật toán Dijkstra/A* trên đồ thị thời gian đầy đủ.
4. Chưa có xác thực người dùng (authentication) vì bài toán không yêu cầu tài khoản cá nhân.

## 8b. Tính năng mở rộng (v2): bản đồ trực tiếp, đa thành phố, đa ngôn ngữ

- **Phạm vi 2 thành phố**: dữ liệu bao phủ cả TP.HCM (10 tuyến) và Biên Hòa - Đồng Nai
  (5 tuyến), phân biệt qua cột `city_id` trên `stops`/`routes`, người dùng lọc theo
  thành phố ở sidebar.
- **Tìm kiếm theo địa chỉ 2 lớp**: lớp 1 (chính, luôn hoạt động kể cả offline) là so
  khớp cục bộ không phân biệt dấu/hoa-thường với tên trạm (`backend/search.py`); lớp 2
  (bổ sung) là geocoding qua OpenStreetMap Nominatim miễn phí, không cần API key
  (`backend/geocoding.py`), dùng khi địa chỉ không khớp trực tiếp tên trạm nào.
- **Bản đồ trực tiếp kiểu BusMap**: toàn bộ trạm hiển thị dạng marker trên 1 bản đồ
  Folium lớn, tô màu theo thành phố; khi chọn 1 phương án di chuyển hoặc duyệt 1 tuyến,
  bản đồ vẽ polyline lộ trình + marker điểm đi/đến.
- **Mô phỏng xe chạy thời gian thực**: bật công tắc "Tự động cập nhật vị trí xe" để
  bản đồ tự làm mới mỗi 8 giây (`streamlit-autorefresh`), tính lại vị trí các "chuyến
  xe" đang chạy dựa trên biểu đồ chạy chuẩn (`backend/tracking.py`) và vẽ icon 🚌 di
  chuyển dọc lộ trình - **luôn ghi rõ đây là ước tính mô phỏng, không phải GPS thật**,
  vì hiện chưa có API GPS công khai miễn phí cho xe buýt tại Việt Nam.
- **Trạng thái hoạt động của tuyến**: mỗi tuyến hiển thị 🟢 (đang trong giờ chạy) hoặc
  ⚪ (ngoài giờ) dựa trên so sánh giờ hiện tại với `first_departure`/`last_departure`
  (`backend/schedule.is_route_active`).
- **Song ngữ Việt/Anh**: toàn bộ nhãn giao diện qua `backend/i18n.py`; tên trạm/tuyến có
  cả bản tiếng Việt có dấu và bản tiếng Anh (cột `*_name_en`) để phục vụ người dùng nước
  ngoài.
- **Giao diện tối/sáng**: chuyển đổi qua CSS tuỳ biến (`inject_theme_css` trong
  `frontend/app.py`) kèm đổi nền bản đồ (`cartodbpositron` / `cartodbdark_matter`); đây
  là giải pháp CSS override ở mức tốt nhất có thể trong giới hạn của Streamlit (không
  phải toàn bộ widget gốc của Streamlit đều đổi màu 100%, đã ghi nhận là giới hạn).

## 9. Hướng phát triển tiếp theo (Future Development)

- Tích hợp API GPS thời gian thực (nếu đơn vị vận hành xe buýt công khai) để thay thế ước tính theo biểu đồ chạy.
- Mở rộng thuật toán tìm tuyến cho phép nhiều hơn 1 lần chuyển tuyến, tối ưu theo cả thời gian lẫn số lần đi bộ.
- Thêm mô hình dự đoán độ trễ (xem [`../model/README.md`](../model/README.md)).
- Thêm định vị "tìm trạm gần nhất" bằng GPS trình duyệt thay vì chọn thủ công từ danh sách.
