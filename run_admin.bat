@echo off
chcp 65001 > nul

echo 正在載入環境變數...

if not exist .env (
    echo ❌ 找不到 .env 檔案
    echo 請建立 .env 檔案並設定 GEMINI_API_KEY
    pause
    exit /b 1
)

for /f "usebackq tokens=1,* delims==" %%a in (.env) do (
    if not "%%a"=="" if not "%%a:~0,1%"=="#" (
        set "%%a=%%b"
    )
)

if "%GEMINI_API_KEY%"=="" (
    echo ❌ GEMINI_API_KEY 未設定
    pause
    exit /b 1
)

echo ✅ 環境變數已載入
echo 🚀 啟動後端管理介面...
streamlit run admin.py --server.port 8501