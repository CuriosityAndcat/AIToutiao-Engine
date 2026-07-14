# HG_Ctrl_App — 完整 Agentic Workflow 框架方案

> 基于 CodeBuddy IDE 全量能力，针对氢发生器嵌入式控制系统设计的闭环 Agent 工作流  
> 设计日期: 2026-07-13 | 不做任何代码变更，纯框架设计方案

---

## 一、框架总览

本框架将 CodeBuddy IDE 的全部能力整合为一个 **四阶段闭环流水线**，实现从知识摄入到知识沉淀的完整生命周期：

```
                    ┌─────────────┐
                    │  用户需求/   │
                    │  定时任务    │
                    └──────┬──────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      ▼                      │
    │  ┌──────────────────────────────────────┐   │
    │  │     Phase 1: 知识库读取 (READ)        │   │
    │  │  AGENTS.md + Rules + Memory + MCP    │   │
    │  └──────────────────┬───────────────────┘   │
    │                     ▼                       │
    │  ┌──────────────────────────────────────┐   │
    │  │     Phase 2: Agent工作流 (ACT)       │   │
    │  │  Plan Mode → Subagents → Hooks       │   │
    │  └──────────────────┬───────────────────┘   │
    │                     ▼                       │
    │  ┌──────────────────────────────────────┐   │
    │  │     Phase 3: 流程反思 (REFLECT)      │   │
    │  │  Checkpoints + CodeReview + Audit    │   │
    │  └──────────────────┬───────────────────┘   │
    │                     ▼                       │
    │  ┌──────────────────────────────────────┐   │
    │  │     Phase 4: 知识库保存 (WRITE)      │   │
    │  │  Memory + Plans + AGENTS.md 更新     │   │
    │  └──────────────────────────────────────┘   │
    │                     │                       │
    └─────────────────────┼───────────────────────┘
                          │
                          ▼
                    ┌──────────┐
                    │ 输出交付  │
                    │ 知识沉淀  │
                    └──────────┘
```

---

## 二、Phase 1: 知识库读取（READ）

### 2.1 机制映射

CodeBuddy 提供了多层级的上下文注入机制，按照**加载时机**和**加载策略**分为四个层次：

| 层级 | CodeBuddy 机制 | 加载时机 | 加载策略 | 作用 |
|------|---------------|---------|---------|------|
| **L1 始终层** | `AGENTS.md` / `CODEBUDDY.md` | 每次会话启动 | 自动全文加载 | 项目全局知识索引 |
| **L1 始终层** | Rules (`alwaysApply: true`) | 每次会话启动 | 自动注入上下文头部 | 编码规范、架构约束 |
| **L2 按需层** | Rules (`agentic request`) | Agent 判断需要时 | 只加载名称+描述，按需读取正文 | 参考文档、使用指南 |
| **L2 按需层** | Skills (`references/`) | Skill 被触发后 | 按需加载 | 领域专业知识 |
| **L3 主动层** | `@Docs` / MCP | 用户或Agent主动调用 | 流式查询 | 外部知识库 |
| **L3 主动层** | `@Files` / `@Git` | 用户主动引用 | 精确选择 | 文件/代码/变更上下文 |
| **L4 记忆层** | Memory (`update_memory`) | 每次会话启动 | 自动注入所有记忆 | 跨会话偏好和项目状态 |
| **L4 记忆层** | Working Memory Files | 会话中按需读取 | Agent 主动 read_file | 每日工作日志 |

### 2.2 当前项目配置

| 配置项 | 文件路径 | 状态 |
|--------|---------|------|
| AGENTS.md | `docs/AGENTS.md` | ✅ 已有，自动加载 |
| Rules | `.codebuddy/rules/agentic-workflow.mdc` | ✅ 已有 |
| Subagents×6 | `.codebuddy/agents/*.md` | ✅ 已有 |
| Memory | `.codebuddy/memory/MEMORY.md` | ✅ 已有 |
| Daily Memory | `.codebuddy/memory/YYYY-MM-DD.md` | ✅ 运行中 |

### 2.3 推荐增强：分层 Rules 体系

当前只有 1 个 rule 文件。建议扩展为三层 Rules 体系：

```
.codebuddy/rules/
├── L1-always-编码规范.mdc       # alwaysApply: true  → MISRA-C/AUTOSAR 规范
├── L1-always-架构约束.mdc       # alwaysApply: true  → 四层依赖规则/禁止越层
├── L2-reference-HC32芯片手册.mdc # agentic request   → MCU寄存器/外设参考
├── L2-reference-FreeRTOS模式.mdc # agentic request   → 任务同步/通信模式
├── L3-manual-安全审查清单.mdc    # manual            → @引用触发
└── L3-manual-代码审查模板.mdc    # manual            → @引用触发
```

**原理**：
- `alwaysApply` 的 Rules 始终注入上下文头部（不占对话窗口，是独立的 System Prompt 前缀）
- `agentic request` 的 Rules 只在 Agent 判断相关时按需加载全文（节省 Token）
- `manual` 的 Rules 需要用户或 Agent 通过 `@` 显式引用

### 2.4 推荐增强：MCP 知识库连接

当前项目没有配置 MCP Server。建议添加：

| MCP Server | 用途 | 配置方式 |
|------------|------|---------|
| GitHub MCP | 查询 HC32 官方 SDK/BSP 更新 | MCP Market 一键安装 |
| 自定义 HC32 MCP | 封装寄存器手册/数据手册查询 | 自定义 stdio 类型 Python 脚本 |

---

## 三、Phase 2: Agent 工作流（ACT）

### 3.1 核心机制：Plan Mode 五步生命周期

这是 CodeBuddy 最核心的 Agentic Workflow 引擎。每个复杂任务都应走这个流程：

```
需求输入
    │
    ▼
┌──────────────────────────────────────────────────────┐
│ Step 1: 需求澄清 (Prepare 状态)                        │
│   - AI 提出 1-2 个关键问题确认技术栈/功能范围/约束条件    │
│   - 用户回答 + 粘贴需求文档/设计截图                     │
│   - AI 生成需求总结 → 用户确认                         │
├──────────────────────────────────────────────────────┤
│ Step 2: 方案制定 (Prepare 状态)                        │
│   - Plan 搜索现有代码仓库                               │
│   - 生成完整方案：需求分析 + 技术方案 + 任务列表          │
│   - AI 智能编排 MCP/Skill/SubAgent                     │
│   - 输出：架构设计 + 数据流 + 可执行步骤清单              │
├──────────────────────────────────────────────────────┤
│ Step 3: 方案确认 (Ready 状态)                          │
│   - 用户审阅并编辑方案（修改技术选型/调整任务/补充约束）    │
│   - 在代码生成前修正方向，避免后期重构                    │
│   - 关键检查：是否符合 MISRA-C？四层依赖是否正确？        │
├──────────────────────────────────────────────────────┤
│ Step 4: 方案实施 (Building 状态)                       │
│   - 按 todolist 逐步执行                               │
│   - 主 Agent 自动调度 agentic Subagents（见 3.2）       │
│   - Hooks 完成安全拦截和日志记录（见 3.3）               │
│   - 每步可中断/调整/切换 Craft Mode 快速修复             │
├──────────────────────────────────────────────────────┤
│ Step 5: 方案完成 (Finished 状态)                       │
│   - 自动保存 Plan 为 Markdown → .codebuddy/plans/     │
│   - 代码变更可通过 Checkpoints 回溯                    │
│   - Plan 可作为后续任务的上下文复用                      │
└──────────────────────────────────────────────────────┘
```

### 3.2 核心机制：agentic Subagents 自动调度

项目中已创建 6 个 agentic 模式的 Subagents。它们在 **Building 阶段由主 Agent 自动调度**：

```
主 Agent (Plan Mode)
    │
    ├── [检测到跨层接口变更] → 自动启动 arch-reviewer
    │      └── 独立上下文窗口，不污染主会话
    │      └── 完成后返回审查结果
    │
    ├── [检测到 MCAL 层代码] → 自动启动 mcal-driver
    │      └── 专注：GPIO/ADC/UART/SPI/I2C/DMA 驱动
    │
    ├── [检测到 FreeRTOS 任务] → 自动启动 rtos-task
    │      └── 专注：任务创建/同步/通信/调度
    │
    ├── [检测到业务逻辑] → 自动启动 app-logic
    │      └── 专注：状态机/工作模式/故障诊断
    │
    ├── [完成代码修改后] → 自动启动 code-checker
    │      └── 专注：MISRA-C/内存/并发/代码质量
    │
    └── [需要文档更新] → 自动启动 doc-writer
           └── 专注：Doxygen/Markdown 文档
```

**关键特性**：
- **独立上下文**：每个 Subagent 有自己的上下文窗口，不会污染主 Agent 的对话
- **不可中途干预**：agentic 模式下要么等完成，要么手动中断
- **工具权限控制**：每个 Subagent 只开放其需要的工具（如 code-checker 无 write 权限）
- **跨项目复用**：通过 user 级别 Subagent（`~/.codebuddy/agents/`）

### 3.3 核心机制：Hooks 安全拦截

Hooks 在 7 个关键事件节点插入自定义脚本。对嵌入式项目最重要的三个：

#### 3.3.1 PreToolUse Hook — 工具执行前验证

```json
// .codebuddy/settings.json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "write_to_file|replace_in_file",
        "hooks": [{
          "type": "command",
          "command": "python3 .codebuddy/hooks/pre_write_check.py",
          "timeout": 5
        }]
      },
      {
        "matcher": "execute_command",
        "hooks": [{
          "type": "command": "python3 .codebuddy/hooks/pre_command_check.py",
          "timeout": 5
        }]
      }
    ]
  }
}
```

检查逻辑示例：
- 禁止修改 `drivers/` 下的 MCAL 原始驱动文件
- 禁止 Application 层 import MCAL 头文件
- 禁止删除 `.codebuddy/` 目录

#### 3.3.2 PostToolUse Hook — 工具执行后审计

```json
{
  "PostToolUse": [{
    "matcher": "write_to_file|replace_in_file",
    "hooks": [{
      "type": "command",
      "command": "python3 .codebuddy/hooks/post_audit.py",
      "timeout": 10
    }]
  }]
}
```

- 记录每次文件修改的时间/内容摘要到审计日志
- 检查修改后的代码是否仍满足 MISRA-C 基本规则

#### 3.3.3 SessionStart Hook — 会话启动注入上下文

```json
{
  "SessionStart": [{
    "matcher": "startup",
    "hooks": [{
      "type": "command",
      "command": "python3 .codebuddy/hooks/session_init.py",
      "timeout": 15
    }]
  }]
}
```

- 自动读取最新的 Memory 文件摘要
- 自动检查 Git 状态并注入最近的变更上下文
- 自动加载项目的 MCU 关键信息

### 3.4 核心机制：Checkpoints 自动版本化

在 Craft/Plan 模式下，每次对话导致文件变更后，系统自动创建检查点。

- **无需手动操作**：系统自动创建
- **高亮显示变更**：鼠标悬浮即可看到 Diff
- **一键回退**：点击 `回退` 恢复到任意检查点
- **工作原理**：每轮对话的文件变更自动版本化

### 3.5 工作模式选择策略

| 场景 | 推荐模式 | 原因 |
|------|---------|------|
| 跨模块架构变更 | **Plan Mode** | 需要完整方案+任务拆解 |
| 新功能开发 | **Plan Mode** | 需要需求澄清+方案制定 |
| 单文件 Bug 修复 | **Craft Mode** | 上下文明确，直接执行 |
| 代码审查 | **Craft Mode + code-checker Subagent** | 单次分析任务 |
| 快速问答 | **Ask Mode** | 不修改代码 |

---

## 四、Phase 3: 流程反思（REFLECT）

### 4.1 反思机制总览

流程反思不是事后的一次性活动，而是**嵌入到工作流每一个环节的持续过程**：

```
Plan 制定阶段            执行阶段              完成后阶段
     │                      │                      │
     ▼                      ▼                      ▼
┌──────────┐    ┌──────────────────┐    ┌──────────────────┐
│ Ready状态 │    │ PreToolUse Hook  │    │ code-checker     │
│ 方案审阅  │    │ 写入前安全验证    │    │ 代码质量审查      │
├──────────┤    ├──────────────────┤    ├──────────────────┤
│ 架构检查  │    │ PostToolUse Hook │    │ Checkpoints      │
│ 依赖审查  │    │ 执行后审计日志    │    │ 不满意→回退       │
├──────────┤    ├──────────────────┤    ├──────────────────┤
│ 扩展编排  │    │ Stop Hook        │    │ Plan 归档        │
│ 能力审核  │    │ 完成后反馈        │    │ 方案可复用审查    │
└──────────┘    └──────────────────┘    └──────────────────┘
```

### 4.2 反思节点详解

#### 节点 1: Plan Ready 状态 — 执行前审阅（最重要的反思节点）

> "在代码生成前修正方向，避免后期重构" — 这是 Plan Mode 的核心价值

| 审阅维度 | 检查要点 | 修正成本 |
|---------|---------|---------|
| 技术方案 | 是否符合 AUTOSAR 四层架构？MCU 外设分配是否合理？ | Preview 修改：几乎为零 / 代码完成后修改：可能需要重构 |
| 任务拆解 | 是否遗漏 FreeRTOS 任务同步？依赖顺序是否正确？ | Preview 调整：修改文字 / 执行中发现：中断并重新规划 |
| 编码规范 | 是否符合 MISRA-C？命名是否符合约定？ | Preview 补充约束 / 代码完成后：批量重命名 |

#### 节点 2: Checkpoints — 执行中回退

- 每轮对话文件变更后自动创建检查点
- 不满意时一键回退到任意历史状态
- **适用场景**：实验性代码失败、需求变更、AI 生成代码不符合预期

#### 节点 3: code-checker Subagent — 代码审查

由主 Agent 在 Building 阶段完成后自动调度，审查维度：
- MISRA-C:2012 违规检查
- 内存泄漏/越界
- FreeRTOS 任务栈溢出风险
- Application 层禁止包含 MCAL 头文件
- 变量初始化/对齐

#### 节点 4: PreCompact Hook — 上下文压缩前反思

在长对话的上下文即将被压缩时（自动或手动 `/summarize` 触发），通过 Hook 脚本：
- 保存完整的对话历史（`.codebuddy/context_history/transcript_*.txt`）
- 提取本次对话中的关键决策和设计决策记录
- 将重要信息追加到 Working Memory 中

#### 节点 5: Stop Hook — Agent 完成后反馈

Agent 每次停止响应时可以注入反馈：
```json
{
  "continue": false,
  "stopReason": "请验证：1) 是否所有 FreeRTOS 任务栈大小已分配合理？2) ADC采样频率是否匹配MCU时钟配置？"
}
```

### 4.3 反思触发条件（自动化规则）

| 触发条件 | 反思动作 |
|---------|---------|
| 修改 `source/Abstraction/` 接口 | arch-reviewer 审查架构一致性 |
| 新增 `.c` 文件 | code-checker 审查代码质量 + 更新 AGENTS.md |
| 修改 FreeRTOS 任务配置 | rtos-task 审查任务栈/优先级 |
| 修改 `source/Application/` | app-logic 审查状态机完整性 |
| 修改 `drivers/` | mcal-driver 审查寄存器配置 |

---

## 五、Phase 4: 知识库保存（WRITE）

### 5.1 保存机制映射

| CodeBuddy 机制 | 保存内容 | 保存时机 | 存储位置 | 作用域 |
|---------------|---------|---------|---------|--------|
| **Plan 归档** | 技术方案 + 任务列表 | Plan Finished | `.codebuddy/plans/*.md` | 项目级 |
| **Working Memory** | 每次工作的摘要日志 | Agent 主动写入 | `.codebuddy/memory/YYYY-MM-DD.md` | 项目级 |
| **Memory (持久化)** | 重要决策/偏好/事实 | 用户或Agent主动 | SQLite (IDE 管理) | 全局/项目 |
| **AGENTS.md 更新** | 项目知识索引 | 重大变更时手动 | `docs/AGENTS.md` | 项目级 |
| **SessionEnd Hook** | 会话状态报告 | 会话结束时 | 自定义脚本输出 | 自定义 |
| **PreCompact Hook** | 完整对话历史 | 上下文压缩前 | `.codebuddy/context_history/` | 项目级 |

### 5.2 各机制的写入策略

#### 5.2.1 Plan 归档（自动）

Plan Mode 完成后，Plan 自动保存为 Markdown 到 `.codebuddy/plans/`：
- **复用价值**：后续任务引用历史 Plan 作为上下文，避免重复描述架构
- **知识沉淀**：形成项目级的决策记录和技术方案库
- **Token 节省**：新对话中引用历史 Plan 快速建立项目背景

#### 5.2.2 Working Memory（Agent 主动）

当前已有的每日日志模式继续保留：
- 每次完成实质性工作后追加记录到 `.codebuddy/memory/YYYY-MM-DD.md`
- 超过 30 天的每日日志提炼到 `MEMORY.md` 并删除原文件
- 内容：做了什么、为什么这样做、有哪些决策

#### 5.2.3 Memory 持久化（Agent 主动调用 `update_memory`）

用于存储跨会话的**长期事实**：
- 用户偏好（如"喜欢用中文回答"）
- 项目约定（如"Application 层禁止包含 MCAL 头文件"）
- 重要决策（如"选择 heap_4 而不是 heap_1 的原因"）

**写入原则**：只在信息具有跨会话价值时才写入，避免写入临时性信息。

#### 5.2.4 AGENTS.md 更新（手动触发）

当发生以下变更时，应更新 `docs/AGENTS.md`：
- 新增模块/文件
- 修改关键接口
- 变更架构设计
- 新增外设映射

#### 5.2.5 SessionEnd Hook（自动）

会话结束时自动触发脚本：
- 生成会话摘要报告
- 统计本次会话的代码变更量
- 清理临时文件

#### 5.2.6 PreCompact Hook（自动）

上下文压缩前触发：
- 备份完整对话历史到 `.codebuddy/context_history/`
- 提取关键决策信息注入到压缩指导中

### 5.3 知识库生命周期

```
日常工作
    │
    ▼
Working Memory (每日日志 .codebuddy/memory/YYYY-MM-DD.md)
    │  (超过 30 天)
    ▼
MEMORY.md (长期记忆 — 提炼为结构化条目)
    │
    ▼
AGENTS.md (项目知识索引 — 结构性变更时更新)
    │
    ▼
Plan 归档 (.codebuddy/plans/) — 技术方案持久化，可被后续任务引用
```

---

## 六、完整工作流示例：以"新增温度传感器模块"为例

### 场景

> 用户需求：在现有系统中增加一个 DS18B20 温度传感器，用于监测电解槽外壳温度

### 流程演示

```
┌─────────────────────────────────────────────────────────┐
│ Phase 1: 知识库读取                                      │
├─────────────────────────────────────────────────────────┤
│ 1. AGENTS.md 自动加载 → 了解 MCU 型号、已有外设映射       │
│ 2. Always Rules 注入 → MISRA-C 规范 + AUTOSAR 四层约束   │
│ 3. Memory 加载 → 知道项目已有 6 个 Subagent              │
│ 4. 搜索代码库 → 发现 OneWire 总线未使用，GPIO PA5 空闲     │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 2: Agent 工作流 (Plan Mode)                        │
├─────────────────────────────────────────────────────────┤
│ Prepare-需求澄清:                                         │
│   AI: "DS18B20 的精度要求是多少？需要几个传感器？          │
│        故障诊断阈值是固定的还是可配置的？"                  │
│   用户: "12-bit 精度, 1 个传感器, 阈值通过 NvManager 配置" │
│                                                         │
│ Prepare-方案制定:                                         │
│   AI 生成技术方案:                                        │
│   ├── MCAL: GPIO PA5 (OneWire), Timer6 (微秒延时)        │
│   ├── Abstraction: DS18B20_Driver (OneWire协议封装)      │
│   ├── Service: TemperatureSensor (数据滤波+阈值比较)      │
│   ├── Application: HealthMonitor 集成温度监测             │
│   └── Task List: 6步可执行任务                            │
│                                                         │
│ Ready-方案确认:                                           │
│   用户审阅 → 确认方案符合架构约束 → 点击"开始执行"          │
│                                                         │
│ Building-方案实施:                                        │
│   ┌─────────────────────────────────────────────┐       │
│   │ 主 Agent 按 todolist 依次执行:                │       │
│   │                                              │       │
│   │ Task 1: MCAL 层 GPIO PA5 配置                │       │
│   │   → 自动启动 mcal-driver Subagent            │       │
│   │   → PreToolUse Hook 验证：不修改 drivers/     │       │
│   │                                              │       │
│   │ Task 2: Abstraction 层 DS18B20 驱动           │       │
│   │   → 主 Agent 直接处理（单层修改）              │       │
│   │   → Checkpoint 自动创建                      │       │
│   │                                              │       │
│   │ Task 3: Service 层温度服务                    │       │
│   │   → 主 Agent 直接处理                         │       │
│   │   → PostToolUse Hook 审计日志                 │       │
│   │                                              │       │
│   │ Task 4-6: Application 层集成                 │       │
│   │   → 自动启动 app-logic Subagent              │       │
│   │   → 自动启动 rtos-task (新任务栈分配)         │       │
│   └─────────────────────────────────────────────┘       │
│                                                         │
│ Finished: Plan 自动保存 → .codebuddy/plans/             │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 3: 流程反思                                        │
├─────────────────────────────────────────────────────────┤
│ 1. code-checker Subagent 自动审查:                       │
│    ✅ MISRA-C Rule 8.5: 外部变量声明检查                  │
│    ⚠️  MCAL_GPIO_PA5 已在两个 .c 中定义 → 修复为 extern   │
│    ✅ Application 层无 MCAL 引用                          │
│    ✅ FreeRTOS 任务栈大小合理 (256 words)                 │
│                                                         │
│ 2. Checkpoints 审查:                                     │
│    查看每一轮变更的 Diff → 确认关键逻辑正确               │
│                                                         │
│ 3. arch-reviewer 架构审查:                               │
│    ✅ DS18B20_Driver 正确放在 Abstraction 层              │
│    ✅ TemperatureSensor 正确放在 Service 层               │
│    ✅ 依赖方向: Application → Service → Abstraction → MCAL│
│                                                         │
│ 4. PreCompact Hook:                                      │
│    对话上下文即将压缩 → 自动保存本次决策记录               │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 4: 知识库保存                                      │
├─────────────────────────────────────────────────────────┤
│ 1. Working Memory 追加 (~/memory/2026-07-13.md):        │
│    "新增 DS18B20 温度传感器模块，GPIO PA5，12-bit 精度"   │
│                                                         │
│ 2. Memory 持久化 (update_memory):                        │
│    "OneWire 总线使用 GPIO PA5，Timer6 做微秒延时"         │
│                                                         │
│ 3. Plan 归档:                                            │
│    .codebuddy/plans/ds18b20-temperature-sensor.md       │
│    包含完整技术方案，可被后续类似任务引用                  │
│                                                         │
│ 4. AGENTS.md 更新:                                       │
│    外设映射新增: GPIO PA5 → DS18B20 OneWire              │
│    新增模块: source/Abstraction/DS18B20_Driver.h/c       │
│             source/Service/TemperatureSensor.h/c         │
│                                                         │
│ 5. SessionEnd Hook:                                      │
│    生成会话摘要 → 3 个文件修改, 2 个新文件, 0 编译错误     │
└─────────────────────────────────────────────────────────┘
```

---

## 七、与已有基础设施的整合方案

### 7.1 现有资源盘点

| 资源 | 文件 | 覆盖的框架阶段 |
|------|------|-------------|
| AGENTS.md | `docs/AGENTS.md` | Phase 1 (知识库读取) |
| 6 个 Subagents | `.codebuddy/agents/*.md` | Phase 2 (Agent 工作流) |
| Working Memory | `.codebuddy/memory/` | Phase 3+4 (反思+保存) |
| agentic-workflow Rule | `.codebuddy/rules/agentic-workflow.mdc` | Phase 1 (知识库读取) |

### 7.2 推荐新增的文件

| 文件 | 作用 | 对应阶段 |
|------|------|---------|
| `.codebuddy/rules/L1-always-编码规范.mdc` | MISRA-C/AUTOSAR 规范始终注入 | Phase 1 |
| `.codebuddy/rules/L1-always-架构约束.mdc` | 四层依赖规则始终注入 | Phase 1 |
| `.codebuddy/hooks/pre_write_check.py` | 写入前安全验证 | Phase 2+3 |
| `.codebuddy/hooks/post_audit.py` | 修改后审计日志 | Phase 3 |
| `.codebuddy/hooks/session_init.py` | 会话启动注入项目信息 | Phase 1 |
| `.codebuddy/hooks/session_end.py` | 会话结束保存摘要 | Phase 4 |
| `.codebuddy/hooks/precompact_save.py` | 压缩前保存对话历史 | Phase 3+4 |
| `.codebuddy/settings.json` | Hooks 配置文件 | Phase 2 |
| `.codebuddy/plans/` (目录) | Plan 归档存储 | Phase 4 |

### 7.3 不需要变更的内容

- **6 个 Subagents**：当前配置已经覆盖了四层架构的所有层级，描述清晰，触发条件明确
- **AGENTS.md**：结构完整，作为 Phase 1 的核心知识入口已经足够
- **Working Memory 模式**：每日日志追加 + MEMORY.md 提炼的模式已经运行良好

---

## 八、框架收益总结

| 维度 | 当前状态 | 完整框架后 |
|------|---------|-----------|
| 知识读取 | AGENTS.md + Memory | AGENTS.md + 分层 Rules + MCP + Skills |
| 方案规划 | 依赖主 Agent 判断 | **Plan Mode 五步流程 > 强制需求澄清+方案审阅** |
| 任务执行 | Craft 模式逐轮对话 | **Plan Mode Building 自动编排 6 个 Subagent** |
| 安全防护 | 无 | **PreToolUse/PostToolUse Hooks 工具级拦截** |
| 过程反思 | 事后手动审查 | **Checkpoints 自动版本化 + Plan Ready 审阅节点** |
| 知识沉淀 | 每日日志手动写入 | **Plan 归档 + SessionEnd Hook + PreCompact 自动保存** |
| 上下文管理 | 依赖 Agent 自主管理 | **/summarize + PreCompact Hook 可控压缩** |
| 可回溯性 | 手动 Git | **Checkpoints 每轮自动版本化 + Plan 存档** |

---

## 九、实施优先级建议

| 优先级 | 动作 | 投入 | 收益 |
|--------|------|------|------|
| **P0** | 习惯使用 Plan Mode 替代 Craft 处理复杂任务 | 零配置 | 强制需求澄清 + 方案审阅 |
| **P0** | 每次复杂任务后手动回看 Checkpoints | 零配置 | 理解变更全貌 |
| **P1** | 创建 `.codebuddy/rules/L1-always-编码规范.mdc` | 15 分钟 | 始终注入 MISRA-C 规范 |
| **P1** | 创建 `.codebuddy/rules/L1-always-架构约束.mdc` | 15 分钟 | 始终注入四层依赖约束 |
| **P1** | 创建 PreToolUse Hook（pre_write_check.py） | 30 分钟 | 防止越层修改 |
| **P2** | 创建 PostToolUse + SessionEnd Hooks | 1 小时 | 审计 + 自动保存 |
| **P2** | 创建 `.codebuddy/rules/L2-reference-*.mdc` | 30 分钟 | 按需加载参考文档 |
| **P3** | 配置 MCP Server（GitHub/HC32） | 1 小时 | 外部知识库连接 |

---

*方案设计完成。下一步按 P0 → P1 → P2 → P3 优先级逐步落地。*
