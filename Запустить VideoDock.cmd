@echo off
cd /d "%~dp0"
if exist "dist\VideoDock\VideoDock.exe" (
    start "" "dist\VideoDock\VideoDock.exe"
) else (
    if exist ".venv\Scripts\pythonw.exe" (
        start "" ".venv\Scripts\pythonw.exe" "app.py"
    ) else (
        echo Run: python -m pip install -r requirements.txt
        echo Then: python app.py
        pause
    )
)
