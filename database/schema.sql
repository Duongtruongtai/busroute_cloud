-- =========================================================================
-- Smart City Bus Assistant - Schema cho Supabase (PostgreSQL)
-- Chay toan bo file nay trong Supabase Dashboard > SQL Editor > New query
-- An toan chay lai nhieu lan (idempotent): dung "if not exists" / ALTER ... ADD COLUMN IF NOT EXISTS.
-- =========================================================================

-- Bang tram dung
create table if not exists stops (
    stop_id      text primary key,
    stop_name    text not null,
    stop_name_en text,
    lat          double precision not null,
    lon          double precision not null,
    is_hub       boolean not null default false,
    city_id      text not null default 'hcmc'
);
alter table stops add column if not exists stop_name_en text;
alter table stops add column if not exists city_id text not null default 'hcmc';

-- Bang tuyen xe buyt
create table if not exists routes (
    route_id           text primary key,
    route_short_name   text not null,
    route_long_name    text not null,
    route_long_name_en text,
    fare_regular       integer not null,
    fare_student       integer not null,
    headway_min        integer not null,
    first_departure    text not null,   -- 'HH:MM'
    last_departure     text not null,   -- 'HH:MM'
    city_id             text not null default 'hcmc'
);
alter table routes add column if not exists route_long_name_en text;
alter table routes add column if not exists city_id text not null default 'hcmc';

-- Bang quan he tuyen - tram (thu tu tram tren moi tuyen + thoi gian tich luy)
create table if not exists route_stops (
    id             bigint generated always as identity primary key,
    route_id       text not null references routes (route_id) on delete cascade,
    stop_id        text not null references stops (stop_id) on delete cascade,
    stop_sequence  integer not null,
    offset_min     integer not null,
    unique (route_id, stop_sequence)
);

create index if not exists idx_route_stops_route on route_stops (route_id);
create index if not exists idx_route_stops_stop on route_stops (stop_id);
create index if not exists idx_stops_city on stops (city_id);
create index if not exists idx_routes_city on routes (city_id);

-- Bang nhat ky tim kiem (chung minh ung dung GHI du lieu that len Cloud Database,
-- dong thoi phuc vu dashboard thong ke "tuyen duoc tim nhieu nhat")
create table if not exists search_logs (
    id               bigint generated always as identity primary key,
    origin_stop_id   text not null,
    origin_stop_name text not null,
    dest_stop_id     text not null,
    dest_stop_name   text not null,
    fare_type        text not null,
    n_results        integer not null default 0,
    searched_at      timestamptz not null default now()
);

create index if not exists idx_search_logs_time on search_logs (searched_at desc);

-- =========================================================================
-- Row Level Security: bat RLS nhung cho phep doc/ghi cong khai qua anon key.
-- Day la du lieu giao thong cong cong (khong nhay cam) nen chinh sach mo la
-- hop ly cho pham vi do an; trong san pham thuc te se gioi han ghi bang
-- service_role key o phia server thay vi anon key o client.
-- =========================================================================
alter table stops enable row level security;
alter table routes enable row level security;
alter table route_stops enable row level security;
alter table search_logs enable row level security;

drop policy if exists "public read stops" on stops;
create policy "public read stops" on stops for select using (true);

drop policy if exists "public read routes" on routes;
create policy "public read routes" on routes for select using (true);

drop policy if exists "public read route_stops" on route_stops;
create policy "public read route_stops" on route_stops for select using (true);

drop policy if exists "public read search_logs" on search_logs;
create policy "public read search_logs" on search_logs for select using (true);

drop policy if exists "public insert search_logs" on search_logs;
create policy "public insert search_logs" on search_logs for insert with check (true);
