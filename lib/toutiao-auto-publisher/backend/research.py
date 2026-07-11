"""
研究检索增强层 — 从 engine_app 的 Phase 3 抽出。

提供：网页搜索、关键词提取、研究上下文构建、精炼查询。
所有 UI 副作用（日志 / 进度）通过 log_fn / progress_fn 注入，
模块本身保持纯逻辑、可单测，不依赖 Streamlit。
"""
import sys as _sys


def search_web(query: str, max_results: int = 5) -> str:
    """使用百度 + 搜狗搜索，返回聚合的搜索结果摘要（纯文本）。

    策略：百度优先 → 搜狗 fallback → 返回空字符串。
    """
    from agent.search_engine import search_web as _do_search
    return _do_search(query, max_results=max_results)


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
    """根据上一轮评估反馈，生成精炼搜索关键词。"""
    if not feedback:
        return ""

    try:
        from ai_writer import AIWriter
        writer = AIWriter()
        prompt = (
            f"根据以下评估反馈和当前内容，提炼一个用于补充搜索的关键词短语（中文，10字以内）。"
            f"直接返回关键词，不要其他文字。\n\n"
            f"评价反馈: {feedback[:200]}\n"
            f"当前内容摘要: {content[:300]}"
        )
        return writer._call_ai(prompt, max_tokens=40, temperature=0.3).strip().strip("。，,.;;\"'")
    except Exception:
        pass
    return ""
