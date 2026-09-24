# -*- coding: utf-8 -*-
"""
Smart City Bus Assistant
Cổng tra cứu tuyến & theo dõi xe buýt đô thị TP. Hồ Chí Minh (74 tuyến, dữ liệu
thực tế 2026) trên bản đồ. Đồ án học phần Ứng dụng Điện toán đám mây.

Kiến trúc Cloud:
    USER -> Streamlit Web App (Cloud Hosting)
         -> Supabase (Cloud Database - PostgreSQL, tự sinh Cloud API qua PostgREST)
         -> Supabase Storage (sao lưu dataset - Cloud Storage)

Ghi chú quan trọng: vị trí xe buýt hiển thị trên bản đồ là MÔ PHỎNG theo biểu đồ
chạy chuẩn (không có API GPS thời gian thực công khai/miễn phí cho xe buýt tại
Việt Nam) - xem `backend/tracking.py` và mục "Giới thiệu" trong ứng dụng.
"""
import os
import sys
from datetime import datetime

import pandas as pd
import streamlit as st
from streamlit_searchbox import st_searchbox

# Cho phep import goi "backend" khi chay `streamlit run frontend/app.py`
# (Streamlit dat sys.path[0] la thu muc chua file script, tuc frontend/,
# nen can them thu muc goc du an vao sys.path).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.datastore import DataStore
from backend.fare import FARE_TYPES, format_minutes, format_vnd
from backend.geocoding import geocode, nearest_stops
from backend.i18n import t
from backend.route_finder import RouteFinder
from backend.schedule import estimate_arrival_at_stop, is_route_active
from backend.search import local_search_stops
from backend.tracking import active_buses

st.set_page_config(page_title="Smart City Bus Assistant", page_icon="🚌", layout="wide")

MAP_CENTER = (10.77, 106.70)
MAP_ZOOM = 11
MANUAL_SENTINEL = "__none__"

# --------------------------------------------------------------------------- #
# Session state defaults
# --------------------------------------------------------------------------- #
for key, default in {
    "lang": "vi", "dark_mode": False,
    "origin_stop_id": None, "dest_stop_id": None, "swap_nonce": 0,
    "selected_itineraries": None, "chosen_itinerary_idx": 0,
    "browse_route_id": MANUAL_SENTINEL, "live_refresh": False,
}.items():
    st.session_state.setdefault(key, default)


# --------------------------------------------------------------------------- #
# Data loading (cached)
# --------------------------------------------------------------------------- #
@st.cache_resource(show_spinner=False)
def get_datastore() -> DataStore:
    return DataStore()


@st.cache_data(ttl=300, show_spinner=False)
def load_data(_ds: DataStore):
    return _ds.get_stops(), _ds.get_routes(), _ds.get_route_stops()


@st.cache_resource(show_spinner=False)
def build_finder(stops_df: pd.DataFrame, routes_df: pd.DataFrame, route_stops_df: pd.DataFrame) -> RouteFinder:
    return RouteFinder(routes_df, route_stops_df, stops_df)


ds = get_datastore()
stops_df, routes_df, route_stops_df = load_data(ds)
finder = build_finder(stops_df, routes_df, route_stops_df)
routes_idx = routes_df.set_index("route_id")


# --------------------------------------------------------------------------- #
# Theme (CSS) injection
# --------------------------------------------------------------------------- #
def inject_theme_css(dark: bool):
    # Ban do can mau sac day du (song ngoi, duong, nhan dia danh) thay vi tile xam don
    # dieu. Tung dung tile "OpenStreetMap" mac dinh cua Folium nhung tile.openstreetmap.org
    # co the bi chan/khong on dinh tren mot so mang (gay ra man hinh xam trong, chi thay
    # duong ve ma khong thay ban do). Doi sang Esri World Street Map - cung ha tang
    # ArcGIS Online da kiem chung on dinh (dung cho tile xam truoc do), van co day du mau
    # sac duong/song/nhan dia danh, mien phi khong can API key. Giao dien toi KHONG doi
    # nguon tile (CartoDB dark can key) ma inject CSS filter dao mau ngay trong HTML cua
    # ban do (xem duoi) - giu nguyen chi tiet ban do.
    tile = ("https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Street_Map/MapServer/tile/{z}/{y}/{x}")
    tile_attr = "Tiles &copy; Esri &mdash; Source: Esri, HERE, Garmin, OpenStreetMap contributors"
    st.session_state["_map_tile"] = tile
    st.session_state["_map_tile_attr"] = tile_attr
    if dark:
        bg, bg2, text, subtext, card, border, accent = (
            "#0f172a", "#1e293b", "#f1f5f9", "#94a3b8", "#1e293b", "#334155", "#38bdf8")
    else:
        bg, bg2, text, subtext, card, border, accent = (
            "#ffffff", "#f8fafc", "#0f172a", "#64748b", "#ffffff", "#e2e8f0", "#2563eb")

    def _rgba(hex_color: str, alpha: float) -> str:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    accent_soft = _rgba(accent, 0.06)
    accent_soft2 = _rgba(accent, 0.14)
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; font-size: 16px; }}

    .stApp {{ background-color: {bg}; }}
    [data-testid="stSidebar"] {{ background-color: {bg2}; }}
    [data-testid="stMarkdownContainer"] {{ color: {text}; }}
    [data-testid="stCaptionContainer"] {{ color: {subtext}; }}

    /* Metric mac dinh cua Streamlit khá to, tren sidebar hep de bi tran/cat chu -
       thu nho + cho xuong dong thay vi cat chu (...). */
    [data-testid="stMetricValue"] {{ color: {text}; font-size: 22px; }}
    [data-testid="stMetricLabel"] {{
        color: {text}; font-size: 13px; white-space: normal; overflow-wrap: break-word;
    }}

    /* ---- Hero / search card ---- */
    .hero-title {{ font-size: 24px; font-weight: 700; color: {text}; margin-bottom: 2px; }}
    .hero-subtitle {{ font-size: 15px; color: {subtext}; margin-bottom: 10px; }}
    .feature-strip {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }}
    .feature-chip {{
        display: inline-flex; align-items: center; gap: 6px; background: {accent_soft2};
        border: 1px solid {border}; border-radius: 999px; padding: 6px 13px;
        font-size: 13px; font-weight: 600; color: {text};
    }}
    .search-card {{
        background-color: {card}; border: 1px solid {border}; border-radius: 16px;
        padding: 18px; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }}

    /* ---- Route / itinerary cards ---- */
    .bus-card {{
        background-color: {card}; border: 1px solid {border}; border-radius: 12px;
        padding: 14px; margin-bottom: 10px; color: {text};
        box-shadow: 0 1px 3px rgba(0,0,0,0.05); overflow-wrap: break-word;
    }}
    .route-number {{
        display: inline-block; background: {accent}; color: white; font-weight: 700;
        font-size: 13.5px; padding: 3px 9px; border-radius: 8px; letter-spacing: 0.3px;
    }}
    .route-name {{ font-size: 14.5px; font-weight: 500; color: {text}; margin-top: 6px; }}
    .metric-row {{ display: flex; gap: 14px; margin-top: 8px; font-size: 13.5px; color: {subtext}; flex-wrap: wrap; }}
    .metric-row b {{ color: {text}; }}
    .tag-pill {{
        display: inline-block; font-size: 12px; font-weight: 600; padding: 3px 8px;
        border-radius: 999px; margin-right: 6px; margin-bottom: 6px;
    }}
    .tag-best {{ background: #dbeafe; color: #1d4ed8; }}
    .tag-fast {{ background: #dcfce7; color: #15803d; }}
    .tag-cheap {{ background: #fef9c3; color: #a16207; }}
    .tag-fewtransfer {{ background: #f3e8ff; color: #7e22ce; }}
    .tag-subsidized {{ background: #dcfce7; color: #15803d; }}
    .tag-not-subsidized {{ background: #fef3c7; color: #b45309; }}

    .bus-badge-active {{ color: #16a34a; font-weight: 600; font-size: 12.5px; }}
    .bus-badge-inactive {{ color: #94a3b8; font-weight: 600; font-size: 12.5px; }}

    /* ---- Bang so sanh phuong an (Citymapper-style: Fastest/Least walking/...) ---- */
    .compare-card {{
        background-color: {card}; border: 1px solid {border}; border-radius: 12px;
        padding: 10px 8px; text-align: center; margin-bottom: 8px; min-height: 92px;
    }}
    .compare-card.active {{ border: 2px solid {accent}; }}
    .compare-time {{ font-size: 23px; font-weight: 700; color: {text}; margin: 3px 0 1px; }}
    .compare-sub {{ font-size: 12px; color: {subtext}; line-height: 1.5; }}

    /* ---- The hanh trinh chinh (hero card): so phut la thanh phan to nhat ---- */
    .hero-card {{
        background-color: {card}; border: 1px solid {border}; border-radius: 14px;
        padding: 18px; margin: 10px 0 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }}
    .hero-time {{ font-size: 38px; font-weight: 700; color: {accent}; line-height: 1.1; }}
    .hero-sub {{ font-size: 14px; color: {subtext}; margin-top: 2px; }}
    .journey-flow {{ margin-top: 14px; font-size: 15px; color: {text}; }}
    .journey-row {{ display: flex; align-items: center; gap: 8px; padding: 3px 0; }}
    .journey-line {{ color: {border}; margin-left: 9px; padding: 1px 0 1px 8px;
        border-left: 2px solid {border}; font-size: 13px; color: {subtext}; }}

    .cloud-status-mini {{ font-size: 12.5px; color: {subtext}; }}

    .stButton>button[kind="primary"] {{
        background-color: {accent}; border-color: {accent}; border-radius: 10px;
        height: 46px; font-weight: 600; font-size: 15px;
    }}
    div[data-testid="stTextInput"] input {{ border-radius: 10px; min-height: 42px; font-size: 15px; }}

    /* ---- Bo chon khu vuc (segmented control) - dang pill be tron, gan gui hon ---- */
    div[data-testid="stSegmentedControl"] label {{
        border-radius: 999px !important; font-weight: 500;
    }}
    div[data-testid="stSegmentedControl"] label[data-checked="true"] {{
        background-color: {accent} !important; border-color: {accent} !important;
    }}

    /* ---- Diem xuyet visual: gradient nhe, hover-lift, bo nut mac dinh - tranh cam giac
       giao dien phang/don dieu ---- */
    .stApp {{ background-image: linear-gradient(180deg, {accent_soft} 0%, {bg} 320px); }}
    .search-card {{ background-image: linear-gradient(135deg, {accent_soft2} 0%, {card} 55%); }}
    .hero-card, .bus-card, .compare-card {{ transition: box-shadow 180ms ease, transform 180ms ease; }}
    .hero-card:hover, .bus-card:hover {{
        box-shadow: 0 6px 16px {accent_soft2}; transform: translateY(-1px);
    }}
    .compare-card:hover {{ box-shadow: 0 4px 10px {accent_soft2}; }}
    div[data-testid="stButton"] button:not([kind="primary"]) {{
        border-radius: 999px !important; border-color: {border} !important;
        font-weight: 600; transition: all 150ms ease;
        background-color: {card} !important; color: {text} !important;
    }}
    div[data-testid="stButton"] button:not([kind="primary"]):hover {{
        border-color: {accent} !important; color: {accent} !important; background: {accent_soft} !important;
    }}

    /* ---- Cac widget Streamlit mac dinh (button/selectbox/dropdown popover) doc theme
       SANG co dinh tu .streamlit/config.toml, khong tu doi theo cong tac Toi/Sang cua
       rieng app (CSS tu che o day, khong phai theme native cua Streamlit) - neu khong
       ghi de rieng se bi "mang trang" giua giao dien toi (nut, o chon, danh sach xo
       xuong deu trang xoa). ---- */
    div[data-testid="stSelectbox"] > div > div,
    div[data-testid="stSelectbox"] input {{
        background-color: {card} !important; color: {text} !important; border-color: {border} !important;
    }}
    div[data-baseweb="popover"] ul, div[data-baseweb="popover"] li,
    div[data-baseweb="menu"], ul[data-baseweb="menu"], li[data-baseweb="menu-item"] {{
        background-color: {card} !important; color: {text} !important;
    }}
    div[data-baseweb="popover"] li:hover, li[data-baseweb="menu-item"]:hover {{
        background-color: {accent_soft2} !important;
    }}
    </style>
    """, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
with st.sidebar:
    lang0 = st.session_state["lang"]
    st.markdown(f"## 🚌 {t('app_title', lang0)}")
    st.caption(t("app_subtitle", lang0))

    c1, c2 = st.columns(2)
    with c1:
        st.selectbox(t("language", lang0), options=["vi", "en"],
                     format_func=lambda x: "🇻🇳 Tiếng Việt" if x == "vi" else "🇬🇧 English", key="lang")
    with c2:
        st.toggle(t("theme_dark", lang0), key="dark_mode")

    lang = st.session_state["lang"]
    dark = st.session_state["dark_mode"]
    inject_theme_css(dark)

    st.divider()
    fare_type = st.radio(t("fare_type", lang), options=list(FARE_TYPES.keys()),
                          format_func=lambda k: t(f"fare_{k}", lang), key="fare_type_radio")

    st.divider()
    m1, m2 = st.columns(2)
    m1.metric(t("n_routes", lang), len(routes_df))
    m2.metric(t("n_stops", lang), len(stops_df))

    st.toggle(t("auto_refresh_on", lang), key="live_refresh")

if st.session_state["live_refresh"]:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=8000, key="live_map_autorefresh")


def fmt_stop(stop_id: str, lang: str) -> str:
    return finder.stop_name(stop_id, lang) if stop_id and stop_id != MANUAL_SENTINEL else stop_id


def leg_distance_km(route_id: str, board_id: str, alight_id: str) -> float:
    """Khoang cach uoc tinh cua 1 CHANG (tu tram len den tram xuong tren 1 tuyen)."""
    from backend.geocoding import haversine_km
    stops_idx = stops_df.set_index("stop_id")
    seq = finder.stops_between(route_id, board_id, alight_id)
    total = 0.0
    for sid_a, sid_b in zip(seq, seq[1:]):
        a, b = stops_idx.loc[sid_a], stops_idx.loc[sid_b]
        total += haversine_km(float(a["lat"]), float(a["lon"]), float(b["lat"]), float(b["lon"]))
    return total


def itinerary_distance_km(itinerary) -> float:
    """Tong khoang cach uoc tinh ca hanh trinh (cong don tat ca cac chang)."""
    return sum(leg_distance_km(l.route_id, l.board_stop_id, l.alight_stop_id) for l in itinerary.legs)


def itinerary_tags(itineraries, idx: int, lang: str) -> str:
    """Gan nhan Phu hop nhat / Nhanh nhat / Re nhat / It chuyen tuyen nhat cho 1 phuong an."""
    if len(itineraries) <= 1:
        return ""
    it = itineraries[idx]
    tags = []
    if idx == 0:
        tags.append(("tag-best", t("tag_best", lang)))
    if it.total_minutes == min(x.total_minutes for x in itineraries):
        tags.append(("tag-fast", t("tag_fastest", lang)))
    if it.total_fare == min(x.total_fare for x in itineraries):
        tags.append(("tag-cheap", t("tag_cheapest", lang)))
    if it.transfers == min(x.transfers for x in itineraries):
        tags.append(("tag-fewtransfer", t("tag_fewest_transfers", lang)))
    return "".join(f'<span class="tag-pill {cls}">{label}</span>' for cls, label in tags)


def subsidized_badge(route_row, lang: str) -> str:
    """The nho bao gia ve tuyen nay co duoc tro gia HSSV hay khong - giup sinh
    vien hieu vi sao gia ve khac nhau giua cac tuyen (toi uu chi phi)."""
    if bool(route_row.get("is_subsidized", True)):
        return f'<span class="tag-pill tag-subsidized">{t("subsidized_yes", lang)}</span>'
    return f'<span class="tag-pill tag-not-subsidized">{t("subsidized_no", lang)}</span>'


def _pick_popular_route(route_id: str):
    """Callback cho chip 'tuyen pho bien' - chuyen ban do sang che do duyet tuyen do
    va xoa ket qua tim kiem hien tai (neu co) de map khong bi ket qua tim kiem cu
    che mat tuyen vua bam."""
    st.session_state.browse_route_id = route_id
    st.session_state.selected_itineraries = None


def _swap_origin_dest():
    """Callback cho nut doi chieu - phai dung on_click (chay truoc khi widget duoc tao lai),
    khong duoc gan truc tiep session_state[key] sau khi widget key do da instantiate.
    Tang swap_nonce de "remount" ca 2 o searchbox voi gia tri default moi (xem _search_ui)."""
    st.session_state.origin_stop_id, st.session_state.dest_stop_id = (
        st.session_state.get("dest_stop_id"), st.session_state.get("origin_stop_id"))
    st.session_state["swap_nonce"] = st.session_state.get("swap_nonce", 0) + 1


def _run_search(o_id: str, d_id: str, fare_type_value: str):
    """Thuc thi tim tuyen + ghi log + luu ket qua vao session_state - dung chung cho nut
    'Tim tuyen xe buyt' va cac nut goi y diem gan (xem find_nearby_alternatives)."""
    results = finder.find(o_id, d_id, fare_type=fare_type_value, max_results=3)
    ds.log_search(o_id, fmt_stop(o_id, "vi"), d_id, fmt_stop(d_id, "vi"), fare_type_value, len(results))
    st.session_state.selected_itineraries = results
    st.session_state.chosen_itinerary_idx = 0


def _apply_manual_pick(kind: str):
    """Callback cho o chon truc tiep tu danh sach (thay the/bo sung o go tim kiem tu do -
    danh cho nguoi dung chua biet ten tram/dia danh can go gi)."""
    key = "manual_origin_pick" if kind == "origin" else "manual_dest_pick"
    sid = st.session_state.get(key)
    if not sid or sid == MANUAL_SENTINEL:
        return
    if kind == "origin":
        st.session_state.origin_stop_id = sid
    else:
        st.session_state.dest_stop_id = sid
    st.session_state["swap_nonce"] = st.session_state.get("swap_nonce", 0) + 1


def find_nearby_alternatives(origin_id: str, dest_id: str, fare_type_value: str, max_suggestions: int = 4):
    """Khi khong tim duoc duong di truc tiep/1-lan-chuyen giua origin_id va dest_id, thu
    goi y cac tram GAN origin hoac GAN dest ma CO duong di duoc - giup nguoi dung co them
    lua chon thay vi chi thay bao loi 'khong tim thay'. Mo rong dan ban kinh tim kiem (1km
    -> 3km -> 6km) vi mang luoi o vung ngoai thanh/xa trung tam thua tram hon."""
    stops_idx_local = stops_df.set_index("stop_id")
    if origin_id not in stops_idx_local.index or dest_id not in stops_idx_local.index:
        return []
    o_row, d_row = stops_idx_local.loc[origin_id], stops_idx_local.loc[dest_id]
    found, seen_pairs = [], set()
    for radius in (1.0, 3.0, 6.0):
        near_o = nearest_stops(float(o_row["lat"]), float(o_row["lon"]), stops_df, radius_km=radius, limit=6)
        for _, r in near_o[near_o.stop_id != origin_id].iterrows():
            pair = ("origin", r.stop_id)
            if pair in seen_pairs:
                continue
            res = finder.find(r.stop_id, dest_id, fare_type=fare_type_value, max_results=1)
            if res:
                found.append({"kind": "origin", "alt_id": r.stop_id, "dist_km": float(r.distance_km),
                               "itinerary": res[0]})
                seen_pairs.add(pair)
        near_d = nearest_stops(float(d_row["lat"]), float(d_row["lon"]), stops_df, radius_km=radius, limit=6)
        for _, r in near_d[near_d.stop_id != dest_id].iterrows():
            pair = ("dest", r.stop_id)
            if pair in seen_pairs:
                continue
            res = finder.find(origin_id, r.stop_id, fare_type=fare_type_value, max_results=1)
            if res:
                found.append({"kind": "dest", "alt_id": r.stop_id, "dist_km": float(r.distance_km),
                               "itinerary": res[0]})
                seen_pairs.add(pair)
        if found:
            break
    found.sort(key=lambda x: x["dist_km"])
    return found[:max_suggestions]


def _apply_alt_suggestion(kind: str, alt_id: str):
    """Callback cho nut goi y diem gan - ap dung diem thay the roi tim tuyen lai ngay
    (khong bat nguoi dung phai bam Tim tuyen them 1 lan nua)."""
    if kind == "origin":
        st.session_state.origin_stop_id = alt_id
    else:
        st.session_state.dest_stop_id = alt_id
    st.session_state["swap_nonce"] = st.session_state.get("swap_nonce", 0) + 1
    fare_type_value = st.session_state.get("fare_type_radio", "student")
    _run_search(st.session_state.origin_stop_id, st.session_state.dest_stop_id, fare_type_value)


def make_stop_search_fn(stops_scope: pd.DataFrame, lang: str):
    """Tra ve ham search(query) -> List[(nhan_hien_thi, stop_id)] cho st_searchbox.
    Uu tien so khop cuc bo (nhanh, khong phu thuoc mang) tren du lieu tuyen; chi khi
    khong khop gi ca va query đủ dai moi thu geocode qua OpenStreetMap lam phuong an
    du phong cho dia chi thuc te khong trung ten tram (han che goi geocode qua nhieu
    lan khi go nhanh, ton trong chinh sach su dung cua Nominatim)."""

    def _fn(query: str):
        query = (query or "").strip()
        if not query:
            return []
        local = local_search_stops(query, stops_scope, limit=8)
        if not local.empty:
            options = []
            for _, row in local.iterrows():
                name = row["stop_name"] if lang == "vi" else row.get("stop_name_en", row["stop_name"])
                options.append((str(name), str(row["stop_id"])))
            return options
        if len(query) < 6:
            return []
        geo = geocode(query, limit=1)
        if not geo:
            return []
        lat, lon = geo[0]["lat"], geo[0]["lon"]
        nearby = nearest_stops(lat, lon, stops_scope, radius_km=1.2, limit=5)
        options = []
        for _, row in nearby.iterrows():
            name = row["stop_name"] if lang == "vi" else row.get("stop_name_en", row["stop_name"])
            dist_m = int(row["distance_km"] * 1000)
            label = f"{name} ({t('distance_away', lang, d=dist_m)})"
            options.append((label, str(row["stop_id"])))
        return options

    return _fn


# --------------------------------------------------------------------------- #
# Top-level tabs
# --------------------------------------------------------------------------- #
tab_map, tab_stats = st.tabs([
    t("tab_map_search", lang), t("tab_stats", lang),
])

# --------------------------------------------------------------------------- #
# TAB: Bản đồ & Tra cứu
# --------------------------------------------------------------------------- #
with tab_map:
    col_left, col_right = st.columns([1, 1.5])

    map_focus = None  # ("itinerary", Itinerary) hoac ("route", route_id) hoac None

    with col_left:
        st.markdown(f'<div class="hero-title">🚌 {t("hero_title", lang)}</div>'
                    f'<div class="hero-subtitle">{t("hero_subtitle", lang)}</div>', unsafe_allow_html=True)

        # ---- Dai tinh nang chinh - luon hien de nguoi dung thay ngay app lam duoc gi,
        # khong can tim kiem truoc moi thay ----
        st.markdown(f"""
        <div class="feature-strip">
            <span class="feature-chip">🗺️ {t('feature_routes', lang)}</span>
            <span class="feature-chip">🔎 {t('feature_lookup', lang)}</span>
            <span class="feature-chip">🕒 {t('feature_arrival', lang)}</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="search-card">', unsafe_allow_html=True)

        # key doi moi moi khi bam nut doi chieu -> "remount" searchbox voi default moi
        # (xem _swap_origin_dest) vi khong duoc gan truc tiep session_state cua 1 widget
        # sau khi widget do da duoc tao trong cung 1 lan chay.
        nonce = st.session_state.get("swap_nonce", 0)
        origin_default_id = st.session_state.get("origin_stop_id")
        dest_default_id = st.session_state.get("dest_stop_id")
        origin_default_term = fmt_stop(origin_default_id, lang) if origin_default_id else ""
        dest_default_term = fmt_stop(dest_default_id, lang) if dest_default_id else ""

        # Style rieng cho o tim kiem (component ben ngoai, tu render trong iframe rieng nen
        # khong tu ke thua CSS cua trang) - truyen mau theo dark/light de tranh "mang trang"
        # giua giao dien toi.
        sb_box, sb_text, sb_placeholder, sb_border, sb_hover = (
            ("#1e293b", "#f1f5f9", "#94a3b8", "#334155", "#334155") if dark
            else ("#ffffff", "#0f172a", "#94a3b8", "#e2e8f0", "#dbeafe")
        )
        SEARCHBOX_STYLE = {
            "searchbox": {
                "control": {"borderRadius": "10px", "minHeight": "44px", "borderColor": sb_border,
                             "backgroundColor": sb_box},
                "input": {"color": sb_text},
                "placeholder": {"color": sb_placeholder},
                "singleValue": {"color": sb_text},
                "option": {"color": sb_text, "backgroundColor": sb_box, "highlightColor": sb_hover},
                "menuList": {"backgroundColor": sb_box, "borderRadius": "10px"},
            },
        }

        oc1, oc2 = st.columns([5, 1])
        with oc1:
            picked_origin = st_searchbox(
                make_stop_search_fn(stops_df, lang), key=f"origin_sb_{nonce}",
                placeholder=t("search_address_placeholder", lang), label=t("origin", lang),
                default=origin_default_id, default_searchterm=origin_default_term,
                style_overrides=SEARCHBOX_STYLE,
            )
        with oc2:
            st.write("")
            st.write("")
            # Dung on_click callback (chay truoc khi cac widget o duoi duoc tao lai) thay vi
            # gan truc tiep session_state sau khi widget da instantiate trong cung 1 lan chay -
            # gan truc tiep se bao loi "cannot be modified after widget instantiated".
            st.button("🔁", help=t("swap", lang), on_click=_swap_origin_dest)
        picked_dest = st_searchbox(
            make_stop_search_fn(stops_df, lang), key=f"dest_sb_{nonce}",
            placeholder=t("search_address_placeholder", lang), label=t("destination", lang),
            default=dest_default_id, default_searchterm=dest_default_term,
            style_overrides=SEARCHBOX_STYLE,
        )
        st.markdown('</div>', unsafe_allow_html=True)

        if picked_origin:
            st.session_state.origin_stop_id = picked_origin
        if picked_dest:
            st.session_state.dest_stop_id = picked_dest

        # ---- Chon truc tiep tu danh sach - danh cho nguoi dung chua biet ten tram/dia
        # danh can go gi (go tim kiem o tren la 1 lua chon THEM cho ai da biet san) ----
        with st.expander(t("manual_pick_expander", lang), expanded=False):
            stop_label_map = {row.stop_id: (row.stop_name if lang == "vi" else row.stop_name_en)
                               for row in stops_df.itertuples()}
            sorted_stop_ids = sorted(stop_label_map, key=lambda sid: stop_label_map[sid])
            manual_opts = [MANUAL_SENTINEL] + sorted_stop_ids

            def _fmt_manual(sid):
                return "—" if sid == MANUAL_SENTINEL else stop_label_map[sid]

            mc1, mc2 = st.columns(2)
            with mc1:
                st.selectbox(t("origin", lang), options=manual_opts, format_func=_fmt_manual,
                             key="manual_origin_pick", on_change=_apply_manual_pick, args=("origin",))
            with mc2:
                st.selectbox(t("destination", lang), options=manual_opts, format_func=_fmt_manual,
                             key="manual_dest_pick", on_change=_apply_manual_pick, args=("dest",))

        # ---- Tuyen tieu bieu: hien san vai tuyen kem ten day du (khong can go tim kiem) -
        # bam vao la xem ngay tren ban do, phu hop nguoi dung moi chua biet chon diem nao ----
        popular = routes_df.sort_values("route_short_name").head(6)["route_id"].tolist()
        if popular:
            st.caption(t("popular_routes", lang))
            pcols = st.columns(2)
            for i, rid in enumerate(popular):
                row = routes_idx.loc[rid]
                long_name = row["route_long_name"] if lang == "vi" else row["route_long_name_en"]
                label = f"{row['route_short_name']} · {long_name}"
                if len(label) > 30:
                    label = label[:27] + "…"
                pcols[i % 2].button(label, key=f"popchip_{rid}", on_click=_pick_popular_route,
                                     args=(rid,), width="stretch")

        search_clicked = st.button(t("find_route_btn", lang), type="primary", width="stretch")

        if search_clicked:
            o_id = st.session_state.get("origin_stop_id")
            d_id = st.session_state.get("dest_stop_id")

            if o_id and d_id and o_id == d_id:
                st.error(t("same_point_error", lang))
                st.session_state.selected_itineraries = None
            elif not o_id or not d_id:
                st.session_state.selected_itineraries = None
            else:
                _run_search(o_id, d_id, fare_type)

        itineraries = st.session_state.selected_itineraries
        if itineraries is not None:
            if len(itineraries) == 0:
                st.warning(t("no_route_found", lang))
                o_id = st.session_state.get("origin_stop_id")
                d_id = st.session_state.get("dest_stop_id")
                alt_suggestions = find_nearby_alternatives(o_id, d_id, fare_type) if o_id and d_id else []
                if alt_suggestions:
                    st.caption(t("try_nearby", lang))
                    for sug in alt_suggestions:
                        alt_name = fmt_stop(sug["alt_id"], lang)
                        if sug["kind"] == "origin":
                            other_name = fmt_stop(d_id, lang)
                            label = f"🔁 {alt_name} → {other_name}  (~{sug['dist_km']:.1f} km)"
                        else:
                            other_name = fmt_stop(o_id, lang)
                            label = f"🔁 {other_name} → {alt_name}  (~{sug['dist_km']:.1f} km)"
                        st.button(label, key=f"altsug_{sug['kind']}_{sug['alt_id']}",
                                  on_click=_apply_alt_suggestion, args=(sug["kind"], sug["alt_id"]),
                                  width="stretch")
            else:
                st.success(t("found_n_options", lang, n=len(itineraries)))
                chosen_idx_state = st.session_state.get("chosen_itinerary_idx", 0)

                # ---- Bang so sanh nhanh (kieu Citymapper: Fastest / Least walking / ...) ----
                if len(itineraries) > 1:
                    st.caption(t("compare_title", lang))
                    cols = st.columns(len(itineraries))
                    for i, (col, it) in enumerate(zip(cols, itineraries)):
                        tags_html = itinerary_tags(itineraries, i, lang)
                        active_cls = "active" if i == chosen_idx_state else ""
                        col.markdown(f"""
                        <div class="compare-card {active_cls}">
                            <div>{tags_html or '&nbsp;'}</div>
                            <div class="compare-time">{format_minutes(it.total_minutes)}</div>
                            <div class="compare-sub">{itinerary_distance_km(it):.1f} km<br/>
                                {format_vnd(it.total_fare)} · {it.transfers} {t('n_transfers_short', lang)}</div>
                        </div>
                        """, unsafe_allow_html=True)

                labels = [t("option_label", lang, i=i + 1) + f" — {it.summary()}"
                          for i, it in enumerate(itineraries)]
                idx = st.radio(t("choose_option", lang), options=range(len(itineraries)),
                                format_func=lambda i: labels[i], key="chosen_itinerary_idx",
                                horizontal=True)
                chosen = itineraries[idx]
                map_focus = ("itinerary", chosen)

                # ---- The hanh trinh chinh (hero card): so phut la thanh phan TO NHAT ----
                dist_km = itinerary_distance_km(chosen)
                origin_name = chosen.legs[0].board_stop_name if lang == "vi" else chosen.legs[0].board_stop_name_en
                dest_name = (chosen.legs[-1].alight_stop_name if lang == "vi"
                             else chosen.legs[-1].alight_stop_name_en)
                flow_rows = [f'<div class="journey-row">📍 <b>{origin_name}</b></div>']
                for i, leg in enumerate(chosen.legs):
                    n_stops_leg = len(finder.stops_between(leg.route_id, leg.board_stop_id, leg.alight_stop_id)) - 1
                    flow_rows.append(f'<div class="journey-line">│ {format_minutes(leg.ride_minutes)}</div>')
                    flow_rows.append(
                        f'<div class="journey-row">🚌 <b>{leg.route_short_name}</b> · '
                        f'{n_stops_leg} {t("n_stops_short", lang)}</div>')
                    if i < len(chosen.legs) - 1:
                        alight_name = leg.alight_stop_name if lang == "vi" else leg.alight_stop_name_en
                        flow_rows.append(f'<div class="journey-line">│</div>')
                        flow_rows.append(
                            f'<div class="journey-row">🔄 {t("transfer_flow", lang)} <b>{alight_name}</b></div>')
                flow_rows.append(f'<div class="journey-line">│</div>')
                flow_rows.append(f'<div class="journey-row">🎯 <b>{dest_name}</b></div>')

                best_tag_html = itinerary_tags(itineraries, idx, lang)
                st.markdown(f"""
                <div class="hero-card">
                    <div>{best_tag_html}</div>
                    <div class="hero-time">{format_minutes(chosen.total_minutes)}</div>
                    <div class="hero-sub">{dist_km:.1f} km · {format_vnd(chosen.total_fare)} ·
                        {chosen.transfers} {t('n_transfers_short', lang)}</div>
                    <div class="journey-flow">{''.join(flow_rows)}</div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"#### {t('itinerary_detail', lang)}")
                now = datetime.now()
                for i, leg in enumerate(chosen.legs):
                    arrival, msg = estimate_arrival_at_stop(
                        leg.first_departure, leg.last_departure, leg.headway_min,
                        leg.board_offset_min, now=now)
                    active = is_route_active(leg.first_departure, leg.last_departure, now=now)
                    status_html = (f"<span class='bus-badge-active'>{t('route_active', lang)}</span>" if active
                                    else f"<span class='bus-badge-inactive'>{t('route_inactive', lang)}</span>")
                    route_name = leg.route_long_name if lang == "vi" else leg.route_long_name_en
                    board_name = leg.board_stop_name if lang == "vi" else leg.board_stop_name_en
                    alight_name = leg.alight_stop_name if lang == "vi" else leg.alight_stop_name_en
                    arrival_txt = (f"{t('expected_arrival', lang)}: <b>{arrival.strftime('%H:%M')}</b>"
                                   if arrival else msg)
                    leg_km = leg_distance_km(leg.route_id, leg.board_stop_id, leg.alight_stop_id)
                    leg_meta = routes_idx.loc[leg.route_id]
                    subsidized_html = subsidized_badge(leg_meta, lang)
                    st.markdown(f"""
                    <div class="bus-card">
                        <span class="route-number">{leg.route_short_name}</span> {status_html} {subsidized_html}
                        <div class="route-name">{route_name}</div>
                        <div class="metric-row">
                            <span>{t('board_at', lang)}: <b>{board_name}</b></span>
                            <span>{t('alight_at', lang)}: <b>{alight_name}</b></span>
                        </div>
                        <div class="metric-row">
                            <span>{t('ride_time', lang)}: <b>{format_minutes(leg.ride_minutes)}</b></span>
                            <span>{t('distance_km', lang)}: <b>{leg_km:.1f} km</b></span>
                            <span>{t('fare_label', lang)}: <b>{format_vnd(leg.fare)}</b></span>
                            <span>{arrival_txt}</span>
                        </div>
                        <div class="metric-row">
                            <span>{t('operated_by', lang)}: <b>{leg_meta['operator_name'] or '—'}</b></span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if i < len(chosen.legs) - 1:
                        st.caption(f"⇩ {t('transfer_at', lang)} **{alight_name}** ⇩")

        st.divider()
        with st.expander(f"🚍 {t('browse_by_route', lang)}", expanded=False):
            route_opts = [MANUAL_SENTINEL] + routes_df["route_id"].tolist()

            def _route_label(rid):
                if rid == MANUAL_SENTINEL:
                    return "—"
                row = routes_idx.loc[rid]
                active = is_route_active(row["first_departure"], row["last_departure"])
                dot = "🟢" if active else "⚪"
                name = row["route_long_name"] if lang == "vi" else row["route_long_name_en"]
                return f"{dot} {row['route_short_name']} — {name}"

            st.selectbox(t("preview_on_map", lang), options=route_opts, format_func=_route_label,
                         key="browse_route_id")
            browsed_rid = st.session_state.browse_route_id
            if browsed_rid != MANUAL_SENTINEL:
                if map_focus is None:
                    map_focus = ("route", browsed_rid)
                r = routes_idx.loc[browsed_rid]
                r_name = r["route_long_name"] if lang == "vi" else r["route_long_name_en"]
                n_stops = int((route_stops_df.route_id == browsed_rid).sum())
                dist_km = r["distance_km"]
                active = is_route_active(r["first_departure"], r["last_departure"])
                status_html = (f"<span class='bus-badge-active'>{t('route_active', lang)}</span>" if active
                               else f"<span class='bus-badge-inactive'>{t('route_inactive', lang)}</span>")
                st.markdown(f"""
                <div class="bus-card">
                    <span class="route-number">{r['route_short_name']}</span> {status_html} {subsidized_badge(r, lang)}
                    <div class="route-name">{r_name}</div>
                    <div class="metric-row">
                        <span>🚏 {n_stops} {t('n_stops_on_route', lang)}</span>
                        <span>📏 {dist_km:.1f} km</span>
                        <span>🕐 {r['first_departure']}–{r['last_departure']}</span>
                    </div>
                    <div class="metric-row">
                        <span>{t('fare_regular', lang)}: <b>{format_vnd(int(r['fare_regular']))}</b></span>
                        <span>{t('fare_student', lang)}: <b>{format_vnd(int(r['fare_student']))}</b></span>
                        <span>{t('operated_by', lang)}: <b>{r['operator_name'] or '—'}</b></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                with st.expander(t("stop_list", lang)):
                    ordered = finder.ordered_stops(browsed_rid)
                    for s in ordered:
                        nm = s["stop_name"] if lang == "vi" else s["stop_name_en"]
                        st.caption(f"→ {nm}")

    # ----------------------------------------------------------------- #
    # Bản đồ (cột phải)
    # ----------------------------------------------------------------- #
    with col_right:
        if map_focus is None:
            st.info(t("map_empty_hint", lang))
        try:
            import folium
            from streamlit_folium import st_folium

            tile = st.session_state.get("_map_tile")
            tile_attr = st.session_state.get("_map_tile_attr")
            fmap = folium.Map(location=MAP_CENTER, zoom_start=MAP_ZOOM, tiles=tile, attr=tile_attr)

            # CSS hieu ung "pulse" (to nho lien tuc) cho marker diem di/den - ve ngay trong
            # tai lieu HTML cua ban do (giong cach lam voi filter dark mode o duoi).
            pulse_css = """
            <style>
            @keyframes pulse-anim { 0% { transform: scale(1); opacity: 0.7; }
                70% { transform: scale(2.8); opacity: 0; } 100% { transform: scale(2.8); opacity: 0; } }
            .pulse-ring { animation: pulse-anim 1.6s ease-out infinite; }
            </style>
            """
            fmap.get_root().html.add_child(folium.Element(pulse_css))

            if dark:
                # Dao mau CHỈ lop tile (khong dao marker/duong ve cua minh) bang CSS filter
                # ngay trong tai lieu HTML cua ban do - tranh phai dung nguon tile toi rieng
                # (nhu CartoDB dark_matter) vi nguon do hien yeu cau API key.
                fmap.get_root().html.add_child(folium.Element("""
                <style>
                .leaflet-tile-pane { filter: invert(1) hue-rotate(200deg) brightness(0.92) contrast(0.9) saturate(0.85); }
                </style>
                """))

            def _pulse_marker(latlon, color, emoji, tooltip):
                html = f"""
                <div style="position:relative;width:34px;height:34px;">
                  <div class="pulse-ring" style="position:absolute;top:9px;left:9px;width:16px;height:16px;
                       border-radius:50%;background:{color};"></div>
                  <div style="position:absolute;top:9px;left:9px;width:16px;height:16px;border-radius:50%;
                       background:{color};box-shadow:0 0 0 2px #fff, 0 1px 4px rgba(0,0,0,0.45);"></div>
                  <div style="position:absolute;top:-8px;left:8px;font-size:20px;">{emoji}</div>
                </div>
                """
                folium.Marker(latlon, icon=folium.DivIcon(html=html, icon_size=(34, 34), icon_anchor=(17, 26)),
                              tooltip=tooltip).add_to(fmap)

            # KHONG hien tat ca tram cua thanh pho tren ban do nua (qua roi mat khi chua
            # tim gi ca) - ban do chi ve noi dung lien quan truc tiep den thao tac hien
            # tai cua nguoi dung: ket qua tim tuyen, hoac tuyen dang duyet.
            tracked_route_ids = []
            all_bounds = []

            if map_focus and map_focus[0] == "itinerary":
                # Chi hien 2 diem di/den (hieu ung nhap nhay), KHONG ve duong noi - thong
                # tin hanh trinh chi tiet (tung chang, tram chuyen tuyen) da co san o the
                # hero-card va cac the chang ben trai roi, ban do chi can dinh vi 2 dau.
                chosen = map_focus[1]
                stops_idx = stops_df.set_index("stop_id")
                for leg in chosen.legs:
                    tracked_route_ids.append(leg.route_id)
                o_row = stops_idx.loc[chosen.legs[0].board_stop_id]
                d_row = stops_idx.loc[chosen.legs[-1].alight_stop_id]
                o_latlon = (float(o_row["lat"]), float(o_row["lon"]))
                d_latlon = (float(d_row["lat"]), float(d_row["lon"]))
                all_bounds.extend([o_latlon, d_latlon])
                _pulse_marker(o_latlon, "#16a34a", "🚏", t("origin", lang))
                _pulse_marker(d_latlon, "#dc2626", "🏁", t("destination", lang))

            elif map_focus and map_focus[0] == "route":
                # Chi hien 2 chấm diem dau/cuoi tuyen (giong che do ket qua tim tuyen o
                # tren) - KHONG ve duong noi, giu ban do gon gang, de nhin.
                rid = map_focus[1]
                ordered = finder.ordered_stops(rid)
                if ordered:
                    o_latlon = (ordered[0]["lat"], ordered[0]["lon"])
                    d_latlon = (ordered[-1]["lat"], ordered[-1]["lon"])
                    all_bounds.extend([o_latlon, d_latlon])
                    _pulse_marker(o_latlon, "#16a34a", "🚏", t("origin", lang))
                    _pulse_marker(d_latlon, "#dc2626", "🏁", t("destination", lang))
                tracked_route_ids.append(rid)

            # Xe buyt mo phong (chi ve khi bat auto-refresh, tranh hieu lam la GPS luon-bat)
            n_buses_shown = 0
            if st.session_state.live_refresh:
                for rid in tracked_route_ids:
                    row = routes_idx.loc[rid]
                    ordered = finder.ordered_stops(rid)
                    buses = active_buses(rid, str(row["route_short_name"]), str(row["first_departure"]),
                                          str(row["last_departure"]), float(row["headway_min"]), ordered)
                    for bus in buses:
                        folium.map.Marker(
                            location=(bus.lat, bus.lon),
                            icon=folium.DivIcon(html='<div style="font-size:22px;line-height:22px;">🚌</div>'),
                            tooltip=f"{bus.trip_label} • {bus.progress_pct:.0f}% • → {bus.next_stop_name}",
                        ).add_to(fmap)
                        n_buses_shown += 1

            if all_bounds:
                fmap.fit_bounds(all_bounds, padding=(40, 40))

            st_folium(fmap, width=None, height=620, key="main_map", returned_objects=[])

            if tracked_route_ids:
                st.caption(t("live_positions_note", lang))
                if st.session_state.live_refresh:
                    st.caption(f"{t('buses_in_service', lang)}: {n_buses_shown}")
                    if n_buses_shown == 0:
                        st.caption(t("no_bus_running", lang))
        except Exception as map_err:  # khong bao gio hien traceback tho cho nguoi dung cuoi
            st.error(t("map_load_error", lang))
            print(f"[map render error] {map_err}", file=sys.stderr)

# --------------------------------------------------------------------------- #
# TAB: Thống kê
# --------------------------------------------------------------------------- #
with tab_stats:
    st.subheader(t("stats_title", lang))
    hub_stats = (
        route_stops_df.groupby("stop_id")["route_id"].nunique().rename("n").reset_index()
        .merge(stops_df[["stop_id", "stop_name", "stop_name_en"]], on="stop_id")
        .sort_values("n", ascending=False).head(10)
    )
    name_col = "stop_name" if lang == "vi" else "stop_name_en"
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**{t('top_hubs', lang)}**")
        st.dataframe(
            hub_stats.rename(columns={name_col: t("stop_name_col", lang), "n": t("route_count_col", lang)})
            [[t("stop_name_col", lang), t("route_count_col", lang)]],
            hide_index=True, width="stretch",
        )
    with c2:
        st.markdown(f"**{t('route_list', lang)}**")
        long_col = "route_long_name" if lang == "vi" else "route_long_name_en"
        show = routes_df.copy()
        show["🟢"] = show.apply(lambda r: "🟢" if is_route_active(r["first_departure"], r["last_departure"]) else "⚪", axis=1)
        st.dataframe(
            show.rename(columns={"route_short_name": "#", long_col: t("route_list", lang).split(" ")[0],
                                  "fare_regular": t("fare_regular", lang), "fare_student": t("fare_student", lang)})
            [["🟢", "#", t("route_list", lang).split(" ")[0], t("fare_regular", lang), t("fare_student", lang)]],
            hide_index=True, width="stretch",
        )

    st.divider()
    st.subheader(t("search_log_title", lang))
    if ds.mode != "cloud":
        st.info(t("search_log_need_cloud", lang))
    else:
        logs = ds.get_search_stats()
        if logs.empty:
            st.info(t("no_logs_yet", lang))
        else:
            l1, l2 = st.columns(2)
            l1.metric(t("total_searches", lang), len(logs))
            l2.metric(t("n_od_pairs", lang), logs.groupby(["origin_stop_name", "dest_stop_name"]).ngroups)
            top_od = (logs.groupby(["origin_stop_name", "dest_stop_name"]).size()
                      .rename("n").reset_index().sort_values("n", ascending=False).head(5))
            st.markdown(f"**{t('top5_searched', lang)}**")
            st.dataframe(
                top_od.rename(columns={"origin_stop_name": t("origin_col", lang),
                                        "dest_stop_name": t("dest_col", lang), "n": t("search_count_col", lang)}),
                hide_index=True, width="stretch",
            )
            st.markdown(f"**{t('recent_searches', lang)}**")
            st.dataframe(
                logs[["searched_at", "origin_stop_name", "dest_stop_name", "fare_type", "n_results"]].head(20),
                hide_index=True, width="stretch",
            )

