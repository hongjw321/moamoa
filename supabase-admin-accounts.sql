-- MOAMOA 관리자 계정 관리 테이블
-- Supabase SQL Editor에서 한 번만 실행하세요.

create table if not exists public.admin_accounts (
  email text primary key,
  role text not null default 'admin' check (role in ('admin', 'super_admin')),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.admin_accounts enable row level security;

revoke all on table public.admin_accounts from anon, authenticated;
grant select, insert, update, delete on table public.admin_accounts to service_role;

create index if not exists admin_accounts_role_idx
  on public.admin_accounts (role);

comment on table public.admin_accounts is
  'MOAMOA 관리자 계정 및 역할 관리. service_role을 사용하는 관리자 Edge Function만 접근.';
