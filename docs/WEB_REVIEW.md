# 网页评审报告：engine_app.py（Streamlit 引擎界面）

> 评审对象：`engine_app.py`（1899 行 → **当前 2249 行**，基于 Streamlit 的「我们的网页」——端口 8502，暗色军事风主题，含 sidebar 配置、阶段指示灯、进度条、日志面板、质量溯源、分步控制）
> 评审方式：静态代码评审（未运行实测），遵循 Agentic Workflow 反射协议
> 评审日期：2026-07-11（初评）
> **更新日期：2026-07-14（重设计完成 + audit 修复）**
> 说明：仅评审、列出不足，**不做任何程序更改**

---

## 一、总分

**71 / 100**（中等偏上，作为个人本地工具可用，距生产级 Web 有差距）

| 维度 | 分 | 说明 |
|------|----|------|
| 视觉与主题 | 16 | 暗色军事风统一、渐变标题、阶段灯动画、log/result 卡片完备 |
| 布局与信息架构 | 15 | sidebar 配置 + 主区（URL/进度/日志/结果）清晰；结果区偏长 |
| 交互与反馈 | 15 | 实时 URL 检测、状态灯、分步「下一步」、错误提示充分 |
| 正确性与健壮性 | 14 | 互斥锁防并发、线程+script_run_ctx、异常兜底、日志持久化好；但状态字典有孤儿键、进度魔法数 |
| 安全性 | 11 | 日志/稿件用 `unsafe_allow_html` 未转义；API Key 明文落盘（本地缓解） |

---

## 二、不足清单（按严重度）

### A. 安全性（最该修）
1. **HTML 注入风险**：`render_logs`（1649 行）与 `render_results` 的 `st.markdown(..., unsafe_allow_html=True)` 直接拼接 `entry["msg"]`、AI 稿件等外部内容，**未做 `html.escape`**。若内容含 `<script>`/`<img onerror>` 会被执行。
   - 缓解：当前为本地单用户桌面工具，攻击面仅限自身输入，危害有限；若部署到远程/多用户则必须修复。
2. **API Key 明文**：`_save_env` 把 Key 明文写入 `.env`（本地可接受，建议附权限提示）。

### B. 正确性与一致性
3. **状态孤儿键**：`_DEFAULTS["stage_status"]`（171–178 行）含「写作」「改写」两键，但实际 `stages` 列表（1329–1335 行）已合并为「研究写作」，这两键**永不更新、永不渲染** → 死状态。应清理为 5 阶段一致。
4. **进度魔法数字散落**：`0.05/0.18/0.28/0.58/0.62/0.65/0.67/0.70/0.80/1.0` 硬编码在多处（627/806/906/1077 等），难维护，应集中为常量或按比例计算。

### C. UI / UX
5. **文案误导**：URL 输入框 label 写「抖音视频链接」、错误提示限死「抖音链接」（1816 行），但下载同时支持 yt-dlp（多平台）。应改为「视频链接（抖音/YouTube 等）」。
6. **日志截断**：`add_log` 仅保留 `session_state.logs` 最近 200 行（264 行），长任务早期日志界面丢失（文件已持久化，可加「完整日志见文件」提示）。
7. **复制依赖 `pyperclip`**：仅本地桌面可用，远程/容器环境失败降级为 `st.code`（1779–1786 行）。
8. **无响应式**：`layout="wide"` + 固定列宽，窄屏拥挤。
9. **首启阻塞 45s**：`torch` 懒加载 spinner 无细节进度（1834 行）。

### D. 可维护性 / 架构
10. **单文件 2249 行**：UI 渲染 + 流水线编排 + 线程 + subprocess + CSS 全混，应拆 `ui/`（sidebar/main/progress/logs/results）+ `pipeline/` 编排层。
11. **颜色硬编码**：`#0D1117`/`#FF6B35` 等散落 CSS 与 Python（1552 行 `status_color`、主标题），应提取为 CSS 变量 / 设计 token。
12. **异常写法怪异**：`try/except Exception/except BaseException` 嵌套（1379–1388 行），功能可达但不规范，建议统一异常分层。

### E. 可观测 / 可访问性
13. **阶段灯仅靠颜色**（绿/橙/灰/红），色盲不友好（下方 caption 描述当前阶段部分缓解）。
14. **无空状态引导**：首次仅 URL 输入，可加示例链接/引导文案。

---

## 三、关键修正说明（评审过程中的判断校正）

- 早先怀疑「进度指示灯错位」：经核实 `execute_pipeline` 的 `stages` 列表使用「研究写作」，`render_progress` 也使用「研究写作」，**二者匹配、灯正常点亮**。
- 真正的问题是 `_DEFAULTS["stage_status"]` 中遗留的「写作」「改写」两键为**永不更新的孤儿键**（与实际 5 阶段脱节），属死状态数据，应清理。

---

## 四、可借助的改进方向（供 FIND-SKILL 检索对照）

| 不足类别 | 关键词（用于技能检索） | 期望能力 |
|----------|------------------------|----------|
| 安全：HTML 注入 / XSS | security audit, html escape, xss, code security | 自动检测/修复未转义渲染 |
| UI/UX 提升 | streamlit ui, frontend, ux, design system | 主题 token、响应式、空状态 |
| 可维护性/重构 | refactoring, code structure, modularization | 单文件拆分、常量提取 |
| 异常处理规范 | error handling, exception | 异常分层最佳实践 |
| 文案/多平台 | copy, i18n | 文案一致性 |

---

## 五、FIND-SKILL 检索结果（可解决各项不足的 skill）

> 检索方式：SkillHub 语义搜索（`/api/v1/search`）+ 分类浏览（it-ops-security / dev-programming / top）
> Fallback（Vercel `npx skills` / ClawHub `npx clawhub`）：**本环境不可用**（`npx skills` 因 Node v21 缺 `styleText` 导出、且 `yaml` 解包 ENOENT 报错）
> 检索日期：2026-07-11
> 说明：**仅检索、未安装任何 skill**（遵循「不做任何程序更改」）

### 5.1 检索结论

| 不足类别（见第二节） | 是否有精准 skill | 命中 skill |
|----------------------|------------------|-----------|
| 整体评审方法（5 维度打分法） | ✅ 精准命中 | **Code Review**（wpank） |
| 安全维度（含 HTML 注入） | ⚠️ 部分（仅 review 层面） | Code Review 类的 security 维度可辅助**发现**，但无专用「XSS 转义修复」skill |
| 可维护性 / 单文件拆分 / 重构 | ❌ 无精准 | 检索返回噪声（self-improving / weather / summarize 等无关项） |
| UI / UX / 响应式 | ❌ 无精准 | 检索返回噪声 |
| 中文多维代码审查 | ✅ 命中 | **AI Code Audit**（caingao） |
| AI 静态分析 / 逻辑流 | ✅ 命中 | **quack-code-review**（jpaulgrayson） |

### 5.2 推荐 skill 清单

| skill | slug | 相关度 | 流行度 | 适用不足 | 说明 |
|-------|------|--------|--------|----------|------|
| **Code Review** (wpank) | `code-review` | 高 | downloads 18.5K / stars 34 | 整体评审方法（A–E 全覆盖） | 系统化审查模式：安全、性能、可维护性、正确性、测试 + 严重等级 + 反模式。与本次 5 维度评审法高度契合，可复用于打分 |
| **AI Code Audit** (caingao) | `ai-code-audit` | 高 | downloads 382 / stars 0 | 中文场景、结构化 review | 中文多维审查代码变更，输出结构化 Review 意见 |
| **quack-code-review** (jpaulgrayson) | `quack-code-review` | 中高 | downloads 3.3K / stars 1 | 安全/bug 发现 | LogicArt AI 分析，发现 bug、安全问题并生成逻辑流可视化 |
| （XSS/HTML 转义修复） | — | ❌ | — | A1 | SkillHub 无精准专项；属通用工程修复 |
| （单文件拆分/重构） | — | ❌ | — | D10/D11 | SkillHub 无精准专项 |
| （Streamlit UI 设计） | — | ❌ | — | C5–C9 | SkillHub 无精准专项 |

### 5.3 建议（待用户授权后再执行）

1. **进入修复阶段时**：可安装 `code-review`（wpank）复跑本评审，用其「严重等级体系」替代/补充当前 5 维打分，提升客观性。
2. **缺口（A1 XSS、D10/D11 重构、C 类 UI）**：SkillHub 无专用 skill，建议：
   - 用本引擎已有能力直接修复（XSS 加 `html.escape`、抽 CSS 变量、拆 `ui/` 模块）；或
   - 自建专用 skill（`npx skills init`），沉淀为本项目评审/修复标准。
3. **未安装声明**：本次严格遵循「不做任何程序更改」，未向 `~/.codebuddy/skills` 写入任何 skill。如需安装上述任一 skill，请单独授权。

---

## 六、GitHub 搜索补充（弥补 SkillHub 专项缺口）

> 搜索方式：`site:github.com` 限定 GitHub 域名，针对 SkillHub 中未精准命中的「XSS 转义」「单文件拆分」「Streamlit UI」等缺口进行补充检索。
> 搜索日期：2026-07-11
> 说明：以下均为外部开源仓库引用，**未安装、未克隆**。

### 6.1 GitHub 命中汇总（按不足映射）

| 不足编号（第二节） | 不足描述 | GitHub 仓库 | Star / 类型 | 解决方式 |
|-------------------|----------|------------|------------|----------|
| A1 | HTML 注入 / XSS（`unsafe_allow_html` 未转义） | [SafeScript](https://github.com/Ishanoshada/SafeScript) | Python 模块 | `pip install safescript` → `safescript.escape_html()` 一行替换 |
| A1 | HTML 注入 / XSS | Streamlit 官方 `st.html` Docs | — | 内置 **DOMPurify** 自动净化（但仍警告开发者风险）；CVE-2023-27494 历史漏洞 |
| A（全） | 安全审计 + 代码审查 | [PS_Audit](https://github.com/Pranay-Praveen/PS_Audit) | Streamlit 工具 | 上传文件 → 自动双通道分析（语法 + 安全视角），**Streamlit 原生** |
| A（全） | AI 代码审查（安全/逻辑/重构） | [AI Code Reviewer](https://github.com/nihadidriszade1/Day8_AI_Code_Reviewer) | Llama 3.3 + Streamlit | 安全审计 + 逻辑分析 + 自动重构建议 |
| C/E（全） | Streamlit UI 设计（颜色硬编码、无设计 token、组件化） | [Microsoft Streamlit_UI_Template](https://github.com/microsoft/Streamlit_UI_Template) | 微软官方 | **CSS 模板集**：单页 chatbot / 多页 app / 仪表盘布局，含教程 |
| D10 | 1899 行单文件拆分 | [Code Splitter](https://github.com/ccarpiog/codeSplitter) | Claude Skill | 自动拆分 Python 单体文件为包结构，含**依赖验证** |
| D10 | 1899 行单文件拆分 | [Python File Splitter](https://mcpmarket.com/zh/tools/skills/python-file-splitter) | Claude Code Skill | 重构大型 Python 文件为可维护包，自动化依赖校验 |
| D10/D11/D12 | 整体架构重构 | [Lato](https://github.com/pgorecki/lato) | Python 微框架 | 依赖注入 + 类型提示，构建模块化单体（modular monolith） |
| E | Streamlit 代码规范 | [streamlit/streamlit code-style-guide](https://github.com/streamlit/streamlit/blob/develop/wiki/code-style-guide.md) | 官方 Wiki | pre-commit formatter + linter 规则，可直接套用 |

### 6.2 对比：SkillHub vs GitHub 覆盖面

| 不足类别 | SkillHub | GitHub |
|----------|----------|--------|
| 代码审查（整体评审方法） | ✅ `code-review`（wpank） | ✅ PS_Audit / AI Code Reviewer |
| XSS / HTML 转义 | ❌ 噪声 | ✅ **SafeScript**（pip installable） |
| Streamlit UI 设计 | ❌ 噪声 | ✅ **Microsoft 官方模板** |
| 单文件拆分 | ❌ 噪声 | ✅ **Code Splitter / Python File Splitter**（Claude Skill） |
| Streamlit 代码规范 | ❌ 未命中 | ✅ streamlit/streamlit 官方 style guide |
| 模块化重构 | ❌ 噪声 | ✅ Lato（依赖注入微框架） |

### 6.3 建议（展望）

- **A1 XSS**：最简单的修复——在 `render_logs` / `render_results` 中对 `msg` 加 `html.escape()`（Python 标准库 `html` 模块）。SafeScript 提供了更完整的安全套件（防 XSS + SQL 注入）。
- **C/D Streamlit UI**：Microsoft 官方模板 `Streamlit_UI_Template` 可作为 UI 重构参考（CSS 变量、组件化布局），直接替换现有硬编码颜色。
- **D10 单文件拆分**：`Code Splitter`（Claude Skill）可辅助将 `engine_app.py` 的 1899 行拆分为 `ui/`（sidebar/main/progress/logs/results）+ `pipeline/` 模块，含自动依赖验证。
- **E 代码规范**：可参考 streamlit 官方 `code-style-guide.md` 配置 pre-commit linter。

---

## 七、最终技能选型结论

> 经过 SkillHub + GitHub 双源检索、14 项不足匹配分析后，**推翻 §五.3 中"进入修复阶段时安装 `code-review`"的建议**——它属于评审方法类 skill，与 Agentic Workflow 内建的 5 维度 20 分反射协议功能重叠，引入第二套评判体系会造成标准混乱。以下为最终选定的 3 个技能（均为外部轻量方案，不纳入本项目 git 仓库）：

### 选定项（3 个）

| 技能/工具 | 类型 | 覆盖不足 | 接入方式 |
|-----------|------|----------|----------|
| **Code Splitter**（ccarpiog） | Agent Skill | D10：1899 行单文件拆分 | `git clone` 到 `~/.codebuddy/skills/code-splitter` |
| **SafeScript**（Ishanoshada） | `pip install` 库 | A1：HTML 注入（`unsafe_allow_html`） | `pip install safescript` |
| **MS Streamlit UI Template** | 参考项目（非 skill） | C8+D11：响应式 + 颜色硬编码 | 仅阅读其 CSS 变量体系，不克隆入库 |

### 已排除项（+ 淘汰理由）

| 候选 | 淘汰理由 |
|------|----------|
| `code-review`（wpank） | Agentic Workflow 已内置 5 维反射协议，引入第二套评判体系造成标准混乱 |
| `ai-code-audit`（caingao） | 同上，功能与内建协议重叠，且中文评审 ≠ 网页 UI 评审 |
| `quack-code-review`（jpaulgrayson） | 安全/逻辑分析能力已被 Agentic Workflow 安全维度覆盖 |
| `Python File Splitter` | 与 Code Splitter 功能完全重叠，Code Splitter 含依赖验证，择优保留 |
| `PS_Audit` | 独立 Streamlit 应用，非 agent skill，无法嵌入本工作流 |
| `AI Code Reviewer` | 同上，独立 Streamlit 应用 |
| `Lato` | 微框架级重构工具，对单文件拆分的粒度太重 |

### 使用约束

- **Code Splitter**：仅在重构 `engine_app.py` 时触发，拆为 `ui/`（sidebar/main/progress/logs/results）+ `pipeline/` 模块，拆分后必须通过依赖验证。
- **SafeScript**：仅一行 `escape_html()` 替代（Python 标准库 `html.escape()` 也可，SafeScript 提供额外安全套件可选）。
- **MS 模板**：仅参考其 CSS 变量/组件布局设计，不复制代码——防止与现有军事风主题冲突。
- **严禁**：将上述任一外部仓库直接纳入本项目 git 树（或通过 `.gitignore` 整体排除）。

> 注：14 项不足中，除 A1 / C8 / D10 / D11 由上述 3 个方案覆盖外，**其余 9 项（A2/B3/B4/C5/C6/C7/C9/D12/E13/E14）均为纯代码修复**，不依赖任何外部工具。


## 八、2026-07-14 更新：已完成事项

自初评以来已完成以下工作（详见 `docs/AgentsWorkSpace/项目经理/2026-07-14-full-audit-plan.md` + `docs/AgentsWorkSpace/项目经理/2026-07-14-ui-redesign-plan.md`）：

| 事项 | 初评状态 | 当前状态 |
|------|---------|---------|
| A1 HTML 注入 | `unsafe_allow_html` 未转义 | ✅ `html.escape()` 已加固 |
| B3 状态孤儿键 | 「写作」「改写」两键永不更新 | ✅ 已清理为 5 阶段一致 |
| B4 进度魔法数字 | 散落硬编码 | ✅ `_PROGRESS_MAP` + `_PROGRESS` 集中管理 |
| C5 文案误导 | 限死「抖音」 | ✅ 改为「视频链接（抖音/YouTube/B站等）」 |
| C6 日志截断 | 200 行 | ✅ 扩至 500 行 + 「完整日志见 log/」提示 |
| C8 无响应式 | layout="wide" | ✅ `@media` 断点已加 |
| D11 颜色硬编码 | 散落 CSS/Python | ✅ CSS Token `:root` 变量 + `ui/styles.css` 独立文件 |
| E13 色盲标签 | 仅颜色 | ✅ 阶段灯已加 emoji + 文字 |
| E14 空状态 | 无引导 | ✅ URL 行有引导 caption |
| — UI 重设计 | 3 Tab 混配置 | ✅ 2 Tab 工作台/成果 + Sidebar 统一收编 + Indigo 主题 |
| — 日志轮转 | 无限增长 | ✅ 10MB×3 自动轮转 + `_TeeStderr` 句柄优化 |
| — 单元测试 | 0 覆盖率 | ✅ 40 项单测 PASS（evaluation/write_stage/ai_writer/research/fact_pipeline） |

**未完成（后续规划）**：
- D10 包级拆分（`engine_app.py` → `ui/` 模块）：AGENTS.md E-3，Tier 3，待规划
- Docker 化 / CI/CD / API Key 轮换：见 audit plan Phase 3
