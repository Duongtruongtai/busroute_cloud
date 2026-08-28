# -*- coding: utf-8 -*-
"""
Ước tính giờ xe đến trạm dựa trên biểu đồ chạy chuẩn (first_departure, last_departure,
headway_min) của tuyến - MÔ PHỎNG theo lịch chạy, KHÔNG phải dữ liệu GPS thời gian thực.
Đây là giới hạn được công bố rõ trong báo cáo (Chương 9 - Limitations) do hiện chưa có
API GPS công khai miễn phí cho xe buýt tại Việt Nam.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Tuple


def parse_hhmm(value: str, ref: datetime) -> datetime:
    hh, mm = value.split(":")
    return ref.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)


def is_route_active(first_departure: str, last_departure: str, now: Optional[datetime] = None) -> bool:
    """Tuyến có đang trong khung giờ hoạt động hôm nay hay không."""
    now = (now or datetime.now()).replace(second=0, microsecond=0)
    start = parse_hhmm(first_departure, now)
    end = parse_hhmm(last_departure, now)
    return start <= now <= end


def next_departures(first_departure: str, last_departure: str, headway_min: int,
                     now: Optional[datetime] = None, count: int = 3) -> Tuple[List[datetime], Optional[str]]:
    """Trả về danh sách các giờ xe khởi hành tiếp theo từ ĐẦU TUYẾN, và thông báo nếu hết giờ chạy."""
    now = (now or datetime.now()).replace(second=0, microsecond=0)
    start = parse_hhmm(first_departure, now)
    end = parse_hhmm(last_departure, now)

    if now > end:
        return [], f"Tuyến đã kết thúc giờ hoạt động hôm nay ({first_departure} - {last_departure})."
    if now < start:
        t = start
    else:
        elapsed = (now - start).total_seconds() / 60.0
        steps = int(elapsed // headway_min) + 1
        t = start + timedelta(minutes=steps * headway_min)

    departures: List[datetime] = []
    while t <= end and len(departures) < count:
        departures.append(t)
        t += timedelta(minutes=headway_min)

    if not departures:
        return [], f"Không còn chuyến nào trong hôm nay (hoạt động {first_departure} - {last_departure})."
    return departures, None


def estimate_arrival_at_stop(first_departure: str, last_departure: str, headway_min: int,
                              stop_offset_min: float, now: Optional[datetime] = None
                              ) -> Tuple[Optional[datetime], Optional[str]]:
    """Giờ xe (chuyến gần nhất) dự kiến đến 1 trạm cụ thể = giờ khởi hành đầu tuyến + offset của trạm."""
    departures, msg = next_departures(first_departure, last_departure, headway_min, now=now, count=1)
    if not departures:
        return None, msg
    arrival = departures[0] + timedelta(minutes=stop_offset_min)
    return arrival, None


def minutes_until(target: datetime, now: Optional[datetime] = None) -> int:
    now = now or datetime.now()
    return max(0, int((target - now).total_seconds() // 60))
