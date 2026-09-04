# -*- coding: utf-8 -*-
"""
Nạp dữ liệu THẬT của tỉnh Kiên Giang (từ file `xebuyt.csv` ở gốc dự án - dữ liệu
trạm xe buýt do người dùng cung cấp) vào bộ dataset chung (stops.csv/routes.csv/
route_stops.csv), nối tiếp sau TP.HCM và Biên Hòa.

QUAN TRỌNG - Xử lý dữ liệu gốc còn thiếu so với schema:
1. File gốc có 1288 dòng nhưng bị LẶP LẠI ĐÚNG 4 LẦN (cột `districtname` là dữ liệu
   export bị nhân bản theo huyện, không phản ánh đúng huyện thật của từng trạm) ->
   loại trùng theo `id`, còn lại 322 trạm duy nhất.
2. Chỉ ~56/322 trạm có toạ độ (x=kinh độ, y=vĩ độ) thật; các trạm còn lại (đa số
   thuộc 9 tuyến chính) KHÔNG có toạ độ, chỉ có tên dạng "Km123+400" (số Km trên
   quốc lộ/tỉnh lộ) hoặc "Điểm dừng... - Điểm 0X" (số thứ tự điểm dừng).
3. Xử lý: với mỗi tuyến, tách số Km/số điểm dừng từ tên trạm để xác định THỨ TỰ
   và vị trí tương đối trên tuyến; trạm không tách được số sẽ được nội suy vị trí
   theo lân cận trong file. Toạ độ tuyệt đối của từng trạm được NỘI SUY tuyến tính
   giữa 2 điểm neo đầu-cuối của tuyến (ưu tiên dùng toạ độ THẬT nếu điểm neo đó đã
   có trong dữ liệu gốc, ví dụ "Bến xe Rạch Giá"; các điểm neo còn lại geocode qua
   OpenStreetMap Nominatim, mỗi tên chỉ gọi 1 lần rồi cache).
4. File gốc KHÔNG có giá vé/giờ chạy/giãn cách -> dùng giá trị MẶC ĐỊNH hợp lý cho
   xe buýt liên huyện (rẻ hơn, giãn cách thưa hơn nội đô) - cần thay bằng số liệu
   thật khi nhóm có được (ghi rõ trong báo cáo là giả định).

Chạy SAU khi đã có sẵn stops.csv/routes.csv/route_stops.csv (tức sau khi chạy
dataset/generate_dataset.py) - script này APPEND thêm dữ liệu Kiên Giang vào 3
file đó (không ghi đè TP.HCM/Biên Hòa).

Chạy: python dataset/import_kiengiang.py
"""
import csv
import os
import re
import sys
import time

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend.geocoding import geocode  # noqa: E402

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_PATH = os.path.join(ROOT, "xebuyt.csv")
CITY_ID = "kiengiang"

# Toa do THAT da co san trong du lieu goc (lat, lon) - uu tien dung thay vi geocode.
REAL_ANCHOR = {
    "Bến xe Rạch Giá": (10.018717, 105.083044),
}

# Moi diem neo (ben xe/dia danh) dung CHUNG 1 stop_id giua cac tuyen co di qua no -
# day chinh la "diem trung chuyen" de thuat toan tim tuyen tim duoc phuong an can
# chuyen tuyen (giong cach lam voi HCMC/Bien Hoa). Neu khong lam vay, moi tuyen se
# co tram rieng biet du cung 1 vi tri vat ly -> khong bao gio tim duoc duong chuyen
# tuyen giua 2 tuyen khac nhau trong du lieu Kien Giang.
ANCHOR_STOP_ID = {
    "Bến xe Kiên Lương, Kiên Giang, Việt Nam": "KG_HUB_KIENLUONG",
    "Thị trấn Tri Tôn, An Giang, Việt Nam": "KG_HUB_TRITON",
    "Hòn Đất, Kiên Giang, Việt Nam": "KG_HUB_HONDAT",
    "Bến xe Rạch Giá": "KG_HUB_RACHGIA",
    "Dương Tơ, Phú Quốc": "KG_HUB_DUONGTO",
    "Dương Đông, Phú Quốc": "KG_HUB_DUONGDONG",
    "Minh Lương, Châu Thành": "KG_HUB_MINHLUONG",
    "Giồng Riềng": "KG_HUB_GIONGRIENG",
}
ANCHOR_DISPLAY_NAME = {
    "KG_HUB_KIENLUONG": "Bến xe Kiên Lương",
    "KG_HUB_TRITON": "Bến xe Tri Tôn",
    "KG_HUB_HONDAT": "Bến xe Hòn Đất",
    "KG_HUB_RACHGIA": "Bến xe Rạch Giá",
    "KG_HUB_DUONGTO": "Bến xe Dương Tơ",
    "KG_HUB_DUONGDONG": "Bến xe Dương Đông",
    "KG_HUB_MINHLUONG": "Ngã ba Minh Lương",
    "KG_HUB_GIONGRIENG": "Trung tâm Giồng Riềng",
}

# Moi tuyen: (ten_tuyen_trong_file -> (diem_neo_dau, diem_neo_cuoi))
# diem_neo la ten dat trong REAL_ANCHOR (dung toa do that) hoac 1 chuoi dia chi de
# geocode qua OpenStreetMap. Thu tu dau/cuoi khong quan trong ve mat chuc nang vi
# RouteFinder da ho tro tuyen 2 chieu.
ROUTE_ANCHORS = {
    "Bến xe Kiên Lương - Quốc lộ 80 - Bến xe Tri Tôn":
        ("Bến xe Kiên Lương, Kiên Giang, Việt Nam", "Thị trấn Tri Tôn, An Giang, Việt Nam"),
    "Bến xe Rạch Giá - Nguyễn Bỉnh Khiêm - Quốc lộ 80 - Bến xe Tri Tôn":
        ("Bến xe Rạch Giá", "Thị trấn Tri Tôn, An Giang, Việt Nam"),
    "Bến xe Tri Tôn - Bến xe Rạch Giá - Nguyễn Bỉnh Khiêm - Quốc lộ 80":
        ("Thị trấn Tri Tôn, An Giang, Việt Nam", "Hòn Đất, Kiên Giang, Việt Nam"),
    "Bến xe Tri Tôn - Quốc lộ 80 - Bến xe Kiên Lương":
        ("Thị trấn Tri Tôn, An Giang, Việt Nam", "Bến xe Kiên Lương, Kiên Giang, Việt Nam"),
    "Bến xe Tri Tôn - Quốc lộ 80 - Nguyễn Bỉnh Khiêm - Bến xe Rạch Giá":
        ("Thị trấn Tri Tôn, An Giang, Việt Nam", "Bến xe Rạch Giá"),
    "Dương Tơ - Suối Tranh - Dương Đông":
        ("Dương Tơ, Phú Quốc", "Dương Đông, Phú Quốc"),
    "Dương Đông - Suối Tranh - Dương Tơ":
        ("Dương Đông, Phú Quốc", "Dương Tơ, Phú Quốc"),
    "Giồng Riềng - Ngã 3 Bến Nhứt - Quốc lộ 61 - Ngã 3 Minh Lương":
        ("Minh Lương, Châu Thành", "Giồng Riềng"),
    "Ngã 3 Minh Lương - Quốc lộ 61 - Ngã 3 Bến Nhứt - Giồng Riềng":
        ("Minh Lương, Châu Thành", "Giồng Riềng"),
}

# Sinh so hieu ngan gon + gia tri mac dinh (chua co trong du lieu goc)
ROUTE_META = {
    "Bến xe Kiên Lương - Quốc lộ 80 - Bến xe Tri Tôn": ("KG-01", 25000, 12000, 60, "05:00", "18:00"),
    "Bến xe Rạch Giá - Nguyễn Bỉnh Khiêm - Quốc lộ 80 - Bến xe Tri Tôn": ("KG-02", 30000, 15000, 60, "05:00", "18:00"),
    "Bến xe Tri Tôn - Bến xe Rạch Giá - Nguyễn Bỉnh Khiêm - Quốc lộ 80": ("KG-03", 30000, 15000, 60, "05:00", "18:00"),
    "Bến xe Tri Tôn - Quốc lộ 80 - Bến xe Kiên Lương": ("KG-04", 25000, 12000, 60, "05:00", "18:00"),
    "Bến xe Tri Tôn - Quốc lộ 80 - Nguyễn Bỉnh Khiêm - Bến xe Rạch Giá": ("KG-05", 30000, 15000, 60, "05:00", "18:00"),
    "Dương Tơ - Suối Tranh - Dương Đông": ("KG-06", 10000, 5000, 30, "05:30", "18:30"),
    "Dương Đông - Suối Tranh - Dương Tơ": ("KG-07", 10000, 5000, 30, "05:30", "18:30"),
    "Giồng Riềng - Ngã 3 Bến Nhứt - Quốc lộ 61 - Ngã 3 Minh Lương": ("KG-08", 15000, 7000, 45, "05:00", "18:00"),
    "Ngã 3 Minh Lương - Quốc lộ 61 - Ngã 3 Bến Nhứt - Giồng Riềng": ("KG-09", 15000, 7000, 45, "05:00", "18:00"),
}

KM_RE = re.compile(r"[Kk]m\s*(\d+)(?:\+(\d+))?")
DIEM_RE = re.compile(r"Điểm\s*0*(\d+)\s*$")

AVG_SPEED_KMH = 30.0  # xe buyt lien huyen chay nhanh hon noi do (it den do, quang duong dai)


def strip_diacritics(text: str) -> str:
    import unicodedata
    nfkd = unicodedata.normalize("NFD", str(text))
    no_marks = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return no_marks.replace("đ", "d").replace("Đ", "D")


def parse_position(ten: str):
    if not isinstance(ten, str):
        return None
    m = KM_RE.search(ten)
    if m:
        km = int(m.group(1))
        part = int(m.group(2)) if m.group(2) else 0
        return km + part / 1000.0
    m2 = DIEM_RE.search(ten)
    if m2:
        return float(m2.group(1))
    return None


_geo_cache = {}


def resolve_anchor(name: str):
    """Tra ve (lat, lon) cho 1 diem neo - dung toa do that neu co, khong thi geocode."""
    if name in REAL_ANCHOR:
        return REAL_ANCHOR[name]
    if name in _geo_cache:
        return _geo_cache[name]
    results = geocode(name, limit=1)
    time.sleep(1.1)  # ton trong chinh sach 1 request/giay cua Nominatim
    if not results:
        print(f"  !! Khong geocode duoc: {name}")
        _geo_cache[name] = None
        return None
    latlon = (results[0]["lat"], results[0]["lon"])
    print(f"  -> {name}: {latlon}")
    _geo_cache[name] = latlon
    return latlon


def main():
    if not os.path.exists(RAW_PATH):
        print(f"Khong tim thay {RAW_PATH}. Hay dat file xebuyt.csv o thu muc goc du an.")
        sys.exit(1)

    raw = pd.read_csv(RAW_PATH, encoding="utf-8-sig")
    raw.columns = [c.lstrip("﻿") for c in raw.columns]
    raw = raw.drop_duplicates(subset="id").reset_index(drop=True)
    print(f"Doc {len(raw)} tram duy nhat tu xebuyt.csv (da loai trung).")

    new_stops = {}   # stop_id -> [stop_id, name_vi, name_en, lat, lon, is_hub, city_id]
    new_route_rows = []
    new_route_stop_rows = []

    print("\nDinh vi cac diem neo dau/cuoi tuyen...")
    for route_name in ROUTE_ANCHORS:
        for anchor in ROUTE_ANCHORS[route_name]:
            resolve_anchor(anchor)

    routed = raw[raw["tuyenxebuyt"].notna()].copy()

    for route_name, group in routed.groupby("tuyenxebuyt", sort=False):
        if route_name not in ROUTE_META:
            print(f"  (bo qua tuyen chua khai bao: {route_name})")
            continue
        short_name, fare_regular, fare_student, headway, first_dep, last_dep = ROUTE_META[route_name]
        route_id = f"KG{short_name.split('-')[1]}"
        anchor_start_name, anchor_end_name = ROUTE_ANCHORS[route_name]
        start_ll = resolve_anchor(anchor_start_name)
        end_ll = resolve_anchor(anchor_end_name)
        if not start_ll or not end_ll:
            print(f"  !! Bo qua tuyen '{route_name}' vi thieu toa do diem neo.")
            continue

        g = group.reset_index(drop=True).copy()
        g["pos_raw"] = g["ten"].apply(parse_position)
        g["pos"] = g["pos_raw"].interpolate(method="linear", limit_direction="both")
        if g["pos"].isna().all():
            g["pos"] = range(len(g))
        # interpolate() o 2 dau mut (khi tram dau/cuoi khong tach duoc so Km/Diem) chi
        # lap lai gia tri gan nhat thay vi noi suy that su -> nhieu tram co the bi trung
        # HET pos, khien frac trung 0.0/1.0 voi diem neo va bi coi la "cung 1 vi tri".
        # Them 1 lech rat nho theo thu tu dong goc de dam bao MOI tram co vi tri rieng
        # biet (khong doi thu tu tuong doi da co, chi pha trung).
        g["pos"] = g["pos"] + g.index * 1e-6
        g = g.sort_values("pos", kind="stable").reset_index(drop=True)

        pos_min, pos_max = g["pos"].min(), g["pos"].max()
        pos_span = (pos_max - pos_min) or 1.0
        dist_km_total = _haversine(start_ll[0], start_ll[1], end_ll[0], end_ll[1])
        total_minutes = max(5.0, dist_km_total / AVG_SPEED_KMH * 60.0)

        new_route_rows.append([
            route_id, short_name, route_name, strip_diacritics(route_name), CITY_ID,
            fare_regular, fare_student, headway, first_dep, last_dep,
        ])

        # Diem neo dau/cuoi duoc them nhu 1 TRAM THAT SU (dung chung stop_id giua cac
        # tuyen co cung diem neo) de tao diem trung chuyen - neu khong lam vay se
        # khong bao gio tim duoc phuong an can chuyen tuyen giua 2 tuyen Kien Giang.
        start_hub_id = ANCHOR_STOP_ID.get(anchor_start_name)
        end_hub_id = ANCHOR_STOP_ID.get(anchor_end_name)
        seq = 1
        if start_hub_id:
            name = ANCHOR_DISPLAY_NAME[start_hub_id]
            new_stops[start_hub_id] = [start_hub_id, name, strip_diacritics(name),
                                        round(start_ll[0], 6), round(start_ll[1], 6), 1, CITY_ID]
            new_route_stop_rows.append([route_id, start_hub_id, seq, 0])
            seq += 1

        # Danh 2% "vung dem" o moi dau cho rieng 2 tram neo (hub) - dam bao KHONG tram
        # trung gian nao co the roi dung frac=0.0/1.0 (trung voi hub) du interpolate()
        # co the lam vai tram dau/cuoi thieu so Km/Diem bi "dinh" vao gia tri bien.
        MARGIN = 0.02
        for _, row in g.iterrows():
            frac_raw = (row["pos"] - pos_min) / pos_span
            frac = MARGIN + frac_raw * (1 - 2 * MARGIN)
            has_real_xy = pd.notna(row.get("x")) and pd.notna(row.get("y"))
            if has_real_xy:
                lat, lon = float(row["y"]), float(row["x"])
            else:
                lat = start_ll[0] + (end_ll[0] - start_ll[0]) * frac
                lon = start_ll[1] + (end_ll[1] - start_ll[1]) * frac

            stop_id = f"{route_id}_ID{int(row['id'])}"
            name_vi = str(row["ten"]) if pd.notna(row["ten"]) else f"Tram {seq}"
            new_stops[stop_id] = [stop_id, name_vi, strip_diacritics(name_vi),
                                   round(lat, 6), round(lon, 6), 0, CITY_ID]
            # Giu 2 chu so thap phan (khong lam tron nguyen): tuyen co 70+ tram trong
            # ~75 phut se khien nhieu tram lam tron trung 1 gia tri phut nguyen, lam
            # thuat toan tim tuyen hieu nham la "cung 1 vi tri" (offset bang nhau).
            offset_min = round(frac * total_minutes, 2)
            new_route_stop_rows.append([route_id, stop_id, seq, offset_min])
            seq += 1

        if end_hub_id:
            name = ANCHOR_DISPLAY_NAME[end_hub_id]
            new_stops[end_hub_id] = [end_hub_id, name, strip_diacritics(name),
                                      round(end_ll[0], 6), round(end_ll[1], 6), 1, CITY_ID]
            new_route_stop_rows.append([route_id, end_hub_id, seq, round(total_minutes, 2)])

        print(f"  {route_id} ({route_name}): {len(g)} tram, ~{dist_km_total:.1f} km, ~{total_minutes:.0f} phut")

    # -------------------------------------------------------------------- #
    # Ghi noi tiep vao stops.csv / routes.csv / route_stops.csv hien co
    # -------------------------------------------------------------------- #
    stops_path = os.path.join(OUT_DIR, "stops.csv")
    routes_path = os.path.join(OUT_DIR, "routes.csv")
    route_stops_path = os.path.join(OUT_DIR, "route_stops.csv")

    existing_stops = pd.read_csv(stops_path)
    existing_routes = pd.read_csv(routes_path)
    existing_route_stops = pd.read_csv(route_stops_path)

    # loai bo du lieu Kien Giang cu (neu chay lai script nay nhieu lan)
    existing_stops = existing_stops[existing_stops["city_id"] != CITY_ID]
    existing_routes = existing_routes[existing_routes["city_id"] != CITY_ID]
    kg_route_ids = set(ROUTE_META[r][0].replace("KG-", "KG") for r in ROUTE_META)
    # (giu don gian: loai theo tien to KG)
    existing_route_stops = existing_route_stops[~existing_route_stops["route_id"].astype(str).str.startswith("KG")]

    new_stops_df = pd.DataFrame(list(new_stops.values()),
                                 columns=["stop_id", "stop_name", "stop_name_en", "lat", "lon", "is_hub", "city_id"])
    new_routes_df = pd.DataFrame(new_route_rows,
                                  columns=["route_id", "route_short_name", "route_long_name", "route_long_name_en",
                                           "city_id", "fare_regular", "fare_student", "headway_min",
                                           "first_departure", "last_departure"])
    new_route_stops_df = pd.DataFrame(new_route_stop_rows,
                                       columns=["route_id", "stop_id", "stop_sequence", "offset_min"])

    pd.concat([existing_stops, new_stops_df], ignore_index=True).to_csv(
        stops_path, index=False, quoting=csv.QUOTE_MINIMAL)
    pd.concat([existing_routes, new_routes_df], ignore_index=True).to_csv(
        routes_path, index=False, quoting=csv.QUOTE_MINIMAL)
    pd.concat([existing_route_stops, new_route_stops_df], ignore_index=True).to_csv(
        route_stops_path, index=False, quoting=csv.QUOTE_MINIMAL)

    print(f"\nDa them {len(new_stops_df)} tram, {len(new_routes_df)} tuyen, "
          f"{len(new_route_stops_df)} dong route_stops cho Kien Giang.")
    print("Da ghi vao stops.csv / routes.csv / route_stops.csv (giu nguyen du lieu TP.HCM/Bien Hoa).")


def _haversine(lat1, lon1, lat2, lon2):
    import math
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


if __name__ == "__main__":
    main()
