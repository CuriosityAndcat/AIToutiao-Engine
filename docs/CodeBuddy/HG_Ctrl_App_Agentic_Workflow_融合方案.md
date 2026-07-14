# HG_Ctrl_App — Agentic Workflow 融合方案

> 融合 `agentic-workflow.mdc` 行为规则 与 四阶段闭环框架，形成完整的项目级 Agent 工作流规范  
> 设计日期: 2026-07-13 | 不做任何代码变更

---

## 一、融合总览

### 1.1 融合思路

两个文档正交互补：

| 文档 | 定位 | 回答的问题 |
|------|------|-----------|
| **agentic-workflow.mdc** (行为规则) | 执行规范 | 怎么做才高质量？多严格？ |
| **四阶段闭环框架** (宏观骨架) | 流程定义 | 做什么？什么时候做？ |

融合后的框架以四阶段闭环为**骨架**，以 agentic-workflow.mdc 的 5 个模块为**质量引擎**内嵌到各阶段：

```
                         ┌─────────────────────────────────────────┐
                         │         前置: 复杂度判定                │
                         │    (agentic-workflow.mdc 模块一)         │
                         │    Tier 1 / Tier 2 / Tier 3              │
                         │    (影响 Phase 1 和 Phase 4 的深度)      │
                         └────────────────┬────────────────────────┘
                                          │
              ┌───────────────────────────┼───────────────────────────┐
              ▼                           ▼                           ▼
          Tier 1                       Tier 2                      Tier 3
     (单文件小改/问答)           (多文件/重构单模块)          (架构设计/系统重构)
              │                           │                           │
              │                           │                           │
┌─────────────┴─────────────┐ ┌───────────┴───────────┐ ┌───────────┴───────────┐
│ Phase 1: READ (简化)      │ │ Phase 1: READ (标准)   │ │ Phase 1: READ (完整)   │
│ 直接使用已有上下文         │ │ AGENTS.md+Rules+Memory │ │ 全部L1-L4+MCP查询      │
├───────────────────────────┤ ├───────────────────────┤ ├───────────────────────┤
│                           │ │                       │ │                       │
│       Phase 2+3: 统一 Tier 3 最高标准执行              │                      │
│       ★ 强制Plan + 规划协议 + Subagents全开            │                      │
│       ★ Hooks全开 + 微循环逐步骤验证回路               │                      │
│       ★ 5维度评分 + 多角色审查 + 宏循环max 3轮         │                      │
│                                                       │                      │
├───────────────────────────┤ ├───────────────────────┤ ├───────────────────────┤
│ Phase 4: WRITE (简化)     │ │ Phase 4: WRITE (标准)  │ │ Phase 4: WRITE (完整)  │
│ 仅Memory日志              │ │ Working Memory+Memory  │ │ 全部6种保存机制        │
└───────────────────────────┘ └───────────────────────┘ └───────────────────────┘
```

> **设计决策**：Phase 2 和 Phase 3 不再按 Tier 分级，统一按 Tier 3 最高标准执行。  
> 理由：一旦触发了本 Agentic Workflow，必然是重要变更，需要用最严格的标准保证质量。  
> Tier 分级**仅影响 Phase 1（知识加载深度）和 Phase 4（知识保存深度）**。

### 1.2 模块映射关系

| agentic-workflow.mdc 模块 | 映射到的四阶段位置 | 作用 |
|---------------------------|-------------------|------|
| **模块一: 复杂度判定** | **前置筛选器** | 决定 Phase 1 和 Phase 4 的知识加载/保存深度 |
| **模块二: 反射协议** | **Phase 3 核心引擎** | 5维度0-100评分 → PASS/FIXABLE/BLOCKED |
| **模块三: 规划协议** | **Phase 2 (统一强制)** | 约束 Plan 结构: 步骤ID/目标/文件/依赖/验证标准 |
| **模块四: 多角色审查** | **Phase 3 (统一启用)** | 4角色视角切换审查方案 |
| **模块五a: 步骤级微循环** | **Phase 2 LOOP 执行循环** | 每步执行后对照验证标准，不通过→回退重做 |
| **模块五b: 全局级宏循环** | **Phase 3 REFLECT FIXABLE 分支** | 5维度评分 < 80 → 全局迭代修正，max 3轮 |
| **边界情况表** | **各阶段异常分支** | 6种场景的行为规则 |

---

## 二、前置: 复杂度判定 (复杂度判定模块)

> 对应 agentic-workflow.mdc 模块一，作为整个框架的前置筛选器

### 2.1 判定方法

收到任务后，回答以下 4 个问题：

| 问题 | 判断标准 |
|------|---------|
| 1. 涉及文件数 > 3？ | 是 → Tier 2+ |
| 2. 需要新设计决策？ | 是 → Tier 3 |
| 3. 影响现有 API/接口？ | 是 → Tier 2+ |
| 4. 用户明确要求"规划"、"设计"、"重构"？ | 是 → Tier 3 |

### 2.2 Tier 定义

| 等级 | 场景 | 四阶段执行深度 |
|------|------|--------------|
| **Tier 1 简单** | 单文件小改、问答、加注释、修 typo | READ(简化) → ACT(跳过本流程，直接执行) → 跳过REFLECT → WRITE(简化) |
| **Tier 2 中等** | 多文件修改、新增功能、重构单一模块 | READ(标准) → **ACT+REFLECT(Tier 3 统一标准)** → WRITE(标准) |
| **Tier 3 复杂** | 架构设计、系统重构、从零搭建、跨模块协调 | READ(完整) → **ACT+REFLECT(Tier 3 统一标准)** → WRITE(完整) |

> **注意**：Tier 1 任务不进入本 Agentic Workflow 流程。Tier 2+ 任务在 Phase 2 和 Phase 3 阶段统一按 Tier 3 最高标准执行。

### 2.3 边界情况处理

| 场景 | 行为 |
|------|------|
| 简单单行修改 | Tier 1 直接执行，不触发任何协议 |
| 技术问答 / 解释概念 | Tier 1 直接回答，无需审查 |
| 连续多条简单指令 | 合并为一次统一标准审查 |
| 上下文不足无法判定 | 默认进入流程，统一标准执行（宁可多审查，不可漏过） |
| 同一任务跨越多轮对话 | 只在最后一轮执行完整 Reflection |
| 文件超过 500 行需要读全 | 先分段读关键部分 → Reflection 判定是否需要全量 |

---

## 三、Phase 1: 知识库读取 (READ)

> 四阶段框架 Phase 1，按 Tier 等级加载不同深度的知识

### 3.1 Tier 分级加载策略

| 加载层级 | 机制 | Tier 1 | Tier 2 | Tier 3 |
|---------|------|--------|--------|--------|
| **L1 始终层** | `AGENTS.md` + `alwaysApply Rules` | ✅ 自动加载 | ✅ 自动加载 | ✅ 自动加载 |
| **L2 按需层** | `agentic request Rules` + Skills | ❌ 跳过 | ✅ 按需加载 | ✅ 按需加载 |
| **L3 主动层** | `@Docs` / MCP / `@Files` / `@Git` | ❌ 跳过 | ⚠️ agent判断 | ✅ 主动查询 |
| **L4 记忆层** | Memory + Working Memory | ✅ 自动加载 | ✅ 自动加载 | ✅ 自动加载 |
| **L5 网络层** | `web_search` / `web_fetch` 互联网搜索 | ❌ 跳过 | ⚠️ 本地知识不足时 | ✅ 主动搜索 |

> **L5 网络搜索触发条件**：当以下任一情况出现时，必须主动进行网络搜索：
> - 项目本地知识库（L1-L4）中找不到答案
> - 任务涉及不熟悉的芯片外设、协议或算法
> - 需要确认最新的技术规范或最佳实践
> - 需要参考同类实现的方案设计
>
> 网络搜索**不是 L3 的替代品**，而是兜底机制——先用本地知识，找不到再用网络搜索补充。

### 3.2 当前项目知识库配置

| 配置项 | 文件路径 | 状态 |
|--------|---------|------|
| AGENTS.md | `docs/AGENTS.md` | ✅ 自动加载 |
| agentic-workflow Skill | `docs/skills/agentic-workflow.md` | ✅ 按需加载 |
| Subagents×6 | `.codebuddy/agents/*.md` | ✅ 已有 |
| Memory (长期) | `.codebuddy/memory/MEMORY.md` | ✅ 已有 |
| Working Memory (每日) | `.codebuddy/memory/YYYY-MM-DD.md` | ✅ 运行中 |

> **注意**：旧的 `.codebuddy/rules/agentic-workflow.mdc` 已删除，以 `docs/skills/agentic-workflow.md` 为准。

### 3.3 网络搜索：知识兜底机制

当本地 L1-L4 知识层无法提供足够信息时，使用网络搜索作为补充：

```
本地知识 → 足够? ──→ 是 → 进入 Phase 2
    │
    └── 否 (找不到答案/不熟悉/需验证)
         │
         ▼
    web_search (关键词: 芯片型号 + 功能描述)
         │
         ▼
    web_fetch (深入阅读搜索结果中的高价值页面)
         │
         ▼
    将搜索结论记录到 Working Memory → 进入 Phase 2
```

**搜索策略**：
- 优先搜索官方文档（芯片数据手册、RTOS 官方文档、协议标准）
- 其次搜索社区实现（GitHub、Stack Overflow、厂商论坛）
- 搜索结果应记录到 Phase 4 的 Memory 中，避免重复搜索

### 3.4 推荐增强: 分层 Rules 体系

```
.codebuddy/rules/
├── agentic-workflow.mdc          # 已有: 行为规则(本融合方案的基础)
├── L1-always-编码规范.mdc         # 新增: alwaysApply → MISRA-C/AUTOSAR
├── L1-always-架构约束.mdc         # 新增: alwaysApply → 四层依赖规则
├── L2-reference-HC32芯片手册.mdc  # 新增: agentic request → MCU寄存器
├── L2-reference-FreeRTOS模式.mdc  # 新增: agentic request → 任务同步模式
├── L3-manual-安全审查清单.mdc     # 新增: manual → @引用触发
└── L3-manual-代码审查模板.mdc     # 新增: manual → @引用触发
```

---

## 四、Phase 2: Agent 工作流 (ACT)

> 四阶段框架 Phase 2 融合 agentic-workflow.mdc 模块三(规划协议)

### 4.1 Phase 2 执行策略（统一 Tier 3 标准）

> **Phase 2 不再按 Tier 分级**，所有通过复杂度判定进入本流程的任务，在 Phase 2 阶段统一按 Tier 3 最高标准执行。

| 维度 | 统一标准 |
|------|---------|
| **工作模式** | **Plan Mode 强制** |
| **Plan 步骤** | **规划协议强制**（步骤ID+目标+文件+依赖+验证标准） |
| **Subagents 调度** | 6个全部可用，按需自动调度 |
| **Hooks 安全拦截** | 全部 Hooks 开启（PreToolUse + PostToolUse） |
| **Checkpoints** | 自动创建 + 关键节点手动标记 |
| **LOOP 执行循环** | **强制逐步骤验证回路**（每步对照验证标准，不通过→回退重做） |

### 4.2 Tier 3 强制: 规划协议

> 对应 agentic-workflow.mdc 模块三

#### 4.2.1 触发条件

满足以下任一条件时必须先规划再执行：
- 涉及 > 3 个文件的修改（与复杂度判定 Tier 2+ 阈值对齐）
- 新增模块/包/服务
- 架构变更（如引入新模式、更换框架）
- 用户明确要求"先出方案"

#### 4.2.2 Plan 结构要求

每个 Plan 必须包含：

```
1. 步骤 ID：唯一标识
2. 目标：该步骤要达成的具体结果
3. 涉及文件：具体文件路径列表
4. 依赖：依赖哪些前置步骤
5. 验证标准：如何判断该步骤完成
```

#### 4.2.3 规划流程：主动 QA + 检验文档 + 自检

> **核心原则**：方案的制定不是 AI 单方面产出后让用户"批准"，而是 AI 主动识别不确定性，与用户逐条核对，不放过任何细节。

整个规划阶段分为三步闭环：

```
方案初稿
    │
    ▼
┌─────────────────────────────────────────────┐
│  Step A: 主动 QA（需求澄清）                  │
│                                             │
│  1. AI 识别方案中所有不确定点、假设、模糊地带   │
│  2. 逐条列出疑问，向用户提问                    │
│  3. 用户逐条答复（不通过则循环回到 2）          │
│  4. 所有疑问得到明确答复后，进入 Step B         │
│                                             │
│  疑问清单模板:                                │
│  ❓ Q1: [具体疑问描述]                         │
│  ❓ Q2: ...                                  │
│  对每个疑问标注: 阻塞级别 (Blocker/Critical/Clarify) │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│  Step B: 生成检验文档                         │
│                                             │
│  将所有已确认的需求、假设、约束整理为结构化文档:  │
│                                             │
│  # 检验文档: <任务名称>                       │
│  ## 1. 已确认需求清单                         │
│  │ ID | 需求描述 | 来源(QA#) | 确认状态       │
│  ## 2. 技术假设清单                          │
│  │ ID | 假设内容 | 验证方式 | 风险等级        │
│  ## 3. 约束条件清单                          │
│  │ ID | 约束内容 | 影响范围                   │
│  ## 4. 边界与异常场景                        │
│  │ ID | 场景描述 | 预期行为 | 是否已覆盖      │
│  ## 5. 未解决疑问（若有）                     │
│                                             │
│  该文档作为方案的"验收标准"                     │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│  Step C: 自检验证                             │
│                                             │
│  对照检验文档，逐条检查方案是否覆盖:            │
│                                             │
│  检验操作:                                   │
│  ✅ 需求清单 每一条是否在方案中有对应实现？     │
│  ✅ 假设清单 是否都有验证计划？                │
│  ✅ 约束清单 是否都被遵守？                    │
│  ✅ 边界场景 是否都有处理逻辑？                │
│  ✅ 未解决疑问 是否清零？                      │
│                                             │
│  检验结果:                                   │
│  ├── 全部通过 → 方案就绪，进入 Building       │
│  └── 有未覆盖项 → 回退补充方案 → 重新 Step C   │
└─────────────────────────────────────────────┘
```

#### 4.2.4 主动 QA 的触发规则

AI 必须在以下情况主动向用户提问，**不得自行假设**：

| 触发场景 | 示例疑问 |
|---------|---------|
| 需求存在歧义 | "吸氢模式下，流量阈值是 200ml/min 还是 300ml/min？" |
| 接口选择不唯一 | "使用 UART2 还是 UART4 连接新模块？" |
| 硬件引脚未明确 | "GPIO PA5 是否已被占用？空闲引脚有哪些？" |
| 异常处理策略 | "传感器故障时，是立即停机还是降级运行？" |
| 初始化顺序依赖 | "新模块的初始化必须在 WiFi 初始化之前还是之后？" |
| 性能权衡 | "优先响应速度还是优先功耗？" |
| 协议格式未指定 | "MQTT Topic 的命名规范是什么？" |
| 安全等级要求 | "该功能是否需要硬件看门狗保护？" |

**提问格式要求**：
- 每个疑问标注阻塞级别：**Blocker**（不回答无法继续）/ **Critical**（影响架构设计）/ **Clarify**（确认细节）
- 对于 Blocker 级别的问题，必须等用户答复后，才能继续方案设计
- 一次性列出所有疑问，避免多轮反复提问

#### 4.2.5 与 Plan Mode 的融合

| 规划协议要求 | 对应 Plan Mode 阶段 | 实现方式 |
|-------------|-------------------|---------|
| 方案初稿 | Step 2: 方案制定 | AI 基于已知信息生成技术方案草稿 |
| 主动 QA | Step 2: 需求澄清 | AI 列出疑问清单 → `ask_followup_question` → 用户逐条答复 |
| 检验文档生成 | Step 2: 方案定稿 | 将 QA 结果整理为结构化检验文档 |
| 自检验证 | Step 2 → Step 3 之间 | 对照检验文档逐条自检，通过后才进入 Ready |
| 用户确认 | Step 3: Ready 状态 | 用户在确认前可查看检验文档和自检结果 |

### 4.3 Subagents 自动调度

6 个 agentic Subagents 在 Building 阶段由主 Agent 按层自动调度：

```
主 Agent (Plan Mode Building)
    │
    ├── [跨层接口变更] → arch-reviewer
    ├── [MCAL 层代码]  → mcal-driver
    ├── [FreeRTOS 任务] → rtos-task
    ├── [业务逻辑]     → app-logic
    ├── [代码修改完成]  → code-checker
    └── [文档更新]     → doc-writer
```

### 4.4 Hooks 安全拦截

| Hook 类型 | 触发时机 | 作用 | 适用范围 | 可实现性 |
|-----------|---------|------|------|---------|
| **PreToolUse** | write_to_file/replace_in_file 前 | 禁止修改 drivers/ 原始驱动 / 禁止越层 import | 统一启用 | ⚠️ 规划中 (P2) |
| **PostToolUse** | 文件修改后 | 审计日志 / MISRA-C 基本规则检查 | 统一启用 | ⚠️ 规划中 (P3) |
| **SessionStart** | 会话启动时 | 自动注入项目上下文 (AGENTS.md + alwaysApply Rules) | 统一启用 | ✅ 已实现 |
| **Stop** | Agent 完成响应时 | 验证提示反馈 | 统一启用 | ✅ 已实现 (working memory 写入) |

> 当前 CodeBuddy 原生支持 SessionStart（通过 alwaysApply Rules）和 Stop（通过 working memory 写入）。PreToolUse/PostToolUse 为 CodeBuddy 规则体系中的 Hooks 能力，需在 P2/P3 阶段通过 `.codebuddy/rules/` 配置落地。

### 4.5 LOOP 执行循环 — 步骤级验证与回退

> 对应 agentic-workflow.mdc 模块五(迭代修正)的微循环层

当前 Phase 2 不能是纯线性的。`agentic-workflow.mdc` 定义的 Evaluator-Optimizer 循环实际包含两层粒度，需要拆分为 Phase 2 内部的"步骤级微循环"和 Phase 3 的"全局级宏循环"。

#### 4.5.1 两层 LOOP 的关系

```
┌─────────────────────────────────────────────────────────────┐
│                     Phase 2: ACT                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Building 阶段内部                         │  │
│  │                                                      │  │
│  │  Step N 执行 ──→ 验证标准检查 ──→ 通过?               │  │
│  │       ↑                          │                   │  │
│  │       │              否 → 回退重做 ──┘                │  │
│  │       │                                              │  │
│  │       是 → Step N+1                                    │  │
│  │                                                      │  │
│  │  ←── 微循环 (Per-Step Verification Loop) ──→         │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼ (全部步骤通过)                    │
│                      Finished                               │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     Phase 3: REFLECT                         │
│                                                             │
│  5维度评分 → score<90? → FIXABLE → 回退到 Phase 2 重新执行  │
│       ↑                                        │            │
│       └────────── 宏循环 (Global Reflection Loop) ┘          │
│                                                             │
│  ←── 最多迭代: 3轮 ──→                               │
└─────────────────────────────────────────────────────────────┘
```

**核心区别**：

| 维度 | 微循环 (Phase 2) | 宏循环 (Phase 3) |
|------|-----------------|-----------------|
| **粒度** | 单个步骤 | 整个任务 |
| **验证依据** | 方案中预设的"验证标准" | 5维度评分体系 |
| **触发时机** | 每步执行完成后立即检查 | 全部步骤完成后全局反思 |
| **回退范围** | 仅回退当前步骤 | 可能回退到任意 Phase |
| **循环上限** | 由步骤复杂度决定（不超过3次） | max 3 轮 |
| **谁执行** | 主 Agent 自检 | 主 Agent + code-checker Subagent |

#### 4.5.2 微循环工作方式

Building 阶段每完成一个 todolist 步骤后，主 Agent 必须执行：

```
Step N 完成
    │
    ▼
对照验证标准自检:
  Q1: 生成的文件内容是否符合该步骤的目标？
  Q2: 是否满足该步骤预设的验证标准？
  Q3: 是否引入了新的编译错误/警告？
  Q4: 是否影响了其他步骤的前置依赖？(若是 → 不能仅回退当前步骤)
    │
    ├── Q1-Q4 全部通过 → 标记 Step N 为 completed → 进入 Step N+1
    │
    ├── Q1-Q3 不通过 → 回退到 Step N 重新执行
    │   ├── 利用 Checkpoints 回退到该步执行前的状态
    │   ├── 分析失败原因，调整实现方式
    │   └── 重新执行（同一步骤最多重试 3 次）
    │        ├── 3次内通过 → 继续
    │        └── 3次仍不通过 → 标记为 BLOCKED，暂停等待用户决策
    │
    └── Q4 不通过 (跨步骤影响) → 不能仅回退当前步骤
        ├── 列出受影响的步骤 (如 Step X, Step Y)
        ├── 回退受影响步骤到 pending 状态
        └── 从 Step N 重新执行，然后重新执行受影响步骤
        (Q4 触发不计入当前步骤的 3 次重试上限)
```

#### 4.5.3 微循环 vs 宏循环的协同

两层循环不是冗余的，而是互补的：

- **微循环** 保证每一步的质量底线，问题在**最小范围**内解决，成本最低
- **宏循环** 保证整体方案的质量，发现步骤之间隐藏的集成性问题

举例：DS18B20 示例中：

```
微循环: Step 2 完成后，验证标准是"读取 ROM ID 正确"
         → ROM ID 读出来是 0xFF → 不通过 → 回退重做 GPIO 时序
         → 修正后 ROM ID 正确 → 通过 → 进入 Step 3

宏循环: 全部 6 步完成后，Reflection 发现"缺少 CRC 校验"
         → score 72 → FIXABLE → 回退到 Phase 2 追加 CRC 函数
```

#### 4.5.4 LOOP 策略（统一标准）

Phase 2 和 Phase 3 的统一 LOOP 策略：

| LOOP 类型 | 执行策略 |
|-----------|---------|
| **微循环 (Phase 2)** | **强制逐步骤验证回路**（每步对照验证标准，不通过→回退重做，同步骤最多重试3次） |
| **宏循环 (Phase 3)** | **3 轮迭代**（5维度评分 < 80 → FIXABLE → 回退到 Phase 2 重新执行） |

---

## 五、Phase 3: 流程反思 (REFLECT)

> 四阶段框架 Phase 3 融合 agentic-workflow.mdc 模块二(反射协议) + 模块四(多角色审查) + 模块五b(全局级宏循环)

**注意**：此处的"迭代修正"是**全局宏循环**，与 Phase 2 中每步执行后的"步骤级微循环"是两层不同粒度的 LOOP。微循环在 Phase 2 Building 阶段内运行，保证单步质量；宏循环在全部步骤完成后运行，保证全局质量。

### 5.1 Phase 3 反思策略（统一 Tier 3 标准）

> **Phase 3 不再按 Tier 分级**，所有任务统一按 Tier 3 最高标准执行反思。

| 维度 | 统一标准 |
|------|---------|
| **5维度评分** | ✅ **强制执行** |
| **多角色审查** | ✅ **启用**（Code Reviewer / Security Auditor / Architect / User Advocate） |
| **迭代修正** | **max 3 轮**（宏循环） |
| **code-checker** | ✅ **自动调度** |
| **Checkpoints 回退** | ✅ **关键节点** |

### 5.2 核心引擎: 反射协议 (5维度评分)

> 对应 agentic-workflow.mdc 模块二，统一强制执行

#### 5.2.1 评分体系

| 维度 | 检查内容 | 0-10 分 | 11-15 分 | 16-20 分 | 满分 |
|------|----------|---------|----------|----------|------|
| **正确性** | 逻辑、边界、错误处理 | 有 bug / 漏边界 | 基本正确，少量边缘情况 | 无已知缺陷 | 20 |
| **集成性** | 代码风格、导入、API兼容 | 风格冲突、破坏接口 | 基本一致，轻微差异 | 无缝集成 | 20 |
| **安全性** | 无硬编码密钥、无注入、输入校验 | 存在安全漏洞 | 基本安全，有改进空间 | 安全最佳实践 | 20 |
| **性能** | 时间复杂度、无冗余IO | 明显性能问题 | 可接受，有优化空间 | 性能最优 | 20 |
| **可维护性** | 命名、注释、单一职责、无重复 | 混乱难维护 | 基本可维护 | 清晰易读 | 20 |
| **总分** | | | | | **100** |

#### 5.2.2 针对性调整：嵌入式项目评分侧重

对于 HG_Ctrl_App 项目，评分时额外关注：

| 维度 | 嵌入式专项检查 |
|------|--------------|
| **正确性** | MISRA-C 违规？FreeRTOS 任务栈溢出？中断优先级嵌套？ |
| **集成性** | AUTOSAR 四层依赖方向正确？Application 未引用 MCAL？ |
| **安全性** | 看门狗配置？堆栈溢出保护？HardFault 处理？ |
| **性能** | ISR 执行时间？任务切换频率？DMA 缓冲区大小？ |
| **可维护性** | Doxygen 注释？变量对齐？区域划分？ |

#### 5.2.3 输出格式

```
[Reflection]
score: <0-100>
correctness: <0-20>  integration: <0-20>  security: <0-20>
performance: <0-20>  maintainability: <0-20>
missing: <遗漏了什么？N/A>
superfluous: <多做了什么？N/A>
verdict: <PASS | FIXABLE | BLOCKED>
```

#### 5.2.4 结论判定

| verdict | 条件 | 行为 |
|---------|------|------|
| **PASS** | score ≥ 90 | 进入 Phase 4 知识库保存 |
| **FIXABLE** | score < 90 且问题可自行修复 | 进入迭代修正 |
| **BLOCKED** | 缺少关键信息、超出能力范围、需用户决策 | 立即停止，输出 BLOCKED 报告 |

**关键规则**：
- 不要为了 PASS 虚高评分
- 发现安全漏洞时，**security ≤ 10 且 correctness ≤ 15**（双重惩罚，安全漏洞本身降低安全性，其引发的错误处理缺陷也降低正确性）
- BLOCKED 不是失败，是负责任的暂停

### 5.3 增强引擎: 多角色审查

> 对应 agentic-workflow.mdc 模块四

Phase 3 统一启用多角色审查，用不同角色视角审查方案：

| 角色 | 关注点 | 典型问题 |
|------|--------|----------|
| **Code Reviewer** | 代码质量、可读性、命名 | "这段代码半年后还能看懂吗？" |
| **Security Auditor** | 漏洞、认证、授权 | "输入校验是否完备？有无注入风险？" |
| **Architect** | 模块边界、耦合度、扩展性 | "改一个字段会影响多少模块？" |
| **User Advocate** | 用户视角、交互体验 | "运维人员能理解这个故障码吗？" |

使用协议：以 "作为 [角色名称]..." 开头进行视角切换，每角色 ≤ 3 条意见。

### 5.4 修正引擎: 迭代修正 (FIXABLE 时)

> 对应 agentic-workflow.mdc 模块五

#### 5.4.1 Evaluator-Optimizer 循环

```
┌─────────────────────────────────────────┐
│                                         │
│  Execution → Reflection(score<90?) → Fix│
│     ↑                                  │
│     └─── max=3轮 ───────────────────────│
│                                         │
│  任一时刻 score ≥ 90 → 立即退出成功      │
│  达到 max_iterations 仍 < 80 → BLOCKED  │
│  停滞检测: 连续2轮 improvement < 5 → BLOCKED │
└─────────────────────────────────────────┘
```

#### 5.4.2 迭代规则（统一标准）

| 规则 | 标准 |
|------|------|
| max_iterations | 3 |
| 停滞检测 | 连续2轮 improvement < 5 分 → BLOCKED |
| 每轮记录 | 分数变化 + 修改内容 + 改进幅度 |
| 每轮 diff report | ✅ 必输出 |

#### 5.4.3 BLOCKED 报告格式

```
[BLOCKED Report]
Final Score: <score>
Iterations: <n>
Blockers:
  1. <阻塞原因>
  2. ...
User Action Needed: <用户需要提供什么 / 做什么>
```

### 5.5 反思触发条件 (按项目模块)

| 触发条件 | 反思动作 |
|---------|---------|
| 修改 `source/Abstraction/` 接口 | arch-reviewer 审查架构一致性 |
| 新增 `.c` 文件 | code-checker 审查代码质量 |
| 修改 FreeRTOS 任务配置 | rtos-task 审查任务栈/优先级 |
| 修改 `source/Application/` | app-logic 审查状态机完整性 |
| 修改 `drivers/` | mcal-driver 审查寄存器配置 |

---

## 六、Phase 4: 知识库保存 (WRITE)

> 四阶段框架 Phase 4 — agentic-workflow.mdc 原来缺少的环节

### 6.1 Tier 分级写入策略

| 保存机制 | 存储位置 | Tier 1 | Tier 2 | Tier 3 |
|---------|---------|--------|--------|--------|
| Working Memory (每日日志) | `.codebuddy/memory/YYYY-MM-DD.md` | ✅ 强制 | ✅ 强制 | ✅ 强制 |
| MEMORY.md 更新 (长期事实) | `.codebuddy/memory/MEMORY.md` | ❌ | ⚠️ 有长期价值时 | ✅ 强制 |
| Plan 归档 | `.codebuddy/plans/` | ❌ | ⚠️ 如果用了Plan | ✅ 强制 |
| AGENTS.md 更新 | `docs/AGENTS.md` | ❌ | ⚠️ 模块变更时 | ✅ 强制 |
| SessionEnd Hook | 自定义脚本 | ❌ | ❌ | ✅ 推荐 |
| PreCompact Hook | `.codebuddy/context_history/` | ❌ | ❌ | ✅ 推荐 |

### 6.2 保存流水线

```
日常工作
    │
    ▼
Working Memory (每日日志 .codebuddy/memory/YYYY-MM-DD.md)
    │
    ├── [Refinement 子阶段] ← 自动触发
    │    ├── R1-R2: 读取日报 → 四维提炼
    │    ├── R3: Confidence H/M/L 标注
    │    ├── R4: 去重检查
    │    ├── R5: 分级写入
    │    │    ├── H → MEMORY.md (直接写入)
    │    │    ├── M → MEMORY.md [AI-Inferred]
    │    │    └── L → .draft/ (隔离待验证)
    │    └── R6: TL;DR 输出 (≤3 条)
    │
    ▼
MEMORY.md (长期记忆 — 累积式知识库)
    │  (超过 200 行 → 归档)
    ├── memory/topics/architecture.md
    ├── memory/topics/ai-workflow.md
    ├── memory/topics/bug-fixes.md
    └── ...
    │
    │  (结构性变更 → 更新)
    ▼
AGENTS.md (项目知识索引)
    │
    ▼
Plan 归档 (.codebuddy/plans/) — 技术方案持久化，可被后续任务引用
```

### 6.3 各机制详细说明

| CodeBuddy 机制 | 保存内容 | 保存时机 | 存储位置 |
|---------------|---------|---------|---------|
| **Plan 归档** | 技术方案 + 任务列表 + Reflection结果 | Plan Finished | `.codebuddy/plans/*.md` |
| **Working Memory** | 每次工作的摘要日志 | Agent 主动写入 | `.codebuddy/memory/YYYY-MM-DD.md` |
| **Memory 持久化** | 重要决策/偏好/事实 | Agent 调用 update_memory | SQLite (IDE 管理) |
| **AGENTS.md 更新** | 项目知识索引 | 重大变更时手动 | `docs/AGENTS.md` |
| **SessionEnd Hook** | 会话状态报告 | 会话结束时 | 自定义脚本 |
| **PreCompact Hook** | 完整对话历史 | 上下文压缩前 | `.codebuddy/context_history/` |

### 6.4 AGENTS.md 更新触发条件

当发生以下变更时，应更新 `docs/AGENTS.md`：
- 新增模块/文件
- 修改关键接口
- 变更架构设计
- 新增外设映射
- **新增 Plan 归档后（引用到 AGENTS.md 中）**

### 6.5 Phase 4 Refinement 子阶段 — 知识提炼引擎

> 在 Phase 4 标准保存流水线之后，增加**自动化知识提炼子阶段**，解决"只记录不提炼"的问题。  设计日期: 2026-07-13

#### 6.5.1 触发条件与执行协议

Phase 4 WRITE（Working Memory 写入）完成后，自动触发 Refinement 子阶段：

```
Phase 4 WRITE (Working Memory 写入)
    │
    ▼
┌────────────────────────────────────────────────┐
│  Refinement 子阶段                              │
│                                                │
│  R1: 读取当日日报 → 检查是否为空（E1边界）       │
│  R2: 四维提炼 → 技术决策/设计约束/发现模式/风险  │
│  R3: Confidence 标注 → H/M/L 三级标记           │
│  R4: 去重检查 → 对比现有 MEMORY.md 条目          │
│  R5: 分级写入 → H→直接写/M→带标签/L→.draft/     │
│  R6: TL;DR 输出 → ≤3句话摘要给用户              │
│                                                │
│  Token预算: ≤5000（超出则触发E6熔断）             │
└────────────────────────────────────────────────┘
    │
    ▼
MEMORY.md (累积知识库) / .draft/ (待验证条目)
```

**执行协议 — 6 步骤详表：**

| 步骤 | 动作 | 输入 | 输出 | 验证标准 |
|------|------|------|------|---------|
| **R1** | 读取当日日报 | `memory/YYYY-MM-DD.md` | 日报文本 | 日报文件存在且非空；若为空→跳过 Refinement → 输出 "本日无新增知识条目" |
| **R2** | 四维提炼 | 日报内容 | 结构化条目列表（每条含：维度标签 + 内容摘要 + 来源行引用） | 每条可追溯到日报原文 |
| **R3** | Confidence 标注 | 提炼条目 | 带 H/M/L 标记的条目 | 判定依据明确（见 6.5.2） |
| **R4** | 去重检查 | 新条目 + 现有 MEMORY.md | 去重后的新条目 | 相似度 > 80% 视为重复，合并日期标签 |
| **R5** | 分级写入 | 去重条目 | MEMORY.md 增量更新 | H级直接写入 / M级追加 `[AI-Inferred]` 标签 / L级写入 `.draft/` |
| **R6** | TL;DR 输出 | 提炼结果 | 用户可见摘要 | ≤3 条要点，≤ 3 句话 |

#### 6.5.2 Confidence Level 知识可信度标记体系

> 核心防御机制：防止 AI 提炼幻觉永久污染 MEMORY.md。

| 级别 | 判定依据 | 写入策略 | 消费行为 | 示例 |
|------|---------|---------|---------|------|
| **H (High)** | 代码事实、用户明确确认的技术决策、编译验证过的参数 | **直接写入 MEMORY.md** | 后续 AI 可直接信任 | "PASS 阈值 = 90"；"MCU 型号 HC32F460PETB" |
| **M (Medium)** | AI 推理总结的模式、最佳实践归纳、从多个日报推断的规律 | **写入 MEMORY.md**，追加 `[AI-Inferred]` 标签 | 后续 AI 可参考但需交叉验证 | "项目倾向使用 FreeRTOS 临界区保护跨任务共享数据" |
| **L (Low)** | 不确定的推断、单次观察的暂定结论、待验证的假设 | **写入 `memory/.draft/YYYY-MM-DD.md`**，不合并到 MEMORY.md | 后续 AI 读取 .draft/ 时可验证升级 | "怀疑 ESP_Abstraction.c 中 CWJAP 重连循环存在死锁风险" |

**L 级别升级路径：**
```
.draft/条目
    │
    ├── 下一轮 AI 消费 .draft/ 时发现代码证据确认 → 升级为 H，合并到 MEMORY.md
    ├── 下一轮 AI 发现矛盾证据 → 降级为错误，从 .draft/ 删除
    └── 30 天未被消费 → 自动过期，从 .draft/ 清理
```

**M 级别降级路径：**
- M 级别条目若在 60 天内被代码变更证伪 → 追加 `[Deprecated: YYYY-MM-DD, 原因]`
- 若被确认 → 移除 `[AI-Inferred]` 标签，升级为 H 级

#### 6.5.3 MEMORY.md 归档与增长控制

**归档阈值：** MEMORY.md > 200 行时触发归档。

**归档策略：**
- 按主题拆分为 `memory/topics/<topic>.md`
- MEMORY.md 精简为：`基础信息块(项目信息+编码规范)` + `最近 3 个月活跃条目` + `topics/ 索引`
- 每日 Refinement 前检查行数，超阈值先归档再提炼

**归档主题分类与映射：**

| 主题文件 | 内容范围 | MEMORY.md 现有章节映射 |
|---------|---------|----------------------|
| `topics/architecture.md` | 架构设计决策、分层规则、接口约束 | "项目基本信息" + "编码规范"（架构部分） |
| `topics/ai-workflow.md` | Agentic Workflow 参数、流程变更、PASS阈值 | "Agentic Workflow 关键参数" |
| `topics/coding-standards.md` | 编码规范、命名约定、MISRA-C 要求 | "编码规范" |
| `topics/bug-fixes.md` | Bug 修复记录、根因分析、经验教训 | （新增） |
| `topics/refactoring.md` | 重构历史、模块演进、接口变更记录 | （新增） |
| `topics/communication.md` | WiFi/MQTT/DWIN 通信相关决策 | （新增） |

**归档后的 MEMORY.md 结构预览：**
```markdown
# 项目长期记忆

## 项目基本信息
... (始终保留)

## 编码规范
... (始终保留)

## 活跃知识 (2026-Q3)
... (最近3个月的提炼条目)

## 知识归档索引
| 主题 | 归档文件 | 最后更新 |
|------|---------|---------|
| 架构设计 | topics/architecture.md | 2026-07-13 |
| AI 工作流 | topics/ai-workflow.md | 2026-07-13 |
| ...
```

#### 6.5.4 边界场景处理矩阵

| ID | 场景 | 触发条件 | 处理逻辑 | 涉及步骤 |
|----|------|---------|---------|---------|
| **E1** | 空日报 | R1 读取日报内容为空或仅琐事 | 跳过 Refinement，输出 "📋 本日无新增知识条目"，正常结束 | R1 |
| **E2** | 重复条目 | R4 去重时发现新条目与已有条目相似度 > 80% | 合并日期标签 `(2026-07-12, 2026-07-13)`，不创建重复条目；若内容有补充则追加到已有条目 | R4 |
| **E3** | MEMORY.md 溢出 | R1 前置检查行数 > 200 | 触发归档：按主题拆分到 `memory/topics/`，MEMORY.md 精简；归档完成后继续提炼 | R1(前置) |
| **E4** | AI 提炼幻觉 | R3 标注 L 级别的不确定条目 | L 级别写入 `.draft/` 隔离，不入 MEMORY.md；M 级别标记 `[AI-Inferred]` 供后续验证；H 级别需有明确代码引用 | R3, R5 |
| **E5** | 知识条目冲突 | R4 去重时发现新旧条目结论矛盾 | 保留最新版本 + 追加历史注释 `[Previously: 旧结论]`；无法自动裁决时标记为 M 级别 `[Needs-Review]`，等待用户确认 | R4, R5 |
| **E6** | Token 预算超限 | 单次 Refinement 预估 Token > 5000 | 熔断降级：仅执行 R1+R2（读取+粗提炼），跳过 R3-R5 精细加工；提炼结果标记 `[Token-Throttled]` 写入日报末尾，下轮优先处理 | R2(中断) |

#### 6.5.5 MVP 试运行策略

为避免一次性引入全部复杂度，分两阶段推进：

**MVP 阶段（前 2 周，2026-07-13 ~ 2026-07-27）：**

| 维度 | MVP 范围 | 全量范围（暂不启用） |
|------|---------|-------------------|
| 提炼维度 | 仅"技术决策" + "设计约束" 2 维 | "发现模式" + "风险" + 2 维 |
| Confidence | 仅 H / M 两级 | L 级 + .draft/ 隔离 |
| 归档 | 不启用（MEMORY.md 尚在增长期） | topics/ 拆分 + 200行阈值 |
| Token 熔断 | 不启用（MVP 规模可控） | 5000 token 上限 |
| 人工回检 | **每周一次**，回检 H 级别条目准确率 | 按需抽查 |

**MVP 验收标准（2026-07-27 评估）：**
1. H 级别条目准确率 ≥ 80%（无事实性错误）
2. 无提炼导致的知识丢失（对比日报原文）
3. 用户感知到"机器在帮我积累知识"的价值

**全量阶段（MVP 通过后）：**
- 扩展提炼维度到 4 维
- 启用 L 级 `.draft/` 隔离 + 30天过期
- 启用 MEMORY.md 归档（>200行触发）
- 启用 Token 熔断（5000 token）

### 6.6 Phase 4 完整链路总览

```
Phase 4: WRITE
    │
    ├── Working Memory 写入 (.codebuddy/memory/YYYY-MM-DD.md) ← 强制
    ├── MEMORY.md 更新 (长期事实)                              ← Tier 2+ 强制
    ├── Plan 归档 (.codebuddy/plans/)                          ← Tier 3 强制
    ├── AGENTS.md 更新                                          ← 重大变更时
    │
    └── [Refinement 子阶段] ← 每次 Phase 4 后自动触发
         │
         ├── R1: 读取当日日报 → 空？→ E1跳过
         ├── R2: 四维提炼
         ├── R3: Confidence H/M/L 标注
         ├── R4: 去重检查 → 重复？→ E2合并 / 冲突？→ E5标记
         ├── R5: 分级写入 → H→MEMORY.md / M→MEMORY.md[AI-Inferred] / L→.draft/
         └── R6: TL;DR 输出 (≤3条要点)
```

---

## 七、融合后的完整工作流示例

以"新增 DS18B20 温度传感器"为例，演示 Tier 3 完整流程：

### 7.1 复杂度判定 → Tier 3

```
判定: 涉及≥6个文件 → 新设计决策 → 跨层修改 → Tier 3
选择: 完整四阶段流程
```

### 7.2 Phase 1: READ (完整 + 网络搜索)

```
1. AGENTS.md 自动加载 → MCU: HC32F460, 外设映射
2. L2 Skills 加载 → agentic-workflow.md 行为规则 (当前唯一可用 Skill)
3. L4 Memory 加载 → 已有6个Subagent, OneWire空闲
4. L3 主动搜索 → OneWire总线未使用, GPIO PA5空闲
5. L5 网络搜索 (本地知识不足):
   → web_search "HC32F460 GPIO bit-bang OneWire timing"
   → web_search "DS18B20 datasheet CRC8 algorithm"
   → web_fetch "HC32F460 Timer6 microsecond delay configuration"
   → 搜索结果记录到 Working Memory

> 注: L1-always-编码规范.mdc / L1-always-架构约束.mdc 为 P1 待创建，
> 当前通过 AGENTS.md 中的 MISRA-C/AUTOSAR 说明 + agentic-workflow Skill 覆盖这些约束。
```

### 7.3 Phase 2: ACT (Plan Mode + 规划协议 + 主动QA + 检验文档)

```
Plan Mode Prepare → 需求澄清 → 方案初稿
   │
   ├── Step A: 主动QA
   │   ❓ Q1 [Blocker]: DS18B20 采样周期要求？1s/5s/10s？
   │       → 用户: 每 2 秒采样一次
   │   ❓ Q2 [Critical]: 传感器故障时系统行为？
   │       → 用户: 报警但不影响主流程，显示 "---"
   │   ❓ Q3 [Critical]: 温度上报到 MQTT 还是仅本地显示？
   │       → 用户: 仅本地 DWIN 屏显示
   │   ❓ Q4 [Clarify]: 故障阈值是否需要通过 NvManager 可配置？
   │       → 用户: 是的，默认 -10°C ~ 85°C
   │   ❓ Q5 [Clarify]: 是否需要在工厂测试模式中加入传感器自检？
   │       → 用户: 需要，检测短路/断路
   │
   ├── Step B: 生成检验文档
   │   # 检验文档: DS18B20温度传感器
   │   ## 1. 已确认需求清单
   │   | R1  | 2秒周期采集温度 | QA-Q1 | ✅ |
   │   | R2  | 故障时显示"---"，不影响主流程 | QA-Q2 | ✅ |
   │   | R3  | 仅本地DWIN显示，不上报MQTT | QA-Q3 | ✅ |
   │   | R4  | 故障阈值可通过NvManager配置 | QA-Q4 | ✅ |
   │   | R5  | 工厂测试模式包含传感器自检 | QA-Q5 | ✅ |
   │   ## 2. 技术假设清单
   │   | H1  | GPIO PA5 空闲可用 | web_search(HC32F460) | 低 |
   │   | H2  | OneWire 时序可用 GPIO 位操作实现 | DS18B20 datasheet | 低 |
   │   | H3  | Timer6 用于微秒延时 | HC32F460 参考手册 | 中 |
   │   ## 3. 约束条件清单
   │   | C1  | Driver 放在 Abstraction 层 | 四层架构规则 | ✅ |
   │   | C2  | 遵循 MISRA-C:2012 | 编码规范 | ✅ |
   │   ## 4. 边界与异常场景
   │   | E1  | 传感器未连接 → 检测为故障 | 显示"---"，报警 | ✅ |
   │   | E2  | 传感器短路 → 工厂检测 | 报 FAULT_SENSOR_SHORT | ✅ |
   │   | E3  | 温度超限(-10°C~85°C) → 报警 | 记录故障码 | ✅ |
   │   ## 5. 未解决疑问
   │   (无)
   │
   ├── Step C: 自检验证
   │   ✅ R1-R5 均在方案步骤中有对应实现
   │   ✅ H1-H3 均通过 web_search 验证
   │   ✅ C1-C2 在方案文件的四层位置和编码规范中体现
   │   ✅ E1-E3 在错误处理步骤中有明确处理逻辑
   │   ✅ 未解决疑问清单为空
   │   → 检验通过！进入 Ready

Plan Mode Ready → 用户确认检验文档 → Building
   │
   ├── 步骤ID: T1, 目标: MCAL GPIO PA5配置, 文件: drivers/gpio/*
   │    验证标准: OneWire时序通过示波器测量
   │
   ├── 步骤ID: T2, 目标: DS18B20驱动 + CRC校验, 文件: source/Abstraction/DS18B20_Driver.*
   │    依赖: T1, 验证标准: 读取ROM ID正确 + CRC校验通过
   │
   ├── 步骤ID: T3, 目标: 温度采集任务, 文件: source/Application/HealthMonitor/
   │    依赖: T2, 验证标准: 每2秒采样一次，数据正确
   │
   ├── 步骤ID: T4, 目标: 故障检测(短路/断路/超限), 文件: source/Application/FaultDiag/
   │    依赖: T2, 验证标准: 各故障场景正确触发
   │
   ├── 步骤ID: T5, 目标: DWIN屏幕显示, 文件: source/Application/ScreenManager/
   │    依赖: T3, 验证标准: 屏幕正确显示温度值或"---"
   │
   ├── 步骤ID: T6, 目标: 工厂测试自检, 文件: source/Application/SelfCheck/
   │    依赖: T2, 验证标准: 传感器短路/断路检测正确
   │
   └── 规划审查: ✅ 依赖清晰 ✅ T1可并行MCAL配置 ✅ 回退方案可行
        ✅ 所有检验文档要求均已覆盖

Building → 主Agent按todolist执行 (含微循环LOOP) ...
   ├── T1 → 自动启动 mcal-driver Subagent
   │      → 验证: OneWire时序正确? → 通过 ✅ → 进入T2
   ├── T2 → PreToolUse Hook 验证
   │      → 验证: ROM ID正确? → 失败 ❌ (读到0xFF)
   │      → 微循环: 回退T2 → 修正GPIO时序 → 重新执行
   │      → 验证: ROM ID正确? → 通过 ✅ → 进入T3
   ├── T3-T5 → app-logic + rtos-task Subagents
   │          → 逐步骤验证均通过 ✅
   └── T6 → code-checker 自动审查 → 全部步骤完成 → Finished
```

### 7.4 Phase 3: REFLECT (全局宏循环: 5维度评分 + 迭代修正)

**第一轮 Reflection (宏循环):**

```
[Reflection]
score: 72
correctness: 16  integration: 18  security: 16
performance: 12  maintainability: 10
missing: DS18B20 CRC校验未实现 → 影响正确性
superfluous: N/A
verdict: FIXABLE
```

**迭代修正 (Tier 3, 第1轮):**

```
diff report:
  + 新增 DS18B20_CRC8() 校验函数
  + 温度读取后增加校验分支，校验失败重试1次
  + 添加 CRC 校验失败的错误码 FAULT_SENSOR_CRC_ERROR
```

**第二轮 Reflection:**

```
[Reflection]
score: 88
correctness: 18  integration: 18  security: 16
performance: 16  maintainability: 20
missing: N/A
superfluous: N/A
verdict: PASS
```

**多角色审查 (Tier 3 可选):**

```
作为 Architect:
  1. DS18B20_Driver 正确放在 Abstraction 层 ✅
  2. 依赖方向: Application → Service → Abstraction → MCAL ✅
  3. 建议CRC失败后增加退避，避免连续快速重试

作为 Security Auditor:
  1. 温度传感器数据越界检查 ✅
  2. 故障阈值可通过 NvManager 配置 ✅
  3. 无外部输入，注入风险极低 ✅
```

### 7.5 Phase 4: WRITE (完整)

```
1. Working Memory 追加:
   "新增DS18B20模块, Reflection PASS(88), 包含CRC校验"

2. Memory 持久化:
   "OneWire总线使用GPIO PA5, Timer6做微秒延时"

3. Plan 归档:
   .codebuddy/plans/ds18b20-temperature-sensor.md
   包含: 技术方案 + 任务列表 + Reflection记录 + 迭代历史

4. AGENTS.md 更新:
   外设映射新增: GPIO PA5 → DS18B20 OneWire
   新增模块索引条目

5. SessionEnd Hook:
   生成摘要: 6文件修改, 2新文件, Reflection 1轮修正, PASS
```

---

## 八、现有基础设施整合清单

### 8.1 已有资源状态

| 资源 | 文件 | 框架阶段 | 状态 |
|------|------|---------|------|
| AGENTS.md | `docs/AGENTS.md` | Phase 1 (READ) | ✅ 已有 |
| agentic-workflow.mdc | `.codebuddy/rules/agentic-workflow.mdc` | Phase 2+3 (执行规范) | ✅ 已有，建议改为 `alwaysApply: true` |
| 6 Subagents | `.codebuddy/agents/*.md` | Phase 2 (ACT) | ✅ 已有 |
| Working Memory | `.codebuddy/memory/` | Phase 3+4 | ✅ 运行中 |
| 融合方案文档 | 本文件 | Phase 1 (READ) | ✅ 新增 |

### 8.2 推荐修改 (不改代码，仅配置)

| 优先级 | 动作 | 说明 |
|--------|------|------|
| **P0** | 将 agentic-workflow.mdc 改为 `alwaysApply: true` | 复杂度判定+反射评分需要始终可用 |
| **P0** | 所有 Phase 2 任务使用 Plan Mode | 零配置，习惯养成 |
| **P1** | 创建 `L1-always-编码规范.mdc` | MISRA-C/AUTOSAR 规范始终注入 |
| **P1** | 创建 `L1-always-架构约束.mdc` | 四层依赖规则始终注入 |
| **P2** | 创建 PreToolUse Hook | 防止越层修改 |
| **P2** | 创建 `L2-reference-*.mdc` | HC32芯片手册 + FreeRTOS模式 |
| **P3** | 创建 PostToolUse + SessionEnd Hooks | 审计 + 自动保存 |
| **P3** | 配置 MCP Server | 外部知识库连接 |

### 8.3 不需要变更的内容

- **6 Subagents**：配置完整，覆盖四层结构
- **AGENTS.md**：结构完整
- **Working Memory 模式**：运行良好

---

## 九、快速参考卡片

```
复杂度判定 (仅影响 Phase 1 和 Phase 4):
  Tier 1 (单文件/问答) → READ(简化) + ACT(跳过本流程) + WRITE(简化)
  Tier 2 (多文件/新功能) → READ(标准) + ACT+REFLECT(统一标准) + WRITE(标准)
  Tier 3 (架构/重构) → READ(完整+L5网络) + ACT+REFLECT(统一标准) + WRITE(完整)

Phase 1 知识加载 (五层):
  L1 始终层 (AGENTS.md+Rules) → L2 按需层 (Skills) → L3 主动层 (@Docs/MCP)
  → L4 记忆层 (Memory) → L5 网络层 (web_search兜底)

Phase 2 规划流程 (三步闭环):
  Step A: 主动QA → 识别所有不确定点 → 逐条与用户核对 (Blocker/Critical/Clarify分级)
  Step B: 生成检验文档 → 需求清单 + 假设清单 + 约束清单 + 边界场景 + 未解决疑问
  Step C: 自检验证 → 对照检验文档逐条检查 → 全部通过才进入 Building

Phase 2+3 统一标准 (Tier 3 最高标准):
  ACT = Plan Mode强制 + 主动QA + 检验文档 + 自检 + Subagents全开 + Hooks全开 + 微循环
  REFLECT = 5维度评分 + 多角色审查(4角色各≤3条) + 宏循环max 3轮

两层 LOOP:
  微循环 (Phase 2) = 每步执行后对照验证标准, 不通过→回退重做(最多3次)
  宏循环 (Phase 3) = 全局5维度评分<80 → FIXABLE → 回退到Phase 2重新执行(max 3轮)

Reflection 判定:
  PASS (score ≥ 90)  → 进入 WRITE
  FIXABLE (score < 90) → 宏循环迭代修正
  BLOCKED (无法继续) → 报告受阻原因, 等待用户决策

Phase 4 Refinement 子阶段 (每次 Phase 4 后自动触发):
  R1: 读日报 → R2: 四维提炼(决策/约束/模式/风险)
  → R3: Confidence(H/M/L) → R4: 去重
  → R5: 分级写入 (H→MEMORY.md / M→[AI-Inferred] / L→.draft/)
  → R6: TL;DR摘要 ≤3条
  MVP阶段(前2周): 仅2维度 + H/M两级 + 每周回检准确率
  全量阶段: 4维度 + L级.draft/隔离 + 归档(>200行→topics/) + Token熔断(5000)

Refinement 边界场景:
  E1空日报跳过 / E2重复合并日期标签 / E3>200行归档topics/
  E4 L级幻觉隔离.draft/ / E5冲突标记[Previously:] / E6 Token>5000熔断[Token-Throttled]

关键约束:
  不要虚高评分 | 安全漏洞 security ≤ 10 | BLOCKED 不是失败
  规划协议 = 步骤ID + 目标 + 文件 + 依赖 + 验证标准
  主动QA = 有疑问必问用户, 不自作假设, Blocker级必须等答复
  检验文档 = 方案验收标准, 自检不通过不进 Building
  迭代停滞检测: 连续2轮 improvement < 5 → BLOCKED
```

---

## 十、框架收益总结

| 维度 | 仅 agentic-workflow.mdc | 仅四阶段框架 | 融合后 |
|------|------------------------|-------------|--------|
| **知识加载** | 无定义 | L1-L4 分层 | ✅ 分层 + Tier 分级深度 |
| **任务分级** | ✅ Tier 1/2/3 | 缺少自动判定 | ✅ Tier 决定四阶段深度 |
| **方案规划** | 抽象规划结构 | Plan Mode 完整流程 | ✅ Plan Mode + 规划协议约束 |
| **任务执行** | 无执行规范 | Subagents + Hooks | ✅ 完整的执行编排 |
| **质量评分** | ✅ 5维度 0-100 | 5个反思节点 | ✅ 定量评分 + 触发条件 |
| **迭代修正** | ✅ max 3轮 | 无 | ✅ 按 Tier 分级迭代 |
| **多角色审查** | ✅ 4角色 | 纯 Subagent | ✅ 角色视角 + Subagent |
| **知识沉淀** | 无 | 6种保存机制 | ✅ 分层写入 + Refinement 自动提炼 |
| **边界处理** | ✅ 6种场景 | 无 | ✅ 全场景覆盖 |
| **安全防护** | 无 | Hooks + Checkpoints | ✅ 工具级安全拦截 |

---

*融合方案完成。下一步按 P0 → P1 → P2 → P3 优先级逐步落地。*
