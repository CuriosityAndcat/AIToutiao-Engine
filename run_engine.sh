#!/bin/bash
# ============================================================
# AIToutiao 引擎模式 v1.0 — Linux/Mac 启动脚本
# 端口: 8502（独立运行）
# 用法: chmod +x run_engine.sh && ./run_engine.sh
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=========================================="
echo "    AIToutiao 引擎模式 v1.0"
echo "    端口: 8502（独立运行）"
echo "=========================================="
echo ""

# ── 依赖检查 ──
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    echo "[ERROR] Python 未安装，请先安装 Python 3.10+"
    exit 1
fi

PYTHON=$(command -v python3 || command -v python)

if ! $PYTHON -c "import streamlit" 2>/dev/null; then
    echo "[WARN] streamlit 未安装。请运行: pip install -r requirements.txt"
    echo "       详细依赖说明见 requirements.txt 头部注释。"
fi

if [ ! -f ".env" ]; then
    echo "[WARN] .env 文件不存在，请复制 .env.example 或通过 Web UI 配置 API Key。"
fi

echo "正在启动 Streamlit 引擎..."
echo ""

# ── 启动 ──
# 无头环境（无 < nul 对应）自动关闭 stdin 避免阻塞
exec "$PYTHON" -m streamlit run engine_app.py \
    --server.port 8502 \
    --server.address 0.0.0.0 \
    --server.fileWatcherType none \
    < /dev/null
