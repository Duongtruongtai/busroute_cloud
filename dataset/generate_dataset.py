"""
Sinh dataset mau (stops.csv, routes.csv, route_stops.csv) cho du an
Smart City Bus Assistant - Cong tra cuu tuyen & uoc tinh thoi gian xe buyt TP.HCM.

Nguon goc du lieu:
- So hieu tuyen, ten tuyen, diem dau/cuoi (ben xe, truong hoc, san bay...) va cac
  truc duong chinh duoc tham khao tu thong tin tuyen xe buyt cong khai tai TP.HCM.
- Toa do cac tram trung gian duoc NOI SUY (interpolate) tuyen tinh giua cac diem
  neo (hub) thuc te de phuc vu minh hoa cho do an hoc phan, KHONG phai du lieu
  GTFS chinh thuc cua Trung tam Quan ly Giao thong cong cong TP.HCM.
- Thoi gian chay giua cac tram uoc tinh theo toc do khai thac binh quan xe buyt
  noi do (bao gom thoi gian dung tram).

Chay: python dataset/generate_dataset.py
Ket qua: stops.csv, routes.csv, route_stops.csv trong cung thu muc dataset/
"""
import csv
import math
import os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Cac diem neo (hub) co that, toa do gan dung (do thap phan)
HUBS = {
    "BEN_THANH": ("Cho Ben Thanh", 10.7724, 106.6980),
    "MIEN_DONG": ("Ben xe Mien Dong moi", 10.8657, 106.7735),
    "MIEN_TAY": ("Ben xe Mien Tay", 10.7398, 106.6180),
    "CV_23_9": ("Cong vien 23/9", 10.7690, 106.6928),
    "DHQG": ("Dai hoc Quoc Gia TP.HCM", 10.8700, 106.8030),
    "CHO_LON": ("Ben xe Cho Lon", 10.7493, 106.6512),
    "TSN": ("San bay Tan Son Nhat", 10.8189, 106.6520),
    "PMH": ("Khu do thi Phu My Hung", 10.7291, 106.7183),
    "BACH_KHOA": ("Dai hoc Bach Khoa", 10.7725, 106.6577),
    "SU_PHAM": ("Dai hoc Su Pham TP.HCM", 10.7599, 106.6822),
    "Q8": ("Ben xe Quan 8", 10.7385, 106.6650),
    "SUOI_TIEN": ("Khu du lich Suoi Tien", 10.8623, 106.8022),
}

# route_id, so hieu, ten tuyen, [chuoi hub theo thu tu], ten duong (dat ten tram),
# so tram trung gian giua MOI cap hub, gia ve pho thong, gia ve sinh vien,
# gian cach chay (phut), gio chay dau, gio chay cuoi
ROUTES = [
    ("R01", "01", "Ben Thanh - Ben xe Cho Lon", ["BEN_THANH", "CHO_LON"],
     "Tran Hung Dao", 3, 6000, 3000, 10, "05:00", "20:30"),
    ("R08", "08", "Ben xe Quan 8 - Dai hoc Quoc Gia", ["Q8", "BEN_THANH", "DHQG"],
     "Nguyen Thi Thap - Xa lo Ha Noi", 3, 6000, 3000, 15, "05:00", "20:00"),
    ("R10", "10", "Dai hoc Quoc Gia - Ben xe Cho Lon", ["DHQG", "BACH_KHOA", "CHO_LON"],
     "Ly Thuong Kiet", 3, 6000, 3000, 15, "05:00", "20:00"),
    ("R19", "19", "Ben Thanh - Dai hoc Quoc Gia (qua Suoi Tien)", ["BEN_THANH", "SUOI_TIEN", "DHQG"],
     "Xa lo Ha Noi", 4, 7000, 3000, 12, "05:00", "21:00"),
    ("R30", "30", "Ben xe Cho Lon - San bay Tan Son Nhat", ["CHO_LON", "TSN"],
     "Ly Thuong Kiet - Truong Chinh", 3, 6000, 3000, 15, "05:30", "20:00"),
    ("R152", "152", "San bay Tan Son Nhat - Ben Thanh", ["TSN", "BEN_THANH"],
     "Truong Son - Nguyen Van Troi", 3, 6000, 3000, 10, "05:00", "21:30"),
    ("R88", "88", "Ben Thanh - Phu My Hung", ["BEN_THANH", "PMH"],
     "Nguyen Huu Tho", 3, 6000, 3000, 15, "05:30", "20:00"),
    ("R93", "93", "Ben xe Mien Dong moi - Ben xe Mien Tay", ["MIEN_DONG", "BEN_THANH", "MIEN_TAY"],
     "Dien Bien Phu", 4, 7000, 3000, 15, "04:30", "20:30"),
    ("R45", "45", "Ben Thanh - Dai hoc Su Pham", ["BEN_THANH", "SU_PHAM"],
     "Cach Mang Thang 8", 2, 6000, 3000, 15, "05:00", "19:30"),
    ("R36", "36", "Ben xe Mien Tay - Ben Thanh", ["MIEN_TAY", "CV_23_9", "BEN_THANH"],
     "Hung Vuong", 3, 6000, 3000, 12, "05:00", "20:00"),
]

AVG_SPEED_KMH = 22.0  # toc do khai thac binh quan (da tinh thoi gian dung tram)


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def main():
    stop_registry = {}  # stop_id -> [stop_id, name, lat, lon, is_hub]
    route_rows = []
    route_stop_rows = []

    def register_stop(stop_id, name, lat, lon, is_hub):
        if stop_id not in stop_registry:
            stop_registry[stop_id] = [stop_id, name, round(lat, 6), round(lon, 6), "1" if is_hub else "0"]

    for (route_id, short_name, long_name, hub_seq, street_hint, n_between,
         fare_base, fare_student, headway, first_dep, last_dep) in ROUTES:
        route_rows.append([route_id, short_name, long_name, fare_base, fare_student,
                            headway, first_dep, last_dep])

        seq = 1
        cum_time = 0.0
        prev_hub_id = hub_seq[0]
        prev_name, prev_lat, prev_lon = HUBS[prev_hub_id]
        register_stop(prev_hub_id, prev_name, prev_lat, prev_lon, True)
        route_stop_rows.append([route_id, prev_hub_id, seq, round(cum_time)])
        seq += 1

        for hub_id in hub_seq[1:]:
            name, lat, lon = HUBS[hub_id]
            dist = haversine_km(prev_lat, prev_lon, lat, lon)
            seg_time = dist / AVG_SPEED_KMH * 60.0

            for i in range(1, n_between + 1):
                frac = i / (n_between + 1)
                ilat = prev_lat + (lat - prev_lat) * frac
                ilon = prev_lon + (lon - prev_lon) * frac
                itime = cum_time + seg_time * frac
                istop_id = f"{route_id}_S{seq}"
                iname = f"{street_hint} - Tram {i} (tuyen {short_name})"
                register_stop(istop_id, iname, ilat, ilon, False)
                route_stop_rows.append([route_id, istop_id, seq, round(itime)])
                seq += 1

            cum_time += seg_time
            register_stop(hub_id, name, lat, lon, True)
            route_stop_rows.append([route_id, hub_id, seq, round(cum_time)])
            seq += 1
            prev_hub_id, prev_name, prev_lat, prev_lon = hub_id, name, lat, lon

    stops_path = os.path.join(OUT_DIR, "stops.csv")
    routes_path = os.path.join(OUT_DIR, "routes.csv")
    route_stops_path = os.path.join(OUT_DIR, "route_stops.csv")

    with open(stops_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["stop_id", "stop_name", "lat", "lon", "is_hub"])
        for row in stop_registry.values():
            w.writerow(row)

    with open(routes_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["route_id", "route_short_name", "route_long_name", "fare_regular",
                     "fare_student", "headway_min", "first_departure", "last_departure"])
        for row in route_rows:
            w.writerow(row)

    with open(route_stops_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["route_id", "stop_id", "stop_sequence", "offset_min"])
        for row in route_stop_rows:
            w.writerow(row)

    print(f"Da sinh {len(stop_registry)} tram, {len(route_rows)} tuyen, "
          f"{len(route_stop_rows)} dong route_stops.")
    print(f"-> {stops_path}")
    print(f"-> {routes_path}")
    print(f"-> {route_stops_path}")


if __name__ == "__main__":
    main()
