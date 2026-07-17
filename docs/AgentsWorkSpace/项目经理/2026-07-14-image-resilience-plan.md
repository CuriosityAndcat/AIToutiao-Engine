# 配图流程韧性改造方案

> **面向 AI 代理的工作者：** 使用 superpowers:subagent-driven-development（推荐）逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。
>
> **关联规格：** 本文是自包含的 Phase A 规格 + Phase B 执行计划，不依赖外部规格文档。

**目标：** 根治配图流程中"生成静默失败→死链→图片数量不足"的 5 层根因，实现纵深防御。

**架构：** 在现有单 Agnes provider 架构上叠加 4 层防御（重试 + 落盘校验 + 组装前过滤 + 内文图固定 3 张），~55 行改动，零新依赖。

**技术栈：** Python 3.10+, `requests`, `time.sleep`, `pathlib`

**诊断结论（5 层根因）：**

| 层级 | 根因 | 影响 |
|------|------|------|
| L1 | `_generate_agnes_image()` 无重试，失败即返回 None | 网络波动导致丢图 |
| L2 | 仅 Agnes 一个 provider，无回退 | Agnes 宕机无图 |
| L3 | `_assemble_article_with_images()` 注入图片引用时不检查文件是否存在 | 封面缺失 → 死链 |
| L4 | 图片数量硬编码（1 封面 + 2 内文），仅 2 张内文不足以覆盖 800-1200 字文章 | 图片太少，阅读体验单薄 |
| L5 | 内文图分布纯机械（`len(body)//(n+1)`），不感知章节 | 图片与内容语义脱节 |

> **证据**：`outputs/20260713/20260713_214023` — 计划 3 张，实际 1 张（inline_1.png），cover.png 缺失但稿件仍引用。

---

## 不改动项（明确排除）

- ❌ 不引入多 provider（Pollinations/豆包等），保持单 Agnes
- ❌ 不修改图片语义分布逻辑（L5 留待后续优化）
- ❌ 不修改 `stage`/`PipelineState` 架构
- ❌ 不修改 `_assemble_article_with_images` 的图片注入策略（只加校验）

---

### 任务 1：`_generate_agnes_image` 添加重试 + 落盘校验（A1 + A2）

**文件：** `engine_app.py:_generate_agnes_image()` 行 1594-1665

- [ ] **步骤 1：添加指数退避重试循环**
  - 将当前 try-except 包裹在 `for attempt in range(3):` 循环内
  - 成功路径：HTTP 200 + 下载成功 + 文件 > 1KB → `return str(output_path)`
  - 失败路径：非成功 → `sleep(2^attempt)` → continue
  - 3 次全失败 → `return None`
  - 注意：`timeout` 参数不变（180s），不因重试改 timeout

- [ ] **步骤 2：添加文件大小校验**
  - 在 `output_path.write_bytes(img_resp.content)` 之后
  - 检查 `output_path.stat().st_size > 1024`（1KB 阈值）
  - 不满足 → 标记为本次失败，进入重试

- [ ] **步骤 3：添加关键日志**
  - 每次重试记录：`[agnes] 第N次尝试失败: {原因}, {sleep}s后重试...`
  - 3 次全失败记录：`[agnes] 3次重试全部失败，放弃: {prompt[:80]}...`

- [ ] **步骤 4：验证**
  - `py_compile engine_app.py` 通过
  - `read_lints engine_app.py` 0 告警

---

### 任务 2：`_assemble_article_with_images` 添加图片存在性校验（A3）

**文件：** `engine_app.py:_assemble_article_with_images()` 行 1927-1997

- [ ] **步骤 1：封面图存在性校验**
  - 注入 `![封面](images/cover.png)` 之前
  - 添加 `if cover_path and Path(cover_path).exists():`
  - 不存在 → `add_log("封面图文件缺失，跳过注入", "warning")`

- [ ] **步骤 2：内文图存在性校验**
  - 对每个 `inline_paths` 中的路径
  - 注入前添加 `if Path(img_path).exists():`
  - 不存在 → `add_log(f"内文配图文件缺失: {Path(img_path).name}，跳过注入", "warning")`

- [ ] **步骤 3：验证**
  - `py_compile engine_app.py` 通过
  - `read_lints engine_app.py` 0 告警

---

### 任务 3：内文图数量固定 3 张（A4）

**文件：** `engine_app.py:step_images()` 行 1782-1924

> **需求修正（2026-07-14）**：每篇文章至少 3 张内文图（而非自适应 1-3 张）。项目文章典型 800-1200 字，3 张内文图 + 1 封面 = 4 图，阅读体验合理。

- [ ] **步骤 1：定义内文图数量常量**
  - 放在 `step_images()` 内部或模块级
  - `INLINE_IMAGE_COUNT = 3`

- [ ] **步骤 2：替换硬编码 `count=2` → `count=INLINE_IMAGE_COUNT`**
  - 行 1843：`_generate_image_prompts_via_llm(title, content, count=INLINE_IMAGE_COUNT)`
  - 行 1869：`_build_inline_prompts(title, content, count=INLINE_IMAGE_COUNT)`

- [ ] **步骤 3：更新进度百分比（可选）**
  - 检查 `_PROGRESS_MAP` 是否需要适配 3 张（当前 `images_cover_done` / `images_all_done` 是百分比跳点，通常不影响）

- [ ] **步骤 4：验证**
  - `py_compile engine_app.py` 通过
  - `read_lints engine_app.py` 0 告警

---

## 影响面分析

| 维度 | 评估 |
|------|------|
| **改动文件** | 仅 `engine_app.py`，3 个函数 |
| **改动行数** | ~55 行（A1~20行 + A3~10行 + A4~10行 + 日志~5行 + 常量~10行） |
| **新增依赖** | 无（`time.sleep`/`pathlib.Path` 均为标准库） |
| **向后兼容** | ✅ `_generate_agnes_image` 签名不变，调用方无需修改 |
| **回归风险** | ✅ 改动仅增强失败处理，不改变成功路径行为 |
| **流水线影响** | ✅ 不阻断流水线的策略不变，仅减少静默失败 |

---

## 验收标准

| 编号 | 标准 | 验证方式 |
|------|------|---------|
| V-1 | `_generate_agnes_image` 在网络波动时自动重试（最多 3 次） | 代码审查 + 单元测试 |
| V-2 | 生成图片文件 < 1KB 时触发重试 | 代码审查 |
| V-3 | `_assemble_article_with_images` 不注入不存在的图片引用 | 代码审查 + 模拟缺失文件 |
| V-4 | 每篇文章固定生成 3 张内文图 prompt | 代码审查 |
| V-5 | `py_compile + lint` 全部通过 | 自动化 |

---

## 不予处理的已知问题（留待后续）

| 问题 | 原因 |
|------|------|
| L5: 内文图语义分布 | 需 NLP 章节检测，改动量超出本次范围 |
| L2: 单 provider 无回退 | Agnes 当前 $0/张稳定，待频繁故障后再升级方案 B |
| 图片风格与内容匹配度 | 属 LLM prompt 优化范畴，非韧性改造 |
