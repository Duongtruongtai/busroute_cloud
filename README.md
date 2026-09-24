# 🚌 Smart City Bus Assistant

**Cổng tra cứu tuyến & ước tính thời gian xe buýt đô thị (TP.HCM)**
Đồ án học phần *Ứng dụng Điện toán đám mây giải quyết vấn đề thực tiễn*.

Sinh viên và người không có xe cá nhân phụ thuộc vào xe buýt nhưng gặp khó khăn khi
tra cứu thời gian xe đến trạm, các điểm trung chuyển hoặc tính toán chi phí di chuyển
tiết kiệm nhất. Ứng dụng cho phép nhập điểm đi/điểm đến, hệ thống gợi ý tuyến xe buýt
tối ưu (trực tiếp hoặc 1 lần chuyển tuyến), hiển thị lộ trình trên bản đồ và tính chi
phí vé (có ưu đãi sinh viên).

**➡️ Link ứng dụng (điền sau khi deploy):** `https://<ten-app>.streamlit.app`

### Tính năng chính (v2)

- 🏙️ **74 tuyến xe buýt & Metro TP.HCM — dữ liệu thực tế 2026** (TP.HCM sau khi sáp
  nhập Bình Dương và Bà Rịa - Vũng Tàu): giá vé, giờ chạy, giãn cách, quãng đường,
  đơn vị vận hành cho từng tuyến.
- 🗺️ **Bản đồ trực tiếp kiểu BusMap**: chọn tuyến/phương án để xem lộ trình.
- 🔎 **Tìm theo địa chỉ tự do**: gõ "Đại học Bách Khoa" hay "Bến Thành" vẫn ra đúng
  trạm gần nhất (so khớp cục bộ + geocoding OpenStreetMap dự phòng).
- 💰 **Tối ưu chi phí**: so sánh vé sinh viên/phổ thông giữa các phương án, kèm nhãn
  "có trợ giá HSSV" / "không trợ giá" giải thích vì sao vé một số tuyến cao hơn.
- 🔁 **Gợi ý điểm chuyển tuyến**: tìm tuyến trực tiếp hoặc tối đa 1 lần chuyển tuyến
  giữa 2 điểm bất kỳ.
- 🚌 **Mô phỏng xe chạy thời gian thực** trên bản đồ (tự làm mới mỗi 8s) — xem giải thích giới hạn ở mục 12.
- 🟢/⚪ **Trạng thái hoạt động của tuyến** theo giờ hiện tại.
- 🇻🇳/🇬🇧 **Song ngữ Việt - Anh**, đầy đủ dấu tiếng Việt.
- 🌙/☀️ **Giao diện tối/sáng**.

---

## 1. Kiến trúc Cloud

```
USER → Streamlit Web App (Cloud Hosting) → Supabase Cloud Database (PostgreSQL)
                                          → Supabase Cloud API (PostgREST)
                                          → Supabase Cloud Storage (backup dataset)
```

Chi tiết đầy đủ (sơ đồ, lý do dùng Cloud, chi phí, bảo mật, giới hạn) xem tại
[`docs/architecture.md`](docs/architecture.md). Thiết kế database xem tại
[`docs/er_diagram.md`](docs/er_diagram.md).

## 2. Cấu trúc thư mục

```
PROJECT/
├── frontend/
│   └── app.py                # Giao diện Streamlit (UI)
├── backend/
│   ├── datastore.py           # Lớp truy xuất dữ liệu (Supabase / fallback CSV)
│   ├── route_finder.py        # Thuật toán tìm tuyến (trực tiếp + 1 lần chuyển)
│   ├── schedule.py             # Ước tính giờ xe đến trạm + trạng thái hoạt động tuyến
│   ├── tracking.py              # Mô phỏng vị trí xe buýt theo thời gian thực
│   ├── search.py                 # Tìm kiếm trạm cục bộ (không phân biệt dấu)
│   ├── geocoding.py               # Định vị địa chỉ tự do qua OpenStreetMap (dự phòng)
│   ├── i18n.py                     # Chuỗi đa ngôn ngữ Việt/Anh
│   └── fare.py                      # Hằng số & định dạng giá vé
├── database/
│   ├── schema.sql               # Script tạo bảng + RLS cho Supabase
│   └── seed_supabase.py         # Script nạp dataset lên Supabase
├── DATA BUS HCM/                # Dữ liệu gốc THẬT (74 tuyến TP.HCM, 2026) - xem mục 14
├── dataset/
│   ├── build_hcm_dataset.py     # Script chuyển dữ liệu gốc -> stops/routes/route_stops.csv
│   ├── geocode_cache.json       # Cache toạ độ điểm mốc (Photon/OSM) - commit kèm để tái tạo offline
│   ├── stops.csv
│   ├── routes.csv
│   └── route_stops.csv
├── model/
│   └── README.md                 # Ghi chú: đề tài không dùng AI/ML + hướng mở rộng
├── docs/
│   ├── architecture.md
│   ├── er_diagram.md
│   └── test_cases.md
├── tests/
│   └── test_route_finder.py
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
├── requirements.txt
└── README.md
```

## 3. Yêu cầu môi trường

- Python 3.10+
- Tài khoản [Supabase](https://supabase.com) (miễn phí)
- Tài khoản [GitHub](https://github.com) + [Streamlit Community Cloud](https://streamlit.io/cloud) (miễn phí) để deploy

## 4. Chạy thử ở máy cá nhân (trước khi có Cloud Database)

Ứng dụng có cơ chế fallback: nếu chưa cấu hình Supabase, tự động dùng dữ liệu CSV
trong `dataset/` để bạn có thể chạy thử ngay.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run frontend/app.py
```

Mở trình duyệt tại `http://localhost:8501`. Sidebar sẽ hiện badge màu **vàng**
("Đang dùng dữ liệu cục bộ") — đây là bước kiểm tra nhanh trước khi qua bước 5.

Chạy test tự động cho thuật toán tìm tuyến:

```bash
python tests/test_route_finder.py
```

## 5. Thiết lập Cloud Database (Supabase) — bắt buộc để đạt điểm tối đa Cloud Architecture

> Nếu bạn đã có project Supabase rồi (project ref dạng `xxxxxxxxxxxxx`), Project URL của
> bạn là `https://<project-ref>.supabase.co` — bỏ qua Bước 1, làm tiếp từ Bước 2.
> Schema (`database/schema.sql`) an toàn khi chạy lại nhiều lần (dùng
> `create table if not exists` + `alter table add column if not exists`).

### Bước 1 — Tạo project

1. Vào https://supabase.com → **Sign up** (có thể đăng nhập bằng GitHub) → **New project**.
2. Đặt tên project (vd `busroute-cloud`), đặt mật khẩu database, chọn region gần nhất
   (Singapore khuyến nghị cho tốc độ với người dùng Việt Nam).
3. Đợi ~2 phút để Supabase khởi tạo hạ tầng (Cloud Compute + PostgreSQL).

### Bước 2 — Tạo bảng dữ liệu

1. Trong project vừa tạo, vào menu **SQL Editor** → **New query**.
2. Mở file [`database/schema.sql`](database/schema.sql), copy toàn bộ nội dung,
   dán vào SQL Editor rồi bấm **Run**.
3. Vào menu **Table Editor**, kiểm tra đã có 4 bảng: `stops`, `routes`, `route_stops`, `search_logs`.

### Bước 3 — Lấy API key

1. Vào **Project Settings** (icon bánh răng) → **API**.
2. Ghi lại 2 giá trị:
   - **Project URL** → dùng làm `SUPABASE_URL`
   - **anon public** key → dùng làm `SUPABASE_KEY` (dùng cho app, đã giới hạn quyền qua RLS)
   - **service_role** key → chỉ dùng cho bước seed dữ liệu bên dưới, **không đưa vào app/secrets.toml**

### Bước 4 — Nạp (seed) dữ liệu mẫu lên Supabase

```bash
# PowerShell
$env:SUPABASE_URL = "https://xxxxx.supabase.co"
$env:SUPABASE_KEY = "<service_role key>"
python database/seed_supabase.py
```

Kỳ vọng thấy log `Hoan tat! Du lieu da san sang tren Supabase.` — kiểm tra lại trong
**Table Editor** thấy đã có 60 dòng `stops`, 10 dòng `routes`, ~73 dòng `route_stops`.

### Bước 5 — Cấu hình app dùng Supabase (local)

```bash
copy .streamlit\secrets.toml.example .streamlit\secrets.toml   # Windows
# hoặc: cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Mở `.streamlit/secrets.toml` vừa tạo, điền `SUPABASE_URL` và **anon public key** (không
phải service_role) đã lấy ở Bước 3. Chạy lại:

```bash
streamlit run frontend/app.py
```

Badge sidebar phải chuyển sang màu **xanh** ("Đang kết nối Cloud Database (Supabase)").
File `secrets.toml` **không** được commit lên Git (đã có trong `.gitignore`).

## 6. Cloud Storage (Supabase Storage) — đã cấu hình

Bucket công khai `datasets` đã được tạo và chứa bản sao lưu 3 file dữ liệu gốc:

- https://pieplfirsanegkuxojch.supabase.co/storage/v1/object/public/datasets/stops.csv
- https://pieplfirsanegkuxojch.supabase.co/storage/v1/object/public/datasets/routes.csv
- https://pieplfirsanegkuxojch.supabase.co/storage/v1/object/public/datasets/route_stops.csv

Vai trò: sao lưu/versioning dataset, tải lại dữ liệu gốc qua HTTPS/CDN. Khi seed lại dữ liệu,
chạy lệnh upload trong `docs/gen_report_buoi4.py` hoặc kéo-thả file mới trên Supabase Dashboard
→ **Storage** → bucket `datasets`.

## 7. Deploy lên Cloud Hosting (Streamlit Community Cloud)

### Bước 1 — Code đã có trên GitHub

Repo: **https://github.com/Duongtruongtai/busroute_cloud** (branch `master`).
Mỗi khi sửa code, đẩy bản mới bằng:

```bash
git add .
git commit -m "Mo ta thay doi"
git push
```

> Kiểm tra kỹ `.gitignore` đã loại `secrets.toml` trước khi push — **không** để lộ API key thật.

### Bước 2 — Deploy

1. Vào https://share.streamlit.io → **Sign in with GitHub** → **New app**.
2. Chọn repo `busroute_cloud`, branch `master`, **Main file path** = `frontend/app.py`.
3. Mở **Advanced settings → Secrets**, dán nội dung giống `.streamlit/secrets.toml`:
   ```toml
   SUPABASE_URL = "https://xxxxx.supabase.co"
   SUPABASE_KEY = "eyJhbGciOi..."
   ```
4. Bấm **Deploy**. Sau ~1-2 phút, ứng dụng có URL dạng `https://<ten-app>.streamlit.app`.
5. Mở URL, xác nhận badge sidebar hiện màu xanh (đang chạy Cloud Database thật) —
   **đây là URL dùng khi demo, KHÔNG dùng localhost khi bảo vệ đồ án.**

## 8. Sử dụng ứng dụng

1. Ở tab **🔍 Tra cứu tuyến**: chọn điểm đi, điểm đến (gõ để lọc nhanh trong danh sách),
   chọn loại vé (sinh viên/phổ thông), bấm **Tìm tuyến xe buýt**.
2. Chọn 1 trong các phương án gợi ý để xem chi tiết từng chặng, giờ xe dự kiến đến trạm,
   giá vé, và bản đồ hành trình.
3. Tab **📊 Thống kê**: xem top trạm trung chuyển nhiều tuyến, danh sách toàn bộ tuyến,
   và (khi đã kết nối Cloud) thống kê lượt tìm kiếm thực tế của người dùng.

## 9. Kiểm thử

Danh sách test case đầy đủ + kết quả: [`docs/test_cases.md`](docs/test_cases.md).

## 10. Giới hạn & hướng phát triển

Xem mục 7–8 trong [`docs/architecture.md`](docs/architecture.md).

## 11. Nguồn dữ liệu

Dữ liệu gốc trong [`DATA BUS HCM/`](DATA%20BUS%20HCM/) là dữ liệu THẬT: 74 tuyến xe
buýt & Metro TP.HCM (2026, sau khi TP.HCM sáp nhập Bình Dương và Bà Rịa - Vũng Tàu) —
tên tuyến, đơn vị vận hành, giá vé, giờ chạy, giãn cách, quãng đường, và danh sách
điểm mốc (landmark) theo thứ tự dọc từng tuyến. Bộ dữ liệu gốc **không** có toạ độ
từng trạm — script [`dataset/build_hcm_dataset.py`](dataset/build_hcm_dataset.py)
định vị (geocode) từng điểm mốc qua Photon/OpenStreetMap (kết quả cache trong
`dataset/geocode_cache.json`), dùng thứ tự điểm mốc làm thứ tự trạm trên tuyến, và
quy đổi thời gian tích luỹ mỗi trạm theo đúng `trip_duration_min` thực tế của tuyến.
Vì vậy toạ độ trạm là **ước lượng theo địa danh** (gần đúng vị trí thật, không phải
toạ độ GPS trạm dừng chính thức) — đủ chính xác để minh hoạ tra cứu/bản đồ cho đồ án
học phần. Điểm mốc không định vị được sẽ được nội suy vị trí tương đối trong tuyến;
tuyến không định vị được tối thiểu 2 điểm mốc sẽ không xuất hiện trên bản đồ/tra cứu
(vẫn hiển thị trong bảng thống kê tuyến). Chạy lại script này khi cần tái tạo dataset:

```bash
python dataset/build_hcm_dataset.py
```
