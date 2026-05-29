#!/bin/bash
# 一键启动脚本

set -e

echo "=== 论文助手启动 ==="

# 检查 .env
if [ ! -f backend/.env ]; then
    echo "创建 .env 文件..."
    cp backend/.env.example backend/.env
    echo "请编辑 backend/.env 填入 API Key"
    exit 1
fi

# 检查 Docker
if command -v docker &> /dev/null; then
    echo "使用 Docker 启动..."
    docker compose up --build -d
    echo "后端运行在 http://localhost:8000"
    echo "查看日志: docker compose logs -f backend"
else
    echo "Docker 未安装，使用本地 Python 启动..."
    cd backend
    uv sync
    uv run python main.py
fi
