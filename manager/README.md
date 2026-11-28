# MOAMOA MANAGER

Windows desktop administration app for the MOAMOA GitHub Pages project.

## Build locally
1. Install 64-bit Python 3.11 or newer on Windows.
2. Open this folder and double-click `build_windows.bat`.
3. The executable is created under `dist\MOAMOA-Manager\MOAMOA-Manager.exe`.

## First launch
- Supabase URL and browser-safe publishable/anon key are saved in `%APPDATA%\MOAMOA Manager\settings.json`.
- GitHub Fine-grained Personal Access Token is stored with Windows Credential Manager through Python keyring.
- Use the least privilege needed (repository metadata/content read and Actions read). Do not grant administration unless a later feature explicitly requires it.
- Never enter Supabase service_role/secret keys in this app.

## Current working features
- Supabase Auth health endpoint connectivity check.
- GitHub repository metadata and latest Actions runs.
- Open Supabase Auth users / Table Editor and GitHub repository / Actions pages.

## Not yet enabled
Member listing, deletion, editing, database backup/restore, content editing and one-click deploy require authenticated server-side admin endpoints and additional implementation. They are intentionally not simulated in this first build.


## 회원 관리 API 설정 (필수)
회원 목록/수정/삭제는 Supabase Edge Function을 통해서만 실행합니다. EXE와 GitHub 저장소에는 service_role 키를 넣지 않습니다.

1. Supabase Dashboard > Edge Functions에서 `admin-users` 함수를 생성합니다.
2. 저장소의 `supabase/functions/admin-users/index.ts` 전체 내용을 붙여 넣고 Deploy 합니다.
3. Edge Function Secrets에 `MOAMOA_ADMIN_EMAILS`를 추가하고 관리자 로그인에 사용할 이메일 주소를 정확히 입력합니다. 여러 명이면 쉼표로 구분합니다.
4. `SUPABASE_SERVICE_ROLE_KEY`는 Supabase Edge Function Secrets에만 저장합니다. 이 키를 EXE, 웹사이트, GitHub 코드/Actions에 입력하지 마세요.
5. Edge Function의 JWT verification을 켜 둡니다.
6. EXE > 환경 설정에 Supabase URL과 publishable/anon key가 저장되어 있는지 확인합니다.
7. 회원 관리 화면에서 허용 목록에 등록한 이메일과 Supabase 비밀번호로 로그인합니다.

관리자 로그인 세션은 Windows 자격 증명 저장소에 저장됩니다. 비밀번호는 저장하지 않습니다. 회원 삭제는 되돌릴 수 없으며 해당 회원의 `user_data`도 외래 키의 ON DELETE CASCADE 설정에 따라 함께 삭제됩니다.

현재 회원 목록은 한 번에 최대 100명까지 표시합니다. 이메일·이름·닉네임 검색, 프로필(이름/닉네임/휴대폰/주소) 수정, 계정 영구 삭제를 지원합니다. 이메일 주소와 비밀번호 자체는 이 화면에서 수정하지 않습니다.
