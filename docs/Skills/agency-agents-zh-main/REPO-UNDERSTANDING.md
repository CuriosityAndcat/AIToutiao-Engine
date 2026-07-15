# agency-agents-zh-main 仓库理解文档

> 本文档是对 `docs/skills/agency-agents-zh-main/` 子仓库的**完整理解**，供本项目（AIToutiao-Engine）协作与本仓库维护者参考。
> 理解过程遵循 **agentic workflow（智能体工作流）** 方法论——下文「0. 理解方法论」说明我们如何按 Andrew Ng 的四类智能体设计模式来解剖本仓库；而本仓库本身恰恰也是这套方法论的「实体化实现」。

---

## 0. 理解方法论（按 agentic workflow 拆解本仓库）

我们不是一次性 dump 内容，而是用智能体工作流的四个经典模式逐步逼近「完全理解」：

| agentic 模式 | 在本理解过程中的应用 | 在本仓库中的对应实现 |
|---|---|---|
| **Planning（规划）** | 先读 `README.md`/`CATALOG.md`/`AGENT-LIST.md` 建立顶层地图，再决定逐层下钻（智能体格式→战略层→工具链）。 | NEXUS 七阶段流水线（发现→策略→基础→构建→加固→上线→运营），每个阶段前先规划。 |
| **Tool Use（工具使用）** | 用 `list_dir` / `read_file` / `search_content` 在 266 个文件中精准定位，而不是通读全部。 | 智能体内部大量调用工具（脚本、测试、截图、API）。`scripts/` 与 `integrations/` 即工具化封装。 |
| **Reflection（反思）** | 每读一层回头校验：格式是否统一？中国原创与翻译如何区分？数量是否对得上 `check-counts.mjs`？发现矛盾再补读 `UPSTREAM.md`/`CONTRIBUTING.md`。 | **现实检验者（Reality Checker）** 默认「需要改进」，开发-测试循环（实现→证据收集者→通过/不通过→重试≤3）即反思闭环。 |
| **Multi-Agent Collaboration（多智能体协作）** | 由主 Agent 统一编排本次理解；如需广度可派 code-explorer 子代理并行采样各部门。 | **NEXUS** 本身就是 266 个智能体组成的协作网络，`智能体编排者` 统一调度。 |

**结论性一句话**：本仓库既是「被理解的对象」，也是「智能体工作流方法论的范本」——它用 266 个角色 + NEXUS 编排协议，把 Planning/Reflection/Multi-Agent 落到了可复用的 Markdown 提示词里。

---

## 1. 仓库定位与规模

| 维度 | 内容 |
|---|---|
| **中文名** | agency-agents 中文版（AI 智能体专家团队） |
| **本质** | 一套**开箱即用的 AI 角色（system prompt）库**，每个智能体 = 独立人设 + 专业流程 + 可交付成果 |
| **上游** | [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents)（MIT），本地已追平上游 `2026-06-16` 状态 |
| **智能体总数** | **266 个**（文件级 parity 已与上游对齐） |
| **来源构成** | 上游翻译 **215** + 中国市场原创 **约 51**（README 正文写 50，权威统计 `AGENT-LIST.md`/`UPSTREAM.md` 记 51） |
| **部门** | 19 个智能体目录 + 1 个 `strategy/` 运营文档目录（README「智能体阵容」按 20 个部门呈现，含战略部） |
| **工具集成** | 支持 **18 种** AI 编程工具（Claude Code / Cursor / Copilot / OpenClaw / Qwen / Trae / Codex 等） |
| **许可证** | MIT（`package.json` version `1.2.6`） |
| **与本项目关系** | 作为 AIToutiao-Engine 的 **SAWORKFLOW「人力资源（WHO·执行）」层**——主 Agent 按任务读取对应角色 `.md` 并采用其设定执行（见第 8 节） |

**关键差异（vs 普通提示词）**：普通提示词只说「你是一个专家」；本仓库每个智能体定义了专家**怎么思考、怎么做事、交付什么**（如 `engineering/engineering-security-engineer.md` 按 OWASP Top 10 逐项审查）。

---

## 2. 目录地图（文件级）

```
agency-agents-zh-main/
├── README.md                 # 总入口：阵容表 + 18 种工具安装 + 中国原创说明
├── CATALOG.md                # 速查表：中文名 → 文件路径（Ctrl+F 用）
├── AGENT-LIST.md             # 权威名单：266 个智能体的 ID/中文名/描述/来源 + 统计
├── CONTRIBUTING.md           # 贡献规范 + 智能体文件格式模板 + 内容红线
├── UPSTREAM.md               # 上游版本追踪 + 翻译覆盖 + 路径差异映射
├── package.json              # 包元数据（name/version/keywords/scripts）
├── LICENSE                   # MIT
├── README.zh-TW.md          # 繁体中文版 README
│
├── <19 个部门目录>/           # 每个 .md = 一个智能体（YAML frontmatter + 正文）
│   ├── academic/        (6)   设计/         (9)   工程/        (41)
│   ├── finance/         (8)   游戏开发/     (20)  GIS/        (13)
│   ├── hr/              (2)   法务/         (2)   营销/        (42)
│   ├── 付费媒体/        (7)   销售/         (9)   安全/        (10)
│   ├── 空间计算/        (6)   专项/         (58)  供应链/      (5)
│   ├── 支持/            (7)   测试/         (9)   产品/        (5)
│   └── 项目管理/        (7)
│
├── strategy/                 # NEXUS 多智能体编排运营文档（不计入智能体数）
│   ├── EXECUTIVE-BRIEF.md    # 高管简报
│   ├── QUICKSTART.md         # 5 分钟上手
│   ├── nexus-strategy.md     # 完整运营纲领（1100+ 行）
│   ├── playbooks/            # 7 份阶段手册 phase-0..phase-6
│   ├── coordination/         # agent-activation-prompts.md + handoff-templates.md
│   └── runbooks/             # 4 份场景手册（startup-mvp / enterprise-feature / marketing-campaign / incident-response）
│
├── scripts/                  # 工具链（bash + ps1 + mjs）
│   ├── convert.sh/.ps1       # 把 .md 转成各工具专用格式 → integrations/<tool>/
│   ├── install.sh/.ps1       # 安装到 ~/.tool/agents 或项目 .tool/
│   ├── lint-agents.sh        # 校验 frontmatter（name/description/color/emoji 必填）
│   ├── check-counts.mjs      # 校验各部门计数与 AGENT-LIST 一致
│   ├── translate-to-lang.sh  # 翻译生成其他语言版本
│   ├── generate-{ko,pt-BR,ru,regional,ar}-catalog.sh / sync-tw.sh
│   └── generate-regional-agent.sh
│
├── integrations/             # 预生成的工具专用格式（convert.sh 产出）
│   ├── claude-code/  cursor/  github-copilot/  openclaw/  opencode/
│   ├── trae/  windsurf/  antigravity/  gemini-cli/  qwen/  codex/
│   ├── deerflow/  hermes/  workbuddy/  codewhale/  kiro/  mcp-memory/
│   └── README.md
│
├── examples/                 # 7 个完整工作流示例
│   ├── workflow-xiaohongshu-launch.md   # 小红书品牌推广完整流程
│   ├── workflow-startup-mvp.md / workflow-landing-page.md
│   ├── workflow-book-chapter.md / workflow-with-memory.md
│   └── nexus-spatial-discovery.md / README.md
│
└── assets/                   # 赞助商图、专家库截图等
```

> 部门计数来源：`AGENT-LIST.md`「按部门统计」。相加 = 266（6+9+41+8+20+13+2+2+42+7+9+10+6+58+5+7+9+5+7）。

---

## 3. 智能体文件格式规范（最关键的可复用契约）

每个智能体是一个 `.md` 文件，`lint-agents.sh` 强制校验。格式由 `CONTRIBUTING.md` 定义、由脚本验证：

### 3.1 YAML Frontmatter（必填 4 字段）

```markdown
---
name: 智能体名称
description: 一句话描述这个智能体干什么
emoji: 💻
color: cyan          # 或十六进制如 "#FF2442"（小红书运营即用了品牌红）
---
```

- `lint-agents.sh` 的 `REQUIRED_FRONTMATTER=("name" "description" "color" "emoji")`；缺任一报 ERROR。
- `convert.sh` 用 `slugify_from_file()` 直接取**文件名**作 slug（如 `marketing-douyin-strategist.md` → `marketing-douyin-strategist`），不依赖中文 `name` 字段，避免跨语言问题。

### 3.2 正文推荐章节（`CONTRIBUTING.md` 模板 + 实际样本）

实际文件（如 `engineering-frontend-developer.md`、`marketing-xiaohongshu-operator.md`）普遍包含：

| 章节 | 作用 |
|---|---|
| `# 智能体名称` | 标题（与 name 一致） |
| **你的身份与记忆** | 角色 / 个性 / 记忆 / 经验 —— 建立人格一致性 |
| **核心使命** | 具体职责与工作内容（分小节） |
| **关键规则** | 做事原则与红线（如平台合规、不写硬广） |
| **技术交付物** | 代码示例、模板、框架（可运行产物） |
| **工作流程** | 分步骤 SOP |
| **沟通风格** | 说话方式与语气示例 |
| **学习与记忆** | 要积累的专业知识 |
| **成功指标** | 可量化衡量标准 |
| **高级能力** | 进阶能力（部分文件有） |

`lint-agents.sh` 对章节仅做 **WARN**（推荐但不强制），靠正则匹配中英文章节标题（如 `身份|记忆|Identity`、`核心使命|Core Mission`、`关键规则|Critical Rules`）。

### 3.3 内容红线（`CONTRIBUTING.md` 明确会直接 close PR）

1. **不绑定具体雇主/公司品牌** —— agent 是「角色和方法论」，中性写法，例外：可引用行业事实标准的设备/软件/协议名（如 Bullmer S90、Adobe Premiere、BSCI 验厂）。
2. **不嵌入第三方工具的 API / Plugin 说明** —— prompt 假设运行在任意 LLM/工具环境，禁止在主体塞特定工具接口名、调用方式、外链。
3. **不做翻译/新增之外的「软推广」** —— 借「补充说明」名义塞外链/自家产品/SEO 锚文本会按性质处理。

> 这三条红线保证：本仓库的提示词是**可移植、无广告、纯方法论**的，能直接被任意 AI 工具加载——这也是它能原生兼容 CodeBuddy 的原因（见第 8 节）。

---

## 4. 部门与角色全景

> 完整 266 条见 `AGENT-LIST.md`（权威）与 `CATALOG.md`（按中文名速查）。此处给出每部门的**定位 + 代表角色 + 中国原创（⭐）标记**，便于快速建立全局印象。

| 部门 | 数量 | 定位 | 代表角色（⭐=中国原创） |
|---|---|---|---|
| **工程 Engineering** | 41 | 「做对」 | 前端/后端/移动/AI 工程师、DevOps、安全、SRE、代码审查员、最小变更工程师；⭐微信小程序、⭐飞书/钉钉集成、⭐上位机(Qt)、⭐机械设计、⭐嵌入式Linux驱动、⭐FPGA/ASIC、⭐IoT方案、⭐语音AI集成 |
| **营销 Marketing** | 42 | 「做快」 | ⭐小红书运营、⭐抖音策略、⭐公众号运营、⭐B站/快手/微博/视频号、⭐百度SEO、⭐私域、⭐直播电商教练、⭐跨境电商、⭐短视频剪辑、⭐新闻情报官、⭐知识付费；出海：TikTok/Twitter/Instagram/Reddit/ASO |
| **专项 Specialized** | 58 | 「连接一切」 | ⭐提示词工程师、⭐智能体编排者(agents-orchestrator)、⭐MCP构建器、⭐工作流架构师、⭐政务ToG售前、⭐医疗合规、⭐高考志愿、⭐留学规划、⭐养殖档案核对、⭐企业风险评估、⭐AI治理政策、⭐会议效率；通用：CFO/战略家/HR/法务等 |
| **游戏开发 Game** | 20 | 全引擎覆盖 | 通用(策划/关卡/叙事/技术美术/音频) + Unity/Unreal/Blender/Godot/Roblox 子目录 |
| **GIS** | 13 | 地理信息全栈 | 分析师/Web GIS/三维/无人机测绘/GeoAI/质检/BIM-GIS |
| **安全 Security** | 10 | 全栈安全 | 应用安全/云安全/合规审计/渗透/事件响应/区块链审计/威胁情报 |
| **设计 Design** | 9 | 「做美」 | UI/UX研究员/UX架构师/品牌守护者/图像提示词工程师/视觉叙事师/趣味注入师/包容性视觉 |
| **销售 Sales** | 9 | 线索到成交 | 客户拓展/赢单策略(MEDDPICC)/Discovery教练/售前/投标 |
| **支持 Support** | 7 | 「撑住」 | 客服/数据分析师/财务追踪/基础设施运维/⭐招聘运营/法务合规/高管摘要 |
| **测试 Testing** | 9 | 「证明能用」 | ⭐证据收集者、⭐现实检验者、API测试/性能基准/无障碍/结果分析/工具评估/工作流优化/⭐嵌入式QA |
| **付费媒体 Paid Media** | 7 | 精准投放 | 审计/创意/社交广告/PPC/程序化/搜索词/归因 |
| **金融 Finance** | 8 | 钱要清楚 | ⭐财务预测、⭐发票管理、⭐金融风控；簿记/分析师/FP&A/投资/税务 |
| **产品 Product** | 5 | 「做对的事」 | 产品经理/Sprint排序师/趋势研究员/反馈分析师/行为助推 |
| **项目管理 PM** | 7 | 「管好」 | 高级项目经理/项目牧羊人/工作室制片人/实验追踪/会议纪要/Jira管家 |
| **空间计算 Spatial** | 6 | 沉浸式 | visionOS/macOS Metal/XR界面/沉浸式/座舱/终端集成 |
| **学术 Academic** | 6 | 叙事支撑 | 人类学家/地理学家/历史学家/叙事学家/心理学家/⭐学习规划师 |
| **供应链 Supply Chain** | 5 | 全原创⭐ | 库存预测/供应商评估/物流路线/采购策略/⭐服装工厂规划 |
| **人力资源 HR** | 2 | 全原创⭐ | ⭐招聘专家、⭐绩效管理专家（上游无，本地新建部门） |
| **法务 Legal** | 2 | 全原创⭐ | ⭐合同审查专家、⭐制度文件撰写专家（本地新建部门） |

**中国原创智能体（核心竞争力）**：约 51 个，主题集中在——
- **国内平台运营**：小红书 / 抖音 / 微信(公众号+视频号+小程序) / B站 / 快手 / 微博 / 知乎 / 百度SEO / 私域 / 直播电商 / 跨境电商 / 短视频剪辑 / 新闻情报官
- **企业协作**：飞书 / 钉钉集成开发
- **垂直领域**：政务ToG、医疗合规、高考志愿、留学规划、Qt工业上位机、机械设计、畜禽养殖档案核对、服装工厂规划
- **业务支撑**：私域流量、合同审查、发票管理、库存预测、动态定价、AI治理、企业风险、会议效率
- **本地新建部门**：`hr/`、`legal/`、`supply-chain/` 整部门为上游所无

> 在 README「智能体阵容」中带 ⭐ 的即原创；`AGENT-LIST.md` 中「来源」列标 `原创`/`翻译`。

---

## 5. NEXUS 多智能体编排框架（本仓库的「皇冠」）

`strategy/` 目录不是又一个提示词，而是把 266 个角色组装成**协同流水线**的运营纲领。核心文件：`nexus-strategy.md`（1100+ 行）、`QUICKSTART.md`、`EXECUTIVE-BRIEF.md`、7 份 `playbooks/`、`coordination/`、`runbooks/`。

### 5.1 七阶段流水线（Pipeline）

```
第0发现 → 第1策略 → 第2基础 → 第3构建 → 第4加固 → 第5上线 → 第6运营
 情报收集   架构设计   基础组件   开发-测试循环  质量门禁   市场推广   持续运营
◆ 每个阶段间有质量门禁 ◆ 阶段内有并行轨道 ◆ 每个边界有反馈循环
```

- **第 3 阶段（构建）** 是心脏：智能体编排者管理**逐任务开发-测试循环**——开发者实现 → 证据收集者(QA)测试 → 通过则下一个 / 不通过带反馈重试（≤3 次）→ 仍失败升级。
- **第 4 阶段（加固）** 由**现实检验者**做最终集成测试，**默认判定「需要改进」**，只有压倒性证据才给「就绪」。

### 5.2 三种激活模式

| 模式 | 智能体数 | 时间线 | 适用 |
|---|---|---|---|
| **NEXUS-Full** | 全部 | 12–24 周 | 完整产品生命周期 |
| **NEXUS-Sprint** | 15–25 | 2–6 周 | 功能 / MVP |
| **NEXUS-Micro** | 5–10 | 1–5 天 | 单任务（修 bug / 内容活动 / 审计） |

### 5.3 核心智能体（协议角色）

- **智能体编排者**（`specialized/agents-orchestrator.md`）：流水线控制器，调度 PM→架构→[开发↔QA 循环]→集成，自带状态报告/完成摘要模板。
- **现实检验者**（`testing/testing-reality-checker.md`）：最终质量唯一权威，证据主义、怀疑默认。
- **证据收集者**（`testing/testing-evidence-collector.md`）：截图/实测 QA，要求视觉证据。

### 5.4 治理机制（可借鉴到本项目）

- **质量门禁**：6 道（0→1 发现门禁 … 5→6 上线门禁），每道有守门人 + 阈值 + 所需证据。
- **交接协议**：`coordination/handoff-templates.md` 定义标准交接文档、QA 不通过反馈、升级报告三类模板——保证「上下文连续性，无智能体冷启动」。
- **核心原则**：流水线完整性、上下文连续、并行执行、证据高于口说、快速失败快速修复、单一信息源。
- **场景 Runbook**：`startup-mvp` / `enterprise-feature` / `marketing-campaign` / `incident-response` 四类预设配置。

> **与本项目 SAWORKFLOW 的呼应**：本仓库的 NEXUS（发现→策略→构建→加固→上线→运营 + 现实检验者门禁）和 AIToutiao-Engine 的 SAWORKFLOW（superpowers 规划 + agency 分角色执行 + evaluation.py 质量门）在思想上是同一套——都用「分角色 + 质量门 + 反思闭环」。区别：NEXUS 通用，SAWORKFLOW 绑定本项目 `evaluation.py`(5维/阈值75/80) 与 `write_stage` 自愈闭环。

---

## 6. 工具链（scripts/）

| 脚本 | 功能 | 关键实现 |
|---|---|---|
| `convert.sh` / `.ps1` | 把部门 `.md` 转成 17+ 种工具格式 → `integrations/<tool>/` | 读 frontmatter（`get_field`）、去 frontmatter 取正文（`get_body`）、slug 取文件名；支持 `--tool` 单工具 |
| `install.sh` / `.ps1` | 安装到用户目录或项目目录；自动检测工具 | 与 `convert.sh` 配合；多数工具需先 convert |
| `lint-agents.sh` | 校验所有智能体文件 | 强制 `name/description/color/emoji`；章节仅 WARN；用 `AGENT_DIRS` 与 convert 同步 |
| `check-counts.mjs` | 校验各部门计数与 `AGENT-LIST.md` 一致 | `npm run check:counts` |
| `translate-to-lang.sh` / `generate-{ko,pt-BR,ru,ar}-catalog.sh` / `sync-tw.sh` | 生成其他语言版本 / 繁体同步 | 多语言扩展 |
| `generate-regional-agent.sh` | 生成区域定制智能体 | 本地化 |

> 提供 `.ps1` 说明对 Windows（含本项目运行环境 win32）友好；CodeBuddy 下一般**无需运行这些脚本**——直接读 `.md` 即可（见第 8 节）。

---

## 7. 集成矩阵（18 种工具）

`integrations/` 下预生成各工具专用格式。`README.md`「工具集成」详列安装位置与注意事项。要点：

- **直接复制即用**：Claude Code（`~/.claude/agents/`）、GitHub Copilot（`~/.github/agents/`）。
- **需 convert 后安装**：Cursor/Trae（`.mdc` rule，建议精选 10–20 条避免 description 互相稀释）、OpenClaw（拆 SOUL/AGENTS/IDENTITY 三文件）、Qwen/Codex/Kiro/Qoder/DeerFlow/Hermes/WorkBuddy/CodeWhale 等。
- **编译为单文件**：Aider（`CONVENTIONS.md`）、Windsurf（`.windsurfrules`）。
- **通用提醒**：全量安装 266 条 rule 会让自动匹配「几乎命中不到任何一条」；推荐精选安装或用 `@规则名` 显式调用，核心 rule（代码审查/git 工作流）可改 `alwaysApply: true`。

---

## 8. 与本父项目 AIToutiao-Engine 的关系（重点）

本仓库在本项目中扮演 **SAWORKFLOW 的「人力资源（WHO·执行）」层**（见 `AGENTS.md` 的 SAWORKFLOW 方法论章节）：

1. **角色分派**：主 Agent 收到自然语言任务后，自动进入 `[NEXUS-模式]` 流程，依据总体方案从 `agency-agents-zh-main/<部门>/<角色>.md` 读取对应角色并采用其设定执行。
2. **CodeBuddy 原生兼容**：因为全是 `SKILL.md`/Markdown + 无第三方工具绑定（红线保证），**无需运行 install/convert 脚本**即可被主 Agent 直接 `read_file` 加载——符合 AGENTS.md「绝不执行其 install/convert 脚本」的约束。
3. **代码/工程任务映射**（`AGENTS.md` 已列出）：前端/UI/Streamlit→`engineering/engineering-frontend-developer.md`；排障→`engineering/engineering-incident-response-commander.md`；最小改动→`engineering/engineering-minimal-change-engineer.md`；代码审查→`engineering/engineering-code-reviewer.md`；运维→`engineering/engineering-devops-automator.md` / `engineering/engineering-sre.md`；架构→`engineering/engineering-software-architect.md` / `engineering/engineering-backend-architect.md`；提交→`engineering/engineering-git-workflow-master.md`。
4. **质量门对齐**：内容任务过本引擎 `evaluation.py`+`write_stage`；代码任务过 `py_compile`+`read_lints`+`engineering-code-reviewer` 走查；这正呼应 NEXUS 的「现实检验者+证据」门禁思想。
5. **进阶用法**：可把 `strategy/nexus-strategy.md` 的七阶段 / 交接模板，作为本项目复杂多角色任务的编排参考（尤其 Phase B 执行阶段的角色交接）。

> 注意区分（AGENTS.md 已澄清）：本仓库的 **NEXUS** ≠ 项目 rule `agentic-workflow.mdc`（Andrew Ng 通用 Agentic Workflow）。两者术语体系不混用；NEXUS 是「角色库编排实例」，agentic-workflow.mdc 是「通用反思/迭代机制参考」。

---

## 9. 使用方式（三种）

1. **手动复制**：`cp marketing/marketing-xiaohongshu-operator.md ~/.claude/agents/` 后在对话中「激活小红书运营专家…」。
2. **脚本一键装**：`./scripts/install.sh --tool claude-code`（或 cursor/qwen/…）。
3. **作为提示词参考 / 本项目角色库**：浏览 `CATALOG.md` 中文名→路径，复制/改编内容；或在本项目由主 Agent 直接按路径 `read_file` 加载并采用人格（最常用）。

激活范式（NEXUS 风格）：
```
激活 [角色] 执行 [任务]。上下文：[背景]。交付物：[预期产出]。质量检查：完成后由证据收集者/代码审查员验证。
```

---

## 10. 维护与扩展

- **翻译上游**：从 `UPSTREAM.md` 查未覆盖项 → 译中文（自然表达、代码注释也译、保持 frontmatter）→ 提 PR。
- **新增中国原创**：直接提 PR（如新平台运营/垂直领域），遵循第 3 节格式与红线。
- **本地校验**：改完跑 `./scripts/lint-agents.sh` + `npm run check:counts` 确保 frontmatter 完整、计数一致。
- **重生成集成**：改完 `./scripts/convert.sh` 重新生成 `integrations/`。
- **上游同步**：跟踪上游 `main`，目录重命名等结构调整一周内同步；`UPSTREAM.md` 记录基线 commit 与覆盖状态。

---

## 11. 理解结论（Reflection 输出）

1. **它是什么**：266 个即插即用 AI 角色 + NEXUS 编排协议，是可移植、无广告、纯方法论的提示词库；本质是把「专家分工 + 质量门禁 + 反思闭环」沉淀为 Markdown。
2. **结构极清晰**：索引三件套（README/CATALOG/AGENT-LIST）→ 19 部门角色 → strategy 编排层 → scripts 工具链 → integrations 18 工具 → examples 实战。可分层消费。
3. **中国原创是护城河**：约 51 个贴合国内平台/合规/工业的原创角色（⭐），是区别于上游的核心价值，也是本项目最可能直接复用的部分。
4. **与本项目零摩擦**：因纯 Markdown + 红线约束，能被 CodeBuddy 主 Agent 直接读取并按 SAWORKFLOW 分角色执行，无需任何安装脚本。
5. **可借鉴的治理资产**：NEXUS 的「七阶段 + 质量门禁 + 交接模板 + 现实检验者」可直接作为本项目多角色复杂任务的编排参考；其「证据高于口说、快速失败快速修复」原则与本项目 `evaluation.py` 质量门高度同源。
6. **注意点**：① 部门数 README 说 20、实际智能体目录 19（`strategy/` 是运营文档不计）；② 中国原创数 README 正文 50 / 权威统计 51，以 `AGENT-LIST.md`/`UPSTREAM.md` 为准；③ 全量安装到 Cursor/Trae 会稀释匹配，须精选。

---

*理解完成时间：2026-07-14 ｜ 方法：agentic workflow（Planning + Tool Use + Reflection + Multi-Agent）｜ 覆盖范围：结构 / 格式 / 266 角色 / NEXUS 框架 / 工具链 / 集成 / 与 AIToutiao-Engine 关系。*
