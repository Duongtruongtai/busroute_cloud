"""Cac hang so va ham tien ich lien quan den ve xe buyt."""

FARE_TYPES = {
    "student": "Ve sinh vien / hoc sinh",
    "regular": "Ve pho thong",
}


def format_vnd(amount: int) -> str:
    return f"{amount:,.0f}".replace(",", ".") + " d"


def format_minutes(minutes: float) -> str:
    m = round(minutes)
    if m < 60:
        return f"{m} phut"
    h, rem = divmod(m, 60)
    return f"{h} gio {rem} phut" if rem else f"{h} gio"
