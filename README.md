# 🚌 Smart City Bus Assistant

**Cổng tra cứu tuyến & ước tính thời gian xe buýt đô thị (TP.HCM)**
Đồ án học phần *Ứng dụng Điện toán đám mây giải quyết vấn đề thực tiễn*.

Sinh viên và người không có xe cá nhân phụ thuộc vào xe buýt nhưng gặp khó khăn khi
tra cứu thời gian xe đến trạm, các điểm trung chuyển hoặc tính toán chi phí di chuyển
tiết kiệm nhất. Ứng dụng cho phép nhập điểm đi/điểm đến, hệ thống gợi ý tuyến xe buýt
tối ưu (trực tiếp hoặc 1 lần chuyển tuyến), hiển thị lộ trình trên bản đồ và tính chi
phí vé (có ưu đãi sinh viên).

**➡️ Link ứng dụng (điền sau khi deploy):** `https://<ten-app>.streamlit.app`

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
│   ├── schedule.py             # Ước tính giờ xe đến trạm theo biểu đồ chạy
│   └── fare.py                  # Hằng số & định dạng giá vé
├── database/
│   ├── schema.sql               # Script tạo bảng + RLS cho Supabase
│   └── seed_supabase.py         # Script nạp dataset lên Supabase
├── dataset/
│   ├── generate_dataset.py      # Script sinh dataset mẫu (đã chạy sẵn)
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

## 6. Đưa dataset lên Cloud Storage (Supabase Storage)

1. Trong Supabase Dashboard → **Storage** → **New bucket** → đặt tên `datasets` → Public bucket.
2. Upload 3 file `dataset/stops.csv`, `dataset/routes.csv`, `dataset/route_stops.csv` vào bucket này
   (kéo-thả trên giao diện web).
3. Đây là bản sao lưu/versioning của dataset gốc — dùng làm bằng chứng "Cloud Storage có vai trò
   thực tế" khi bảo vệ đồ án (mục 4 - Cloud Architecture, 15 điểm).

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
4. Tab **ℹ️ Giới thiệu**: tóm tắt vấn đề, giải pháp, kiến trúc Cloud — dùng lại nội dung
   này cho báo cáo/slide.

## 9. Kiểm thử

Danh sách test case đầy đủ + kết quả: [`docs/test_cases.md`](docs/test_cases.md).

## 10. Giới hạn & hướng phát triển

Xem mục 7–8 trong [`docs/architecture.md`](docs/architecture.md).

## 11. Nguồn dữ liệu

Bộ dữ liệu mẫu (`dataset/`) được biên soạn thủ công theo cấu trúc chuẩn GTFS
(`stops.txt`, `routes.txt`, `stop_times.txt` rút gọn thành 3 file CSV), dựa trên số hiệu
tuyến và các điểm đầu-cuối (bến xe, trường học, sân bay) công khai tại TP.HCM; toạ độ các
trạm trung gian được nội suy tuyến tính để phục vụ minh hoạ cho đồ án học phần — **không**
phải trích xuất trực tiếp từ GTFS chính thức. Script sinh dữ liệu:
[`dataset/generate_dataset.py`](dataset/generate_dataset.py).
