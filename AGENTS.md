# AGENTS.md — AIToutiao-Engine 项目地图

> 本文件是项目的「地图」，供 AI 协作与人类开发者快速定位模块、理解架构。
> 非规格文档（见 `specs/`）。本文只描述「现状」，不规定「未来」。

---

## 一句话定位

一个将**视频/口播素材**经「下载 → 转录 → 研究写作 → 配图 → 组装发布」流水线，自动生成并发布头条/公众号图文内容的 Agentic 引擎。`agent/` 是自建的 Harness 框架层（对齐 OpenAI Agents SDK + LangGraph），`lib/toutiao-auto-publisher/` 是生产主项目。

---

## 顶层目录职责

| 路径 | 职责 | 备注 |
|---|---|---|
| `agent/` | **Harness 框架层** — Agent 定义、Runner、Graph、记忆、护栏、搜索、LLM 封装 | 12 个模块，对齐 OpenAI Agents SDK + LangGraph API |
| `lib/toutiao-auto-publisher/` | **生产主项目** — 内容研究/写作/评估/发布的后端实现 | 真实跑流水线的代码 |
| `lib/sensevoice-asr/` | 语音识别（ASR）子项目，视频转文字 | 含测试 mp3/png |
| `lib/video-batch-download-main/` | 视频批量下载子项目（Node/JS 为主） | 第三方改造 |
| `lib/wewrite-main/` | 微信写作相关（YAML 配置 + py） | 第三方改造 |
| `docs/` | 选题/对比分析/对接文档 + 网页评审基线 | `WEB_REVIEW.md`（网页评审）、`douyin_topics.md` 等 |
| `engine_app.py` | **生产编排入口 + 全链路观测** | 三通道 `add_log` + `log/` 落盘 |
| `requirements.txt` / `run_engine.bat` / `README.md` | 依赖、启动脚本、说明 | — |
| `_test_faster_whisper.py` / `_test_transcribe_speed.py` | ASR 速度验证脚本 | 散落根目录，待归入 `lib/sensevoice-asr/` |

---

## `agent/` 模块职责（12 个，已逐文件核实）

| 模块 | 对齐框架 | 职责 | 生产接入状态 |
|---|---|---|---|
| `__init__.py` | — | 包导出，`__version__="0.2.0"`，聚合全部公共 API | 被 `write_stage` 等 `from agent.xxx import` |
| `agent.py` | OpenAI Agents SDK `agent.py` | `Agent` 定义：`name`+`instructions`+`tools`+`handoffs`+`guards` | 框架层，未直接接生产循环 |
| `config.py` | OpenAI Agents SDK `run.py` | `RunConfig`：`max_iterations`/`temperature`/`model`/`api_key`/`base_url`/`max_tokens` | 框架层 |
| `graph.py` | LangGraph `StateGraph` | `AgentGraph` Evaluator-Optimizer 工作流图构建器 | ⚠ **未接生产**（`write_stage` 自带循环） |
| `guardrails.py` | OpenAI Agents SDK `guardrails.py` | 三层护栏：`InputGuardrail` / `PolicyGuardrail` / `OutputGuardrail` | ✅ **已接**（`write_stage` 输入/输出/人工化三处调用） |
| `llm_client.py` | 对齐 `ai_writer.py` `AIWriter._call_ai()` | `LLMClient` 封装 OpenAI SDK 调 DeepSeek | 框架层，模式与 `ai_writer` 一致 |
| `memory.py` | LangGraph Reflexion | 三层记忆：`ConversationMemory`(短期) / `WorkingMemory`(工作) / `LongTermMemory`(长期，待接入) | ✅ **`WorkingMemory` 已被 `write_stage` 使用** |
| `runner.py` | OpenAI Agents SDK `run.py` | `Runner` 执行器，编排 `search→execute→evaluate→{PASS/END|FIXABLE|fix|BLOCKED}` | 框架层，未直接接生产 |
| `search_engine.py` | — | `search_web` 百度优先→搜狗 fallback（国内直连） | ✅ **已被 `research.py` 使用** |
| `state.py` | LangGraph `StateGraph` | `AgentState` TypedDict + `add_messages` reducer | 框架层 |
| `tools.py` | OpenAI Agents SDK `function_tool.py` | `function_tool` 装饰器 + `ToolRegistry` | 框架层 |
| `types.py` | LangGraph Reflexion `cool_classes.py` | Pydantic 模型：`Reflection`/`AnswerQuestion`/`ReviseAnswer`/`ResearchQuery`/`SearchResult`/`TaskResult` | 框架层 |

---

## `lib/toutiao-auto-publisher/backend` 关键文件

| 文件 | 职责 | 与 `agent/` 的关联 |
|---|---|---|
| `write_stage.py` | **写作阶段**：Evaluator-Optimizer 自愈闭环（迭代择优 `best_score`） | `from agent.memory import WorkingMemory` ✅ |
| `research.py` | 内容研究/资料检索 | `from agent.search_engine import search_web` ✅ |
| `evaluation.py` | **5 维度验收**：事实/完整/结构/风格/去AI味，`QUALITY_PASS_THRESHOLD=75` | 被 `write_stage` 调用 ✅ |
| `ai_writer.py` | AI 写作核心 `AIWriter`，`_call_ai()` 调用模式 | `llm_client.py` 对齐此模式 |
| `models.py` | 数据模型 `ContentType` / `ContentStyle` 等 | 机器可读契约来源 |
| `publisher_service.py` | 发布服务 | — |
| `config.py` / `main.py` | 配置 / 入口 | — |
| `prompts/` | 10 个 prompt 模板 | — |
| `STYLE_GUIDE_MILITARY.md` | 军事风风格指南 | — |

---

## 生产流水线 ↔ 文件映射

```
下载   → lib/video-batch-download-main/        (视频批量下载)
转录   → lib/sensevoice-asr/ + _test_*.py       (ASR 语音转文字)
研究写作→ lib/toutiao-auto-publisher/backend/
           research.py ──search_web──▶ agent/search_engine.py
           write_stage.py ──WorkingMemory──▶ agent/memory.py
                          └─evaluate_content─▶ evaluation.py (5维/阈值75)
配图   → (prompts/ + 配图逻辑，由 engine_app.py 编排)
组装发布→ engine_app.py + publisher_service.py
观测   → engine_app.py 三通道 add_log + log/ 落盘
```

---

## Harness 六组件在生产中的接入状态（关键事实）

| 组件 | 状态 | 说明 |
|---|---|---|
| 记忆 `WorkingMemory` | ✅ 已接 | `write_stage` 跨轮反思累积 |
| 搜索 `search_web` | ✅ 已接 | `research.py` 调用 |
| 自愈 Evaluator-Optimizer | ✅ 已接 | `write_stage` 迭代闭环 |
| 验收 `evaluation` | ✅ 已接 | 5 维度 + 阈值 75 |
| 护栏 `guardrails` | ✅ 已接 | `write_stage` 输入/输出/人工化接入三层护栏 |
| 通用编排 `AgentGraph`/`Runner` | ⚠ 未接 | `write_stage` 自带循环，两套自愈并存 |

> 结论：Harness 六组件中 **4 项已在生产运行**，真实缺口仅为「护栏未接线」与「观测未结构化」，以及文档层（本文即补此缺口）。

---

## 开发约束（指针式）

1. **改生产逻辑**优先改 `lib/toutiao-auto-publisher/backend/`，尤其 `write_stage.py` / `research.py` / `evaluation.py`。
2. **`agent/` 是框架层**，改动需保持与 OpenAI Agents SDK / LangGraph API 对齐（各文件头部标注了参考源码）。
3. **护栏改动不会自动生效**——`guardrails.py` 仅定义框架，`write_stage` 需新增调用点才接入生产。
4. **验收标准以 `evaluation.py` 为准**（5 维 + 阈值 75），不要另起炉灶。
5. **新增 ASR 验证脚本**应归入 `lib/sensevoice-asr/`，避免散落根目录。
6. 规格化契约优先复用 `models.py` 的 `ContentType` / `ContentStyle`，而非新建类型。
7. **改网页 UI（`engine_app.py`）**前先查 `docs/WEB_REVIEW.md`（评审基线 + 技能选型结论）。

---

*生成时间：2026-07-11 · 本文为「项目目录方案」文档，不含任何代码改动。*
