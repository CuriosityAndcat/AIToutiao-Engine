# 优化页面 UI — 总体方案（2026-07-12）

> 模式：[NEXUS-Sprint] · 触发：用户自然语言「优化页面UI」→ Agent 自动规划
> 范围：A 档（纯 UI/UX 体验优化，不动安全 / 不动架构拆分）
> 质量门：evaluation.py 5 维 / 阈值 75 + 不改生产逻辑之外的破坏

## 一、上下文核查（关键发现）
对比 WEB_REVIEW.md（2026-07-11）与 engine_app.py 当前代码，E-2 + Track3 + 文案修复已覆盖 A 档 8 项中的 7 项：
- D11 颜色 token 化 ✅ / C8 响应式 @media ✅ / C6 日志截断提示 ✅ / C9 首启分阶段状态 ✅
- C5 文案（视频链接多平台）✅ / E14 空状态引导 ✅ / A1 XSS(html.escape) ✅（render_logs 1902 已转义）
- **唯一实质缺口：E13 阶段灯仅颜色+文字，缺形状图标强化色盲友好**

## 二、任务拆分与角色指派
| 任务 | 指派角色（agency） | 内容 | 验收标准 |
|---|---|---|---|
| T1 审计确认 | design/design-ux-researcher | 逐条验证 A 档 8 项达标情况，出清单 | 推理级：8 项状态明确，无遗漏 |
| T2 色盲友好增强 | design/design-ui-designer（+ux-researcher 无障碍视角） | 阶段灯点内叠加形状图标 ✓/▶/✕/○，与颜色+文字三重冗余 | 色盲用户仅凭形状即可区分 4 态；evaluation 风格/结构维≥75 |
| T3 设计师走查打磨 | design/design-ui-designer | 空状态增加示例链接，降低首用认知负担 | 首屏有可拷贝示例；低风险提示 |

## 三、角色校正记录
- `inclusive-visuals-specialist` 实为 AI 生图偏见专家，不用于网页无障碍 → 已由 UI 设计师 + UX 研究员 替代，符合"专业的人做专业的事"。

## 四、检查点
1. 编辑后 `python -m py_compile engine_app.py` 通过（语法门）。
2. 对照 evaluation.py 5 维推理级打分 ≥75。
3. 交付：本方案 + 代码改动；不 commit（待用户授权）。
