# -*- coding: utf-8 -*-
"""
Smart City Bus Assistant
Cổng tra cứu tuyến & theo dõi xe buýt đô thị (TP.HCM + Biên Hòa - Đồng Nai) trên bản đồ.
Đồ án học phần Ứng dụng Điện toán đám mây.

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

LEG_COLORS = ["#2563eb", "#dc2626", "#16a34a", "#d97706"]
CITY_COLORS = {"hcmc": "#2563eb", "bienhoa": "#7c3aed", "kiengiang": "#16a34a"}
CITY_IDS = ("all", "hcmc", "bienhoa", "kiengiang")
CITY_ICON = {"all": "🌐", "hcmc": "🏙️", "bienhoa": "🏘️", "kiengiang": "🌾"}
MANUAL_SENTINEL = "__none__"

# --------------------------------------------------------------------------- #
# Session state defaults
# --------------------------------------------------------------------------- #
for key, default in {
    "lang": "vi", "dark_mode": False, "city_filter": "all",
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


# --------------------------------------------------------------------------- #
# Theme (CSS) injection
# --------------------------------------------------------------------------- #
def inject_theme_css(dark: bool):
    # Ban do dung tile OpenStreetMap chuan (mau sac day du: song ngoi, duong, nhan dia
    # danh...) thay vi tile xam don dieu - mien phi, khong can API key. Voi giao dien
    # toi, KHONG doi nguon tile (CartoDB dark can key) ma inject CSS filter dao mau
    # ngay trong HTML cua ban do (xem render_dark_map_css) - giu nguyen chi tiet ban do.
    tile = "OpenStreetMap"
    st.session_state["_map_tile"] = tile
    st.session_state["_map_tile_attr"] = None
    if dark:
        bg, bg2, text, subtext, card, border, accent = (
            "#0f172a", "#1e293b", "#f1f5f9", "#94a3b8", "#1e293b", "#334155", "#38bdf8")
    else:
        bg, bg2, text, subtext, card, border, accent = (
            "#ffffff", "#f8fafc", "#0f172a", "#64748b", "#ffffff", "#e2e8f0", "#2563eb")
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}

    .stApp {{ background-color: {bg}; }}
    [data-testid="stSidebar"] {{ background-color: {bg2}; }}
    [data-testid="stMarkdownContainer"] {{ color: {text}; }}
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {{ color: {text}; }}
    [data-testid="stCaptionContainer"] {{ color: {subtext}; }}

    /* ---- Hero / search card ---- */
    .hero-title {{ font-size: 28px; font-weight: 700; color: {text}; margin-bottom: 2px; }}
    .hero-subtitle {{ font-size: 15px; color: {subtext}; margin-bottom: 20px; }}
    .search-card {{
        background-color: {card}; border: 1px solid {border}; border-radius: 16px;
        padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }}

    /* ---- Route / itinerary cards ---- */
    .bus-card {{
        background-color: {card}; border: 1px solid {border}; border-radius: 12px;
        padding: 16px; margin-bottom: 10px; color: {text};
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}
    .route-number {{
        display: inline-block; background: {accent}; color: white; font-weight: 700;
        font-size: 14px; padding: 4px 10px; border-radius: 8px; letter-spacing: 0.3px;
    }}
    .route-name {{ font-size: 15px; font-weight: 500; color: {text}; margin-top: 6px; }}
    .metric-row {{ display: flex; gap: 18px; margin-top: 10px; font-size: 13.5px; color: {subtext}; flex-wrap: wrap; }}
    .metric-row b {{ color: {text}; }}
    .tag-pill {{
        display: inline-block; font-size: 11.5px; font-weight: 600; padding: 3px 9px;
        border-radius: 999px; margin-right: 6px; margin-bottom: 6px;
    }}
    .tag-best {{ background: #dbeafe; color: #1d4ed8; }}
    .tag-fast {{ background: #dcfce7; color: #15803d; }}
    .tag-cheap {{ background: #fef9c3; color: #a16207; }}
    .tag-fewtransfer {{ background: #f3e8ff; color: #7e22ce; }}

    .bus-badge-active {{ color: #16a34a; font-weight: 600; font-size: 12.5px; }}
    .bus-badge-inactive {{ color: #94a3b8; font-weight: 600; font-size: 12.5px; }}

    .cloud-status-mini {{ font-size: 12px; color: {subtext}; }}

    .stButton>button[kind="primary"] {{
        background-color: {accent}; border-color: {accent}; border-radius: 10px;
        height: 48px; font-weight: 600; font-size: 14.5px;
    }}
    div[data-testid="stTextInput"] input {{ border-radius: 10px; min-height: 44px; }}

    /* ---- Bo chon khu vuc (segmented control) - dang pill be tron, gan gui hon ---- */
    div[data-testid="stSegmentedControl"] label {{
        border-radius: 999px !important; font-weight: 500;
    }}
    div[data-testid="stSegmentedControl"] label[data-checked="true"] {{
        background-color: {accent} !important; border-color: {accent} !important;
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
    # Phong thu: bat ke nguyen nhan gi khien gia tri luu khong hop le, luon fallback ve "all"
    # thay vi de KeyError lam sap ung dung (khong bao gio hien traceback cho nguoi dung cuoi).
    # (Widget chon khu vuc THAT nam o dau trang chinh - gan phan tim kiem - de de thay hon,
    # xem CITY_LABEL/CITY_ICON o duoi; muc nay chi dam bao gia tri luon hop le.)
    if st.session_state.get("city_filter") not in CITY_IDS:
        st.session_state["city_filter"] = "all"
    city_filter = st.session_state["city_filter"]

    fare_type = st.radio(t("fare_type", lang), options=list(FARE_TYPES.keys()),
                          format_func=lambda k: t(f"fare_{k}", lang), key="fare_type_radio")

    st.divider()
    routes_view = routes_df if city_filter == "all" else routes_df[routes_df.city_id == city_filter]
    stops_view = stops_df if city_filter == "all" else stops_df[stops_df.city_id == city_filter]
    m1, m2 = st.columns(2)
    m1.metric(t("n_routes", lang), len(routes_view))
    m2.metric(t("n_stops", lang), len(stops_view))

    st.toggle(t("auto_refresh_on", lang), key="live_refresh")

    st.divider()
    st.caption(t("cloud_status_footer", lang))
    if ds.mode == "cloud":
        st.markdown(f'<span class="cloud-status-mini">🟢 {t("cloud_connected", lang)}</span>', unsafe_allow_html=True)
    else:
        st.markdown(f'<span class="cloud-status-mini">🟡 {t("cloud_local", lang)}</span>', unsafe_allow_html=True)
    with st.expander(t("why_no_cloud", lang) if ds.mode != "cloud" else t("cloud_status_footer", lang)):
        st.write(t("why_no_cloud_body", lang))
        if ds.connect_error:
            st.code(ds.connect_error, language="text")
        if st.button(t("refresh_cloud", lang)):
            get_datastore.clear()
            load_data.clear()
            build_finder.clear()
            st.rerun()

if st.session_state["live_refresh"]:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=8000, key="live_map_autorefresh")


def fmt_stop(stop_id: str, lang: str) -> str:
    return finder.stop_name(stop_id, lang) if stop_id and stop_id != MANUAL_SENTINEL else stop_id


def route_distance_km(route_id: str) -> float:
    """Tong khoang cach uoc tinh cua 1 tuyen (tong haversine giua cac tram lien tiep)."""
    from backend.geocoding import haversine_km
    ordered = finder.ordered_stops(route_id)
    total = 0.0
    for a, b in zip(ordered, ordered[1:]):
        total += haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
    return total


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


def _swap_origin_dest():
    """Callback cho nut doi chieu - phai dung on_click (chay truoc khi widget duoc tao lai),
    khong duoc gan truc tiep session_state[key] sau khi widget key do da instantiate.
    Tang swap_nonce de "remount" ca 2 o searchbox voi gia tri default moi (xem _search_ui)."""
    st.session_state.origin_stop_id, st.session_state.dest_stop_id = (
        st.session_state.get("dest_stop_id"), st.session_state.get("origin_stop_id"))
    st.session_state["swap_nonce"] = st.session_state.get("swap_nonce", 0) + 1


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
tab_map, tab_stats, tab_about = st.tabs([
    t("tab_map_search", lang), t("tab_stats", lang), t("tab_about", lang),
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

        city_labels = {"all": t("city_all", lang), "hcmc": t("city_hcmc", lang),
                       "bienhoa": t("city_bienhoa", lang), "kiengiang": t("city_kiengiang", lang)}
        st.segmented_control(
            t("city", lang), options=list(CITY_IDS), required=True,
            format_func=lambda x: f"{CITY_ICON.get(x, '')} {city_labels.get(x, x)}",
            key="city_filter", label_visibility="collapsed",
        )
        if st.session_state.get("city_filter") not in CITY_IDS:
            st.session_state["city_filter"] = "all"
        city_filter = st.session_state["city_filter"]
        routes_view = routes_df if city_filter == "all" else routes_df[routes_df.city_id == city_filter]
        stops_view = stops_df if city_filter == "all" else stops_df[stops_df.city_id == city_filter]

        st.markdown('<div class="search-card">', unsafe_allow_html=True)

        # key doi moi moi khi bam nut doi chieu -> "remount" searchbox voi default moi
        # (xem _swap_origin_dest) vi khong duoc gan truc tiep session_state cua 1 widget
        # sau khi widget do da duoc tao trong cung 1 lan chay.
        nonce = st.session_state.get("swap_nonce", 0)
        origin_default_id = st.session_state.get("origin_stop_id")
        dest_default_id = st.session_state.get("dest_stop_id")
        origin_default_term = fmt_stop(origin_default_id, lang) if origin_default_id else ""
        dest_default_term = fmt_stop(dest_default_id, lang) if dest_default_id else ""

        # Style rieng cho o tim kiem (component ben ngoai, khong tu doi theo dark mode cua
        # trang) - giu luon sang/de doc, be tron, mau xanh dong bo voi thuong hieu app.
        SEARCHBOX_STYLE = {
            "searchbox": {
                "control": {"borderRadius": "10px", "minHeight": "44px", "borderColor": "#e2e8f0"},
                "input": {"color": "#0f172a"},
                "placeholder": {"color": "#94a3b8"},
                "singleValue": {"color": "#0f172a"},
                "option": {"color": "#0f172a", "backgroundColor": "#ffffff", "highlightColor": "#dbeafe"},
                "menuList": {"backgroundColor": "#ffffff", "borderRadius": "10px"},
            },
        }

        oc1, oc2 = st.columns([5, 1])
        with oc1:
            picked_origin = st_searchbox(
                make_stop_search_fn(stops_view, lang), key=f"origin_sb_{nonce}",
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
            make_stop_search_fn(stops_view, lang), key=f"dest_sb_{nonce}",
            placeholder=t("search_address_placeholder", lang), label=t("destination", lang),
            default=dest_default_id, default_searchterm=dest_default_term,
            style_overrides=SEARCHBOX_STYLE,
        )
        st.markdown('</div>', unsafe_allow_html=True)

        if picked_origin:
            st.session_state.origin_stop_id = picked_origin
        if picked_dest:
            st.session_state.dest_stop_id = picked_dest

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
                results = finder.find(o_id, d_id, fare_type=fare_type, max_results=3)
                ds.log_search(o_id, fmt_stop(o_id, "vi"), d_id, fmt_stop(d_id, "vi"), fare_type, len(results))
                st.session_state.selected_itineraries = results
                st.session_state.chosen_itinerary_idx = 0

        itineraries = st.session_state.selected_itineraries
        if itineraries is not None:
            if len(itineraries) == 0:
                st.warning(t("no_route_found", lang))
            else:
                st.success(t("found_n_options", lang, n=len(itineraries)))
                labels = [
                    f"{t('option_label', lang, i=i + 1)}: {it.summary()} • {format_minutes(it.total_minutes)} • "
                    f"{format_vnd(it.total_fare)} • {it.transfers} {t('n_transfers', lang).lower()}"
                    for i, it in enumerate(itineraries)
                ]
                idx = st.radio(t("choose_option", lang), options=range(len(itineraries)),
                                format_func=lambda i: labels[i], key="chosen_itinerary_idx")
                chosen = itineraries[idx]
                map_focus = ("itinerary", chosen)

                tags_html = itinerary_tags(itineraries, idx, lang)
                if tags_html:
                    st.markdown(tags_html, unsafe_allow_html=True)

                m1, m2, m3 = st.columns(3)
                m1.metric(t("total_time", lang), format_minutes(chosen.total_minutes))
                m2.metric(t("total_fare", lang), format_vnd(chosen.total_fare))
                m3.metric(t("n_transfers", lang), chosen.transfers)

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
                    st.markdown(f"""
                    <div class="bus-card">
                        <span class="route-number">{leg.route_short_name}</span> {status_html}
                        <div class="route-name">{route_name}</div>
                        <div class="metric-row">
                            <span>{t('board_at', lang)}: <b>{board_name}</b></span>
                            <span>{t('alight_at', lang)}: <b>{alight_name}</b></span>
                        </div>
                        <div class="metric-row">
                            <span>{t('ride_time', lang)}: <b>{format_minutes(leg.ride_minutes)}</b></span>
                            <span>{t('fare_label', lang)}: <b>{format_vnd(leg.fare)}</b></span>
                            <span>{arrival_txt}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if i < len(chosen.legs) - 1:
                        st.caption(f"⇩ {t('transfer_at', lang)} **{alight_name}** ⇩")

        st.divider()
        st.markdown(f"#### {t('browse_by_route', lang)}")
        route_opts = [MANUAL_SENTINEL] + routes_view["route_id"].tolist()

        def _route_label(rid):
            if rid == MANUAL_SENTINEL:
                return "—"
            row = routes_view[routes_view.route_id == rid].iloc[0]
            active = is_route_active(row["first_departure"], row["last_departure"])
            dot = "🟢" if active else "⚪"
            name = row["route_long_name"] if lang == "vi" else row["route_long_name_en"]
            return f"{dot} {row['route_short_name']} — {name}"

        st.selectbox(t("preview_on_map", lang), options=route_opts, format_func=_route_label, key="browse_route_id")
        browsed_rid = st.session_state.browse_route_id
        if browsed_rid != MANUAL_SENTINEL:
            if map_focus is None:
                map_focus = ("route", browsed_rid)
            r = routes_view[routes_view.route_id == browsed_rid].iloc[0]
            r_name = r["route_long_name"] if lang == "vi" else r["route_long_name_en"]
            n_stops = int((route_stops_df.route_id == browsed_rid).sum())
            dist_km = route_distance_km(browsed_rid)
            active = is_route_active(r["first_departure"], r["last_departure"])
            status_html = (f"<span class='bus-badge-active'>{t('route_active', lang)}</span>" if active
                           else f"<span class='bus-badge-inactive'>{t('route_inactive', lang)}</span>")
            st.markdown(f"""
            <div class="bus-card">
                <span class="route-number">{r['route_short_name']}</span> {status_html}
                <div class="route-name">{r_name}</div>
                <div class="metric-row">
                    <span>🚏 {n_stops} {t('n_stops_on_route', lang)}</span>
                    <span>📏 {dist_km:.1f} km</span>
                    <span>🕐 {r['first_departure']}–{r['last_departure']}</span>
                </div>
                <div class="metric-row">
                    <span>{t('fare_regular', lang)}: <b>{format_vnd(int(r['fare_regular']))}</b></span>
                    <span>{t('fare_student', lang)}: <b>{format_vnd(int(r['fare_student']))}</b></span>
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
        try:
            import folium
            from streamlit_folium import st_folium

            tile = st.session_state.get("_map_tile", "OpenStreetMap")
            centers = {"hcmc": (10.78, 106.70), "bienhoa": (10.95, 106.83),
                       "kiengiang": (10.02, 105.08), "all": (10.2, 105.5)}
            zoom = 12 if city_filter != "all" else 8
            fmap = folium.Map(location=centers.get(city_filter, centers["all"]), zoom_start=zoom, tiles=tile)

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
                # Chi hien 2 diem di/den (hieu ung nhap nhay), KHONG ve duong noi/mui ten -
                # thong tin hanh trinh chi tiet da co o cac the ben trai roi.
                chosen = map_focus[1]
                for leg in chosen.legs:
                    tracked_route_ids.append(leg.route_id)
                stops_idx = stops_df.set_index("stop_id")
                o_row = stops_idx.loc[chosen.legs[0].board_stop_id]
                d_row = stops_idx.loc[chosen.legs[-1].alight_stop_id]
                o_latlon = (float(o_row["lat"]), float(o_row["lon"]))
                d_latlon = (float(d_row["lat"]), float(d_row["lon"]))
                all_bounds.extend([o_latlon, d_latlon])
                _pulse_marker(o_latlon, "#16a34a", "🚏", t("origin", lang))
                _pulse_marker(d_latlon, "#dc2626", "🏁", t("destination", lang))

            elif map_focus and map_focus[0] == "route":
                rid = map_focus[1]
                ordered = finder.ordered_stops(rid)
                latlons = [(s["lat"], s["lon"]) for s in ordered]
                all_bounds.extend(latlons)
                row = routes_view[routes_view.route_id == rid].iloc[0]
                folium.PolyLine(latlons, color=LEG_COLORS[0], weight=6, opacity=0.9,
                                 tooltip=str(row["route_short_name"])).add_to(fmap)
                tracked_route_ids.append(rid)

            # Xe buyt mo phong (chi ve khi bat auto-refresh, tranh hieu lam la GPS luon-bat)
            n_buses_shown = 0
            if st.session_state.live_refresh:
                for rid in tracked_route_ids:
                    row = routes_df[routes_df.route_id == rid].iloc[0]
                    ordered = finder.ordered_stops(rid)
                    buses = active_buses(rid, str(row["route_short_name"]), str(row["first_departure"]),
                                          str(row["last_departure"]), int(row["headway_min"]), ordered)
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

# --------------------------------------------------------------------------- #
# TAB: Giới thiệu
# --------------------------------------------------------------------------- #
with tab_about:
    if lang == "vi":
        st.markdown("""
### Vấn đề thực tế
Sinh viên và người không có xe cá nhân phụ thuộc vào xe buýt nhưng gặp khó khăn khi
tra cứu thời gian xe đến trạm, các điểm trung chuyển, hoặc tính toán chi phí di chuyển
tiết kiệm nhất giữa nhiều tuyến — đặc biệt khi không nhớ chính xác tên trạm mà chỉ biết
địa chỉ/địa danh gần đó.

**Đối tượng:** sinh viên, người cao tuổi, người đi làm bằng phương tiện công cộng tại
TP. Hồ Chí Minh và Biên Hòa - Đồng Nai.

### Giải pháp
Nhập địa chỉ/địa danh (hoặc chọn trạm trực tiếp) cho điểm đi - điểm đến, hệ thống tự
động gợi ý tuyến tối ưu (trực tiếp hoặc 1 lần chuyển tuyến), hiển thị trực quan trên
bản đồ kèm mô phỏng vị trí xe đang chạy, ước tính giờ đến và chi phí vé.

### Kiến trúc Cloud
```
USER -> Streamlit Web App (Cloud Hosting) -> Supabase PostgreSQL (Cloud Database)
                                            -> Supabase PostgREST (Cloud API)
                                            -> Supabase Storage (Cloud Storage - backup dataset)
```

### Vì sao vị trí xe là "mô phỏng" chứ không phải GPS thật?
Hiện **không có API GPS thời gian thực công khai/miễn phí** cho xe buýt tại Việt Nam —
BusMap và Buýt Đồng Nai là hệ thống nội bộ, không mở dữ liệu vị trí xe cho bên thứ ba,
và việc trích xuất dữ liệu riêng của họ vi phạm điều khoản dịch vụ nên nhóm không thực
hiện. Thay vào đó, ứng dụng **tính toán vị trí ước tính** của từng chuyến xe dựa trên
giờ khởi hành chuẩn + giãn cách chạy + thời gian đã trôi qua, nội suy theo lộ trình —
minh hoạ trực quan tương tự Grab/Be nhưng luôn được ghi rõ là ước tính, không phải GPS
thật (xem `backend/tracking.py`).

### Nguồn dữ liệu & giới hạn
Bộ dữ liệu (`dataset/`) biên soạn thủ công theo cấu trúc chuẩn GTFS, dựa trên địa danh
có thật tại TP.HCM và Biên Hòa; toạ độ trạm trung gian được nội suy tuyến tính để minh
hoạ, không phải dữ liệu GTFS chính thức. Tìm kiếm theo địa chỉ tự do dùng OpenStreetMap
Nominatim (miễn phí, không cần API key) làm phương án bổ sung khi tên không khớp trực
tiếp dữ liệu tuyến.
        """)
    else:
        st.markdown("""
### The problem
Students and people without a personal vehicle rely on buses but struggle to check
arrival times, find transfer points, or work out the cheapest route across multiple
lines — especially when they only know a nearby address, not the exact stop name.

**Target users:** students, elderly people, and commuters using public transport in
Ho Chi Minh City and Bien Hoa - Dong Nai.

### The solution
Enter an address/place name (or pick a stop directly) for origin and destination; the
system suggests the optimal route (direct or 1 transfer), visualizes it on a map with
simulated live bus positions, and estimates arrival time and fare.

### Cloud architecture
```
USER -> Streamlit Web App (Cloud Hosting) -> Supabase PostgreSQL (Cloud Database)
                                            -> Supabase PostgREST (Cloud API)
                                            -> Supabase Storage (Cloud Storage - dataset backup)
```

### Why are bus positions "simulated" instead of real GPS?
There is currently **no free public real-time GPS API** for buses in Vietnam — BusMap
and Buyt Dong Nai are closed internal systems that do not expose vehicle-position data
to third parties, and scraping their private data would violate their terms of service,
so the team did not do that. Instead, the app **computes an estimated position** for
each trip from the standard departure time + headway + elapsed time, interpolated along
the route — a Grab/Be-style visualization that is always clearly labeled as an estimate,
not real GPS (see `backend/tracking.py`).

### Data source & limitations
The dataset (`dataset/`) is manually authored following the GTFS structure, based on
real places in Ho Chi Minh City and Bien Hoa; intermediate stop coordinates are linearly
interpolated for illustration, not an official GTFS feed. Free-text address search uses
OpenStreetMap Nominatim (free, no API key) as a fallback when the query doesn't match a
stop name directly.
        """)
