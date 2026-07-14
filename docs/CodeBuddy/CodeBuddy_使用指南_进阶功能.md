# CodeBuddy 使用指南 — 进阶功能

> 来源: https://www.codebuddy.cn/docs/ide/  
> 抓取日期: 2026-07-13

---

## MCP

快速导航
介绍
配置
一键安装 MCP Server
自定义配置 MCP Server
使用
MCP
​
介绍
​

MCP (Model ContextProtocol，模型上下文协议) ，旨在解决大模型语言（LLM）与外部数据源及工具之间无缝集成的需求。它通过标准化 AI 系统与数据源的交互方式，帮助模型获取更丰富的上下文信息，从而生成更准确、更相关的响应。其主要的功能如下：

上下文共享：应用程序可以通过 MCP 向模型提供所需的上下文信息（如文件内容、数据库记录等），增强模型的理解能力。

工具暴露：MCP 允许应用程序将功能（如文件读写、API 调用）暴露给模型，模型可以调用这些工具完成复杂任务。

可组合的工作流：开发者可以利用 MCP 集成多个服务和组件，构建灵活、可扩展的 AI 工作流。

安全性：通过本地服务器运行，MCP 避免将敏感数据上传至第三方平台，确保数据隐私。

CodeBuddy IDE 支持您进行MCP Server 配置，扩展您的应用程序的功能。

配置
​

在侧栏对话面板右上方，点击 CodeBuddy Settings 按钮。

切换到 MCP 标签页。目前支持自定义配置 MCP Server，同时支持在 MCPMarket 中一键安装 MCP Server。

一键安装 MCP Server
​

在 MCP Market 中提供了大量的 MCP Server，您可以一键进行安装。

根据您的实际需求，选择 MCP Server 进行一键安装。安装成功后，MCP Server 显示绿色状态，如果安装失败将显示红色状态。

自定义配置 MCP Server
​

在 MCP 标签页下，点击右侧的 Add MCP 按钮。

在 json 配置文件中，添加 MCP Server 配置内容，例如：

json
{
  "mcpServers": {
    "python-tools": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "my_mcp_server"],
      "env": {
        "PYTHONPATH": "/path/to/tools"
      },
      "description": "Python toolset"
    }
  }
}
使用
​

MCP Server 安装成功后，您可以在 MCP Server 右侧点击 Tryto Run 按钮去进行验证使用；也可以直接在 Craft Agent 下输入任务需求，Agent 将根据您的任务需求进行分析，然后调用 MCP Server工具来完成您的任务。

最后更新: 2026/1/21 15:41

Pager
上一页
记忆
下一页
配置集成

---

## 配置集成

快速导航
功能特性
Supabase
连接 Supabase
在项目中使用 Supabase
断开 Supabase 连接
Tencent CloudBase
常见问题
连接失败怎么办？
如何切换不同的后端服务？
配置集成
​

CodeBuddy 集成了 Supabase 和 Tencent CloudBase 后端服务，无需进行繁琐的配置，即可获得一个可运行的后端环境。

功能特性
​
开箱即用：无需手动配置数据库、认证等后端服务
多平台支持：支持 Supabase 和腾讯云 CloudBase 两大主流后端平台
一键连接：通过简单的授权流程即可完成后端服务接入
Supabase
​

Supabase 是一个开源的 Firebase 替代方案，主要提供以下后端服务：

服务类型	说明
数据库服务	托管的 SQL 数据库，无需担心数据库运维
身份验证服务	用于应用程序的用户登录和用户管理
边缘函数	用于 API 需求，支持与 Stripe 等第三方服务通信
连接 Supabase
​

在侧栏对话框中，按路径找到并点击 Supabase 进行连接

登录或注册 Supabase 账号

完成 API 授权即可

在项目中使用 Supabase
​

选择要连接的现有 Supabase 项目，或创建一个新项目

单击 Connect project 进行连接

连接成功

在您的项目中，选择需要增加的服务即可

断开 Supabase 连接
​

在侧栏对话框中，单击 Integration 右侧的设置，进入 CodeBuddy 的配置页

在设置页中，切换到 Integrations 标签

点击所连接的 Supabase 项目右侧的 DisableConnect 即可

Tencent CloudBase
​

Tencent CloudBase（简称 TCB）是腾讯云提供的云原生一体化开发平台，主要提供以下后端服务：

服务类型	说明
登录认证	完整的用户身份管理和访问控制解决方案
数据库	基于 Serverless 架构，开通即用的数据管理服务
云函数	无需管理服务器即可运行后端代码
云存储	支持图片、文档、音视频等非结构化数据存储

常见问题
​
连接失败怎么办？
​

请检查以下几点：

确保网络连接正常
确认账号已正确登录
检查是否已完成必要的授权步骤
如何切换不同的后端服务？
​

在 Integrations 设置页中，可以断开当前连接的服务，然后重新连接其他服务。

最后更新: 2026/1/21 15:41

Pager
上一页
MCP
下一页
预览

---

## 预览

快速导航
功能特性
实时预览
方式一：自动调用
方式二：手动触发
预览效果
AI 视觉优化
方式一：自然语言优化
方式二：DOM 编辑器
修复错误
常见问题
预览页面空白怎么办？
预览
​

CodeBuddy IDE 支持通过浏览器内核自动渲染代码修改后的运行效果，允许您在不切换工具、不手动启动服务的情况下，即时查看当前工程代码的运行效果，实现 实时调试和预览。

功能特性
​
即时渲染：代码修改后自动渲染运行效果，无需手动刷新
零配置：无需手动启动服务或切换工具
视觉优化：支持选择组件通过自然语言进行 UI 优化
实时预览
​

有以下 两种方式 可以打开本地工程预览：

方式一：自动调用
​

在 CraftAgent 下代码生成或修改执行完后，Agent 自动调用工具打开 Preview。

方式二：手动触发
​
手动点击 Chat 面板右上角 Preview 工具进行预览

或者手动输入 Prompt 来触发 Agent 打开 Preview，实时预览运行效果

示例 Prompt：

text
请打开预览，让我看看当前页面的效果

预览效果
​

预览效果如下图所示：

AI 视觉优化
​

在预览页面中，您可以选择部分组件，并通过 自然语言 或 DOM 编辑器 对 UI 进行优化。

方式一：自然语言优化
​

单击 AI 视觉优化 按钮

选择需要优化的组件，在下方输入框中输入修改意见

text
请把这个按钮改成蓝色背景

查看优化效果。如果还不满意，可以继续进行样式优化

方式二：DOM 编辑器
​

您也可以使用 DOM 编辑器直接修改组件样式。

修复错误
​

点击 send errors，将错误发送到对话，由AI自动修复。

常见问题
​
预览页面空白怎么办？
​

预览页面显示空白或无法正常加载时，可能由以下原因导致：

代码存在语法错误：检查控制台是否有报错信息
依赖未正确安装：确认 node_modules 已安装，尝试重新执行 npm install
端口被占用或服务未启动：检查开发服务器是否正常运行

解决方法：

在对话中描述问题现象，例如输入"预览页面空白，请帮我排查问题"
如果预览窗口显示错误信息，点击 Send Errors 将错误发送给 AI 进行分析
尝试手动重新触发预览：点击 Chat 面板右上角的 Preview 按钮，或输入"请重新打开预览"

最后更新: 2026/1/21 15:41

Pager
上一页
配置集成
下一页
部署

---

## 部署

快速导航
快速选择
部署入口
EdgeOne Pages
CloudBase
Cloud Studio
Tencent Lighthouse
选型指引
Cloud Studio
部署流程
部署结果
EdgeOne Pages
适用场景
常见问题
部署失败怎么办？
临时地址的有效期是多久？
如何更新已部署的应用？
部署
​

连接腾讯云能力，一键交付到目标环境。

CodeBuddy 提供多种部署入口，帮助你将项目从开发预览、团队联调逐步交付到线上环境。你可以根据项目交付物形态（静态站点、服务端应用、Serverless 应用等）选择合适的部署方式。所有入口均支持在 CodeBuddy 内完成连接、配置与发布流程，减少重复配置成本。

快速选择
​
部署方式	适合场景	核心特点
EdgeOne Pages	纯静态网站/前端应用	全球 CDN 加速，自动构建
CloudBase	前端 + 云开发一体化	集成后端能力，环境隔离
Cloud Studio	临时预览/快速演示	即时预览，无需域名
Tencent Lighthouse	全栈应用/自定义服务	完整服务器控制权
部署入口
​
EdgeOne Pages
​
适用：纯静态网站与前端应用
用途：将构建产物发布为可访问的网站（如文档站、官网、前端 SPA）
典型场景：个人博客、企业官网、SPA 单页应用、营销落地页
特点：全球 CDN 边缘节点加速、自动 CI/CD、免费 HTTPS 与自动证书管理
CloudBase
​
适用：前端与云开发一体化项目
用途：以托管与函数化方式部署应用与接口，支持与 CloudBase 数据库/云函数无缝集成
典型场景：需要用户认证与数据库的应用、前后端一体化开发、轻量后端与函数接口
特点：环境隔离（开发/测试/生产）、内置 CDN 加速、安全域名配置
Cloud Studio
​
适用：开发阶段预览与联调
用途：在云端开发环境中运行项目，快速获得可访问的预览地址
典型场景：原型验证、给客户快速展示、内部测试预览、临时分享链接
特点：即时部署、无需域名配置；临时链接，不适合生产环境
Tencent Lighthouse
​
适用：需要完整运行环境的服务部署
用途：将应用交付到轻量云服务器环境，适用于需要系统级依赖或长驻服务的场景
典型场景：后端服务、全栈应用、Next.js SSR（服务端渲染）、自定义服务器配置
特点：完整的云服务器控制权、支持任意后端语言、可运行数据库与 Nginx 等服务
选型指引
​

根据交付物形态选择部署入口：

如果你的项目是纯前端静态资源（HTML/CSS/JS），推荐使用 EdgeOne Pages
如果你的项目已集成 CloudBase 数据库/认证，或需要前后端一体化能力，推荐使用 CloudBase
如果你需要快速展示给他人，且不需要长期访问，使用 Cloud Studio 进行临时预览
如果你需要完整的服务器控制权，或需要运行非静态的后端服务，选择 Tencent Lighthouse 或询问Codebuddy，获取智能建议

你也可以根据团队习惯与项目实际情况选择合适的部署方式。

Cloud Studio
​

Cloud Studio 提供一键部署能力，可将应用快速发布至云端沙箱环境，生成一个可分享的访问链接，便于团队即时试用与反馈。

部署流程
​
点击 Cloud Studio 触发 Deploy

Agent 会先扫描整个代码库，分析项目类型，选择使用 Cloud Studio 沙盒环境进行部署
部署结果
​

部署成功后，最终生成一个 可公开访问的临时地址。

EdgeOne Pages
​

EdgeOne Pages 是高效的生产级站点部署平台，能快速构建并发布静态站点和无服务器（Serverless）应用，实现从代码到线上服务的快速交付。

适用场景
​
面向公众的正式网站发布
需要稳定、高性能的生产环境
需要 CDN 加速的静态站点

部署流程

常见问题
​
部署失败怎么办？
​

请检查以下几点：

项目代码是否有语法错误
依赖是否正确安装
查看部署日志中的错误信息
临时地址的有效期是多久？
​

Cloud Studio 生成的临时地址有一定的有效期限制，如需长期使用，建议使用 EdgeOne Pages 进行正式部署。

如何更新已部署的应用？
​

修改代码后，重新触发部署即可自动更新。

最后更新: 2026/1/21 15:41

Pager
上一页
预览
下一页
智能提交

---

## 智能提交

快速导航
功能特性
使用智能提交
通过 Git 面板触发
Commit Message 规范
常用类型（type）
使用示例
常见问题
如何修改已生成的 commit message？
支持哪些 Git 操作？
智能提交
​

智能提交（Smart Commit）是 CodeBuddy 提供的 Git 提交辅助功能，能够自动分析代码变更内容，智能生成规范的 commit message，帮助开发者规范开发流程，提升团队协作效率。

功能特性
​
智能分析：自动分析代码变更内容，理解修改意图
规范生成：生成符合 Conventional Commits 规范的提交信息
一键提交：简化 Git 提交流程，提升开发效率
多语言支持：支持中英文 commit message 生成
使用智能提交
​
通过 Git 面板触发
​

点击将单个或全部文件添加到暂存区。然后点击消息右部的“AI COMMIT”按钮

在 IDE 的 Git 面板中，查看待提交的文件变更
点击 CodeBuddy 的智能提交按钮
Agent 自动分析变更内容，生成 commit message
确认无误后，点击提交即可
Commit Message 规范
​

智能提交生成的 commit message 遵循 Conventional Commits 规范：

text
<type>(<scope>): <subject>

<body>
常用类型（type）
​
类型	说明
feat	新功能
fix	修复 bug
docs	文档变更
style	代码格式调整（不影响代码逻辑）
refactor	代码重构（既不是新功能也不是修复 bug）
perf	性能优化
test	添加或修改测试
chore	构建过程或辅助工具的变动
使用示例
​

假设您修改了登录模块的验证逻辑，智能提交可能生成如下 commit message：

text
fix(auth): 修复登录验证失败时的错误提示

- 修复用户名为空时未显示错误提示的问题
- 优化密码错误时的提示文案
- 添加登录失败次数限制
常见问题
​
如何修改已生成的 commit message？
​

生成的 commit message 可以在提交前进行手动编辑，根据实际情况进行调整。

支持哪些 Git 操作？
​

智能提交主要支持：

生成 commit message
执行 git commit
可配合其他 Git 操作使用（如 push、merge 等）

最后更新: 2026/1/21 15:41

Pager
上一页
部署
下一页
微信 ClawBot 接入指南（推荐）

---

