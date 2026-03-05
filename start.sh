#!/bin/bash

echo "========================================"
echo "  航空维护管理系统 - 启动脚本"
echo "========================================"
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: Python 3 未安装"
    exit 1
fi

# 检查pip是否安装
if ! command -v pip3 &> /dev/null; then
    echo "❌ 错误: pip3 未安装"
    exit 1
fi

# 安装依赖
echo "📦 正在检查并安装依赖..."
pip3 install -r requirements.txt -q
echo ""

# 检查是否需要生成SSL证书
if [ ! -f "backend/cert.pem" ]; then
    echo "⚠️  未检测到SSL证书"
    echo ""
    read -p "是否生成SSL证书以启用HTTPS（远程访问需要）? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "🔐 正在生成SSL证书..."
        python3 generate_cert.py
        echo ""
    fi
fi

# 检查SSL证书状态并显示访问信息
cd backend
if [ -f "cert.pem" ] && [ -f "key.pem" ]; then
    echo "✅ 检测到SSL证书，将使用HTTPS模式启动"
    echo "📍 本地访问: https://localhost:8000"
    
    # 获取本机IP
    if command -v ip &> /dev/null; then
        LOCAL_IP=$(ip route get 1 | awk '{print $7;exit}')
    elif command -v ifconfig &> /dev/null; then
        LOCAL_IP=$(ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | head -n1)
    fi
    
    if [ ! -z "$LOCAL_IP" ]; then
        echo "📍 远程访问: https://$LOCAL_IP:8000"
    fi
    
    echo ""
    echo "⚠️  首次访问时浏览器会提示证书不受信任"
    echo "    请点击'高级' → '继续访问'即可"
else
    echo "📍 访问地址: http://localhost:8000"
    echo "⚠️  远程访问时摄像头/麦克风可能无法使用"
    echo "💡 运行 'python3 generate_cert.py' 生成SSL证书"
fi

echo ""
echo "========================================"
echo ""

# 启动应用
echo "🚀 正在启动服务器..."
echo ""
python3 main.py
