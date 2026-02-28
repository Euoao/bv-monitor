#!/usr/bin/env bash
# ──────────────────────────────────────────────
# BV Monitor - 卸载 systemd 服务
# 用法: sudo bash scripts/uninstall.sh
# ──────────────────────────────────────────────
set -euo pipefail

SERVICE_NAME="bv-monitor"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

# ── 权限检查 ──
if [ "$(id -u)" -ne 0 ]; then
    echo "❌ 请使用 sudo 运行此脚本"
    echo "   用法: sudo bash $0"
    exit 1
fi

# ── 检查是否已安装 ──
if [ ! -f "$SERVICE_FILE" ]; then
    echo "ℹ️  服务未安装，无需卸载"
    exit 0
fi

echo "🔧 卸载 BV Monitor 服务..."

# ── 停止 & 禁用 ──
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "⏸  停止服务..."
    systemctl stop "$SERVICE_NAME"
fi

if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "🚫 禁用开机自启..."
    systemctl disable "$SERVICE_NAME"
fi

# ── 删除 service 文件 ──
rm -f "$SERVICE_FILE"
systemctl daemon-reload

echo ""
echo "✅ 服务已卸载"
echo ""
echo "   注意: 采集数据保留在项目的 data/ 目录中，未被删除"
