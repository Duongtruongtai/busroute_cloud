"""
Kiem tra nhanh (khong dung pytest de khong them dependency) cho RouteFinder.
Chay: python tests/test_route_finder.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from backend.route_finder import RouteFinder

DATASET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset")


def load():
    stops = pd.read_csv(os.path.join(DATASET_DIR, "stops.csv"))
    routes = pd.read_csv(os.path.join(DATASET_DIR, "routes.csv"))
    route_stops = pd.read_csv(os.path.join(DATASET_DIR, "route_stops.csv"))
    return stops, routes, route_stops


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        raise SystemExit(1)


def main():
    stops, routes, route_stops = load()
    finder = RouteFinder(routes, route_stops, stops)

    # TC01: tuyen truc tiep Ben Thanh -> Ben xe Cho Lon (tuyen 01)
    res = finder.find("BEN_THANH", "CHO_LON", fare_type="student")
    check("TC01 co it nhat 1 phuong an Ben Thanh -> Cho Lon", len(res) >= 1)
    check("TC01 phuong an dau tien la truc tiep (0 lan chuyen)", res[0].transfers == 0)
    check("TC01 gia ve sinh vien = 3000", res[0].total_fare == 3000)

    # TC02: can chuyen tuyen - Ben xe Mien Tay -> Dai hoc Quoc Gia
    # (Mien Tay chi noi truc tiep Ben Thanh qua R36/R93; DHQG noi Ben Thanh qua R19/R08)
    res2 = finder.find("MIEN_TAY", "DHQG", fare_type="regular")
    check("TC02 tim duoc phuong an Mien Tay -> DHQG", len(res2) >= 1)
    check("TC02 phuong an toi uu co dung 1 lan chuyen", res2[0].transfers == 1)
    check("TC02 diem chuyen tuyen la Ben Thanh", res2[0].legs[1].board_stop_id == "BEN_THANH")

    # TC03: khong ton tai duong di -> tra ve danh sach rong, khong crash
    res3 = finder.find("BEN_THANH", "BEN_THANH", fare_type="student")
    check("TC03 diem di = diem den tra ve rong", res3 == [])

    # TC04: stops_between tra ve dung thu tu, bao gom ca 2 dau
    seq = finder.stops_between("R01", "BEN_THANH", "CHO_LON")
    check("TC04 stops_between bat dau tai diem di", seq[0] == "BEN_THANH")
    check("TC04 stops_between ket thuc tai diem den", seq[-1] == "CHO_LON")
    check("TC04 stops_between co it nhat 2 tram", len(seq) >= 2)

    print("\nTat ca test PASS.")


if __name__ == "__main__":
    main()
