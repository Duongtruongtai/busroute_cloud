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
    """Tim cac tram co ten (VI hoac EN) chua tat ca cac tu trong query (khong phan biet dau/hoa-thuong)."""
    if not query or not query.strip():
        return stops_df.iloc[0:0]

    tokens = [t for t in normalize_vi(query).split() if t]
    if not tokens:
        return stops_df.iloc[0:0]

    def score(row) -> int:
        haystack = normalize_vi(f"{row['stop_name']} {row.get('stop_name_en', '')}")
        if all(tok in haystack for tok in tokens):
            # uu tien tram co ten khop gan dung tu dau (vd go dung ten truong/tuyen)
            return len(haystack) - haystack.find(tokens[0])
        return -1

    df = stops_df.copy()
    df["_score"] = df.apply(score, axis=1)
    matched = df[df["_score"] >= 0].sort_values("_score", ascending=False)
    return matched.head(limit).drop(columns="_score")
