@echo off

REM 视频通话系统启动脚本

echo 正在启动视频通话系统...

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: Python 未安装
    pause
    exit /b 1
)

REM 检查pip是否安装
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: pip 未安装
    pause
    exit /b 1
)

REM 安装依赖
echo 正在安装依赖...
pip install -r requirements.txt

REM 启动应用
echo 正在启动应用...
cd backend
python main.py
pause
