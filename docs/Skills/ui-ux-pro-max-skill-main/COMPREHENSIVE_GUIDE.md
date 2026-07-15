# UI/UX Pro Max Skill — 完整掌握指南

> 对 `ui-ux-pro-max-skill-main` 的全面分析文档，涵盖架构、数据库、脚本、使用方式与集成方案。
> 分析日期：2026-07-14

---

## 一、项目概览

| 属性 | 值 |
|------|-----|
| 名称 | `ui-ux-pro-max` |
| 类型 | CodeBuddy Skill（也支持 Claude/Cursor/Copilot 等 19 个 AI 平台） |
| 许可 | CC-BY-NC-4.0 |
| 安装方式 | CLI (`npm i -g ui-ux-pro-max-cli`) 或 手动复制 SKILL.md + data/ 到 `.codebuddy/skills/` |
| 文件格式 | SKILL.md（主入口） + CSV 数据库 + Python 搜索脚本 + TypeScript CLI |
| 核心能力 | UI 风格推荐、配色方案、字体配对、UX 审查、图表选型、产品设计系统推荐 |

---

## 二、架构总览（三层）

```
┌───────────────────────────────────────────────────┐
│  SKILL.md（入口层）                                 │
│  - 何时使用 / 何时跳过                               │
│  - 10 大类 UX 规则优先级速查表                        │
│  - Quick Reference（300+ 条子规则）                   │
│  - 搜索指令 (~search / ~design-system)               │
├───────────────────────────────────────────────────┤
│  Scripts（搜索层）                                   │
│  - search.py    → BM25 全文搜索引擎                  │
│  - core.py      → CSV 加载 / 缓存 / 领域搜索          │
│  - design_system.py → 产品→设计系统 推荐引擎          │
├───────────────────────────────────────────────────┤
│  Data（知识库层 — 14 个 CSV）                        │
│  - styles.csv        67 种 UI 风格                  │
│  - colors.csv        163 套产品配色方案              │
│  - typography.csv    57 组字体配对                   │
│  - ux-guidelines.csv 99 条 UX 指南                  │
│  - charts.csv        25 种图表类型决策矩阵           │
│  - ui-reasoning.csv  93+ 条 UI 推理规则              │
│  - app-interface.csv 移动端界面指南 (30 条)           │
│  - landing.csv       落地页模式                      │
│  - motion.csv        动效规范                        │
│  - products.csv      产品类型映射                    │
│  - icons.csv         图标规范                        │
│  - react-performance.csv React 性能                   │
│  - google-fonts.csv  Google Fonts 索引               │
│  - stacks/           22 个技术栈特化 CSV              │
└───────────────────────────────────────────────────┘
```

---

## 三、七大数据库详解

### 3.1 风格库（67 种）

分类体系：

| 大类 | 数量 | 代表风格 |
|------|------|---------|
| **General**（通用） | 19 | Minimalism、Neumorphism、Glassmorphism、Brutalism、Claymorphism、Aurora UI、Neubrutalism、Bento Box Grid、Y2K、Cyberpunk、Organic Biophilic、AI-Native UI、Memphis Design、Vaporwave、HUD/Sci-Fi、Pixel Art、Gen Z Chaos、Biomimetic、Anti-Polish |
| **Landing Page**（落地页） | 8 | Hero-Centric、Conversion-Optimized、Feature-Rich Showcase、Minimal & Direct、Social Proof-Focused、Interactive Product Demo、Trust & Authority、Storytelling-Driven |
| **BI/Analytics**（数据分析） | 9 | Data-Dense Dashboard、Heat Map、Executive Dashboard、Real-Time Monitoring、Drill-Down Analytics、Comparative Analysis、Predictive Analytics、User Behavior Analytics、Financial Dashboard、Sales Intelligence Dashboard |
| **Mobile**（移动端） | 10+ | Bauhaus、Minimalist Monochrome、Material You MD3、Flat Design Mobile、Claymorphism Mobile、Cyberpunk Mobile、Enterprise SaaS Mobile、Neumorphism Mobile、Neo Brutalism Mobile、Sketch Hand-Drawn Mobile 等 |
| **Special**（特殊风格） | ~20 | Spatial UI (VisionOS)、E-Ink/Paper、Kinetic Typography、Parallax Storytelling、Swiss Modernism 2.0、Dimensional Layering、3D Product Preview、Voice-First Multimodal、Interactive Cursor Design、Chromatic Aberration/RGB Split、Vintage Analog/Retro Film 等 |

每种风格记录包含：类型标签、关键词、主/辅色、特效&动画、最佳场景、禁止场景、明/暗模式支持、性能评级、无障碍评级、移动端适配、转化率适配、框架兼容性、复杂度、AI Prompt 关键词、CSS 技术关键词、实施检查清单、设计系统变量。

### 3.2 配色方案库（163 套）

按产品类型分类，每套包含 **12 个语义色值**：

| 色值 Token | 含义 |
|-----------|------|
| Primary | 主色 |
| On Primary | 主色上文字色 |
| Secondary | 辅色 |
| On Secondary | 辅色上文字色 |
| Accent | 强调色（CTA） |
| On Accent | 强调色上文字色 |
| Background | 背景色 |
| Foreground | 前景/文字色 |
| Card | 卡片背景 |
| Card Foreground | 卡片文字 |
| Muted | 弱化背景 |
| Muted Foreground | 弱化文字 |
| Border | 边框色 |
| Destructive | 危险操作色 |
| On Destructive | 危险操作上文字 |
| Ring | 聚焦环色 |

覆盖 163 种产品类型，从 SaaS、电商、金融仪表盘、医疗、教育，到游戏、加密、太空科技、量子计算等前沿领域。每种配色都有 **WCAG 对比度调优** 注释。

### 3.3 字体配对库（57 组）

字段：配对名称、分类（Serif+Sans / Sans+Sans / Display+...）、标题字体、正文字体、风格关键词、最佳场景、Google Fonts URL、CSS Import、Tailwind Config、使用注意事项。

配对类型覆盖：

| 配对类型 | 数量 | 代表作 |
|----------|------|--------|
| Serif + Sans | ~15 | Playfair Display + Inter、Cormorant + Montserrat |
| Sans + Sans | ~20 | Poppins + Open Sans、Inter + Inter、Plus Jakarta Sans |
| Display + Sans | ~8 | Bebas Neue + Source Sans 3、Righteous + Poppins |
| Mono + Sans | ~5 | JetBrains Mono + IBM Plex Sans、Fira Code + Fira Sans |
| Script + Serif/Sans | ~3 | Great Vibes + Cormorant Infant |
| 多语言专用 | ~6 | 中文(SC/TC)、日文(JP)、韩文(KR)、阿拉伯、泰文、希伯来文、越南文 |

### 3.4 UX 指南库（99 条）

按 10 大类别组织，每条含：类别、问题描述、平台、说明、Do/Don't、好/坏代码示例、严重程度（Critical/High/Medium/Low）。

| 优先级 | 类别 | 条目数 | 核心原则 |
|--------|------|--------|---------|
| **P1 (CRITICAL)** | Accessibility | ~15 | 对比度 4.5:1+、Alt 文本、键盘导航、Aria 标签 |
| **P2 (CRITICAL)** | Touch & Interaction | ~12 | 44×44px 触摸目标、8px+ 间距、加载反馈 |
| **P3 (HIGH)** | Performance | ~10 | WebP/AVIF、懒加载、预留空间防 CLS |
| **P4 (HIGH)** | Style Selection | ~8 | 匹配产品类型、一致性、SVG 图标 |
| **P5 (HIGH)** | Layout & Responsive | ~10 | 移动优先断点、viewport meta、无横向滚动 |
| **P6 (MEDIUM)** | Typography & Color | ~10 | 基础 16px、行高 1.5、语义色彩 Token |
| **P7 (MEDIUM)** | Animation | ~8 | 150-300ms 时长、运动传达意义、尊重 reduced-motion |
| **P8 (MEDIUM)** | Forms & Feedback | ~10 | 可见标签、字段旁错误、辅助文本 |
| **P9 (HIGH)** | Navigation Patterns | ~10 | 底部导航 ≤5 项、可预测的返回行为 |
| **P10 (LOW)** | Charts & Data | ~8 | 图表类型匹配、无障碍配色、数据表格替代方案 |

SKILL.md 中 Quick Reference 进一步细化为 **300+ 条子规则**，涵盖具体平台的实现细节（Apple HIG、Material Design、WCAG）。

### 3.5 图表类型决策矩阵（25 种）

核心决策字段：

| 字段 | 说明 |
|------|------|
| Data Type / Keywords | 数据类型与触发关键词 |
| Best Chart Type | 首选图表 |
| Secondary Options | 备选方案 |
| When to Use / NOT to Use | 使用/避免场景 |
| Data Volume Threshold | 数据量阈值（SVG/Canvas/聚合建议） |
| Color Guidance | 配色指导 |
| Accessibility Grade | 无障碍等级（A-AAA） |
| A11y Fallback | 无障碍回退方案 |
| Library Recommendation | 推荐库（Chart.js / Recharts / D3.js / Plotly / ApexCharts 等） |
| Interactive Level | 交互层级（Hover / Zoom / Drill / Pan / Real-time） |

覆盖 25 种类型：折线图、柱状图、饼图/甜甜圈、散点图/气泡图、热力图、地理地图、漏斗图/Sankey、仪表盘、预测线（含置信区间）、异常检测、树图、桑基图、瀑布图、雷达图、K线图、网络图、箱线图、子弹图、华夫饼图、旭日图、分解树、3D 散点/表面图、流式实时图、词云、流程图。

### 3.6 UI 推理规则库（93+ 条）

按产品类型提供设计系统推荐，每条包含：

- **UI_Category**：产品类别
- **Recommended_Pattern**：推荐布局模式
- **Style_Priority**：风格优先级（如 Glassmorphism + Flat Design）
- **Color_Mood**：色彩情感
- **Typography_Mood**：排版氛围
- **Key_Effects**：关键特效
- **Decision_Rules**：决策规则（JSON 格式，含 must_have / if_condition）
- **Anti_Patterns**：反模式
- **Severity**：严重程度

典型推理示例（B2B Service）：
```
风格: Trust & Authority + Minimalism
配色: Professional blue + Neutral grey
排版: Formal + Clear typography
特效: Section transitions + Feature reveals
必须: case-studies + roi-messaging
禁止: Playful design + Hidden credentials + AI purple/pink gradients
```

### 3.7 移动端界面指南（app-interface.csv，30 条）

针对 iOS/Android/React Native 的专项指南，涵盖：
- 无障碍：图标按钮标签、表单标签、Role/Traits、动态更新
- 触控：触摸目标 44×44pt、间距、手势冲突
- 导航：返回行为、底部标签 ≤5、模态关闭
- 表单：内联验证、键盘类型、自动聚焦、密码可见性
- 性能：虚拟化列表、图片缓存、防抖
- 动画：缓动函数、尊重 reduced-motion
- 安全区域：SafeAreaView 使用
- 主题：明暗模式对比度

---

## 四、脚本系统

### 4.1 search.py（BM25 搜索引擎）

```python
# 核心能力
- BM25 全文搜索（跨所有 CSV）
- 支持 --domain 过滤（style / color / typography / ux / chart / product / stack）
- 支持 --stack 技术栈过滤
- 支持 --json 结构化输出
- 支持 --human-readable 格式化输出

# 搜索示例
python search.py "dashboard analytics" --domain color --human-readable
python search.py "glassmorphism" --domain style
python search.py "hierarchy" --domain ux
python search.py "font pair serif" --domain typography
python search.py "trading candlestick" --domain chart
```

### 4.2 core.py（核心加载层）

- 批量 CSV 加载与内存缓存
- 领域到 CSV 文件的路由映射
- 技术栈覆盖查找（`--stack` 参数时搜索 `data/stacks/*.csv` 覆盖默认 CSV）

### 4.3 design_system.py（设计系统推荐引擎）

```python
python design_system.py "financial dashboard"
# 输出：
#   Style Priority: Dark Mode (OLED) + Data-Dense
#   Color Mood: Dark bg + Red/Green alerts + Trust blue
#   Typography: Clear + Functional
#   Key Effects: Real-time number animations + Alert pulse
#   Must Have: real-time-updates, high-contrast
#   Anti-Patterns: Light mode default, Slow rendering
```

---

## 五、技术栈特化数据（22 种）

每个技术栈有独立的 CSV 文件（`data/stacks/`），提供框架特定的实现建议：

| 技术栈 | 文件 | 覆盖内容 |
|--------|------|---------|
| React | `react.csv` | 组件结构、hooks 模式、状态管理 |
| Next.js | `nextjs.csv` | SSR/SSG、路由、Image 组件 |
| Vue | `vue.csv` | 组合式 API、单文件组件 |
| Angular | `angular.csv` | 模块/组件、RxJS |
| Svelte | `svelte.csv` | 响应式声明 |
| React Native | `react-native.csv` | 原生组件、性能 |
| Flutter | `flutter.csv` | Widget 树、Material |
| SwiftUI | `swiftui.csv` | 声明式 UI、HIG |
| Tailwind | `html-tailwind.csv` | 工具类映射 |
| shadcn/ui | `shadcn.csv` | 组件组合 |
| Three.js | `threejs.csv` | 3D 渲染 |
| 其他 | astro / laravel / nuxt / jetpack-compose / winui / wpf / avalonia / javafx / uwp / uno |

---

## 六、平台集成（19 个模板）

`templates/platforms/` 包含 19 个 AI 平台的安装配置：

| 平台 | 安装路径 | 文件 |
|------|---------|------|
| **CodeBuddy** | `.codebuddy/skills/ui-ux-pro-max/` | `SKILL.md` |
| Claude Code | `.claude/skills/ui-ux-pro-max/` | `SKILL.md` |
| Cursor | `.cursor/rules/` | `ui-ux-pro-max` |
| Windsurf | `.windsurf/rules/` | — |
| GitHub Copilot | `.github/copilot-instructions.md` 或 `.github/prompts/` | — |
| Codex | `skills/ui-ux-pro-max/` | `SKILL.md` |
| 其他 13 个 | 各平台目录 | — |

每个模板 json 定义了 `folderStructure`、`scriptPath`、`frontmatter` 等，CLI (`uipro init --ai <platform>`) 自动生成。

---

## 七、CLI 工具

```bash
# 全局安装
npm install -g ui-ux-pro-max-cli

# 安装到特定 AI 助手
uipro init --ai codebuddy    # CodeBuddy
uipro init --ai claude       # Claude Code
uipro init --ai cursor       # Cursor
uipro init --ai all          # 所有助手

# 其它命令
uipro init --force           # 覆盖已有文件
uipro versions               # 查看可用版本
uipro update                 # 更新 CLI + 数据
```

原理：CLI 从 GitHub 拉取最新模板和数据，按平台配置生成对应文件。CodeBuddy 环境下建议**手动复制** `SKILL.md` + `data/` + `scripts/` 到 `.codebuddy/skills/ui-ux-pro-max/`。

---

## 八、知识注入层级（在 CodeBuddy 中的定位）

```
L1 始终层  →  AGENTS.md + alwaysApply Rules
L2 按需层  →  Skills (SKILL.md) ← ui-ux-pro-max 在此层
L3 主动层  →  @Docs / @Files / @Git / MCP
L4 记忆层  →  Memory + Working Memory
L5 网络层  →  web_search / web_fetch
```

`ui-ux-pro-max` 作为 Skill 驻留在 L2 层：AI 遇到 UI 相关任务时按需加载 `SKILL.md`，进而调用 `scripts/search.py` 查询数据库。

---

## 九、与本项目的关联

### 当前集成状态

| 项目 | 状态 |
|------|------|
| `.codebuddy/skills/ui-ux-pro-max/` | ✅ 已安装 (2026-07-13) |
| `ui-designer` Subagent | ✅ 已创建，引用此 Skill |

### 适用场景

本 Skill 可用于：
1. **`engine_app.py` Streamlit UI 优化**：查询 UX 指南（表单、反馈、布局、无障碍）
2. **配色方案选择**：从 163 套中选择适合「AI 内容引擎」的配色
3. **字体配对**：从 57 组中选择中文友好的组合（含简体中文专用配对 `Noto Sans SC`）
4. **图表选型**：为数据展示面板选择最佳图表类型
5. **移动端适配**（如未来做移动版）：参考 app-interface.csv 的 30 条移动端指南

### 对 `ui-designer` Subagent 的价值

Subagent 的 System Prompt 已引用此 Skill，可用于：
- 审查 Streamlit UI 的无障碍合规性
- 推荐与内容生产引擎匹配的设计风格
- 提供 CSS/token 级别的配色方案
- 在 UI 重构时快速查询最佳实践

---

## 十、数据库使用速查表

```
需求场景                     → 搜索命令 / 查询目标
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
为新项目选风格                → ~search "风格关键词" --domain style
选产品配色                    → ~search "产品类型" --domain color
选字体配对                    → ~search "字体关键词" --domain typography
审查无障碍                    → ~search "accessibility contrast" --domain ux
选图表类型                    → ~search "趋势 时间序列" --domain chart
完整设计系统推荐               → ~design-system "产品类型"
查特定技术栈实现               → ~search "问题" --domain ux --stack react
落地页设计                    → ~search "hero cta" --domain style
移动端适配                    → ~search "touch target" --domain ux
动效规范                      → ~search "animation duration" --domain ux
```

---

## 十一、总结

`ui-ux-pro-max` 是一个**全面的 UI/UX 设计智能知识库**，规模如下：

| 维度 | 数量 |
|------|------|
| UI 风格 | 67 种 |
| 配色方案 | 163 套（每套 12 色值） |
| 字体配对 | 57 组 |
| UX 指南 | 99 条（扩展为 300+ 子规则） |
| 图表类型 | 25 种（含完整决策矩阵） |
| 设计推理规则 | 93+ 条 |
| 技术栈特化 | 22 种 |
| 平台模板 | 19 个 |
| 移动端专项 | 30 条 |
| **总 CSV 行数** | **~2000+ 行结构化数据** |

**核心优势**：
- 数据库驱动 → 可搜索、可验证、非纯 prompt 幻觉
- 平台无关 → 同一数据通过模板适配 19 个 AI 平台
- 生产级别 → 含 WCAG 对比度验证、代码示例、Do/Don't
- 可扩展 → CSV 格式易于追加新风格/配色/技术栈
