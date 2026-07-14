# GitHub 检索：将「员工/岗位」封装为 Agent 的仓库

> 检索日期：2026-07-12
> 检索方式：Agentic Workflow（Tier 2 研究 + 文档整理，零代码更改）
> 检索源：`web_search` + `site:github.com` 限定，针对「role-based / employee / virtual company」多 Agent 框架
> 背景：用户询问是否存在「把项目经理、程序员、美工等员工封装成各个 skill」的仓库（与 obra/superpowers 的「技能库」范式相对）

---

## 一、关键结论：两种范式

| 范式 | 核心单元 | 代表仓库 | 你描述的「员工」 |
|------|----------|----------|------------------|
| **技能库范式** | 可组合能力（Skill） | `obra/superpowers`、`anthropics/skills` | ❌ 无岗位概念 |
| **角色/员工范式** | 扮演岗位的员工（Role/Agent） | `MetaGPT`、`ChatDev`、`CrewAI`、`AutoGen`、`CAMEL` | ✅ 正是此类 |

**结论**：把"员工"封装起来的仓库**确实存在**，且是成熟生态，统称 **role-based / role-playing multi-agent framework**。它们不是把员工叫"skill"，而是叫"Role / Agent"，但每个角色定义（人设 + 目标 + 工具 + 后台 LLM）本质就是一个**可复用、自包含的能力包**，功能上等同于"某个员工的 skill"。

> ⚠️ 严格说，GitHub 上没有仓库把岗位**字面命名**为 `skill` 又按员工打包；行业惯例是用"Role/Agent"表达同一件事。若想兼得二者，可用 superpowers 的 `SKILL.md` 格式去包裹 MetaGPT 的角色定义（见第五节）。

---

## 二、代表仓库对比

### 1. MetaGPT（FoundationAgents/MetaGPT）— 最贴近「软件公司员工」
- **仓库**：https://github.com/FoundationAgents/MetaGPT
- **理念**：`Code = SOP (Team)`——把传统软件公司的 SOP 用 LLM 智能体实现。
- **内置员工角色**：`ProductManager`（定需求）、`Architect`（设计系统）、`ProjectManager`（拆分任务）、`Engineer`（写码）、`QaEngineer`（测试）。
- **特点**：角色间按标准化流程（SOP）接力产出文档（需求/设计/任务/代码），最像真实公司组织架构。
- **适合**：自动化软件开发全流程。

### 2. ChatDev（OpenBMB/ChatDev）— 字面「虚拟软件公司」
- **仓库**：https://github.com/OpenBMB/ChatDev
- **理念**：Virtual Software Company——各种智能体扮演**传统公司岗位**协作开发。
- **内置员工角色**：`CEO`、`CTO`、`Programmer`（参与专门的功能研讨会 functional seminars），覆盖设计/编码/测试/文档全生命周期。
- **特点**：用"研讨会"对话模式模拟公司开会；角色即员工，最直观地对应你问的"项目经理/程序员"。
- **适合**：教学/演示多 Agent 协作，以及轻量软件开发。

### 3. CrewAI（crewAIInc/crewAI）— 角色扮演编排框架
- **仓库**：https://github.com/crewAIInc/crewAI
- **核心抽象**：`Agent`（角色）/ `Task`（任务）/ `Crew`（团队）/ `Process`（流程）。
- **特点**：每个 Agent 用自然语言定义**角色定位 + 目标 + 背景故事**，支持 Sequential / Hierarchical 流程；被定位为"面向组织架构"的范式。
- **适合**：自定义任意岗位团队（如加一个"美工 Agent"负责 UI），灵活度高。

### 4. AutoGen（microsoft/autogen）— 多 Agent 对话框架
- **仓库**：https://github.com/microsoft/autogen
- **特点**：`conversable agents` 通过自动化群聊（Group Chat）协作；可混编 LLM Agent、工具 Agent、人类。角色通过 system message 定义。
- **适合**：通用多 Agent 编排，工程化能力强（微软背书，57k+★）。

### 5. CAMEL（camel-ai/camel）— 角色扮演起源
- **仓库**：https://github.com/camel-ai/camel
- **特点**：最早提出"角色扮演"多 Agent 协作（AI User + AI Assistant），可用于构建任意岗位对。

---

## 三、对比总表

| 仓库 | 员工角色示例 | 协作模式 | 岗位是否可自定义 | 语言/生态 |
|------|--------------|----------|------------------|-----------|
| MetaGPT | 产品经理/架构师/项目经理/工程师/QA | SOP 接力文档 | ✅（继承 Role 类） | Python |
| ChatDev | CEO/CTO/程序员 | 功能研讨会群聊 | 部分 | Python |
| CrewAI | 任意（Agent=role） | Sequential/Hierarchical | ✅ 完全 | Python |
| AutoGen | 任意（system msg） | Group Chat | ✅ 完全 | Python |
| CAMEL | 任意（role-play） | 对话 | ✅ 完全 | Python |

---

## 四、与本引擎（AIToutiao-Engine）的映射

本引擎当前流水线**已隐式包含岗位分工**，只是没显式"员工化"：

| 本引擎模块 | 对应的「员工」 |
|------------|----------------|
| `research.py` + `agent/search_engine.py` | 研究员 / 资料采集 |
| `write_stage.py`（Evaluator-Optimizer） | 写手 + 自检编辑 |
| `evaluation.py`（5 维/阈值75） | 质量审查员 |
| `publisher_service.py` | 发布运营 |
| `engine_app.py` 编排 | 项目经理（调度） |
| 配图逻辑 / prompts | 美工 |

→ 若想引入"员工范式"，最轻量路线是 **CrewAI**：定义 研究员/写手/审查员/美工/项目经理 五个 Agent，由 `engine_app.py` 当前编排逻辑充当 Crew 的 Process。

---

## 五、落地建议（不改代码）

1. **想要「员工即 skill」的严格形态**：以 superpowers 的 `SKILL.md` 结构为外壳，把 MetaGPT 各 Role 的 `goal/constraints/actions` 写入 `## Core Pattern`，即可得到一个"角色型 skill"（如 `role-product-manager`）。
2. **想直接跑多角色协作**：优先试 **CrewAI**（自定义岗位最灵活）或 **MetaGPT**（开箱即用的软件公司员工）。
3. **与本引擎结合**：本引擎已是"流程驱动"，引入员工范式建议只替换 `engine_app.py` 的调度层（用 Crew/Process 替代手写 stage 函数），backend 生产逻辑不动（符合 AGENTS.md 约束）。

---

## 六、风险提示
- 以上均为外部开源仓库引用，**未 clone、未安装、未运行**。
- role-based 框架 2024 年曾被批评"更慢更贵更不可靠"；2025-2026 共识是**多 Agent 是手段非目的**，应仅在单 Agent 天花板处引入分工（与本引擎"Tier 分级"哲学一致）。

---

[Reflection]
score: 86
missing:
  - 未实际 clone 任一仓库验证角色定义的代码实现（仅基于 README/DeepWiki/文档概述归纳）
  - CAMEL 仅以"已知常识"列入，未做独立 GitHub 检索确认最新仓库状态
superfluous: N/A
verdict: PASS
分项：正确性 17（明确区分 skill 范式 vs role 范式，结论准确）/ 集成性 18（已映射本引擎隐式岗位分工）/ 安全性 17（仅检索未安装，标注风险）/ 性能 18（并行 7 次检索，无冗余）/ 可维护性 16（文档分区清晰，但 CAMEL 条目置信度略低）。
