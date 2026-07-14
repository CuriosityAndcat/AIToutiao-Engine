# 仓库评审：obra/superpowers（Agentic Skills Framework）

> 审查日期：2026-07-12
> 审查方式：Agentic Workflow（Tier 2 研究 + 文档整理，零代码更改）
> 仓库：https://github.com/obra/superpowers ｜ MIT License ｜ v6.1.1 (2026-07-02) ｜ 252k★ / 22.5k Forks
> 作者：Jesse Vincent（obra）+ Prime Radiant 团队

---

## 一、仓库定位

一套**面向编程代理（Coding Agent）的软件开发方法论 + 可组合技能库**。核心主张：让 AI 代理接到任务后**先梳理需求→出规范→制定计划→子代理驱动开发→内置审查与测试**，而非直接写代码。

- 支持 Claude Code / Cursor / Codex / Kimi Code / OpenCode / Pi / GitHub Copilot CLI 等。
- 通过各代理的插件机制安装（`/plugin install`、`agy plugin install` 等），注入 `skills/` + 启动钩子（`AGENTS.md`/`CLAUDE.md`/`GEMINI.md`）。
- 文件语言占比：Shell 54% / JS 39% / TS 2.5% / HTML 2.1% / Python 1.8%。

---

## 二、核心技能库（skills/）清单

| 分类 | 技能 | 作用 |
|------|------|------|
| 测试 | `test-driven-development` | RED-GREEN-REFACTOR 循环 |
| 调试 | `systematic-debugging` | 四阶段根因分析 |
| 调试 | `verification-before-completion` | 确保问题真被修复 |
| 协作 | `brainstorming` | 苏格拉底式需求细化（HARD-GATE 禁止提前编码） |
| 协作 | `writing-plans` | 编写详细实现计划 |
| 协作 | `executing-plans` | 带检查点批量执行 |
| 协作 | `dispatching-parallel-agents` | 并发子代理工作流 |
| 协作 | `requesting-code-review` | 提交前自检清单 |
| 协作 | `receiving-code-review` | 响应反馈 |
| 协作 | `using-git-worktrees` | 并行分支管理 |
| 协作 | `finishing-a-development-branch` | 合并/PR 决策 |
| 协作 | `subagent-driven-development` | 每任务隔离子代理 + 双维评审 |
| 元 | `writing-skills` | 创建新技能的最佳实践（TDD 用于过程文档） |
| 元 | `using-superpowers` | 技能系统介绍 |

**基本工作流（Basic Workflow）**：
`brainstorming → using-git-worktrees → writing-plans → (subagent-driven-development | executing-plans) → test-driven-development → requesting-code-review → finishing-a-development-branch`

---

## 三、重点技能深度解析

### 3.1 `brainstorming`（需求细化，对应我们的「先做计划」）
- **HARD-GATE**：展示设计且用户批准前，**禁止写代码/搭脚手架/调实现技能**；唯一出口是调用 `writing-plans`。
- 步骤：探索上下文 → 一次一问澄清（聚焦 purpose/constraints/success criteria）→ 提 2-3 方案附权衡 → 分节设计确认 → 写 spec 到 `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` 并 commit → 规格自审 → 用户审查。
- 反模式：用「太简单」当借口跳过流程；即使改 todo/config 也要走设计（可极简）。
- 哲学：YAGNI ruthlessly、单一职责、增量验证。

→ **与本引擎对照**：本引擎的「Tier 3 需先出 Plan」「改网页 UI 前先查 WEB_REVIEW」正是同一 HARD-GATE 思想。可借鉴其「分节确认 + spec 落盘」机制，强化当前偏口头的计划环节。

### 3.2 `writing-skills`（元技能：如何写技能，对应我们「自建 skill」需求）
- **铁律**：`NO SKILL WITHOUT A FAILING TEST FIRST`——把 TDD 用于过程文档。
  - RED：无技能时跑压力场景，记录代理的「合理化借口」；
  - GREEN：写最小技能精准堵漏，复跑验证合规；
  - REFACTOR：发现新借口加显式反驳，重测至「防弹」。
- **SKILL.md 标准结构**：YAML frontmatter（`name`+`description`）→ `## Overview` → `## When to Use` → `## Core Pattern` → `## Quick Reference` → `## Implementation` → `## Common Mistakes`。
- **description 铁律**：只写触发条件（`Use when…`），**绝不摘要流程**（否则代理走捷径不读正文）；理想 <500 字符。
- **防合理化**：显式堵漏洞 + 「精神即字面」原则 + 红旗列表。
- 命名：`name` 仅字母数字连字符；主动语态、动词优先。

→ **与本引擎对照**：我们此前讨论「自建 code-review skill 骨架」「FIND-SKILL 检索缺口」。本技能提供了**可操作的技能编写规范**，可直接用于沉淀本项目专用 skill（如 XSS 修复、ui 拆分）。这正是 `$HOME/.codebuddy/skills` 的落地方法论。

### 3.3 `subagent-driven-development`（子代理调度，对应我们的「多 Agent 分工」）
- **每任务一个全新隔离子代理**，任务间**顺序执行**（明确禁止并行派遣实现子代理以避免冲突）。
- **每任务双维评审**：Spec 合规性 + 代码质量；Critical/Important → 派 fix 子代理 → 重评，直至通过。
- **最终全分支评审**：用最强模型跑 `review-package MERGE_BASE HEAD`。
- **模型分级选派**：机械任务用最廉价模型，集成/判断用标准，架构/终审用最强；**必须显式声明模型**。
- **文件化交接**：`task-brief` 简报 + 报告文件 + diff，避免上下文污染；进度账本 `.superpowers/sdd/progress.md` 防重复派遣。

→ **与本引擎对照**：本引擎的 `Task` 子代理 + 多角色审查（Code Reviewer）已对齐其「隔离 + 评审」思想，但**缺「每任务强制评审 + 模型分级选派 + 进度账本」三件具体化机制**。

---

## 四、与本引擎 Agentic Workflow 的映射

| superpowers 概念 | 本引擎对应（AGENTS.md） | 差距 / 可借鉴点 |
|------------------|--------------------------|----------------|
| `brainstorming` HARD-GATE | Tier 3 需先出 Plan | 借鉴：spec 落盘 + 分节确认 |
| `writing-plans` / `executing-plans` | 任务计划 + 反射协议 | 本引擎反射偏「评分」而非「计划执行」 |
| `requesting-code-review` | 多角色审查 / 5 维评估 | 已对齐 |
| `subagent-driven-development` | `Task` 子代理 + 多角色 | 缺：每任务强制评审、模型分级、进度账本 |
| `test-driven-development` | 评估 `QUALITY_PASS_THRESHOLD=75` | 阈值即「验收测试」，但无单测集成 |
| `writing-skills` | （待建）自建 skill | **直接采用**：本项目缺技能编写规范 |
| `systematic-debugging` | 自检修复循环 | 可借鉴四阶段根因分析 |
| `using-git-worktrees` | git 工作流 | 本引擎未用 worktree 隔离 |

---

## 五、可借鉴点（落地建议，不改代码）

1. **引入 `writing-skills` 规范自建本项目的专用 skill**
   - 针对 WEB_REVIEW 缺口（A1 XSS、D10/D11 重构、C 类 UI），按 `NO SKILL WITHOUT A FAILING TEST` 原则逐个写 skill，沉淀到 `$HOME/.codebuddy/skills`。
   - 采用标准 SKILL.md 结构 + description 只写触发条件。

2. **强化 HARD-GATE 与 spec 落盘**
   - 对 Tier 3 任务，复用 `brainstorming` 的「分节确认 + 写 `docs/specs/...-design.md` + 提交」机制，让当前口头计划可追踪。

3. **补齐子代理调度三机制**
   - 每任务强制评审（Spec 合规 + 质量双维）；
   - 显式声明子代理模型（廉价/标准/最强分级）；
   - 进度账本防重复派遣（当前 `todo_write` 已部分承担）。

4. **TDD 心态用于过程改进**
   - 把「代理犯的错」当成 RED，写一条规则/技能当 GREEN，复测至防弹——与本引擎「反馈与自愈闭环」一致。

---

## 六、安全 / 风险提示

- 仓库 README 含各代理的**安装命令**，执行会向对应编码代理注入技能与启动钩子，改变其行为。本次仅分析，**未执行任何安装命令**。
- 技能内含「写文件 / git commit / 启动本地服务」指令；若后续实际启用，需用户逐条批准。
- 含可选遥测（Prime Radiant Logo，默认开；`SUPERPOWERS_DISABLE_TELEMETRY` 可关）。

---

## 七、FIND-SKILL 关联

- 本仓库本身即「代码评审 / 技能编写」类 skill 的**权威来源**，可补 SkillHub 在 `code-review`(wpank) 之外的更完整方法论。
- 与 WEB_REVIEW.md 第五节检索互补：superpowers 的 `requesting-code-review` + `writing-skills` 可直接用于落地我们此前规划的「自建 code-review skill」。

---

[Reflection]
score: 88
missing:
  - 未拉取全部 14 个 SKILL.md 原文（仅深读 brainstorming / writing-skills / subagent-driven-development 三个最相关项；其余按目录+概述归纳）
  - 未实际 clone 仓库验证 scripts/（task-brief / review-package）的具体实现
superfluous: N/A
verdict: PASS
分项：正确性 18（HARD-GATE、TDD-for-skills、串行子代理等关键点准确提炼）/ 集成性 18（已与本引擎 Agentic Workflow 逐条映射）/ 安全性 17（仅分析未安装，并标注安装风险）/ 性能 18（并行抓取 3 个核心 skill，无冗余）/ 可维护性 17（文档分区清晰、映射表与落地建议分离）。
