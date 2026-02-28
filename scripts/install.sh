#!/usr/bin/env bash
# ──────────────────────────────────────────────
# BV Monitor - 安装 systemd 服务
# 用法: sudo bash scripts/install.sh [端口号]
# 示例: sudo bash scripts/install.sh 9000
# ──────────────────────────────────────────────
set -euo pipefail

SERVICE_NAME="bv-monitor"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
PORT="${1:-8000}"

# ── 路径检测 ──
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
VENV_UVICORN="$PROJECT_DIR/.venv/bin/uvicorn"

# ── 权限检查 ──
if [ "$(id -u)" -ne 0 ]; then
    echo "❌ 请使用 sudo 运行此脚本"
    echo "   用法: sudo bash $0"
    exit 1
fi

# ── 前置检查 ──
if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ 未找到虚拟环境，请先在项目目录执行: uv sync"
    exit 1
fi

if [ ! -f "$VENV_UVICORN" ]; then
    echo "❌ 未找到 uvicorn，请先在项目目录执行: uv sync"
    exit 1
fi

# 检测项目目录的所有者（用于 User/Group）
RUN_USER="$(stat -c '%U' "$PROJECT_DIR")"
RUN_GROUP="$(stat -c '%G' "$PROJECT_DIR")"

echo "🔧 安装 BV Monitor 服务..."
echo "   项目目录: $PROJECT_DIR"
echo "   运行用户: $RUN_USER"
echo "   监听端口: $PORT"

# ── 如果已有旧服务，先停掉 ──
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "⏸  停止旧服务..."
    systemctl stop "$SERVICE_NAME"
fi

# ── 生成 service 文件 ──
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=BV Monitor - B站视频数据实时监控
After=network.target

[Service]
Type=simple
User=$RUN_USER
Group=$RUN_GROUP
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_UVICORN main:app --host 127.0.0.1 --port $PORT
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# ── 启用并启动 ──
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl start "$SERVICE_NAME"

echo ""
echo "✅ 服务已安装并启动！"
echo ""
echo "   访问地址: http://localhost:$PORT"
echo ""
echo "   常用命令:"
echo "     查看状态   systemctl status $SERVICE_NAME"
echo "     查看日志   journalctl -u $SERVICE_NAME -f"
echo "     重启服务   sudo systemctl restart $SERVICE_NAME"
echo "     停止服务   sudo systemctl stop $SERVICE_NAME"
