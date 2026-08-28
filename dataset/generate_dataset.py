# -*- coding: utf-8 -*-
"""
Sinh dataset mẫu (stops.csv, routes.csv, route_stops.csv) cho dự án
Smart City Bus Assistant - Cổng tra cứu tuyến & ước tính thời gian xe buýt
TP. Hồ Chí Minh và Biên Hòa (Đồng Nai).

Nguồn gốc dữ liệu:
- Số hiệu tuyến, tên tuyến, điểm đầu/cuối (bến xe, trường học, bệnh viện,
  khu công nghiệp, sân bay...) tham khảo các địa danh có thật tại TP.HCM và
  Biên Hòa - Đồng Nai.
- Toạ độ các trạm trung gian được NỘI SUY (interpolate) tuyến tính giữa các
  điểm neo (hub) thực tế để phục vụ minh hoạ cho đồ án học phần, KHÔNG phải
  dữ liệu GTFS chính thức của cơ quan quản lý giao thông công cộng.
- Thời gian chạy giữa các trạm ước tính theo tốc độ khai thác bình quân xe
  buýt nội đô (đã bao gồm thời gian dừng trạm).

Chạy: python dataset/generate_dataset.py
Kết quả: stops.csv, routes.csv, route_stops.csv trong cùng thư mục dataset/
"""
import csv
import math
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Mỗi hub: key -> (tên tiếng Việt, tên tiếng Anh, lat, lon, city_id)
HUBS = {
    # ---- TP. Hồ Chí Minh ----
    "BEN_THANH": ("Chợ Bến Thành", "Ben Thanh Market", 10.7724, 106.6980, "hcmc"),
    "MIEN_DONG": ("Bến xe Miền Đông mới", "New Mien Dong Bus Station", 10.8657, 106.7735, "hcmc"),
    "MIEN_TAY": ("Bến xe Miền Tây", "Mien Tay Bus Station", 10.7398, 106.6180, "hcmc"),
    "CV_23_9": ("Công viên 23/9", "23/9 Park", 10.7690, 106.6928, "hcmc"),
    "DHQG": ("Đại học Quốc Gia TP.HCM", "Vietnam National University HCMC", 10.8700, 106.8030, "hcmc"),
    "CHO_LON": ("Bến xe Chợ Lớn", "Cho Lon Bus Station", 10.7493, 106.6512, "hcmc"),
    "TSN": ("Sân bay Tân Sơn Nhất", "Tan Son Nhat Airport", 10.8189, 106.6520, "hcmc"),
    "PMH": ("Khu đô thị Phú Mỹ Hưng", "Phu My Hung Urban Area", 10.7291, 106.7183, "hcmc"),
    "BACH_KHOA": ("Đại học Bách Khoa", "HCMC University of Technology", 10.7725, 106.6577, "hcmc"),
    "SU_PHAM": ("Đại học Sư Phạm TP.HCM", "HCMC University of Education", 10.7599, 106.6822, "hcmc"),
    "Q8": ("Bến xe Quận 8", "District 8 Bus Station", 10.7385, 106.6650, "hcmc"),
    "SUOI_TIEN": ("Khu du lịch Suối Tiên", "Suoi Tien Tourist Park", 10.8623, 106.8022, "hcmc"),

    # ---- Biên Hòa - Đồng Nai ----
    "BX_BIEN_HOA": ("Bến xe Biên Hòa", "Bien Hoa Bus Station", 10.9420, 106.8460, "bienhoa"),
    "GA_BIEN_HOA": ("Ga Biên Hòa", "Bien Hoa Railway Station", 10.9368, 106.8496, "bienhoa"),
    "CHO_BIEN_HOA": ("Chợ Biên Hòa", "Bien Hoa Market", 10.9447, 106.8235, "bienhoa"),
    "CV_BIEN_HUNG": ("Công viên Biên Hùng", "Bien Hung Park", 10.9490, 106.8290, "bienhoa"),
    "DH_LAC_HONG": ("Đại học Lạc Hồng", "Lac Hong University", 10.9553, 106.8081, "bienhoa"),
    "DH_DONG_NAI": ("Đại học Đồng Nai", "Dong Nai University", 10.9490, 106.8330, "bienhoa"),
    "BV_DONG_NAI": ("Bệnh viện Đa khoa Đồng Nai", "Dong Nai General Hospital", 10.9463, 106.8386, "bienhoa"),
    "NGA_TU_VUNG_TAU": ("Ngã tư Vũng Tàu", "Vung Tau Junction", 10.9633, 106.8636, "bienhoa"),
    "KCN_BIEN_HOA_1": ("Khu công nghiệp Biên Hòa 1", "Bien Hoa Industrial Park 1", 10.9310, 106.8330, "bienhoa"),
    "KCN_BIEN_HOA_2": ("Khu công nghiệp Biên Hòa 2", "Bien Hoa Industrial Park 2", 10.9575, 106.8555, "bienhoa"),
    "TRUONG_NGUYEN_TRI_PHUONG": ("Trường Nguyễn Tri Phương (đường Nguyễn Ái Quốc)",
                                  "Nguyen Tri Phuong School (Nguyen Ai Quoc St.)", 10.9750, 106.8590, "bienhoa"),
    "VINCOM_BIEN_HOA": ("Vincom Plaza Biên Hòa", "Vincom Plaza Bien Hoa", 10.9490, 106.8425, "bienhoa"),
}

# route_id, số hiệu, tên tuyến (VI), tên tuyến (EN), [chuỗi hub theo thứ tự],
# tên đường (VI), tên đường (EN), số trạm trung gian giữa MỖI cặp hub,
# giá vé phổ thông, giá vé sinh viên, giãn cách chạy (phút), giờ chạy đầu, giờ chạy cuối
ROUTES = [
    # ---- TP. Hồ Chí Minh ----
    ("R01", "01", "Bến Thành - Bến xe Chợ Lớn", "Ben Thanh - Cho Lon Bus Station",
     ["BEN_THANH", "CHO_LON"], "Trần Hưng Đạo", "Tran Hung Dao St.",
     3, 6000, 3000, 10, "05:00", "20:30"),
    ("R08", "08", "Bến xe Quận 8 - Đại học Quốc Gia", "District 8 - Vietnam National University",
     ["Q8", "BEN_THANH", "DHQG"], "Nguyễn Thị Thập - Xa lộ Hà Nội", "Nguyen Thi Thap - Ha Noi Highway",
     3, 6000, 3000, 15, "05:00", "20:00"),
    ("R10", "10", "Đại học Quốc Gia - Bến xe Chợ Lớn", "Vietnam National University - Cho Lon",
     ["DHQG", "BACH_KHOA", "CHO_LON"], "Lý Thường Kiệt", "Ly Thuong Kiet St.",
     3, 6000, 3000, 15, "05:00", "20:00"),
    ("R19", "19", "Bến Thành - Đại học Quốc Gia (qua Suối Tiên)", "Ben Thanh - VNU-HCM (via Suoi Tien)",
     ["BEN_THANH", "SUOI_TIEN", "DHQG"], "Xa lộ Hà Nội", "Ha Noi Highway",
     4, 7000, 3000, 12, "05:00", "21:00"),
    ("R30", "30", "Bến xe Chợ Lớn - Sân bay Tân Sơn Nhất", "Cho Lon - Tan Son Nhat Airport",
     ["CHO_LON", "TSN"], "Lý Thường Kiệt - Trường Chinh", "Ly Thuong Kiet - Truong Chinh St.",
     3, 6000, 3000, 15, "05:30", "20:00"),
    ("R152", "152", "Sân bay Tân Sơn Nhất - Bến Thành", "Tan Son Nhat Airport - Ben Thanh",
     ["TSN", "BEN_THANH"], "Trường Sơn - Nguyễn Văn Trỗi", "Truong Son - Nguyen Van Troi St.",
     3, 6000, 3000, 10, "05:00", "21:30"),
    ("R88", "88", "Bến Thành - Phú Mỹ Hưng", "Ben Thanh - Phu My Hung",
     ["BEN_THANH", "PMH"], "Nguyễn Hữu Thọ", "Nguyen Huu Tho St.",
     3, 6000, 3000, 15, "05:30", "20:00"),
    ("R93", "93", "Bến xe Miền Đông mới - Bến xe Miền Tây", "New Mien Dong - Mien Tay Bus Station",
     ["MIEN_DONG", "BEN_THANH", "MIEN_TAY"], "Điện Biên Phủ", "Dien Bien Phu St.",
     4, 7000, 3000, 15, "04:30", "20:30"),
    ("R45", "45", "Bến Thành - Đại học Sư Phạm", "Ben Thanh - HCMC University of Education",
     ["BEN_THANH", "SU_PHAM"], "Cách Mạng Tháng 8", "Cach Mang Thang 8 St.",
     2, 6000, 3000, 15, "05:00", "19:30"),
    ("R36", "36", "Bến xe Miền Tây - Bến Thành", "Mien Tay Bus Station - Ben Thanh",
     ["MIEN_TAY", "CV_23_9", "BEN_THANH"], "Hùng Vương", "Hung Vuong St.",
     3, 6000, 3000, 12, "05:00", "20:00"),

    # ---- Biên Hòa - Đồng Nai ----
    ("BH01", "BH-01", "Bến xe Biên Hòa - Chợ Biên Hòa", "Bien Hoa Bus Station - Bien Hoa Market",
     ["BX_BIEN_HOA", "GA_BIEN_HOA", "CHO_BIEN_HOA"], "Cách Mạng Tháng Tám", "Cach Mang Thang Tam St.",
     3, 6000, 3000, 15, "05:00", "19:30"),
    ("BH02", "BH-02", "Ga Biên Hòa - Đại học Lạc Hồng (qua Nguyễn Ái Quốc)",
     "Bien Hoa Railway Station - Lac Hong University (via Nguyen Ai Quoc)",
     ["GA_BIEN_HOA", "TRUONG_NGUYEN_TRI_PHUONG", "BX_BIEN_HOA", "CV_BIEN_HUNG", "DH_DONG_NAI", "DH_LAC_HONG"],
     "Nguyễn Ái Quốc - Huỳnh Văn Nghệ", "Nguyen Ai Quoc - Huynh Van Nghe St.",
     2, 8000, 3000, 20, "05:00", "19:30"),
    ("BH03", "BH-03", "Ngã tư Vũng Tàu - Ga Biên Hòa (qua KCN Biên Hòa 2)",
     "Vung Tau Junction - Bien Hoa Railway Station (via Industrial Park 2)",
     ["NGA_TU_VUNG_TAU", "KCN_BIEN_HOA_2", "GA_BIEN_HOA"], "Đồng Khởi", "Dong Khoi St.",
     3, 7000, 3000, 20, "05:00", "19:00"),
    ("BH04", "BH-04", "Chợ Biên Hòa - Bệnh viện Đa khoa Đồng Nai", "Bien Hoa Market - Dong Nai General Hospital",
     ["CHO_BIEN_HOA", "DH_DONG_NAI", "BV_DONG_NAI"], "Đồng Khởi", "Dong Khoi St.",
     3, 6000, 3000, 20, "05:00", "19:30"),
    ("BH05", "BH-05", "Khu công nghiệp Biên Hòa 1 - Vincom Plaza",
     "Industrial Park 1 - Vincom Plaza Bien Hoa",
     ["KCN_BIEN_HOA_1", "CV_BIEN_HUNG", "VINCOM_BIEN_HOA"], "Bùi Văn Hòa - Đồng Khởi", "Bui Van Hoa - Dong Khoi St.",
     3, 6000, 3000, 20, "05:00", "19:00"),
]

AVG_SPEED_KMH = 22.0  # tốc độ khai thác bình quân (đã tính thời gian dừng trạm)


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def main():
    stop_registry = {}  # stop_id -> [stop_id, stop_name, stop_name_en, lat, lon, is_hub, city_id]
    route_rows = []
    route_stop_rows = []

    def register_stop(stop_id, name_vi, name_en, lat, lon, is_hub, city_id):
        if stop_id not in stop_registry:
            stop_registry[stop_id] = [stop_id, name_vi, name_en, round(lat, 6), round(lon, 6),
                                       "1" if is_hub else "0", city_id]

    for (route_id, short_name, long_name_vi, long_name_en, hub_seq, street_vi, street_en, n_between,
         fare_regular, fare_student, headway, first_dep, last_dep) in ROUTES:

        city_id = HUBS[hub_seq[0]][4]
        route_rows.append([route_id, short_name, long_name_vi, long_name_en, city_id,
                            fare_regular, fare_student, headway, first_dep, last_dep])

        seq = 1
        cum_time = 0.0
        prev_hub_id = hub_seq[0]
        prev_name_vi, prev_name_en, prev_lat, prev_lon, _ = HUBS[prev_hub_id]
        register_stop(prev_hub_id, prev_name_vi, prev_name_en, prev_lat, prev_lon, True, city_id)
        route_stop_rows.append([route_id, prev_hub_id, seq, round(cum_time)])
        seq += 1

        for hub_id in hub_seq[1:]:
            name_vi, name_en, lat, lon, _ = HUBS[hub_id]
            dist = haversine_km(prev_lat, prev_lon, lat, lon)
            seg_time = dist / AVG_SPEED_KMH * 60.0

            for i in range(1, n_between + 1):
                frac = i / (n_between + 1)
                ilat = prev_lat + (lat - prev_lat) * frac
                ilon = prev_lon + (lon - prev_lon) * frac
                itime = cum_time + seg_time * frac
                istop_id = f"{route_id}_S{seq}"
                iname_vi = f"{street_vi} - Trạm {i} (tuyến {short_name})"
                iname_en = f"{street_en} - Stop {i} (Route {short_name})"
                register_stop(istop_id, iname_vi, iname_en, ilat, ilon, False, city_id)
                route_stop_rows.append([route_id, istop_id, seq, round(itime)])
                seq += 1

            cum_time += seg_time
            register_stop(hub_id, name_vi, name_en, lat, lon, True, city_id)
            route_stop_rows.append([route_id, hub_id, seq, round(cum_time)])
            seq += 1
            prev_hub_id, prev_name_vi, prev_name_en, prev_lat, prev_lon = hub_id, name_vi, name_en, lat, lon

    stops_path = os.path.join(OUT_DIR, "stops.csv")
    routes_path = os.path.join(OUT_DIR, "routes.csv")
    route_stops_path = os.path.join(OUT_DIR, "route_stops.csv")

    with open(stops_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["stop_id", "stop_name", "stop_name_en", "lat", "lon", "is_hub", "city_id"])
        for row in stop_registry.values():
            w.writerow(row)

    with open(routes_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["route_id", "route_short_name", "route_long_name", "route_long_name_en", "city_id",
                     "fare_regular", "fare_student", "headway_min", "first_departure", "last_departure"])
        for row in route_rows:
            w.writerow(row)

    with open(route_stops_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["route_id", "stop_id", "stop_sequence", "offset_min"])
        for row in route_stop_rows:
            w.writerow(row)

    n_hcmc = sum(1 for r in stop_registry.values() if r[6] == "hcmc")
    n_bh = sum(1 for r in stop_registry.values() if r[6] == "bienhoa")
    print(f"Đã sinh {len(stop_registry)} trạm ({n_hcmc} TP.HCM, {n_bh} Biên Hòa), "
          f"{len(route_rows)} tuyến, {len(route_stop_rows)} dòng route_stops.")
    print(f"-> {stops_path}")
    print(f"-> {routes_path}")
    print(f"-> {route_stops_path}")


if __name__ == "__main__":
    main()
