#!/bin/bash

# 视频通话系统启动脚本

echo "正在启动视频通话系统..."

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: Python 3 未安装"
    exit 1
fi

# 检查pip是否安装
if ! command -v pip3 &> /dev/null; then
    echo "错误: pip3 未安装"
    exit 1
fi

# 安装依赖
echo "正在安装依赖..."
pip3 install -r requirements.txt

# 启动应用
echo "正在启动应用..."
cd backend
python3 main.py
