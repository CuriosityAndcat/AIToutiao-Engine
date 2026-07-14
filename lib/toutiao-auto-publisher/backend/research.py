"""
研究检索增强层 — 从 engine_app 的 Phase 3 抽出。

提供：网页搜索、关键词提取、研究上下文构建、精炼查询。
所有 UI 副作用（日志 / 进度）通过 log_fn / progress_fn 注入，
模块本身保持纯逻辑、可单测，不依赖 Streamlit。
"""
import sys as _sys
import re as _re


def _clean_search_noise(text: str) -> str:
    """过滤搜索结果中的 CSS/JS 代码噪声，保留自然语言内容。

    搜索引擎抓取时可能混入页面代码片段，在进入 Claim-Pipeline
    的 Extract 阶段前过滤，防止垃圾代码污染声明提取质量。
    """
    if not text:
        return text

    lines = text.split("\n")
    clean_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            clean_lines.append(line)
            continue

        # 1. 跳过纯 CSS 行（选择器 + 属性）
        if _re.match(r'^[.#]?[\w\-]+\s*\{', stripped):
            continue
        if _re.match(r'^\s*(background|color|font|margin|padding|border|display|position|width|height|top|left|right|bottom|z-index|overflow|opacity|transform|transition|animation|flex|grid)\s*:', stripped, _re.IGNORECASE):
            continue
        if stripped in ("{", "}", "};"):
            continue

        # 2. 跳过纯 JS/代码行
        if _re.match(r'^(function|var |let |const |if \(|for \(|while \(|return |console\.|document\.|window\.|\.addEventListener|\.querySelector)', stripped):
            continue
        if _re.match(r'^[a-zA-Z_$][\w$]*\s*=\s*', stripped) and ('(' in stripped or '{' in stripped):
            continue

        # 3. 跳过 HTML 注释
        if stripped.startswith("<!--") or stripped.startswith("//") or stripped.startswith("/*"):
            continue

        # 4. 跳过 URL-only 行
        if _re.match(r'^https?://', stripped) and len(stripped.split()) == 1:
            continue

        # 5. 跳过符号占比 > 70% 的行（非自然语言）
        alpha_chars = sum(1 for c in stripped if c.isalpha() or '\u4e00' <= c <= '\u9fff')
        if len(stripped) > 0 and alpha_chars / len(stripped) < 0.3:
            continue

        clean_lines.append(line)

    return "\n".join(clean_lines)


def search_web(query: str, max_results: int = 5) -> str:
    """使用百度 + 搜狗搜索，返回聚合的搜索结果摘要（纯文本）。

    策略：百度优先 → 搜狗 fallback → 返回空字符串。
    自动过滤 CSS/JS 代码噪声。
    """
    from agent.search_engine import search_web as _do_search
    raw = _do_search(query, max_results=max_results)
    return _clean_search_noise(raw)


def extract_key_topics(state) -> str:
    """从视频标题和转录文本中提取核心关键词/搜索查询词。"""
    title = state.outputs.get("video_title", "")
    transcript = state.outputs.get("transcript_text", "")

    # 组合可用文本
    source = title[:200] if title else ""
    if transcript:
        source += "\n" + transcript[:500]

    if not source.strip():
        return ""

    # 用 DeepSeek 提炼搜索关键词
    try:
        from ai_writer import AIWriter
        writer = AIWriter()
        prompt = (
            f"从以下视频内容中提取 1-3 个最核心的搜索关键词（中文），"
            f"用于在网络上查找相关背景资料。直接返回关键词，用逗号分隔，不要其他文字。\n\n"
            f"{source[:600]}"
        )
        keywords = writer._call_ai(prompt, max_tokens=60, temperature=0.3)
        return keywords.strip().strip("。，,.;;\"'")
    except Exception:
        pass

    # 回退：直接用标题作为搜索词
    if title:
        return title[:100]
    return source[:100]


def build_research_context(state, log_fn=print, progress_fn=None) -> str:
    """执行网页搜索，构建写作参考文献。返回聚合的研究上下文。

    log_fn(msg, level): 日志回调，默认 print
    progress_fn(pct: float): 进度回调，可空
    """
    keywords = extract_key_topics(state)
    if not keywords:
        _sys.stderr.write("[research] 无关键词，跳过搜索\n"); _sys.stderr.flush()
        return ""

    try:
        log_fn(f"🔍 搜索关键词: {keywords}", "info")
    except Exception:
        pass
    _sys.stderr.write(f"[research] 开始搜索: {keywords}\n"); _sys.stderr.flush()

    # 拆分多关键词分别搜索
    queries = [q.strip() for q in keywords.replace("，", ",").split(",") if q.strip()][:3]
    if not queries:
        queries = [keywords]

    all_results = []
    for q in queries:
        result = search_web(q, max_results=3)
        if result:
            all_results.append(f"### 搜索「{q}」结果:\n{result}")
        _sys.stderr.write(f"[research] 查询 '{q[:30]}...' → {len(result)} 字符\n"); _sys.stderr.flush()

    context = "\n\n".join(all_results)
    if context:
        try:
            log_fn(f"📚 搜集到 {len(all_results)} 组背景资料 ({len(context)} 字符)", "success")
        except Exception:
            pass
    else:
        try:
            log_fn("⚠️ 未搜集到有效网络资料，将仅基于视频文本生成", "warning")
        except Exception:
            pass

    if progress_fn:
        try:
            progress_fn(0.34)
        except Exception:
            pass
    return context


def extract_refined_query(content: str, feedback: str, state) -> str:
    """根据上一轮评估反馈，生成精炼搜索关键词。

    ⚠️ B-1 临时修复（B-2 Claim-Pipeline 后将被声明级搜索逻辑替代）：
    原有逻辑直接用反馈文本搜 → 搜"俄军送奶车伪装来源"等幻觉内容 → 死循环。
    修复：注入原始视频主题作为锚点，指示 LLM 忽略反馈中的具体编造细节，
    改为搜索该主题的「核心事实」方向（宽泛而非具体）。
    """
    if not feedback:
        return ""

    # 提取视频标题作为搜索锚点（防止被反馈中的幻觉细节带偏）
    video_title = ""
    try:
        video_title = state.outputs.get("video_title", "") or ""
    except Exception:
        pass

    try:
        from ai_writer import AIWriter
        writer = AIWriter()
        prompt = (
            f"评估员指出以下内容存在事实不符: {feedback[:200]}\n"
            f"原始视频主题: {video_title[:100]}\n"
            f"请忽略反馈中的具体细节描述，提炼1个关于该主题"
            f"「核心事实」的搜索词（中文，10字以内，宽泛而非具体）。"
            f"直接返回关键词，不要其他文字。"
        )
        return writer._call_ai(prompt, max_tokens=40, temperature=0.3).strip().strip("。，,.;;\"'")
    except Exception:
        pass
    return ""
