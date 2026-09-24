# -*- coding: utf-8 -*-
"""
Sinh dataset TP.HCM THAT (stops.csv/routes.csv/route_stops.csv) tu du lieu goc
trong "DATA BUS HCM/" (74 tuyen xe buyt & metro, du lieu 2026 - TP.HCM sau khi
sap nhap Binh Duong va Ba Ria - Vung Tau).

Du lieu goc CHI co thong tin cap-tuyen (gia ve, gio chay, gian cach, khoang cach)
va danh sach "diem moc" (key_landmarks) theo thu tu doc tuyen o dang van ban tu do
- KHONG co toa do tram. Script nay:
  1. Doc routes_master.csv -> thong so tung tuyen (parse so kieu VN: "14,0" ->
     14.0, "5.000 d" -> 5000).
  2. Doc route_paths_and_landmarks.csv -> voi moi tuyen, chon 1 huong chinh tac
     (uu tien "Luot di" > "Hai chieu"/"Vong tron" > dong dau tien) va dung danh
     sach key_landmarks cua huong do lam chuoi tram theo thu tu.
  3. Dinh vi (geocode) tung diem moc DUY NHAT 1 lan, dung CHUNG 1 stop_id o moi
     noi no xuat hien -> day la co che tao "diem trung chuyen" giua cac tuyen.
  4. Diem moc khong dinh vi duoc se noi suy vi tri theo vi tri tuong doi trong
     danh sach (giua 2 diem lang gieng da dinh vi duoc).
  5. offset_min tung tram = khoang cach haversine luy ke, quy doi ve dung tong
     thoi gian trip_duration_min THAT cua tuyen (khong gia dinh toc do co dinh).

QUAN TRONG - nha cung cap geocode: Nominatim (dung o backend/geocoding.py cho
tinh nang tim kiem trong app) khong the ket noi tu moi truong build hien tai (bi
tu choi ket noi - co the do mang cua nha cung cap ha tang). Script nay dung
Photon (https://photon.komoot.io, cung du lieu OpenStreetMap, API mo, khong can
key) CHI DE SINH DU LIEU (khong anh huong toi tinh nang tim kiem dia chi tu do
luc chay app - cai do van dung Nominatim qua backend/geocoding.py nhu cu).

Ket qua duoc CACHE vao dataset/geocode_cache.json (commit kem) de chay lai
khong can goi mang nua va dataset tai tao duoc (reproducible).

Chay: python dataset/build_hcm_dataset.py
"""
import csv
import json
import math
import os
import re
import sys
import time
import unicodedata

import pandas as pd
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "DATA BUS HCM")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(OUT_DIR, "geocode_cache.json")

ROUTES_MASTER_PATH = os.path.join(
    RAW_DIR, "Dataset Xe Bus TP.HCM - Datasets Chuan Hoa Cho Web App - routes_master.csv")
LANDMARKS_PATH = os.path.join(
    RAW_DIR, "Dataset Xe Bus TP.HCM - Datasets Chuan Hoa Cho Web App - route_paths_and_landmarks.csv")

CITY_ID = "hcmc"
PHOTON_URL = "https://photon.komoot.io/api/"
USER_AGENT = "SmartCityBusAssistant-CourseProject/1.0 (dataset build script)"
DIRECTION_PRIORITY = {"Lượt đi": 0, "Hai chiều": 1, "Vòng tròn": 1, "Lượt về": 2}

# Tam bien toa do (bias) khu vuc TP.HCM mo rong (Sai Gon - Binh Duong - Vung Tau
# - Con Dao) de Photon uu tien ket qua trong vung, khong bat buoc.
BIAS_LAT, BIAS_LON = 10.55, 106.85
HCM_CITY_HINTS = ("hồ chí minh", "ho chi minh", "bình dương", "binh duong",
                   "vũng tàu", "vung tau", "bà rịa", "ba ria", "côn đảo", "con dao")


# --------------------------------------------------------------------------- #
# Parse so kieu Viet Nam
# --------------------------------------------------------------------------- #
def parse_vi_decimal(s):
    """"9,62" -> 9.62 ; "40,0" -> 40.0"""
    if s is None:
        return None
    s = str(s).strip().replace(",", ".")
    if not s:
        return None
    return float(s)


def parse_vnd(s):
    """"5.000 ₫" -> 5000 ; "0 ₫" -> 0"""
    if s is None:
        return None
    digits = re.sub(r"[^\d]", "", str(s))
    return int(digits) if digits else 0


def strip_diacritics(text):
    nfkd = unicodedata.normalize("NFD", str(text))
    no_marks = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return no_marks.replace("đ", "d").replace("Đ", "D")


def slugify(name):
    ascii_name = strip_diacritics(name).upper()
    ascii_name = re.sub(r"[^A-Z0-9]+", "_", ascii_name).strip("_")
    return ascii_name[:40] or "STOP"


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# --------------------------------------------------------------------------- #
# Geocoding (Photon) voi cache tren dia
# --------------------------------------------------------------------------- #
def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)


def _photon_query(query):
    try:
        resp = requests.get(
            PHOTON_URL,
            params={"q": query, "limit": 5, "lat": BIAS_LAT, "lon": BIAS_LON},
            headers={"User-Agent": USER_AGENT}, timeout=8.0,
        )
        resp.raise_for_status()
        feats = resp.json().get("features", [])
    except Exception:
        return None

    def score(feat):
        props = feat.get("properties", {})
        city = str(props.get("city", "")).lower()
        is_vn = props.get("countrycode") == "VN"
        in_region = any(h in city for h in HCM_CITY_HINTS)
        return (is_vn, in_region)

    feats_vn = [f for f in feats if f.get("properties", {}).get("countrycode") == "VN"]
    pool = feats_vn or feats
    if not pool:
        return None
    pool.sort(key=score, reverse=True)
    coords = pool[0]["geometry"]["coordinates"]  # [lon, lat]
    return {"lat": coords[1], "lon": coords[0]}


def geocode_landmark(name, cache):
    if name in cache:
        return cache[name]
    result = _photon_query(f"{name}, Thành phố Hồ Chí Minh, Việt Nam")
    if result is None:
        # thu lai bo phan trong ngoac (vd "(ranh Tay Ninh)", "(Nha ga T3)")
        stripped = re.sub(r"\s*\([^)]*\)", "", name).strip()
        if stripped and stripped != name:
            time.sleep(0.4)
            result = _photon_query(f"{stripped}, Thành phố Hồ Chí Minh, Việt Nam")
    cache[name] = result
    time.sleep(0.4)
    return result


# --------------------------------------------------------------------------- #
# Doc du lieu goc
# --------------------------------------------------------------------------- #
def load_routes_master():
    df = pd.read_csv(ROUTES_MASTER_PATH, skiprows=3, dtype=str, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    df = df.dropna(subset=["route_id"]).reset_index(drop=True)
    return df


def load_landmarks():
    df = pd.read_csv(LANDMARKS_PATH, skiprows=2, dtype=str, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    df = df.dropna(subset=["route_id"]).reset_index(drop=True)

    canonical = {}
    for _, row in df.iterrows():
        rid = row["route_id"].strip()
        prio = DIRECTION_PRIORITY.get(str(row.get("direction_type", "")).strip(), 1)
        if rid not in canonical or prio < canonical[rid][0]:
            canonical[rid] = (prio, row)
    return {rid: row for rid, (prio, row) in canonical.items()}


def landmark_sequence(row):
    raw = str(row.get("key_landmarks", "") or "")
    items = [x.strip() for x in raw.split(",") if x.strip()]
    # loai bo lap lien tiep (tranh tram trung offset)
    seq = []
    for name in items:
        if not seq or seq[-1] != name:
            seq.append(name)
    return seq


# --------------------------------------------------------------------------- #
# Xay dung stops / routes / route_stops
# --------------------------------------------------------------------------- #
def main():
    print("Doc du lieu goc...")
    routes_master = load_routes_master()
    landmarks_by_route = load_landmarks()
    print(f"  {len(routes_master)} tuyen trong routes_master.csv, "
          f"{len(landmarks_by_route)} tuyen co du lieu diem moc.")

    cache = load_cache()
    n_cached_before = len(cache)

    stop_registry = {}          # landmark_name -> stop_id
    stop_coords = {}            # stop_id -> (lat, lon)
    stop_routes_count = {}      # stop_id -> so tuyen dung chung (de suy is_hub)

    route_rows = []
    route_stop_rows = []
    unresolved_routes = []

    print("Dinh vi diem moc (Photon, co cache)...")
    for i, r in routes_master.iterrows():
        route_id = r["route_id"].strip()
        landmark_row = landmarks_by_route.get(route_id)

        fare_regular = parse_vnd(r.get("fare_regular_vnd"))
        fare_student = parse_vnd(r.get("fare_student_vnd"))
        headway_min = parse_vi_decimal(r.get("headway_min"))
        distance_km = parse_vi_decimal(r.get("distance_km"))
        trip_duration_min = parse_vi_decimal(r.get("trip_duration_min")) or 30.0
        is_subsidized = str(r.get("is_subsidized", "")).strip().upper() == "TRUE"

        route_rows.append([
            route_id, route_id, r.get("route_name", "").strip(), r.get("route_name", "").strip(),
            CITY_ID, fare_regular, fare_student, headway_min,
            r.get("start_time", "").strip(), r.get("end_time", "").strip(),
            r.get("operator_name", "").strip(), is_subsidized, distance_km,
        ])

        if landmark_row is None:
            unresolved_routes.append((route_id, "khong co du lieu diem moc"))
            continue

        names = landmark_sequence(landmark_row)

        # dinh vi tung diem moc (dung cache/geocode, chia se stop_id theo ten
        # giua cac tuyen -> tao diem trung chuyen)
        positions = []  # (idx, name, (lat, lon) hoac None)
        for idx, name in enumerate(names):
            if name in stop_registry and stop_registry[name] in stop_coords:
                latlon = stop_coords[stop_registry[name]]
            else:
                geo = geocode_landmark(name, cache)
                latlon = (geo["lat"], geo["lon"]) if geo else None
            positions.append((idx, name, latlon))

        resolved = [(idx, ll) for idx, _, ll in positions if ll is not None]
        if len(resolved) < 2:
            unresolved_routes.append((route_id, f"chi dinh vi duoc {len(resolved)}/{len(names)} diem moc"))
            continue

        # noi suy vi tri cac diem moc chua dinh vi duoc, dua tren vi tri (index)
        # tuong doi giua 2 diem lang gieng da dinh vi gan nhat
        seq_latlon = []
        for idx, name, latlon in positions:
            if latlon is not None:
                seq_latlon.append(latlon)
                continue
            prev_i, prev_ll = max((p for p in resolved if p[0] < idx), default=resolved[0], key=lambda p: p[0])
            next_i, next_ll = min((p for p in resolved if p[0] > idx), default=resolved[-1], key=lambda p: p[0])
            span = (next_i - prev_i) or 1
            frac = (idx - prev_i) / span
            seq_latlon.append((
                prev_ll[0] + (next_ll[0] - prev_ll[0]) * frac,
                prev_ll[1] + (next_ll[1] - prev_ll[1]) * frac,
            ))

        # gan stop_id: dung lai neu ten diem moc da co trong registry (uu tien
        # toa do dinh vi that tu tuyen khac), tao moi neu chua co
        seq_stop_ids = []
        for (idx, name, _), latlon in zip(positions, seq_latlon):
            sid = stop_registry.get(name)
            if sid is None:
                sid = slugify(name)
                base_sid, n = sid, 2
                while sid in stop_coords:
                    sid = f"{base_sid}_{n}"
                    n += 1
                stop_registry[name] = sid
                stop_coords[sid] = latlon
            seq_stop_ids.append(sid)

        # cumulative haversine -> offset_min ty le voi trip_duration_min that
        cum = [0.0]
        for k in range(1, len(seq_latlon)):
            d = haversine_km(*seq_latlon[k - 1], *seq_latlon[k])
            cum.append(cum[-1] + d)
        total = cum[-1]
        for seq_i, sid in enumerate(seq_stop_ids):
            offset = (cum[seq_i] / total * trip_duration_min) if total > 0 else (
                seq_i / max(1, len(seq_stop_ids) - 1) * trip_duration_min)
            route_stop_rows.append([route_id, sid, seq_i + 1, round(offset, 2)])
            stop_routes_count[sid] = stop_routes_count.get(sid, 0) + 1

        if (i + 1) % 10 == 0:
            print(f"  ... {i + 1}/{len(routes_master)} tuyen da xu ly")

    save_cache(cache)
    n_new = len(cache) - n_cached_before
    print(f"Da geocode {n_new} diem moc moi (tong cache: {len(cache)}).")

    # -------------------------------------------------------------------- #
    # Ghi stops.csv / routes.csv / route_stops.csv
    # -------------------------------------------------------------------- #
    endpoint_stops = set()
    for rid in {rs[0] for rs in route_stop_rows}:
        rows_for_route = sorted((rs for rs in route_stop_rows if rs[0] == rid), key=lambda x: x[2])
        endpoint_stops.add(rows_for_route[0][1])
        endpoint_stops.add(rows_for_route[-1][1])

    stops_out = []
    for name, sid in stop_registry.items():
        if sid not in stop_coords:
            continue
        lat, lon = stop_coords[sid]
        is_hub = stop_routes_count.get(sid, 0) >= 2 or sid in endpoint_stops
        stops_out.append([sid, name, name, round(lat, 6), round(lon, 6), int(is_hub), CITY_ID])

    stops_df = pd.DataFrame(stops_out, columns=[
        "stop_id", "stop_name", "stop_name_en", "lat", "lon", "is_hub", "city_id",
    ]).drop_duplicates(subset="stop_id")

    routes_df = pd.DataFrame(route_rows, columns=[
        "route_id", "route_short_name", "route_long_name", "route_long_name_en", "city_id",
        "fare_regular", "fare_student", "headway_min", "first_departure", "last_departure",
        "operator_name", "is_subsidized", "distance_km",
    ])

    route_stops_df = pd.DataFrame(route_stop_rows, columns=[
        "route_id", "stop_id", "stop_sequence", "offset_min",
    ])

    stops_df.to_csv(os.path.join(OUT_DIR, "stops.csv"), index=False, quoting=csv.QUOTE_MINIMAL)
    routes_df.to_csv(os.path.join(OUT_DIR, "routes.csv"), index=False, quoting=csv.QUOTE_MINIMAL)
    route_stops_df.to_csv(os.path.join(OUT_DIR, "route_stops.csv"), index=False, quoting=csv.QUOTE_MINIMAL)

    print("\n=== Tom tat ===")
    print(f"routes.csv       : {len(routes_df)} tuyen")
    print(f"stops.csv        : {len(stops_df)} tram (diem moc dinh vi duoc)")
    print(f"route_stops.csv  : {len(route_stops_df)} dong")
    routable = route_stops_df["route_id"].nunique()
    print(f"Tuyen co the dinh tuyen (>= 2 tram): {routable}/{len(routes_df)}")
    if unresolved_routes:
        print(f"\nTuyen KHONG dinh tuyen duoc ({len(unresolved_routes)}):")
        for rid, reason in unresolved_routes:
            print(f"  - {rid}: {reason}")


if __name__ == "__main__":
    main()
