# 网页默认值 + 阶段三阈值调整方案

> 方案日期：2026-07-14 · 模式：[NEXUS-Sprint] · 状态：📋 方案已产出，待审批执行
> 智能体分工：multi-agent-architect（阶段三架构评估）+ ui-minimal-change（UI 影响面走查）
> 质量门：py_compile + lint + 真跑实测

---

## 一、需求概述

| # | 需求 | 规则 |
|---|------|------|
| D1 | 流程按钮默认执行全流程，不分步 | 选"组装"为默认值，连续执行到底 |
| D2 | 默认为文章 | content_type 默认从 toutie → article |
| D3 | 默认为包明说 | **已满足**（当前默认即 baoming_shuo） |
| D4 | 默认打开 Cookie | toggle 默认从 False → True |
| D5 | 阶段三轮数 10→3，取最高分，不超 80 也不中断 | 改 MAX_RESEARCH_ITERATIONS + 去掉中断逻辑 + 增加质量警告 |

---

## 二、变更明细

### 2.1 UI 层改动（`engine_app.py`，共 ~10 行）

#### D1：流程模式默认全流程

| 项目 | 内容 |
|------|------|
| 文件 | `engine_app.py` |
| 位置 | L1740–1753 |
| 当前 | `st.selectbox` options 第一项 `("全部", "全部阶段（分步执行）")` → `step_mode=True`（分步暂停） |
| 改为 | options 第一项 `("assemble", "组装（输出完整稿件）")` → `step_mode=False`（连续执行到底） |
| 实现 | 调整 options 列表顺序（`st.selectbox` 默认选中第一个） |
| help 同步 | 更新为 `"选「全部」为分步执行，选具体阶段则连续执行到该阶段即停"` |

```python
# 调整后
stop_at = st.selectbox(
    "执行到阶段",
    options=[
        ("assemble", "组装（输出完整稿件）"),       # ← 新默认
        ("全部", "全部阶段（分步执行）"),
        ("download", "下载"),
        ("transcribe", "转录"),
        ("write", "研究写作"),
        ("generate_images", "配图"),
    ],
    ...
)
```

| 影响链路 | 说明 |
|----------|------|
| `stop_at="assemble"` → `step_mode=False` | `_run_stages` L1551 判断：stop_at ≠ "全部" → step_mode=False → 连续执行 |
| `st.session_state.sidebar_stop_at` | Streamlit 持久化；已访问过的老用户不受影响（旧值在 session_state） |
| `stage_event.wait()` / `awaiting_next` | step_mode=False 时不触发，各阶段自动流转 |
| `break` 时机 | L1570–1572：到达 assemble 阶段完成后 break，即走完全流程 |

#### D2：默认内容类型"文章"

| 项目 | 内容 |
|------|------|
| 文件 | `engine_app.py` |
| 位置 | L1716–1722 |
| 当前 | `st.radio` 无 `index` 参数，默认 `index=0`（微头条） |
| 改为 | 加 `index=1`（文章） |
| 改动量 | +1 行 |

```python
content_type = st.radio(
    "内容类型",
    options=[("toutie", "微头条"), ("article", "文章")],
    format_func=lambda x: x[1],
    horizontal=True,
    index=1,                      # ← 新增
    key="sidebar_content_type",
)
```

| 影响 | 说明 |
|------|------|
| `state.content_type="article"` | 传入 `write_stage.py`，触发 L897–902 的 article 分支 |
| 字数上限 | 1200 → 2000 字符（更长输出） |
| 风格传递 | article 模式下 `content_style=None`（不传风格参数） |
| `PipelineState` 默认值 | L330 `content_type="toutie"` 不动（运行时从 UI 显式传入） |

#### D3：默认"包明说" — 无需改动

当前 `st.selectbox` 默认即 `"baoming_shuo"`。`PipelineState.__init__` 默认也是 `content_style="baoming_shuo"`。✅

#### D4：默认打开 Cookie

| 项目 | 内容 |
|------|------|
| 文件 | `engine_app.py` |
| 位置 | L1727–1728 |
| 当前 | `st.toggle("🍪 浏览器 Cookie", value=False, ...)` |
| 改为 | `value=True` |
| 改动量 | 1 字符 |

```python
use_browser_cookies = st.toggle("🍪 浏览器 Cookie", value=True,
    help="允许 yt-dlp 从 Chrome 浏览器提取 Cookie 用于抖音下载（仅下载阶段生效）")
```

| 影响 | 说明 |
|------|------|
| yt-dlp `cookiesfrombrowser` | L670 读取该值，无 Chrome / 无 Cookie 时 yt-dlp 静默 fallback，不会崩溃 |
| 风险 | 极低 — yt-dlp 对 cookiesfrombrowser 失败有内置降级 |

---

### 2.2 阶段三改动（`write_stage.py`，共 ~15 行）

#### D5：轮数 10→3 + 去掉 80 分中断 + 最高分策略 + 质量警告

受影响位置：

| 行号 | 当前内容 | 改动 |
|------|----------|------|
| **L25** | `MAX_RESEARCH_ITERATIONS = 10` | → `= 3` |
| **L298–309** | `if best_score < 80: return False`（中断流水线） | → 改为警告日志 + `quality_warning=True`，**不 return False** |
| **L712–715** | Claim-Pipeline 路径同样中断 | → 同步改为警告（保持两路径一致） |
| **L773–780** | `_fallback_v2_mode` 硬编码 `score >= 85` | → 引用统一常量或改为 `>= 80` |

##### D5-A：`MAX_RESEARCH_ITERATIONS`（L25）

```python
# 改动前
MAX_RESEARCH_ITERATIONS = 10

# 改动后
MAX_RESEARCH_ITERATIONS = 3
```

| 影响链 | 说明 |
|--------|------|
| L138 `WorkingMemory(max_iterations=3)` | 只影响 `to_prompt()` 中的 `进度: N/3` 显示，不影响存储 |
| L856 `for iteration in range(1, 4)` | 最多 3 轮循环 |
| L956–960 `best_score` 跟踪 | **取最高分**（已有逻辑，无需改动） |

##### D5-B：去掉 80 分中断（L298–309）

```python
# 改动前（L297–309）
    # 严格完成校验
    if best_score < RESEARCH_WRITE_PASS_THRESHOLD:
        log(
            f"❌ 研究-写作阶段未达标: 最佳评分 {best_score} < {RESEARCH_WRITE_PASS_THRESHOLD}，"
            f"阶段未完成，流水线中止",
            "error",
        )
        _sys.stderr.write(...)
        stage("研究写作", "failed")
        return False

    state.mark_done("write")
    stage("研究写作", "done")

# 改动后
    # 质量门：低于阈值警告但不中断流水线
    if best_score < RESEARCH_WRITE_PASS_THRESHOLD:
        log(
            f"⚠️ 研究-写作阶段评分偏低: 最佳评分 {best_score} < {RESEARCH_WRITE_PASS_THRESHOLD}，"
            f"已标记质量警告，继续流水线",
            "warning",
        )
        state.outputs["quality_warning"] = True  # 在最终输出文件头部展示警告
        _sys.stderr.write(
            f"[loop] quality_warning: best_score={best_score} < "
            f"threshold={RESEARCH_WRITE_PASS_THRESHOLD}\n"
        ); _sys.stderr.flush()

    state.mark_done("write")
    stage("研究写作", "done")
    if best_score < RESEARCH_WRITE_PASS_THRESHOLD:
        stage("研究写作", "done_warning")  # 有警告但已完成
```

##### D5-C：Claim-Pipeline 路径同步（L712–715）

```python
# 同样逻辑：去掉 return False，改为警告 + quality_warning
```

##### D5-D：`_fallback_v2_mode` 硬编码 85（L773–780）

```python
# 改动前
if score >= 85 and ...:

# 改动后
if score >= RESEARCH_WRITE_PASS_THRESHOLD and ...:
```

##### D5-E：最终输出文件增加质量警告（`_save_outputs` L175–184 区域附近）

在写入 `_ai_raw.md` 时，若 `state.outputs.get("quality_warning")` 为 True，在文件头部追加：

```markdown
> ⚠️ **质量警告**：AI 综合评分 {best_score}/100（低于阈值 {RESEARCH_WRITE_PASS_THRESHOLD}）。
> 建议人工复核内容的事实准确性和表达质量。
```

##### D5-F：`_build_result()` / 成果展示增加警告展示（`engine_app.py`）

在成果 Tab 中，若 `quality_warning=True`，用 `st.warning()` 展示黄色警告横幅。

---

## 三、风险矩阵

| 风险 | 等级 | 说明 | 缓解 |
|------|------|------|------|
| 低质文流入终端 | 🔴 高 | 50–70 分文章将无阻拦进入配图/组装/发布 | D5-E 质量警告标记 + 落盘前文件头部警告 |
| 3 轮迭代不够收敛 | 🟡 中 | 复杂话题（财经/法律）评分可能来不及提升 | 观察达标率趋势，必要时回退到 5 轮 |
| 两路径行为不一致 | 🟡 中 | V2 去掉中断但 CP 保留会不一致 | D5-C 同步去除 CP 路径中断 |
| 老用户 session_state 覆盖新默认 | 🟢 低 | Streamlit 持久化设计，已访问过的老用户不受 D1/D2 影响 | 新用户立即生效，老用户可手动切换 |
| D2 article 不传 content_style | 🟢 低 | `article` 模式下 `cs=None`，不影响输出质量 | 评估维度不含风格维度 |

---

## 四、非目标（明确不做）

| 事项 | 原因 |
|------|------|
| 改 `PipelineState` L330 默认值 | 运行时总是从 UI 传入，非流水线路径（`tests/`）不受影响 |
| D10 包级拆分 | 独立 Tier 3 任务，不混入本 Sprint |
| 重命名 `stop_at` 语义 | 破坏性变更，需独立 PR |
| 改 `evaluation.py` 的 `FACT_HARD_FLOOR` | 独立的事实护栏，与本次无关 |

---

## 五、执行计划

### 阶段 1：UI 层改动（ui-minimal-change 执行）

| 步骤 | 内容 | 文件 | 改动量 |
|------|------|------|--------|
| 1.1 | D1: options 顺序调整 | `engine_app.py` L1742–1749 | ~8 行 |
| 1.2 | D2: `st.radio` 加 `index=1` | `engine_app.py` L1716–1722 | +1 行 |
| 1.3 | D4: toggle `value=True` | `engine_app.py` L1727 | 1 字符 |

### 阶段 2：阶段三改动（需 full understanding of pipeline）

| 步骤 | 内容 | 文件 | 改动量 |
|------|------|------|--------|
| 2.1 | D5-A: `MAX_RESEARCH_ITERATIONS=3` | `write_stage.py` L25 | 1 字符 |
| 2.2 | D5-B: L298–309 中断→警告 | `write_stage.py` | ~8 行重构 |
| 2.3 | D5-C: CP 路径 L712–715 同步 | `write_stage.py` | ~5 行重构 |
| 2.4 | D5-D: `_fallback_v2_mode` 硬编码 85→常量 | `write_stage.py` L773 | 1 行 |
| 2.5 | D5-E: `_save_outputs` 增加质量警告标记 | `write_stage.py` | ~5 行 |
| 2.6 | D5-F: `_build_result` 增加 `st.warning` | `engine_app.py` | ~3 行 |

### 质量门

- `py_compile engine_app.py` + `py_compile write_stage.py`
- `read_lints` 两个文件
- 真跑测试：`tests/run_stage.py --stage 3` 确认 3 轮机制 + 低于 80 分不中断

---

## 六、智能体分工

| 角色 | 职责 | 状态 |
|------|------|------|
| `multi-agent-architect` | 阶段三架构风险评估 — L298 中断逻辑去留/两路径一致性/下游依赖/WorkingMemory 耦合 | ✅ 报告已产出 |
| `ui-minimal-change` | UI 默认值影响面走查 — 定位位置/影响链路/session_state 持久化/最小改动量 | ✅ 报告已产出 |
| `ui-frontend-developer` | 执行阶段 1：UI 层 3 项改动 | ⏳ 待审批后执行 |
| `writing-prompt-engineer` | 监督阶段 2：迭代轮数变更对写作质量的影响 | ⏳ 待审批后执行 |

---

*方案完成时间：2026-07-14 · 待审批后执行*
