#!/bin/bash

echo "========================================"
echo "  航空维护管理系统 - 停止脚本"
echo "========================================"
echo ""

echo "正在停止航空系统..."
echo ""

# 检查是否有进程在端口8000上运行
process_pid=$(lsof -ti:8000 2>/dev/null)

if [ ! -z "$process_pid" ]; then
    echo "✅ 找到正在运行的进程，正在关闭..."
    echo "🔄 进程 ID: $process_pid"
    echo ""
    
    # 优雅地关闭进程（发送SIGTERM信号）
    kill -TERM $process_pid 2>/dev/null
    
    # 等待进程关闭（最多10秒）
    for i in {1..10}; do
        if ! kill -0 $process_pid 2>/dev/null; then
            echo "✅ 进程已成功关闭"
            break
        fi
        if [ $i -eq 10 ]; then
            echo "⚠️  超时，强制关闭进程..."
            kill -9 $process_pid 2>/dev/null
        fi
        sleep 1
    done
    
    echo ""
    echo "✅ 航空系统已成功停止"
else
    echo "⚠️  未找到在端口8000上运行的进程"
    echo "ℹ️  航空系统可能未在运行"
fi

echo ""
echo "========================================"
echo ""

# 等待2秒后自动关闭
sleep 2
