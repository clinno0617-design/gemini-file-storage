@echo off
chcp 65001 > nul

echo 正在載入環境變數...

if not exist .env (
    echo ❌ 找不到 .env 檔案
    echo 請建立 .env 檔案並設定環境變數
    pause
    exit /b 1
)

for /f "usebackq tokens=1,* delims==" %%a in (.env) do (
    if not "%%a"=="" if not "%%a:~0,1%"=="#" (
        set "%%a=%%b"
    )
)

if "%DB_PASSWORD%"=="" (
    echo ❌ DB_PASSWORD 未設定
    pause
    exit /b 1
)

echo ✅ 環境變數已載入
echo 🚀 啟動資料庫管理介面...
streamlit run db_viewer.py --server.port 8503