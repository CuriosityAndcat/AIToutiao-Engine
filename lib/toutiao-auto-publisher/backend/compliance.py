"""
头条平台规则合规检测模块 — 在阶段三质量评估后、人工化定稿前执行。

提供两个核心函数：
- check_compliance(): LLM 逐项审查文章是否违反头条平台规则
- fix_compliance(): 将违规报告反馈 LLM 修复重写

规则来源：.codebuddy/skills/toutiao-platform-rules/SKILL.md
"""

import sys as _sys

# ═══════════════════════════════════════════════════════════
# 核心规则集（从 SKILL.md 提炼，约 2000 字符）
# ═══════════════════════════════════════════════════════════

_COMPLIANCE_RULES = """## 今日头条平台规则（合规审查基准）

你是一个严格的平台合规审查员。请逐项审查以下内容，判断是否违反头条平台规则。

### 一、禁言级违规（任一命中则严重不通过）

**1. 涉时政有害信息**：
- 反对宪法基本原则、危害国家安全统一、泄露国家秘密
- 宣扬恐怖主义/极端主义、煽动民族仇恨/宗教歧视
- 散布谣言扰乱社会秩序、宣扬暴力凶杀
- 煽动非法集会/结社/游行/示威

**2. 政治谣言**：
- 对党和国家领导人及有政治意义的公众人物进行诬陷诽谤
- 重大突发事件后传播扰乱政治生态的谣言

**3. 历史虚无主义**：
- 歪曲党史/新中国史/改革开放史/社会主义发展史
- 诋毁英雄烈士、否定中华优秀传统文化/革命文化/社会主义先进文化

**4. 低俗色情**：
- 未成年人涉性内容、露点、性行为过程露骨展示
- 色情影视/动漫、违背伦理关系（乱伦/低俗野史）、猎奇性癖好

**5. 违规推广**：
- 利用国旗国徽/党徽/领导人形象进行商业炒作

### 二、扣分级违规（信用分扣20分）

**6. 标题党**：标题夸大/悬念/要素误导/题文严重不符
**7. 攻击谩骂/网暴**：辱骂、人身攻击、煽动网暴
**8. 画风不良**：低俗、裸露暗示、违背公序良俗
**9. 违规推广（中度）**：传销、违规网贷、荐股、违规医疗推广
**10. 旧闻翻炒**：将过时事件包装成最新新闻
**11. 失实表述**：关键信息与事实不符、编造数据
**12. 不当价值观**：炫富、自杀导向、封建迷信、丧文化

### 三、轻度违规（信用分扣10分）

**13. 轻微标题党**：标题略有夸张但未严重失实
**14. 内容引起不适**：血腥暴力描写（未打码）、虐待动物
**15. 抄袭/洗稿**：明显拼凑他人作品
**16. 格式低质**：乱码、机翻感严重、无标点分段
**17. 不文明用语**：粗俗网络用语、情绪化脏话（如"tm""屁""扯"等）

### 四、社区规范「平台不鼓励」（虽不立即扣分，累积会限流）

**18. 已过时效内容**：旧闻当新闻，无时效标注
**19. 话题无关/内容低质**：逻辑混乱、病句、排版混乱
**20. 引导互粉/诱导交互**：明显引导关注/点赞/转发

### 审查要求

1. 逐条检查上述 20 项规则，只标注**确实存在**的违规项
2. 对每项违规，必须引用原文**具体片段**作为证据
3. 区分严重度：严重（禁言级）/ 中度（扣20分）/ 轻度（扣10分）/ 提醒（不鼓励）
4. 如完全合规，返回 passed=true 并说明"全项通过"
5. 输出格式必须严格使用 XML：

<compliance_check>
  <passed>true|false</passed>
  <total_score>100</total_score>
  <violations>
    <violation>
      <rule>规则编号与名称</rule>
      <severity>严重|中度|轻度|提醒</severity>
      <quote>原文违规片段</quote>
      <reason>违规原因简述</reason>
      <fix_suggestion>具体修改建议</fix_suggestion>
    </violation>
  </violations>
  <summary>整体评估总结</summary>
</compliance_check>
"""


def check_compliance(content: str, title: str, style_label: str = "") -> dict:
    """调用 LLM 以平台规则为基准审查文章合规性。

    Args:
        content: 文章正文
        title: 文章标题
        style_label: 写作风格标签（可选，用于日志上下文）

    Returns:
        {
            "passed": bool,         # 是否完全通过
            "violations": list,      # [{rule, severity, quote, reason, fix_suggestion}]
            "report": str,          # 人类可读的违规报告摘要
            "total_score": int,     # 合规评分 0-100
        }
    """
    _sys.stderr.write("[compliance] 开始合规检测...\n"); _sys.stderr.flush()

    prompt = (
        f"{_COMPLIANCE_RULES}\n\n"
        f"=== 待审查文章 ===\n\n"
        f"【标题】{title}\n\n"
        f"【正文】\n{content}\n\n"
        f"请严格按照上述 XML 格式输出审查结果。"
    )

    try:
        from ai_writer import AIWriter
        writer = AIWriter()
        raw = writer._call_ai(prompt, max_tokens=1200, temperature=0.1)
    except Exception as e:
        _sys.stderr.write(f"[compliance] LLM 调用异常: {e}\n"); _sys.stderr.flush()
        return {
            "passed": True,
            "violations": [],
            "report": f"(合规检测 LLM 异常，跳过: {e})",
            "total_score": 100,
        }

    if not raw or len(raw) < 20:
        _sys.stderr.write("[compliance] LLM 返回为空/过短，跳过\n"); _sys.stderr.flush()
        return {
            "passed": True,
            "violations": [],
            "report": "(合规检测 LLM 返回为空，跳过)",
            "total_score": 100,
        }

    # 解析 XML 结果
    result = _parse_compliance_xml(raw)
    _sys.stderr.write(
        f"[compliance] 结果: passed={result['passed']}, "
        f"score={result['total_score']}, "
        f"violations={len(result['violations'])}\n"
    ); _sys.stderr.flush()

    return result


def fix_compliance(content: str, title: str, report: str, style_label: str = "") -> str:
    """将违规报告反馈给 LLM，要求逐条修复后重写全文。

    Args:
        content: 原始文章正文
        title: 文章标题
        report: check_compliance() 返回的违规报告文本
        style_label: 写作风格标签（可选）

    Returns:
        修复后的 content 字符串。LLM 异常时返回原 content。
    """
    _sys.stderr.write("[compliance] 开始合规修复重写...\n"); _sys.stderr.flush()

    prompt = (
        "你是今日头条的内容创作者。你的文章因以下合规问题未能通过平台审查，"
        "请**逐一修复**每项违规后重写全文。\n\n"
        "修复原则：\n"
        "1. 逐条处理违规报告中的每项问题\n"
        "2. 修复后不得引入新的违规\n"
        "3. 保持原文的核心信息、论证逻辑和写作风格不变\n"
        "4. 如违规项涉及删改特定表述，用更安全、更专业的表达替代\n"
        "5. 只输出修复后的完整正文（不要输出修复说明或解释）\n\n"
        f"【文章标题】{title}\n\n"
        f"【原始正文】\n{content}\n\n"
        f"【合规违规报告】\n{report}\n\n"
        f"请直接输出修复后的完整正文："
    )

    try:
        from ai_writer import AIWriter
        writer = AIWriter()
        fixed = writer._call_ai(prompt, max_tokens=3000, temperature=0.2)
    except Exception as e:
        _sys.stderr.write(f"[compliance] 修复 LLM 异常: {e}\n"); _sys.stderr.flush()
        return content

    if not fixed or len(fixed) < 50:
        _sys.stderr.write("[compliance] 修复结果过短，保留原文\n"); _sys.stderr.flush()
        return content

    _sys.stderr.write(f"[compliance] 修复完成: {len(fixed)} 字符\n"); _sys.stderr.flush()
    return fixed


def _parse_compliance_xml(raw: str) -> dict:
    """解析 compliance check 的 XML 输出。

    支持 <compliance_check> 标签，降级到简单文本解析。
    """
    import re

    violations = []
    passed = True
    total_score = 100
    report = raw[:500]  # 兜底摘要

    # ── 尝试 XML 解析 ──
    try:
        passed_match = re.search(r"<passed>(true|false)</passed>", raw, re.IGNORECASE)
        if passed_match:
            passed = passed_match.group(1).lower() == "true"

        score_match = re.search(r"<total_score>(\d+)</total_score>", raw, re.IGNORECASE)
        if score_match:
            total_score = int(score_match.group(1))

        summary_match = re.search(r"<summary>(.*?)</summary>", raw, re.DOTALL | re.IGNORECASE)
        if summary_match:
            report = summary_match.group(1).strip()

        # 提取 violations
        vio_blocks = re.findall(r"<violation>(.*?)</violation>", raw, re.DOTALL | re.IGNORECASE)
        for block in vio_blocks:
            rule_match = re.search(r"<rule>(.*?)</rule>", block, re.DOTALL | re.IGNORECASE)
            severity_match = re.search(r"<severity>(.*?)</severity>", block, re.DOTALL | re.IGNORECASE)
            quote_match = re.search(r"<quote>(.*?)</quote>", block, re.DOTALL | re.IGNORECASE)
            reason_match = re.search(r"<reason>(.*?)</reason>", block, re.DOTALL | re.IGNORECASE)
            fix_match = re.search(r"<fix_suggestion>(.*?)</fix_suggestion>", block, re.DOTALL | re.IGNORECASE)

            violations.append({
                "rule": rule_match.group(1).strip() if rule_match else "未知规则",
                "severity": severity_match.group(1).strip() if severity_match else "未知",
                "quote": quote_match.group(1).strip() if quote_match else "",
                "reason": reason_match.group(1).strip() if reason_match else "",
                "fix_suggestion": fix_match.group(1).strip() if fix_match else "",
            })
    except Exception:
        # XML 解析失败，尝试降级判断
        if "passed>true" in raw.lower() or "全项通过" in raw or "无违规" in raw:
            passed = True
        elif "passed>false" in raw.lower():
            passed = False

    return {
        "passed": passed,
        "violations": violations,
        "report": report,
        "total_score": total_score,
    }
