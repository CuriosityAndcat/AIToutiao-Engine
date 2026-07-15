# 组装阶段「完整稿件_配图版.md」架构修复方案

- 文档类型：**纯方案文档（只描述，不修改任何 .py / 现有 .md）**
- 作者视角：AIToutiao-Engine 写作提示词工程师
- 日期：2026-07-15
- 关联产物：`outputs/20260714/20260714_175422/完整稿件_配图版.md`（问题样本）
- 参考标杆：`docs/采集/包明说/包明说_"中国人不得买地！"…主板回应一针见血.md`

---

## 0. 用户要求（正确架构）

> 需要有一个 `title`，然后是文章内容，文章内容中穿插三个内容图片，最后跟一个封面图片。

即顺序为：**`title` →（正文，其中穿插 3 张内文图）→ 1 张封面图（文末）**。

---

## 1. 正确目标架构模板

依据用户要求与包明说真实头条文（参考 A）的"正文直接以段落开场、无多余 `#` 标题、无平台标签"特征，推荐如下 markdown 模板。

> **title 承载方式决策**：参考 A 的 frontmatter 用 `title:` 字段承载标题，正文直接以段落开场（无 `#` 标题）；而当前引擎在 `write_stage.py` 已用 `# {best_title}` 作为文章首行承载标题，且下游 `publisher_service.py` 的 `convert_markdown_to_html` 依赖 `# ` 渲染 `<h1>`、并单独从 `generated_title` 取标题填发布框。**两者只取其一、且必须置于文首正文前、封面图之前**。
>
> 综合"最小改动 + 下游兼容"原则，**保留单个 `# 正式标题` 行作为 title 承载（置于文件第 1 行），不引入 frontmatter**（避免改动 `publisher_service.py` 与 `state.outputs` 读取逻辑）。封面图以单个 `![封面](images/cover.png)` 置于文件最后一行之后。

```markdown
# 霍尔木兹海峡"买路钱"：美军20%收费背后的霸权焦虑与致命反击

（正文段落：以开场白/钩子直接起头，不再出现第二个 # 文章标题、不出现 #话题标签、不出现"抖音"字样）

（正文段落…）

![内文配图](images/inline_1.png)

（正文段落…）

![内文配图](images/inline_2.png)

（正文段落…）

![内文配图](images/inline_3.png)

（正文段落 + 金句/互动收尾…）

![封面](images/cover.png)
```

**结构断言（供验收）**：
1. 文件第 1 行是且仅是一个 `# 正式标题`（无 `#话题标签`、无"抖音"字样、无第二个 `# 标题`）。
2. 标题与正文之间无封面图（封面不在开头）。
3. 正文内恰好 3 张 `![内文配图](images/inline_N.png)`（N=1,2,3）。
4. 文件末行为 `![封面](images/cover.png)`，其后无正文、无元数据行。
5. 全文件无 `*第N轮 | 评分… | 人工化改写 | …*` 之类的流水线元数据行。

---

## 2. 当前缺陷对照表

| # | 问题点 | 现状（问题文件） | 正确形态 |
|---|--------|------------------|----------|
| 1 | 封面图位置 | 第 3 行 `![封面](images/cover.png)`，位于标题之前、正文之前 | 置于文件**最后**（正文之后） |
| 2 | 标题结构 | 出现**两个** `#` 标题：第 1 行抖音风 `# …#霍尔木兹 #美军收费 #第五舰队遇袭 抖音`（含 `#话题标签` + "抖音"），第 5 行才是正式 `# 霍尔木兹海峡"买路钱"…` | 仅**一个** `#` 正式标题，位于文首，无平台标签、无"抖音"字样 |
| 3 | 标题被平台标签污染 | `best_title` 携带抖音 `#话题标签` 与结尾"抖音"（来自未清洗的视频原始标题兜底） | 标题为干净的正式文章标题 |
| 4 | 末尾元数据行 | 第 47-48 行 `*第1轮 | 评分72 | 人工化改写 | 2026-07-14T17:57:24.066709*` | 去除或规整（不应残留在面向发布的稿件中） |
| 5 | 内容图片穿插 | 3 张内文图穿插位置基本合理（✓ 此处正常） | 保持：3 张内文图穿插于正文 |

---

## 3. 根因分析（具体函数 / 文件:行号）

### 问题 1：封面图被拼到开头（应为文末）
- **`engine_app.py:1402-1419`**（`_assemble_article_with_images` 的"注入封面图"分支）：
  逻辑为"找到第一个以 `# ` 开头的行，在其下方插入封面图"。这把封面插在**标题之后、正文之前**，而非文末。
  ```python
  # engine_app.py:1408-1419
  insert_idx = 0
  for i, line in enumerate(lines):
      if line.startswith("# "):
          insert_idx = i + 1
          while insert_idx < len(lines) and lines[insert_idx].strip() == "":
              insert_idx += 1
          break
  if insert_idx > 0:
      lines.insert(insert_idx, f"![封面]({cover_rel})")
      lines.insert(insert_idx + 1, "")
      content = "\n".join(lines)
  ```
  → 这正是封面出现在第 3 行（标题后）的直接原因。正确做法应为 `lines.append(...)` 到末尾。

### 问题 2 + 3：抖音风 `#标题` + `#话题标签` + "抖音" 来源
- **`write_stage.py:284-287`**（`_apply_humanize_and_finalize` 保存人工化版本）：
  ```python
  output_file.write_text(
      f"# {title}\n\n{content}\n\n---\n"
      f"*第{best_iteration}轮 | 评分{best_score} | 人工化改写 | {datetime.now().isoformat()}*",
      encoding="utf-8",
  )
  ```
  文件的 `# {title}` 第一行即问题文件的抖音风 `# 标题`。`title` = `best_title`。
- **`write_stage.py:927`**（V2 主循环）/ **`:558`**（CP）/ **`:756`**（CP 降级）：
  ```python
  title = (result.get("title", "") or "").strip() or _fallback_title(raw_video_title)
  ```
  当 LLM 未返回 `标题：` 时，`best_title` 回退到 `_fallback_title(raw_video_title)`。
- **`write_stage.py:333-347`**（`_fallback_title`）：清洗**不彻底**——只去 `抖音独家/独家` 前缀与 `【[` 方括号，**未去除行内 `#话题标签`（如 `#霍尔木兹 #美军收费`）和结尾"抖音"字样**。抖音下载的原始标题（`engine_app.py:548-566` `_download_via_node` 提取的 `title`）常带这些平台标签，于是被原样写入 `best_title` → `generated_file` 第一行 → 组装后成为文件首行。
  ```python
  def _fallback_title(video_title: str) -> str:
      ...
      t = re.sub(r"[【\[].*?[\]】]", "", t).strip()  # 只去方括号标签
      return t or video_title.strip()                 # #话题标签 / "抖音" 残留
  ```
  → 这是"抖音风标题 + 两个 `# 标题`"的根因（首个 `#` 行是污染的 `best_title`，第二个 `#` 行才是 LLM 正常返回的正式标题）。
- 注：`prompts/*` 各风格模板统一要求输出 `标题：xxx` 格式（`baoming_shuo.py:52`、`global_archive.py:55`、`general.py:19`、`story_narrative.py` 同），**不会**主动产出 `#话题标签` 抖音风标题；问题确系 `raw_video_title` 兜底污染，非 prompt 缺陷。

### 问题 4：末尾元数据行来源
- **`write_stage.py:286`**（人工化版本）与 **`write_stage.py:206`**（AI 原始版本）都会写入形如
  `*第N轮 | 评分X | 人工化改写 | <ISO时间戳>*` 的元数据行。
- 组装函数 `_assemble_article_with_images`（`engine_app.py:1375-1462`）只是**原样读取 `generated_file` 文本**并注入图片，**不会剥离这行元数据**，故它随正文进入 `完整稿件_配图版.md` 末尾。
- 该元数据行对"面向发布的最终稿件"属于噪声，应去除或规整（见第 4 节）。

---

## 4. 修复建议（仅描述，不执行）

### 4.1 封面图改 append 到文末
- **文件**：`engine_app.py`，函数 `_assemble_article_with_images`，第 1402-1419 行。
- **改动**：删除"找到第一个 `# ` 行下方插入"的逻辑，改为在 `content` 末尾追加：
  ```
  \n\n![封面](images/cover.png)
  ```
  （保留 `if cover_file.exists()` 校验；保持极简、无说明文字的设计约束）。
- **涉及 prompts？** 否，纯组装逻辑改动。

### 4.2 标题只保留一个正式 title，去除抖音 `#话题标签`
两处协同修复：
- **A. 彻底清洗兜底标题** —— `write_stage.py:333-347` 的 `_fallback_title`：在现有方括号清洗后，**追加去除 `#话题标签`（`re.sub(r"#\S+", "", t)`）与结尾"抖音"等平台词**（`t = re.sub(r"抖音$", "", t).strip()` 并去除多余空格）。确保 `best_title` 永不被平台标签污染。
- **B. 组装阶段强制只保留首个 `# 标题`** —— 在 `engine_app.py` `_assemble_article_with_images` 写入前，对 `content` 做规整：若正文内出现多于一个以 `# ` 开头的行（即 LLM 在正文又写了 `# 章节` 之外的第二个文章标题），**仅保留文件首行那个 `# 正式标题`**，移除后续重复的文章级 `# 标题`（注意：章节标题 `## 一、…` 是 `## `，不是 `# `，不应被误删——用严格 `line == "# ..."` 或 `line.startswith("# ")` 且非 `## ` 判定）。
- **涉及 prompts？** 否（prompt 已正确要求 `标题：xxx`，无需改）。若担心 LLM 偶发把正文首段写成第二个 `# 标题`，可在 `prompts/baoming_shuo.py` 等输出格式段**追加一句约束**："只输出一次标题（标题：xxx 一行），正文内禁止再写 `# 文章标题`"，作为双保险（可选，非必须）。

### 4.3 末尾元数据行去除 / 规整
- **文件**：`write_stage.py:284-287`（人工化版本）/ `:203-208`（AI 原始版本）。
- **改动**（推荐最小侵入）：在 `_assemble_article_with_images`（`engine_app.py`）写入 `完整稿件_配图版.md` **之前**，从 `content` 中剥离形如 `*第N轮 | 评分… | …*` 的元数据行（正则 `re.sub(r"\n*^\*第.*轮 \| 评分.*\*$", "", content, flags=re.MULTILINE)`）。
  理由：元数据对调试/质检有价值，应保留在 `*_ai_raw.md` 与 `{prefix}_{run_id}.md` 中，但**不应进入面向发布的配图版**。集中在一处（组装函数）剥离，避免改动两处写入点。
- **涉及 prompts？** 否。

### 4.4 改动影响面小结
| 改动 | 文件:行 | 类型 |
|------|---------|------|
| 封面图 append 到文末 | `engine_app.py:1402-1419` | 组装逻辑 |
| 兜底标题清洗 `#标签`/"抖音" | `write_stage.py:333-347` | 标题清洗 |
| 组装只保留一个 `#标题` | `engine_app.py` `_assemble_article_with_images` | 组装逻辑 |
| 剥离末尾元数据行 | `engine_app.py` `_assemble_article_with_images` | 组装逻辑 |
| （可选）prompt 双保险约束 | `prompts/baoming_shuo.py` 等输出格式段 | prompt 资产 |

> 上述均为生产逻辑改动，按规约**需先呈现方案由用户拍板后再实施**；本文件仅作方案归档。

---

## 5. 验收标准（实施后 `完整稿件_配图版.md` 应满足）

1. **title 唯一且干净**：第 1 行为单个 `# 正式标题`；标题字符串内不含 `#话题标签`、不含"抖音"、不含平台前缀；全文件仅此一个 `# `（单井号）文章标题（`## ` 章节标题不受影响）。
2. **正文穿插 3 内文图**：正文区域恰好 3 处 `![内文配图](images/inline_1.png|inline_2.png|inline_3.png)`，分布合理（非全部堆在末尾）。
3. **封面图在文末**：文件最后一行（或末段）为 `![封面](images/cover.png)`，其前是正文，其后无任何正文或元数据。
4. **无流水线元数据残留**：文件不含 `*第N轮 | 评分… | 人工化改写 | …*` 行。
5. **结构顺序断言**：`title → 正文(含3内文图) → 封面图`，与用户描述完全一致。
6. **下游兼容**：`publisher_service.py` 的 `convert_markdown_to_html` 仍能将首行 `# 标题` 渲染为 `<h1>`，并从 `state.outputs["generated_title"]` 单独取标题填发布框（不受影响，因 `generated_title` 取自 `best_title`，未改动其来源）。
7. **评分不退化**：以 `evaluation.py` 五维（事实/完整/结构/风格/去AI味）口径，修复后结构清晰度维度应提升（去除冗余标题与元数据噪声），其余维度不应因本次纯结构改动而下降；研究写作阈值 `RESEARCH_WRITE_PASS_THRESHOLD=80` 仍适用。

---

## 附：参考 A（包明说真实头条文）关键结构摘录

- frontmatter：`---` 内 `source/author/title/content_type/tab/collected_at`，`title: "“中国人不得买地！”美国第38个州通过新法案，中方回应一针见血"`。
- 正文**直接以段落开场白开头**（"如果告诉一百年前的美国人……"），无 `#` 文章标题、无图片标记（原始采集文无图）。
- 通篇包明说风格：强博主腔、第一人称观点、口语化、金句收尾（"而墙，从来都是自己砌的。"）。
- 启示：面向发布的稿件应是"干净正文 + 必要图片"，不夹带平台标签与流水线元数据。

---

## 补充修复 C：元数据正则通用化（2026-07-15 实测发现并修复）

### 背景
方案 §4.3 落地时，组装函数元数据剥离正则初版为 `r"\n*---\n*\*第[^\n]*轮 \| 评分[^\n]*\*"`（硬编码 `*第` 开头）。实测 S5 重跑发现：当 `generated_file` 指向 AI 原始稿（`*_ai_raw.md`）时，文末残留 `---` + `*AI 原始生成 | 第N轮 | 评分 | …*`。

### 根因
`write_stage.py` 有两处元数据写入（均前置 `---`）：
- `_save_outputs`（约 203–208 行）：写 AI 原始稿，格式 `*AI 原始生成 | 第{best_iteration}轮 | 评分{best_score} | {datetime}*`；当 `generated_file` 指向 ai_raw（人工化未启用或失败）时进入组装。
- `_apply_humanize_and_finalize`（284–288，仅 enable_humanize=True 且成功）：写人工化稿，格式 `*第{best_iteration}轮 | 评分{best_score} | 人工化改写 | {datetime}*`。
初版正则只覆盖后者（硬编码 `*第` 开头），漏剥前者。

### 修复（已实施，ui-minimal-change 执行）
`engine_app.py` 第 1449 行正则通用化为：
```python
content = re.sub(r"\n*---\n*\*[^*\n]*\*", "", content)
```
- 匹配 `---` 后紧跟的任意 `*...*` 元数据行，覆盖两种格式；
- 要求 `---` 前置，不误删正文引用块 `> *…*` 或孤立 `*强调*`。
`py_compile` 通过、`read_lints` 0 诊断。

### 验证（S5 重跑，真实产物）
文末为 `你怎么看？\n\n![封面](images/cover.png)`，无任何 `*...*` 元数据残留；话题标签（若有）亦被方案正文剥离；架构（标题/3 内文图/封面文末）完好。§5.4 验收第 4 条"无流水线元数据残留"现应理解为覆盖 `*AI 原始生成` 与 `*第N轮 | 人工化改写` 两种格式。
