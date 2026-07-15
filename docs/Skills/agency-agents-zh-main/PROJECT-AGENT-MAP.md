# PROJECT-AGENT-MAP — 本仓库对 AIToutiao-Engine 有用的 Agent 映射表

> 本文件是 `agency-agents-zh-main`（266 个中文 AI 专家角色库）与本项目 **AIToutiao-Engine**（视频/口播素材 → 头条/公众号图文自动生成引擎）之间的「可用角色 ↔ 项目环节」对照表。
> 配套理解文档：`REPO-UNDERSTANDING.md`。
> 用法：所有角色均为纯 Markdown，由主 Agent（或 CodeBuddy subagent）在对话中 `read_file` 加载即可，**绝不跑 install/convert 脚本**。

---

## 0. 本项目生产流水线（对照锚点）

```
下载   → lib/video-batch-download-main/          (视频批量下载, Node/JS)
转录   → lib/sensevoice-asr/ + _test_*.py        (ASR 语音转文字, Python)
研究写作→ lib/toutiao-auto-publisher/backend/     (research.py / write_stage.py / evaluation.py / ai_writer.py / fact_pipeline.py)
配图   → prompts/ + Agnes Image 2.0 Flash        (中文 prompt 体系)
组装发布→ engine_app.py + publisher_service.py     (Streamlit UI + 发布服务)
质量门 → evaluation.py (5 维 / 通用阈值 75 / 研究写作 80) + write_stage 自愈闭环 + guardrails.py 三层护栏
框架层 → agent/ (Agent / Runner / AgentGraph / memory / guardrails / search_engine / llm_client)
```

## 1. 按 agentic workflow 四模式归类（Andrew Ng：Planning / Tool Use / Reflection / Multi-Agent）

### 一、Planning（规划）—— 选题、平台策略、内容定位
| Agent | 路径 | 价值 |
|---|---|---|
| 新闻情报官 `marketing-daily-news-briefing` | `marketing/marketing-daily-news-briefing.md` | 多源新闻实时采集+交叉验证，直接产出写作者可用简报，**最贴合选题情报** |
| 中国市场本地化策略师 `marketing-china-market-localization-strategist` | `marketing/marketing-china-market-localization-strategist.md` | 趋势信号→头条/小红书/微信/抖音可执行选题策略 |
| 抖音策略师 `marketing-douyin-strategist` | `marketing/marketing-douyin-strategist.md` | 口播/短视频同源，爆款策划与算法机制可作写作调性参考 |
| 微信公众号运营 `marketing-wechat-operator` | `marketing/marketing-wechat-operator.md` | 公众号内容策略、裂变、私域，对应 publisher_service 发布侧 |
| 小红书运营专家 `marketing-xiaohongshu-operator` | `marketing/marketing-xiaohongshu-operator.md` | 爆款公式、种草结构，可迁移到微头条写作 |
| 内容创作者 `marketing-content-creator` | `marketing/marketing-content-creator.md` | 多平台内容策划，统一选题→成稿叙事 |
| 趋势研究员 `product-trend-researcher` | `product/product-trend-researcher.md` | 6-18 个月前瞻，辅助长期选题池 |
| 商业战略家 `business-strategist` | `specialized/business-strategist.md` | 内容商业化与竞争定位（批次 D 选题变现） |

### 二、Tool Use（工具使用 / 工程技术实现）
| Agent | 路径 | 价值 |
|---|---|---|
| 语音 AI 集成工程师 `engineering-voice-ai-integration-engineer` | `engineering/engineering-voice-ai-integration-engineer.md` | **直接对应转录阶段**：端到端语音转录流水线、Whisper/云端 ASR |
| 前端开发者 `engineering-frontend-developer` | `engineering/engineering-frontend-developer.md` | `engine_app.py` 的 Streamlit/UI 层优化 |
| 提示词工程师 `engineering-prompt-engineer` / `prompt-engineer` | `engineering/engineering-prompt-engineer.md` / `specialized/prompt-engineer.md` | 优化 `prompts/` 下模板与风格切换，提升 5 维评分 |
| 图像提示词工程师 `design-image-prompt-engineer` | `design/design-image-prompt-engineer.md` | 配图中文 prompt 体系优化，贴合 Agnes Image 2.0 |
| AI 工程师 `engineering-ai-engineer` | `engineering/engineering-ai-engineer.md` | LLM 调用工程化（`ai_writer.py`/`llm_client.py`） |
| 数据工程师 `engineering-data-engineer` | `engineering/engineering-data-engineer.md` | 内容/日志数据管线、湖仓 |
| DevOps 自动化师 `engineering-devops-automator` | `engineering/engineering-devops-automator.md` | 流水线 CI/CD、`run_engine.bat` 部署 |
| MCP 构建器 `specialized-mcp-builder` | `specialized/specialized-mcp-builder.md` | 为引擎扩展工具集成（搜索/发布） |
| 微信小程序开发者 `engineering-wechat-mini-program-developer` | `engineering/engineering-wechat-mini-program-developer.md` | 发布侧多渠道扩展 |
| 文档生成器 `specialized-document-generator` | `specialized/specialized-document-generator.md` | 生成最终图文 DOCX/PDF 交付物 |

### 三、Reflection（反思 / 质量验收 / 合规护栏）
| Agent | 路径 | 价值 |
|---|---|---|
| 现实检验者 `testing-reality-checker` | `testing/testing-reality-checker.md` | **思想同源**于 `evaluation.py` 质量门：默认"需要改进"，要求压倒性证据才放行 |
| 代码审查员 `engineering-code-reviewer` | `engineering/engineering-code-reviewer.md` | 代码质量门（SAWORKFLOW 代码任务质量门之一） |
| 最小变更工程师 `engineering-minimal-change-engineer` | `engineering/engineering-minimal-change-engineer.md` | 严守最小改动纪律，拒绝范围蔓延 |
| 证据收集者 `testing-evidence-collector` | `testing/testing-evidence-collector.md` | 验收结论需证据链，贴合 `log/` 三通道观测 |
| 模型 QA 专家 `specialized-model-qa` | `specialized/specialized-model-qa.md` | 端到端审计 LLM 输出质量（去 AI 味/事实幻觉） |
| 百度 SEO 专家 `marketing-baidu-seo-specialist` | `marketing/marketing-baidu-seo-specialist.md` | 标题/关键词优化，提升头条搜索曝光 |
| AI 治理政策专家 `specialized-ai-policy-writer` | `specialized/specialized-ai-policy-writer.md` | 内容安全护栏，贴合 `guardrails.py` 三层 |
| 法务合规员 `support-legal-compliance-checker` / 制度文件撰写专家 `legal-policy-writer` | `support/support-legal-compliance-checker.md` / `legal/legal-policy-writer.md` | 中国《个人信息保护法》三法合规，发布前检查 |
| 工作流优化师 `testing-workflow-optimizer` | `testing/testing-workflow-optimizer.md` | 流水线瓶颈消除、局部刷新防闪等优化 |

### 四、Multi-Agent Collaboration（多智能体协作 / 编排）
| Agent | 路径 | 价值 |
|---|---|---|
| 智能体编排者 `agents-orchestrator` | `specialized/agents-orchestrator.md` | **核心参照**：编排整个开发/内容工作流，等价于 SAWORKFLOW 控制平面 |
| 多智能体系统架构师 `engineering-multi-agent-systems-architect` | `engineering/engineering-multi-agent-systems-architect.md` | 拓扑/上下文/信任/故障恢复/human-in-the-loop，**直接对应 `agent/graph.py`+`runner.py` 待接入** |
| 工作流架构师 `specialized-workflow-architect` | `specialized/specialized-workflow-architect.md` | 为引擎绘制完整工作流树（下载→转录→研究写作→配图→发布） |
| 幕僚长 `specialized-chief-of-staff` | `specialized/specialized-chief-of-staff.md` | 跨部门协调、OKR 追踪，适合总控选题+成稿+发布 |
| Git 工作流大师 `engineering-git-workflow-master` | `engineering/engineering-git-workflow-master.md` | 约定式提交、分支策略 |
| 高级项目经理 `project-manager-senior` | `project-management/project-manager-senior.md` | 把规格拆成可执行任务、记取经验教训 |

---

## 2. 优先级建议 — 最该先用的 Top 8（已创建为 CodeBuddy subagent）

> 这 8 个已落地为可调用角色，文件位于 `.codebuddy/agents/`，对话中按需 `@` 或派发即可。

| # | Agent（subagent 名） | 源角色路径 | 对应流水线环节 | 核心用途 |
|---|---|---|---|---|
| 1 | `news-briefing-expert` | `marketing/marketing-daily-news-briefing.md` | 选题/规划 | 多源新闻→结构化简报，直接喂 `write_stage` |
| 2 | `voice-ai-transcription-engineer` | `engineering/engineering-voice-ai-integration-engineer.md` | 转录 | 端到端 ASR 流水线优化（`lib/sensevoice-asr`） |
| 3 | `image-prompt-engineer` | `design/design-image-prompt-engineer.md` | 配图 | 中文配图 prompt 体系（Agnes Image 2.0） |
| 4 | `writing-prompt-engineer` | `engineering/engineering-prompt-engineer.md` | 研究写作 | `prompts/` 模板与风格切换调优 |
| 5 | `reality-checker` | `testing/testing-reality-checker.md` | 验收 | 质量门，与 `evaluation.py` 同源 |
| 6 | `agent-orchestrator` | `specialized/agents-orchestrator.md` | 总控 | SAWORKFLOW 控制平面/编排 |
| 7 | `multi-agent-architect` | `engineering/engineering-multi-agent-systems-architect.md` | 框架接入 | `agent/graph.py`+`runner.py` 接入参照 |
| 8 | `legal-compliance-checker` | `support/support-legal-compliance-checker.md` | 发布合规 | 发布前中国法规合规检查 |

---

## 3. 与本项目的质量门关系

- **内容质量门**：`reality-checker`（现实检验者，默认"需要改进"）思想与本项目 `evaluation.py`（5 维 / 通用阈值 75 / 研究写作 80）+ `write_stage` 自愈闭环同源；作为 SAWORKFLOW 的质量门执行者。
- **代码质量门**：`engineering-code-reviewer` + `engineering-minimal-change-engineer` 对应 SAWORKFLOW 代码任务质量门（真跑实测级）。
- **安全护栏**：`legal-compliance-checker` + `specialized-ai-policy-writer` 对应 `guardrails.py` 输入/输出/政策三层护栏。
- **编排**：`agent-orchestrator` + `multi-agent-architect` 对应 SAWORKFLOW 两阶段协议与 `agent/` 框架层的 `AgentGraph`/`Runner`（当前未接生产，两条自愈并存）。

---

## 4. 维护

- 本表随 `agency-agents-zh-main` 上游同步（基线 2026-06-16）与本项目流水线演进更新。
- 新增可用角色时，按四模式归类追加，并优先评估是否进入 Top 8。
- 所有角色通过 `read_file` 加载源 `.md`，不修改源角色文件、不执行其 install/convert 脚本。
