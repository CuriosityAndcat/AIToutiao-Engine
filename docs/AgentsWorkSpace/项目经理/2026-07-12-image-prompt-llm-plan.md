# 配图 Prompt LLM 驱动改造（方案 A 增强）

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 让 `engine_app.py` 网页流水线生成的配图，其 Prompt 质量对齐 Round 3 人工优化水平，复用已有的 DeepSeek LLM（`AIWriter`），不改动 Pollinations API 与任何依赖。

**架构：** 在 `step_images()` 中优先调用 DeepSeek LLM 根据文章内容生成结构化图片 Prompt（封面+2张内文），失败则回退到现有硬编码模板；下游 `_generate_pollinations_image()` 与图片注入逻辑完全不变。

**技术栈：** Python / OpenAI SDK（DeepSeek）/ Streamlit / Pollinations HTTP API（不变）

---

## 文件结构

- 修改：`engine_app.py`
  - 新增模块级常量：`_IMAGE_PROMPT_SYSTEM`、`_IMAGE_PROMPT_USER`
  - 新增函数：`_generate_image_prompts_via_llm()`、`_parse_llm_image_prompts()`
  - 修改函数：`step_images()`（Prompt 来源改为 LLM 优先 + fallback）
  - 保留函数：`_build_cover_prompt()`、`_build_inline_prompts()`（作为兜底，不删）

---

### 任务 1：新增 LLM Prompt 模板与生成函数

**文件：**
- 修改：`engine_app.py`（在 `_generate_pollinations_image()` 之后、`_build_cover_prompt()` 之前插入）

- [ ] **步骤 1：插入模块级常量与两个新函数**

```python
# ============================================================
# 配图 Prompt 生成（LLM 驱动，DeepSeek / Pollinations flux 优化）
# ============================================================

# 系统指令：专为 Pollinations/flux 模型优化（参考 design-image-prompt-engineer 角色设定）
_IMAGE_PROMPT_SYSTEM = """You are an expert AI image prompt engineer specializing in the Pollinations flux model.
Write English image prompts in natural, descriptive language for a Chinese military-news article.

Rules:
- Subject must be specific to the article (real equipment, place, or event). NEVER generic phrases like "military equipment".
- For maps/geopolitics: describe as "stylized satellite map illustration" and name the real regions (e.g. East Asia, Japan, China coast).
- Style: cinematic photorealism, war documentary aesthetic, dramatic lighting, professional news photography.
- Composition: keep the main subject and ALL visual interest in the TOP 85% of the frame; the bottom 15% must be empty dark space (reserved for cropping).
- Hard bans (write as natural negatives): without any text, without letters, without watermark, without logo, without cockpit close-up.
- Max 400 characters per prompt. Pure English. No explanations, no markdown."""

# 用户指令模板
_IMAGE_PROMPT_USER = """Article title: {title}
Article content (excerpt): {content}

Generate image prompts for this military news article:
- 1 COVER prompt: the single most striking visual representing the article's core subject.
- {inline_count} INLINE prompts: distinct supporting scenes (e.g. one geopolitical/map view, one equipment/formation view).

Return EXACTLY this format (one line each, no extra text):
COVER: <prompt>
INLINE_1: <prompt>
INLINE_2: <prompt>

Each prompt: natural English, under 400 characters, no text/watermark/logo, top-85% composition."""


def _generate_image_prompts_via_llm(title: str, content: str, count: int = 2) -> dict:
    """调用 DeepSeek LLM 生成配图 prompt（封面 + 内文）。

    返回 {'cover': str|None, 'inline': [str,...]}。
    任何异常（无 Key / 超时 / 解析失败）都向上抛出，由调用方 fallback 到硬编码模板。
    """
    from ai_writer import AIWriter

    inline_count = max(1, count)
    user_prompt = _IMAGE_PROMPT_USER.format(
        title=title[:80],
        content=content[:1500].replace("\n", " "),
        inline_count=inline_count,
    )

    writer = AIWriter()
    raw = writer._call_ai(
        user_prompt,
        system_prompt=_IMAGE_PROMPT_SYSTEM,
        max_tokens=800,
        temperature=0.7,
    )

    return _parse_llm_image_prompts(raw, count)


def _parse_llm_image_prompts(raw: str, count: int = 2) -> dict:
    """解析 LLM 输出为 {'cover': str|None, 'inline': [str,...]}。"""
    result = {"cover": None, "inline": []}
    if not raw:
        return result

    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.upper().startswith("COVER:"):
            result["cover"] = line.split(":", 1)[1].strip()[:500]
        elif line.upper().startswith("INLINE_"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                p = parts[1].strip()[:500]
                if p:
                    result["inline"].append(p)

    return result
```

- [ ] **步骤 2：运行语法检查**

运行：`python -c "import ast; ast.parse(open('engine_app.py', encoding='utf-8').read()); print('OK')"`
预期：输出 `OK`

- [ ] **步骤 3：Commit（可选，本地先行）**

```bash
git add engine_app.py
git commit -m "feat(images): 配图 Prompt 改为 DeepSeek LLM 驱动（flux 优化 + fallback）"
```

---

### 任务 2：修改 step_images() 接入 LLM

**文件：**
- 修改：`engine_app.py`（`step_images()` 函数内，约 1275-1296 行）

- [ ] **步骤 1：替换封面 Prompt 来源为 LLM 优先 + fallback**

找到：
```python
        # ── 1. 生成封面图 ──
        cover_prompt = _build_cover_prompt(title, content[:200])
        add_log(f"封面 prompt: {cover_prompt[:80]}...", "info")
```
替换为：
```python
        # ── 1. 生成配图 Prompt（优先 LLM，失败 fallback 硬编码）──
        llm_cover = None
        llm_inline = []
        try:
            _prompts = _generate_image_prompts_via_llm(title, content, count=2)
            llm_cover = _prompts.get("cover")
            llm_inline = _prompts.get("inline") or []
            add_log("配图 Prompt 由 DeepSeek LLM 生成（flux 优化）", "success")
        except Exception as _e:
            _sys.stderr.write(f"[images] LLM prompt 生成失败，使用 fallback: {_e}\n"); _sys.stderr.flush()
            add_log("LLM 配图 Prompt 生成失败，使用内置模板兜底", "warning")

        cover_prompt = llm_cover or _build_cover_prompt(title, content[:200])
        add_log(f"封面 prompt: {cover_prompt[:80]}...", "info")
```

- [ ] **步骤 2：替换内文 Prompt 来源为 LLM 优先 + fallback**

找到：
```python
        # ── 2. 生成内文配图 ──
        inline_prompts = _build_inline_prompts(title, content, count=2)
        add_log(f"计划生成 {len(inline_prompts)} 张内文配图", "info")
```
替换为：
```python
        # ── 2. 生成内文配图 ──
        inline_prompts = llm_inline if llm_inline else _build_inline_prompts(title, content, count=2)
        add_log(f"计划生成 {len(inline_prompts)} 张内文配图", "info")
```

- [ ] **步骤 3：运行语法检查**

运行：`python -c "import ast; ast.parse(open('engine_app.py', encoding='utf-8').read()); print('OK')"`
预期：输出 `OK`

- [ ] **步骤 4：Commit**

```bash
git add engine_app.py
git commit -m "feat(images): step_images 接入 LLM 配图 Prompt + 兜底回退"
```

---

## 质量门（本项目验收标准）

- 代码层：语法检查通过；`step_images` 在无 LLM Key 时仍能跑通（fallback 生效）
- 功能层：配置 DeepSeek Key 后，流水线日志出现 "配图 Prompt 由 DeepSeek LLM 生成"，且封面/内文 prompt 含文章具体实体（非 "military equipment" 泛化词）
- 不做：不改动 Pollinations API、不新增依赖、不改动图片注入逻辑
