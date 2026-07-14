# CodeBuddy 平台接入与高级功能

> 来源: https://www.codebuddy.cn/docs/ide/  
> 抓取日期: 2026-07-13

---

## 微信ClawBot

快速导航
前提条件
配置微信 ClawBot 集成
1. 进入 Claw 设置
2. 等待二维码生成
3. 使用微信扫描二维码
4. 确认绑定成功
开始使用
常见问题
CodeBuddy 接入微信 ClawBot 指南
​

本指南将帮助您通过 CodeBuddy 的「微信 ClawBot 集成」能力，将 CodeBuddy 接入微信。绑定后，您可以直接在微信中向电脑上的 CodeBuddy 发送任务，并接收执行结果。

前提条件
​

在开始之前，请确保您已满足以下条件：

已在电脑上安装并登录CodeBuddy IDE
手机上已登录一个可正常使用的微信 >= 8.0.70

微信 ClawBot 接入无需填写 App ID、App Secret 等开发凭证，只需扫码即可完成绑定。

配置微信 ClawBot 集成
​
1. 进入 Claw 设置
​
打开 CodeBuddy Agent 工作台
在左侧 Claw 栏点击齿轮图标，进入「Claw 设置」

在集成列表中找到「微信 ClawBot 集成」
点击右侧的「配置」按钮

2. 等待二维码生成
​

点击「配置」后，按钮会短暂显示为「绑定中...」，CodeBuddy 正在生成用于绑定的二维码。

3. 使用微信扫描二维码
​

二维码生成后会直接显示在卡片下方。打开手机微信，扫描该二维码即可完成绑定。

注意

二维码有时效限制。如果二维码过期或扫码失败，请重新点击「配置」生成新的二维码。

4. 确认绑定成功
​

扫码完成后，卡片状态会变为「已连接」。如果后续需要更换账号，可以点击「解绑」后重新绑定。

开始使用
​

绑定完成后，您就可以直接在微信里和 CodeBuddy 对话，例如：

帮我总结今天桌面上最新的会议记录
帮我检查这个项目最近改过的接口有没有明显问题
帮我生成一个登录页原型

CodeBuddy 会在电脑上自动执行任务，并把执行过程和最终结果同步回微信聊天窗口。

如果您已经能在微信里收到 CodeBuddy 的执行结果，说明微信 ClawBot 接入已完成。

当微信消息到达时，CodeBuddy 会自动切换到 Claw 标签页并加载对应的会话，无需手动切换。

常见问题
​

Q：页面一直停留在绑定中怎么办？

确认电脑上的 CodeBuddy 正在运行，且网络连接正常
关闭当前配置窗口后重新进入「微信 ClawBot 集成」
如果问题仍然存在，重启 CodeBuddy 后重新绑定

Q：扫码后没有显示已绑定怎么办？

确认扫码使用的是您希望绑定的微信账号
等待几秒钟让绑定状态同步
如果二维码已经失效，请点击「重试」生成新的二维码后再次扫码

Q：微信里发消息没有响应怎么办？

确认电脑上的 CodeBuddy 仍在运行，且 Claw 服务未关闭
返回「Claw 设置」检查微信 ClawBot 集成状态是否仍为「已绑定」
如有必要，可先解绑后重新扫码绑定

最后更新: 2026/7/2 15:35

Pager
上一页
智能提交
下一页
模型配置

---

## 模型配置

快速导航
概述
配置文件位置
用户级配置
项目级配置
配置优先级
配置结构
配置字段说明
models
LanguageModel 字段
availableModels
使用场景
1. 添加自定义模型
2. 覆盖内置模型配置
3. 限制可用模型列表
4. 项目特定配置
热重载
标签系统
合并策略
示例配置
API 端点 URL 格式说明
OpenRouter 平台配置示例
DeepSeek 平台配置示例
完整示例
故障排查
配置未生效
模型未在列表中显示
热重载未触发
models.json 配置指南
​
概述
​

models.json 是一个配置文件，用于自定义模型列表和控制模型下拉列表的显示。该配置支持两个级别：

用户级: ~/.codebuddy/models.json - 全局配置，适用于所有项目
项目级: <workspace>/.codebuddy/models.json - 项目特定配置，优先级高于用户级
配置文件位置
​
用户级配置
​
~/.codebuddy/models.json
项目级配置
​
<project-root>/.codebuddy/models.json
配置优先级
​

配置合并优先级从高到低：

项目级 models.json
用户级 models.json
内置默认配置

项目级配置会覆盖用户级配置中的相同模型定义（基于 id 字段匹配）。availableModels 字段：项目级完全覆盖用户级，不进行合并。

配置结构
​
json
{
  "models": [
    {
      "id": "model-id",
      "name": "Model Display Name",
      "vendor": "vendor-name",
      "apiKey": "sk-actual-api-key-value",
      "maxInputTokens": 200000,
      "maxOutputTokens": 8192,
      "url": "https://api.example.com/v1/chat/completions",
      "supportsToolCall": true,
      "supportsImages": true
    }
  ]
}
配置字段说明
​
models
​

类型： Array<LanguageModel>

定义自定义模型列表。可以添加新模型或覆盖内置模型配置。

LanguageModel 字段
​
字段	类型	必填	说明
id	string	✓	模型唯一标识符
name	string	-	模型显示名称
vendor	string	-	模型供应商 （如 OpenAI, Google）
apiKey	string	-	API 密钥（实际密钥值，非环境变量名）
maxInputTokens	number	-	最大输入 token 数
maxOutputTokens	number	-	最大输出 token 数
url	string	-	API 端点 URL (必须是接口完整路径,一般以 /chat/completions 结尾）
supportsToolCall	boolean	-	是否支持工具调用
supportsImages	boolean	-	是否支持图片输入
supportsReasoning	boolean	-	是否支持推理模式

重要说明：

目前仅支持 OpenAI 接口格式的 API
url 字段必须是接口完整路径,一般以 /chat/completions 结尾
例如: https://api.openai.com/v1/chat/completions 或 http://localhost:11434/v1/chat/completions
availableModels
​

类型： Array<string>

控制模型下拉列表中显示哪些模型。只有在此数组中列出的模型 ID 才会在 UI 中显示。

如果未配置或为空数组，则显示所有模型
配置后，只显示列出的模型 ID
可以同时包含内置模型和自定义模型的 ID
使用场景
​
1. 添加自定义模型
​

在用户级或项目级添加新的模型配置：

json
{
  "models": [
    {
      "id": "my-custom-model",
      "name": "My Custom Model",
      "vendor": "OpenAI",
      "apiKey": "sk-custom-key-here",
      "maxInputTokens":128000,
      "maxOutputTokens":4096,
      "url": "https://api.myservice.com/v1/chat/completions",
      "supportsToolCall": true
    }
  ]
}
2. 覆盖内置模型配置
​

修改内置模型的默认参数：

json
{
  "models": [
    {
      "id": "gpt-4-turbo",
      "name": "GPT-4 Turbo (Custom Endpoint)",
      "vendor": "OpenAI",
      "url": "https://my-proxy.example.com/v1/chat/completions",
      "apiKey": "sk-your-key-here"
    }
  ]
}
3. 限制可用模型列表
​

只在下拉列表中显示特定模型：

json
{
  "availableModels": [
    "gpt-4-turbo",
    "gpt-4o",
    "my-custom-model"
  ]
}
4. 项目特定配置
​

为特定项目使用不同的模型或 API 端点：

项目 A (.codebuddy/models.json):

json
{
  "models": [
    {
      "id": "project-a-model",
      "name": "Project A Model",
      "vendor": "OpenAI",
      "url": "https://project-a-api.example.com/v1/chat/completions",
      "apiKey": "sk-project-a-key",
      "maxInputTokens":100000,
      "maxOutputTokens":4096
    }
  ],
  "availableModels": ["project-a-model", "gpt-4-turbo"]
}

删除配置中的 "availableModels" 字段后，需要同步删除上方，后再保存配置。

项目A修改示例：

热重载
​

配置文件支持热重载：

文件变更会被自动检测
使用 1 秒防抖延迟避免频繁重载
配置更新后会自动同步到应用

监听的文件：

~/.codebuddy/models.json （用户级）
<workspace>/.codebuddy/models.json （项目级）
标签系统
​

通过 models.json 添加的模型会自动标记 custom 标签，便于在 UI 中识别和过滤。

合并策略
​

配置使用 SmartMerge 策略：

相同 ID 的模型配置会被覆盖
不同 ID 的模型会被追加
项目级配置优先于用户级配置
availableModels 过滤在所有合并完成后执行
示例配置
​
API 端点 URL 格式说明
​

必须使用完整路径： 所有自定义模型的 url 字段一般以 /chat/completions 结尾。

✅ 正确示例：

https://api.openai.com/v1/chat/completions
https://api.myservice.com/v1/chat/completions
http://localhost:11434/v1/chat/completions
https://my-proxy.example.com/v1/chat/completions

❌ 错误示例：

https://api.openai.com/v1
https://api.myservice.com
http://localhost:11434
OpenRouter 平台配置示例
​

使用 OpenRouter 访问多种模型：

json
{
  "models": [
    {
      "id": "openai/gpt-4o",
      "name": "open-router-model",
      "url": "https://openrouter.ai/api/v1/chat/completions",
      "apiKey": "sk-or-v1-your-openrouter-api-key",
      "maxInputTokens":128000,
      "maxOutputTokens":4096,
      "supportsToolCall": true,
      "supportsImages": false
    }
  ]
}
DeepSeek 平台配置示例
​

使用 DeepSeek 模型：

json
{
  "models": [
    {
      "id": "deepseek-chat",
      "name": "DeepSeek Chat",
      "vendor": "DeepSeek",
      "url": "https://api.deepseek.com/v1/chat/completions",
      "apiKey": "sk-your-deepseek-api-key",
      "maxInputTokens":32000,
      "maxOutputTokens":4096,
      "supportsToolCall": true,
      "supportsImages": false
    }
  ]
}
完整示例
​
json
{
  "models": [
    {
      "id": "gpt-4o",
      "name": "GPT-4o",
      "vendor": "OpenAI",
      "apiKey": "sk-your-openai-key",
      "maxInputTokens":128000,
      "maxOutputTokens":16384,
      "supportsToolCall": true,
      "supportsImages": true
    },
    {
      "id": "my-local-llm",
      "name": "My Local LLM",
      "vendor": "Ollama",
      "url": "http://localhost:11434/v1/chat/completions",
      "apiKey": "ollama",
      "maxInputTokens":8192,
      "maxOutputTokens":2048,
      "supportsToolCall": true
    }
  ],
  "availableModels": [
    "gpt-4o",
    "my-local-llm"
  ]
}
故障排查
​
配置未生效
​
检查 JSON 格式是否正确
确认文件路径是否正确
查看日志输出确认配置是否被加载
确认环境变量中的 API 密钥是否已设置
模型未在列表中显示
​
检查模型 ID 是否在 availableModels 中列出
确认 models 配置是否正确
验证必填字段 （id, name, provider) 是否都已提供
热重载未触发
​
配置文件变更有 1 秒防抖延迟
确保文件确实被保存到磁盘
检查文件监听是否正常启动 （查看调试日志）

最后更新: 2026/5/8 10:42

Pager
上一页
微信 ClawBot 接入指南（推荐）
下一页
Plan 模式

---

## Plan模式

快速导航
介绍
为什么选择 Plan
传统 AI 助手的困境
Plan Mode 的解法
Plan Mode vs Craft Mode：什么时候用哪个？
进入与选择 Plan Mode
使用方式：Plan 的五步生命周期
第一步：需求澄清（Prepare 状态）
第二步：方案制定（Prepare 状态）
第三步：方案编辑/确认（Ready 状态）
第四步：方案实施（Building 状态）
第五步：方案完成（Finished 状态）
使用原则
任务粒度控制
Preview 阶段的审阅价值
扩展能力的协同作用
Plan 的复用价值
Plan 与 Craft 的灵活切换
Plan Mode
​
介绍
​

Plan Mode 致力于让「计划」本身成为研发流中的第一公民：在 IDE 内完成需求澄清、方案设计、任务拆解与执行协同，不必跳转多款工具。Plan 以轻量、可交互的 AI 协作方式，把 MCP、Skill、Subagent 等能力编织成可插拔的矩阵，既能满足小团队的敏捷协作，也能支撑大型项目的定制化治理。

为什么选择 Plan
​
传统 AI 助手的困境
​

想象一个熟悉的场景：

你正在开发一个功能，对 AI 助手说：「帮我实现一个购物车，支持增删改查和结算」。AI 开始工作了——它创建了一个文件，写了一些代码，然后...它创建了另一个文件，又写了一些代码。

十分钟后，你发现：

数据结构设计得很奇怪，和你现有的用户系统对不上
状态管理用了一个你从没用过的库
有三个文件的命名风格完全不一致
你专属于自己的 MCP、Skill、SubAgent 等没有在你的预期内使用
最关键的是，它漏掉了优惠券功能

问题的根源是什么？ AI 收到指令就立即动手，没有先对齐需求、拆解任务、确认方向——缺少一个关键环节：规划。

Plan Mode 的解法
​

CodeBuddy 在「理解」和「执行」之间插入了「规划」环节——在执行前先想清楚要做什么、怎么做、分几步做。

痛点	传统模式	Plan Mode
执行偏差	AI 的实现方向与用户预期不符	需求澄清环节对齐预期
不可控性	用户无法预知 AI 会做什么	方案预览，执行前可审阅
修正成本高	每次修改都可能引入新问题	完整规划，避免反复
上下文丢失	长对话中 AI 逐渐「忘记」初衷	计划持久化，状态可追溯
Plan Mode vs Craft Mode：什么时候用哪个？
​

Plan 和 Craft 不是非此即彼的选择，而是针对不同场景的两种协作模式。理解它们的差异，能让你的开发效率翻倍。

维度	Plan Mode	Craft Mode
工作方式	先规划后执行，在编码前明确方案	直接执行，快速响应指令
适用场景	复杂功能、架构设计、多文件协同	局部修改、单文件优化、Bug 修复
输出形式	完整方案（需求+技术+设计+任务）	直接代码结果
可控性	高 - 执行前可审阅和调整方案	中 - 边执行边调整
扩展能力	智能编排 MCP/Skill/SubAgent	按需调用扩展

选择 Plan Mode 的典型场景：

🏗️ 新功能从零实现 - 需要明确技术选型、架构设计和实现路径
🔄 多文件协同修改 - 涉及多个模块，需要统一的技术方案指导
🎨 UI/UX 设计与实现 - 需要先设计视觉风格和交互逻辑再编码
🔧 存量项目改造 - 需要理解现有架构，确保新功能符合项目规范
📋 复杂任务拆解 - 需要将大型需求分解为可执行的步骤

选择 Craft Mode 的典型场景：

🐛 快速 Bug 修复 - 问题明确，需要快速定位和修复
✨ 单文件局部调整 - 改动范围小，直接执行更高效
📝 代码重构优化 - 针对已有代码进行改进
🔍 代码解释理解 - 需要理解某段代码的作用

Plan Mode 的核心价值：

规划准确性 - 通过渐进式澄清对话，确保 AI 真正理解你的需求
方案全面性 - 输出包含需求分析、技术架构、视觉设计、任务拆解的完整方案
执行可控性 - 在代码生成前可以审阅和调整方案，避免后期重构
扩展协同性 - 智能编排 MCP、Skill、SubAgent 等扩展能力，生成专属方案
知识复用性 - 完成的 Plan 保存为 Markdown，可作为项目知识库复用
进入与选择 Plan Mode
​
打开侧栏，选择 Plan Mode。
在入口可查看已保存的计划列表或新建计划。
若已有项目计划，可直接打开，未完成的计划会保留上下文与执行进度。
选择 Plan Mode	新建计划入口

	
计划概览

使用方式：Plan 的五步生命周期
​

Plan 将一次协同过程拆分为五个阶段，每个阶段都支持人机协作与图片提示，帮助你在 IDE 内完成从想法到落地的闭环。

mermaid
flowchart LR
  A[需求澄清] --> B[方案制定]
  B --> C[方案编辑/确认]
  C --> D[方案实施]
  D --> E[方案完成]

  style A fill:#e6f3ff
  style B fill:#fff3e6
  style C fill:#e6ffe6
  style D fill:#ffe6e6
  style E fill:#f3e6ff

第一步：需求澄清（Prepare 状态）
​

在这一阶段，AI 会通过渐进式对话帮你明确需求边界，确保双方对任务的理解一致。

具体操作：

描述需求 - 在输入框中描述你的目标或粘贴需求文档
回答澄清问题 - AI 会提出 1-2 个关键问题，确认技术栈、功能范围、限制条件等
确认需求 - 回答完所有问题后，AI 会生成需求总结，确认后进入下一步
AI 提出澄清问题	提供选项供用户选择

	

小贴士：

提供尽可能具体的上下文（技术栈、项目结构、期望效果等）
可以直接粘贴需求文档或设计稿截图
澄清问题的质量直接影响后续方案的准确性
第二步：方案制定（Prepare 状态）
​

需求确认后，AI 会生成完整的方案草稿。这是 Plan Mode 的核心——在执行前就把所有事情想清楚。

方案生成过程：

Plan 会根据你提供的任务要求，先给出实施大纲，再在已有的项目中搜索相关的代码、设计、文档等，生成方案草稿。

方案包含的内容：

模块	说明
需求分析	提炼核心价值、功能边界和预期输出
技术方案	技术选型、架构设计、关键组件和数据流
视觉设计	UI 风格、交互逻辑、配色方案（如适用）
任务列表	可执行的步骤清单，标明依赖关系和优先级
扩展能力	推荐使用的 MCP/Skill/SubAgent 及其用途

AI 会智能编排你的扩展能力：

分析任务需求，自动匹配合适的 MCP、Skill、SubAgent
在方案中说明每个扩展的作用和预期产出
避免幻觉调用，只使用你已配置的扩展
第三步：方案编辑/确认（Ready 状态）
​

生成方案后，你可以审阅、编辑并确认。这是「执行前可预见」的关键环节——在代码生成前修正方向，避免后期重构。

可以编辑的内容：

编辑类型	操作
正文内容	调整描述、补充约束、添加参考链接
技术方案	修改技术选型、调整架构设计
任务列表	插入/删除/重排任务，补充执行细节
扩展能力	增删插件或智能体以适配新场景
Markdown 编辑	更新任务列表

	
设计配置编辑	方案扩展配置

	

确认执行前检查：

技术方案是否符合项目现有架构？
任务拆解是否完整，依赖顺序是否正确？
设计规范是否与现有 UI 风格一致？
扩展能力选择是否合理？
第四步：方案实施（Building 状态）
​

点击「开始执行」后，计划进入执行阶段。AI 会按照任务列表逐步执行，并实时反馈进度。

执行过程：

状态切换 - 计划状态变为 Building，任务按序执行
进度反馈 - AI 每完成一个任务会标记状态，你可以实时查看进度
中断处理 - 执行中可以随时暂停，提出新需求或调整方向
深度调用扩展 - AI 会按照方案中的规划，深度调用 MCP、Skill 等扩展能力

执行状态	过程结果

	

执行中的调整：

微调方案 - 可以在编辑区修改正文，diff 会高亮显示变化
切换 Craft - 对于局部问题，切换到 Craft Mode 快速修复更高效
中断恢复 - 遇到新需求时，AI 会暂停当前计划，处理完后再恢复

第五步：方案完成（Finished 状态）
​

全部任务完成后，计划进入完成状态。

完成后的操作：

操作	说明
查看成果	在编辑器中查看生成的代码和修改的文件
归档计划	计划自动保存为 Markdown 文件，位于 .codebuddy/plans/
导出分享	可下载计划文件，与团队共享或继续迭代
复用知识	历史计划可作为上下文引用，帮助 AI 快速理解项目背景
完成与保存	下载计划

	
使用原则
​
任务粒度控制
​
做法	原因	风险
单一 Plan 聚焦单一功能模块	AI 在有限上下文内保持一致性更强	过大的 Plan 会导致命名不一致、接口风格混乱、状态管理冲突
功能模块完成后再开始下一个	可验证的中间产物便于问题定位	多个未完成的 Plan 并行会增加上下文混乱
复杂需求由 AI 自行拆分	AI 能基于技术依赖关系合理划分边界	人工强制拆分可能破坏模块间的自然耦合
Preview 阶段的审阅价值
​

在方案生成后、执行前认真审阅，是避免后期重构的关键环节。

审阅维度	检查要点	修正成本对比
技术方案	是否符合项目现有架构、技术栈选择是否合理	Preview 修改：几乎为零 / 代码完成后修改：可能需要重构
任务拆解	是否遗漏关键步骤、依赖顺序是否正确	Preview 修改：调整文字 / 执行中发现：需要中断并重新规划
设计规范	是否与现有 UI 风格一致、命名是否符合规范	Preview 修改：补充约束 / 代码完成后：批量重命名

核心原则：在代码生成前修正方向，避免后期重构。

扩展能力的协同作用
​

扩展能力（Skills、MCP、SubAgents、Integration）不是独立的工具，而是与 Plan Mode 形成协同矩阵：

扩展类型	作用机制	典型应用
Skills	注入领域知识和最佳实践到规划上下文	frontend-design 提升 UI 设计质量
MCP	连接外部服务，获取实时数据和最新文档	Context7 获取框架最新 API 文档
SubAgents	处理特定类型的复杂子任务	debug-with-logger 系统化问题诊断
Integration	打通部署和数据库等基础设施	CloudBase/CloudStudio 一键部署

扩展能力在 Plan 生成阶段被注入上下文，AI 会根据任务需求智能选择并在 todolist 中显式引用。

Plan 的复用价值
​

完成的 Plan 保存在 .codebuddy/plans 目录下，具有以下复用价值：

上下文传递：新任务可引用历史 Plan，快速建立项目背景理解
Token 节省：避免重复描述已有的架构和规范
知识沉淀：形成项目级的决策记录和技术方案库

使用建议：

在新对话中引用历史 Plan，帮助 AI 快速了解项目背景
将成功的架构设计和技术选型保存为模板，供后续类似功能复用
Plan 与 Craft 的灵活切换
​

Plan 和 Craft 不是非此即彼的选择，而是可以灵活切换的搭档——先用 Plan 把架构想清楚，再用 Craft 快速处理执行中的细节问题。

场景	推荐模式	原因
宏观架构设计	Plan	需要完整的需求分析和任务拆解
多文件协同修改	Plan	需要统一的技术方案指导
新功能从零实现	Plan	需要明确的实现路径
局部细节调整	Craft	改动范围小，无需完整规划
单函数优化	Craft	上下文明确，直接执行更高效
Bug 快速修复	Craft	问题定位清晰，无需任务拆解

经验法则：架构级改动用 Plan，细节级调整用 Craft。

最后更新: 2026/1/21 15:41

Pager
上一页
模型配置
下一页
Subagents

---

## Subagents

快速导航
背景
优势
核心概念
模式
agentic
manual
作用范围
创建 Subagents
配置说明
Subagents 示例
agentic
manual
Tips
Subagents 创建建议
Description 编写建议
System Prompt 编写建议
Tools 选择建议
Subagents 使用指南
​
背景
​

CodeBuddy IDE 中的 Subagents 是专门的 AI 助手，可以用来处理特定类型的任务。它们通过提供自定义 System Prompt、Tools 和 MCP 服务等特定任务的配置，从而能够更有效地解决问题。本文旨在介绍 CodeBuddy IDE 中 Subagents 的具体使用方法，让大家能快速上手。

优势
​

Subagents 通过专业化分工提升任务处理效果：每个 Subagents 专注于特定领域（如代码审查、调试、数据分析），配合自定义的 System Prompt 和 Tools，比通用 Agent 更精准高效。此外，Subagents 支持灵活的权限控制（仅授予必要 Tools）和跨项目复用（user 级别全局生效），一次配置即可在多个项目中使用并与团队共享，显著提升开发效率和协作体验。

核心概念
​
模式
​

在 CodeBuddy IDE 中存在两种模式，分别是 agentic 和 manual，他们都会在设置页中 Subagents 名称的后面展示出来。

agentic
​

由主 Agent (Craft Agent) 自动判断调用时机，拥有独立上下文窗口，执行时不会污染主会话。需要注意的是这种模式下 Subagents 的调用是不能中途干预的，即当触发了 agentic 的 Subagents 的时候只有两种情况，要么等待 Subagents 完成任务后将结果返回给主 Agent (Craft Agent)，要么直接手动中断当前的对话。

manual
​

manual 模式允许用户手动选择并完全替代主 Agent，适用于需要深度定制交互流程的专业场景。创建完成后，可在 Agent 选择框中选中使用。

作用范围
​

Subagents 中分为 project 和 user 两个级别。其中 project 级别（位于 .codebuddy/agents/ 目录）只在当前工作区生效，user 级别（位于 ~/.codebuddy/agents/ 目录）则适用于全部项目。

创建 Subagents
​

Subagents 在本地存储为 Markdown 文件，也可以在对应路径下创建文件来配置 Subagents，不过在 IDE 中推荐使用设置页 Agent Tab 下的 Create Agent 按钮创建不同模式的 Subagents。点击按钮时选中的是 User Agent Tab 则会创建 user 级别的 Subagents，反之则为 project 级别。

下面两张图分别为创建 agentic 模式和 manual 模式的 Subagents 可以自定义的配置。

agentic 模式配置	manual 模式配置

	

这个表格则展示了不同模式下配置字段的含义，以及是否必要。

配置说明
​
名称	功能	agentic	manual
Name	Subagents 的唯一标识	Required	Required
Description	Subagents 用途的唯一描述	Required	Optional
Auto Run	Subagents 调用工具时是否需要用户的同意	Optional	Optional
System Prompt	Subagents 执行时的系统提示词	Optional	Optional
Model	Subagents 执行时使用的模型	Optional	Optional
Tools Built-In	Subagents 执行时可使用的内置工具列表	Optional	Optional
Tools MCP	Subagents 执行时可使用的 MCP Server	Optional	Optional
Subagents 示例
​
agentic
​
---
name: timezone-introducer
description: Use this agent when you need to present the current time across multiple time zones or regions,such as when scheduling global meetings, displaying world clocks, or providing time context for international audiences. Examples: - User: 'What time is it in different parts of the world?' → Use timezone-introducer to show current times across major cities. - User: 'Show me the time in Tokyo, London, and New York' → Use timezone-introducer to display those specific timezone times. - User: 'I need to schedule a meeting with teams in Sydney and San Francisco' → Use timezone-introducer to show both time zones and find overlapping hours.
model: glm-4.6
tools: WebFetch, WebSearch
agentMode: agentic
enabled: true
enabledAutoRun: true
---
You are a world clock expert who specializes in providing accurate, clear time information across multiple time zones. You will:

1. **Identify Requested Locations**: Parse the user's request to determine which cities, countries, or time zones they want to know about. If locations are vague or unspecified, default to major global business centers (New York, London, Tokyo, Sydney, Dubai).

2. **Calculate Current Times**: Use your knowledge of time zones and daylight saving time rules to provide the exact current time for each location. Always include the timezone abbreviation (e.g., EST, PST, GMT, JST) and indicate whether daylight saving time is in effect.

3. **Format for Clarity**: Present times in a clean, easy-to-read format. Use 24-hour format for international contexts unless the user specifies 12-hour format. Include the day of week and date for clarity, especially when crossing international date lines.

4. **Add Contextual Information**: Include helpful details like UTC offset, whether it's business hours there, and any relevant notes about time differences (e.g., '1 hour ahead of you' or '1 day behind').

5. **Handle Edge Cases**: If a user requests a non-existent timezone or ambiguous location (like 'Central Time' without country context), ask for clarification or provide both possibilities. Be aware of locations that don't observe daylight saving time.

6. **Presentation Style**: Use a consistent format like:
   - Location: Day, Date - Time (Timezone) UTC±X
   - Optional: [Business hours: Yes/No] or [1 hour ahead of your location]

Always verify your timezone calculations and ensure accuracy. If you encounter any timezone data uncertainties, acknowledge them and provide the most likely correct information.

运行效果如下所示

manual
​
---
name: weather-expert
enabled: true
agentMode: manual
tools: WebFetch, WebSearch
enabledAutoRun: true
---
You are a specialized weather information agent that provides accurate, detailed, and user-friendly weather data. Your role is to deliver comprehensive weather information in Chinese, ensuring users understand current conditions, forecasts, and any weather-related implications for their activities.

You will:
- Always respond in Chinese, regardless of the user's language
- Provide current weather conditions when available
- Include temperature, humidity, precipitation, wind conditions, and visibility
- Offer forecasts for requested time periods (today, tomorrow, this week, etc.)
- Mention any weather warnings or alerts relevant to the location
- Suggest appropriate clothing or activity recommendations based on conditions
- Clarify location if not specified or ambiguous
- Use metric units (Celsius, km/h, etc.) by default
- Format information clearly with bullet points or numbered lists when presenting multiple data points

When providing weather information:
1. Start with a brief summary of current/requested conditions
2. Present detailed data in an organized manner
3. Include practical implications (e.g., "适合户外活动" or "记得带伞")
4. End with helpful suggestions or reminders

If weather data is unavailable for a requested location or time period, clearly explain the limitation and offer alternatives when possible. Always maintain a helpful, informative tone while being concise and actionable.

执行效果如下图所示：

Tips
​
Subagents 创建建议
​

创建具有单一、明确职责的 Subagents，而不是让一个 Subagents 完成所有任务。这可以提高性能并使 Subagents 更具可预测性。

Description 编写建议
​

编写 Description 时建议从三个方面进行考虑，分别是指定专长、定义范围和给出明确的触发条件。以下是一个简单例子

❌ bad case
"A helpful assistant for code."

✅ good case
"Expert code review specialist. Proactively reviews code for quality, security, and maintainability. Use immediately after writing or modifying code."
System Prompt 编写建议
​

编写 System Prompt 时建议明确定义角色和职责、提供具体操作流程、设定约束和边界。要知道提供的约束越多 Subagents 的效果也会越好。

Tools 选择建议
​

选择 Tools 时建议仅添加 Subagents 所需的工具。这提高了安全性并帮助 Subagents 专注于相关任务。

最后更新: 2026/2/8 11:57

Pager
上一页
Plan 模式
下一页
Skills

---

## Skills

快速导航
Skills 能提供什么
Skill 的结构
SKILL.md (必需)
打包资源 (可选)
1. Scripts (scripts/)
2. References (references/)
3. Assets (assets/)
渐进式披露设计原则
创建 Skill 的流程
最佳实践
Skill 管理
Skills
​

Skills 是模块化的、自包含的能力包，通过提供专门的知识、工作流和工具来扩展 AI Agent 的能力。它们就像是针对特定领域或任务的“入职指南”，将通用的 AI Agent 转变为具备专业程序性知识的专家。

Skills 能提供什么
​
专业工作流：针对特定领域的自动多步骤程序。
工具集成：处理特定文件格式或 API 的指令。
领域专业知识：公司特定的知识、架构和业务逻辑。
打包资源：用于复杂和重复任务的脚本、参考资料和资产。
Skill 的结构
​

每个 Skill 由一个必需的 SKILL.md 文件和可选的打包资源组成。Skill 应建立在工作区的 .codebuddy/skills/ 目录下。

skill-name/
├── SKILL.md (必需)
│   ├── YAML frontmatter 元数据 (必需)
│   │   ├── name: (必需)
│   │   └── description: (必需)
│   └── Markdown 指令 (必需)
└── Bundled Resources (可选)
    ├── scripts/          - 可执行代码 (Python/Bash 等)
    ├── references/       - 旨在根据需要加载到上下文中的文档
    └── assets/           - 用在输出中的文件 (模板、图标、字体等)
SKILL.md (必需)
​

这是 Skill 的核心定义文件。

元数据 (YAML Frontmatter):name 和 description 决定了 AI 何时会使用这个 Skill。描述需具体说明 Skill 的功能和使用场景。

示例：

markdown
---
name: pdf-editor
description: This skill should be used when users ask to modify, rotate, or extract text from PDF files.
allowed-tools: # 可选，指定允许使用的工具
disable: false # 可选，是否禁用
---

# PDF Editor

To rotate a PDF...
打包资源 (可选)
​
1. Scripts (scripts/)
​

用于需要确定性可靠性或被重复重写的任务的可执行代码。

用途：当代码被重复重写或需要高可靠性时。
示例：scripts/rotate_pdf.py 用于 PDF 旋转。
2. References (references/)
​

旨在根据需要加载到上下文中以辅助 AI 思考的文档和参考资料。

用途：数据库架构、API 文档、领域知识、公司政策等。
优势：保持 SKILL.md 精简，仅在 AI 确定需要时才加载。
3. Assets (assets/)
​

不打算加载到上下文中，而是用于 AI 生成的输出中的文件。

用途：品牌资产、PPT 模板、HTML/React 样板代码等。
渐进式披露设计原则
​

Skills 使用三级加载系统来高效管理上下文：

元数据 (Metadata)：始终在上下文中 (~100 词)。
Skill 主体 (SKILL.md body)：当 Skill 被触发时加载 (<5k 词)。
打包资源 (Bundled resources)：按需由 AI 加载 (无限制)。
创建 Skill 的流程
​
理解需求：明确 Skill 的使用场景和触发条件。
规划资源：分析是否需要脚本、参考文档或资产模板。
创建目录：在 .codebuddy/skills/ 下创建新的 Skill 目录。
编写 SKILL.md：
填写 YAML 元数据。
编写 Markdown 指令。使用指令性语言（如 "To accomplish X, do Y"）。
引用打包的资源。
最佳实践
​
具体明确的描述：在 description 中清楚地说明 Skill 何时应该被使用。
指令性语言：在 SKILL.md 中使用动词开头的指令，而不是第二人称。
按需加载：将长篇文档放入 references/，避免 SKILL.md 过于臃肿。
避免重复：信息应存在于 SKILL.md 或引用文件中，不要两处都有。
Skill 管理
​

CodeBuddy 在设置页面中提供了可视化的界面来帮助你管理 Skills。

在设置管理页面中，你可以：

集中管理：查看和管理当前项目（Project Skills）和用户级别（User Skills）的所有 Skills。
导入 Skill：点击右上角的“导入 Skill”按钮，可以导入你从网络上获取的 Skills。

最后更新: 2026/1/21 15:41

Pager
上一页
Subagents
下一页
Hooks

---

## Hooks

快速导航
📑 目录
概述
功能特性
支持的 Hook 事件
1. SessionStart - 会话启动
2. SessionEnd - 会话结束
3. PreToolUse - 工具执行前
4. PostToolUse - 工具执行后
5. UserPromptSubmit - 用户输入提交
6. Stop - Agent 停止响应
7. PreCompact - 上下文压缩前
Hook 脚本规范
输入格式
输出格式
退出码规范
环境变量
配置说明
配置文件位置
配置文件结构
配置字段说明
matcher (匹配器)
command (命令路径)
timeout (超时时间)
完整示例
示例 1: 命令安全验证
示例 2: 智能修改命令参数
示例 3: 文件修改前自动备份
示例 4: 会话启动时注入项目上下文
示例 5: 上下文压缩前保存重要信息
实战指南
快速开始 - 5 分钟配置第一个 Hook
调试技巧进阶
常见 Hook 模式
项目模板推荐
最佳实践
1. 脚本开发
2. 安全性
3. 性能优化
4. 调试技巧
5. 配置管理
性能优化建议
1. 减少 Hook 执行时间
2. 优化 Matcher 配置
3. 并行执行的注意事项
安全最佳实践
1. 输入验证
2. 命令注入防护
3. 路径遍历防护
4. 权限最小化
高级用法
条件执行
多规则组合
外部服务集成
常见问题
Q1: Hook 没有被执行？
Q2: Hook 执行超时？
Q3: 如何调试 Hook 脚本？
Q4: 多个 Hook 的执行顺序？
Q5: Hook 修改的参数不生效？
Q6: SessionStart Hook 每次请求都触发？
附录
A. 完整的 HookInput 接口定义
B. 完整的 HookOutput 接口定义
C. 环境变量列表
D. 退出码详细说明
E. 常用工具名称列表
总结
Hook 功能使用文档
​
📑 目录
​
概述
功能特性
支持的 Hook 事件
1. SessionStart - 会话启动
2. SessionEnd - 会话结束
3. PreToolUse - 工具执行前
4. PostToolUse - 工具执行后
5. UserPromptSubmit - 用户输入提交
6. Stop - Agent 停止响应
7. PreCompact - 上下文压缩前
Hook 脚本规范
配置说明
完整示例
实战指南
最佳实践
性能优化建议
安全最佳实践
高级用法
常见问题
附录
概述
​

Hook 功能允许您在 AI Agent 执行的关键节点插入自定义脚本，实现对 Agent 行为的精细控制。Hook 机制完全兼容 Claude Code Hooks 规范，提供了一种强大且灵活的扩展方式。

功能特性
​
✅ 多事件支持: 支持 7 种关键事件（SessionStart、SessionEnd、PreToolUse、PostToolUse、UserPromptSubmit、Stop、PreCompact）
✅ 工具拦截: 在工具执行前后进行验证、修改或阻止
✅ 上下文注入: 在会话不同阶段动态注入额外上下文
✅ 并行执行: 多个 Hook 自动并行执行，提升性能
✅ 自动去重: 相同命令自动去重，避免重复执行
✅ 灵活配置: 支持正则匹配、超时控制、项目级/用户级配置
✅ 会话跟踪: 智能识别会话变化，避免重复触发 SessionStart
✅ 安全可靠: 完善的错误处理和超时机制
支持的 Hook 事件
​
1. SessionStart - 会话启动
​

触发时机: 会话开始时（每个新会话只触发一次）

触发逻辑:

系统通过对比 conversationId 判断是否为新会话
同一会话中多次请求不会重复触发
切换到新会话或清空会话后会重新触发

用途:

初始化项目环境
注入项目特定上下文
设置会话级别的配置
加载项目规范和文档

Matcher 匹配字段: source

startup - 首次启动（目前仅支持此值）

输入数据 (stdin JSON):

json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.txt",
  "cwd": "/project/path",
  "hook_event_name": "SessionStart",
  "source": "startup"
}

输出数据 (stdout JSON):

json
{
  "continue": true,
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "项目使用 TypeScript + React，请优先使用函数式组件"
  }
}

示例配置:

json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/session_start.py",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
2. SessionEnd - 会话结束
​

触发时机: 会话终止时

用途:

清理临时资源
保存会话状态
生成会话报告

Matcher 匹配字段: reason

other - 会话结束（目前仅支持此值，包括切换会话、删除会话、清空会话等场景）

输入数据:

json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.txt",
  "cwd": "/project/path",
  "hook_event_name": "SessionEnd",
  "reason": "other"
}

输出数据:

json
{
  "continue": true,
  "systemMessage": "会话已清理，临时文件已删除"
}
3. PreToolUse - 工具执行前
​

触发时机: 任何工具执行前

用途:

验证工具参数
修改工具输入
阻止危险操作
权限检查
记录审计日志

Matcher 匹配字段: tool_name

示例: Bash, Write, Read
支持正则: Write|Edit
匹配所有: * 或空字符串

输入数据:

json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.txt",
  "cwd": "/project/path",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "npm install",
    "requires_approval": false
  }
}

输出数据 - 允许执行:

json
{
  "continue": true,
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow"
  }
}

输出数据 - 修改参数:

json
{
  "continue": true,
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "已添加 --legacy-peer-deps 参数",
    "modifiedInput": {
      "command": "npm install --legacy-peer-deps",
      "requires_approval": false
    }
  }
}

输出数据 - 阻止执行:

json
{
  "continue": false,
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "检测到危险命令: rm -rf /"
  }
}

输出数据 - 请求用户确认:

json
{
  "continue": true,
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "检测到 git push --force，是否继续？"
  }
}
4. PostToolUse - 工具执行后
​

触发时机: 工具执行完成后

用途:

记录工具执行日志
后处理工具输出
触发后续操作
发送通知

Matcher 匹配字段: tool_name

输入数据:

json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.txt",
  "cwd": "/project/path",
  "hook_event_name": "PostToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "npm test"
  },
  "tool_response": {
    "exitCode": 0,
    "stdout": "All tests passed",
    "stderr": ""
  }
}

输出数据:

json
{
  "continue": true,
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "测试已通过，可以继续开发"
  }
}
5. UserPromptSubmit - 用户输入提交
​

触发时机: 用户提交消息时

用途:

预处理用户输入
添加上下文信息
检测特定关键词
输入验证

Matcher: 不使用（所有提交都触发）

输入数据:

json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.txt",
  "cwd": "/project/path",
  "hook_event_name": "UserPromptSubmit",
  "prompt": "帮我实现一个登录功能"
}

输出数据:

json
{
  "continue": true,
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "提示：项目已集成 JWT 认证库，建议使用"
  }
}

阻止输入:

json
{
  "continue": false,
  "stopReason": "输入包含敏感信息，已阻止"
}
6. Stop - Agent 停止响应
​

触发时机: Agent 完成响应时

用途:

提供反馈给 Agent
记录执行状态
触发后续任务

Matcher: 不使用

输入数据:

json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.txt",
  "cwd": "/project/path",
  "hook_event_name": "Stop",
  "stop_hook_active": false
}

输出数据 - 提供反馈 (exit code 2):

json
{
  "continue": false,
  "stopReason": "请验证代码是否通过了单元测试"
}
7. PreCompact - 上下文压缩前
​

触发时机: 上下文即将被压缩时

用途:

保存重要信息
提供压缩指导
备份完整上下文

Matcher 匹配字段: trigger

manual - 用户手动触发 /summarize
auto - 自动压缩

输入数据:

json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.txt",
  "cwd": "/project/path",
  "hook_event_name": "PreCompact",
  "trigger": "auto",
  "custom_instructions": "保留所有 API 设计相关的讨论"
}

输出数据 (exit code 0):

json
{
  "continue": true,
  "hookSpecificOutput": {
    "hookEventName": "PreCompact",
    "additionalContext": "重要：保留数据库表结构设计"
  }
}

说明: Exit code 0 时，stdout 的内容会被添加为额外的压缩指导

Hook 脚本规范
​
输入格式
​

Hook 脚本通过 stdin 接收 JSON 格式的输入数据。

通用字段:

json
{
  "session_id": "会话 ID",
  "transcript_path": "对话记录文件路径",
  "cwd": "当前工作目录",
  "hook_event_name": "事件名称"
}

事件特定字段:

SessionStart: source
SessionEnd: reason
PreToolUse/PostToolUse: tool_name, tool_input, tool_response
UserPromptSubmit: prompt
PreCompact: trigger, custom_instructions
Stop: stop_hook_active
输出格式
​

Hook 脚本通过 stdout 返回 JSON 格式的输出。

基本结构:

json
{
  "continue": true,
  "suppressOutput": false,
  "systemMessage": "可选的系统消息",
  "stopReason": "阻止原因（当 continue=false 时）",
  "hookSpecificOutput": {
    "hookEventName": "事件名称",
    "permissionDecision": "allow|deny|ask",
    "permissionDecisionReason": "决策原因",
    "modifiedInput": {},
    "additionalContext": "额外上下文"
  }
}

字段说明:

continue: 是否允许操作继续（false 表示阻止）
suppressOutput: 是否隐藏 stdout 输出
systemMessage: 显示给用户的系统消息
stopReason: 阻止原因
hookSpecificOutput: 事件特定的输出数据
退出码规范
​
退出码	含义	行为
0	成功执行	允许操作继续，stdout 可能被处理
1	非阻塞错误	显示 stderr 作为警告，允许继续
2	阻塞错误	阻止操作，stderr 传递给 Agent/模型
其他	非阻塞错误	同退出码 1

特殊规则:

PreToolUse: 退出码 2 会阻止工具执行
Stop: 退出码 2 表示提供反馈，stderr 会注入到下一条消息
PreCompact: 退出码 0 时，stdout 会作为额外的压缩指导
环境变量
​

Hook 脚本执行时可访问以下环境变量：

CLAUDE_PROJECT_DIR: 项目根目录（兼容 Claude Code）
CODEBUDDY_PROJECT_DIR: 项目根目录（CodeBuddy 特定）
配置说明
​
配置文件位置
​

优先级（高到低）：

项目级: <workspace>/.codebuddy/settings.json
用户级: ~/.codebuddy/settings.json

项目级配置会覆盖用户级配置。

配置文件结构
​
json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "/absolute/path/to/script.py",
            "timeout": 10
          }
        ]
      },
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/backup_script.sh",
            "timeout": 20
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/init.py",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
配置字段说明
​
matcher (匹配器)
​

正则表达式，用于匹配特定条件。

语法:

空字符串 "" 或 "*": 匹配所有
单个值: "Bash"
多个值: "Write|Edit"
正则表达式: "Read.*|Grep.*"

不同事件的匹配目标:

PreToolUse/PostToolUse: 匹配 tool_name（如 Bash, Write, Read, Edit 等）
SessionStart: 匹配 source
SessionEnd: 匹配 reason
PreCompact: 匹配 trigger
UserPromptSubmit/Stop: 不使用 matcher
command (命令路径)
​

Hook 脚本的路径。

要求:

✅ 推荐使用绝对路径
✅ 支持环境变量: "$CODEBUDDY_PROJECT_DIR/.codebuddy/hooks/script.py"
✅ 可包含解释器: "python3 /path/to/script.py"
⚠️ 需要确保脚本有执行权限
timeout (超时时间)
​

Hook 执行的超时时间，单位：秒。

默认值: 60 秒
推荐设置: 根据脚本复杂度调整
简单验证: 5-10 秒
文件操作: 15-30 秒
网络请求: 30-60 秒
完整示例
​
示例 1: 命令安全验证
​

场景: 阻止危险的 rm -rf 命令

Hook 脚本 (validate_command.py):

python
#!/usr/bin/env python3
import json
import sys

DANGEROUS_COMMANDS = ['rm -rf /', 'dd if=/dev/zero', 'mkfs']

def main():
    input_data = json.loads(sys.stdin.read())

    if input_data.get('tool_name') != 'Bash':
        print(json.dumps({"continue": True}))
        return 0

    command = input_data.get('tool_input', {}).get('command', '')

    for dangerous in DANGEROUS_COMMANDS:
        if dangerous in command:
            output = {
                "continue": False,
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"检测到危险命令: {dangerous}"
                }
            }
            print(json.dumps(output, ensure_ascii=False))
            return 0

    print(json.dumps({"continue": True}))
    return 0

if __name__ == "__main__":
    sys.exit(main())

配置:

json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/validate_command.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
示例 2: 智能修改命令参数
​

场景: 自动为 npm install 添加 --legacy-peer-deps 参数

Hook 脚本 (modify_npm.py):

python
#!/usr/bin/env python3
import json
import sys
import re

def main():
    input_data = json.loads(sys.stdin.read())

    if input_data.get('tool_name') != 'Bash':
        print(json.dumps({"continue": True}))
        return 0

    tool_input = input_data.get('tool_input', {})
    command = tool_input.get('command', '')

    # 检查是否是 npm install
    if re.match(r'^npm\s+(i|install)\b', command.strip()):
        # 如果没有 --legacy-peer-deps，添加它
        if '--legacy-peer-deps' not in command:
            modified_command = command.strip() + ' --legacy-peer-deps'

            output = {
                "continue": True,
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "permissionDecisionReason": "已自动添加 --legacy-peer-deps 参数",
                    "modifiedInput": {
                        "command": modified_command,
                        "requires_approval": tool_input.get('requires_approval', False)
                    }
                }
            }
            print(json.dumps(output, ensure_ascii=False))
            return 0

    print(json.dumps({"continue": True}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
示例 3: 文件修改前自动备份
​

场景: 在修改文件前自动创建备份

Hook 脚本 (backup_files.py):

python
#!/usr/bin/env python3
import json
import sys
import os
import shutil
from datetime import datetime

def main():
    input_data = json.loads(sys.stdin.read())
    tool_name = input_data.get('tool_name', '')

    # 只处理文件写入工具
    if tool_name not in ['Write', 'Edit']:
        print(json.dumps({"continue": True}))
        return 0

    tool_input = input_data.get('tool_input', {})
    file_path = tool_input.get('filePath')

    if not file_path or not os.path.exists(file_path):
        print(json.dumps({"continue": True}))
        return 0

    # 创建备份目录
    project_dir = os.environ.get('CODEBUDDY_PROJECT_DIR', '')
    backup_dir = os.path.join(project_dir, '.codebuddy', 'backups')
    os.makedirs(backup_dir, exist_ok=True)

    # 生成备份文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"{os.path.basename(file_path)}.{timestamp}.bak"
    backup_path = os.path.join(backup_dir, backup_name)

    # 创建备份
    shutil.copy2(file_path, backup_path)

    output = {
        "continue": True,
        "systemMessage": f"已备份至: {backup_path}"
    }
    print(json.dumps(output, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())

配置:

json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/backup_files.py",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
示例 4: 会话启动时注入项目上下文
​

场景: 在会话开始时自动注入项目配置信息

Hook 脚本 (session_start.py):

python
#!/usr/bin/env python3
import json
import sys
import os

def main():
    input_data = json.loads(sys.stdin.read())
    project_dir = os.environ.get('CODEBUDDY_PROJECT_DIR', '')

    # 读取项目配置
    config_file = os.path.join(project_dir, '.codebuddy', 'project.json')
    project_info = ""

    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
            project_info = f"""
项目名称: {config.get('name', 'Unknown')}
技术栈: {', '.join(config.get('tech_stack', []))}
编码规范: {config.get('coding_standard', 'Standard')}
"""

    output = {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": f"""
会话已启动!
项目目录: {project_dir}
启动源: {input_data.get('source', 'unknown')}
{project_info}
"""
        }
    }

    print(json.dumps(output, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
示例 5: 上下文压缩前保存重要信息
​

场景: 在自动压缩前保存完整对话历史

Hook 脚本 (save_context.py):

python
#!/usr/bin/env python3
import json
import sys
import os
import shutil
from datetime import datetime

def main():
    input_data = json.loads(sys.stdin.read())

    # 只处理自动压缩
    if input_data.get('trigger') != 'auto':
        print(json.dumps({"continue": True}))
        return 0

    project_dir = os.environ.get('CODEBUDDY_PROJECT_DIR', '')
    transcript_path = input_data.get('transcript_path', '')

    if not transcript_path or not os.path.exists(transcript_path):
        print(json.dumps({"continue": True}))
        return 0

    # 创建保存目录
    save_dir = os.path.join(project_dir, '.codebuddy', 'context_history')
    os.makedirs(save_dir, exist_ok=True)

    # 保存对话历史
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    save_path = os.path.join(save_dir, f'transcript_{timestamp}.txt')
    shutil.copy2(transcript_path, save_path)

    output = {
        "continue": True,
        "systemMessage": f"上下文已保存至: {save_path}"
    }
    print(json.dumps(output, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())

配置:

json
{
  "hooks": {
    "PreCompact": [
      {
        "matcher": "auto",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/save_context.py",
            "timeout": 20
          }
        ]
      }
    ]
  }
}
实战指南
​
快速开始 - 5 分钟配置第一个 Hook
​

第一步：创建配置文件

bash
mkdir -p ~/.codebuddy
cat > ~/.codebuddy/settings.json << 'EOF'
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "/usr/bin/env python3 -c \"import json,sys; print(json.dumps({'continue': True, 'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': 'Hook 配置成功！'}}))\"",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
EOF

第二步：重启 Agent

启动新会话，如果看到 "Hook 配置成功！" 说明配置生效。

第三步：创建你的第一个真实 Hook

bash
# 创建 Hook 脚本目录
mkdir -p ~/.codebuddy/hooks

# 创建测试脚本
cat > ~/.codebuddy/hooks/my_first_hook.py << 'EOF'
#!/usr/bin/env python3
import json
import sys

def main():
    input_data = json.loads(sys.stdin.read())

    output = {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": f"欢迎使用 Agent-Craft！当前项目: {input_data.get('cwd', 'unknown')}"
        }
    }

    print(json.dumps(output, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
EOF

# 添加执行权限
chmod +x ~/.codebuddy/hooks/my_first_hook.py

第四步：更新配置文件

json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/YOUR_USERNAME/.codebuddy/hooks/my_first_hook.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
调试技巧进阶
​

技巧1: 使用日志文件调试

python
import sys

def debug_log(message):
    """写入调试日志而不影响 stdout"""
    with open('/tmp/hook_debug.log', 'a') as f:
        f.write(f"{message}\n")

# 在 Hook 脚本中使用
debug_log(f"Received input: {json.dumps(input_data)}")

技巧2: 验证 JSON 输出格式

bash
# 测试脚本输出的 JSON 是否有效
echo '{"hook_event_name":"SessionStart"}' | python3 your_hook.py | jq .

技巧3: 监控 Hook 执行

bash
# 实时查看 Hook 日志
tail -f ~/.codebuddy/logs/agent-craft.log | grep -i hook

技巧4: 使用环境变量传递信息

python
import os

# 在 Hook 中获取项目目录
project_dir = os.environ.get('CODEBUDDY_PROJECT_DIR', '')
claude_dir = os.environ.get('CLAUDE_PROJECT_DIR', '')  # 兼容 Claude Code
常见 Hook 模式
​

模式1: 白名单验证

python
ALLOWED_COMMANDS = [
    'npm install',
    'npm test',
    'git status',
    'git diff'
]

def is_allowed(command):
    return any(command.startswith(allowed) for allowed in ALLOWED_COMMANDS)

模式2: 参数增强

python
def enhance_command(command):
    """自动添加常用参数"""
    enhancements = {
        'npm install': ' --legacy-peer-deps',
        'git push': ' --dry-run',  # 安全模式
    }

    for prefix, suffix in enhancements.items():
        if command.startswith(prefix) and suffix not in command:
            return command + suffix

    return command

模式3: 条件路由

python
def should_block(input_data):
    """根据多个条件判断是否阻止"""
    tool_name = input_data.get('tool_name')
    tool_input = input_data.get('tool_input', {})

    # 规则1: 阻止删除重要文件
    if tool_name == 'Write':
        file_path = tool_input.get('file_path', '')
        if any(important in file_path for important in ['.git', 'package.json']):
            return True, "不能删除重要文件"

    # 规则2: 阻止危险命令
    if tool_name == 'Bash':
        command = tool_input.get('command', '')
        if 'rm -rf /' in command or 'dd if=' in command:
            return True, "检测到危险命令"

    return False, None
项目模板推荐
​

Node.js 项目 Hook 配置

json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "node ~/.codebuddy/hooks/nodejs-init.js",
            "timeout": 15
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.codebuddy/hooks/npm-safety-check.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}

Python 项目 Hook 配置

json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.codebuddy/hooks/python-env-check.py",
            "timeout": 10
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.codebuddy/hooks/python-lint.py",
            "timeout": 20
          }
        ]
      }
    ]
  }
}
最佳实践
​
1. 脚本开发
​
✅ 错误处理: 脚本配置异常处理，减少阻塞主流程
✅ 快速执行: Hook 应快速完成，减少耗时操作
✅ 幂等性: Hook 可能被多次调用，多次执行结果一致
✅ 日志记录: 使用 sys.stderr 输出调试信息，不要污染 stdout
2. 安全性
​
⚠️ 输入验证: 始终验证输入数据的合法性
⚠️ 白名单优于黑名单: 使用白名单机制进行权限控制
⚠️ 避免代码注入: 不要直接执行用户输入
⚠️ 最小权限: Hook 脚本应以最小必要权限运行
3. 性能优化
​
⏱ 设置合理超时: 根据脚本复杂度设置 timeout
⏱ 并行设计: 避免 Hook 之间的依赖，充分利用并行执行
⏱ 缓存结果: 对于重复计算，考虑缓存结果
4. 调试技巧
​

手动测试 Hook 脚本:

bash
echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"npm install"}}' | \
  python3 /path/to/your_hook.py

调试输出:

python
# 在 Hook 脚本中输出调试信息
import sys

sys.stderr.write(f"[DEBUG] Processing command: {command}\n")
sys.stderr.flush()
5. 配置管理
​
📁 项目特定 Hook: 放在 <workspace>/.codebuddy/ 下，随项目版本控制
📁 个人 Hook: 放在 ~/.codebuddy/ 下，跨项目复用
性能优化建议
​
1. 减少 Hook 执行时间
​
✅ 使用快速语言: Shell 脚本通常比 Python 启动更快
✅ 避免重复工作: 缓存计算结果
✅ 异步处理: 非关键操作使用后台任务
✅ 提前退出: 尽早判断是否需要处理

示例:

python
# 不好的做法：每次都加载大文件
def main():
    with open('huge_config.json', 'r') as f:
        config = json.load(f)  # 每次都读取
    # ... 处理逻辑

# 好的做法：缓存配置
CONFIG_CACHE = None

def get_config():
    global CONFIG_CACHE
    if CONFIG_CACHE is None:
        with open('huge_config.json', 'r') as f:
            CONFIG_CACHE = json.load(f)
    return CONFIG_CACHE
2. 优化 Matcher 配置
​
json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/fast_check.sh",
            "timeout": 3
          }
        ]
      },
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/general_check.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
3. 并行执行的注意事项
​
多个 Hook 会并行执行，不要依赖执行顺序
避免 Hook 之间的文件写入冲突
使用文件锁或原子操作处理共享资源
python
import fcntl

def safe_append_log(message):
    """线程安全的日志写入"""
    with open('/tmp/hook.log', 'a') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.write(message + '\n')
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
安全最佳实践
​
1. 输入验证
​

永远不要信任输入数据:

python
def validate_input(input_data):
    """验证输入数据的完整性"""
    required_fields = ['hook_event_name', 'session_id']

    for field in required_fields:
        if field not in input_data:
            raise ValueError(f"Missing required field: {field}")

    # 验证字段类型
    if not isinstance(input_data.get('tool_input'), dict):
        raise ValueError("tool_input must be a dictionary")

    return True
2. 命令注入防护
​

不要直接执行用户输入:

python
# ❌ 危险：直接执行
os.system(f"echo {user_input}")

# ✅ 安全：使用参数化
import subprocess
subprocess.run(['echo', user_input], check=True)
3. 路径遍历防护
​
python
import os

def safe_file_access(file_path, project_dir):
    """确保文件路径在项目目录内"""
    abs_path = os.path.abspath(file_path)
    abs_project = os.path.abspath(project_dir)

    if not abs_path.startswith(abs_project):
        raise ValueError("Path traversal detected")

    return abs_path
4. 权限最小化
​
python
# Hook 脚本应该以最小权限运行
# 避免使用 sudo 或 root 权限

# ✅ 检查权限
if os.geteuid() == 0:
    print("Warning: Running as root is not recommended", file=sys.stderr)
高级用法
​
条件执行
​

在 Hook 脚本中根据条件决定是否处理：

python
def main():
    input_data = json.loads(sys.stdin.read())

    # 仅在特定条件下处理
    if not should_process(input_data):
        print(json.dumps({"continue": True}))
        return 0

    # 执行处理逻辑
    ...
多规则组合
​

在一个 Hook 脚本中实现多个规则：

python
def main():
    input_data = json.loads(sys.stdin.read())

    # 应用多个规则
    for rule in RULES:
        if rule.matches(input_data):
            return rule.apply(input_data)

    # 默认行为
    print(json.dumps({"continue": True}))
    return 0
外部服务集成
​

Hook 可以调用外部 API 或服务：

python
import requests

def check_with_external_service(command):
    response = requests.post('https://api.example.com/validate',
                            json={'command': command},
                            timeout=5)
    return response.json()
常见问题
​
Q1: Hook 没有被执行？
​

检查清单:

✅ 配置文件路径正确 (settings.json 在 .codebuddy 目录下)
✅ hooks 字段配置正确，JSON 格式有效
✅ matcher 正则表达式能匹配目标
✅ Hook 脚本有执行权限 (chmod +x script.py)
✅ 脚本路径正确（推荐使用绝对路径）
✅ 脚本第一行有正确的 shebang (#!/usr/bin/env python3)
Q2: Hook 执行超时？
​

解决方法:

增加 timeout 配置值
优化 Hook 脚本性能
检查是否有死循环或阻塞操作
Q3: 如何调试 Hook 脚本？
​

调试步骤:

使用 echo 手动传入测试数据
在脚本中使用 sys.stderr 输出调试信息
验证 JSON 格式是否正确
Q4: 多个 Hook 的执行顺序？
​

答案:

Hook 并行执行，不保证执行顺序
如需顺序执行，将逻辑合并到一个 Hook 脚本中
相同命令会自动去重
Q5: Hook 修改的参数不生效？
​

检查要点:

确保返回了 modifiedInput 字段
确保 permissionDecision 为 allow
检查字段名称是否与工具参数匹配
验证 JSON 格式正确
确保 continue 为 true
Q6: SessionStart Hook 每次请求都触发？
​

原因: SessionStart 应该只在新会话触发一次

解决方法:

系统通过 conversationId 跟踪会话
同一会话中多次请求不会重复触发
如果仍有问题，查看日志中的会话 ID 是否变化
附录
​
A. 完整的 HookInput 接口定义
​
typescript
interface HookInput {
  // 通用字段
  session_id?: string;              // 会话 ID
  transcript_path?: string;          // 对话记录路径
  cwd?: string;                      // 当前工作目录
  hook_event_name: string;          // Hook 事件名称

  // SessionStart 专用（目前仅支持 'startup'）
  source?: 'startup';

  // UserPromptSubmit 专用
  prompt?: string;                   // 用户输入内容

  // PreToolUse/PostToolUse 专用
  tool_name?: string;                // 工具名称
  tool_input?: Record<string, any>;  // 工具输入参数
  tool_response?: any;               // 工具响应（仅 PostToolUse）

  // Stop 专用
  stop_hook_active?: boolean;        // 是否已激活 Stop Hook

  // PreCompact 专用
  trigger?: 'manual' | 'auto';       // 触发方式
  custom_instructions?: string;      // 自定义压缩指令
}
B. 完整的 HookOutput 接口定义
​
typescript
interface HookOutput {
  // 基本控制
  continue?: boolean;                // 是否继续执行（默认 true）
  stopReason?: string;               // 停止原因
  suppressOutput?: boolean;          // 是否隐藏输出
  systemMessage?: string;            // 系统消息

  // Hook 特定输出
  hookSpecificOutput?: {
    hookEventName: string;           // Hook 事件名称

    // PreToolUse 专用
    permissionDecision?: 'allow' | 'deny' | 'ask';
    permissionDecisionReason?: string;
    modifiedInput?: Record<string, any>;

    // SessionStart/UserPromptSubmit/PostToolUse 专用
    additionalContext?: string;      // 额外上下文
  };
}
C. 环境变量列表
​
环境变量	说明	示例值
CODEBUDDY_PROJECT_DIR	项目根目录	/path/to/project
CLAUDE_PROJECT_DIR	项目根目录（Claude Code 兼容）	/path/to/project
D. 退出码详细说明
​
退出码	含义	stdout	stderr	行为
0	成功	作为结果处理	忽略	继续执行，可能注入上下文
1	警告	忽略	作为警告显示	继续执行
2	阻止/反馈	忽略	传递给 Agent	PreToolUse: 阻止执行<br>Stop: 提供反馈
其他	错误	忽略	作为警告显示	继续执行
E. 常用工具名称列表
​

⚠️ 重要说明：配置文件中的 matcher 支持双向别名匹配（写 CLI 风格或 IDE 风格都可以匹配）。但 Hook 脚本接收到的 tool_name 取决于运行环境：

IDE (Craft Agent): 使用 IDE 风格 (如 execute_command, write_to_file)
CLI: 使用 CLI 风格 (如 Bash, Write)

工具名称映射表:

CLI 风格	IDE 风格	功能说明
Read	read_file	读取文件
Write	write_to_file	写入文件
Edit	replace_in_file	编辑/替换文件内容
Glob	list_dir	文件模式匹配/搜索文件
Grep	search_content	内容搜索
Bash	execute_command	执行 Shell 命令
Task	task	子代理任务
WebSearch	web_search	网络搜索
WebFetch	web_fetch	获取网页内容
总结
​

Hook 功能提供了强大的扩展能力，允许您在 AI Agent 的关键节点插入自定义逻辑。通过合理使用 Hook，您可以：

🛡️ 增强安全性: 验证和阻止危险操作
🔧 自动化流程: 智能修改参数、自动备份文件
📊 监控审计: 记录工具执行日志
🎯 定制行为: 注入项目特定上下文

开始使用 Hook 功能，让您的 AI Agent 更智能、更安全、更符合项目需求！

Happy Hooking! 🎣

最后更新: 2026/4/15 17:48

Pager
上一页
Skills
下一页
定价详情

---

