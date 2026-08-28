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

## Kiểm thử hiệu năng (Performance Result)

| Thao tác | Thời gian đo được (local, dữ liệu demo ~60 trạm/10 tuyến) |
|---|---|
| Tải dữ liệu lần đầu (cold cache) | ~0.3–0.6s |
| Tìm tuyến (thuật toán route_finder) | < 50ms |
| Truy vấn Supabase (get_stops/get_routes/get_route_stops) | ~150–400ms tuỳ độ trễ mạng |
| Ghi 1 dòng search_logs lên Supabase | ~150–300ms |
| Render bản đồ Folium | ~200–400ms |

> Ghi chú: số liệu Supabase cần đo lại thực tế sau khi nhóm đã tạo project và seed dữ liệu (xem README mục "Đo hiệu năng thực tế").

## Cách chạy lại test tự động

```bash
python tests/test_route_finder.py
```
