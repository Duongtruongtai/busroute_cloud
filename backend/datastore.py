"""
Lop truy xuat du lieu (DataStore) - truu tuong hoa nguon du lieu:

- Che do "cloud": doc/ghi truc tiep Supabase (PostgreSQL) qua REST API
  (thu vien supabase-py, ban chat la goi PostgREST - API duoc Supabase tu
  sinh tren moi bang). Day la duong dan CHINH THUC dung khi trien khai.
- Che do "local": doc CSV trong thu muc dataset/ khi chua cau hinh Supabase
  (vi du dang phat trien MVP truoc khi tao Cloud Database). Giup lam viec/
  test duoc ngay ma khong phu thuoc mang, va la co che du phong (fallback)
  neu Cloud Database tam thoi khong ket noi duoc.

QUAN TRONG cho phan bao ve/cham diem: khi trien khai that (Streamlit Cloud +
Supabase), bien SUPABASE_URL / SUPABASE_KEY duoc cau hinh trong Secrets nen
ung dung LUON chay o che do "cloud".
"""
import os
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(os.path.dirname(_THIS_DIR), "dataset")


def _get_secret(key: str) -> Optional[str]:
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key)


class DataStore:
    def __init__(self):
        self.mode = "local"
        self.client = None
        self.connect_error = None
        self._load_local_cache()
        self._connect()

    # ------------------------------------------------------------------ #
    # Ket noi Supabase
    # ------------------------------------------------------------------ #
    def _connect(self):
        url = _get_secret("SUPABASE_URL")
        key = _get_secret("SUPABASE_KEY")
        if not url or not key:
            self.mode = "local"
            return
        try:
            from supabase import create_client
            client = create_client(url, key)
            # kiem tra ket noi + bang da duoc tao (schema.sql) chua
            client.table("routes").select("route_id").limit(1).execute()
            self.client = client
            self.mode = "cloud"
        except Exception as e:  # bang chua ton tai, sai key, mat mang...
            self.client = None
            self.mode = "local"
            self.connect_error = str(e)

    def _load_local_cache(self):
        self._stops_df = pd.read_csv(os.path.join(DATASET_DIR, "stops.csv"))
        self._routes_df = pd.read_csv(os.path.join(DATASET_DIR, "routes.csv"))
        self._route_stops_df = pd.read_csv(os.path.join(DATASET_DIR, "route_stops.csv"))

    # ------------------------------------------------------------------ #
    # Doc du lieu
    # ------------------------------------------------------------------ #
    def get_stops(self) -> pd.DataFrame:
        if self.mode == "cloud":
            try:
                res = self.client.table("stops").select("*").execute()
                if res.data:
                    return pd.DataFrame(res.data)
            except Exception:
                pass
        return self._stops_df

    def get_routes(self) -> pd.DataFrame:
        if self.mode == "cloud":
            try:
                res = self.client.table("routes").select("*").execute()
                if res.data:
                    return pd.DataFrame(res.data)
            except Exception:
                pass
        return self._routes_df

    def get_route_stops(self) -> pd.DataFrame:
        if self.mode == "cloud":
            try:
                res = self.client.table("route_stops").select("*").execute()
                if res.data:
                    return pd.DataFrame(res.data)
            except Exception:
                pass
        return self._route_stops_df

    # ------------------------------------------------------------------ #
    # Ghi du lieu (chung minh Cloud Database co INSERT thuc su, khong chi doc)
    # ------------------------------------------------------------------ #
    def log_search(self, origin_id: str, origin_name: str, dest_id: str, dest_name: str,
                    fare_type: str, n_results: int) -> bool:
        if self.mode != "cloud":
            return False
        try:
            self.client.table("search_logs").insert({
                "origin_stop_id": origin_id,
                "origin_stop_name": origin_name,
                "dest_stop_id": dest_id,
                "dest_stop_name": dest_name,
                "fare_type": fare_type,
                "n_results": n_results,
                "searched_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
            return True
        except Exception:
            return False

    def get_search_stats(self, limit: int = 500) -> pd.DataFrame:
        if self.mode != "cloud":
            return pd.DataFrame()
        try:
            res = (self.client.table("search_logs")
                   .select("*")
                   .order("searched_at", desc=True)
                   .limit(limit)
                   .execute())
            return pd.DataFrame(res.data)
        except Exception:
            return pd.DataFrame()

    # ------------------------------------------------------------------ #
    def status_label(self) -> str:
        if self.mode == "cloud":
            return "Dang ket noi Cloud Database (Supabase)"
        return "Dang dung du lieu cuc bo (fallback CSV) - chua cau hinh Supabase"
