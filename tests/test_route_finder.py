"""
Kiem tra nhanh (khong dung pytest de khong them dependency) cho RouteFinder.
Chay: python tests/test_route_finder.py

Dung fixture TONG HOP (khong doc dataset/*.csv that) de bai test khong phu
thuoc vao noi dung dataset TP.HCM thuc te (duoc sinh/geocode lai boi
dataset/build_hcm_dataset.py va co the thay doi) - chi kiem tra logic cua
RouteFinder: tuyen truc tiep, 1 lan chuyen tuyen qua tram chung, tuyen chay
khu hoi (2 chieu), va cac truong hop bien.
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from backend.route_finder import RouteFinder

# ----------------------------------------------------------------------------- #
# Fixture tong hop: 2 tuyen giao nhau tai tram HUB.
#   R1: A - HUB - B   (5 tram)
#   R2: HUB - C - D   (3 tram, xuat phat tu HUB)
# -> di A -> B: truc tiep tren R1.
# -> di A -> D: phai chuyen tuyen tai HUB (R1 -> R2).
# ----------------------------------------------------------------------------- #
STOPS = pd.DataFrame([
    {"stop_id": "A", "stop_name": "Diem A", "stop_name_en": "Point A", "lat": 10.70, "lon": 106.60, "is_hub": 0},
    {"stop_id": "M1", "stop_name": "Tram giua 1", "stop_name_en": "Mid 1", "lat": 10.72, "lon": 106.62, "is_hub": 0},
    {"stop_id": "HUB", "stop_name": "Tram trung chuyen", "stop_name_en": "Hub", "lat": 10.75, "lon": 106.65, "is_hub": 1},
    {"stop_id": "M2", "stop_name": "Tram giua 2", "stop_name_en": "Mid 2", "lat": 10.77, "lon": 106.67, "is_hub": 0},
    {"stop_id": "B", "stop_name": "Diem B", "stop_name_en": "Point B", "lat": 10.80, "lon": 106.70, "is_hub": 0},
    {"stop_id": "C", "stop_name": "Diem C", "stop_name_en": "Point C", "lat": 10.76, "lon": 106.68, "is_hub": 0},
    {"stop_id": "D", "stop_name": "Diem D", "stop_name_en": "Point D", "lat": 10.78, "lon": 106.72, "is_hub": 0},
])

ROUTES = pd.DataFrame([
    {"route_id": "R1", "route_short_name": "R1", "route_long_name": "Tuyen R1 (A - Hub - B)",
     "route_long_name_en": "Route R1 (A - Hub - B)", "fare_regular": 7000, "fare_student": 4000,
     "headway_min": 10.0, "first_departure": "05:00", "last_departure": "21:00"},
    {"route_id": "R2", "route_short_name": "R2", "route_long_name": "Tuyen R2 (Hub - C - D)",
     "route_long_name_en": "Route R2 (Hub - C - D)", "fare_regular": 6000, "fare_student": 3000,
     "headway_min": 15.0, "first_departure": "05:00", "last_departure": "21:00"},
])

ROUTE_STOPS = pd.DataFrame([
    {"route_id": "R1", "stop_id": "A", "stop_sequence": 1, "offset_min": 0.0},
    {"route_id": "R1", "stop_id": "M1", "stop_sequence": 2, "offset_min": 5.0},
    {"route_id": "R1", "stop_id": "HUB", "stop_sequence": 3, "offset_min": 10.0},
    {"route_id": "R1", "stop_id": "M2", "stop_sequence": 4, "offset_min": 15.0},
    {"route_id": "R1", "stop_id": "B", "stop_sequence": 5, "offset_min": 20.0},
    {"route_id": "R2", "stop_id": "HUB", "stop_sequence": 1, "offset_min": 0.0},
    {"route_id": "R2", "stop_id": "C", "stop_sequence": 2, "offset_min": 8.0},
    {"route_id": "R2", "stop_id": "D", "stop_sequence": 3, "offset_min": 16.0},
])


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        raise SystemExit(1)


def main():
    finder = RouteFinder(ROUTES, ROUTE_STOPS, STOPS)

    # TC01: tuyen truc tiep A -> B tren R1
    res = finder.find("A", "B", fare_type="student")
    check("TC01 co it nhat 1 phuong an A -> B", len(res) >= 1)
    check("TC01 phuong an dau tien la truc tiep (0 lan chuyen)", res[0].transfers == 0)
    check("TC01 gia ve sinh vien = 4000", res[0].total_fare == 4000)

    # TC02: can chuyen tuyen tai HUB - A -> D (R1 khong toi D, R2 khong toi A)
    res2 = finder.find("A", "D", fare_type="regular")
    check("TC02 tim duoc phuong an A -> D", len(res2) >= 1)
    check("TC02 phuong an toi uu co dung 1 lan chuyen", res2[0].transfers == 1)
    check("TC02 diem chuyen tuyen la HUB", res2[0].legs[1].board_stop_id == "HUB")

    # TC03: khong ton tai duong di khi diem di = diem den -> tra ve danh sach rong
    res3 = finder.find("A", "A", fare_type="student")
    check("TC03 diem di = diem den tra ve rong", res3 == [])

    # TC04: stops_between tra ve dung thu tu, bao gom ca 2 dau
    seq = finder.stops_between("R1", "A", "B")
    check("TC04 stops_between bat dau tai diem di", seq[0] == "A")
    check("TC04 stops_between ket thuc tai diem den", seq[-1] == "B")
    check("TC04 stops_between di qua ca 2 tram giua", seq == ["A", "M1", "HUB", "M2", "B"])

    # TC05: tuyen chay khu hoi (2 chieu) - di NGUOC chieu "shape" cua R1 (B -> A)
    res5 = finder.find("B", "A", fare_type="student")
    check("TC05 tim duoc duong B -> A (tuyen chay 2 chieu)", len(res5) >= 1)
    check("TC05 la tuyen truc tiep", res5[0].transfers == 0)

    # TC06: stops_between tra ve dung thu tu khi di NGUOC chieu "shape" cua tuyen
    seq6 = finder.stops_between("R1", "B", "A")
    check("TC06 stops_between chieu nguoc bat dau tai diem di", seq6[0] == "B")
    check("TC06 stops_between chieu nguoc ket thuc tai diem den", seq6[-1] == "A")

    # TC07: khong co duong di giua 2 tram khong lien thong qua bat ky tuyen nao
    res7 = finder.find("M1", "C", fare_type="student")
    check("TC07 M1 -> C can 1 lan chuyen (qua HUB)", len(res7) >= 1 and res7[0].transfers == 1)

    print("\nTat ca test PASS.")


if __name__ == "__main__":
    main()
