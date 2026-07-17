# AIToutiao-Engine 网页 UI 重设计方案

> 生成日期：2026-07-14
> 类型：[NEXUS-Sprint] UI 重设计
> 审查 Agent：ui-frontend-developer + ui-code-reviewer（并行输出，本方案为汇总版）
> 设计智能库：ui-ux-pro-max（Modern Dark + Bento Grids + Cinematic Dark）
> 状态：**✅ 已执行完成（2026-07-14，5 Phase 全量落地）**

---

## 一、当前 UI 诊断（6 大核心问题）

| # | 问题 | 严重度 | 说明 |
|---|------|--------|------|
| 1 | **色彩体系廉价** | 🔴 | `#0A0E14` 纯黑底 + `#FF6B35` 暖橙强调，在暗色下刺眼不专业 |
| 2 | **布局职责重叠** | 🔴 | Sidebar 放 6 项配置 + Tab3 又放配置，用户找不到东西 |
| 3 | **工作台内容过载** | 🟡 | Tab1 堆砌：标题→状态灯→URL→空状态→进度→日志→按钮 |
| 4 | **组件风格不统一** | 🟡 | 玻璃态/阴影卡片/面板三种混用，无统一视觉语言 |
| 5 | **信息层级混乱** | 🟡 | 衬线字体 Newsreader 与工具定位不符、进度三行冗余 |
| 6 | **双轨主题冲突** | 🟡 | JS `localStorage` 按钮与 Streamlit `st.toggle` 不同步 |

---

## 二、设计系统（全量替换）

### 2.1 设计理念

**「专业 AI 内容生产仪表盘」** —— 对标 Linear / Vercel Dashboard / Notion 的克制专业风格。

核心原则：**克制**（≤4 语义色）、**清晰**（3 级信息层级）、**高效**（所有配置归 Sidebar）、**专业**（暗色为主，长时间使用不疲劳）。

### 2.2 色彩系统

#### 暗色主题（默认）

```
── 背景层级 ──
--bg-base:        #0B1120    ← 深夜蓝（替代纯黑 #0A0E14）
--bg-surface:     #111827    ← 卡片
--bg-elevated:    #1F2937    ← hover/代码区

── 文字 ──
--text-primary:   #F1F5F9    ← 主文字
--text-secondary: #94A3B8    ← 辅助
--text-muted:     #64748B    ← 禁用/占位
--text-inverse:   #0B1120    ← 强调色底上文字

── 语义色 ──
--accent:         #6366F1    ← Indigo 蓝紫（替代暖橙 #FF6B35）
--accent-hover:   #818CF8
--success:        #10B981    ← Emerald 绿（替代 #3FB950）
--warning:        #F59E0B    ← Amber
--danger:         #EF4444    ← Red（替代 #F85149）
--info:           #38BDF8    ← Sky 蓝

── 边框 ──
--border:         rgba(148,163,184,0.10)
--border-hover:   rgba(148,163,184,0.20)
--border-accent:  rgba(99,102,241,0.30)
```

#### 浅色主题（通过 `[data-theme="light"]` 切换）

```
--bg-base:        #F8FAFC    ← 暖灰白（替代刺眼白 #F8F9FB）
--bg-surface:     #FFFFFF
--bg-elevated:    #F1F5F9
--text-primary:   #0F172A
--text-secondary: #475569
--text-muted:     #94A3B8
--accent:         #4F46E5    ← 暗一个色阶的 Indigo
--success:        #059669
--warning:        #D97706
--danger:         #DC2626
--info:           #0284C7
```

#### 语义色应用映射

| 语义色 | 用途 |
|--------|------|
| `--accent` | 主按钮、链接、选中态 |
| `--success` | 完成状态、通过标记 |
| `--warning` | 运行中/进行中标记 |
| `--danger` | 错误、失败、删除 |
| `--info` | 信息提示、帮助 |

### 2.3 排版系统

```
── 字体族 ──
--font-sans:  'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif
--font-mono:  'JetBrains Mono', 'Consolas', monospace

── 字号 ──
--text-xs:	11px    ← 标签/徽章
--text-sm:	13px    ← 辅助说明
--text-base: 14px    ← 正文
--text-md:	16px    ← 卡片标题
--text-lg:	20px    ← 页面标题
--text-xl:	24px    ← 主大标题
--text-2xl:  32px

── 行高（只在 CSS 规则中指定，不作为 token）──
标题 1.2 / 正文 1.5 / 代码 1.6
```

> **关键变更**：去掉 `Newsreader` 衬线字体 → 全用 Inter 无衬线，匹配工具/仪表盘定位。

### 2.4 间距 & 圆角 & 阴影

```
── 间距（4px 基准）──
--space-xs:  4px
--space-sm:  8px
--space-md:  12px
--space-lg:  16px
--space-xl:  20px
--space-2xl: 24px
--space-3xl: 32px
--space-4xl: 48px

── 圆角 ──
--radius-sm: 6px
--radius-md: 8px
--radius-lg: 12px
--radius-xl: 16px

── 阴影 ──
--shadow-card:    0 1px 3px rgba(0,0,0,0.30)
--shadow-elevated: 0 4px 6px rgba(0,0,0,0.25), 0 10px 30px rgba(0,0,0,0.15)
--shadow-none:    none
```

### 2.5 过渡 & 组件 token

```
--transition-fast:   150ms ease
--transition-normal: 250ms ease
--transition-slow:   350ms ease
--sidebar-width:     260px
--input-height:      44px
--btn-height-lg:     48px
```

---

## 三、布局重构

### 3.1 当前 → 目标

```
当前架构                         目标架构
┌─────────────────────┐         ┌─────────────────────┐
│ Sidebar              │         │ Sidebar（统一）      │
│  内容风格/类型/主题   │         │  ⚙️ 内容配置         │
│  人工化/配图/执行范围  │         │  风格/类型/主题      │
│                      │         │  开关/执行范围       │
│ Tab1 运行监控         │         │  ──────────         │
│ Tab2 成果展示         │         │  🔑 API 密钥        │
│ Tab3 配置 ← 重叠！    │         │  DeepSeek + Agnes   │
└─────────────────────┘         │  ──────────         │
                                │  📖 快捷参考         │
                                │                      │
                                │ Tab1 🎯 工作台       │
                                │  URL + 生成 + 进度   │
                                │  + 日志（可折叠）     │
                                │                      │
                                │ Tab2 📊 成果         │
                                │  封面 + 质量 + 稿件   │
                                └─────────────────────┘
```

**关键变更**：
1. **3 Tab → 2 Tab**：删除「⚙️ 配置」Tab，全部配置归入 Sidebar
2. **Sidebar 统一**：内容配置（上）+ API 密钥（下）+ 快捷参考
3. **简化主题切换**：仅保留 Streamlit `st.toggle`，删除 JS `localStorage` 按钮

### 3.2 工作台（Tab1）布局

```
┌────────────────────────────────────────────────┐
│  🎯 AIToutiao Engine    [● 就绪]               │  ← 单行标题 + 状态
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │ 视频链接（抖音 / YouTube / B站 等）       │   │  ← 卡片式 URL 区
│  │ ┌───────────────────────────┐ ┌────────┐│   │
│  │ │ 在此粘贴链接或分享内容……    │ │▶ 一键生成││   │  ← 5:1 比例
│  │ └───────────────────────────┘ └────────┘│   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │ ① 下载  →  ② 转录  →  ③ 研究写作        │   │  ← Steps 组件
│  │         →  ④ 配图  →  ⑤ 组装            │   │
│  │ ████████████░░░░░░░░░░░  67%  3m 12s     │   │  ← 进度条 + 时间
│  └─────────────────────────────────────────┘   │
│                                                 │
│  ┌─ 📋 运行日志 ─────────────────── [展开] ─┐  │
│  │ [12:30:01] ✅ 下载完成 (15.2 MB)          │  │  ← 可折叠
│  │ [12:30:45] 🎙️ 语音转录中...               │  │
│  └──────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
```

### 3.3 成果（Tab2）布局

**空状态**：
```
┌────────────────────────────────────────────────┐
│               📊 暂无成果                        │
│          在工作台启动流水线后，                    │
│          完成的稿件将在此处展示                    │
│               [▶ 前往工作台]                      │
└────────────────────────────────────────────────┘
```

**有结果时**：
```
┌────────────────────────────────────────────────┐
│  📦 成果概览                                     │
│  ┌──────┐  ┌─────────────────────────────┐     │
│  │ 封面  │  │ 标题：XXX | 评分：88/100      │     │
│  │ 图    │  │ 字符：1200 | 迭代：3轮        │     │
│  │      │  │ [📂打开] [📥下载] [📋复制]    │     │
│  └──────┘  └─────────────────────────────┘     │
│                                                 │
│  📊 质量仪表盘（迭代历史表 + 搜索溯源）            │
│  总计3轮 | 最佳第2轮 | 最高88分 | 通过2/3        │
│  [DataFrame table]                              │
│                                                 │
│  📄 生成的稿件                                   │
│  [scrollable content preview]                   │
│                                                 │
│  📋 所有输出文件 [可展开]                        │
└────────────────────────────────────────────────┘
```

---

## 四、组件设计规范

### 4.1 主题切换

**方案**：**单一 `st.toggle`（删除 JS localStorage 按钮）**

```python
# Sidebar 中
theme = st.toggle("🌙 暗色主题", value=True, help="切换界面主题")
st.session_state.theme = "dark" if theme else "light"
```

CSS 中通过 `[data-theme="dark"]` / `[data-theme="light"]` 选择器注入 token，不再依赖 JS 操作 DOM。

### 4.2 一键生成按钮

```css
/* 主 CTA 按钮：全宽 + 加高 + 渐变 */
.btn-generate {
  height: var(--btn-height-lg);          /* 48px */
  padding: 0 var(--space-3xl);           /* 0 32px */
  background: var(--accent);             /* #6366F1 Indigo */
  color: var(--text-inverse);            /* 白字 */
  border-radius: var(--radius-md);       /* 8px */
  font-weight: 600; font-size: 15px;
  transition: all var(--transition-fast);
  box-shadow: 0 0 0 0 var(--accent);     /* 初始无 glow */
}
.btn-generate:hover {
  background: var(--accent-hover);
  box-shadow: 0 0 0 3px var(--accent-muted);  /* focus ring */
  transform: translateY(-1px);
}
.btn-generate:active {
  transform: translateY(0);
}
```

### 4.3 阶段流程 Steps

用 **水平 Steps 组件**替代当前简陋的「点+线」：

```
  ① 下载      ② 转录      ③ 研究写作    ④ 配图      ⑤ 组装
  ●━━━━━━●━━━━━━◉━━━━━━○━━━━━━○
  done      done     running   pending    pending
```

每个 step：
- **done**：实心 Indigo 点 + 绿色连线 + ✓ 图标
- **running**：呼吸动画 Indigo 点 + 灰色连线
- **pending**：空心灰色点 + 灰色连线
- **failed**：红色实心点 + 红色连线 + ✕ 图标

连接线用 `linear-gradient` 实现动态进度着色。

### 4.4 日志面板

```css
.log-panel {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  max-height: 300px;
  overflow-y: auto;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: 1.6;
  padding: var(--space-md);
}
.log-line { 
  padding: 2px 0;
  border-left: 2px solid transparent;
  padding-left: var(--space-sm);
}
/* 按级别着色左边框 */
.log-line.stage  { color: var(--accent);  border-left-color: var(--accent); }
.log-line.info   { color: var(--text-secondary); }
.log-line.success { color: var(--success); border-left-color: var(--success); }
.log-line.error  { color: var(--danger);  border-left-color: var(--danger); }
.log-line.warning { color: var(--warning); border-left-color: var(--warning); }
```

### 4.5 状态药丸 Badge

```
● 就绪          ● 运行中          ● 已完成
（灰色圆点）     （amber 呼吸）     （emerald 静态）
```

```css
.status-badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 12px;
  border-radius: var(--radius-xl);
  font-size: var(--text-sm);
  font-weight: 500;
}
.status-badge::before {
  content: ""; width: 6px; height: 6px; border-radius: 50%;
}
.status-badge.ready    { color: var(--text-secondary); background: var(--bg-elevated); }
.status-badge.ready::before { background: var(--text-muted); }
.status-badge.running  { color: var(--warning); }
.status-badge.running::before { background: var(--warning); animation: pulse-dot 1.5s ease infinite; }
.status-badge.done     { color: var(--success); }
.status-badge.done::before { background: var(--success); }
```

### 4.6 卡片

统一使用一种卡片样式（取消玻璃态和 panel 的混用）：

```css
.card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-xl);
  margin-bottom: var(--space-lg);
  box-shadow: var(--shadow-card);
  transition: border-color var(--transition-fast);
}
.card:hover {
  border-color: var(--border-hover);
}
```

---

## 五、实施路线图

### Phase 1：CSS Token 全量替换（零功能风险，~1小时）

**改动范围**：仅 `_inject_css()` 函数（当前 ~600 行 → 目标 ~400 行）

| 操作 | 说明 |
|------|------|
| 替换 `_TOKENS_DARK` | 全部 29 个 token 值替换为新色彩系统 |
| 替换 `_TOKENS_LIGHT` | 同上，对齐暗色变量名 |
| 删除死 token | `--glass-bg`, `--glass-border`, `--z-*`(×5) 删除 |
| 新增 token | `--accent-hover`, `--accent-muted`, `--bg-overlay`, `--text-primary/inverse`, `--text-secondary`, `--border-hover/accent`, `--success/warning/danger-muted`, `--shadow-elevated/none` |
| 更新字体引用 | `--font-heading` → 统一为 `--font-sans`（去掉 Newsreader） |
| 压缩 CSS 规则 | 删除未使用的 `.glass-*`、`.hero-*`、`.panel` 变体 |

**质量门**：
- `py_compile engine_app.py` 无语法错误
- `read_lints engine_app.py` 零新增告警
- 启动 Streamlit → 肉眼确认暗/亮两套主题颜色正确

### Phase 2：布局改造（~2小时）

| 操作 | 说明 |
|------|------|
| 删除 Tab3 `tab_config` | 从 `st.tabs` 移除「⚙️ 配置」 |
| 迁移配置到 Sidebar | `render_config_panel()` 内容（API Key/下载设置/快捷参考）移入 `render_sidebar()` |
| 合并 `render_sidebar()` | 内容配置（上）+ 分隔线 + API 密钥（下）+ 快捷参考 |
| 删除 JS 主题按钮 | 行 698-731 的 `<script>` 块删除 |
| 统一主题切换 | 仅保留 `st.toggle("🌙 暗色主题", ...)` |
| `render_main()` 重构 | Title + 状态药丸 合并为一行；URL 输入区卡片化 |
| `render_results()` 空状态 | 新增无结果时引导面板 |

**质量门**：
- Sidebar 功能完整（风格/类型/主题/开关/范围/API Key/参考 全部可用）
- 主题切换：toggle 拖动后立即生效，无闪烁，刷新后保持
- Tab 结构正确：仅 2 个 Tab（工作台 + 成果）

### Phase 3：组件样式重写（~1.5小时）

| 操作 | 说明 |
|------|------|
| Steps 组件重写 | 水平 Steps 替代当前「点+线」，包含序号图标 + 状态着色 + 连接线渐变 |
| 日志面板重写 | 终端风格 → Dashboard 面板风格，左色条标识级别 |
| 按钮系统统一 | 主按钮（Indigo 渐变）、次按钮（outline）、危险按钮（Red outline） |
| 卡片统一 | 全项目统一 `.card` 类 |
| 进度条优化 | 减少冗余行（仅进度条 + 百分比），增加已用时间显示 |
| 状态药丸重写 | Badge 组件带呼吸动画 |

### Phase 4：空状态 & 动效（~1小时）

| 操作 | 说明 |
|------|------|
| 工作台空状态 | 首次进入显示友好引导文案 + 示例链接 |
| 成果空状态 | 引导用户去工作台启动流水线 |
| 加载态优化 | `st.status` 分阶段反馈（引擎初始化/模型加载/转录中） |
| 过渡动效 | 所有 hover/press/状态切换加 150-250ms ease |
| `prefers-reduced-motion` | 尊重系统无障碍设置，关闭动画 |

### Phase 5：安全性加固（~30分钟）

| 操作 | 说明 |
|------|------|
| 防 XSS 加强 | `status_state`、`status_text`、阶段 `name`/`s_text`、`run_id` 加 `html.escape()` |
| API Key 提示 | 保存时追加警告「仅本地使用，请勿分享 .env 文件」 |

---

## 六、改动文件清单

| 文件 | 改动类型 | 风险 |
|------|----------|------|
| `engine_app.py` | **CSS 全量替换 + HTML 布局改造 + Sidebar 重构 + Tab 合并** | 🟡 中等（UI 层大量改动，零生产逻辑触碰） |

> 仅改 `engine_app.py` 一个文件，零生产逻辑改动（下载/转录/写作/配图/发布代码闭封不动）。

---

## 七、不改动的部分（明确约束）

- 不修改 `st.set_page_config()`（端口 8502、wide 布局不变）
- 不修改 `execute_pipeline()` / `step_download()` / `step_transcribe()` / 任何流水线阶段函数
- 不修改 `write_stage.py` / `research.py` / `evaluation.py` / `ai_writer.py` 等后端模块
- 不修改 `_generate_agnes_image()` / `_assemble_article_with_images()` 配图逻辑
- 不修改 `add_log()` / `_TeeStderr` / 日志系统
- 不修改 `_DEFAULTS` / `PipelineState` / session_state 初始化逻辑
- 不新增 Python 依赖包

---

## 八、视觉对比（关键变更一览）

| 维度 | 当前 | 目标 |
|------|------|------|
| 底色 | `#0A0E14` 纯黑 | `#0B1120` 深夜蓝 |
| 强调色 | `#FF6B35` 暖橙 | `#6366F1` Indigo 蓝紫 |
| 完成色 | `#3FB950` 亮绿 | `#10B981` Emerald |
| 字体 | Newsreader 衬线 + Roboto | Inter 无衬线（全程） |
| Tab 数 | 3（监控/成果/配置） | 2（工作台/成果） |
| 配置位置 | Sidebar(6项) + Tab3(API+) | Sidebar 全收 |
| 主题切换 | JS按钮 + Streamlit toggle 双轨 | 单一 Streamlit toggle |
| 卡片样式 | 玻璃态/阴影/面板 三种 | 统一 `.card` 一种 |
| 阶段流程 | 点 + 线（简陋） | 水平 Steps + 连线渐变 |
| CSS 行数 | ~600 行 | ~400 行 |

---

> **下一步**：等待用户确认方案后，按 Phase 1→5 顺序执行。
