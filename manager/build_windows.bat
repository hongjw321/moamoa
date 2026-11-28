@echo off
setlocal
cd /d %~dp0
py -3 -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pyinstaller --noconfirm --clean --windowed --name "MOAMOA-Manager" --collect-all keyring --hidden-import=services --paths . main.py
echo.
echo Build complete: manager\dist\MOAMOA-Manager\MOAMOA-Manager.exe
pause
