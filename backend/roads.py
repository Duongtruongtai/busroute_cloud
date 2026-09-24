# -*- coding: utf-8 -*-
"""
Vẽ đường đi THEO HÌNH DẠNG ĐƯỜNG XÁ THẬT (road-following polyline) thay vì
nối thẳng từ điểm này sang điểm kia, dùng OSRM (Open Source Routing Machine)
- dịch vụ định tuyến mã nguồn mở, MIỄN PHÍ, không cần API key.

QUAN TRỌNG: OSRM sẽ "bắt dính" (snap) bất kỳ toạ độ nào vào con đường thật gần
nhất rồi tính đường đi thật giữa các điểm đó. Vì vậy tính năng này cho ra hình
dạng đường đi thật cho CẢ dữ liệu trạm thật (Kiên Giang) LẪN dữ liệu trạm mẫu/
nội suy (TP.HCM, Biên Hòa) - toạ độ trạm có thể là ước lượng, nhưng đường vẽ
ra luôn đi theo đường xá có thật.

Giới hạn cần công bố rõ: dùng máy chủ DEMO công khai của cộng đồng OSRM
(router.project-osrm.org) - chỉ dành cho mục đích thử nghiệm/đánh giá, không
phải hạ tầng production. Phù hợp quy mô đồ án học phần; nếu triển khai thực
tế với lưu lượng lớn cần tự host OSRM hoặc dùng dịch vụ trả phí (Mapbox/
Google Directions). Mọi lỗi/timeout đều được bắt và trả về None để nơi gọi
tự động dùng lại đường nối thẳng (không bao giờ làm sập ứng dụng).
"""
from typing import List, Optional, Tuple

import requests

OSRM_BASE = "https://router.project-osrm.org/route/v1/driving/"

# Cache trong bo nho tien trinh (khong phu thuoc Streamlit) - moi cap toa do chi
# goi OSRM 1 lan, cac lan xem lai sau (rerun, nguoi dung khac) dung lai ket qua
# da cache, giam tai cho may chu demo cong khai.
_cache: dict = {}


def road_path(waypoints_latlon: List[Tuple[float, float]], timeout: float = 6.0
              ) -> Optional[List[Tuple[float, float]]]:
    """
    waypoints_latlon: danh sach >= 2 diem [(lat, lon), ...] theo thu tu di qua.
    Tra ve danh sach [(lat, lon), ...] noi tiep nhau theo DUONG THAT, hoac None
    neu loi/timeout/khong tim duoc duong (noi goi tu fallback ve noi thang).
    """
    if len(waypoints_latlon) < 2:
        return None
    key = tuple(waypoints_latlon)
    if key in _cache:
        return _cache[key]

    coords = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in waypoints_latlon)
    url = f"{OSRM_BASE}{coords}"
    try:
        resp = requests.get(url, params={"overview": "simplified", "geometries": "geojson"},
                             timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            _cache[key] = None
            return None
        line = data["routes"][0]["geometry"]["coordinates"]  # [[lon, lat], ...]
        path = [(lat, lon) for lon, lat in line]
        _cache[key] = path
        return path
    except Exception:
        _cache[key] = None
        return None


def downsample_waypoints(latlon_list: List[Tuple[float, float]], max_points: int = 12
                          ) -> List[Tuple[float, float]]:
    """Giam so waypoint (luon giu diem dau/cuoi) truoc khi goi OSRM - tuyen co qua
    nhieu tram (vd 70+ tram o Kien Giang) se lam URL qua dai / request qua cham."""
    n = len(latlon_list)
    if n <= max_points:
        return latlon_list
    step = (n - 1) / (max_points - 1)
    idxs = sorted({round(i * step) for i in range(max_points)})
    return [latlon_list[i] for i in idxs]
