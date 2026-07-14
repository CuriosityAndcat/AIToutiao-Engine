# CodeBuddy 用户指南

> **来源**: https://www.codebuddy.cn/docs/ide/User-guide/Overview
> **抓取时间**: 2026-07-13

---

## 1. 基础能力（5 项）

### 1.1 智能对话
多轮对话与复杂逻辑推导，支持技术问答、代码解释、架构建议等。

### 1.2 代码补全
毫秒级预测，适配项目私有风格。支持上下文的智能补全和 NES（Next Edit Suggestions）前瞻式编辑，快捷键 `Ctrl + Shift + Enter`。

### 1.3 Figma 转代码
UI 设计稿直接转化为高质量前端代码，内置 Figma 集成功能。

### 1.4 组件库集成
支持企业级 UI 组件，基于 TDesign、MUI、Shadcn 等，可通过自然语言调整样式。

### 1.5 智能诊断
自动发现 Bug 与性能瓶颈，一键修复。

---

## 2. 快速开始

### 2.1 对话入口

| 操作系统 | 内联对话 | 侧边栏对话 |
|----------|----------|------------|
| **macOS** | `⌘ + I` | `Ctrl + ⌘ + I` |
| **Windows** | `Ctrl + I` | `Ctrl + Win + I` |

### 2.2 基础交互
- **新建会话**：点击 `+` 按钮
- **上下文引用**：使用 `@` 符号引用文件、代码块、函数等
- **多模态输入**：支持图片拖拽、截图直接粘贴到对话框

---

## 3. 智能工作流（三种模式）

| 模式 | 说明 |
|------|------|
| **Ask（对话模式）** | 技术问答，不修改代码。适合提问、解释代码、讨论方案 |
| **Craft（Agent模式）** | 代码生成与局部修改。AI 自动调用工具完成代码编写、文件操作等任务 |
| **Plan（计划模式）** | 跨文件复杂任务，先制定计划再执行。AI 会先规划步骤，用户确认后再执行 |

- 支持**自定义 Agent** 创建，分为 Agentic（自动调用）和 Manual（手动选择）两种模式

---

## 4. 进阶特性

| 特性 | 说明 |
|------|------|
| **Memory（记忆）** | AI 自动记住偏好与重要信息，持续优化对话体验。可在设置中开启/关闭 |
| **Rules（规则）** | 自定义编码规范。支持用户级规则和项目级规则，可选择多种类型 |
| **Skills（技能）** | 专业指令集，封装可复用的工作流。内置 skill-creator，可通过对话交互创建自定义 Skill |
| **MCP（模型上下文协议）** | 支持 MCP 服务器扩展，可访问文件系统、调用 LLM 生成响应等 |
| **自定义模型** | 支持在 `.codebuddy/models.json` 中配置私有或第三方模型 API 接入 |
| **自定义指令** | 通过 Slash Command 创建个性化快捷指令 |

---

## 5. 集成与生态

### 5.1 云服务
- **CloudBase**：腾讯云全栈后端服务
- **Supabase**：开源 BaaS 平台
- **CloudStudio**：一键部署沙箱环境

### 5.2 前端组件
标准化组件库规范，支持自然语言调整界面样式和布局。

### 5.3 设计组件
- **Figma**：设计稿直接导入，一键转换为生产代码
- **DOM 实时编辑**：内置浏览器支持 DOM 编辑与屏幕尺寸切换

---

## 6. 用户指南子页面索引

完整用户指南包含以下子页面（部分页面需登录访问）：

```
/docs/ide/User-guide/Code-Completion      # 代码补全
/docs/ide/User-guide/Memory               # 记忆功能
/docs/ide/User-guide/Rules                # 规则配置
/docs/ide/User-guide/MCP                  # MCP 协议
/docs/ide/User-guide/Slash-Commands       # 斜杠指令
/docs/ide/User-guide/config-integration   # 集成配置
/docs/ide/User-guide/Features/Plan-Mode   # 计划模式
/docs/ide/User-guide/Features/Skills      # 技能管理
/docs/ide/User-guide/Features/Subagents   # 子代理
/docs/ide/User-guide/Features/models      # 模型配置
```

---

*文档整理自 CodeBuddy 官方用户指南，仅供学习参考*
