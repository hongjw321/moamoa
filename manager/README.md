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
