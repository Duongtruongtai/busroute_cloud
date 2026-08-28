# -*- coding: utf-8 -*-
"""
Mô phỏng vị trí xe buýt theo thời gian thực (simulated live tracking).

QUAN TRỌNG: hiện KHÔNG có API GPS thời gian thực công khai/miễn phí cho xe buýt
tại Việt Nam (BusMap và Buýt Đồng Nai là hệ thống nội bộ, không mở dữ liệu vị trí
xe cho bên thứ ba). Module này TÍNH TOÁN vị trí ước tính của từng "chuyến xe" đang
chạy dựa trên: giờ khởi hành theo biểu đồ chuẩn (first_departure/headway_min) và
thời gian đã trôi qua kể từ lúc khởi hành, nội suy tuyến tính giữa các trạm theo
offset_min. Đây là mô phỏng phục vụ minh hoạ trực quan (giống UX của Grab/Be) chứ
KHÔNG phải theo dõi GPS thật - luôn được ghi rõ trên giao diện.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from backend.schedule import parse_hhmm


@dataclass
class BusPosition:
    route_id: str
    trip_label: str
    departure_time: datetime
    elapsed_min: float
    progress_pct: float
    lat: float
    lon: float
    next_stop_name: str


def _interpolate(ordered_stops: List[dict], elapsed_min: float):
    """ordered_stops: list cac dict {stop_id, stop_name, offset_min, lat, lon}, da sort theo offset_min."""
    if not ordered_stops:
        return None
    if elapsed_min <= ordered_stops[0]["offset_min"]:
        s = ordered_stops[0]
        return s["lat"], s["lon"], s["stop_name"]
    if elapsed_min >= ordered_stops[-1]["offset_min"]:
        s = ordered_stops[-1]
        return s["lat"], s["lon"], s["stop_name"]

    for prev, nxt in zip(ordered_stops, ordered_stops[1:]):
        if prev["offset_min"] <= elapsed_min <= nxt["offset_min"]:
            span = nxt["offset_min"] - prev["offset_min"]
            frac = 0.0 if span <= 0 else (elapsed_min - prev["offset_min"]) / span
            lat = prev["lat"] + (nxt["lat"] - prev["lat"]) * frac
            lon = prev["lon"] + (nxt["lon"] - prev["lon"]) * frac
            return lat, lon, nxt["stop_name"]
    last = ordered_stops[-1]
    return last["lat"], last["lon"], last["stop_name"]


def active_buses(route_id: str, route_short_name: str, first_departure: str, last_departure: str,
                  headway_min: int, ordered_stops: List[dict], now: Optional[datetime] = None,
                  max_trips: int = 500) -> List[BusPosition]:
    """Danh sach vi tri uoc tinh cua tat ca 'chuyen xe' dang chay tren 1 tuyen tai thoi diem now."""
    if not ordered_stops or headway_min <= 0:
        return []
    now = (now or datetime.now()).replace(second=0, microsecond=0)
    total_duration = ordered_stops[-1]["offset_min"]

    start = parse_hhmm(first_departure, now)
    end = parse_hhmm(last_departure, now)

    buses: List[BusPosition] = []
    t = start
    n = 0
    while t <= end and n < max_trips:
        trip_end = t + timedelta(minutes=total_duration)
        if t <= now <= trip_end:
            elapsed = (now - t).total_seconds() / 60.0
            pos = _interpolate(ordered_stops, elapsed)
            if pos:
                lat, lon, next_stop_name = pos
                progress = 0.0 if total_duration <= 0 else min(100.0, max(0.0, elapsed / total_duration * 100.0))
                buses.append(BusPosition(
                    route_id=route_id,
                    trip_label=f"{route_short_name} - {t.strftime('%H:%M')}",
                    departure_time=t,
                    elapsed_min=elapsed,
                    progress_pct=progress,
                    lat=lat, lon=lon,
                    next_stop_name=next_stop_name,
                ))
        t += timedelta(minutes=headway_min)
        n += 1
    return buses
