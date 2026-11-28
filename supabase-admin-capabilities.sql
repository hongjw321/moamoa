-- MOAMOA 일반 관리자 세부 권한 설정
-- Supabase SQL Editor에서 한 번 실행하세요.
alter table public.admin_accounts
  add column if not exists capabilities jsonb not null
  default '["members_read","announcements_manage","activity_logs_read"]'::jsonb;

update public.admin_accounts
set capabilities = '["members_read","announcements_manage","activity_logs_read"]'::jsonb
where role = 'admin' and capabilities is null;

comment on column public.admin_accounts.capabilities is
  '일반 관리자별 허용 기능 목록. 권한 검증은 admin-users Edge Function에서 수행.';
