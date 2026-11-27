-- Run this SQL in Supabase Dashboard > SQL Editor.
-- Each signed-in user can read and write only their own MOAMOA save data.
create table if not exists public.user_data (
  user_id uuid primary key references auth.users(id) on delete cascade,
  payload jsonb not null default '{"used":false,"owned":[],"history":[],"attendance":[],"cart":[]}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.user_data enable row level security;

drop policy if exists "Users can read their own MOAMOA data" on public.user_data;
create policy "Users can read their own MOAMOA data"
on public.user_data for select
to authenticated
using (auth.uid() = user_id);

drop policy if exists "Users can insert their own MOAMOA data" on public.user_data;
create policy "Users can insert their own MOAMOA data"
on public.user_data for insert
to authenticated
with check (auth.uid() = user_id);

drop policy if exists "Users can update their own MOAMOA data" on public.user_data;
create policy "Users can update their own MOAMOA data"
on public.user_data for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

grant select, insert, update on public.user_data to authenticated;
