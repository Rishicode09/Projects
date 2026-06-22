-- Sample seed data for local development.
-- Replace the user_id below with a real auth.users id from your project, then
-- run: supabase db reset  (which applies migrations + this seed).

-- NOTE: This assumes a test user exists. Create one via the Supabase Auth UI
-- or `supabase auth admin create-user`, then substitute its UUID here.
do $$
declare
  demo_user uuid;
begin
  select id into demo_user from auth.users order by created_at limit 1;
  if demo_user is null then
    raise notice 'No auth users found — skipping seed. Create a user first.';
    return;
  end if;

  insert into public.user_settings (user_id, is_premium)
  values (demo_user, false)
  on conflict (user_id) do nothing;

  insert into public.products
    (user_id, name, brand, category, retailer, purchase_date, purchase_price, warranty_expiry, return_expiry)
  values
    (demo_user, 'Sony WH-1000XM5', 'Sony', 'electronics', 'Best Buy',
      current_date - interval '40 days', 399.99,
      current_date + interval '690 days', current_date - interval '10 days'),
    (demo_user, 'Dyson V15 Vacuum', 'Dyson', 'appliances', 'Dyson.com',
      current_date - interval '15 days', 749.00,
      current_date + interval '20 days', current_date + interval '15 days'),
    (demo_user, 'Herman Miller Aeron', 'Herman Miller', 'furniture', 'Office Depot',
      current_date - interval '300 days', 1395.00,
      current_date + interval '3800 days', null),
    (demo_user, 'DeWalt Drill Kit', 'DeWalt', 'tools', 'Home Depot',
      current_date - interval '5 days', 159.00,
      current_date + interval '1090 days', current_date + interval '25 days');
end $$;
