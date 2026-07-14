# 事实幻觉根除方案 — 从 Prompt 到 Pipeline

> **日期**：2026-07-13  
> **模式**：`[NEXUS-Sprint]`  
> **状态**：Phase B 执行完成 — B-1 止血 ✅ + B-2 Claim-Pipeline 核心开发 ✅（`py_compile`+`lint` 全通过）。`CLAIM_PIPELINE_ENABLED = False`（待实测验证后改为 `True`）。B-1.4 实测 + B-3 调优待执行。  
> **问题**：研究-写作阶段连续两次运行均无法突破 90 分门（88 分/10 轮 + 82 分/10 轮），LLM 持续编造来源中不存在的事实细节（具体日期、战术细节、数据等）

---

## 一、问题诊断（三次运行证据链）

### 运行 #1（2026-07-13 17:23，V1 用户层事实边界）
| 主题 | 最佳分 | 轮次 | 核心编造行为 |
|---|---|---|---|
| 美军 UFO 解密 | 88/100 | 第 3 轮（共 10 轮） | 编造"2026 年 5 月 8 日、5 月 22 日、6 月 12 日、7 月 10 日"等具体解密日期；编造"特朗普备战 2026 年大选"政治关联 |

- 事实准确分震荡：70→75→75→75→75→70→60→75→75→60，从未突破 80 硬门槛
- 精炼搜索逐轮劣化：`事实准确性硬伤` → `特朗普2026年大选备战` → `美国大选周期`（搜幻觉内容 → 搜到无关结果 → 下一轮继续编）

### 运行 #2（2026-07-13 17:39，V2 系统级事实边界）
| 主题 | 最佳分 | 轮次 | 核心编造行为 |
|---|---|---|---|
| AI 无人机战术 | 82/100 | 第 2/3/4/6/9 轮（共 10 轮） | 编造"120 辆伪装军车被 AI 无人机蜂群摧毁""俄军送奶车伪装被热成像锁定""AI 自由落体闪避拦截机""360 辆运输车一周团灭"等战术细节 |

- 事实准确分震荡：60→70→75→70→60→75→65→55→70→60，同样从未突破 80
- 精炼搜索同样劣化：`AI无人机蜂群战例` → `俄军送奶车战术来源` → `俄军伪装送奶车细节`（搜幻觉生成的内容）

### 关键发现

**V2（系统级事实边界）对 V1 无显著改善**：88 分 → 82 分（反而下降，因为军事话题搜索资料更薄）。

**死循环机制**：
```
编造事实 → 评估员发现 → 反馈含编造细节
→ extract_refined_query(feedback) → 搜"俄军送奶车伪装事件来源"
→ 搜不到真实来源（因为这件事根本没发生！）
→ LLM 拿不到新证据，换个方式继续编 → 下一轮评估再次发现 → ...
```

**V1/V2 的共性局限**：两者都是 prompt engineering——在同一 LLM 调用中要求"遵守事实"+"写出风格"，这是**结构性矛盾**，不是 prompt 措辞问题。

---

## 二、为什么 Prompt 方案不够（产业研究）

### 2.1 学术共识

| 研究 | 结论 |
|---|---|
| **LLM Hallucination Comprehensive Survey** (arxiv 2510.06265, 2026) | 幻觉根源贯穿 LLM 全生命周期（预训练→微调→推理），不能仅靠推理阶段的 prompt 解决 |
| **Zylos Research 2026** | 现代方法组合不确定性估计 + 自洽性检查 + 检索增强 + 实时护栏，幻觉率降低最高 96% |
| **Anthropic Contextual Retrieval** (2024) | RAG 中信息编码丢失上下文是幻觉主因，需上下文嵌入 + BM25 混合检索 |

### 2.2 行业最佳实践

| 方法 | 论文/来源 | 核心思路 |
|---|---|---|
| **VeriFact-CoT** | arxiv 2509.05741 (2025.09) | 多阶段自验证：fact verification → reflection → citation generation，LLM 自我检查中间推理步骤 |
| **Claimify** | Microsoft Research, ACL 2025 | 四阶段流水线：句子拆分→筛选(排除非事实)→消歧(指代消解)→分解(原子声明)，99% 蕴含关系 |
| **AFEV** | Expert Systems w/ App (2026) | 原子事实提取 + 证据检索 + 验证，三步合一 |
| **Grounded Generation** | zeroentropy.dev (2026.07) | 强制 LLM 答案引用检索来源，RAG 管线的标准幻觉防御 |
| **Plan Before You Write** | OpenReview (2025) | 写作任务分解为子任务，计划→执行→验证 |

> 核心共识：**多阶段流水线（提取→验证→生成）优于单次 prompt 调优**。

---

## 三、推荐方案：Claim-Pipeline（三阶段事实锚定流水线）

### 3.1 架构总览

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       Claim-Pipeline 四阶段                               │
│                                                                          │
│  阶段 1: Extract      阶段 2: Ground      阶段 2.5: Merge   阶段 3: Compose │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  ┌──────────────┐ │
│  │ 搜索资料     │    │ 事实声明列表 │    │ 跨迭代去重   │  │ 确定事实     │ │
│  │ + 视频摘要   │ ─→ │ 逐一比对来源 │ ─→ │ 新旧声明合并 │→│ 部分证实     │ │
│  │              │    │ 标记置信度   │    │ 按来源覆盖   │  │ + 风格指令   │ │
│  │ ↓ LLM 提取   │    │ ↓ LLM 验证   │    │ ↓ 规则引擎   │  │ ↓ LLM 写作   │ │
│  │ 原子事实声明 │    │ ✅已验证     │    │ 去重+排序    │  │ 微头条正文   │ │
│  │ (列表形式)   │    │ ⚠️部分证实  │    │              │  │ (✅直接用,   │ │
│  │              │    │ ❌无来源     │    │              │  │ ⚠️标推测)   │ │
│  └──────────────┘    └──────────────┘    └──────────────┘  └──────────────┘ │
│                                                │                           │
│  质量门: 来源覆盖率 < 70% ←──────────────────┘                           │
│  → 补充搜索 → 回到阶段 1                                                 │
│  质量门: 综合分 < 90（阶段 3 输出经 evaluation.py 评估）                   │
└──────────────────────────────────────────────────────────────────────────┘
```

> **Token 预估**（单轮，基于 DeepSeek 定价）
> - 阶段 1 Extract 输入：视频摘要 ≤2000 字 + 最近 3 轮搜索 ~4500 字 = ~6500 字 ≈ 5000 tokens
> - 阶段 2 Ground 输入：声明列表 ~500 字 + 原始资料 ~3000 字 = ~3500 字 ≈ 2600 tokens
> - 阶段 2.5 Merge：零 LLM 调用
> - 阶段 3 Compose 输入：声明池 ~800 字 + prompt ~500 字 ≈ 1300 tokens
> - 合计约 ~5000 + ~2600 + ~1300 = ~8900 tokens 输入。DeepSeek 上下文窗口足够，成本可控。

### 3.2 阶段详解

#### 阶段 1: Extract（事实提取器）

**角色**：`claim-extractor`（可参考 `docs/Skills/agency-agents-zh-main/testing/testing-fact-checker.md`）

**输入**：
- 视频转录摘要（≤2000 字）
- 累计搜索资料（最近 3 轮）

**LLM 调用**（temperature=0.1，零风格指令）：
```
你是一个严格的事实提取器。从以下资料中提取所有可验证的事实声明。
规则：
1. 每条声明必须是自包含的（脱离上下文可理解）
2. 标注每条声明的来源：[视频] 或 [搜索: 关键词]
3. 区分确定性：✅确定 / ⚠️推测 / ❓存疑
4. 不添加、不推断、不演绎资料中不存在的信息
5. 如果资料中只有概括描述，保持概括，不补充细节

输出格式（纯列表）:
- [来源: X] [确定性] 声明文本
```

**输出示例**：
```
- [来源: 搜索「美军UFO解密」] [✅确定] 2020年美国国防部正式解密了一批UFO相关档案
- [来源: 搜索「美军UFO解密」] [⚠️推测] 这批档案包含162份不明空中现象报告
- [来源: 视频] [✅确定] 视频中展示了部分解密画面
- [来源: 搜索「美军UFO解密」] [❓存疑] 2026年有新一轮解密计划（仅一处提及，未见官方确认）
```

**关键**: 这一步**完全剥离风格要求**，LLM 只做信息提取，不做"写作"。

---

#### 阶段 2: Ground（事实锚定）

**角色**：`source-verifier`

**输入**：阶段 1 输出 + 原始搜索资料全文

**LLM 调用**（temperature=0.1）：
```
你是一个严格的事实审核员。逐一检查以下声明是否在原始资料中有依据。
对于每条声明：
1. 在原始资料中搜索相同或等价表述
2. 如果找到 → 保持声明，标记 CONFIRMED
3. 如果部分匹配 → 修正声明使其完全匹配来源，标记 PARTIAL
4. 如果完全找不到 → 标记 UNVERIFIED（不保留）
5. 汇总: 来源覆盖率 = (CONFIRMED + PARTIAL) / 总声明数

输出格式（JSON Lines，每行一条，无外层包裹，尾部一行 METADATA）：
{"id":1,"status":"CONFIRMED","text":"修正/确认后的声明文本","source_quote":"资料原文片段"}
{"id":2,"status":"PARTIAL","text":"修正后匹配来源的声明","source_quote":"资料原文片段"}
{"id":3,"status":"UNVERIFIED","text":"","source_quote":""}
METADATA coverage=2/3=66.7%
```
> 选 JSON Lines 而非 XML：实测 LLM 对 JSON Lines 格式遵循率远高于 XML（无嵌套标签、无闭合陷阱）。解析器用 `_safe_parse_verification()`：逐行 `json.loads()` + `METADATA` 正则 fallback，单行解析失败则跳过该行（容错）。

**质量门**: 覆盖率 < 70% → 触发补充搜索 → 回到阶段 1

---

#### 阶段 2.5: Merge（跨迭代声明合并）

**角色**：确定性规则引擎（**非 LLM 调用**），纯代码逻辑。

**输入**：
- 当前迭代的阶段 2 输出（`CONFIRMED` + `PARTIAL` 声明列表）
- 历史迭代的累积声明池

**合并逻辑**（纯 Python stdlib，零 LLM 调用）：
```
1. 精确匹配：声明 ID（如 "claim_3"）相同 → 直接分桶
2. 模糊匹配：difflib.SequenceMatcher.ratio() > 0.5 → 归入同桶
   （注：ratio() 为中文字符级比对，0.5 阈值已覆盖同义改写；
    极端短声明（<10字）跳过分桶，单独保留）
3. 同桶内覆盖规则：
   - 新 CONFIRMED > 旧 CONFIRMED（最新来源胜出，覆盖可能过时的数字/表述）
   - 新 CONFIRMED > 旧 PARTIAL（等级提升）
   - 新 PARTIAL > 旧 UNVERIFIED（等级提升）
   - 同来源不同文本 → 保留两者（可能为不同角度的事实）
4. 去重后按「CONFIRMED 优先、PARTIAL 居后、来源多样化降序」排序
5. 输出：合并后的「可用声明池」{确定事实: [...], 部分事实: [...]}
```
> 合并引擎放在 `fact_pipeline.py`，不涉及 LLM 调用，不新增依赖（仅 `difflib` stdlib）。跨迭代声明累积确保后续轮次不丢失已验证事实。

---

#### 阶段 3: Compose（风格写手）

**角色**：现有 `AIWriter.generate_toutie()` + 风格 prompt

**输入**：
- 阶段 2.5 合并后的声明池（区分「确定事实」与「部分事实」）
- 视频摘要
- 风格 system prompt（包明说/晋说/全球档案馆/听风的蚕）

**LLM 调用**（temperature=风格对应的值，复用 `STYLE_ROUTER`）：
```
【确定事实】（可直接引用，无需标注来源）
{CONFIRMED 声明列表}

【部分证实/推测】（引用时必须标注"据报道""据不完全统计""据分析"）
{PARTIAL 声明列表}

【写作要求】
基于以上事实，按指定风格写一篇微头条。
- 可以调整语言风格、句式、结构
- 「确定事实」可直接引用；「部分事实」必须带不确定性标记
- 不能新增以下信息：具体日期（日/月）、具体人名（非公众人物）、具体数字（人数/金额等）
  → 除非在「确定事实」中有明确记录
- 如果事实不足以支撑丰富内容，用分析性/推理性语言填充

【视频摘要】
{视频转录摘要}

【输出】
标题: ...
正文: ...
```

**关键**: 风格写手的输入是一个**已锁定且分层**的事实池——「确定事实」直接引用，「部分事实」自动加标记，无法编造。

---

### 3.3 与现有系统的衔接

| 现有组件 | 改动 | 说明 |
|---|---|---|
| `write_stage.py` | 重写主循环 + 新增开关 | 单轮 `generate_toutie()` → 四阶段 Claim-Pipeline。新增 `CLAIM_PIPELINE_ENABLED = False` 开关（B-2 开发期关闭，完成后开启），旧模式保留为降级 fallback |
| **`fact_pipeline.py`**（**新建**） | 新增模块 | 阶段 1 `extract_claims()` + 阶段 2 `verify_claims()` + 阶段 2.5 `merge_claims()` + `Claim`/`VerifiedClaim`/`ClaimsPool` 数据模型。**与 `ai_writer.py` 物理隔离**。LLM 访问通过**依赖注入**：函数接受 `llm_call: Callable` 参数，由 `write_stage.py` 从 `AIWriter` 实例传入（`ai_writer._call_ai`），避免循环依赖 |
| `ai_writer.py` | 新增 `compose_from_claims(claims_pool, style, transcript)` | 仅阶段 3：从声明池 + 风格路由生成正文。复用 `STYLE_ROUTER` temperature。**关键：跳过 `_FACT_BOUNDARY_SYSTEM` 注入**（声明池本身是更强的约束，叠加会造成指令冗余/潜在措辞冲突） |
| `evaluation.py` | 评估 prompt 增强 | 新增 `claims_pool_summary` 参数（区别于 `research_context`），注入声明池摘要到评估 prompt，截断长度从 800 → 1500 字。区分"声明池中存在但未用"（完整性扣分）vs "声明池中不存在但写了"（事实准确严重扣分） |
| `research.py` | 修复 `extract_refined_query()` | B-1 止血（⚠️ 临时修复，B-2 后将被 Claim-Pipeline 的声明级搜索逻辑替代）：从反馈中剥离幻觉。B-2 增强：Claim-Pipeline 模式下搜"事实缺口主题"而非"编造细节" |
| `agent/memory.py` | WorkingMemory 扩展 | 新增 `unverified_claims: list[str]` + `knowledge_gaps: list[str]` 两个字段；`to_prompt()` 增强以格式化声明级反思（零破坏性改动）。记录未验证声明 ID、事实缺口方向，指导下一轮搜索 |
| `prompts/baoming_shuo.py` 等 | 移除与事实边界矛盾的指令 | "每段至少 1 个数字"→ 完全移除，改为"有数据处引用，无则分析" |
| `agent/guardrails.py` | 无需修改 | 护栏仍作用于阶段 3 Compose 输出（同现有逻辑），阶段 1/2 的提取和验证结果不经过护栏（纯内部中间产物） |

---

### 3.4 失效保护与降级路径

| 场景 | 触发条件 | 降级策略 |
|---|---|---|
| **阶段 1 失败** | `extract_claims()` 返回 0 条声明 | → 降级为当前 V2 模式（单次 `generate_toutie()` + 事实边界 prompt），但**质量门降至 85**（接受事实边界约束下的最好结果） |
| **阶段 2 覆盖率极低** | 连续 2 次补充搜索后覆盖率仍 < 50% | → 用已有声明（含 `⚠️推测`）+ 在阶段 3 prompt 中强制全部标注不确定性 → 质量门降至 85 |
| **阶段 2 覆盖率不足** | 覆盖率 50-70% | → 补充搜索 1 次 → 仍 < 70% → 按上一条处理 |
| **阶段 3 不达标** | Compose 后 `evaluate_content()` < 90 | → 同现有逻辑：记录最佳结果，补充搜索 → 回到阶段 1（新搜索资料扩展声明池）。**关键：声明池跨迭代累积**（Merge 步骤保留历史 CONFIRMED 声明），每轮不丢失已验证事实 |
| **搜索限流/无结果** | 同轮内连续 3 次 `search_web()` 返回空 | → 用已有声明 Compose + 所有声明标注不确定性 → 质量门降至 85（百度/搜狗反爬保护） |
| **达到最大迭代** | 迭代数 ≥ `MAX_RESEARCH_ITERATIONS`（建议从 10 降至 5） | → 取最佳轮次，判定失败（与现有逻辑一致） |
| **总体 API 调用** | — | 从 1 调用/轮（当前）→ **3 LLM 调用/轮**（Extract + Verify + Compose）+ 1 次评估。总轮次预计从 10 降至 2-3，**净 API 量持平或略降**。Merge 步骤零 LLM 调用（stdlib `difflib` 规则引擎） |

---

## 四、辅助修复：精炼搜索方向纠偏

**当前问题**（`research.py:110-116`）：
```python
# 错误: 用包含幻觉的评估反馈做搜索词
prompt = f"根据以下评估反馈...提炼搜索关键词..."
# 输入: "事实准确性存疑：文中称俄军送奶车伪装..."
# 输出搜索: "俄军送奶车战术来源" ← 幻觉！这件事不存在！
```

**修复方案**（与 Claim-Pipeline 配合）：
```python
def extract_refined_query(content, feedback, state):
    """从反馈中提取核心主题词（剥离幻觉细节）"""
    prompt = (
        f"评估员指出以下内容存在事实不符: {feedback[:200]}\n"
        f"原始视频主题: {state.raw_video_title}\n"
        f"请忽略反馈中的具体细节描述，提炼1个关于该主题"
        f"「核心事实」的搜索词（10字以内，宽泛而非具体）。"
    )
    # 期望输出: "无人机作战模式" 而非 "俄军送奶车伪装来源"
```

**核心原则**：搜索方向应从"查证具体编造细节"转向"拓宽核心主题的事实面"。

---

## 五、实施计划（Phase B 执行路线）

### Phase B-1: 基础修复（0.5 天，可立即执行）

| 任务 | 文件 | 内容 |
|---|---|---|
| B-1.1 | `research.py` | 修复 `extract_refined_query()` 搜索方向（⚠️ **临时修复**——B-2 后此函数将被 Claim-Pipeline 的声明级搜索逻辑完全替代） |
| B-1.2 | `baoming_shuo.py` | 移除"每段至少 1 个数字"硬性要求（已在 V2 条件化，本次完全移除，改为"有具体数据处引用，无则分析"） |
| B-1.3 | 质量门 | `py_compile` + `lint` |
| B-1.4 | 实测 | 用 UFO/军事话题各跑 1 次，观察分数趋势 |

> B-1 属于"止血"——阻止搜索死循环和 prompt 指令矛盾。不改架构。B-1.1 为临时修复，B-2 后将被替代。

### Phase B-2: Claim-Pipeline 核心（1.5-2 天）

| 任务 | 文件 | 内容 |
|---|---|---|
| B-2.0 | `write_stage.py` | 新增 `CLAIM_PIPELINE_ENABLED = False` 开关 + 条件分支。旧模式完整保留为降级 fallback（`not CLAIM_PIPELINE_ENABLED` 时走原路径） |
| B-2.1 | **`fact_pipeline.py`**（新建） | 新增 `extract_claims(research_context, transcript, llm_call)` 方法——阶段 1，temperature=0.1。`llm_call` 由 `write_stage.py` 注入 `AIWriter._call_ai` |
| B-2.2 | **`fact_pipeline.py`** | 新增 `verify_claims(claims, raw_sources, llm_call)` 方法 + `_safe_parse_verification()` JSON Lines 容错解析器——阶段 2，temperature=0.1。`llm_call` 同通过 DI 传入 |
| B-2.3 | **`fact_pipeline.py`** | 新增 `merge_claims(new_claims, history_pool)` 规则引擎——阶段 2.5，零 LLM 调用，仅依赖 stdlib `difflib.SequenceMatcher`（ratio>0.5 分桶 + ID 精确匹配兜底 + 短声明 <10 字跳过） |
| B-2.4 | **`fact_pipeline.py`** | 新增 `Claim` / `VerifiedClaim` / `ClaimsPool` 数据模型 |
| B-2.5 | `ai_writer.py` | 新增 `compose_from_claims(claims_pool, style, transcript)` 方法——阶段 3，区分「确定事实」/「部分事实」，复用 `STYLE_ROUTER` temperature。**跳过 `_FACT_BOUNDARY_SYSTEM` 注入**（声明池约束已更强） |
| B-2.6 | `write_stage.py` | 重写主循环：当 `CLAIM_PIPELINE_ENABLED=True` 时单轮内 Extract→Ground→Merge→Compose→Evaluate 顺序调用；声明池跨迭代累积；`False` 时走原路径 |
| B-2.7 | `write_stage.py` | 迭代控制：覆盖率达到 70% 后才进入阶段 3；`MAX_RESEARCH_ITERATIONS` 从 10 降至 5；搜索限流保护（同轮内连续 3 次空结果→降级 Compose） |
| B-2.8 | `evaluation.py` | 新增 `claims_pool_summary` 参数（区别于 `research_context`），截断长度 800→1500 字；评估 prompt 增强：区分"有声明未用"vs"无声明编造" |
| B-2.9 | `agent/memory.py` | WorkingMemory 扩展：新增 `unverified_claims: list[str]` + `knowledge_gaps: list[str]` 两个字段；`to_prompt()` 增强以格式化声明级反思（零破坏性改动） |
| B-2.10 | `research.py` | `extract_refined_query()` B-2 增强：Claim-Pipeline 模式下搜"事实缺口主题"而非"编造细节"；替代 B-1.1 的临时修复 |
| B-2.11 | 质量门 | `py_compile` × 3（`fact_pipeline.py` / `ai_writer.py` / `write_stage.py`）+ `lint` + 实测（UFO + 军事各 1 次，含新旧模式 A/B 对照） |
| B-2.12 | `specs/acceptance.md` | 更新验收标准，新增 Claim-Pipeline 章节 + `fact_pipeline.py` 测试方法说明 |

### Phase B-3: 优化调参（0.5 天）

| 任务 | 内容 |
|---|---|
| B-3.1 | 覆盖率阈值调优（建议起始 70%，根据实测调整） |
| B-3.2 | 最大迭代轮次调整（三阶段后预计 2-3 轮达标，MAX_RESEARCH_ITERATIONS 可从 10 降至 5） |
| B-3.3 | 评估 prompt 调整：从评估员 prompt 中移除"背景资料仅 800 字"限制（三阶段已保证事实锚定） |

---

## 六、预期效果

> **轮次语义定义**：1 轮 = Claim-Pipeline 完整执行 1 次（Extract → Ground → Merge → Compose → Evaluate）。
> 同一轮内，如果阶段 2 覆盖率不达标，补充搜索 + 重新 Extract/Ground 不算新轮次（算同轮内的搜索扩充）。

| 指标 | 当前（V2） | Phase B-1（止血） | Phase B-2（Claim-Pipeline） |
|---|---|---|---|
| 首次达标轮次 | 从未达标 | 6-8 轮 | 1-2 轮（每轮含 3 次 LLM + 1 次评估） |
| 最高综合分 | 82-88 | 85-92 | 90-95 |
| 事实准确分 | 55-75（震荡） | 65-82 | 80-95 |
| 编造行为 | 高频（每轮都编） | 中频（减少 ~50%） | 极低（物理隔离：阶段 3 只能改写声明池） |
| 单轮 LLM 调用 | 2（写作+评估） | 2 | 4（提取+验证+写作+评估） |
| 总 LLM 调用 | ~22（10 轮 × ~2.2） | ~14（7 轮 × 2） | ~12-16（2-3 轮 × 4 + 同轮内搜索扩充 × ~2） |
| 搜索死循环 | 存在 | 改善 | 根治（搜事实缺口而非编造细节） |
| 声明池跨迭代累积 | ❌ 无 | ❌ 无 | ✅ Merge 步骤保留历史 CONFIRMED 声明 |

---

## 七、决策建议

### 推荐路线

**先止血（B-1）→ 验证效果 → 再上 Claim-Pipeline（B-2）**

理由：
1. B-1 改动小（2 文件），当天可出结果，快速验证搜索修复是否有效
2. B-1 如果能把分数拉到 88-92，可以暂时降低 B-2 的紧迫性
3. B-2 是架构级改动，需要更充分的测试

### 风险提示

1. **API 成本**：B-2 单轮 4 次调用，但总轮次减少 → 预期总成本持平或略降
2. **延迟增加**：单轮处理时间 ≈ 3 倍（3 次串行 LLM 调用），但轮次减少 → 总时间基本持平
3. **极端情况**：搜索资料极为稀少时（如冷门军事细节），阶段 1 可能提取不到足够声明 → 需要良好降级策略

---

## 参考来源

1. **VeriFact-CoT** — Multi-stage self-verification (arxiv 2509.05741, 2025.09)
2. **Claimify** — Microsoft Research, ACL 2025. 原子声明提取四阶段流水线
3. **AFEV** — Atomic Fact Extraction and Verification (Expert Systems w/ App, 2026)
4. **Grounded Generation** — zeroentropy.dev (2026.07). 强制引用检索来源
5. **LLM Hallucination SOTA 2026** — Zylos Research. 组合方案降低幻觉 96%
6. **Plan Before You Write** — OpenReview (2025). 写作计划→执行→验证
7. **Anthropic Contextual Retrieval** (2024). RAG 上下文增强
8. **JointCQ** — ACL 2026. 声明-查询-证据三阶段幻觉检测

---

*方案版本: v1.2 | Phase B 执行完成（8 文件改动，~750 行新增，零新增依赖）| B-1.4 实测 + B-3 调优待执行*
