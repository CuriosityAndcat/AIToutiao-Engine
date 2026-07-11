# 抖音分享主题整理（douyinconect.txt）

> 来源文件：`docs/douyinconect.txt`（QQ 聊天记录「荡汐人间」于 07-11 09:20 前后分享的 7 条抖音链接）
> 整理时间：2026-07-11
> 说明：以下每条均包含「原始抖音分享」+「联网检索补充内容」。与本引擎（AI 内容创作 / 公众号分发）相关的条目已标注「可借鉴点」。

---

## 1. Vibe Coding 大赏 ｜ Harness Engineering

- **原始分享**：【是花子呀_的作品】vibecoding大赏｜ Harness eng...
  - 链接：https://v.douyin.com/AmP-3UxCrRw/
- **主题概述**：从「Vibe Coding（氛围编程）」到「Harness Engineering（工程化编排）」的范式演进。
- **检索补充（基础）**：
  - 2025 年 Andrej Karpathy 提出 Vibe Coding；2026 年已成主流 AI 开发范式，但统计显示 **AI 项目失败率高达 67%**，暴露其局限性（凭直觉让 AI 生成代码、缺乏工程约束与验证）。
  - 演进路径：`Vibe Coding → SDD（Spec-Driven Development，规范驱动开发） → Harness Engineering`。
  - Harness Engineering 强调把 AI 当作「被编排的工程资源」：明确规格、约束、验证闭环，而非只靠对话「感觉」。
- **可借鉴点**：可作为「AI 编程范式」系列选题；本引擎的 Agentic Workflow（复杂度分级、规划、反射协议、多角色审查）正是 Harness Engineering 的工程化落地，详见下方 1.1 映射与 1.2 知识扩展。

### 1.1 内容详解（视频转录稿整理｜来源：`docs/douyinconect_Content.txt`）

> 视频作者：是花子呀（抖音号「荡汐人间」于 07-11 09:20 分享）
> 核心主张：**让 AI 在家写代码、人出门玩——靠的不是提示词技巧，而是把目标与验收标准定义清楚，再交给多个 AI 子代理分工执行。**
> 案例演示：在 Codex 输入一条指令，AI 连续工作 3 小时，独立开发出一个完整游戏。

**Harness Engineering 三步法**

1. **建地图（项目根目录的「地图」文件）**
   - 作用：让 AI 快速了解项目整体情况，避免注意力被分散、自行探索耗时。
   - 必填信息：
     - 项目是做什么（一句话说清，例如「开发一个 2D 小游戏」）；
     - 项目仓库结构（代码 / 资源 / 文档分别对应哪些文件夹）；
   - 按需补充：开发约束（不能做什么、必须遵守的规则）。
   - 注意：地图只是「目录」，不是完整说明书，**不要把所有细节都塞进去**。

2. **写规格文档（Spec）**
   - 放在指定文件夹下，要写得非常详细：游戏机制是什么、视觉风格是什么、本版本具体交付哪些内容。
   - 若交付物复杂，拆成两层：先写主规格文档，再从里面链接到子模块文档（案例中将规格拆分为「游戏机制」+「视觉校验」两份子文档）。

3. **写验收标准（Acceptance Criteria）**
   - 关键要「具体、可量化」：能对照的直接给数字；含糊的地方必须明确判定方法。
   - **特别重要**：必须要求 AI 提供「测试通过的证据」，从源头杜绝 AI 偷懒。

**为什么单 Agent 不行？**

- 让同一个 AI「既写代码又当测试验收」，它会偷懒：十几分钟就告诉你「任务完成」，但产出质量一塌糊涂。
- 一句话总结：**不能让 AI 既当运动员又当裁判**，必须让一群 AI 分工合作。

**多 Agent 分工方案**

- 手动创建子代理并编排其工作（可行但略麻烦，作者称后续单独出片）。
- 直接用一个开源插件 **spower（suppower）**：安装后在搜索栏输入 `spower` → 添加；点 `+` → 插件 → `power`，即可让 AI 自动创建多个子代理并分配任务。
  - 每个子代理职责明确：例如「写测试的子代理」依据验收标准设计详细测试用例；「写代码的子代理」负责开发。
  - 分工后开发时长会被拉长，但最终结果更可靠、更完美。

**作者总结**

- Harness Engineering 的关键 = **清晰定义目标 + 验收标准**，再交给不同子代理执行。
- 若 AI 产出不理想，应先反思「是不是没跟 AI 交代清楚」，而不是靠聊天来补救——这是驾驭工程（Harness）与提示工程（Prompt）最本质的区别。

**与本引擎（AIToutiao-Engine）的映射**

| 花子的方法 | 本引擎 Agentic Workflow 对应 |
|-----------|------------------------------|
| 地图文件（项目结构 + 约束） | 项目根结构 + `always_applied_workspace_rules` 中的约束 |
| 规格文档（目标 / 交付物） | 规划协议（Tier 3 的 Plan：目标 / 涉及文件 / 依赖 / 验证标准） |
| 验收标准（可量化 + 测试证据） | 反射协议（5 维度评分 + PASS / FIXABLE / BLOCKED 判定） |
| 多 Agent 分工（spower） | Task 子代理 / 多角色审查（Code Reviewer 等） |

→ **高度契合**：本引擎已有的「复杂度分级 + 规划 + 反射 + 多角色审查」正是 Harness Engineering 的工程化落地。可据此做一篇《用 Agentic Workflow 实践 Harness Engineering》的内容选题。

### 1.2 知识扩展（联网检索归纳）

> 以下为围绕「Vibe Coding → SDD → Harness Engineering」范式演进的系统性检索整理，用于补全视频未展开的概念与工具链。

**① Harness Engineering（驾驭工程）正式定义**
- **起源**：2026 年 2 月由 HashiCorp 联合创始人、Terraform 之父 **Mitchell Hashimoto** 正式命名。
- **定义**：AI 时代的全新软件工程学科——设计和实现系统来**约束、告知、验证、修正** AI 智能体的行为，让强大但不可预测的模型可靠完成复杂任务。
- **通俗比喻**：给 AI 套「缰绳 + 马鞍 + 跑道 + 护栏 + 仪表盘」。大模型决定 AI「能做到多牛」，Harness 决定 AI「能稳定用多久」。核心理念：**AI 犯一次错，就搞一套工程化方案让它不再犯**，靠系统而非反复调 Prompt 解决不稳定 / 幻觉 / 越权 / 难追溯。

**② 六大核心组件（落地系统要点）**
1. **上下文架构**：只给 AI 看当前步骤所需信息，长任务定期重置上下文，记忆存外部库/文件。
2. **架构约束层（最核心）**：硬拦截错误——代码必须过自定义 ESLint、禁止访问高危 API、强制任务步骤顺序。
3. **工具编排层**：统一管理 AI 可调用的工具/API，控制权限、限流、失败重试、结果格式化。
4. **记忆与状态管理**：短期记会话、长期记历史；任务进度存 Git/数据库，支持出错自动回滚。
5. **全链路观测与监控**：记录每步思考/调用/输出/耗时，实时监控成功率与幻觉率，异常即告警或拦截。
6. **反馈与自愈闭环**：出错 → 回滚/修复 → 新增一条拦截规则 → 重试 → 记录优化，使 AI 犯错越来越少。

**③ 三种「工程」对比**

| 工程类型 | 核心思路 | 通俗理解 | 最大痛点 |
|----------|----------|----------|----------|
| 提示词工程 | 优化指令求模型听话 | 哄着 AI 做事 | 不稳定、不可复用 |
| 上下文工程 | 喂对资料（如 RAG） | 给 AI 准备参考书 | 靠 AI 自觉，管不住乱犯错 |
| Harness 工程 | 搭系统约束让 AI 不得不正确 | 给 AI 装「笼子」定死规则 | 前期搭系统稍费功夫 |

**④ SDD 规范驱动开发（承上启下的中间范式）**
- **定义**：以「规范（Specification）」作为软件开发的第一性产物，Spec-First 而非 Code-First；代码不再是唯一事实来源，而是规范的一个实现结果，须持续对齐。
- **五层执行模型**（自顶向下逐级约束，将「意图→实现→验证→治理」串成链路）：

  | 层级 | 名称 | 核心职责 |
  |------|------|----------|
  | 5 | 治理层 Governance | 规范演化、版本管理、人机决策 |
  | 4 | 验证层 Validation | 实时对齐：合约测试、模式验证、漂移拦截 |
  | 3 | 执行层 Execution | 运行时实现：骨架人工治理 + 业务逻辑 AI 生成 |
  | 2 | 生成层 Generation | 意图→可执行形式：跨语言代码/类型/SDK 生成 |
  | 1 | 规范层 Specification | 定义系统行为：API、消息契约、领域模式、策略约束 |

- **OpenSpec 工具链**（SDD 实战方案，`@fission-ai/openspec`）：四步流水线 `propose（发起变更/定义规范）→ explore（分析影响）→ apply-change（按规范生成代码）→ archive（合并回源真相）`。本质：人类定义规则（Spec），AI 执行规则，杜绝「开盲盒式」AI 编程。

**⑤ Vibe Coding 工具生态（2026 主流横评）**
- 代表工具：**Cursor、Windsurf、Roo Code、Claude Code、Codex、Lovable、Bolt.new、通义灵码** 等。
- 选型维度：Agent 自主能力（是否支持 Long-running Agent）、定价、国内可用性、原型/SVG/浏览器生成适配。
- 局限性：纯 Vibe Coding 缺乏架构约束与验证闭环，是 AI 项目 67% 失败率的主因之一；正因此才演进到 SDD / Harness。

**⑥ 与本引擎的再映射（知识扩展视角）**

| Harness 概念 | 本引擎 Agentic Workflow 对应 | 补充 |
|--------------|------------------------------|------|
| 架构约束层（ESLint 硬拦截） | `always_applied_workspace_rules` 强制规则 | 规则即「护栏」 |
| 记忆与状态管理（Git/DB 回滚） | `.codebuddy` 持久化任务/记忆 | 状态跨会话保留 |
| 反馈与自愈闭环 | 反射协议 5 维度评分 → FIXABLE 迭代（max 3 轮） | 评分即「漂移检测」 |
| 全链路观测 | Todo 列表 + Reflection diff report | 过程可追踪 |
| 多 Agent 分工 | Task 子代理 / 多角色审查（Code Reviewer 等） | 避免「既当运动员又当裁判」 |

→ 结论：**本引擎的 Agentic Workflow 已天然实现 Harness Engineering 的核心闭环**，可直接作为「如何用 Agentic Workflow 落地 Harness Engineering」的内容选题素材。

---

## 2. LLM Wiki（姜胡说 / Karpathy 方法论）

- **原始分享**：【诡狡程序猫的作品】被姜胡说的 llm-wiki 视频刺激到了，我肝了...
  - 链接：https://v.douyin.com/LclRg9TCy1M/
- **主题概述**：用 LLM 持续构建并维护结构化 Markdown 个人知识库的方法论（源自 Karpathy 的 GitHub Gist，3 天 5000+ Star）。
- **检索补充（开源实现）**：
  - GitHub：`https://github.com/luotwo/llm-wiki`（196 Stars）— 含 Claude Code Skill，目录分 `raw/`（原始资料，不可变）与 `wiki/`（LLM 维护的知识库）。
  - GitHub：`https://github.com/taffy123d/Karpathy-LLM-Wiki` — 提供 Agent 集成与查询接口。
  - 核心闭环：`Ingest（导入）→ Query（查询）→ Lint（维护）`。知识随每次导入「复利」积累，LLM 负责交叉引用、一致性维护。
  - 工具搭配：Obsidian + Obsidian Web Clipper + Git。
- **可借鉴点**：本 `docs/` 目录未来可尝试用 LLM Wiki 思路维护「选题库 / 工具库」，把零散抖音链接沉淀为结构化知识库。

---

## 3. 提升前端「高级感」的开源项目

- **原始分享**：【小L不废话的作品】一款提升前端高级感的开源项目 # 前端 # vib...
  - 链接：https://v.douyin.com/0yDpmudy6xo/
- **主题概述**：用于提升前端页面视觉「高级感」的开源 UI / 模板项目。
- **检索补充**：
  - 模板聚合站 HtmlRev：1500+ 免费美观前端模板，覆盖 Vue / React / Bootstrap / Angular（juejin / 腾讯云开发者社区均有推荐）。
  - 通用做法：精致排版、留白、动效、统一设计 token 是「高级感」的关键。
- **可借鉴点**：本引擎生成的头条/公众号页面若需提升视觉质感，可参考此类模板与排版规范（见第 6 条 gzh-design-skill）。

---

## 4. Clypra —— 开源视频剪辑器（剪映替代）

- **原始分享**：【kailong liu 企业家的图文作品】看到这个，我直接把剪映订阅给退了… Clypra...
  - 链接：https://v.douyin.com/B9geeV0qk24/
- **主题概述**：一款开源现代化桌面视频编辑器，定位为「CapCut（剪映）高级能力」的开源替代。
- **检索补充**：
  - 技术栈：**Tauri 2 + React 19 + TypeScript + Rust + FFmpeg + Zustand**。
  - 目标：免费实现 CapCut Premium 核心功能（专业级时间轴、多轨编辑、音频波形可视化、字幕文字覆盖、帧级精确编辑、硬件加速）。
  - 团队：AIEraDev；B 站相关视频称其 Star 已达 66.9K 量级。
  - 优势：相比 Electron，Tauri/Rust 体积更小、性能更高。
- **可借鉴点**：若本引擎后续要做「视频版头条」或短视频自动生成，Clypra 可作为本地无水印、无订阅的视频处理底座。

---

## 5. 如何 1:1 还原 UI（设计稿 → 代码）

- **原始分享**：【做游戏的小卡的作品】如何1:1还原UI 不光是游戏UI，网页UI，小程...
  - 链接：https://v.douyin.com/qED369jiY78/
- **主题概述**：从设计稿（Figma / 截图 / 手绘）1:1 还原为前端代码的方法与工具。
- **检索补充**：
  - 蚂蚁 **WeaveFox**：多模态 AI，输入设计图/截图/草图自动生成生产级前端代码，号称 1:1 还原。
  - **Figma MCP + Claude Code**：开启 Figma 桌面端 MCP 服务，让 Agent 直接读取设计稿生成代码。
  - **Copixel**：前端 UI 走查 1:1 还原辅助插件（像素级比对）。
  - **Codex + Agent Browser**：通过 ref 引用 + 浏览器自动化实现 UI 自动校准与精准样式还原。
- **可借鉴点**：本引擎生成 Web/小程序页面时，可结合 Figma MCP / WeaveFox 思路提升还原度。

---

## 6. 开源公众号排版 Skill（gzh-design-skill）

- **原始分享**：【极客开源的图文作品】开源公众号排版Skill，没有一点AI味。gzh-...
  - 链接：https://v.douyin.com/SZsjeUoVT7s/
- **主题概述**：面向 AI Agent 的公众号排版 Skill，Markdown 一键转内联样式 HTML。
- **检索补充**：
  - GitHub：`https://github.com/isjiamu/gzh-design-skill`（约 1.7k Star）。
  - 核心能力：输入 Markdown → 按选定主题生成**样式全内联**的 HTML（粘贴公众号编辑器后格式不丢）。
  - 自动化：自动编章节号、关键词下划线、引言卡、目录、代码块/图片处理、作者签名；内置校验脚本（ERROR 清零才交付）。
  - 跨模型兼容：Claude / GPT / Gemini / DeepSeek / Kimi / 通义千问 / 智谱 GLM 均可。
  - 内置 6 套主题：摸鱼绿（默认）、红白色系、石墨极简风、留白禅意风、摸鱼票据风、橄榄手记。
  - 安装：`npx skills add https://github.com/isjiamu/gzh-design-skill` 或 `git clone` 到 `~/.claude/skills/`。
- **可借鉴点**：**与本引擎高度相关**——可直接用于把 AI 生成的头条文章排版为公众号草稿，实现「写→排→发」闭环。建议优先集成评估。

---

## 7. Seedance 导演级 Skills（字节跳动 AI 视频）

- **原始分享**：【Javen_AI研习社的作品】紧急收藏！Seedance 导演级skills分享...
  - 链接：https://v.douyin.com/t5JV3J5HwiQ/
- **主题概述**：字节跳动 Seedance 系列 AI 视频生成模型的「导演级」使用技巧 / Skills 分享。
- **检索补充**：
  - **Seedance 2.0**：字节跳动电影级 AI 视频生成器，一句话 → 15 秒电影级片段，原生音效、音素级口型同步、导演级镜头控制；在 Artificial Analysis 榜单领先。
  - **Seedance 2.5**：宣布将于 **2026-07-16** 全面开放 API，正式商业化。
  - 国内对标：即梦 Seedance（字节）vs 可灵 AI（快手）；即梦更友好全面，可灵 4K/古风更强。
  - 适用范围：专业团队预演大片、普通用户一键生成短视频。
- **可借鉴点**：可关注 7-16 API 开放节点，作为引擎「AI 视频头条」素材生成的可选模型。

---

## 总览与建议

| # | 主题 | 类型 | 与本引擎关联度 | 建议动作 |
|---|------|------|--------------|----------|
| 1 | Vibe Coding / Harness | 理念 | 中 | 内容选题参考 |
| 2 | LLM Wiki | 方法论/工具 | 中 | 可用于 `docs/` 知识库建设 |
| 3 | 前端高级感项目 | 资源 | 中 | 提升生成页视觉 |
| 4 | Clypra | 开源工具 | 中高 | 视频处理底座评估 |
| 5 | 1:1 还原 UI | 方法/工具 | 中 | 提升页面还原度 |
| 6 | gzh-design-skill | 开源 Skill | **高** | 优先集成公众号排版 |
| 7 | Seedance | AI 视频模型 | 中高 | 关注 7-16 API 开放 |

**优先跟进**：第 6 条 `gzh-design-skill`（直接打通「AI 写文 → 公众号排版」）与第 7 条 Seedance API（7-16 开放，潜在视频生成能力）。

---

### 参考链接汇总
- LLM Wiki: https://github.com/luotwo/llm-wiki ｜ https://github.com/taffy123d/Karpathy-LLM-Wiki
- Clypra: 基于 Tauri2/React19/Rust/FFmpeg（AIEraDev 团队）
- gzh-design-skill: https://github.com/isjiamu/gzh-design-skill
- Seedance: https://seeddance.ai/zh/seedance-2-0
- 原始抖音分享合集见 `docs/douyinconect.txt`
