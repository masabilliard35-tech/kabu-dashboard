@echo off
cd /d "%~dp0"
netstat -ano | findstr :8501 | findstr LISTENING >nul
if %errorlevel%==0 (
    echo App is already running. Opening browser.
    start "" http://localhost:8501
    timeout /t 2 >nul
    exit /b
)
echo Starting the app. The browser opens in ~10-20 seconds.
echo If it does not open, visit http://localhost:8501
echo (Do NOT close this window - closing it stops the app)
"C:\Users\masab\AppData\Local\Programs\Python\Python312\python.exe" -m streamlit run app.py --server.headless false
pause