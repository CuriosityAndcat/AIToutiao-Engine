# 烽火情报 — 新写作风格开发任务 [NEXUS-Sprint]

> 创建：2026-07-17 | 项目经理 | 用户拍板待执行

## 需求摘要

**原始需求**：用户在审阅 `outputs/20260717/20260717_111558/文章_20260717_111558.md` 后提出两条限制：
1. 禁止「一、xxx」「二、xxx」编号式章节标题
2. 禁止「说实话」「就离谱」「说白了」「这波操作我是真没看懂」等模板化口语标记

用户明确要求**新建独立风格「烽火情报」**，而非修改现有包明说路径。

**模式判定**：[NEXUS-Sprint] — 功能级 MVP：新建风格 prompt + 人工化规则 + 全链路注册（7 文件）

**涉及模块**：`prompts/fenghuo_qingbao.py`（新建）、`prompts/humanize.py`、`prompts/__init__.py`、`models.py`、`ai_writer.py`、`write_stage.py`、`engine_app.py`、`config.py`

---

## 技术架构回顾

风格系统分两层，注册链路：`models.py → ai_writer.py → write_stage.py → engine_app.py`

```
models.py (ContentStyle枚举)  ─┐
prompts/fenghuo_qingbao.py     ├→ ai_writer.py (STYLE_ROUTER)
prompts/humanize.py (新路径)   ├→ ai_writer.py (_HUMANIZE_ROUTER)
engine_app.py (UI选择器)       ┘
config.py (DEFAULT_CONTENT_STYLE)
```

现有 4 种风格中，全球档案馆是唯一有**专属人工化路径**的风格，也是唯一明确**禁止口语标记**的。烽火情报将参照其设计模式。

---

## 任务清单

### [ ] 任务 1：新建风格 prompt — `prompts/fenghuo_qingbao.py`

**描述**：基于 `baoming_shuo.py` 创建烽火情报风格定义。保留包明说核心（反差悬念 + 短句节奏 + 数据佐证），增加以下约束：
- 禁止「一、xxx」「二、xxx」编号式章节标题
- 禁止「说实话」「就离谱」「说白了」「我服了」「这操作我是真没看懂」等模板化口语
- 角色名改为"烽火情报局"
- 保留金句模板（不是…而是… / 最X的是…），但要求嵌入自然而非堆砌

**指派角色**：`writing-prompt-engineer` subagent（已落地）

**验收标准**：
- 新建 `fenghuo_qingbao.py` 写入 `lib/toutiao-auto-publisher/backend/prompts/`
- 包含 `SYSTEM_PROMPT_FENGHUO_QINGBAO` + `FENGHUO_QINGBAO_TOUTIE_PROMPT`
- prompt 中明确禁止编号标题和模板口语
- `py_compile` 通过

**质量门**：`read_lints` + `py_compile`

---

### [ ] 任务 2：注册新风格到 `prompts/__init__.py`

**描述**：在 `prompts/__init__.py` 中 import 新 prompt 并加入 `__all__`

**指派角色**：主 Agent

**验收标准**：
- `from prompts import SYSTEM_PROMPT_FENGHUO_QINGBAO` 无报错

**质量门**：`py_compile`

---

### [ ] 任务 3：新增烽火情报专属人工化路径 — `prompts/humanize.py`

**描述**：在 `humanize.py` 末尾新增烽火情报专属人工化 System + User Prompt，规则如下：
- 参考全球档案馆路径 "绝对禁止" 部分（禁止口语标记）
- **不用** "馆长/家人们" 人称（那是全球档案馆专属）
- **禁止** `## 一、` `## 二、` 编号式章节标题——改为自然分段，每段用一个强有力的主题句开头
- **禁止** "说实话/就离谱/我服了/这操作我是真没看懂/说白了" 等模板口语
- **保留** 金句模板（不是…而是… / 最X的是…）但不过度堆砌
- **保留** 短句节奏和机枪感
- 段落长度不均衡
- 字数与原文相当

**指派角色**：`writing-prompt-engineer` subagent

**验收标准**：
- 新增 `FENGHUO_QINGBAO_HUMANIZE_SYSTEM_PROMPT` + `FENGHUO_QINGBAO_HUMANIZE_USER_PROMPT`
- 两个 prompt 均明确禁止编号标题和模板口语
- 同时更新 `prompts/__init__.py` 导出

**质量门**：`py_compile` + `read_lints`

---

### [ ] 任务 4：注册 `ContentStyle.FENGHUO_QINGBAO` — `models.py`

**描述**：
- `models.py` `ContentStyle` 枚举新增 `FENGHUO_QINGBAO = "fenghuo_qingbao"`
- `style_label()` 函数新增映射：`"fenghuo_qingbao": "烽火情报（专业锐评型）"`

**指派角色**：主 Agent

**验收标准**：
- `ContentStyle("fenghuo_qingbao")` 不抛异常
- `style_label("fenghuo_qingbao")` 返回 "烽火情报（专业锐评型）"

**质量门**：`py_compile`

---

### [ ] 任务 5：注册 STYLE_ROUTER + HUMANIZE_ROUTER — `ai_writer.py`

**描述**：
- `STYLE_ROUTER` 新增：`ContentStyle.FENGHUO_QINGBAO: (SYSTEM_PROMPT_FENGHUO_QINGBAO, FENGHUO_QINGBAO_TOUTIE_PROMPT, 0.7)`
- `_HUMANIZE_ROUTER` 新增：`ContentStyle.FENGHUO_QINGBAO: (FENGHUO_QINGBAO_HUMANIZE_SYSTEM_PROMPT, FENGHUO_QINGBAO_HUMANIZE_USER_PROMPT, 0.7)`
- 新增 import 语句

**指派角色**：主 Agent

**验收标准**：
- 两处路由均能正确路由到烽火情报 prompt
- 原有 4 风格不受影响

**质量门**：`py_compile` + `read_lints`

---

### [ ] 任务 6：更新 UI 选择器 + 默认风格 — `engine_app.py` + `config.py`

**描述**：
- `engine_app.py` 风格 selectbox 新增选项：`("fenghuo_qingbao", "🗡️ 烽火情报（专业锐评型）")`，放在第一位
- `config.py` `DEFAULT_CONTENT_STYLE` 改为 `"fenghuo_qingbao"`

**指派角色**：`ui-minimal-change` subagent

**验收标准**：
- UI 下拉框中烽火情报排在首位
- 不选风格时默认走烽火情报
- 原有 4 风格仍可选、不受影响

**质量门**：`py_compile` + `read_lints` + 起 Streamlit 看 UI

---

### [ ] 任务 7：真跑实测验证

**描述**：用 `tests/run_loop.py` 或 `tests/run_stage.py --stage 3` 以烽火情报风格跑一次完整 S3→S5，验证产出文章：
1. 无「一、xxx」「二、xxx」编号标题
2. 无「说实话」「就离谱」「说白了」「我服了」等模板口语
3. evaluation.py 5 维 ≥80（研究写作阈值）
4. 保留包明说核心特征（反差悬念、短句节奏）

**指派角色**：主 Agent（执行实测）

**验收标准**：
- 产出文章通过所有 4 项检查
- 评分 ≥80

**质量门**：`run_loop.py` 或 `run_stage.py` 实测

---

## 改动文件汇总

| # | 文件 | 类型 | 行数估计 |
|---|------|------|----------|
| 1 | `prompts/fenghuo_qingbao.py` | 新建 | ~70 行 |
| 2 | `prompts/__init__.py` | 修改 | +4 行 |
| 3 | `prompts/humanize.py` | 修改 | +~100 行（新路径） |
| 4 | `models.py` | 修改 | +3 行 |
| 5 | `ai_writer.py` | 修改 | +4 行 |
| 6 | `engine_app.py` | 修改 | +1 行（UI 选项） |
| 7 | `config.py` | 修改 | 1 行改值 |

> 全部为零生产逻辑改动，仅 prompt 层 + 注册层。

---

## 风险与范围控制

**已识别范围蔓延风险**：
- ❌ **不要**趁机改其他 4 个风格（用户只要求新风格）
- ❌ **不要**动 `evaluation.py` 评分标准（这是独立质量门）
- ❌ **不要**改 `write_stage.py` 自愈逻辑

**待澄清项**：
- 无。所有需求用户已明确。

---

## 执行顺序

```
T1(建prompt) → T2(注册导出) → T3(建humanize) → T4(注册枚举)
    → T5(注册路由) → T6(UI+默认) → T7(实测)
```
