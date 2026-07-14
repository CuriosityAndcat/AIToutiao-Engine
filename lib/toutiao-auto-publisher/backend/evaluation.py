"""
内容质量评估层 — 从 engine_app 的 Phase 3 抽出。

完全无 UI 依赖（仅写 stderr），不依赖 Streamlit，可直接单测。
"""
import sys as _sys
import re as _re

QUALITY_PASS_THRESHOLD = 75        # 质量评分通过线（0-100）
FACT_HARD_FLOOR = 80                 # 事实准确性硬门槛：低于此值直接判不通过（防带错稿放行）
# 反馈中出现这些词视为「事实硬伤」，无论综合分多少均强制打回重写
_FACT_INJURY_MARKERS = (
    "硬伤", "存疑", "编造", "杜撰", "与事实不符", "事实不准确",
    "失实", "误导", "无可靠来源", "未证实",
)


def _xml_get(tag: str, text: str) -> str:
    """从文本中提取 XML 标签内容，返回首个匹配。"""
    m = _re.search(f"<{tag}>(.*?)</{tag}>", text, _re.DOTALL | _re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _xml_get_int(tag: str, text: str, default: int = 50) -> int:
    """提取数值型标签，解析失败返回默认值。"""
    val = _xml_get(tag, text)
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def evaluate_content(content: str, title: str, style: str,
                     research_context: str = "",
                     threshold: int = QUALITY_PASS_THRESHOLD,
                     claims_pool_summary: str = "") -> dict:
    """使用 DeepSeek API 评估生成内容的质量。

    改为 XML 标签格式输出（对齐 Anthropic Evaluator-Optimizer 最佳实践），
    XML 标签解析比 JSON 大括号匹配更稳定，不易被 LLM 额外说明文字污染。

    Args:
        threshold: 通过线，默认使用全局 QUALITY_PASS_THRESHOLD。
                   研究-写作阶段可传入更高阈值（如 80）做严格验收。
        claims_pool_summary: Claim-Pipeline 模式专用——声明池摘要，
                             用于区分「有声明未用」（完整性扣分）vs「无声明编造」（事实准确严重扣分）。

    返回: {
        "score": int(0-100), "feedback": str, "passed": bool,
        "dimensions": {维度名: 分数}, "threshold": int,
    }
    """
    _sys.stderr.write("[eval] 开始评估内容质量 (XML 模式)...\n"); _sys.stderr.flush()

    eval_prompt = (
        "你是一个严格的内容质量评审员。请评估以下微头条/文章内容的质量，"
        "从以下维度评分（每项满分100）：\n\n"
        "1. **事实准确性**：是否与已知事实一致，无明显编造内容\n"
        "2. **信息完整性**：是否覆盖了关键信息点（人物、事件、原因、影响）\n"
        "3. **结构清晰度**：段落分明、逻辑连贯、易读性强\n"
        "4. **风格一致性**：是否符合指定写作风格的要求\n"
        "5. **去AI味程度**：读起来是否像真人写作，有无机器腔\n\n"
        "评分规则：\n"
        "- 综合分 = 5 项平均分\n"
        f"- 综合分 >= {threshold} 且无单项低于 50 → 通过\n"
        f"- 事实准确性维度 < {FACT_HARD_FLOOR} → 直接判不通过（事实硬门槛，带错稿不放行）\n"
        "- 若内容存在事实硬伤/编造/存疑/与已知资料不符，即使综合分达标也判 NEEDS_IMPROVEMENT\n"
        "- 否则 → 不通过，需重写\n\n"
        f"目标写作风格：{style}\n\n"
    )

    if research_context:
        eval_prompt += (
            "【参考背景资料】（用于校验事实准确性）\n"
            f"{research_context[:1500]}\n\n"
        )

    if claims_pool_summary:
        eval_prompt += (
            "【声明池摘要】（本文应基于此声明池写作）\n"
            f"{claims_pool_summary[:1500]}\n\n"
            "注意：如果正文中存在声明池中没有的事实细节 → 属于编造，"
            "事实准确性维度应严重扣分（≤60）；"
            "如果声明池中有但正文未使用 → 属于信息遗漏，完整性维度扣分。\n\n"
        )

    eval_prompt += (
        f"【标题】\n{title}\n\n"
        f"【正文】（共 {len(content)} 字）\n{content[:2000]}\n\n"
        "请严格按以下 XML 标签格式输出评估结果（不要输出其他任何文字）：\n"
        "<evaluation>PASS 或 NEEDS_IMPROVEMENT 或 FAIL</evaluation>\n"
        "<score>综合分整数</score>\n"
        "<dimensions>\n"
        "  <事实准确>整数</事实准确>\n"
        "  <信息完整>整数</信息完整>\n"
        "  <结构清晰>整数</结构清晰>\n"
        "  <风格一致>整数</风格一致>\n"
        "  <去AI味>整数</去AI味>\n"
        "</dimensions>\n"
        "<feedback>一句话总结优劣和改进建议</feedback>"
    )

    try:
        from ai_writer import AIWriter

        writer = AIWriter()
        response = writer._call_ai(eval_prompt, max_tokens=500, temperature=0.1)

        # ── 优先 XML 解析 ──
        eval_status = _xml_get("evaluation", response)
        score = _xml_get_int("score", response, default=50)
        feedback = _xml_get("feedback", response)

        # 提取 5 维度分
        dimensions_section = _xml_get("dimensions", response) or response
        dimensions = {
            "事实准确": _xml_get_int("事实准确", dimensions_section, default=50),
            "信息完整": _xml_get_int("信息完整", dimensions_section, default=50),
            "结构清晰": _xml_get_int("结构清晰", dimensions_section, default=50),
            "风格一致": _xml_get_int("风格一致", dimensions_section, default=50),
            "去AI味": _xml_get_int("去AI味", dimensions_section, default=50),
        }

        if not eval_status or not feedback:
            # ── 降级 1: XML 不完整，尝试 JSON 解析 ──
            _sys.stderr.write("[eval] XML 不完整，尝试 JSON 降级解析\n"); _sys.stderr.flush()
            try:
                import json as _json
                json_match = _re.search(r'\{[^}]+\}', response, _re.DOTALL)
                if json_match:
                    result = _json.loads(json_match.group())
                    score = int(result.get("综合分", 50))
                    feedback = result.get("反馈", "无评价")
                    eval_status = "PASS" if result.get("通过", False) else "NEEDS_IMPROVEMENT"
                    # 尝试提取分维度
                    for dim_key, json_key in [
                        ("事实准确", "事实准确"), ("信息完整", "信息完整"),
                        ("结构清晰", "结构清晰"), ("风格一致", "风格一致"),
                        ("去AI味", "去AI味"),
                    ]:
                        if json_key in result:
                            dimensions[dim_key] = int(result[json_key])
            except Exception:
                pass

        # ── 降级 2: 完全解析失败，规则判断 ──
        if not feedback:
            _sys.stderr.write("[eval] XML/JSON 均解析失败，使用规则判断\n"); _sys.stderr.flush()
            score = 50
            feedback = f"评估解析失败，原始响应: {response[:100]}"
            eval_status = "PASS" if len(content) > 100 else "FAIL"

        passed = eval_status.upper() == "PASS"
        # 强制检查：分数低于阈值则不过
        if score < threshold:
            passed = False
        # 任一项低于 50 也不通过
        if any(v < 50 for v in dimensions.values()):
            passed = False

        # ── 事实准确性硬门槛（防带已知硬伤的稿子放行）──
        fact_score = dimensions.get("事实准确", 50)
        if fact_score < FACT_HARD_FLOOR:
            passed = False
            _extra = f"事实准确性 {fact_score} 低于硬门槛 {FACT_HARD_FLOOR}，已强制打回重写"
            feedback = (feedback + f"（⚠️ {_extra}）") if feedback else f"⚠️ {_extra}"
        # 反馈含事实硬伤关键词 → 无论综合分多少均不通过
        if any(_m in feedback for _m in _FACT_INJURY_MARKERS):
            passed = False
            if "⚠️" not in feedback:
                feedback = f"⚠️ 检测到事实硬伤描述，已强制打回重写。{feedback}"

        _sys.stderr.write(
            f"[eval] XML模式 评分={score}, 通过={passed}, "
            f"维度={{{', '.join(f'{k}={v}' for k,v in dimensions.items())}}}\n"
        ); _sys.stderr.flush()

        return {
            "score": score,
            "feedback": feedback,
            "passed": passed,
            "dimensions": dimensions,
            "threshold": threshold,
        }

    except Exception as e:
        _sys.stderr.write(f"[eval] 评估异常: {e}\n"); _sys.stderr.flush()
        return {
            "score": QUALITY_PASS_THRESHOLD,
            "feedback": f"评估模块异常，跳过评估: {e}",
            "passed": True,
            "dimensions": {"事实准确": 70, "信息完整": 70, "结构清晰": 70, "风格一致": 70, "去AI味": 70},
            "threshold": QUALITY_PASS_THRESHOLD,
        }
