# model/

Đề tài này **không sử dụng mô hình AI/ML** ở phiên bản hiện tại — chức năng gợi ý
tuyến tối ưu được giải quyết bằng thuật toán tìm đường theo đồ thị tuyến-trạm
(graph search cổ điển: tuyến trực tiếp → tối đa 1 lần chuyển tuyến), cài đặt tại
[`backend/route_finder.py`](../backend/route_finder.py). Thư mục này được giữ lại
để khớp với cấu trúc thư mục chuẩn của học phần.

## Hướng phát triển AI/ML (Future Work)

Nếu phát triển tiếp, có thể bổ sung mô hình dự đoán trong thư mục này, ví dụ:

- **Dự đoán thời gian trễ chuyến** dựa trên dữ liệu lịch sử `search_logs` +
  khung giờ cao điểm/thấp điểm (hồi quy đơn giản hoặc time-series).
- **Xếp hạng tuyến theo mức độ đông đúc dự kiến** dựa trên tần suất tìm kiếm
  lịch sử để gợi ý khung giờ đi lại tối ưu cho sinh viên.
- **Gợi ý điểm trung chuyển tối ưu bằng Reinforcement Learning** thay cho
  thuật toán tham lam hiện tại khi mạng lưới tuyến mở rộng lớn hơn nhiều.

Khi có mô hình thật, kiến trúc Cloud sẽ mở rộng thành:

```
USER -> Web App -> Cloud API -> AI MODEL -> Database -> Result
```
