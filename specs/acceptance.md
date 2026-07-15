# specs/acceptance.md — 内容质量验收标准

> 权威源：`lib/toutiao-auto-publisher/backend/evaluation.py`
> 本文是将代码中的验收逻辑「文档化」为正式标准，**禁止在别处另立验收**。
> 流水线与状态契约见 `pipeline.md`。

---

## 1. 权威函数

```python
evaluate_content(content: str, title: str, style: str, research_context: str = "") -> dict
```

- 调用方式：经 `AIWriter._call_ai`（DeepSeek），`temperature=0.1`，`max_tokens=500`
- 纯逻辑、无 UI 依赖（仅写 stderr）

---

## 2. 五个验收维度（每项满分 100）

| 维度 | 含义 | 校验要点 |
|---|---|---|
| 事实准确 | 与已知事实一致，无明显编造 | 结合 `research_context` 比对 |
| 信息完整 | 覆盖人物 / 事件 / 原因 / 影响 | 关键点无遗漏 |
| 结构清晰 | 段落分明、逻辑连贯、易读 | — |
| 风格一致 | 符合指定写作风格 | 对比 `style` 参数（`ContentStyle` 中文标签） |
| 去AI味 | 像真人写作，无机器腔 | — |

---

## 3. 通过算法（代码即标准）

1. 综合分 `score` = 5 项维度分的平均值（整数）
2. **通用通过条件（默认）**：
   - `score >= QUALITY_PASS_THRESHOLD`（= **75**）
   - 且 5 个维度中**任意一个不低于 50**
   - **事实准确性硬门槛**：`FACT_HARD_FLOOR = 80`（`evaluation.py:10`），事实准确性维度低于此值直接判不通过，不受通用阈值 75 影响
3. **研究-写作阶段专用条件**：
   - `write_stage.py` 调用 `evaluate_content(..., threshold=80)`，要求 `score >= 80`
   - 且 5 个维度中**任意一个不低于 50**
   - 若迭代结束后最佳分仍低于 80，研究-写作阶段判为失败，流水线中止
4. 否则 `passed = False`（触发重写 / 迭代）

> 源码常量：
> - 通用通过线：`evaluation.py:9` → `QUALITY_PASS_THRESHOLD = 75`
> - 事实硬门槛：`evaluation.py:10` → `FACT_HARD_FLOOR = 80`
> - 研究-写作专用线：`write_stage.py:25` → `RESEARCH_WRITE_PASS_THRESHOLD = 80`
> - 单维下限：`evaluation.py:133` → `if any(v < 50 for v in dimensions.values()): passed = False`

---

## 4. 输出契约（返回值 dict）

| 字段 | 类型 | 说明 |
|---|---|---|
| `score` | int | 综合分 0-100 |
| `feedback` | str | 一句话优劣总结与改进建议 |
| `passed` | bool | 是否通过 |
| `dimensions` | dict | `{"事实准确","信息完整","结构清晰","风格一致","去AI味": int}` |

---

## 5. 解析降级策略（健壮性）

评估输出优先 XML 标签解析；失败按以下顺序降级：

1. **XML 解析**：`<evaluation>` / `<score>` / `<dimensions>` / `<feedback>`
2. **JSON 解析**：兼容旧格式
3. **规则判断**：无反馈时 `content > 100` 字判 `PASS`，否则 `FAIL`，`score = 50`
4. **模块异常**：返回 `passed=False, score=0, 维度全 0`（不再默认放行，由流水线自愈机制接管重试）

---

## 6. 与风格系统的关系

- `style` 参数来自 `state.content_style`，经 `models.style_label()` 转为中文标签
- 「风格一致」维度针对该标签校验；**新增风格须在 `models.ContentStyle` 登记**

---

## 7. 使用约束

1. 验收以**本文件 + `evaluation.py`** 为唯一权威，禁止在业务代码中硬编码另一套阈值。
2. 通用阈值 **75**、研究-写作阈值 **80**、单维下限 **50** 的修改必须经评审，并同步更新本文件。
3. 写作循环（`write_stage.research_and_write`）以 `passed` 作为迭代停止条件，直到 `PASS` 或达到 `MAX_RESEARCH_ITERATIONS`。研究-写作阶段若迭代结束最佳分仍低于 80，阶段判失败、流水线中止。
4. **事实边界机制（2026-07-13 新增，V2 升级）**：
   - **系统级（V2 核心）**：`ai_writer.py` `_FACT_BOUNDARY_SYSTEM` 常量在 `generate_toutie()` / `generate_article()` 中注入 system prompt 前缀（6 条规则，优先级高于风格指令），从 LLM 指令优先层根除编造冲动。
   - **用户层（V1 保留，已精简）**：`write_stage.py` 话题前缀 `_FACT_BOUNDARY_INSTRUCTION`（一行提醒），第 2 轮起如上一轮事实准确 < 85 额外注入 `_build_fact_fix_block()`（针对性矫正）。
   - 评估使用累积研究上下文（最近 3 轮），而非仅首轮。

---

## 8. Claim-Pipeline 模式（2026-07-13 新增，B-2）

### 8.1 架构

四阶段事实锚定流水线，根治 LLM 编造事实（幻觉）：
1. **阶段 1 Extract**（`fact_pipeline.extract_claims`）：从搜索资料 + 视频摘要提取原子事实声明
2. **阶段 2 Ground**（`fact_pipeline.verify_claims`）：逐条比对来源验证（CONFIRMED/PARTIAL/UNVERIFIED）
3. **阶段 2.5 Merge**（`fact_pipeline.merge_claims`）：跨迭代声明合并去重（规则引擎，零 LLM）
4. **阶段 3 Compose**（`AIWriter.compose_from_claims`）：从已验证声明池写作
5. **阶段 4 Evaluate**（`evaluate_content`）：质量评估，注入声明池摘要

### 8.2 关键常量

| 常量 | 值 | 位置 | 说明 |
|---|---|---|---|
| `CLAIM_PIPELINE_ENABLED` | `False`（默认） | `write_stage.py` | 开发完成后改为 `True` |
| `_CP_MAX_ITERATIONS` | `5` | `write_stage.py` | Claim-Pipeline 模式最大迭代轮数 |
| `_CP_MIN_COVERAGE` | `0.7` | `write_stage.py` | 进入 Compose 阶段的最低来源覆盖率 |
| `_CP_MAX_EMPTY_SEARCHES` | `3` | `write_stage.py` | 连续空搜索结果数上限（触发降级） |

### 8.3 评估增强

- `evaluate_content()` 新增 `claims_pool_summary` 参数
- 声明池摘要注入评估 prompt：「有声明未用」→ 完整性扣分，「无声明编造」→ 事实准确严重扣分（≤60）
- 参考背景资料截断从 800 → 1500 字

### 8.4 降级路径

| 场景 | 触发条件 | 策略 |
|---|---|---|
| 阶段 1 空声明 | `extract_claims()` 返回 0 条 | → V2 模式（单次 `generate_toutie`）+ 质量门 85 |
| 覆盖率极低 | 连续 2 轮 < 50% | → 已有声明 Compose + 全部标注不确定性 + 质量门 85 |
| 搜索限流 | 连续 3 次 `search_web()` 返回空 | → 降级 Compose + 质量门 85 |

### 8.5 `fact_pipeline.py` 测试方法

```python
# 纯逻辑函数，可直接单测（无需 LLM / API）
from fact_pipeline import merge_claims, VerifiedClaim, ClaimsPool

v1 = VerifiedClaim(id=1, status="CONFIRMED", text="声明A", source_quote="...", source_label="[搜索: x]")
v2 = VerifiedClaim(id=2, status="PARTIAL", text="声明B", source_quote="...", source_label="[搜索: y]")
pool = merge_claims([v1, v2], None)
assert pool.coverage == 1.0
assert len(pool.confirmed) == 1
assert len(pool.partial) == 1
```

### 8.6 WorkingMemory 扩展

- 新增 `unverified_claims: list[str]` — 记录未验证声明 ID
- 新增 `knowledge_gaps: list[str]` — 记录事实缺口方向
- `to_prompt()` 自动格式化上述信息（零破坏性改动）
