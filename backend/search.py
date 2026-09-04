# -*- coding: utf-8 -*-
"""
Tìm kiếm trạm cục bộ (local search) theo tên/địa danh - không phụ thuộc mạng.

Đây là phương án tìm kiếm CHÍNH (nhanh, luôn hoạt động kể cả khi demo offline
hoặc dịch vụ geocoding bên ngoài bị chậm/lỗi), so khớp không phân biệt dấu
tiếng Việt và không phân biệt hoa/thường. Geocoding qua OpenStreetMap
(`backend/geocoding.py`) là phương án BỔ SUNG cho địa chỉ tự do không có
trong dữ liệu tuyến.
"""
import re
import unicodedata

import pandas as pd

_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)


def normalize_vi(text: str) -> str:
    """Bo dau tieng Viet + dau cau + ha chu thuong, dung de so khop khong phan biet dau/dau cau."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFD", text)
    no_marks = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    no_marks = no_marks.replace("đ", "d").replace("Đ", "D").lower().strip()
    no_punct = _PUNCT_RE.sub(" ", no_marks)
    return re.sub(r"\s+", " ", no_punct).strip()


def local_search_stops(query: str, stops_df: pd.DataFrame, limit: int = 8) -> pd.DataFrame:
    """Tim cac tram co ten (VI hoac EN) khop voi query (khong phan biet dau/hoa-thuong).

    Uu tien tram khop TAT CA cac tu trong query (chinh xac nhat); neu khong co tram
    nao khop het (vd nguoi dung go them tu thua nhu "trạm", "bến" khong co trong ten
    that), rot xuong khop CANG NHIEU TU CANG TOT - tranh tra ve rong khien nguoi dung
    tuong lam la khong co goi y nao ca."""
    if not query or not query.strip():
        return stops_df.iloc[0:0]

    tokens = [tk for tk in normalize_vi(query).split() if tk]
    if not tokens:
        return stops_df.iloc[0:0]

    df = stops_df.copy()
    df["_haystack"] = df.apply(
        lambda row: normalize_vi(f"{row['stop_name']} {row.get('stop_name_en', '')}"), axis=1)
    df["_n_match"] = df["_haystack"].apply(lambda h: sum(1 for tok in tokens if tok in h))
    df["_first_pos"] = df["_haystack"].apply(lambda h: h.find(tokens[0]))

    matched = df[df["_n_match"] > 0].copy()
    if matched.empty:
        return stops_df.iloc[0:0]
    # uu tien: khop nhieu tu nhat, roi den khop gan dau ten hon (vd go dung ten truong/tuyen)
    matched = matched.sort_values(["_n_match", "_first_pos"], ascending=[False, True])
    return matched.head(limit).drop(columns=["_haystack", "_n_match", "_first_pos"])
