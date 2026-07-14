# 融合方案：superpowers × agency-agents

> 讨论日期：2026-07-12
> 流程：Agentic Workflow（Tier 2 设计讨论 + 文档整理，零代码更改）
> 输入：`docs/superpowers_review.md`（技能库/方法论）+ `docs/agency_agents_review.md`（230+ 员工角色库）
> 目标：论证二者可否结合，并给出可落地的融合架构与本引擎适配方案

---

## 一、两个范式本质互补（不是替代）

| 维度 | superpowers | agency-agents | 互补关系 |
|------|-------------|---------------|----------|
| 提供什么 | **方法论 + 技能（HOW）** | **员工角色库（WHO）** | 一个管"流程"，一个管"人力" |
| 核心单元 | `SKILL.md`（能力） | `agent .md`（角色，含人格/规则/交付/流程/指标） | 不同颗粒度 |
| 强项 | HARD-GATE、brainstorming→plans→TDD→review、子代理双维评审 | 230+ 现成岗位、即插即用、多工具 convert | 缺啥补啥 |
| 弱项 | **无预设岗位**（没有 PM/设计师/审查员实体） | **无编排方法论**（没有门禁、没有 TDD 闭环、没有评审周期） | 正好互填 |

**结论**：二者不冲突，是**"操作系统"与"人事库"**的关系。superpowers 当控制平面（怎么干），agency-agents 当人力资源（谁去干）。

---

## 二、融合方案（4 个候选，由浅入深）

### 方案 A：superpowers 编排 + agency 角色当"简报"
- 用 superpowers 的 `subagent-driven-development` 驱动流程；每派一个任务，把对应的 agency `agent .md` 作为 `task-brief` 的角色设定喂给子代理。
- **改动最小**：agency 的 .md 原样当作"角色说明书"注入，不动 superpowers 技能。
- 代价：agency 的"强人格"可能给确定性流水线任务带来 token 膨胀/漂移。

### 方案 B：把 agency 角色改写成 superpowers SKILL
- 用 `writing-skills` 规范，把每个 agency `agent .md` 转成 `SKILL.md`（name + 仅触发条件 description + Core Pattern）。
- **优点**：可被 superpowers 技能分发机制自动发现。
- **代价**：丢掉 agency 最核心的"人格/身份/成功指标"维度，降级成纯能力——得不偿失。

### 方案 C（推荐）：统一「Agent Contract」契约 ★
- 定义一种**合并格式**，一份 `.md` 同时是"可发现的技能"和"有血有肉的角色"：
  - **取自 superpowers**：frontmatter(`name`+`description`仅触发条件)、`## When to Use`、`## HARD-GATE` 纪律、`## Verification`(TDD/验收)。
  - **取自 agency-agents**：`## Identity & Memory`(人格)、`## Critical Rules`、`## Technical Deliverables`、`## Workflow Process`、`## Success Metrics`。
- 这样角色既能按 superpowers 流程被调度，又保留 agency 的人设与交付标准。
- 需写一个 `agency2contract` 转换脚本（复用 agency 已有的 `convert.sh` 思路，新增"→superpowers 契约"目标格式）。

### 方案 D：分层架构（方案 C 的运行形态）
```
Layer 1 方法论  : superpowers skills (brainstorming / writing-plans / TDD / requesting-code-review)
Layer 2 人力资源 : agency-agents 角色 .md（按 division 组织：engineering/design/marketing/...）
Layer 3 编排控制 : Controller（= superpowers controller，或本引擎 engine_app.py）
                  · 在 executing-plans / subagent-driven-development 时，按任务选角色 .md 作为子代理 brief
                  · 套用 superpowers 的「每任务双维评审 + 模型分级 + 进度账本」
Layer 4 工具适配 : agency convert.sh（端口到目标工具）+ superpowers 插件（加载 skills）
```

---

## 三、映射到本引擎（AIToutiao-Engine）

本引擎流水线 `下载→转录→研究→写作→评估→配图→发布` 已是"流程驱动"，superpowers 方法论我们**已经在用**（Tier 分级、Reflection、Evaluator-Optimizer）。缺的就是"显式角色"。

| 流水线阶段 | 当前（隐式） | 可引入的 agency 角色 | 套用的 superpowers 纪律 |
|------------|--------------|----------------------|--------------------------|
| 研究 `research.py` | 研究员 | `Marketing/Content Creator`、`SEO Specialist` | brainstorming 门禁 |
| 写作 `write_stage.py` | 写手+自检 | `Engineering/Code Reviewer`（自检编辑） | TDD / verification-before-completion |
| 评估 `evaluation.py` | 审查员 | `Testing/Reality Checker`、`Evidence Collector` | requesting-code-review 双维 |
| 配图 prompts | 美工 | `Design/Image Prompt Engineer`、`UI Designer` | （创意阶段保留人格） |
| 编排 `engine_app.py` | 项目经理 | `Specialized/Agents Orchestrator`、`Chief of Staff` | subagent-driven-development |
| 发布 `publisher_service.py` | 运营 | `Marketing/Social Media` 类 | executing-plans 检查点 |

**本引擎落地建议（方案 C+D 的裁剪版）**：
1. 不引入 230+ 全员，只**精选 6–8 个**与流水线对应的角色（去人格化用于后端确定阶段，保留人格用于写作/配图创意阶段）。
2. 把 superpowers 的 HARD-GATE + 每任务双维评审 + 模型分级选派，**接到 `engine_app.py` 的 stage 调度层**（仅改调度，不动 backend 生产逻辑，符合 AGENTS.md 约束）。
3. 角色 `.md` 以方案 C 的「Agent Contract」格式落地到 `$HOME/.codebuddy/agents/` 或 skills。

---

## 四、风险与缓解

| 风险 | 说明 | 缓解 |
|------|------|------|
| 人格开销 | agency 强人格给确定性任务带来 token 膨胀/漂移 | 后端阶段去人格，仅创意阶段保留 |
| 格式错配 | SKILL.md vs agent .md 结构不同 | 方案 C 统一契约 + 转换器 |
| 过度引入 | 230+ 角色远超需求 | 裁剪到 6–8 个流水线相关角色 |
| 工具耦合 | 二者假设 Claude Code/Cursor；本引擎跑在 CodeBuddy+Python | 仅借鉴概念与契约格式，不硬装插件 |
| 方法论过重 | superpowers 全流程对简单任务偏重 | 沿用本引擎 Tier 分级，低 Tier 不走完整 SDLC |

---

## 五、推荐路线总结

**采用方案 C（统一 Agent Contract）+ 方案 D（分层）的裁剪版**：
- superpowers = 控制平面（纪律/门禁/评审）
- agency-agents = 人力资源（裁剪后的角色库）
- 本引擎 = 把二者接进 `engine_app.py` 调度层，backend 不动

> 即：**用 superpowers 的"章法"指挥 agency-agents 的"人手"**，补齐 superpowers 无人、agency 无法的双向缺口。

---

## 六、实地验证（本地 checkout，2026-07-12）

> 用户已将两个仓库 clone 到 `D:\AIToutiao-Engine\docs\Skills\`（`agency-agents-main/` 315 文件、`superpowers-main/` 153 文件）。本章用真实源码闭合上文两个 `missing` 项。

### 6.1 关键发现：agency-agents 的 `convert.sh` 已原生输出 SKILL.md

已读 `agency-agents-main/scripts/convert.sh`（732 行）。它把同一份 `agent .md` 转成 13+ 工具格式，其中 **`antigravity` 和 `osaurus` 两个目标直接产出的就是 superpowers 同款 `SKILL.md`**（name + description frontmatter + 正文 body）：

```bash
# convert_antigravity() / convert_osaurus()
cat > "$outfile" <<HEREDOC
---
name: agency-$(slugify "$name")     # 如 agency-reality-checker
description: ${description}         # 整段描述
---
${body}                              # 人格/使命/流程/指标 全部进正文
HEREDOC
```

**结论**：方案 C 的"Agent Contract"不是空想——agency 的 `.md` 到 superpowers `SKILL.md` 的机械转换，agency 自己已经做了一半。我们只需在这基础上**注入 superpowers 的纪律字段**（HARD-GATE / Verification / `description` 改为仅触发条件）。

### 6.2 逐字段比对（方案 C 契约字段映射，已验证）

| 方案 C「Agent Contract」字段 | agency `agent .md` 现状（读 `testing-reality-checker.md`） | superpowers `SKILL.md` 现状（读 `brainstorming/SKILL.md`） | 融合动作 |
|------|------|------|------|
| frontmatter `name` | ✅ `name: Reality Checker` | ✅ `name: brainstorming` | 直接复用 |
| frontmatter `description` | ⚠️ 整段描述（含"何时用"） | ✅ **仅触发条件**（"You MUST use this before..."） | **改写**：agency 的 description 需拆成"触发条件"填 frontmatter + "何时用"留正文 `## When to Use` |
| `## Identity & Memory`（人格） | ✅ 完整（Role/Personality/Memory） | ❌ 无 | 取 agency |
| `## Critical Rules` | ✅（`## 🚨 Your Mandatory Process` + AUTOMATIC FAIL） | ⚠️ 部分（`## HARD-GATE` 纪律） | **合并**：agency 的强制流程 + superpowers 的 HARD-GATE 门禁 |
| `## Technical Deliverables` | ✅（报告模板/截图证据） | ❌ 无 | 取 agency |
| `## Workflow Process` | ✅（STEP1-3 分步） | ⚠️ 有 `## Checklist` + `## Process Flow`（dot 图） | 合并两式 |
| `## Success Metrics` | ✅（`## Your Success Metrics`） | ❌ 无 | 取 agency |
| `## Verification`（TDD/验收） | ❌ 无 | ✅ `verification-before-completion` 技能 | **注入**：给每个 agency 角色补 TDD/验收门槛 |
| HARD-GATE 纪律 | ❌ 无 | ✅ `<HARD-GATE>` 标签 | **注入** |

> agency `Reality Checker` 自带 `## 🚨 Your Mandatory Process`（NEVER SKIP 命令）与 `## 🚫 AUTOMATIC FAIL Triggers`（"零问题/满分无证据"直接判失败）——这本身就和 superpowers 的"证据优于声明"哲学同构，融合阻力极小。

### 6.3 格式错配的真实摩擦（风险项已证实）

- **description 语义冲突**：agency 把完整描述写进 frontmatter `description`，而 superpowers 强制 `description` 只写**触发条件**（否则技能分发会误触发）。→ 转换器必须重写 description。
- **超量角色**：agency 本地 230+ 个 `.md`（README 自称 230+；本地 division 目录实测 engineering 49 / specialized 54 / marketing 36 / testing 9 / design 9 / security 10 / sales 9 / strategy 17 / gis 13 / game 20 等，合计≈300）。本引擎只需 6–8 个。
- **工具耦合**：两仓库 install/convert 全假设 Claude Code / Cursor / Gemini / OpenCode，无 CodeBuddy 目标。本引擎只能借鉴「契约概念 + 字段格式」，不能硬跑其安装脚本（且安装脚本会改 `~/.claude` 等外部目录，**不执行**）。

### 6.4 落地到本引擎的最小可行动作（不改代码）

1. 从 `agency-agents-main/` 挑 2 个最贴合角色作为**范本**：`testing/testing-reality-checker.md`（↔ 本引擎 `evaluation.py` 5 维审查）→ 改名为 `evaluation-reviewer`；`design/design-image-prompt-engineer.md`（↔ 本引擎配图 prompts）→ 改名为 `image-art-director`。
2. 用方案 C 契约模板，把每个范本转成一份「superpowers 风格 SKILL.md」（frontmatter 仅触发条件 + 注入 HARD-GATE/Verification + 保留 agency 人格/交付/指标）。
3. 落盘到 `D:\AIToutiao-Engine\docs\Skills\contracts/`（纯文档资产，不进 `$HOME`、不装任何插件），作为后续 `engine_app.py` 调度层改革的设计基线。

---

[Reflection]
score: 89（较初版 +2：两个 missing 已闭环）
missing: N/A（已读 convert.sh 源码 + reality-checker / brainstorming 两个样本做逐字段比对，原 two missing 全数闭合）
superfluous: N/A
verdict: PASS（升级为实据支撑）
分项：正确性 19（互补性 + 字段映射均经源码验证）/ 集成性 18（已逐阶段映射本引擎流水线）/ 安全性 18（仅分析未执行 install/convert 外部脚本）/ 性能 17（基于本地 checkout 直接核对）/ 可维护性 17（分层清晰，风险与缓解成对列出，并新增 6.x 实证章节）。
