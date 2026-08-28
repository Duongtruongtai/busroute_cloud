"""
Nap du lieu tu dataset/*.csv len Supabase (Cloud Database).

Dieu kien truoc khi chay:
1. Da tao project Supabase va chay xong database/schema.sql trong SQL Editor.
2. Da dat 2 bien moi truong (hoac tao file .env va load thu cong):
   SUPABASE_URL=https://xxxxx.supabase.co
   SUPABASE_KEY=<service_role key - de co quyen ghi, KHONG dung cho client/app>

Chay:
    python database/seed_supabase.py
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATASET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset")


def main():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("Loi: can dat bien moi truong SUPABASE_URL va SUPABASE_KEY truoc khi chay.")
        print("Vi du (PowerShell):")
        print('  $env:SUPABASE_URL = "https://xxxxx.supabase.co"')
        print('  $env:SUPABASE_KEY = "service_role_key..."')
        sys.exit(1)

    from supabase import create_client
    client = create_client(url, key)

    stops = pd.read_csv(os.path.join(DATASET_DIR, "stops.csv"))
    routes = pd.read_csv(os.path.join(DATASET_DIR, "routes.csv"))
    route_stops = pd.read_csv(os.path.join(DATASET_DIR, "route_stops.csv"))

    # is_hub trong CSV la 0/1 -> chuyen ve boolean cho dung kieu Postgres
    stops["is_hub"] = stops["is_hub"].astype(bool)

    print(f"Dang xoa du lieu cu (neu co)...")
    client.table("route_stops").delete().neq("route_id", "").execute()
    client.table("routes").delete().neq("route_id", "").execute()
    client.table("stops").delete().neq("stop_id", "").execute()

    print(f"Dang nap {len(stops)} tram...")
    client.table("stops").insert(stops.to_dict(orient="records")).execute()

    print(f"Dang nap {len(routes)} tuyen...")
    client.table("routes").insert(routes.to_dict(orient="records")).execute()

    print(f"Dang nap {len(route_stops)} dong route_stops...")
    # Insert theo lo (batch) de tranh vuot gioi han payload
    records = route_stops.to_dict(orient="records")
    batch_size = 200
    for i in range(0, len(records), batch_size):
        client.table("route_stops").insert(records[i:i + batch_size]).execute()

    print("Hoan tat! Du lieu da san sang tren Supabase.")


if __name__ == "__main__":
    main()
