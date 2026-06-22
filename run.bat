@echo off
cd /d "%~dp0"

rem 既に起動していればブラウザを開くだけ
netstat -ano | findstr :8501 | findstr LISTENING >nul
if %errorlevel%==0 (
    echo アプリは既に起動しています。ブラウザを開きます。
    start "" http://localhost:8501
    timeout /t 2 >nul
    exit /b
)

echo アプリを起動しています。十数秒後にブラウザが自動で開きます。
echo 開かない場合は、起動完了後に http://localhost:8501 にアクセスしてください。
echo （このウィンドウは閉じないでください。閉じるとアプリが停止します）
"C:\Users\masab\AppData\Local\Programs\Python\Python312\python.exe" -m streamlit run app.py
pause
