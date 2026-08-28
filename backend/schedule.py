"""
Uoc tinh gio xe den tram dua tren bieu do chay chuan (first_departure, last_departure,
headway_min) cua tuyen - MO PHONG, khong phai du lieu GPS thoi gian thuc.
Day la gioi han duoc cong bo ro trong bao cao (Chuong 9 - Limitations).
"""
from datetime import datetime, timedelta
from typing import List, Optional, Tuple


def _parse_hhmm(value: str, ref: datetime) -> datetime:
    hh, mm = value.split(":")
    return ref.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)


def next_departures(first_departure: str, last_departure: str, headway_min: int,
                     now: Optional[datetime] = None, count: int = 3) -> Tuple[List[datetime], Optional[str]]:
    """Tra ve danh sach cac gio xe khoi hanh tiep theo tu DAU TUYEN, va thong bao neu het gio chay."""
    now = (now or datetime.now()).replace(second=0, microsecond=0)
    start = _parse_hhmm(first_departure, now)
    end = _parse_hhmm(last_departure, now)

    if now > end:
        return [], f"Tuyen da ket thuc gio hoat dong hom nay ({first_departure} - {last_departure})."
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
        return [], f"Khong con chuyen nao trong hom nay (hoat dong {first_departure} - {last_departure})."
    return departures, None


def estimate_arrival_at_stop(first_departure: str, last_departure: str, headway_min: int,
                              stop_offset_min: float, now: Optional[datetime] = None
                              ) -> Tuple[Optional[datetime], Optional[str]]:
    """Gio xe (chuyen gan nhat) du kien den 1 tram cu the = gio khoi hanh dau tuyen + offset cua tram."""
    departures, msg = next_departures(first_departure, last_departure, headway_min, now=now, count=1)
    if not departures:
        return None, msg
    arrival = departures[0] + timedelta(minutes=stop_offset_min)
    return arrival, None


def minutes_until(target: datetime, now: Optional[datetime] = None) -> int:
    now = now or datetime.now()
    return max(0, int((target - now).total_seconds() // 60))
