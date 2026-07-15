# AIToutiao Engine 🚀

独立内容生成引擎 —— 视频下载 → 语音转录 → AI写作 → 人工化改写 → 配图生成 → 图文组装，一键完成。

> 📌 **新成员 / AI 协作请先读 [`AGENTS.md`](AGENTS.md)**（项目地图），涉及流水线查 [`specs/pipeline.md`](specs/pipeline.md)，涉及验收查 [`specs/acceptance.md`](specs/acceptance.md)，涉及网页查 [`docs/WEB_REVIEW.md`](docs/WEB_REVIEW.md)，使用约定见 [`specs/USAGE.md`](specs/USAGE.md)。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# 可选依赖（发布阶段需要）
playwright install chromium  # YouTube/抖音浏览器自动化
# Node.js 18+  — 抖音 Playwright 下载所需

# 2. 配置环境
copy .env.example .env
# 编辑 .env 填入你的 DeepSeek API Key

# 3. 下载 SenseVoice 模型（可选，使用 sensevoice 转录后端时需要）
# 从 ModelScope 下载 SenseVoiceSmall 到 lib/sensevoice-asr/models/iic/SenseVoiceSmall/
# 或设置环境变量 SENSEVOICE_MODEL_DIR 指向模型目录
# 未配置时将自动回退到 transformers/whisper-small

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
| ✍️ 写作 | DeepSeek AI 生成文章（4 种风格可选） |
| 🔄 改写 | 人工化处理，去除 AI 味 |
| 🖼️ 配图 | Agnes AI 生成匹配图片 |
| 📦 组装 | 图文混排，输出最终内容 |

### 写作风格（4 种）

| 风格 | 作者对标 | 特点 |
|------|---------|------|
| 🔥 包明说（默认） | 包明说 | 反差悬念型，适合军事/时政 |
| 📚 晋说 | 晋说 | 乡愁叙事型，适合人文/历史 |
| 🏛️ 全球档案馆 | 全球档案馆 | 馆长悬疑型，适合科技/解密 |
| 📖 听风的蚕 | 听风的蚕 | 评书故事型，适合历史/故事 |

### 实验功能

- **Claim-Pipeline（B-2）**：四阶段事实锚定（提取→验证→合并→写作），根治 LLM 幻觉，`write_stage.py` 中 `CLAIM_PIPELINE_ENABLED = False`（开发中）

## 项目结构

```
AIToutiao-Engine/
├── engine_app.py          # Streamlit 主界面（端口 8502）
├── run_engine.bat         # Windows 启动脚本
├── AGENTS.md              # 项目地图（AI 协作入口）
├── requirements.txt       # Python 依赖清单
├── .env.example           # 环境变量模板
├── agent/                 # Harness 框架层（Agent/Runner/Graph/内存/护栏/搜索）
├── lib/                   # 内嵌依赖库
│   ├── sensevoice-asr/    # SenseVoice 语音识别
│   ├── toutiao-auto-publisher/  # 头条发布后端（write/research/evaluation）
│   ├── video-batch-download-main/  # 视频批量下载（Node/JS）
│   └── wewrite-main/      # 写作工具链（cover_prompt_builder/image_gen）
├── docs/                  # 文档/Skills/选题分析/风格分析
├── specs/                 # 流水线+验收契约（pipeline.md / acceptance.md）
├── tests/                 # 阶段功能测试入口（run_stage.py）
├── scripts/               # 实用脚本
├── outputs/               # 运行产物输出目录
├── log/                   # 日志文件落盘
├── backup/                # 备份文件
└── .codebuddy/            # CodeBuddy IDE 配置（Skills/Agents/Rules/Memory）
```

## 配置说明

所有配置通过 `.env` 文件管理，详见 `.env.example`。

关键配置项：
- `AI_API_KEY` — DeepSeek API 密钥（必填）
- `TRANSCRIBE_BACKEND` — 转录后端（`sensevoice` / `transformers` / `faster_whisper`）
- `DEFAULT_CONTENT_TYPE` — 默认内容类型（`toutie` = 微头条 / `article` = 文章）
- `ENABLE_PUBLISH` — 是否启用发布阶段
