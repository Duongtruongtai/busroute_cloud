# -*- coding: utf-8 -*-
"""
Thuật toán tìm tuyến xe buýt tối ưu (trực tiếp + tối đa 1 lần chuyển tuyến).

Cách tiếp cận (có thể giải thích trực tiếp khi bảo vệ đồ án):
1. Tìm tất cả các tuyến đi qua cả điểm đi và điểm đến -> gợi ý TUYẾN TRỰC TIẾP.
2. Nếu không có tuyến trực tiếp (hoặc để có thêm lựa chọn), duyệt qua từng tuyến
   đi qua điểm đi, xét các trạm mà tuyến đó đi qua SAU điểm đi làm "điểm trung
   chuyển" ứng viên; tại mỗi điểm trung chuyển, kiểm tra các tuyến khác đi qua
   điểm đó và có thể tiếp tục đến điểm đến -> gợi ý TUYẾN CÓ 1 LẦN CHUYỂN.
3. Xếp hạng kết quả theo: số lần chuyển tăng dần, rồi đến tổng thời gian di chuyển.

Độ phức tạp: O(số_tuyến_qua_điểm_đi * số_trạm_mỗi_tuyến * số_tuyến_qua_điểm_trung_chuyển),
phù hợp với quy mô mạng lưới demo (~15 tuyến, ~100 trạm). Với mạng lưới lớn hơn trong
thực tế, đây là bước có thể nâng cấp lên Dijkstra/A* trên đồ thị thời gian (future work).
"""
from dataclasses import dataclass
from typing import List, Optional, Set

import pandas as pd

TRANSFER_WALK_MIN = 3.0  # thời gian ước tính đi bộ + đợi giữa 2 tuyến tại cùng 1 trạm


@dataclass
class Leg:
    route_id: str
    route_short_name: str
    route_long_name: str
    route_long_name_en: str
    board_stop_id: str
    board_stop_name: str
    board_stop_name_en: str
    alight_stop_id: str
    alight_stop_name: str
    alight_stop_name_en: str
    board_offset_min: float
    alight_offset_min: float
    ride_minutes: float
    fare: int
    headway_min: int
    first_departure: str
    last_departure: str


@dataclass
class Itinerary:
    legs: List[Leg]
    total_minutes: float
    total_fare: int
    transfers: int

    def summary(self) -> str:
        return " -> ".join(f"{l.route_short_name}" for l in self.legs)


class RouteFinder:
    def __init__(self, routes_df: pd.DataFrame, route_stops_df: pd.DataFrame, stops_df: pd.DataFrame):
        self.routes_df = routes_df.set_index("route_id")
        self.stops_df = stops_df.set_index("stop_id")
        self.route_stops_df = route_stops_df.copy()

        self._by_route = {
            rid: g.sort_values("stop_sequence").reset_index(drop=True)
            for rid, g in route_stops_df.groupby("route_id")
        }
        self._routes_by_stop = route_stops_df.groupby("stop_id")["route_id"].apply(set).to_dict()

    def stop_name(self, stop_id: str, lang: str = "vi") -> str:
        try:
            row = self.stops_df.loc[stop_id]
            if lang == "en" and "stop_name_en" in row and pd.notna(row["stop_name_en"]):
                return str(row["stop_name_en"])
            return str(row["stop_name"])
        except KeyError:
            return stop_id

    def routes_through(self, stop_id: str) -> Set[str]:
        return self._routes_by_stop.get(stop_id, set())

    def ordered_stops(self, route_id: str) -> List[dict]:
        """Danh sach tram theo thu tu tren 1 tuyen, kem toa do - dung cho ve ban do / tracking."""
        g = self._by_route.get(route_id)
        if g is None:
            return []
        result = []
        for _, row in g.iterrows():
            sid = row["stop_id"]
            srow = self.stops_df.loc[sid]
            result.append({
                "stop_id": sid,
                "stop_name": str(srow["stop_name"]),
                "stop_name_en": str(srow.get("stop_name_en", srow["stop_name"])),
                "offset_min": float(row["offset_min"]),
                "lat": float(srow["lat"]),
                "lon": float(srow["lon"]),
            })
        return result

    def stops_between(self, route_id: str, board_stop_id: str, alight_stop_id: str) -> List[str]:
        """Danh sach stop_id lien tiep tren 1 tuyen tu tram len den tram xuong (dung ve polyline).
        Ho tro ca chieu nguoc (tuyen chay khu hoi) - tra ve theo dung thu tu di chuyen thuc te."""
        g = self._by_route[route_id]
        o_seq = int(g[g.stop_id == board_stop_id].iloc[0]["stop_sequence"])
        d_seq = int(g[g.stop_id == alight_stop_id].iloc[0]["stop_sequence"])
        lo, hi = min(o_seq, d_seq), max(o_seq, d_seq)
        seg = g[(g.stop_sequence >= lo) & (g.stop_sequence <= hi)].sort_values("stop_sequence")
        stop_ids = list(seg["stop_id"])
        return list(reversed(stop_ids)) if o_seq > d_seq else stop_ids

    def _fare(self, route_id: str, fare_type: str) -> int:
        row = self.routes_df.loc[route_id]
        return int(row["fare_student"] if fare_type == "student" else row["fare_regular"])

    def _direct_leg(self, route_id: str, origin_id: str, dest_id: str, fare_type: str) -> Optional[Leg]:
        # Tuyen xe buyt that su luon chay khu hoi (2 chieu), nen 1 tuyen co the dung de
        # di theo CA HAI chieu doc theo hanh lang cua no - khong chi theo dung thu tu
        # offset_min tang dan (offset_min chi la mo ta 1 SHAPE vat ly, khong phai huong
        # di cu the cua 1 chuyen xe). Thoi gian di chuyen = tri tuyet doi cua chenh lech offset.
        g = self._by_route.get(route_id)
        if g is None:
            return None
        o = g[g.stop_id == origin_id]
        d = g[g.stop_id == dest_id]
        if o.empty or d.empty:
            return None
        o_off = float(o.iloc[0]["offset_min"])
        d_off = float(d.iloc[0]["offset_min"])
        if d_off == o_off:
            return None
        route = self.routes_df.loc[route_id]
        return Leg(
            route_id=route_id,
            route_short_name=str(route["route_short_name"]),
            route_long_name=str(route["route_long_name"]),
            route_long_name_en=str(route.get("route_long_name_en", route["route_long_name"])),
            board_stop_id=origin_id,
            board_stop_name=self.stop_name(origin_id, "vi"),
            board_stop_name_en=self.stop_name(origin_id, "en"),
            alight_stop_id=dest_id,
            alight_stop_name=self.stop_name(dest_id, "vi"),
            alight_stop_name_en=self.stop_name(dest_id, "en"),
            board_offset_min=o_off,
            alight_offset_min=d_off,
            ride_minutes=abs(d_off - o_off),
            fare=self._fare(route_id, fare_type),
            headway_min=int(route["headway_min"]),
            first_departure=str(route["first_departure"]),
            last_departure=str(route["last_departure"]),
        )

    def find(self, origin_id: str, dest_id: str, fare_type: str = "student",
              max_results: int = 3) -> List[Itinerary]:
        if origin_id == dest_id:
            return []

        origin_routes = self.routes_through(origin_id)
        dest_routes = self.routes_through(dest_id)
        itineraries: List[Itinerary] = []

        # 1) Tuyen truc tiep
        for rid in origin_routes & dest_routes:
            leg = self._direct_leg(rid, origin_id, dest_id, fare_type)
            if leg:
                itineraries.append(Itinerary(legs=[leg], total_minutes=leg.ride_minutes,
                                              total_fare=leg.fare, transfers=0))

        # 2) Toi da 1 lan chuyen tuyen (tuyen chay khu hoi nen xet ca 2 huong tu diem di)
        for r1 in origin_routes:
            g1 = self._by_route[r1]
            candidates = g1[g1.stop_id != origin_id]

            for _, cand in candidates.iterrows():
                transfer_stop = cand["stop_id"]
                if transfer_stop == dest_id:
                    continue
                for r2 in self.routes_through(transfer_stop):
                    if r2 == r1:
                        continue
                    if dest_id not in set(self._by_route[r2]["stop_id"]):
                        continue
                    leg1 = self._direct_leg(r1, origin_id, transfer_stop, fare_type)
                    leg2 = self._direct_leg(r2, transfer_stop, dest_id, fare_type)
                    if not leg1 or not leg2:
                        continue
                    wait2 = leg2.headway_min / 2.0
                    total_minutes = leg1.ride_minutes + TRANSFER_WALK_MIN + wait2 + leg2.ride_minutes
                    total_fare = leg1.fare + leg2.fare
                    itineraries.append(Itinerary(legs=[leg1, leg2], total_minutes=total_minutes,
                                                  total_fare=total_fare, transfers=1))

        # Loai trung + xep hang: it chuyen tuyen hon truoc, roi den thoi gian ngan hon
        seen = set()
        deduped: List[Itinerary] = []
        for it in itineraries:
            key = tuple((l.route_id, l.board_stop_id, l.alight_stop_id) for l in it.legs)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(it)

        deduped.sort(key=lambda it: (it.transfers, it.total_minutes))
        return deduped[:max_results]
