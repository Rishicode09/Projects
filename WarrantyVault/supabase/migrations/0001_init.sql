-- Warranty Vault — initial schema
-- Run with: supabase db push  (or apply via the Supabase SQL editor)

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- products
-- ---------------------------------------------------------------------------
create type product_category as enum (
  'electronics', 'appliances', 'furniture', 'tools', 'clothing', 'automotive', 'other'
);

create table if not exists public.products (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users (id) on delete cascade,
  name            text not null check (char_length(name) between 1 and 120),
  brand           text,
  category        product_category not null default 'other',
  retailer        text,
  purchase_date   date not null,
  purchase_price  numeric(12, 2) not null default 0 check (purchase_price >= 0),
  warranty_expiry date,
  return_expiry   date,
  receipt_url     text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create index if not exists products_user_id_idx on public.products (user_id);
create index if not exists products_warranty_expiry_idx on public.products (warranty_expiry);

-- ---------------------------------------------------------------------------
-- user_settings (one row per user)
-- ---------------------------------------------------------------------------
create table if not exists public.user_settings (
  user_id         uuid primary key references auth.users (id) on delete cascade,
  notifications   jsonb not null default
                    '{"warranty_30_day": true, "warranty_7_day": true, "return_1_day": true}'::jsonb,
  is_premium      boolean not null default false,
  analytics_opt_in boolean not null default false,
  updated_at      timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- updated_at trigger
-- ---------------------------------------------------------------------------
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger products_set_updated_at
  before update on public.products
  for each row execute function public.set_updated_at();

create trigger user_settings_set_updated_at
  before update on public.user_settings
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Row Level Security — users may only access their own rows
-- ---------------------------------------------------------------------------
alter table public.products enable row level security;
alter table public.user_settings enable row level security;

create policy "products are owner-only"
  on public.products for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "settings are owner-only"
  on public.user_settings for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- Auto-provision a settings row on signup
-- ---------------------------------------------------------------------------
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.user_settings (user_id) values (new.id)
  on conflict (user_id) do nothing;
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
