"""
Smart City Bus Assistant
Cong tra cuu tuyen & uoc tinh thoi gian xe buyt do thi (TP.HCM) - do an hoc phan
Ung dung Dien toan dam may.

Kien truc Cloud:
    USER -> Streamlit Web App (Cloud Hosting)
         -> Supabase (Cloud Database - PostgreSQL, tu sinh Cloud API qua PostgREST)
         -> Supabase Storage (sao luu dataset - Cloud Storage)
"""
import os
import sys
from datetime import datetime

import pandas as pd
import streamlit as st

# Cho phep import goi "backend" khi chay `streamlit run frontend/app.py`
# (Streamlit dat sys.path[0] la thu muc chua file script, tuc frontend/,
# nen can them thu muc goc du an vao sys.path).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.datastore import DataStore
from backend.fare import FARE_TYPES, format_minutes, format_vnd
from backend.route_finder import Itinerary, RouteFinder
from backend.schedule import estimate_arrival_at_stop

st.set_page_config(
    page_title="Smart City Bus Assistant",
    page_icon="🚌",
    layout="wide",
)

LEG_COLORS = ["#2563eb", "#dc2626", "#16a34a", "#d97706"]


# --------------------------------------------------------------------------- #
# Data loading (cached)
# --------------------------------------------------------------------------- #
@st.cache_resource(show_spinner=False)
def get_datastore() -> DataStore:
    return DataStore()


@st.cache_data(ttl=300, show_spinner="Dang tai du lieu tuyen xe buyt...")
def load_data(_ds: DataStore):
    return _ds.get_stops(), _ds.get_routes(), _ds.get_route_stops()


@st.cache_resource(show_spinner=False)
def build_finder(stops_df: pd.DataFrame, routes_df: pd.DataFrame, route_stops_df: pd.DataFrame) -> RouteFinder:
    return RouteFinder(routes_df, route_stops_df, stops_df)


ds = get_datastore()
stops_df, routes_df, route_stops_df = load_data(ds)
finder = build_finder(stops_df, routes_df, route_stops_df)

stop_options = stops_df.sort_values("stop_name")["stop_id"].tolist()
stop_name_map = dict(zip(stops_df["stop_id"], stops_df["stop_name"]))


def fmt_stop(stop_id: str) -> str:
    return stop_name_map.get(stop_id, stop_id)


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown("## 🚌 Smart City Bus Assistant")
    st.caption("Tra cuu tuyen & uoc tinh thoi gian xe buyt do thi")

    if ds.mode == "cloud":
        st.success("🟢 " + ds.status_label())
    else:
        st.warning("🟡 " + ds.status_label())
        with st.expander("Vi sao chua ket noi Cloud Database?"):
            st.write(
                "Ung dung se tu dong chuyen sang Supabase (Cloud Database) khi bien "
                "`SUPABASE_URL` va `SUPABASE_KEY` duoc cau hinh trong `.streamlit/secrets.toml` "
                "(local) hoac muc Secrets cua Streamlit Cloud (khi trien khai). "
                "Xem huong dan trong README.md."
            )
            if ds.connect_error:
                st.code(ds.connect_error, language="text")

    st.divider()
    fare_type = st.radio(
        "Loai ve",
        options=list(FARE_TYPES.keys()),
        format_func=lambda k: FARE_TYPES[k],
        index=0,
    )

    st.divider()
    st.metric("So tuyen dang khai thac (demo)", len(routes_df))
    st.metric("So tram dung", len(stops_df))

    if st.button("🔄 Lam moi du lieu tu Cloud"):
        get_datastore.clear()
        load_data.clear()
        build_finder.clear()
        st.rerun()


# --------------------------------------------------------------------------- #
# Main tabs
# --------------------------------------------------------------------------- #
tab_search, tab_stats, tab_about = st.tabs(["🔍 Tra cuu tuyen", "📊 Thong ke", "ℹ️ Gioi thieu"])

# --------------------------------------------------------------------------- #
# TAB 1: Tra cuu tuyen
# --------------------------------------------------------------------------- #
with tab_search:
    st.subheader("Nhap diem di - diem den")

    col1, col_swap, col2 = st.columns([5, 1, 5])
    if "origin" not in st.session_state:
        st.session_state.origin = stop_options[0]
    if "dest" not in st.session_state:
        st.session_state.dest = stop_options[1] if len(stop_options) > 1 else stop_options[0]

    with col1:
        origin = st.selectbox("📍 Diem di", options=stop_options, format_func=fmt_stop,
                               key="origin")
    with col_swap:
        st.write("")
        st.write("")
        if st.button("🔁", help="Doi chieu diem di / diem den"):
            st.session_state.origin, st.session_state.dest = st.session_state.dest, st.session_state.origin
            st.rerun()
    with col2:
        dest = st.selectbox("🏁 Diem den", options=stop_options, format_func=fmt_stop,
                             key="dest")

    search_clicked = st.button("🔍 Tim tuyen xe buyt", type="primary", width='stretch')

    if search_clicked:
        if origin == dest:
            st.error("Diem di va diem den dang trung nhau. Vui long chon 2 tram khac nhau.")
        else:
            itineraries = finder.find(origin, dest, fare_type=fare_type, max_results=3)
            ds.log_search(origin, fmt_stop(origin), dest, fmt_stop(dest), fare_type, len(itineraries))
            st.session_state["last_itineraries"] = itineraries
            st.session_state["last_origin"] = origin
            st.session_state["last_dest"] = dest

    itineraries = st.session_state.get("last_itineraries")

    if itineraries is not None:
        if len(itineraries) == 0:
            st.warning(
                "Khong tim thay tuyen phu hop (truc tiep hoac 1 lan chuyen tuyen) giua 2 diem da chon "
                "trong du lieu demo hien tai. Hay thu 2 tram khac, vi du cac ben trung tam nhu "
                "'Cho Ben Thanh' hoac 'Ben xe Cho Lon'."
            )
        else:
            st.success(f"Tim thay {len(itineraries)} phuong an di chuyen.")
            labels = [
                f"Phuong an {i + 1}: {it.summary}  •  {format_minutes(it.total_minutes)}  •  "
                f"{format_vnd(it.total_fare)}  •  {it.transfers} lan chuyen"
                for i, it in enumerate(itineraries)
            ]
            chosen_idx = st.radio("Chon phuong an de xem chi tiet / ban do:", options=range(len(itineraries)),
                                   format_func=lambda i: labels[i])
            chosen: Itinerary = itineraries[chosen_idx]

            m1, m2, m3 = st.columns(3)
            m1.metric("Tong thoi gian uoc tinh", format_minutes(chosen.total_minutes))
            m2.metric("Tong tien ve", format_vnd(chosen.total_fare))
            m3.metric("So lan chuyen tuyen", chosen.transfers)

            st.markdown("#### Chi tiet hanh trinh")
            now = datetime.now()
            for i, leg in enumerate(chosen.legs):
                arrival, msg = estimate_arrival_at_stop(
                    leg.first_departure, leg.last_departure, leg.headway_min,
                    leg.board_offset_min, now=now,
                )
                with st.container(border=True):
                    st.markdown(
                        f"**Chang {i + 1}: Tuyen {leg.route_short_name}** — {leg.route_long_name}"
                    )
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"🚏 Len xe: **{leg.board_stop_name}**")
                    c2.write(f"🏁 Xuong xe: **{leg.alight_stop_name}**")
                    c3.write(f"⏱ Thoi gian tren xe: **{format_minutes(leg.ride_minutes)}**")
                    c4, c5 = st.columns(2)
                    c4.write(f"💵 Gia ve: **{format_vnd(leg.fare)}**")
                    if arrival:
                        c5.write(f"🕒 Xe du kien den tram luc: **{arrival.strftime('%H:%M')}**")
                    else:
                        c5.write(f"🕒 {msg}")
                if i < len(chosen.legs) - 1:
                    st.markdown(
                        f"<div style='text-align:center;color:#999;'>⇩ Chuyen tuyen tai "
                        f"<b>{leg.alight_stop_name}</b> (uoc tinh cho + di bo ~"
                        f"{format_minutes(3 + chosen.legs[i + 1].headway_min / 2)}) ⇩</div>",
                        unsafe_allow_html=True,
                    )

            st.markdown("#### Ban do hanh trinh")
            try:
                import folium
                from streamlit_folium import st_folium

                stops_idx = stops_df.set_index("stop_id")
                all_latlon = []
                fmap = folium.Map(location=[10.78, 106.70], zoom_start=12, tiles="cartodbpositron")

                for i, leg in enumerate(chosen.legs):
                    seq = finder.stops_between(leg.route_id, leg.board_stop_id, leg.alight_stop_id)
                    latlons = [(float(stops_idx.loc[sid, "lat"]), float(stops_idx.loc[sid, "lon"])) for sid in seq]
                    all_latlon.extend(latlons)
                    color = LEG_COLORS[i % len(LEG_COLORS)]
                    folium.PolyLine(latlons, color=color, weight=5, opacity=0.85,
                                     tooltip=f"Tuyen {leg.route_short_name}").add_to(fmap)
                    for j, sid in enumerate(seq):
                        row = stops_idx.loc[sid]
                        is_endpoint = j == 0 or j == len(seq) - 1
                        folium.CircleMarker(
                            location=(float(row["lat"]), float(row["lon"])),
                            radius=6 if is_endpoint else 3,
                            color=color, fill=True, fill_opacity=0.9,
                            popup=str(row["stop_name"]),
                        ).add_to(fmap)

                o_row = stops_idx.loc[chosen.legs[0].board_stop_id]
                d_row = stops_idx.loc[chosen.legs[-1].alight_stop_id]
                folium.Marker((float(o_row["lat"]), float(o_row["lon"])), popup="Diem di",
                               icon=folium.Icon(color="green", icon="play", prefix="fa")).add_to(fmap)
                folium.Marker((float(d_row["lat"]), float(d_row["lon"])), popup="Diem den",
                               icon=folium.Icon(color="red", icon="flag", prefix="fa")).add_to(fmap)

                if all_latlon:
                    fmap.fit_bounds(all_latlon)

                st_folium(fmap, width=None, height=480, key="route_map")
            except ImportError:
                st.info("Cai dat `folium` va `streamlit-folium` (xem requirements.txt) de hien thi ban do.")

# --------------------------------------------------------------------------- #
# TAB 2: Thong ke
# --------------------------------------------------------------------------- #
with tab_stats:
    st.subheader("Thong ke mang luoi")
    hub_stats = (
        route_stops_df.groupby("stop_id")["route_id"].nunique().rename("so_tuyen_di_qua")
        .reset_index().merge(stops_df[["stop_id", "stop_name"]], on="stop_id")
        .sort_values("so_tuyen_di_qua", ascending=False).head(10)
    )
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Top 10 tram trung chuyen nhieu tuyen nhat**")
        st.dataframe(
            hub_stats.rename(columns={"stop_name": "Ten tram", "so_tuyen_di_qua": "So tuyen"})
            [["Ten tram", "So tuyen"]],
            hide_index=True, width='stretch',
        )
    with c2:
        st.markdown("**Danh sach tuyen dang khai thac**")
        st.dataframe(
            routes_df.rename(columns={
                "route_short_name": "So hieu", "route_long_name": "Lo trinh",
                "fare_regular": "Gia pho thong", "fare_student": "Gia sinh vien",
                "headway_min": "Gian cach (phut)",
            })[["So hieu", "Lo trinh", "Gia pho thong", "Gia sinh vien", "Gian cach (phut)"]],
            hide_index=True, width='stretch',
        )

    st.divider()
    st.subheader("Lich su tim kiem tu Cloud Database (search_logs)")
    if ds.mode != "cloud":
        st.info(
            "Tinh nang nay doc du lieu that tu bang `search_logs` tren Supabase. "
            "Hay cau hinh Cloud Database (xem README) de xem thong ke tim kiem thuc te "
            "cua nguoi dung."
        )
    else:
        logs = ds.get_search_stats()
        if logs.empty:
            st.info("Chua co luot tim kiem nao duoc ghi nhan. Hay thu tra cuu 1 tuyen o tab dau tien.")
        else:
            l1, l2 = st.columns(2)
            l1.metric("Tong so luot tim kiem", len(logs))
            top_od = (
                logs.groupby(["origin_stop_name", "dest_stop_name"]).size()
                .rename("so_lan").reset_index().sort_values("so_lan", ascending=False).head(5)
            )
            l2.metric("So cap diem di-den khac nhau", logs.groupby(["origin_stop_name", "dest_stop_name"]).ngroups)

            st.markdown("**Top 5 tuyen duong duoc tim kiem nhieu nhat**")
            st.dataframe(
                top_od.rename(columns={"origin_stop_name": "Diem di", "dest_stop_name": "Diem den",
                                        "so_lan": "So lan tim"}),
                hide_index=True, width='stretch',
            )
            st.markdown("**20 luot tim kiem gan nhat**")
            st.dataframe(
                logs[["searched_at", "origin_stop_name", "dest_stop_name", "fare_type", "n_results"]].head(20),
                hide_index=True, width='stretch',
            )

# --------------------------------------------------------------------------- #
# TAB 3: Gioi thieu
# --------------------------------------------------------------------------- #
with tab_about:
    st.markdown(
        """
### Van de thuc te
Sinh vien va nguoi khong co xe ca nhan phu thuoc vao xe buyt nhung gap kho khan
khi tra cuu thoi gian xe den tram, cac diem trung chuyen, hoac tinh toan chi phi
di chuyen tiet kiem nhat giua nhieu tuyen.

**Doi tuong:** sinh vien, nguoi cao tuoi, nguoi di lam bang phuong tien cong cong.

### Giai phap
Cong tra cuu tuyen xe buyt cho phep nguoi dung nhap diem di / diem den, he thong
tu dong goi y tuyen toi uu (truc tiep hoac co 1 lan chuyen tuyen), uoc tinh thoi
gian xe den va chi phi ve (uu dai sinh vien), hien thi truc quan tren ban do.

### Kien truc Cloud
```
USER
  |
  v
Streamlit Web App  ---------------->  Cloud Hosting (Streamlit Community Cloud)
  |
  v
supabase-py client
  |
  v
Supabase (PostgreSQL) --------------> Cloud Database
  |  \\
  |   \\--> PostgREST (Cloud API tu sinh, goi qua supabase-py)
  v
Supabase Storage  ------------------> Cloud Storage (sao luu dataset CSV)
```

### Cong nghe su dung
| Thanh phan | Cong nghe |
|---|---|
| Frontend + Backend | Streamlit (Python) |
| Cloud Database | Supabase (PostgreSQL) |
| Cloud API | Supabase auto REST API (PostgREST) qua `supabase-py` |
| Cloud Storage | Supabase Storage (sao luu dataset) |
| Cloud Hosting | Streamlit Community Cloud |
| Ban do | Folium + streamlit-folium |
| Version control | GitHub |

### Nguon du lieu & gioi han
Bo du lieu demo (`dataset/`) duoc bien soan thu cong theo cau truc chuan GTFS
(stops / routes / route_stops), dua tren so hieu tuyen va cac diem dau-cuoi
(ben xe, truong hoc, san bay) co that tai TP.HCM; toa do cac tram trung gian
duoc **noi suy tuyen tinh** giua cac diem neo de phuc vu minh hoa, khong phai
du lieu GTFS chinh thuc. Gio xe la **uoc tinh theo bieu do chay chuan** (chua
tich hop GPS thoi gian thuc) - day la huong phat trien tiep theo cua du an.
        """
    )
