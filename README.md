# AIToutiao Engine 🚀

独立内容生成引擎 —— 视频下载 → 语音转录 → AI写作 → 人工化改写 → 配图生成 → 图文组装，一键完成。

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# 2. 配置环境
copy .env.example .env
# 编辑 .env 填入你的 DeepSeek API Key

# 3. 下载 SenseVoice 模型（可选，使用 sensevoice 转录后端时需要）
# 从 ModelScope 下载 SenseVoiceSmall 到 models/iic/SenseVoiceSmall/

# 4. 启动引擎
run_engine.bat
# 或: streamlit run engine_app.py --server.port 8502
```

打开浏览器访问 `http://localhost:8502`

## 流水线阶段

| 阶段 | 说明 |
|------|------|
| 📥 下载 | 通过 Playwright 自动下载视频 |
| 🎙️ 转录 | SenseVoice / Whisper 语音转文字 |
| ✍️ 写作 | DeepSeek AI 生成文章 |
| 🔄 改写 | 人工化处理，去除 AI 味 |
| 🖼️ 配图 | AI 生成匹配图片 |
| 📦 组装 | 图文混排，输出最终内容 |

## 项目结构

```
AIToutiao-Engine/
├── engine_app.py          # Streamlit 主界面（端口 8502）
├── run_engine.bat         # Windows 启动脚本
├── agent/                 # Agent 控制系统
├── lib/                   # 内嵌依赖库
│   ├── sensevoice-asr/    # 语音识别
│   ├── toutiao-auto-publisher/  # 头条发布
│   ├── video-batch-download-main/  # 视频下载
│   └── wewrite-main/      # 写作工具链
├── config/                # 配置文件
├── prompts/               # AI 提示词
└── backup/                # 备份文件
```

## 配置说明

所有配置通过 `.env` 文件管理，详见 `.env.example`。

关键配置项：
- `AI_API_KEY` — DeepSeek API 密钥（必填）
- `TRANSCRIBE_BACKEND` — 转录后端（`sensevoice` / `transformers` / `faster_whisper`）
- `DEFAULT_CONTENT_TYPE` — 默认内容类型（`toutie` = 微头条 / `article` = 文章）
- `ENABLE_PUBLISH` — 是否启用发布阶段
