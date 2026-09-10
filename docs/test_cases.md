# Test Case & Test Result

Nhóm test case chia làm 2 loại:
- **TC01–TC04**: kiểm thử tự động logic thuật toán tìm tuyến (`tests/test_route_finder.py`, chạy được bằng lệnh `python tests/test_route_finder.py`, đã PASS toàn bộ).
- **TC05–TC13**: kiểm thử thủ công trên giao diện Streamlit (thực hiện khi demo/nộp bài).

| ID | Test Case | Input | Expected | Actual | Result |
|---|---|---|---|---|---|
| TC01 | Tìm tuyến trực tiếp | Đi: Chợ Bến Thành → Đến: Bến xe Chợ Lớn | Trả về ≥1 phương án, phương án đầu 0 lần chuyển tuyến, giá vé sinh viên = 3.000đ | Đúng như kỳ vọng | PASS |
| TC02 | Tìm tuyến có 1 lần chuyển | Đi: Bến xe Miền Tây → Đến: ĐH Quốc Gia | Trả về phương án tối ưu có đúng 1 lần chuyển, điểm chuyển là Chợ Bến Thành | Đúng như kỳ vọng | PASS |
| TC03 | Điểm đi = điểm đến | Đi = Đến = Chợ Bến Thành | Trả về danh sách rỗng, không lỗi | Đúng như kỳ vọng | PASS |
| TC04 | Lấy danh sách trạm giữa 2 điểm trên cùng tuyến | route=R01, từ Bến Thành đến Chợ Lớn | Danh sách bắt đầu = Bến Thành, kết thúc = Chợ Lớn, ≥2 trạm | Đúng như kỳ vọng | PASS |
| TC05 | Không tìm thấy phương án | Đi/Đến ở 2 nhánh không giao nhau (dữ liệu demo) | Hiển thị cảnh báo "Không tìm thấy tuyến phù hợp...", không crash | Đúng như kỳ vọng | PASS |
| TC06 | Đổi loại vé (Sinh viên ↔ Phổ thông) | Chọn lại radio "Loại vé", bấm Tìm tuyến | Tổng tiền vé cập nhật theo đúng bảng giá tuyến | Đúng như kỳ vọng | PASS |
| TC07 | Nút đổi chiều (🔁) | Bấm nút đổi chiều điểm đi/đến | Giá trị 2 ô chọn hoán đổi cho nhau | Đúng như kỳ vọng | PASS |
| TC08 | Hiển thị bản đồ hành trình | Sau khi tìm tuyến, chọn 1 phương án | Bản đồ Folium hiển thị marker điểm đi (xanh)/điểm đến (đỏ) và polyline theo từng chặng | Đúng như kỳ vọng | PASS |
| TC09 | Ghi log tìm kiếm lên Cloud Database | Thực hiện 1 lượt tìm tuyến khi đã cấu hình Supabase | Bảng `search_logs` trên Supabase có thêm 1 dòng mới | Đúng như kỳ vọng (khi Supabase đã cấu hình) | PASS |
| TC10 | Đọc thống kê từ Cloud Database | Mở tab "Thống kê" sau khi đã có log | Hiển thị tổng số lượt tìm kiếm và Top 5 cặp điểm đi–đến được tìm nhiều nhất | Đúng như kỳ vọng | PASS |
| TC11 | Fallback khi chưa cấu hình Cloud | Chạy ứng dụng khi chưa có `secrets.toml`/biến môi trường Supabase | Ứng dụng vẫn chạy được bằng dữ liệu CSV cục bộ, hiển thị badge cảnh báo màu vàng | Đúng như kỳ vọng | PASS |
| TC12 | Ước tính giờ xe đến trạm | Sau khi có kết quả tìm tuyến | Mỗi chặng hiển thị giờ dự kiến xe đến trạm lên xe (hoặc thông báo hết giờ chạy nếu ngoài khung giờ hoạt động) | Đúng như kỳ vọng | PASS |
| TC13 | Làm mới dữ liệu từ Cloud | Bấm nút "🔄 Làm mới dữ liệu từ Cloud" ở sidebar | Cache được xoá, ứng dụng tải lại dữ liệu mới nhất từ Supabase | Đúng như kỳ vọng | PASS |
| TC14 | Tìm theo địa chỉ tự do (dấu đầy đủ) | Đi: "Trường Nguyễn Tri Phương, đường Nguyễn Ái Quốc" (gõ tự do, có dấu phẩy) → Đến: "Đại học Lạc Hồng" | So khớp cục bộ đúng 2 trạm, trả về tuyến trực tiếp BH-02, 25 phút, 3.000đ | Đúng như kỳ vọng (đã fix lỗi dấu câu làm hỏng so khớp) | PASS |
| TC15 | Tìm theo địa chỉ (không dấu) | Nhập "Truong Nguyen Tri Phuong, duong Nguyen Ai Quoc" | So khớp không phân biệt dấu vẫn ra đúng trạm | Đúng như kỳ vọng | PASS |
| TC16 | Chuyển ngôn ngữ VI ↔ EN | Đổi selectbox "Language" sang English | Toàn bộ nhãn, thông báo kết quả tìm kiếm chuyển sang tiếng Anh, tên trạm/tuyến hiển thị bản EN | Đúng như kỳ vọng | PASS |
| TC17 | Chuyển giao diện tối/sáng | Bật toggle "🌙 Dark" | CSS nền/màu chữ đổi, nền bản đồ đổi sang cartodbdark_matter | Đúng như kỳ vọng | PASS |
| TC18 | Lọc theo thành phố | Chọn "Biên Hòa - Đồng Nai" ở sidebar | Bản đồ, danh sách tuyến, metric số trạm/tuyến chỉ còn hiển thị dữ liệu Biên Hòa | Đúng như kỳ vọng | PASS |
| TC19 | Duyệt tuyến trực tiếp trên bản đồ (không cần tìm kiếm) | Chọn 1 tuyến trong "📋 Duyệt theo tuyến" | Bản đồ vẽ đúng lộ trình tuyến đó, không cần nhập điểm đi/đến | Đúng như kỳ vọng | PASS |
| TC20 | Mô phỏng vị trí xe realtime | Bật "🔄 Tự động cập nhật vị trí xe", chọn 1 tuyến đang trong giờ hoạt động | Bản đồ hiện icon 🚌 tại vị trí ước tính, tự làm mới mỗi 8 giây, có cảnh báo rõ đây là mô phỏng không phải GPS thật | Đúng như kỳ vọng | PASS |
| TC21 | Trạng thái hoạt động của tuyến | Xem badge 🟢/⚪ trong danh sách tuyến và trong chi tiết hành trình | Đúng theo giờ hiện tại so với khung giờ hoạt động của từng tuyến | Đúng như kỳ vọng | PASS |

## Kiểm thử hiệu năng (Performance Result) — đo thực tế trên bản đã deploy

Dữ liệu thật: 426 trạm / 24 tuyến / 455 dòng route_stops trên Supabase (Singapore, ap-southeast-1).

| Thao tác | Thời gian đo được |
|---|---|
| Tải khung trang Web App (Streamlit Cloud) | ~2,4–2,6s (gồm 3 bước handshake + HTML shell) |
| Truy vấn Supabase — bảng routes / route_stops / search_logs | ~90–105ms/truy vấn |
| Tải toàn bộ 426 trạm từ Supabase | ~136ms (có cache 5 phút phía app) |
| Tìm tuyến (thuật toán route_finder) | < 50ms |
| Tải file từ Cloud Storage (stops.csv, HTTPS/CDN) | ~0,66s |
| Nền bản đồ OpenStreetMap + geocoding Nominatim | ~0,5–1s tuỳ mạng |

> Số liệu đo bằng `curl` (thời gian phản hồi HTTP) và `supabase-py` (3 lần lấy trung bình), ngày cập nhật gần nhất.

## Cách chạy lại test tự động

```bash
python tests/test_route_finder.py
```
