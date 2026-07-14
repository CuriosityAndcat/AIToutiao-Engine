# CodeBuddy 支持

> 来源: https://www.codebuddy.cn/docs/ide/  
> 抓取日期: 2026-07-13

---

## 故障排除

快速导航
登录问题
Q: 卡在登录界面无法完成登录
日志问题
Q: 如何查看本地日志？
账户相关问题
Q: 购买旗舰版后登录提示积分余额不足
远程开发（ SSH 常见问题）
Q: 无法连接
网络检查
Q: 代理检测显示“失败/警告”（如 connect ECONNREFUSED）怎么办？
Q: Hosts 解析显示“警告/异常”怎么排查？
Q: 服务连通性显示“失败”（HTTP 失败）怎么办？
Q: TCP 连接延迟显示“失败/警告”怎么处理？
Q: 丢包率显示异常（高丢包或 100% 丢包）怎么办？
Q: 常见错误码和网络检查项如何对应？
Figma 使用
Q: Figma 无法添加到对话中？
插件相关
Q: 安装问题
Q: Python 没有语法高亮, 无法跳转定义
Q: C/C++ 无法跳转/高亮
终端
Q: 无法打开终端
Q: 终端无法复用
MCP
Q: MCP使用
Q: MCP连接不上
语言
Q: 如何约束Agent对话语言
文件与工作空间
Q：更新时提示"检测到应用安装目录下存在用户项目目录"
Q：Claw工作空间的历史会话找不到了怎么办？
常见问题
​

使用CodeBuddy的过程中遇问题可以在本页查询解决方案。如果没有成功解决，建议向 codebuddy@tencent.com 发送邮件咨询。

登录问题
​
Q: 卡在登录界面无法完成登录
​
选择在浏览器中打开尝试再次拉起登录验证窗口
选择复制链接后自行打开浏览器，ctrl + v 或右键粘贴链接到浏览器，完成登录验证

日志问题
​
Q: 如何查看本地日志？
​

MAC：打开 CodeBuddy IDE，点击顶部帮助 ---> 打开日志文件夹，找到对应的日志 （.zip） 包

Windows：

打开 CodeBuddy IDE，点击顶部帮助 ---> 打开日志文件夹，找到对应的日志 （.zip） 包

手动查询路径：C:\Users\<你的用户名>\AppData\Roaming\CodeBuddy\logs（将<你的用户名>替换为 Windows 系统用户名）

账户相关问题
​
Q: 购买旗舰版后登录提示积分余额不足
​

检查账户是否已购买旗舰版

检查账户是否还有余额，点击跳转企业后台查询。

检查是否登录到正确的账号

退出当前账号，通过 手机号 重新登录到旗舰版账号

远程开发（ SSH 常见问题）
​
Q: 无法连接
​

远程SSH插件请求/登录报错

需测试下本地IDE是否正常登录, 如果是远程服务器上的请求问题,要确认远程服务器的外网是否可访问, 如使用ping+网址来判断

如果无法登录，排查如下：

打开 CodeBuddy IDE 设置 Ctrl/Cmd+,

搜索 codebuddy.remote.SSH.enableDynamicForwarding

取消勾选这个选项(设置为 false)

重新连接 SSH

打开容器报错

原因是 Codebuddy 上使用的 Vscode 的 Remotessh 和 dev-container 插件, 报错是 Vscode 的插件报错。 使用 Codebuddy IDE 不需要额外安装 Vscode 官方的 Remotessh 和 dev-container 插件, IDE 内置了这两个插件，需要卸载掉 Vscode 的插件使用内置插件连接即可。

网络检查
​
Q: 代理检测显示“失败/警告”（如 connect ECONNREFUSED）怎么办？
​

可能原因

已开启代理模式，但代理服务未启动、端口不可达或地址填写错误。
代理协议不兼容（建议优先使用 HTTP 代理）。
本机安全软件或公司网络策略拦截了代理端口。

排查指引

打开 IDE 设置，检查代理项（http.proxy、codingcopilot.httpProxySettings、codingcopilot.httpProxyURL）是否配置正确。
在终端验证代理可用性：
国内版：curl -x http://127.0.0.1:8004 -v https://copilot.tencent.com
国际版：curl -x http://127.0.0.1:8004 -v https://www.codebuddy.ai。
若代理验证失败，先修复代理服务（启动进程、校对端口/协议）；无需代理时可临时关闭后重试。
Q: Hosts 解析显示“警告/异常”怎么排查？
​

可能原因

hosts 文件存在旧映射，导致域名被解析到错误 IP。
DNS 服务异常，无法正确解析目标域名。
VPN/系统代理影响了本地解析路径。

排查指引

检查 hosts 文件是否包含目标域名映射：
macOS/Linux：/etc/hosts
Windows：C:\Windows\System32\drivers\etc\hosts
对比解析结果：
国内版：nslookup copilot.tencent.com 或 dig copilot.tencent.com
国际版：nslookup www.codebuddy.ai 或 dig www.codebuddy.ai。
删除错误映射并刷新 DNS 缓存后，重新执行网络检测。
Q: 服务连通性显示“失败”（HTTP 失败）怎么办？
​

可能原因

服务端点可解析，但 HTTP 请求被拦截、超时或握手失败。
证书链、公司网关或代理鉴权导致请求失败。
短时网络波动引发偶发失败。

排查指引

在终端验证服务可达：
国内版：curl -v https://copilot.tencent.com
国际版：curl -v https://www.codebuddy.ai。
再执行超时验证：
国内版：timeout 30s curl -v https://copilot.tencent.com
国际版：timeout 30s curl -v https://www.codebuddy.ai。
若失败，重点检查错误关键词（如 timeout、certificate、proxy、connection refused），按对应方向继续排查。
Q: TCP 连接延迟显示“失败/警告”怎么处理？
​

可能原因

到目标主机 443 端口的直连被防火墙或企业网络策略阻断。
网络质量差导致连接超时。
代理场景下可能出现“直连失败但代理可用”。

排查指引

先测试 TCP 连通性（macOS/Linux）：
国内版：nc -vz copilot.tencent.com 443
国际版：nc -vz www.codebuddy.ai 443。
若不可达，检查本机与公司网络出站规则是否放通 443。
若代理已启用且业务正常，可结合 Proxy Detection 结果综合判断。
Q: 丢包率显示异常（高丢包或 100% 丢包）怎么办？
​

可能原因

当前链路质量差，存在真实丢包。
目标或中间设备禁用了 ICMP（Ping），导致看起来“全丢包”。
本机环境不支持 ping 或结果无法解析。

排查指引

先看检测结果中的 Sent/Received 是否持续异常，而非单次抖动。
终端补充验证：
国内版：ping -c 18 copilot.tencent.com（Windows：ping -n 18 copilot.tencent.com）
国际版：ping -c 18 www.codebuddy.ai（Windows：ping -n 18 www.codebuddy.ai）。
若业务访问正常但 ICMP 全丢包，优先判断为 ICMP 受限，并结合 Service Connectivity 与 TCP 结果综合判断。
Q: 常见错误码和网络检查项如何对应？
​

可能原因

3002/3003 多与链路连通性相关。
3005 多与短时波动或请求超时相关。
10001 多与代理配置不当相关。

排查指引

3002/3003：优先查看“TCP 连接延迟”与“服务连通性”两项检查结果。
3005：先重试；频繁出现时重点查看“丢包率”与“服务连通性”，并确认输入是否超出上下文窗口（约 200K）。
10001：检查代理协议与地址，建议优先使用 HTTP 代理。
Figma 使用
​
Q: Figma 无法添加到对话中？
​

需要申请 Figma 编辑和开发权限，因为 Figma 查看权限默认不开放 Api

开发侧可只开通开发权限，需要先切普通模式再切换到开发模式（ Figma 网页若切换不成功，需手动切换一次）

插件相关
​
Q: 安装问题
​

一般是因为本地之前装过错误版本的插件或者有插件迁移导致，以下两个方案选一个执行：

方案一：

卸载插件；

清空 cache vsix：help > open Logs Folder > 回退到上一级目录 > cachedVSIXs 的文件夹；

（~/Library/Application\ Support/CodeBuddy\ CN/CachedExtensionVSIXs）

清空本地插件，删除 .codebuddycn/extensions/${插件id}

重新去插件商店安装；

方案二：

卸载插件，查询一下 Vscode 1.100.0 对应的插件版本，安装指定版本插件

Q: Python 没有语法高亮, 无法跳转定义
​

Pylance 校验了微软自己的签名，第三方会有运行不起来的问题"

卸载 Pylance
安装 BasedPyrightBasedPyright 默认的检查比较严格，觉得多余可以在设置的这个位置改成 standard：

basedpyright.analysis.typeCheckingMode

Q: C/C++ 无法跳转/高亮
​
C/C++ 微软官方的插件在 CodeBuddy IDE 上会有限制, Codebuddy IDE 建议安装 clangd 作为 c/c++的 lsp (语法高亮和跳转) , 建议安装 clangd 插件进行代码跳转和高亮

注意: 同时要卸载掉 C/C++ 插件, 否则会有冲突

2 如果个别还有问题,确认下项目跟目录是否存在 compile_commands.json文件, 使用如下命令生成:

 cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON

终端
​
Q: 无法打开终端
​

操作方法如下：点击顶部CodeBuddy IDE ，查看首选项，选择设置。

在设置中所搜 Shell，开启 Terminal › Integrated › Shell Integration: Decorations 为 Enabled

Q: 终端无法复用
​

MAC

zsh 安装了有慢速组件或者主题会导致获取 Terminal 状态失败

对 zsh 没有诉求的用户，可以考虑更换 bash 主题

对 zsh 有诉求的用户，可以排查下 ~/.zshrc 有没有配置类似的主题

MCP
​
Q: MCP使用
​

需要在 Craft 模式下使用,Ask 模式不能修改文件，所以禁用了 Mcp，因为 Mcp 可能会修改文件

Q: MCP连接不上
​

将配置文件内名称有空格的位置删除

语言
​
Q: 如何约束Agent对话语言
​

配置 Rules 切换语言，示例如下图：

文件与工作空间
​
Q：更新时提示"检测到应用安装目录下存在用户项目目录"
​
常见原因：CodeBuddy 升级采用全量覆盖,即移除安装目录下的旧版内容，再写入新版文件。若目录中存在你的个人文件（文档、项目、截图等），覆盖时会被一并删除且无法恢复。
建议处理：
打开安装目录：在 CodeBuddy CN 图标上 右键 -> 打开文件所在位置。

常见安装目录路径：

windows：C:\Users{用户名}\AppData\Local\Programs\CodeBuddy
macOS：/Applications/CodeBuddy.app

安装目录下通常有bin, locales, resources, tools, _ 这些文件夹。

移除对话产生的文件夹，仅保留文件名为 bin , locales , resources 和 tools 的系统文件夹。检查是否有个人文件，如果有也请一并移走防止被安装程序覆盖。

重新打开IDE，点击上方 帮助 -> 检查更新，等待安装包下载完成。

Q：Claw工作空间的历史会话找不到了怎么办？
​
常见原因： Claw工作空间中，最近产生对话的任务会在Claw中展示，其他任务仅在工作空间列表展示。
建议处理： Claw适用于远程控制，在电脑端新建任务时不建议将Claw作为工作空间。

最后更新: 2026/7/1 17:09

Pager
上一页
最佳实践
下一页
安全与隐私

---

## 安全与隐私

快速导航
隐私保护
敏感数据保护建议
报告安全问题
重要提示
安全与隐私指南
​
隐私保护
​

CodeBuddy IDE 采取以下隐私保护措施：

敏感信息有限保留期
限制访问用户会话数据

完整隐私政策详情请参考 服务条款 和 隐私政策 文档。

敏感数据保护建议
​
使用环境变量 - 不要在代码中硬编码敏感信息
配置文件加密 - 使用 git-crypt 等工具加密敏感配置
定期轮换凭据 - 使用 apiKeyHelper 动态获取密钥
报告安全问题
​

如果发现安全漏洞，请遵循以下流程：

不要公开披露 - 避免在公开渠道讨论漏洞详情
通过官方渠道联系我们 - 提供安全报告渠道
提供详细信息 - 包含完整的重现步骤和影响范围
协调披露 - 在问题修复前，给予合理的时间窗口
重要提示
​

⚠️ 虽然这些保护措施显著降低了风险，但没有系统能完全免疫所有攻击。在使用任何 AI 工具时，始终保持良好的安全实践。

用户责任：CodeBuddy IDE 只拥有用户授予的权限，用户有责任在批准之前审查建议的代码和命令的安全性。

最后更新: 2026/2/6 23:45

Pager
上一页
故障排除
下一页
联系我们

---

## 联系我们

快速导航
反馈入口
联系我们
​

使用CodeBuddy的过程中遇问题可以向 codebuddy@tencent.com 发送邮件咨询。

如果您希望CodeBuddy提供更好的功能来满足您的需求，请在CodeBuddy IDE内反馈给团队。

反馈入口
​

在IDE内点击右上角的头像图标，选择帮助与反馈：

在意见反馈处描述您的需求，建议上传图片并勾选上传日志，以便团队更准确地理解您的需求和问题:

最后更新: 2026/5/11 15:56

Pager
上一页
安全与隐私
下一页
概览

---

