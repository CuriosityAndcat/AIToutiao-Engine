# AIToutiao-Engine Docker 镜像
# 构建: docker build -t aitoutiao-engine .
# 运行: docker-compose up -d
#
# 注意事项：
# 1. SenseVoice ASR 默认 CPU 模式（GPU 直通需 nvidia-docker）
# 2. Playwright 浏览器需额外安装（仅发布阶段需要）
# 3. Windows 路径已在代码中用 Path() 处理，跨平台兼容

FROM python:3.10-slim

LABEL org.opencontainers.image.title="AIToutiao-Engine"
LABEL org.opencontainers.image.description="视频→转录→研究写作→配图→组装发布的 Agentic 引擎"

# ── 系统依赖 ──
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ── 应用目录 ──
WORKDIR /app

# ── Python 依赖 ──
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# ── Node.js（可选：视频批量下载子项目需要）──
# RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
#     && apt-get install -y nodejs

# ── 应用代码 ──
COPY . .

# ── 运行时目录 ──
RUN mkdir -p outputs log

# ── 端口 ──
EXPOSE 8502

# ── 健康检查 ──
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8502/_stcore/health || exit 1

# ── 启动 ──
ENV STREAMLIT_SERVER_PORT=8502
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_FILE_WATCHER_TYPE=none
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

CMD ["streamlit", "run", "engine_app.py", \
     "--server.port=8502", \
     "--server.address=0.0.0.0", \
     "--server.fileWatcherType=none"]
