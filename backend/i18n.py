# -*- coding: utf-8 -*-
"""Đa ngôn ngữ (Việt / English) cho giao diện."""

STRINGS = {
    "app_title": {"vi": "Smart City Bus Assistant", "en": "Smart City Bus Assistant"},
    "app_subtitle": {
        "vi": "Tra cứu tuyến & theo dõi xe buýt trên bản đồ",
        "en": "Route lookup & live bus tracking on the map",
    },
    "cloud_connected": {"vi": "Đang kết nối Cloud Database (Supabase)", "en": "Connected to Cloud Database (Supabase)"},
    "cloud_local": {"vi": "Đang dùng dữ liệu cục bộ (chưa cấu hình Supabase)", "en": "Using local data (Supabase not configured)"},
    "why_no_cloud": {"vi": "Vì sao chưa kết nối Cloud Database?", "en": "Why isn't Cloud Database connected?"},
    "why_no_cloud_body": {
        "vi": "Ứng dụng tự động chuyển sang Supabase khi biến `SUPABASE_URL` và `SUPABASE_KEY` "
              "được cấu hình trong `.streamlit/secrets.toml` (local) hoặc mục Secrets của Streamlit Cloud.",
        "en": "The app automatically switches to Supabase once `SUPABASE_URL` and `SUPABASE_KEY` are "
              "configured in `.streamlit/secrets.toml` (local) or the Streamlit Cloud Secrets panel.",
    },
    "language": {"vi": "Ngôn ngữ", "en": "Language"},
    "theme": {"vi": "Giao diện", "en": "Theme"},
    "theme_dark": {"vi": "🌙 Tối", "en": "🌙 Dark"},
    "theme_light": {"vi": "☀️ Sáng", "en": "☀️ Light"},
    "fare_type": {"vi": "Loại vé", "en": "Fare type"},
    "fare_student": {"vi": "Vé sinh viên / học sinh", "en": "Student fare"},
    "fare_regular": {"vi": "Vé phổ thông", "en": "Regular fare"},
    "city": {"vi": "Thành phố", "en": "City"},
    "city_all": {"vi": "Tất cả", "en": "All"},
    "city_hcmc": {"vi": "TP. Hồ Chí Minh", "en": "Ho Chi Minh City"},
    "city_bienhoa": {"vi": "Biên Hòa - Đồng Nai", "en": "Bien Hoa - Dong Nai"},
    "city_kiengiang": {"vi": "Kiên Giang", "en": "Kien Giang"},
    "n_routes": {"vi": "Số tuyến đang khai thác", "en": "Active routes"},
    "n_stops": {"vi": "Số trạm dừng", "en": "Bus stops"},
    "refresh_cloud": {"vi": "🔄 Làm mới dữ liệu từ Cloud", "en": "🔄 Refresh data from Cloud"},
    "tab_map_search": {"vi": "🗺️ Bản đồ & Tra cứu", "en": "🗺️ Map & Route lookup"},
    "tab_stats": {"vi": "📊 Thống kê", "en": "📊 Statistics"},
    "tab_about": {"vi": "ℹ️ Giới thiệu", "en": "ℹ️ About"},
    "browse_by_route": {"vi": "📋 Duyệt theo tuyến", "en": "📋 Browse by route"},
    "preview_on_map": {"vi": "Xem trên bản đồ", "en": "Preview on map"},
    "resolved_as": {"vi": "→ Xác định là", "en": "→ Resolved as"},
    "no_match_local": {
        "vi": "Không khớp trạm nào trong dữ liệu. Đang thử định vị bằng bản đồ (OpenStreetMap)...",
        "en": "No matching stop in the dataset. Trying to geocode via OpenStreetMap...",
    },
    "manual_pick_expander": {"vi": "Hoặc chọn trực tiếp trạm từ danh sách", "en": "Or pick a stop directly from the list"},
    "clear_results": {"vi": "Xoá kết quả", "en": "Clear results"},
    "distance_away": {"vi": "cách {d} m", "en": "{d} m away"},
    "hero_title": {"vi": "Tìm đường bằng xe buýt", "en": "Find your bus route"},
    "hero_subtitle": {
        "vi": "Nhập điểm đi và điểm đến — chúng tôi tìm tuyến tối ưu cho bạn",
        "en": "Enter your origin and destination — we'll find the best route",
    },
    "map_load_error": {
        "vi": "⚠️ Không thể tải bản đồ cho lựa chọn hiện tại. Vui lòng thử lại hoặc chọn thành phố khác.",
        "en": "⚠️ Couldn't load the map for the current selection. Please try again or pick another city.",
    },
    "tag_best": {"vi": "✨ Phù hợp nhất", "en": "✨ Best match"},
    "tag_fastest": {"vi": "⚡ Nhanh nhất", "en": "⚡ Fastest"},
    "tag_cheapest": {"vi": "💰 Rẻ nhất", "en": "💰 Cheapest"},
    "tag_fewest_transfers": {"vi": "🔁 Ít chuyển tuyến nhất", "en": "🔁 Fewest transfers"},
    "n_stops_on_route": {"vi": "trạm", "en": "stops"},
    "distance_km": {"vi": "Khoảng cách", "en": "Distance"},
    "operating_hours": {"vi": "Giờ hoạt động", "en": "Operating hours"},
    "route_info": {"vi": "Thông tin tuyến", "en": "Route info"},
    "stop_list": {"vi": "Danh sách trạm trên tuyến", "en": "Stops on this route"},
    "cloud_status_footer": {"vi": "Trạng thái hệ thống", "en": "System status"},
    "search_by_address": {"vi": "Tìm theo địa chỉ / địa điểm", "en": "Search by address / place"},
    "search_address_placeholder": {
        "vi": "vd: Trường Nguyễn Tri Phương, đường Nguyễn Ái Quốc",
        "en": "e.g. Nguyen Tri Phuong School, Nguyen Ai Quoc street",
    },
    "or_pick_stop": {"vi": "hoặc chọn trực tiếp trạm", "en": "or pick a stop directly"},
    "origin": {"vi": "📍 Điểm đi", "en": "📍 Origin"},
    "destination": {"vi": "🏁 Điểm đến", "en": "🏁 Destination"},
    "swap": {"vi": "Đổi chiều điểm đi / điểm đến", "en": "Swap origin / destination"},
    "find_route_btn": {"vi": "🔍 Tìm tuyến xe buýt", "en": "🔍 Find bus route"},
    "geocode_searching": {"vi": "Đang định vị địa chỉ...", "en": "Looking up address..."},
    "geocode_not_found": {
        "vi": "Không định vị được địa chỉ này. Hãy thử mô tả cụ thể hơn hoặc chọn trạm trực tiếp bên dưới.",
        "en": "Couldn't locate this address. Try a more specific description or pick a stop directly below.",
    },
    "geocode_found_stops": {
        "vi": "Đã định vị địa chỉ. Các trạm gần nhất:",
        "en": "Address located. Nearest stops:",
    },
    "no_nearby_stop": {
        "vi": "Không có trạm xe buýt nào trong bán kính {radius} m quanh địa chỉ này.",
        "en": "No bus stop found within {radius} m of this address.",
    },
    "same_point_error": {
        "vi": "Điểm đi và điểm đến đang trùng nhau. Vui lòng chọn 2 trạm khác nhau.",
        "en": "Origin and destination are the same. Please choose two different stops.",
    },
    "no_route_found": {
        "vi": "Không tìm thấy tuyến phù hợp (trực tiếp hoặc 1 lần chuyển tuyến) giữa 2 điểm đã chọn "
              "trong dữ liệu hiện tại. Hãy thử 2 trạm khác, ví dụ các bến trung tâm.",
        "en": "No suitable route (direct or 1 transfer) found between the two selected points in the "
              "current data. Try different stops, e.g. central hub stations.",
    },
    "found_n_options": {"vi": "Tìm thấy {n} phương án di chuyển.", "en": "Found {n} travel options."},
    "option_label": {"vi": "Phương án {i}", "en": "Option {i}"},
    "choose_option": {"vi": "Chọn phương án để xem chi tiết / bản đồ:", "en": "Choose an option to see details / map:"},
    "total_time": {"vi": "Tổng thời gian ước tính", "en": "Total estimated time"},
    "total_fare": {"vi": "Tổng tiền vé", "en": "Total fare"},
    "n_transfers": {"vi": "Số lần chuyển tuyến", "en": "Transfers"},
    "itinerary_detail": {"vi": "Chi tiết hành trình", "en": "Itinerary details"},
    "leg": {"vi": "Chặng", "en": "Leg"},
    "board_at": {"vi": "🚏 Lên xe", "en": "🚏 Board at"},
    "alight_at": {"vi": "🏁 Xuống xe", "en": "🏁 Alight at"},
    "ride_time": {"vi": "⏱ Thời gian trên xe", "en": "⏱ Ride time"},
    "fare_label": {"vi": "💵 Giá vé", "en": "💵 Fare"},
    "expected_arrival": {"vi": "🕒 Xe dự kiến đến trạm lúc", "en": "🕒 Bus expected at stop"},
    "route_active": {"vi": "🟢 Tuyến đang hoạt động", "en": "🟢 Route in service"},
    "route_inactive": {"vi": "⚪ Ngoài giờ hoạt động", "en": "⚪ Out of service"},
    "transfer_at": {"vi": "Chuyển tuyến tại", "en": "Transfer at"},
    "route_map": {"vi": "Bản đồ hành trình", "en": "Route map"},
    "live_positions_note": {
        "vi": "⚠️ Vị trí xe buýt trên bản đồ là **ước tính mô phỏng** theo biểu đồ chạy chuẩn "
              "(giờ khởi hành, giãn cách), KHÔNG phải dữ liệu GPS thời gian thực (hiện chưa có "
              "API GPS công khai miễn phí cho xe buýt tại Việt Nam).",
        "en": "⚠️ Bus positions on the map are **simulated estimates** based on the standard schedule "
              "(departure times, headway), NOT real-time GPS data (no free public bus-GPS API exists "
              "in Vietnam yet).",
    },
    "auto_refresh_on": {"vi": "🔄 Tự động cập nhật vị trí xe (mô phỏng)", "en": "🔄 Auto-refresh bus positions (simulated)"},
    "select_route_to_track": {"vi": "Chọn tuyến để theo dõi trên bản đồ", "en": "Select a route to track on the map"},
    "buses_in_service": {"vi": "Số xe đang chạy (mô phỏng)", "en": "Buses currently running (simulated)"},
    "no_bus_running": {
        "vi": "Không có xe nào đang chạy tuyến này vào lúc này (ngoài khung giờ hoạt động).",
        "en": "No bus is currently running this route (outside operating hours).",
    },
    "stats_title": {"vi": "Thống kê mạng lưới", "en": "Network statistics"},
    "top_hubs": {"vi": "Top 10 trạm trung chuyển nhiều tuyến nhất", "en": "Top 10 busiest transfer stops"},
    "route_list": {"vi": "Danh sách tuyến đang khai thác", "en": "List of active routes"},
    "search_log_title": {"vi": "Lịch sử tìm kiếm từ Cloud Database (search_logs)", "en": "Search history from Cloud Database (search_logs)"},
    "search_log_need_cloud": {
        "vi": "Tính năng này đọc dữ liệu thật từ bảng `search_logs` trên Supabase. Hãy cấu hình Cloud "
              "Database (xem README) để xem thống kê tìm kiếm thực tế.",
        "en": "This feature reads live data from the `search_logs` table on Supabase. Configure the "
              "Cloud Database (see README) to see real search statistics.",
    },
    "no_logs_yet": {"vi": "Chưa có lượt tìm kiếm nào được ghi nhận.", "en": "No searches logged yet."},
    "total_searches": {"vi": "Tổng số lượt tìm kiếm", "en": "Total searches"},
    "n_od_pairs": {"vi": "Số cặp điểm đi-đến khác nhau", "en": "Distinct origin-destination pairs"},
    "top5_searched": {"vi": "Top 5 tuyến đường được tìm kiếm nhiều nhất", "en": "Top 5 most searched routes"},
    "recent_searches": {"vi": "20 lượt tìm kiếm gần nhất", "en": "20 most recent searches"},
    "stop_name_col": {"vi": "Tên trạm", "en": "Stop name"},
    "route_count_col": {"vi": "Số tuyến", "en": "Route count"},
    "origin_col": {"vi": "Điểm đi", "en": "Origin"},
    "dest_col": {"vi": "Điểm đến", "en": "Destination"},
    "search_count_col": {"vi": "Số lần tìm", "en": "Searches"},
}


def t(key: str, lang: str = "vi", **kwargs) -> str:
    entry = STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(lang, entry.get("vi", key))
    return text.format(**kwargs) if kwargs else text
