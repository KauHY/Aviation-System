@echo off

REM 航空系统 - 停止脚本

echo 正在停止航空系统...
echo.

REM 检查是否有进程在端口8000上运行
netstat -ano | find "8000" >nul 2>&1
if %errorlevel% equ 0 (
    echo 找到正在运行的进程，正在关闭...
    
    REM 获取进程ID并关闭
    for /f "tokens=5" %%a in ('netstat -ano ^| find "8000"') do (
        echo 关闭进程 ID: %%a
        taskkill /PID %%a /F /T >nul 2>&1
    )
    
    echo 进程已关闭
    echo.
    echo 航空系统已成功停止
) else (
    echo 未找到在端口8000上运行的进程
    echo 航空系统可能未在运行
)

echo.
pause
