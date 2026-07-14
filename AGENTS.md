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
| `docs/Skills/` | **本地化 Agent 技能/角色库**（superpowers-zh / agency-agents-zh / ui-ux-pro-max） | 纯 `SKILL.md`/`Markdown`，CodeBuddy 纯对话调用，详见「SAWORKFLOW 操作方法论」 |
| `.codebuddy/` | **CodeBuddy IDE 配置层** — Skills / Agents / Rules / Memory | 详见下方「CodeBuddy 配置层」 |

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
| `evaluation.py` | **5 维度验收**：事实/完整/结构/风格/去AI味，通用线 75，研究-写作阶段可传入 90 严格验收 | 被 `write_stage` 调用 ✅ |
| `ai_writer.py` | AI 写作核心 `AIWriter`，`_call_ai()` 调用模式 | `llm_client.py` 对齐此模式 |
| `models.py` | 数据模型 `ContentType` / `ContentStyle` 等 | 机器可读契约来源 |
| `publisher_service.py` | 发布服务 | — |
| `config.py` / `main.py` | 配置 / 入口 | — |
| `prompts/` | 10 个 prompt 模板 | — |
| `fact_pipeline.py` | **Claim-Pipeline 三阶段事实锚定**（B-2）：提取→验证→合并，零 LLM 依赖注入 | 待接入 `write_stage`，详见 `docs/plans/2026-07-13-fact-hallucination-plan.md` |
| `STYLE_GUIDE_MILITARY.md` | 军事风风格指南 | — |

---

## 生产流水线 ↔ 文件映射

```
下载   → lib/video-batch-download-main/        (视频批量下载)
转录   → lib/sensevoice-asr/ + _test_*.py       (ASR 语音转文字)
研究写作→ lib/toutiao-auto-publisher/backend/
           research.py ──search_web──▶ agent/search_engine.py
           write_stage.py ──WorkingMemory──▶ agent/memory.py
                          └─evaluate_content─▶ evaluation.py (5维/通用阈值75，研究写作专用80)

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
| 验收 `evaluation` | ✅ 已接 | 5 维度 + 通用阈值 75，研究-写作阶段可传 80 |
| 护栏 `guardrails` | ✅ 已接 | `write_stage` 输入/输出/人工化接入三层护栏 |
| 通用编排 `AgentGraph`/`Runner` | ⚠ 未接 | `write_stage` 自带循环，两套自愈并存 |

> 结论：Harness 六组件中 **5 项已在生产运行**（记忆 / 搜索 / 自愈 / 验收 / 护栏），仅余「通用编排 `AgentGraph`/`Runner` 未接」（`write_stage` 自带循环，两套自愈并存）与「观测未结构化」两项缺口。

---

## 开发约束（指针式）

1. **改生产逻辑**优先改 `lib/toutiao-auto-publisher/backend/`，尤其 `write_stage.py` / `research.py` / `evaluation.py`。
2. **`agent/` 是框架层**，改动需保持与 OpenAI Agents SDK / LangGraph API 对齐（各文件头部标注了参考源码）。
3. **护栏改动不会自动生效**——`guardrails.py` 仅定义框架，`write_stage` 需新增调用点才接入生产。
4. **验收标准以 `evaluation.py` 为准**（5 维 + 通用阈值 75 / 研究-写作阶段 80），不要另起炉灶。
5. **新增 ASR 验证脚本**应归入 `lib/sensevoice-asr/`，避免散落根目录。
6. 规格化契约优先复用 `models.py` 的 `ContentType` / `ContentStyle`，而非新建类型。
7. **改网页 UI（`engine_app.py`）**前先查 `docs/WEB_REVIEW.md`（评审基线 + 技能选型结论）。

---

## SAWORKFLOW 操作方法论（superpowers 规划 + agency-agents 执行）

> 已评估可行（2026-07-12，零程序改动）。将外部技能/角色库作为「方法论 + 人力资源」接入本引擎的对话式工作流，实现"专业的人做专业的事"。

> ⚠️ **命名澄清（2026-07-12）**：本「SAWORKFLOW」**不是** CodeBuddy 规则 `agentic-workflow.mdc` 中的 "Agentic Workflow"。二者是两套独立流程，切勿混淆：
> - **SAWORKFLOW** = 本项目专项方法论 = superpowers-zh（规划/审查）+ agency-agents-zh（分角色执行），即本节内容。
> - **Agentic Workflow**（`agentic-workflow.mdc`）= 吴恩达（Andrew Ng）提出的通用 Agentic Workflow 流程，**独立保留、不做更改**。
> 任务执行按本 SAWORKFLOW 走；涉及通用反思/迭代机制时可参考 `.mdc`，但两者的术语体系不混用（SAWORKFLOW 用 Micro/Sprint/Full + evaluation.py@75；`.mdc` 用 Tier 1/2/3 + 反思评分@80）。

### 三层拼装
- **控制平面（HOW · 规划/审查）**：`docs/Skills/superpowers-zh-main/`（superpowers 中文增强版，20 个 `SKILL.md` 技能：brainstorming / writing-plans / requesting-code-review / verification-before-completion / subagent-driven-development / workflow-runner 等）。负责工作/任务/方案划分与确认、审查。
- **人力资源（WHO · 执行）**：`docs/Skills/agency-agents-zh-main/`（266 中文角色 / 20 部门，含抖音/小红书/微信/头条等中国市场智能体）。按总体方案分角色执行。
- **质量门**：本引擎 `evaluation.py`（5 维 / 通用阈值 75，研究-写作阶段 80）+ `write_stage` 自愈闭环（替代 superpowers 的 Reality Checker / TDD 终裁）。

### 两阶段协议（CodeBuddy 纯对话执行，不跑任何 install 脚本）
- **Phase A 规划（superpowers 主导）**：读 `brainstorming`+`writing-plans`+`requesting-code-review`（可选 `workflow-runner`），对任务做 HARD-GATE 共识 → 产出结构化「总体方案」（阶段→任务拆分→每任务指派 agency 角色→每任务验收标准→检查点）→ 方案自检。落盘 `docs/plans/<日期>-<任务>-plan.md`，并写入 `.codebuddy/memory/`。
- **Phase B 执行（agency-agents 主导）**：依据总体方案，对每项任务读对应 `agency-agents-zh-main/<角色>.md` 并采用其设定执行；完成后用 `evaluation.py`+`write_stage` 做质量门，不通过打回（≤3 次）。可借主 agent 的 `Task` 子代理工具为各角色任务并行派发。

### 触发方式（用户侧 vs Agent 侧，关键修正）
> **用户不是专家、不必会挑角色/阶段/质量门。** 正确分工：用户只说"人话"任务，规划与角色指派由 Agent 自动完成。

- **用户只需发自然语言任务指令**（无需任何特殊格式），例如：
  `优化页面UI` / `本期头条选题并成稿` / `给稿子配图` / `修复 Streamlit 弃用告警` / `排查 transformers 报错` 。
  - **凡是「项目相关更改」或「专业性问题」→ 一律进入 workflow**（不分内容生产 / 代码 / 运维 / 排障）。这是统一铁律，无例外。
  - 唯一不进 workflow 的：纯闲聊、纯常识问答（与项目无关、无需规划/角色/质量门）。
  - ⚠️ 边界修正（2026-07-12，用户指示推翻"仅内容生产"误判）：代码/工程任务同样适用，且因可真跑验证，质量门比内容更硬。
- **`[NEXUS-<模式>]` 模板是 Agent 的「内部执行契约」**，不是用户输入格式。Agent 收到自然语言任务后，**自行**翻译成该模板并在执行过程中向用户透明展示（让用户看见"我正在用哪个角色、走哪阶段、过哪道质量门"），用户无需填写。

### Agent 内部执行契约（透明展示用，用户不必填）
```
[NEXUS-<Micro/Sprint/Full>] <规划|执行>阶段：<superpowers 技能 或 agency 角色.md> 作为 <角色名>，
执行 <任务>，按 phase-[X]..phase-[Y]，质量门=evaluation.py(通用75/研究写作80)+write_stage，交接写 .codebuddy/memory/。
```
- 前缀 `[NEXUS-模式]` 由 Agent 自动判定（单任务=Micro / 功能MVP=Sprint / 完整产品=Full）；角色=`.md 路径`+角色名由 Agent 依总体方案指派；纪律=superpowers；质量门=本引擎验收。

### 风险与缓解（对话环境下）
1. 编码语境错配 → 概念转译（代码/单测→内容稿/evaluation.py；git 检查点→deliverable+.codebuddy/memory/）。
2. 人格膨胀 → 后端确定性阶段去人格，仅写作/配图创意阶段保留角色人格。
3. 纪律靠 Agent 自主维持 → 收到自然语言任务即自动进入 `[NEXUS-模式]` 并执行两阶段协议，用户无需手动触发。
4. 验收门级别 → 内容任务用推理级（真出内容时调本项目真实流水线）；**代码/工程任务用真跑实测级**（`py_compile`+`lint`+起服务看日志），比内容更硬、可客观判定。

### 代码/工程任务的角色映射与质量门（2026-07-12 边界修正）
> 旧边界误将 workflow 限缩于"内容生产"，已推翻：代码改动、运维配置、报错诊断等专业技术任务一律走 workflow；因可真跑验证，质量门比内容更硬。

- **角色映射**（路径相对 `docs/Skills/agency-agents-zh-main/`）：
  - 前端/UI/Streamlit：`engineering/engineering-frontend-developer.md`
  - 报错诊断/排障：`engineering/engineering-incident-response-commander.md`
  - 最小改动纪律：`engineering/engineering-minimal-change-engineer.md`
  - 代码审查质量门：`engineering/engineering-code-reviewer.md`
  - 运维/启动配置：`engineering/engineering-devops-automator.md` / `engineering/engineering-sre.md`
  - 架构决策：`engineering/engineering-software-architect.md` / `engineering/engineering-backend-architect.md`
  - 提交规范：`engineering/engineering-git-workflow-master.md`
- **superpowers 工程技能**：`brainstorming`(HARD-GATE 澄清影响面) / `writing-plans`(Sprint/Full 落 docs/plans) / `requesting-code-review`(交 code-reviewer 走查) / `verification-before-completion`(**py_compile + lint + 真跑实测**，可执行的必须实测) / `subagent-driven-development`(复杂改动派子代理)。
- **质量门（代码任务）**：① 硬门 `py_compile` + `read_lints`；② `engineering-code-reviewer` 角色走查；③ 涉及内容产出时仍过 `evaluation.py`(5维/通用75/研究写作80)+`write_stage`；④ 可真跑的必须实测（如起 Streamlit 看日志确认告警消失）。
- **模式轻量化**：单点修复用 `[NEXUS-Micro]`（诊断→列方案→用户拍板→改→验证，不强制写长文档）；功能级 `[NEXUS-Sprint]`；产品/架构级 `[NEXUS-Full]`。

### 接入约定
- CodeBuddy 不在 superpowers/agency 官方支持清单，但其技能均为 `SKILL.md`/`Markdown` → **原生兼容**，走「纯对话读 SKILL.md」或「复制到 `.codebuddy/skills/` 常驻」；**绝不执行其 install/convert 脚本**（会改写 `~/.claude` 等外部目录）。

---

## `.codebuddy/` 配置层

> CodeBuddy IDE 原生的项目配置层，AI 在每次对话中自动加载。详见 `docs/CodeBuddy/` 完整知识库。

| 路径 | 类型 | 职责 | 状态 |
|------|------|------|------|
| `.codebuddy/skills/ui-ux-pro-max/` | Skill | UI/UX 设计智能库 — 67 种风格 / 161 套配色 / 57 组字体 / 99 条 UX 指南 / 22 个技术栈，含 BM25 搜索脚本 | ✅ 已安装 (2026-07-13) |
| `.codebuddy/agents/ui-designer.md` | Subagent (manual) | Streamlit UI 设计师 — 专注本项目的界面设计/优化/审查，引用 ui-ux-pro-max Skill | ✅ 已创建 (2026-07-13) |
| `.codebuddy/rules/MAP.mdc` | Rule | 历史规则（`agentic-workflow.mdc` 等），按 `.mdc` 扩展名自动加载 | ✅ 已有 |
| `.codebuddy/memory/` | Working Memory | 跨会话持久化记忆（`MEMORY.md` + 每日 `YYYY-MM-DD.md`） | ✅ 运行中 |

### Skill vs Agent 关系

- **Skill** = "会什么" — 知识/流程/脚本，被动加载，可被主 Agent 或 Subagent 调用
- **Subagent** = "谁来做" — 独立 AI 角色，有独立上下文 + 独立 Tools 权限
- **绑定方式**：Subagent 的 System Prompt 中引用 Skill（如 `ui-designer` 引用 `ui-ux-pro-max`）

### 知识注入层级

```
L1 始终层  →  AGENTS.md + alwaysApply Rules
L2 按需层  →  agentic request Rules + Skills (SKILL.md)
L3 主动层  →  @Docs / @Files / @Git / MCP
L4 记忆层  →  Memory (IDE管理) + Working Memory (.codebuddy/memory/)
L5 网络层  →  web_search / web_fetch（兜底）
```

---

## `docs/CodeBuddy/` — CodeBuddy 产品知识库

> 2026-07-13 从官方文档完整抓取，共 14 个文件。本目录持续作为项目对 CodeBuddy IDE 能力的权威参考。

### 文档地图

| 文件 | 内容 | 关键价值 |
|------|------|---------|
| `产品介绍` | IDE/插件/CLI 三形态、全流程 AI 驱动、Figma 转代码 | 产品边界 |
| `入门指南` | 安装登录、快速开始、环境要求 | 新手入口 |
| `使用指南_核心功能` | 代码补全、内联对话、斜杠指令、上下文（@）、规则、检查点、历史、记忆 | 日常开发 |
| `使用指南_进阶功能` | MCP、集成配置（Supabase/CloudBase）、预览、部署（4种平台）、智能提交 | 能力扩展 |
| `使用指南_智能体模式` | Agent 概览、任务创建/管理/对话/结果查看、Figma 集成 | Agent 核心 |
| `平台接入与高级功能` | **微信 ClawBot 接入**、models.json 自定义模型、**Plan 模式**（5步生命周期）、**Subagents**（agentic/manual）、**Skills**（SKILL.md+三级加载）、**Hooks**（7个事件+5个实战示例） | 进阶能力 |
| `用户指南` | 浓缩版：3种模式+5项进阶特性+生态集成 | 速查卡片 |
| `账号与计费` | 4档定价（免费/标准99/高级199/旗舰999）、积分机制、退款规则 | 成本 |
| `支持` | 故障排除（SSH/Figma/MCP/终端/网络）、安全与隐私 | 排障 |
| `最佳实践` | 4层渐进学习路径（基础→进阶→工程→高级），含博客/Vibe Coding/Spec-Kit/CRM等实践案例 | 方法论 |
| `博客摘要` | 7 篇精选（Agent Team、Skills 效率、Craft 智能体实战、WorkBuddy 等）+ 版本演进时间线 | 社区 |
| `框架方案` | **四阶段闭环**（READ→ACT→REFLECT→WRITE）+ 6个 Subagent + Hooks 安全拦截 + Plan Mode | 工程框架 |
| `融合方案` | agentic-workflow.mdc 与四阶段框架融合，**Tier 1/2/3** 复杂度分级、**两层 LOOP**、**主动 QA 协议** | 工程方法论 |

### 与本项目的关键对照

| CodeBuddy 能力 | 本项目落地方式 | 状态 |
|---------------|-------------|------|
| Plan 模式（5步生命周期） | SAWORKFLOW Phase A→B 两阶段协议 | ✅ 方法论对等 |
| Subagents（agentic/manual） | `ui-designer` Subagent + SAWORKFLOW 角色分派 | ✅ 已创建首个 |
| Skills（SKILL.md） | `ui-ux-pro-max` Skill + superpowers-zh/agency-agents-zh | ✅ 首个已安装 |
| Hooks（7事件） | 待评估：可用于拦截危险操作（如误删 `.env`） | ⏳ 待配置 |
| Rules（三层） | `MAP.mdc`（agentic）+ `AGENTS.md`（always 等效） | ✅ 已有 |
| Memory | `.codebuddy/memory/MEMORY.md` + 每日 `YYYY-MM-DD.md` | ✅ 运行中 |
| Checkpoints | IDE 自动管理 | ✅ 自动 |

---

## 项目进度（SAWORKFLOW 批次）

> 按 SAWORKFLOW 复杂度分级推进，已完成项均经「执行→反思→验证」闭环。

| 批次 | 内容 | 状态 | 提交 |
|---|---|---|---|
| 批次 A | 文档体系（AGENTS.md + specs + 网页评审 WEB_REVIEW） | ✅ 完成 | `5961330` |
| E-1 | 网页快速修复（9 项：C5 文案 / C6 日志 / C9 spinner / E13 图标 / E14 空状态） | ✅ 完成 | 早前提交 |
| 批次 B | 护栏接线（Input/Policy/Output 三层接入 `write_stage`） | ✅ 完成 | `5c1b643` |
| D11+C8 | CSS 颜色 token 化（`:root` 变量替换 16 处硬编码）+ 响应式 `@media` 断点 | ✅ 完成 | `5c1b643` |
| **E-2** | **写作风格切换**：屏蔽 military/sharp/data/flash/discussion，接入 `docs/风格分析` 4 位作者（包明说默认+晋说+全球档案馆+听风的蚕），新增 3 prompt 模块并复用 `_red_lines` 红线 | ✅ 完成 | `4f944b6` |
| **网页UI重设计** | **Track1 三Tab分区（运行监控/成果展示/配置）+ Track2 token补全/卡片阴影/阶段连接线/质检`st.dataframe`整宽 + Track3 首启`st.status`/fragment局部刷新防闪 + 浅色主题切换**（`engine_app.py` UI 层，零生产逻辑改动，零新增依赖） | ✅ 完成 | ⚠ 未提交 |
| **方法论落地** | **SAWORKFLOW 操作方法论**：superpowers-zh 规划/review + agency-agents-zh 分角色执行，两阶段协议 + 标准 `[NEXUS-]` 模板 + 质量门(evaluation.py+write_stage)，纯对话零程序改动 | ✅ 完成 | ⚠ 未提交 |
| **Agnes 配图接入** | **Agnes Image 2.0 Flash 替换 Pollinations**：`engine_app.py` 配图链路全切中文 prompt + Agnes API，文件大小提升 25–30 倍（~1.5 MB vs ~50 KB），中文 prompt 体系 ERNIE 优化，配置面板新增 Agnes 三项 | ✅ 完成 | ⚠ 未提交 |
| **CodeBuddy配置** | **Skill + Agent 落地**：`ui-ux-pro-max` Skill（67风格/161配色/BM25搜索）→ `.codebuddy/skills/`，`ui-designer` Subagent → `.codebuddy/agents/`，AGENTS.md 补入 `.codebuddy/` + `docs/CodeBuddy/` 两章 | ✅ 完成 | ⚠ 未提交 |
| **G-1** | **全球档案馆风格 Prompt 修复**：文体错位修正（分析评论体→场景代入叙事体）+ 章节电影感 + 金句多样性。Layer A (`global_archive.py` 5处) + Layer B (`humanize.py` 3处)，~60行，零生产逻辑变更 | ✅ 完成 (2026-07-14) | ⚠ 未提交 |
| E-3 | 包级拆分（`engine_app.py` 1899 行 → `ui/` 模块），Tier 3 需先出 Plan | ⏳ 待规划 | — |
| **B-2** | **Claim-Pipeline 事实锚定**：三阶段流水线（提取→验证→合并）根治事实幻觉，`fact_pipeline.py` 已产出，待接入 `write_stage` 迭代闭环 | ⏳ 模块就绪，待接入 | ⚠ 未提交 |
| 批次 C | `graph.py` 通用编排决策（AgentGraph/Runner 接入生产循环） | ⏳ 待立项 | — |
| 批次 D | 内容选题变现（`scripts/` + `docs/` 研究产出 review 后提交） | ⏳ 待评审 | 本批次提交 |
| **tests/ 阶段测试入口** | **各阶段功能测试框架**：`tests/run_stage.py`（`--stage 1|2|3|4|5`）+ `tests/_harness.py`（streamlit stub 注入后 import engine_app），直接调用项目真实函数做功能测试（非 LLM 模拟）；S3/S4/S5 已真跑实测通过，S2 因 torch/funasr 环境冲突待修 | ✅ 完成 (2026-07-14) | 本批次提交 |

> ✅ **提交状态（2026-07-14）**：自 `4f944b6` 以来累积的 **17 个 modified + 15 个 untracked** 已统一提交到 `master`，覆盖网页UI重设计 / Agnes配图 / CodeBuddy配置 / 全球档案馆G-1 / Claim-Pipeline(B-2) / SAWORKFLOW方法论 / tests阶段测试入口 等批次；批次 D（`scripts/`+`docs/采集`+`docs/风格分析`）一并入库，留待后续 review。

**随本次提交入库的内容**：
- `scripts/`（4 py：analyze_style / curate_corpus / synthesize_style / toutiao_collect）
- `docs/采集/`（85 md）、`docs/风格分析/`（46 文件）—— 内容研究产出；其中 `风格分析/` 已落地为 E-2 的生产风格系统（包明说/晋说/全球档案馆/听风的蚕）
- `docs/plans/`（4 份方案：知识库接入 / 配图 LLM prompt / UI 优化 / 事实幻觉 Claim-Pipeline）
- `docs/网页优化/`、`docs/网页UI优化方案/` — UI 重设计相关分析文档
- `docs/Skills/`（superpowers-zh / agency-agents-zh / ui-ux-pro-max）— 本地技能库
- `docs/CodeBuddy/`（14 文件）— CodeBuddy 产品知识库
- `docs/agentic-workflow.md` / `docs/role_agent_frameworks.md` / `docs/superpowers_review.md` / `docs/superpowers_x_agency.md` — 框架调研笔记
- `tests/`（3 文件：`__init__.py` / `_harness.py` / `run_stage.py`）— 各阶段功能测试入口（直接调项目真实函数，非 LLM 模拟）

---

*最后更新：2026-07-14 · 新增 tests/ 阶段测试入口批次并实跑验证（S3/S4/S5 PASS，S2 待 torch/funasr 环境修复）；将自 4f944b6 以来累积的 17 modified + 15 untracked 统一提交 master。*
