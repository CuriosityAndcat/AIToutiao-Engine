# World Monitor 项目深度分析

> 创建日期：2026-07-18
> 分析对象：[koala73/worldmonitor](https://github.com/koala73/worldmonitor) v2.5.23
> GitHub Stars: 62k | Forks: 9.6k | License: AGPL-3.0
> 官方站点：https://worldmonitor.app
> 分析目的：评估该项目作为 AIToutiao-Engine 军事号视频素材源与情报输入端的可行性

---

## 一、项目定位

World Monitor 是一个 **实时全球情报仪表盘**，核心解决「信息碎片化、地理无关联、分析门槛高」的痛点。它把地缘政治、军事、经济、基础设施、自然灾害等多维度信息聚合到一个统一的态势感知界面上。

对 AIToutiao-Engine 军事号而言，这个项目有 **三重价值**：

| 价值维度 | 说明 |
|---------|------|
| **① 实时情报输入** | 取代手动搜索 → AI 自动获取结构化军事情报（航班、舰船、冲突、CII 评分） |
| **② 视频素材源** | 2D/3D 地图 + 数据可视化层 → 可录制为「军事态势感知」风格视频 |
| **③ 选题信号源** | CII 突变、地理聚合告警、冲突升级 → 自动触发选题简报 |

---

## 二、技术架构总览

```
浏览器/桌面应用（DeckGLMap + GlobeMap + 105 面板组件）
         │
      fetch /api/*
         │
   Vercel 边缘函数（SPA + API 网关 + 中间件）  ←→  Upstash Redis（缓存）
         │                                        ↑
   +---------+-----------+                     Railway 服务
   │  Railway AIS Relay  │                     · 种子循环
   │  Consumer Prices    │                     · 数据预处理
   +---------------------+
         │
   +-----+------+---------+
   │ 65+ 外部 API 提供方  │
   +-----------------------+
```

### 技术栈

| 层 | 技术 |
|----|------|
| **前端** | Vanilla TypeScript + Vite + deck.gl + globe.gl/Three.js + MapLibre GL |
| **桌面** | Tauri 2.x (Rust) + Node.js 边车 |
| **AI/ML** | Ollama / Groq / OpenRouter + Transformers.js（浏览器端 ONNX 推理） |
| **API/协议** | Protocol Buffers（281 proto 文件，35 服务），sebuf HTTP 标注 |
| **部署** | Vercel Edge Functions（60+）、Railway relay、Tauri、PWA、Docker |
| **缓存** | Upstash Redis（3 级缓存 + CDN + Service Worker） |

### 6 个变体站点（同一代码库）

| 变体 | 域名 | 侧重 |
|------|------|------|
| **world** | worldmonitor.app | 全球综合（默认） |
| tech | tech.worldmonitor.app | 科技动态 |
| finance | finance.worldmonitor.app | 金融市场 |
| commodity | commodity.worldmonitor.app | 大宗商品 |
| energy | energy.worldmonitor.app | 能源态势 |
| happy | happy.worldmonitor.app | 正面新闻 |

---

## 三、军事相关核心能力（与我们最相关的部分）

### 3.1 军用飞机追踪

- **数据源**：OpenSky Network（ADS-B 数据）
- **元数据**：Wingbits（飞机序列号、所有者、建造年份）
- **刷新频率**：每 **8 分钟** 更新一次
- **反封锁机制**：OpenSky 屏蔽云提供商 IP → 桌面版通过 Node.js 边车 + 强制 IPv4 绕过；或使用 RadarVirtuel 镜像
- **可视化**：在 deck.gl 2D 地图 + globe.gl 3D 地球上以图标/路径图层展示

### 3.2 海军舰船追踪

- **数据源**：aisstream.io WebSocket（AIS 自动识别系统）
- **刷新**：实时流式推送
- **数据字段**：MMSI、经纬度（5 位小数）、船舶类型、最后更新
- **内存管理**：`vesselRegistry` Map + 两级背压队列防溢出
- **叠加**：USNI Fleet Report 合并航母打击群信息

### 3.3 冲突事件监控

| 数据源 | 提供内容 |
|--------|---------|
| **ACLED**（实时） | 抗议、暴动、战斗、爆炸、平民暴力、死亡人数 |
| **UCDP GED**（历史基线） | 2 年内窗口的冲突分类（war/minor） |
| **OREF**（以色列） | 火箭弹/民防实时警报 |
| **GDELT** | 全球事件语调与紧张态势评分 |

### 3.4 国家不稳定指数（CII v8）

**这是本项目最有价值的特性。** 对 31 个 Tier-1 国家做高频不稳定性评分：

#### 四维评分体系

| 维度 | 权重 | 数据来源 |
|------|:----:|---------|
| **Unrest（骚乱）** | 25% | ACLED 抗议/暴动 + 断网/断电事件 |
| **Conflict（冲突）** | 30% | ACLED 战斗/爆炸/平民暴力 + UCDP + 死亡人数 |
| **Security（安全）** | 20% | 军机飞行数量 + 军舰活动 + 航空关闭 + GPS 干扰 |
| **Information（信息）** | 25% | 机密新闻标题 + 国家归属威胁摘要 |

#### 最终公式

```
加权事件分 = Unrest×0.25 + Conflict×0.30 + Security×0.20 + Information×0.25
混合得分   = 基线风险×0.4 + 加权事件分×0.6 + 动态加成
```

#### 评分等级

| 分数 | 等级 | 含义 |
|------|------|------|
| 0-30 | low | 低风险 |
| 31-50 | normal | 正常 |
| 51-65 | elevated | 升高 |
| 66-80 | high | 高风险 |
| 81-100 | critical | 危急 |

#### 31 个 Tier-1 国家

| 区域 | 国家 |
|------|------|
| 美洲 | 美国、委内瑞拉、巴西、墨西哥、古巴 |
| 欧洲 | 德国、法国、英国、波兰 |
| 东欧 | 俄罗斯、乌克兰 |
| 中东 | 伊朗、以色列、沙特、阿联酋、土耳其、叙利亚、也门、伊拉克、黎巴嫩、埃及、卡塔尔 |
| 亚太 | 中国、台湾、朝鲜、印度、巴基斯坦、缅甸、韩国、日本 |
| 中亚/南亚 | 阿富汗 |

**注意**：伊朗和以色列在该系统中是重点监控对象——与我们「美军再打伊朗能打多久」选题直接相关。

### 3.5 信号系统

#### 地理聚合检测（Geo-Convergence）
- 将事件按 1° 网格存储
- 同一网格内出现 ≥3 种事件类型 → 触发告警
- 告警分 = 类型数×25 + min(25, 事件总数×2)

#### 热点升级评分
针对预定义热点地区（`INTEL_HOTSPOTS`），加权：
- 新闻活跃度 35%
- CII 贡献 25%
- 地理聚合 25%
- 军事活动 15%

#### 关键词爆发检测
- 7 天基线窗口 + 2h 滚动窗口
- 突发倍数 ≥ 3 → 触发「关键词趋势」信号

---

## 四、其他重要能力

### 4.1 新闻聚合与 AI 简报
- **500+ 精选新闻源**，覆盖 15 个分类
- AI 实时生成摘要（支持本地 Ollama 运行）
- 新闻聚类（Jaccard 相似度 + Worker 线程计算）
- 跨流关联：军事↔经济↔灾难↔升级信号联动

### 4.2 双地图引擎 + 56 种图层
- **deck.gl 2D 平面地图**：散点、路径、图标、热力图、聚类等
- **globe.gl 3D 地球**：单 `htmlElementsData` 数组，大气着色、自动旋转
- **56 种地图图层**：军事飞行、舰船、冲突事件、抗议、地震、野火、网络威胁、航空等
- PMTiles 协议底图

### 4.3 金融雷达
- 29 个全球股票交易所
- 大宗商品 + 加密货币
- 7 信号市场综合指数

### 4.4 程序化访问（与我们集成最相关）

#### MCP 服务器
- 112 个工具（tools），33 个服务（services）
- 支持 Streamable HTTP
- 可接入 Claude Code / Cursor / Windsurf 等 AI IDE

#### Python SDK
```bash
pip install worldmonitor-sdk
```
零依赖客户端，可获取：国家简报、风险评分、冲突/网络/市场/新闻推送。

#### CLI 工具
```bash
npx worldmonitor seismology list-earthquakes --min_magnitude 6
npx worldmonitor military list-flights --region middle-east
npx worldmonitor intelligence get-country-score --code IR
```

#### REST API
- OpenAPI 规范
- Vercel Edge 托管
- 分级缓存：fast(300s) ~ daily(86400s)

---

## 五、完整数据源清单（65+ 提供商）

### 军事与安全
| 数据源 | 内容 |
|--------|------|
| OpenSky Network | ADS-B 航班状态向量 |
| Wingbits | 飞机序列号/所有者/建造年份 |
| aisstream.io | 全球 AIS 船舶实时位置 |
| USNI Fleet Report | 航母打击群部署信息 |
| ACLED | 武装冲突地点与事件（实时） |
| UCDP GED | 乌普萨拉冲突数据（历史基线） |
| OREF | 以色列火箭弹/民防实时警报 |
| PizzINT | 敏感地点活跃度监控 |
| GPSJAM | GPS/GNSS 干扰全球地图 |

### 地缘政治与情报
| 数据源 | 内容 |
|--------|------|
| GDELT | 全球事件语调与紧张态势 |
| 美国国务院旅行建议 | 4 级旅行警告 |
| 自定义抓取脚本 | 伊朗敏感地点（帕尔钦、阿巴斯港等） |

### 经济与金融
| 数据源 | 内容 |
|--------|------|
| FRED | 美联储经济数据 |
| BIS | 国际清算银行 |
| WTO | 世界贸易组织 |
| Finnhub | 财报/日历/国会交易/社交情绪 |
| SEC EDGAR | Form 4 内部人交易解析 |

### 环境与灾害
| 数据源 | 内容 |
|--------|------|
| USGS | 地震实时数据 |
| HAPI/HDX | 人道主义/流离失所数据 |

### 新闻与媒体
- 500+ RSS 新闻源（15 分类，25 种语言）
- AI 新闻聚类 + 摘要（浏览器端 ONNX + Ollama）

---

## 六、对 AIToutiao-Engine 军事号的价值评估

### 6.1 作为「视频素材源」

**方案 A：直接录制 World Monitor 界面**

做「军事态势感知」风格视频：录屏 World Monitor 的 3D 地球 + 2D 地图 + CII 面板 + 军事飞行图层，加上 AI 配音解说当前态势。

| 维度 | 评价 |
|------|------|
| 画质 | **高** — deck.gl/globe.gl 专业 GIS 渲染 |
| 物理准确 | **满分** — 真实 ADS-B/AIS 数据 |
| 原创性 | **满分** — 自录界面 + 自配解说 |
| 风格独特 | **独有** — 目前头条/抖音上很少有这种风格的军事视频 |
| 实时性 | 领先 — 数据 8 分钟刷新，可做「今日实时态势」系列 |
| 门槛 | 中 — 需自部署或使用公开站点 |

**方案 B：通过 API/SDK 拉数据 → 自行可视化**

用 Python SDK 拉 CII 评分 + 冲突事件 → 在本地用 matplotlib/plotly 做定制图表 → 录制成视频。更灵活但开发工作量大。

### 6.2 作为「选题信号源」

可接入 `news-briefing-expert` Agent：

```
World Monitor CII 突变/告警 → 触发选题信号
                             → news-briefing-expert 自动生成选题简报
                             → content-creator 写作
```

具体触发规则：
- **CII spike**：某国分数变化 ≥ 10 点 → 立即选题
- **Geo-Convergence alert**：3+ 事件类型在同一 1° 网格交汇 → 区域热点选题
- **Conflict escalation**：UCDP 状态从 minor→war → 战争升级选题
- **Military flight surge**：某区域军机数量异常增加 → 军事动向选题

### 6.3 作为「写作数据源」

CII 的四维评分（unrest/conflict/security/information）可直接作为文章数据佐证：

```
"根据实时不稳定性指数，伊朗今天的 security 维度从 45 暴涨到 72，
这意味着过去 24 小时内霍尔木兹海峡周边军机活动激增了 3 倍..."
```

### 6.4 风险与限制

| 风险 | 说明 | 缓解 |
|------|------|------|
| **AGPL-3.0 许可证** | 自部署修改后必须开源 | 仅使用 API/MCP（不修改源码）则不受影响 |
| **API 依赖** | 公共 API 无可用性 SLA | 桌面版有 Node.js 边车绕过云 IP 限制 |
| **数据延迟** | 种子脚本 8min-1h 不等 | 对于文章生产（非实时交易）完全够用 |
| **学习成本** | 自部署涉及 Vercel+Railway+Redis | 建议先用公开站点 worldmonitor.app，满意后再自部署 |

---

## 七、推荐集成方案

### 短期（本周可做）

1. **试用公开站点** → 在 worldmonitor.app 上录制中东区域的 3D 地球 + 军事图层 → 手动加 AI 配音 → 产出一条「今日中东态势」视频
2. **验证选题信号** → 手动查看 CII 面板 + 告警列表 → 看谁能触发选题 → 与现有 news-briefing-expert 选题质量对比

### 中期（1-2 周）

1. **接入 MCP 服务** → 部署 `worldmonitor-mcp` 到 CodeBuddy → `news-briefing-expert` Agent 可通过 MCP tools 拉结构化情报
2. **Python SDK 集成** → 写一个 `lib/worldmonitor_fetcher.py` 适配器 → 给 `research.py` 增加 World Monitor 数据源

### 长期（1 月+）

1. **自部署 World Monitor** → Vercel + Railway + Redis → 定制军事号专属面板（只显示中东/亚太/台海区域）
2. **自动化视频生成** → 定制仪表盘 → Puppeteer 定时截图 → FFmpeg 拼帧 → AI 配音 → 自动发布

---

## 八、快速验证清单

| 步骤 | 操作 | 预期结果 | 用时 |
|------|------|---------|------|
| 1 | 打开 worldmonitor.app，切换到中东视角 | 看到伊朗/以色列周边的军机飞行轨迹 + CII 面板 | 2 分钟 |
| 2 | 打开 Military 面板 | 看到当前活跃的军机列表 + 航母部署状态 | 1 分钟 |
| 3 | 查看 CII → Iran | 看到伊朗实时不稳定性分数 + 四维分解 + 24h 趋势 | 1 分钟 |
| 4 | 查看 Alerts | 看到当前活跃的地理聚合告警 + CII spike | 1 分钟 |
| 5 | 用 OBS/系统录屏录一段 30 秒的 3D 地球旋转 | 产出第一个「态势感知」风格素材 | 5 分钟 |
| 6 | 加 AI 配音（剪映 TTS） | 完整 30 秒视频成品 | 3 分钟 |

---

## 九、相关链接

| 资源 | 链接 |
|------|------|
| GitHub 主仓库 | https://github.com/koala73/worldmonitor |
| 官方站点 | https://worldmonitor.app |
| CII 方法学文档 | https://www.worldmonitor.app/docs/country-instability-index |
| MCP 服务器（社区） | https://github.com/mahimn01/worldmonitor-mcp |
| Python SDK | `pip install worldmonitor-sdk` |
| 军事追踪文档 | https://github.com/koala73/worldmonitor/blob/main/docs/military-tracking.mdx |
| 架构文档 | https://github.com/koala73/worldmonitor/blob/main/ARCHITECTURE.md |
| DeepWiki 解析 | https://deepwiki.com/koala73/worldmonitor |

---

*本文档由军事号运营指挥官协调生成，基于对 koala73/worldmonitor v2.5.23 的完整分析。2026-07-18。*
