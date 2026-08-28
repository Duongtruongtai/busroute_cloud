# -*- coding: utf-8 -*-
"""
Định vị địa chỉ tự do (free-text) sang toạ độ, dùng Nominatim (OpenStreetMap) -
dịch vụ geocoding MIỄN PHÍ, không cần API key.

Tuân thủ chính sách sử dụng của Nominatim (https://operations.osmfoundation.org/policies/nominatim/):
- Gửi header User-Agent định danh ứng dụng.
- Chỉ gọi 1 request mỗi lần người dùng bấm tìm kiếm (không polling), có cache
  ở tầng app (st.cache_data) để tránh gọi lặp lại cùng 1 truy vấn.
"""
import math
from typing import List, Optional, TypedDict

import pandas as pd
import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "SmartCityBusAssistant-CourseProject/1.0 (Streamlit Cloud demo)"


class GeocodeResult(TypedDict):
    display_name: str
    lat: float
    lon: float


def geocode(query: str, limit: int = 1, timeout: float = 6.0) -> List[GeocodeResult]:
    """Chuyển địa chỉ/địa điểm dạng text tự do sang toạ độ (lat, lon)."""
    if not query or not query.strip():
        return []
    q = query.strip()
    if "việt nam" not in q.lower() and "vietnam" not in q.lower():
        q = f"{q}, Việt Nam"

    params = {"q": q, "format": "jsonv2", "limit": limit, "countrycodes": "vn"}
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    results: List[GeocodeResult] = []
    for item in data:
        try:
            results.append({
                "display_name": item.get("display_name", q),
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
            })
        except (KeyError, ValueError, TypeError):
            continue
    return results


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest_stops(lat: float, lon: float, stops_df: pd.DataFrame,
                   radius_km: float = 0.8, limit: int = 5) -> pd.DataFrame:
    """Trả về các trạm gần 1 toạ độ nhất, trong bán kính radius_km, kèm cột distance_km."""
    df = stops_df.copy()
    df["distance_km"] = df.apply(lambda r: haversine_km(lat, lon, float(r["lat"]), float(r["lon"])), axis=1)
    df = df[df["distance_km"] <= radius_km].sort_values("distance_km")
    return df.head(limit)
