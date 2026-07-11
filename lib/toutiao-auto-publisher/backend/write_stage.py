"""
研究-写作编排层 — 从 engine_app 的 Phase 3 抽出。

research_and_write 通过 PipelineHooks 注入日志/阶段/进度回调，
从而脱离 Streamlit 的 session_state，行为与原 _research_and_write 完全一致。
"""
import sys as _sys
import traceback
from dataclasses import dataclass
from typing import Callable, Optional
from datetime import datetime

from research import (
    build_research_context,
    extract_key_topics,
    extract_refined_query,
    search_web,
)
from evaluation import evaluate_content, QUALITY_PASS_THRESHOLD
from models import style_label as _style_label
from agent.guardrails import InputGuardrail, PolicyGuardrail, OutputGuardrail

MAX_RESEARCH_ITERATIONS = 3       # 最大研究-重写轮数


@dataclass
class PipelineHooks:
    """编排层与 UI 之间的解耦钩子。

    log_fn(msg, level): 日志回调，默认 print
    stage_fn(name, status): 阶段状态回调，可空
    progress_fn(pct: float): 进度回调，可空
    """
    log_fn: Callable[[str, str], None] = print
    stage_fn: Optional[Callable[[str, str], None]] = None
    progress_fn: Optional[Callable[[float], None]] = None


def research_and_write(state, hooks: Optional[PipelineHooks] = None) -> bool:
    """研究驱动的写作循环：搜索背景 → 生成 → 评估 → 迭代重写。

    替换原有的 step_write + step_humanize 独立调用，
    将两个阶段合并为一个智能迭代流程。
    最大迭代次数由 MAX_RESEARCH_ITERATIONS 控制。

    v2 增强：集成 WorkingMemory 跨轮次反思追踪。
    """
    hooks = hooks or PipelineHooks()

    def log(msg, level="info"):
        try:
            hooks.log_fn(msg, level)
        except Exception:
            pass

    def stage(name, status):
        if hooks.stage_fn:
            try:
                hooks.stage_fn(name, status)
            except Exception:
                pass

    def progress(p):
        if hooks.progress_fn:
            try:
                hooks.progress_fn(p)
            except Exception:
                pass

    from agent.memory import WorkingMemory

    _sys.stderr.write("[loop] ==== 研究-写作循环开始 (v2 WorkingMemory) ====\n"); _sys.stderr.flush()

    transcript = state.outputs.get("transcript_text", "")
    if not transcript:
        desc = state.outputs.get("video_description", "")
        title = state.outputs.get("video_title", "")
        transcript = f"标题：{title}\n\n{desc}" if (title or desc) else ""
        if not transcript:
            log("没有转录文本，无法生成内容", "error")
            stage("研究写作", "failed")
            return False

    _sys.stderr.write(f"[loop] 输入文本: {len(transcript)} 字符\n"); _sys.stderr.flush()

    # ── 0.0 输入护栏：检查转录文本是否包含越狱/违规指令 ──
    _in_res = InputGuardrail().check(transcript)
    if not _in_res.passed:
        log(f"输入护栏拦截: {_in_res.reason}", "error")
        stage("研究写作", "failed")
        return False

    # ── 0. 执行前研究：提取关键词并搜索 ──
    stage("研究写作", "running")
    log("阶段3/5: 网络研究 + AI 写作（含质量评估迭代）", "stage")

    # 初始化 WorkingMemory（跨轮次反思累积）
    task_desc = f"为视频《{state.outputs.get('video_title', '')}》写{state.content_type}，风格={state.content_style}"
    wm = WorkingMemory(task=task_desc, max_iterations=MAX_RESEARCH_ITERATIONS)
    wm.search_context = ""  # 将在各轮中累积

    research_context = build_research_context(state, log_fn=log, progress_fn=progress)
    all_research_notes = [research_context] if research_context else []
    # 跟踪每轮搜索关键词（用于 UI 展示）
    search_queries_by_iter = []  # [(iteration, query_str), ...]
    if research_context:
        search_queries_by_iter.append((1, extract_key_topics(state) or "初始关键词"))

    # 构建增强后的写作主题
    base_topic = transcript[:2000]
    enhanced_topic = base_topic
    if research_context:
        enhanced_topic = (
            f"【视频原文摘要】\n{base_topic}\n\n"
            f"【网络背景资料（供事实参考）】\n{research_context[:1500]}"
        )

    log(f"输入文本: {len(transcript)} 字符", "info")
    log(f"风格: {state.content_style}", "info")
    progress(0.35)

    best_content = ""
    best_title = ""
    best_score = 0
    best_iteration = 0
    eval_records = []

    # ── 迭代循环 ──
    for iteration in range(1, MAX_RESEARCH_ITERATIONS + 1):
        _sys.stderr.write(f"[loop] 第 {iteration}/{MAX_RESEARCH_ITERATIONS} 轮\n"); _sys.stderr.flush()

        if iteration == 1:
            topic = enhanced_topic
            log(f"📝 第 1 轮：使用网络研究资料生成初稿", "info")
        else:
            # 后续轮次：根据评估反馈，重新搜索并补充资料
            log(f"🔄 第 {iteration} 轮：根据评估反馈重新搜索...", "info")

            # 根据上次评估反馈调整搜索关键词
            last_feedback = eval_records[-1].get("feedback", "") if eval_records else ""
            refine_query = extract_refined_query(best_content, last_feedback, state)
            if refine_query:
                log(f"🔍 精炼搜索: {refine_query[:60]}...", "info")
                search_queries_by_iter.append((iteration, refine_query))
                new_context = search_web(refine_query, max_results=5)
                if new_context:
                    all_research_notes.append(new_context)
                    wm.search_context = f"{wm.search_context}\n[第{iteration}轮] {new_context[:500]}".strip()
                    log(f"📚 补充 {len(new_context)} 字符背景资料", "info")

            # 重新构建增强主题（注入累积反思）
            cumulative_context = "\n\n---\n\n".join(all_research_notes[-2:])  # 最近2轮研究
            wm_prompt = wm.to_prompt() if wm.reflections else ""
            topic = (
                f"【视频原文摘要】\n{transcript[:2000]}\n\n"
                f"【网络背景资料（累计研究）】\n{cumulative_context[:2000]}"
            )
            if wm_prompt:
                topic += f"\n\n【历史改进要求（请逐一修复）】\n{wm_prompt}"

        # ── 1. 调用 AI 写作 ──
        try:
            from ai_writer import AIWriter
            from models import ContentType as _CT, ContentStyle as _CS

            writer = AIWriter()
            cs = state.content_style
            if _CS and isinstance(cs, str):
                try:
                    cs = _CS(cs)
                except ValueError:
                    cs = _CS.GENERAL

            if _CT is not None:
                if state.content_type == "article":
                    ct = _CT.ARTICLE
                else:
                    ct = _CT.TOUTIE
                result = writer.generate(
                    topic=topic,
                    content_type=ct,
                    content_style=cs if state.content_type == "toutie" else None,
                    max_chars=2000 if state.content_type == "article" else 1200,
                )
            else:
                if state.content_type == "article":
                    result = writer.generate(
                        topic=topic, content_type="article", max_chars=2000,
                    )
                else:
                    result = writer.generate(
                        topic=topic, content_type="toutie",
                        content_style=cs, max_chars=1200,
                    )
        except Exception as e:
            log(f"AI 写作异常（第{iteration}轮）: {e}", "error")
            traceback.print_exc()
            if iteration == MAX_RESEARCH_ITERATIONS:
                stage("研究写作", "failed")
                return False
            continue

        title = result.get("title", "")
        content = result.get("content", "")
        char_count = result.get("char_count", len(content))

        if not content or len(content) < 50:
            log(f"第{iteration}轮内容过短，跳过", "warning")
            eval_records.append({"feedback": "内容过短，需扩充"})
            continue

        # ── 2. 如果需要人工化，先不改写，先评估原始质量 ──
        _sys.stderr.write(f"[loop] 第{iteration}轮: {char_count} 字符\n"); _sys.stderr.flush()

        # ── 3. 质量评估 ──
        log(f"📊 第{iteration}轮质量评估中...", "info")
        style_label = _style_label(state.content_style)
        eval_result = evaluate_content(content, title, style_label, research_context)
        eval_records.append(eval_result)

        score = eval_result["score"]
        feedback = eval_result["feedback"]
        passed = eval_result["passed"]
        dimensions = eval_result.get("dimensions", {})

        log(
            f"第{iteration}轮评估: 综合分={score}/100 | {'✅ 通过' if passed else '❌ 需改进'}",
            "success" if passed else "warning",
        )
        if feedback:
            log(f"评估反馈: {feedback[:100]}", "info")
        if dimensions:
            dim_summary = " | ".join(f"{k}={v}" for k, v in dimensions.items())
            log(f"分维度: {dim_summary}", "info")

        # ── 记录反思到 WorkingMemory（跨轮次累积）──
        wm.add_reflection(f"[第{iteration}轮 评分={score}] {feedback}")
        wm.iterations = iteration

        # 记录最佳结果
        if score > best_score:
            best_score = score
            best_content = content
            best_title = title
            best_iteration = iteration

        # 检查是否达标
        if passed:
            _sys.stderr.write(f"[loop] 第{iteration}轮通过，停止迭代\n"); _sys.stderr.flush()
            break
        else:
            if iteration < MAX_RESEARCH_ITERATIONS:
                log(f"准备第{iteration + 1}轮重写...", "info")
                progress(0.35 + iteration * 0.03)

    # ── 4. 使用最佳结果 ──
    if not best_content:
        log("所有轮次均未生成有效内容", "error")
        stage("研究写作", "failed")
        return False

    content = best_content
    title = best_title

    # ── 3.5 输出护栏：政策合规 + 输出质量下限 ──
    _policy_res = PolicyGuardrail().check(content)
    if not _policy_res.passed and _policy_res.severity == "error":
        log(f"输出护栏拦截（政策合规）: {_policy_res.reason}", "error")
        stage("研究写作", "failed")
        return False
    if not _policy_res.passed:
        log(f"输出护栏警告: {_policy_res.reason}", "warning")
    _out_res = OutputGuardrail().check(content)
    if not _out_res.passed:
        log(f"输出护栏提示: {_out_res.reason}", "warning")

    log(
        f"✅ 研究-写作完成: 第{best_iteration}轮最佳, 评分={best_score}/100, "
        f"共{len(all_research_notes)}组网络资料",
        "success",
    )

    # 保存 AI 原始版本
    prefix = "微头条" if state.content_type == "toutie" else "文章"
    raw_file = state.run_dir / f"{prefix}_{state.run_id}_ai_raw.md"
    research_log = state.run_dir / f"{prefix}_{state.run_id}_research.md"
    raw_file.write_text(
        f"# {title}\n\n{content}\n\n---\n"
        f"*AI 原始生成 | 第{best_iteration}轮 | 评分{best_score} | {datetime.now().isoformat()}*",
        encoding="utf-8",
    )

    # 保存研究笔记
    research_notes_content = "\n\n---\n\n".join(
        f"## 第{i+1}次研究\n{r}" for i, r in enumerate(all_research_notes) if r
    )
    if research_notes_content:
        research_log.write_text(
            f"# 研究笔记\n\n{research_notes_content}\n\n---\n"
            f"| 迭代 | 评分 | 反馈 |\n|------|------|------|\n" +
            "\n".join(
                f"| 第{i+1}轮 | {r.get('score', '?')} | {r.get('feedback', '')[:50]} |"
                for i, r in enumerate(eval_records)
            ),
            encoding="utf-8",
        )

    state.outputs["generated_title"] = title
    state.outputs["generated_content"] = content
    state.outputs["generated_file"] = str(raw_file)
    state.outputs["char_count"] = len(content)
    state.outputs["research_notes"] = all_research_notes
    state.outputs["eval_records"] = [
        {
            "iteration": i + 1,
            "score": r["score"],
            "passed": r.get("passed", r["score"] >= QUALITY_PASS_THRESHOLD),
            "dimensions": r.get("dimensions", {}),
            "feedback": r.get("feedback", ""),
            "search_queries": [
                q for it, q in search_queries_by_iter if it == i + 1
            ],
        }
        for i, r in enumerate(eval_records)
    ]
    state.outputs["best_iteration"] = best_iteration
    state.outputs["best_score"] = best_score

    state.mark_done("write")
    progress(0.45)

    # ── 5. 人工化改写（如果启用，内嵌于研究写作阶段） ──
    if state.enable_humanize:
        log("→ 人工化改写（去 AI 味）...", "stage")
        progress(0.48)

        try:
            from ai_writer import AIWriter
            writer = AIWriter()
            result = writer.humanize(content)
            humanized = result["content"]
            h_char_count = result["char_count"]

            # 对人工化结果也做一次轻量评估（仅检查是否有严重退化）
            h_eval = evaluate_content(humanized, title, _style_label(state.content_style))
            if h_eval["score"] < best_score - 20:
                log(
                    f"人工化后质量下降（{best_score}→{h_eval['score']}），保留最佳版本",
                    "warning",
                )
            else:
                _h_policy = PolicyGuardrail().check(humanized)
                if not _h_policy.passed and _h_policy.severity == "error":
                    log(f"人工化结果触发政策合规拦截，保留 AI 原文: {_h_policy.reason}", "warning")
                else:
                    content = humanized
                    log(f"人工化改写完成 ({h_char_count} 字符)", "success")

            # 保存人工化版本
            output_file = state.run_dir / f"{prefix}_{state.run_id}.md"
            output_file.write_text(
                f"# {title}\n\n{content}\n\n---\n"
                f"*第{best_iteration}轮 | 评分{best_score} | 人工化改写 | {datetime.now().isoformat()}*",
                encoding="utf-8",
            )

            state.outputs["humanized_content"] = content
            state.outputs["generated_content"] = content
            state.outputs["generated_file"] = str(output_file)
            state.outputs["humanized_file"] = str(output_file)
            state.outputs["char_count"] = len(content)

        except Exception as e:
            log(f"人工化改写失败（保留 AI 原文）: {e}", "warning")

        state.mark_done("humanize")
        progress(0.55)
    else:
        log("跳过人工化改写（未启用）", "info")
        state.mark_done("humanize")

    # ── 6. 输出最终报告 ──
    log(
        f"🏁 研究-写作循环完成 | 最佳轮次: 第{best_iteration}轮 | "
        f"评分: {best_score}/100 | 网络资料: {len(all_research_notes)}组",
        "success",
    )

    _sys.stderr.write(
        f"[loop] ==== 循环结束 ==== best_round={best_iteration} "
        f"score={best_score} research_groups={len(all_research_notes)}\n"
    ); _sys.stderr.flush()

    return True
