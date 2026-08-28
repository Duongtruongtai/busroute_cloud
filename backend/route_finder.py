"""
Thuat toan tim tuyen xe buyt toi uu (truc tiep + toi da 1 lan chuyen tuyen).

Cach tiep can (co the giai thich truc tiep khi bao ve do an):
1. Tim tat ca cac tuyen di qua ca diem di va diem den -> goi y TUYEN TRUC TIEP.
2. Neu khong co tuyen truc tiep (hoac de co them lua chon), duyet qua tung tuyen
   di qua diem di, xet cac tram ma tuyen do di qua SAU diem di lam "diem trung
   chuyen" ung vien; tai moi diem trung chuyen, kiem tra cac tuyen khac di qua
   diem do va co the tiep tuc den diem den -> goi y TUYEN CO 1 LAN CHUYEN.
3. Xep hang ket qua theo: so lan chuyen tang dan, roi den tong thoi gian di chuyen.

Do phuc tap: O(so_tuyen_qua_diem_di * so_tram_moi_tuyen * so_tuyen_qua_diem_trung_chuyen),
phu hop voi quy mo mang luoi demo (~10 tuyen, ~60 tram). Voi mang luoi lon hon trong
thuc te, day la buoc co the nang cap len Dijkstra/A* tren do thi thoi gian (future work).
"""
from dataclasses import dataclass, field
from typing import List, Optional, Set

import pandas as pd

TRANSFER_WALK_MIN = 3.0  # thoi gian uoc tinh di bo + doi giua 2 tuyen tai cung 1 tram


@dataclass
class Leg:
    route_id: str
    route_short_name: str
    route_long_name: str
    board_stop_id: str
    board_stop_name: str
    alight_stop_id: str
    alight_stop_name: str
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

    @property
    def summary(self) -> str:
        return " -> ".join(f"Tuyen {l.route_short_name}" for l in self.legs)

    @property
    def transfer_stop_names(self) -> List[str]:
        return [l.board_stop_name for l in self.legs[1:]]


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

    def stop_name(self, stop_id: str) -> str:
        try:
            return str(self.stops_df.loc[stop_id, "stop_name"])
        except KeyError:
            return stop_id

    def routes_through(self, stop_id: str) -> Set[str]:
        return self._routes_by_stop.get(stop_id, set())

    def stops_between(self, route_id: str, board_stop_id: str, alight_stop_id: str) -> List[str]:
        """Danh sach stop_id lien tiep tren 1 tuyen tu tram len den tram xuong (dung ve polyline)."""
        g = self._by_route[route_id]
        o_seq = int(g[g.stop_id == board_stop_id].iloc[0]["stop_sequence"])
        d_seq = int(g[g.stop_id == alight_stop_id].iloc[0]["stop_sequence"])
        seg = g[(g.stop_sequence >= o_seq) & (g.stop_sequence <= d_seq)].sort_values("stop_sequence")
        return list(seg["stop_id"])

    def _fare(self, route_id: str, fare_type: str) -> int:
        row = self.routes_df.loc[route_id]
        return int(row["fare_student"] if fare_type == "student" else row["fare_regular"])

    def _direct_leg(self, route_id: str, origin_id: str, dest_id: str, fare_type: str) -> Optional[Leg]:
        g = self._by_route.get(route_id)
        if g is None:
            return None
        o = g[g.stop_id == origin_id]
        d = g[g.stop_id == dest_id]
        if o.empty or d.empty:
            return None
        o_off = float(o.iloc[0]["offset_min"])
        d_off = float(d.iloc[0]["offset_min"])
        if d_off <= o_off:
            return None  # du lieu mo phong xe chay 1 chieu trong danh sach nay
        route = self.routes_df.loc[route_id]
        return Leg(
            route_id=route_id,
            route_short_name=str(route["route_short_name"]),
            route_long_name=str(route["route_long_name"]),
            board_stop_id=origin_id,
            board_stop_name=self.stop_name(origin_id),
            alight_stop_id=dest_id,
            alight_stop_name=self.stop_name(dest_id),
            board_offset_min=o_off,
            alight_offset_min=d_off,
            ride_minutes=d_off - o_off,
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

        # 2) Toi da 1 lan chuyen tuyen
        for r1 in origin_routes:
            g1 = self._by_route[r1]
            o1_rows = g1[g1.stop_id == origin_id]
            if o1_rows.empty:
                continue
            o1_off = float(o1_rows.iloc[0]["offset_min"])
            candidates = g1[g1.offset_min > o1_off]

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
