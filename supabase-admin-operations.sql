-- MOAMOA 운영 관리 기능
-- Supabase Dashboard > SQL Editor에서 전체 실행하세요.

create table if not exists public.announcements (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  body text not null,
  is_published boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  published_at timestamptz
);

alter table public.announcements enable row level security;
drop policy if exists "Public can read published announcements" on public.announcements;
create policy "Public can read published announcements"
on public.announcements for select
to anon, authenticated
using (is_published = true);
grant select on public.announcements to anon, authenticated;
grant all on public.announcements to service_role;

create table if not exists public.member_activity_logs (
  id bigint generated always as identity primary key,
  user_id uuid references auth.users(id) on delete set null,
  email text,
  action text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists member_activity_logs_created_at_idx
on public.member_activity_logs(created_at desc);
create index if not exists member_activity_logs_user_id_idx
on public.member_activity_logs(user_id);
alter table public.member_activity_logs enable row level security;
grant all on public.member_activity_logs to service_role;

create table if not exists public.admin_error_logs (
  id bigint generated always as identity primary key,
  source text not null default 'admin-api',
  message text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists admin_error_logs_created_at_idx
on public.admin_error_logs(created_at desc);
alter table public.admin_error_logs enable row level security;
grant all on public.admin_error_logs to service_role;

create or replace function public.moamoa_capture_auth_activity()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if TG_OP = 'INSERT' then
    insert into public.member_activity_logs(user_id, email, action, details)
    values (new.id, new.email, '회원가입', jsonb_build_object('source', 'supabase-auth'));
  else
    if new.last_sign_in_at is distinct from old.last_sign_in_at
       and new.last_sign_in_at is not null then
      insert into public.member_activity_logs(user_id, email, action, details)
      values (new.id, new.email, '로그인', jsonb_build_object('source', 'supabase-auth'));
    end if;
    if new.raw_user_meta_data is distinct from old.raw_user_meta_data then
      insert into public.member_activity_logs(user_id, email, action, details)
      values (new.id, new.email, '프로필 변경', jsonb_build_object('source', 'supabase-auth'));
    end if;
  end if;
  return new;
end;
$$;

drop trigger if exists moamoa_auth_activity_trigger on auth.users;
create trigger moamoa_auth_activity_trigger
after insert or update of last_sign_in_at, raw_user_meta_data on auth.users
for each row execute function public.moamoa_capture_auth_activity();

-- 관리자 API가 service_role로만 조회/기록합니다.
