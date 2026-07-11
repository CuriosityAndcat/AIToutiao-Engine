# specs/pipeline.md — 内容生产流水线契约

> 权威源：`lib/toutiao-auto-publisher/backend/` 各模块 + `engine_app.py`
> 本文描述「阶段级」与「函数级」输入-输出契约，供 AI 协作时定位与对接，不含实现。
> 验收标准见 `acceptance.md`；项目地图见 `AGENTS.md`。

---

## 1. 流水线概览（5 阶段）

| 阶段 | 编号 | 处理位置 | 输出落点 |
|---|---|---|---|
| 下载 | 0 | `lib/video-batch-download-main/` | 视频文件 → `engine_app` state |
| 转录 | 1 | `lib/sensevoice-asr/` + `_test_*.py` | `state.outputs.transcript_text` |
| 研究写作 | 2 | `backend/research.py` + `write_stage.py` | `state.outputs.content` / `title` + `eval_records` |
| 配图 | 3 | `prompts/` + `engine_app` 编排 | 封面/配图路径 |
| 组装发布 | 4 | `engine_app.py` + `publisher_service.py` | 平台发布结果 |

**编排入口**：`engine_app.py`（三通道 `add_log` 观测 + `log/` 落盘）。

---

## 2. 共享状态契约：PipelineState

模块间通过 `state` 对象传递（`research.py` / `write_stage.py` 共享同一结构）。

### `state.outputs`（dict）

| 字段 | 类型 | 方向 | 说明 |
|---|---|---|---|
| `video_title` | str | 入 | 视频标题 |
| `video_description` | str | 入 | 视频描述（无转录时回退拼接） |
| `transcript_text` | str | 入 | 阶段1 转录结果；研究写作主输入 |
| `content` | str | 出 | 最终正文（`write_stage` 写入） |
| `title` | str | 出 | 最终标题（`write_stage` 写入） |

### `state` 顶层字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `content_type` | `ContentType` | 见 `models.py`（`TOUTIE` / `ARTICLE`） |
| `content_style` | `ContentStyle` | 见 `models.py`（7 种风格枚举） |

---

## 3. 阶段级契约

### 阶段 2 研究写作（核心）

- **输入**：`state.outputs.transcript_text`（缺失时回退为 `video_title + video_description` 拼接）
- **处理**：`write_stage.research_and_write(state, hooks) -> bool`
  - 内部调用 `research.build_research_context` → `evaluation.evaluate_content`
  - 集成 `agent.memory.WorkingMemory` 跨轮反思累积
  - 最大轮数 `MAX_RESEARCH_ITERATIONS = 3`（源码 `write_stage.py:22`）
- **输出**：
  - 返回值 `bool`（成功 / 失败）
  - `state.outputs.content` / `title` 写入最终稿
  - 内部累积 `eval_records`（每轮评分）、`search_queries_by_iter`（每轮关键词，供 UI 展示）

### 其他阶段

- 阶段 0 / 1 / 3 / 4 入口在 `engine_app.py`，细节见各子项目文档（`sensevoice-asr` / `video-batch-download-main` / `wewrite-main`）。

---

## 4. 函数级接口契约（精确签名）

| 模块.函数 | 签名 | 返回 | 契约要点 |
|---|---|---|---|
| `research.search_web` | `(query: str, max_results: int = 5) -> str` | 聚合摘要文本 | 百度优先 → 搜狗回退 → 空串 |
| `research.extract_key_topics` | `(state) -> str` | 关键词串 | 从 `video_title` + `transcript_text` 提炼 |
| `research.build_research_context` | `(state, log_fn=print, progress_fn=None) -> str` | 研究上下文 | 调用 `search_web`；UI 副作用经 `log_fn`/`progress_fn` 注入 |
| `research.extract_refined_query` | `(content, feedback, state) -> str` | 精炼词 | 按评估反馈生成再搜索词 |
| `write_stage.PipelineHooks` | `dataclass(log_fn, stage_fn, progress_fn)` | — | 编排层与 UI 解耦钩子 |
| `write_stage.research_and_write` | `(state, hooks=None) -> bool` | 成功标志 | 主写作循环 |
| `evaluation.evaluate_content` | `(content, title, style, research_context="") -> dict` | 见 `acceptance.md` | 5 维验收 |

---

## 5. 对接约束

1. **纯逻辑可单测**：UI 副作用一律经 `log_fn` / `stage_fn` / `progress_fn` 注入（见 `PipelineHooks`），禁止直接依赖 Streamlit。
2. **唯一写作入口**：`research_and_write` 是写作主函数，不要旁路直调 `ai_writer`。
3. **统一状态传递**：用 `state.outputs` dict + `state` 顶层字段，不要新增全局大杂烩变量。
4. **风格一致**：以 `state.content_style`（`models.ContentStyle`）为准，与 `evaluate_content` 的 `style` 参数对齐。
