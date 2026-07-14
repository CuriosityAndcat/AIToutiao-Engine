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
import re

from research import (
    build_research_context,
    extract_key_topics,
    extract_refined_query,
    search_web,
)
from evaluation import evaluate_content, QUALITY_PASS_THRESHOLD
from models import style_label as _style_label
from agent.guardrails import InputGuardrail, PolicyGuardrail, OutputGuardrail

MAX_RESEARCH_ITERATIONS = 10      # 最大研究-重写轮数（Claim-Pipeline 模式建议 5）
RESEARCH_WRITE_PASS_THRESHOLD = 80  # 研究-写作阶段完成线（高于通用 75）
CLAIM_PIPELINE_ENABLED = False      # B-2 开发完成为 True。False 时走原路径（旧模式保留为降级 fallback）

# Claim-Pipeline 专用常量
_CP_MAX_ITERATIONS = 5              # Claim-Pipeline 模式最大迭代轮数
_CP_MIN_COVERAGE = 0.7              # 进入 Compose 阶段的最低来源覆盖率
_CP_MAX_EMPTY_SEARCHES = 3          # 连续空搜索结果数上限（触发降级）

# ── 事实边界指令 — 用户层精简提醒（系统级 _FACT_BOUNDARY_SYSTEM 已在 ai_writer 层注入） ──
_FACT_BOUNDARY_INSTRUCTION = (
    "【事实提醒】请严格基于下方来源写作，不编造不存在的信息（日期/人名/协议名/数字）。\n\n"
)


def _fallback_title(video_title: str) -> str:
    """短视频标题兜底：清洗平台标签前缀，避免微头条缺失标题。

    当 LLM 未返回标题（极端情况）时，回退使用清洗后的原始短视频标题，
    保证 state.generated_title 永不为空（根治缺标题缺陷）。
    """
    if not video_title:
        return ""
    t = video_title
    for _p in ("抖音独家", "快手独家", "头条独家", "独家"):
        if t.startswith(_p):
            t = t[len(_p):]
    t = t.replace("___", " ").replace("_", " ").strip()
    t = re.sub(r"[【\[].*?[\]】]", "", t).strip()  # 去掉方括号标签
    return t or video_title.strip()


def _build_fact_fix_block(last_eval_record: dict) -> str:
    """当上一轮事实准确性是瓶颈时，生成针对性矫正块。

    只在「事实准确」维度 < 85 时触发（说明 LLM 在编造事实），
    生成一个高优先级的矫正指令，要求严格只使用已有资料。
    """
    dims = last_eval_record.get("dimensions", {})
    feedback = last_eval_record.get("feedback", "")
    fact_score = dims.get("事实准确", 100)

    if fact_score >= 85:
        return ""  # 事实准确度 OK，不需要额外矫正

    return (
        f"\n\n【事实矫正 — 上一轮问题必须修复】\n"
        f"上一轮事实准确性仅 {fact_score} 分，评估指出以下事实问题：\n"
        f"{feedback[:400]}\n\n"
        f"本轮重写铁律：\n"
        f"- 严禁编造任何日期、人名、地名、协议名称\n"
        f"- 不确定的信息用\"据报道\"\"据媒体披露\"\"有消息称\"标记\n"
        f"- 如果资料不包含某个细节，就不要写那个细节\n"
    )


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


# ═══════════════════════════════════════════════════════════════
# Claim-Pipeline 模式（B-2 新增）
# ═══════════════════════════════════════════════════════════════

def _research_and_write_claim_pipeline(state, hooks, log, stage, progress) -> bool:
    """Claim-Pipeline 模式：四阶段事实锚定写作循环。

    单轮流程：Extract → Ground → Merge → Compose → Evaluate
    声明池跨迭代累积，Merge 步骤保留历史 CONFIRMED 声明。
    """
    from agent.memory import WorkingMemory
    from fact_pipeline import (
        extract_claims, verify_claims, merge_claims,
        ClaimsPool, generate_knowledge_gap_query,
    )

    transcript = state.outputs.get("transcript_text", "")
    raw_video_title = state.outputs.get("video_title", "")
    if not transcript:
        desc = state.outputs.get("video_description", "")
        transcript = f"标题：{raw_video_title}\n\n{desc}" if (raw_video_title or desc) else ""
        if not transcript:
            log("没有转录文本，无法生成内容", "error")
            stage("研究写作", "failed")
            return False

    # 输入护栏
    _in_res = InputGuardrail().check(transcript)
    if not _in_res.passed:
        log(f"输入护栏拦截: {_in_res.reason}", "error")
        stage("研究写作", "failed")
        return False

    stage("研究写作", "running")
    log("阶段3/5: Claim-Pipeline 事实锚定写作（四阶段）", "stage")

    # WorkingMemory
    task_desc = f"为视频《{raw_video_title}》写{state.content_type}，风格={state.content_style} (Claim-Pipeline)"
    wm = WorkingMemory(task=task_desc, max_iterations=_CP_MAX_ITERATIONS)
    wm.search_context = ""

    # 初始搜索
    research_context = build_research_context(state, log_fn=log, progress_fn=progress)
    all_research_notes = [research_context] if research_context else []
    empty_search_count = 0  # 连续空搜索计数

    log(f"输入文本: {len(transcript)} 字符", "info")
    log(f"风格: {state.content_style}", "info")
    progress(0.35)

    best_content = ""
    best_title = ""
    best_score = 0
    best_iteration = 0
    best_pool: Optional[ClaimsPool] = None
    eval_records = []

    # 获取 LLM 调用函数（依赖注入）
    from ai_writer import AIWriter
    from models import ContentStyle as _CS
    writer = AIWriter()
    llm_call = writer._call_ai

    # 风格解析
    cs = state.content_style
    if isinstance(cs, str):
        try:
            cs = _CS(cs)
        except ValueError:
            cs = _CS.BAOMING_SHUO

    history_pool: Optional[ClaimsPool] = None  # 跨迭代累积

    for iteration in range(1, _CP_MAX_ITERATIONS + 1):
        _sys.stderr.write(f"[cp] 第 {iteration}/{_CP_MAX_ITERATIONS} 轮\n"); _sys.stderr.flush()
        log(f"📝 第 {iteration} 轮: Extract → Ground → Compose", "info")

        cumulative_research = "\n\n---\n\n".join(all_research_notes[-3:])

        # ── 同轮内 Extract→Ground 循环 ──
        # 覆盖率不足时补充搜索 + 重试 Extract/Ground（不消耗迭代轮次）
        _cp_coverage_retries = 0
        _CP_MAX_COVERAGE_RETRIES = 3  # 同轮内最多补充搜索次数
        verified_claims = []
        coverage = 0.0

        while True:
            # ── 阶段 1: Extract ──
            log("  阶段1: 提取原子事实声明...", "info")
            claims = extract_claims(cumulative_research, transcript, llm_call)
            if not claims:
                log("  ⚠️ 阶段1 提取失败，降级为 V2 模式", "warning")
                return _fallback_v2_mode(state, hooks, log, stage, progress, transcript,
                                         raw_video_title, research_context, all_research_notes)

            log(f"  提取 {len(claims)} 条声明", "info")

            # ── 阶段 2: Ground ──
            log("  阶段2: 比对来源验证声明...", "info")
            verified_claims, coverage = verify_claims(claims, cumulative_research, llm_call)
            confirmed_count = sum(1 for v in verified_claims if v.status == "CONFIRMED")
            partial_count = sum(1 for v in verified_claims if v.status == "PARTIAL")
            log(f"  验证结果: CONFIRMED={confirmed_count}, PARTIAL={partial_count}, "
                f"覆盖率={coverage:.0%}", "info")

            # ── 覆盖率达标 → 跳出内循环，进入 Merge → Compose ──
            if coverage >= _CP_MIN_COVERAGE:
                break

            # ── 覆盖率不足 ──
            _cp_coverage_retries += 1
            log(f"  覆盖率 {coverage:.0%} < {_CP_MIN_COVERAGE:.0%}，补充搜索 "
                f"(同轮内第{_cp_coverage_retries}次)...", "warning")

            # 覆盖率极低保护（同轮内 2 次重试后仍 < 50% → 降级）
            if coverage < 0.5 and _cp_coverage_retries >= 2:
                log(f"  覆盖率持续极低 ({coverage:.0%})，使用已有声明降级 Compose", "warning")
                break

            # 重试次数上限
            if _cp_coverage_retries >= _CP_MAX_COVERAGE_RETRIES:
                log(f"  同轮内 {_cp_coverage_retries} 次补充搜索后覆盖率仍不足，降级 Compose", "warning")
                break

            # 根据声明池缺口生成搜索词
            temp_pool = merge_claims(verified_claims, None)
            gap_query = generate_knowledge_gap_query(temp_pool, raw_video_title, llm_call)

            if gap_query:
                log(f"  🔍 补充搜索: {gap_query[:60]}", "info")
                new_context = search_web(gap_query, max_results=5)
                if new_context:
                    all_research_notes.append(new_context)
                    empty_search_count = 0
                    log(f"  📚 补充 {len(new_context)} 字符资料", "info")
                    # 更新 cumulative_research 以纳入新资料
                    cumulative_research = "\n\n---\n\n".join(all_research_notes[-3:])
                else:
                    empty_search_count += 1
                    log(f"  ⚠️ 搜索无结果 ({empty_search_count}/{_CP_MAX_EMPTY_SEARCHES})", "warning")
            else:
                empty_search_count += 1

            # 搜索限流保护
            if empty_search_count >= _CP_MAX_EMPTY_SEARCHES:
                log(f"  ⚠️ 连续 {_CP_MAX_EMPTY_SEARCHES} 次搜索无结果，降级 Compose", "warning")
                break

        # ── 阶段 2.5: Merge ──
        log("  阶段2.5: 跨迭代声明合并...", "info")
        pool = merge_claims(verified_claims, history_pool)
        history_pool = pool  # 累积
        log(f"  声明池: CONFIRMED={len(pool.confirmed)}, PARTIAL={len(pool.partial)}, "
            f"覆盖率={pool.coverage:.0%}", "info")

        # 记录声明级反思到 WorkingMemory
        unverified = [v for v in verified_claims if v.status == "UNVERIFIED"]
        if unverified:
            wm.unverified_claims = [f"claim_{v.id}" for v in unverified[:5]]
        if pool.coverage < 0.8:
            wm.knowledge_gaps = [f"覆盖率仅{pool.coverage:.0%}，主题={raw_video_title[:30]}"]

        # ── 阶段 3: Compose ──
        log(f"  阶段3: 从声明池写作 ({len(pool.confirmed)} 确定 + {len(pool.partial)} 部分)...", "info")
        result = writer.compose_from_claims(
            claims_pool=pool,
            style=cs,
            transcript=transcript,
            max_chars=1200,
        )

        title = (result.get("title", "") or "").strip() or _fallback_title(raw_video_title)
        content = result.get("content", "")
        char_count = result.get("char_count", len(content))

        if not content or len(content) < 50:
            log(f"  内容过短，跳过", "warning")
            eval_records.append({"feedback": "内容过短，需扩充", "score": 0})
            continue

        # ── 阶段 4: Evaluate ──
        log(f"📊 第 {iteration} 轮质量评估中...", "info")
        style_label = _style_label(cs)
        cumulative_for_eval = "\n\n---\n\n".join(all_research_notes[-3:]) if all_research_notes else research_context
        eval_result = evaluate_content(
            content, title, style_label, cumulative_for_eval,
            threshold=RESEARCH_WRITE_PASS_THRESHOLD,
            claims_pool_summary=pool.summary(),
        )
        eval_records.append(eval_result)

        score = eval_result["score"]
        feedback = eval_result["feedback"]
        passed = eval_result["passed"]
        dimensions = eval_result.get("dimensions", {})

        log(
            f"第 {iteration} 轮评估: 综合分={score}/100 | "
            f"{'✅ 通过' if passed else '❌ 需改进'}",
            "success" if passed else "warning",
        )
        if dimensions:
            dim_summary = " | ".join(f"{k}={v}" for k, v in dimensions.items())
            log(f"分维度: {dim_summary}", "info")

        # 记录反思
        wm.add_reflection(f"[第{iteration}轮 评分={score}] {feedback}")
        wm.iterations = iteration

        # 记录最佳结果
        if score > best_score:
            best_score = score
            best_content = content
            best_title = title
            best_iteration = iteration
            best_pool = pool

        # 达标 → 结束
        if passed:
            _sys.stderr.write(f"[cp] 第{iteration}轮通过，停止迭代\n"); _sys.stderr.flush()
            break
        else:
            if iteration < _CP_MAX_ITERATIONS:
                log(f"准备第{iteration + 1}轮...", "info")
                progress(0.35 + iteration * 0.04)

    # ── 4. 输出处理（与现有逻辑保持一致）──
    if not best_content:
        log("所有轮次均未生成有效内容", "error")
        stage("研究写作", "failed")
        return False

    content = best_content
    title = best_title

    # 输出护栏
    _policy_res = PolicyGuardrail().check(content)
    if not _policy_res.passed and _policy_res.severity == "error":
        log(f"输出护栏拦截: {_policy_res.reason}", "error")
        stage("研究写作", "failed")
        return False
    if not _policy_res.passed:
        log(f"输出护栏警告: {_policy_res.reason}", "warning")
    _out_res = OutputGuardrail().check(content)
    if not _out_res.passed:
        log(f"输出护栏提示: {_out_res.reason}", "warning")

    log(
        f"✅ 研究-写作完成(Claim-Pipeline): 第{best_iteration}轮最佳, 评分={best_score}/100",
        "success",
    )

    # 保存文件
    prefix = "微头条" if state.content_type == "toutie" else "文章"
    raw_file = state.run_dir / f"{prefix}_{state.run_id}_ai_raw.md"
    research_log = state.run_dir / f"{prefix}_{state.run_id}_research.md"
    raw_file.write_text(
        f"# {title}\n\n{content}\n\n---\n"
        f"*Claim-Pipeline | 第{best_iteration}轮 | 评分{best_score} | "
        f"{datetime.now().isoformat()}*",
        encoding="utf-8",
    )
    research_notes_content = "\n\n---\n\n".join(
        f"## 第{i+1}次研究\n{r}" for i, r in enumerate(all_research_notes) if r
    )
    if research_notes_content:
        research_log.write_text(
            f"# 研究笔记 (Claim-Pipeline)\n\n{research_notes_content}\n\n---\n"
            f"| 迭代 | 评分 | 覆盖 | 反馈 |\n|------|------|------|------|\n" +
            "\n".join(
                f"| 第{i+1}轮 | {r.get('score', '?')} | {best_pool.coverage if best_pool else '?'} | {r.get('feedback', '')[:50]} |"
                for i, r in enumerate(eval_records)
            ),
            encoding="utf-8",
        )

    state.outputs["generated_title"] = title
    state.outputs["generated_content"] = content
    state.outputs["generated_file"] = str(raw_file)
    state.outputs["char_count"] = len(content)
    state.outputs["research_notes"] = all_research_notes
    state.outputs["claim_pipeline"] = True
    state.outputs["eval_records"] = [
        {
            "iteration": i + 1,
            "score": r.get("score", 0),
            "passed": r.get("passed", False),
            "dimensions": r.get("dimensions", {}),
            "feedback": r.get("feedback", ""),
        }
        for i, r in enumerate(eval_records)
    ]
    state.outputs["best_iteration"] = best_iteration
    state.outputs["best_score"] = best_score

    progress(0.45)

    # 人工化（与现有逻辑一致）
    if state.enable_humanize:
        log("→ 人工化改写（去 AI 味）...", "stage")
        progress(0.48)
        try:
            result = writer.humanize(content, content_style=cs)
            humanized = result["content"]
            h_eval = evaluate_content(
                humanized, title, _style_label(cs),
                claims_pool_summary=best_pool.summary() if best_pool else "",
            )
            if h_eval["score"] < best_score - 20:
                log(f"人工化后质量下降，保留最佳版本", "warning")
            else:
                _h_policy = PolicyGuardrail().check(humanized)
                if not _h_policy.passed and _h_policy.severity == "error":
                    log(f"人工化结果触发护栏拦截", "warning")
                else:
                    content = humanized
                    log(f"人工化完成 ({len(content)} 字符)", "success")
            output_file = state.run_dir / f"{prefix}_{state.run_id}.md"
            output_file.write_text(
                f"# {title}\n\n{content}\n\n---\n"
                f"*Claim-Pipeline 第{best_iteration}轮 | 评分{best_score} | "
                f"人工化 | {datetime.now().isoformat()}*",
                encoding="utf-8",
            )
            state.outputs["generated_content"] = content
            state.outputs["generated_file"] = str(output_file)
        except Exception as e:
            log(f"人工化失败: {e}", "warning")
        state.mark_done("humanize")
    else:
        state.mark_done("humanize")

    # 严格完成校验
    if best_score < RESEARCH_WRITE_PASS_THRESHOLD:
        log(f"❌ 未达标: {best_score} < {RESEARCH_WRITE_PASS_THRESHOLD}", "error")
        stage("研究写作", "failed")
        return False

    state.mark_done("write")
    stage("研究写作", "done")
    log(f"🏁 Claim-Pipeline 完成 | 最佳: 第{best_iteration}轮 | 评分: {best_score}/100", "success")
    return True


def _fallback_v2_mode(state, hooks, log, stage, progress, transcript,
                      raw_video_title, research_context, all_research_notes) -> bool:
    """Claim-Pipeline 降级：回到 V2 单次 generate_toutie() + 事实边界模式。

    当阶段 1 Extract 返回 0 条声明时触发。
    """
    log("→ 降级为 V2 模式（单次写作 + 事实边界，质量门 85）", "warning")
    from ai_writer import AIWriter
    from models import ContentStyle as _CS

    writer = AIWriter()
    cs = None
    try:
        cs_raw = getattr(state, 'content_style', 'baoming_shuo')
        cs = _CS(str(cs_raw)) if cs_raw else _CS.BAOMING_SHUO
    except Exception:
        cs = _CS.BAOMING_SHUO

    enhanced_topic = (
        _FACT_BOUNDARY_INSTRUCTION +
        f"【视频原文摘要】\n{transcript[:2000]}\n\n"
        f"【网络背景资料】\n{research_context[:1500]}" if research_context
        else _FACT_BOUNDARY_INSTRUCTION + transcript[:2000]
    )

    result = writer.generate_toutie(enhanced_topic, 1200, cs)
    title = (result.get("title", "") or "").strip() or _fallback_title(raw_video_title)
    content = result.get("content", "")

    if not content or len(content) < 50:
        stage("研究写作", "failed")
        return False

    eval_result = evaluate_content(content, title, _style_label(cs), research_context, threshold=85)
    score = eval_result["score"]

    prefix = "微头条" if state.content_type == "toutie" else "文章"
    raw_file = state.run_dir / f"{prefix}_{state.run_id}_ai_raw.md"
    raw_file.write_text(
        f"# {title}\n\n{content}\n\n---\n"
        f"*Claim-Pipeline 降级 V2 | 评分{score} | {datetime.now().isoformat()}*",
        encoding="utf-8",
    )

    state.outputs["generated_title"] = title
    state.outputs["generated_content"] = content
    state.outputs["generated_file"] = str(raw_file)
    state.outputs["char_count"] = len(content)
    state.outputs["best_score"] = score

    if score >= 85:
        state.mark_done("write")
        stage("研究写作", "done")
        return True
    else:
        log(f"降级 V2 模式仍未达标: {score} < 85", "error")
        stage("研究写作", "failed")
        return False


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

    # ── Claim-Pipeline 模式分发 ──
    if CLAIM_PIPELINE_ENABLED:
        return _research_and_write_claim_pipeline(
            state, hooks, log, stage, progress,
        )

    transcript = state.outputs.get("transcript_text", "")
    raw_video_title = state.outputs.get("video_title", "")  # 原始短视频标题，作标题兜底源
    if not transcript:
        desc = state.outputs.get("video_description", "")
        title = raw_video_title
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
    enhanced_topic = _FACT_BOUNDARY_INSTRUCTION + base_topic
    if research_context:
        enhanced_topic = (
            _FACT_BOUNDARY_INSTRUCTION +
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

            # 重新构建增强主题（注入累积反思 + 事实边界 + 事实矫正）
            cumulative_context = "\n\n---\n\n".join(all_research_notes[-3:])  # 最近3轮研究
            wm_prompt = wm.to_prompt() if wm.reflections else ""
            # 事实矫正块：只在上一轮事实准确性 < 85 时注入
            last_eval = eval_records[-1] if eval_records else {}
            fact_fix_block = _build_fact_fix_block(last_eval)
            topic = (
                _FACT_BOUNDARY_INSTRUCTION +
                f"【视频原文摘要】\n{transcript[:2000]}\n\n"
                f"【网络背景资料（累计研究）】\n{cumulative_context[:2000]}"
            )
            if fact_fix_block:
                topic += fact_fix_block
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

        # 标题：优先用 LLM 生成的标题；为空时回退清洗后的短视频标题（根治缺标题）
        title = (result.get("title", "") or "").strip() or _fallback_title(raw_video_title)
        content = result.get("content", "")
        char_count = result.get("char_count", len(content))

        if not content or len(content) < 50:
            log(f"第{iteration}轮内容过短，跳过", "warning")
            eval_records.append({"feedback": "内容过短，需扩充"})
            continue

        # ── 2. 如果需要人工化，先不改写，先评估原始质量 ──
        _sys.stderr.write(f"[loop] 第{iteration}轮: {char_count} 字符\n"); _sys.stderr.flush()

        # ── 3. 质量评估 ──
        log(f"📊 第 {iteration} 轮质量评估中...", "info")
        style_label = _style_label(state.content_style)
        # 用累积研究上下文（最近3轮）做事实校验，而非仅首轮
        cumulative_for_eval = "\n\n---\n\n".join(all_research_notes[-3:]) if all_research_notes else research_context
        eval_result = evaluate_content(
            content, title, style_label, cumulative_for_eval,
            threshold=RESEARCH_WRITE_PASS_THRESHOLD,
        )
        eval_records.append(eval_result)

        score = eval_result["score"]
        feedback = eval_result["feedback"]
        passed = eval_result["passed"]
        dimensions = eval_result.get("dimensions", {})
        used_threshold = eval_result.get("threshold", RESEARCH_WRITE_PASS_THRESHOLD)

        log(
            f"第 {iteration} 轮评估: 综合分={score}/100 | 阈值={used_threshold} | {'✅ 通过' if passed else '❌ 需改进'}",
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
            "passed": r.get("passed", r["score"] >= r.get("threshold", QUALITY_PASS_THRESHOLD)),
            "threshold": r.get("threshold", QUALITY_PASS_THRESHOLD),
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

    progress(0.45)

    # ── 5. 人工化改写（如果启用，内嵌于研究写作阶段） ──
    if state.enable_humanize:
        log("→ 人工化改写（去 AI 味）...", "stage")
        progress(0.48)

        try:
            from ai_writer import AIWriter
            writer = AIWriter()
            result = writer.humanize(content, content_style=cs)
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

    # ── 6. 严格完成校验：研究-写作阶段必须达到 90 分 ──
    if best_score < RESEARCH_WRITE_PASS_THRESHOLD:
        log(
            f"❌ 研究-写作阶段未达标: 最佳评分 {best_score} < {RESEARCH_WRITE_PASS_THRESHOLD}，"
            f"阶段未完成，流水线中止",
            "error",
        )
        _sys.stderr.write(
            f"[loop] 研究-写作阶段未达标: best_score={best_score} "
            f"threshold={RESEARCH_WRITE_PASS_THRESHOLD}\n"
        ); _sys.stderr.flush()
        stage("研究写作", "failed")
        return False

    # ── 7. 输出最终报告 ──
    state.mark_done("write")
    stage("研究写作", "done")
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
