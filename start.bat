@echo off
chcp 65001 >nul

echo ========================================
echo   航空维护管理系统 - 启动脚本
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: Python 未安装
    pause
    exit /b 1
)

REM 检查pip是否安装
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: pip 未安装
    pause
    exit /b 1
)

REM 安装依赖
echo 📦 正在检查并安装依赖...
pip install -r requirements.txt -q
echo.

REM 检查是否需要生成SSL证书
if not exist "backend\cert.pem" (
    echo ⚠️  未检测到SSL证书
    echo.
    choice /C YN /M "是否生成SSL证书以启用HTTPS（远程访问需要）"
    if errorlevel 2 goto skip_cert
    if errorlevel 1 (
        echo.
        echo 🔐 正在生成SSL证书...
        python generate_cert.py
        echo.
    )
)

:skip_cert
REM 检查SSL证书状态并显示访问信息
cd backend
if exist "cert.pem" (
    if exist "key.pem" (
        echo ✅ 检测到SSL证书，将使用HTTPS模式启动
        echo 📍 本地访问: https://localhost:8000
        for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
            set IP=%%a
            goto :found_ip
        )
        :found_ip
        if defined IP (
            set IP=%IP: =%
            echo 📍 远程访问: https://!IP!:8000
        )
        echo.
        echo ⚠️  首次访问时浏览器会提示证书不受信任
        echo     请点击"高级" → "继续访问"即可
    )
) else (
    echo 📍 访问地址: http://localhost:8000
    echo ⚠️  远程访问时摄像头/麦克风可能无法使用
    echo 💡 运行 'python generate_cert.py' 生成SSL证书
)
echo.
echo ========================================
echo.

REM 启动应用
echo 🚀 正在启动服务器...
echo.
python main.py

pause
