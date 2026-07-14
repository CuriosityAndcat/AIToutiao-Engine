"""
Claim-Pipeline — 三阶段事实锚定流水线（B-2 新增）。

模块职责：
  阶段 1 — extract_claims()     从资料中提取原子事实声明
  阶段 2 — verify_claims()      逐条比对来源验证
  阶段 2.5 — merge_claims()     跨迭代声明合并去重（规则引擎，零 LLM 调用）
  ClaimsPool 数据模型            声明池聚合

LLM 访问方式：依赖注入 — 所有阶段函数接受 llm_call: Callable 参数，
由 write_stage.py 从 AIWriter._call_ai 传入，避免循环依赖。
"""

from __future__ import annotations

import json as _json
import re as _re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Callable, Optional


# ═══════════════════════════════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════════════════════════════


@dataclass
class Claim:
    """阶段 1 提取的原子事实声明（未验证）"""
    id: int                          # 声明序号（1-based）
    text: str                        # 声明文本（自包含，脱离上下文可理解）
    source_label: str                # 来源标记：[视频] 或 [搜索: 关键词]
    certainty: str                   # ✅确定 / ⚠️推测 / ❓存疑


@dataclass
class VerifiedClaim:
    """阶段 2 验证后的声明"""
    id: int
    status: str                      # CONFIRMED / PARTIAL / UNVERIFIED
    text: str                        # 验证/修正后的声明文本
    source_quote: str                # 资料原文片段
    source_label: str = ""           # 原始来源标记（跨迭代合并时需要）


@dataclass
class ClaimsPool:
    """阶段 2.5 合并后的可用声明池"""
    confirmed: list[VerifiedClaim] = field(default_factory=list)   # 确定事实
    partial: list[VerifiedClaim] = field(default_factory=list)      # 部分证实
    total_claims: int = 0
    coverage: float = 0.0            # 来源覆盖率 = (CONFIRMED+PARTIAL) / 总声明数

    @property
    def all_verified(self) -> list[VerifiedClaim]:
        """所有已验证声明（CONFIRMED + PARTIAL）"""
        return self.confirmed + self.partial

    @property
    def verified_count(self) -> int:
        return len(self.confirmed) + len(self.partial)

    def to_prompt_text(self) -> str:
        """格式化为 Compose 阶段的 prompt 输入"""
        lines: list[str] = []
        if self.confirmed:
            lines.append("【确定事实】（可直接引用，无需标注来源）")
            for c in self.confirmed:
                lines.append(f"- {c.text}")
        if self.partial:
            lines.append('\n【部分证实/推测】（引用时必须标注「据报道」「据分析」等）')
            for p in self.partial:
                lines.append(f"- {p.text}")
        return "\n".join(lines)

    def summary(self) -> str:
        """简短摘要（注入评估 prompt 用）"""
        parts = []
        if self.confirmed:
            parts.append(f"确定事实 {len(self.confirmed)} 条: {'; '.join(c.text[:60] for c in self.confirmed[:5])}")
        if self.partial:
            parts.append(f"部分事实 {len(self.partial)} 条: {'; '.join(p.text[:60] for p in self.partial[:5])}")
        parts.append(f"来源覆盖率 {self.coverage:.0%}")
        return " | ".join(parts)


# ═══════════════════════════════════════════════════════════════
# 阶段 1: Extract — 事实提取器
# ═══════════════════════════════════════════════════════════════

_EXTRACT_SYSTEM = (
    "你是一个严格的事实提取器。从以下资料中提取所有可验证的事实声明。\n"
    "规则：\n"
    "1. 每条声明必须是自包含的（脱离上下文可理解）\n"
    "2. 标注每条声明的来源：[视频] 或 [搜索: 关键词]\n"
    "3. 区分确定性：✅确定 / ⚠️推测 / ❓存疑\n"
    "4. 不添加、不推断、不演绎资料中不存在的信息\n"
    "5. 如果资料中只有概括描述，保持概括，不补充细节\n"
    "\n"
    "输出格式（纯列表，每行一条，不编号）:\n"
    "[来源: X] [确定性] 声明文本\n"
)


def extract_claims(
    research_context: str,
    transcript: str,
    llm_call: Callable[..., str],
) -> list[Claim]:
    """阶段 1：从搜索资料 + 视频摘要中提取原子事实声明。

    Args:
        research_context: 累计搜索资料文本（最近 N 轮）
        transcript: 视频转录摘要
        llm_call: LLM 调用函数，签名同 AIWriter._call_ai(prompt, max_tokens, temperature)

    Returns:
        Claim 列表。若提取失败返回空列表。
    """
    input_text = (
        f"【视频内容摘要】\n{transcript[:2000]}\n\n"
        f"【搜索资料】\n{research_context[:4500]}"
    )

    try:
        response = llm_call(
            _EXTRACT_SYSTEM + "\n\n" + input_text,
            max_tokens=1500,
            temperature=0.1,
        )
        if not response:
            return []
    except Exception:
        return []

    claims: list[Claim] = []
    idx = 0
    for line in response.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # 解析格式: [来源: X] [确定性] 声明文本
        m = _re.match(r'\[来源:\s*(.+?)\]\s*\[(.+?)\]\s*(.+)', line)
        if not m:
            # 尝试宽松匹配
            if line.startswith("- ") or line.startswith("* "):
                line = line[2:]
            if len(line) > 10:
                idx += 1
                claims.append(Claim(
                    id=idx,
                    text=line,
                    source_label="[来源未标注]",
                    certainty="❓存疑",
                ))
            continue
        idx += 1
        claims.append(Claim(
            id=idx,
            text=m.group(3).strip(),
            source_label=f"[{m.group(1).strip()}]",
            certainty=m.group(2).strip(),
        ))

    return claims


# ═══════════════════════════════════════════════════════════════
# 阶段 2: Ground — 事实锚定
# ═══════════════════════════════════════════════════════════════

_VERIFY_SYSTEM = (
    "你是一个严格的事实审核员。逐一检查以下声明是否在原始资料中有依据。\n"
    "对于每条声明：\n"
    "1. 在原始资料中搜索相同或等价表述\n"
    "2. 如果找到 → 保持声明，标记 CONFIRMED\n"
    "3. 如果部分匹配 → 修正声明使其完全匹配来源，标记 PARTIAL\n"
    "4. 如果完全找不到 → 标记 UNVERIFIED（不保留）\n"
    "\n"
    "输出格式（JSON Lines，每行一条，无外层包裹，尾部一行 METADATA）：\n"
    '{"id":1,"status":"CONFIRMED","text":"修正/确认后的声明文本","source_quote":"资料原文片段"}\n'
    '{"id":2,"status":"PARTIAL","text":"修正后匹配来源的声明","source_quote":"资料原文片段"}\n'
    '{"id":3,"status":"UNVERIFIED","text":"","source_quote":""}\n'
    "METADATA coverage=2/3=66.7%\n"
    "\n"
    "注意：只输出 JSON Lines 和 METADATA 行，不要输出任何解释或 Markdown 包裹。"
)


def _safe_parse_verification(response: str) -> tuple[list[VerifiedClaim], float]:
    """容错解析 JSON Lines 格式的验证输出。

    逐行尝试 json.loads()，跳过解析失败的行。
    METADATA 行用正则 fallback。
    """
    verified: list[VerifiedClaim] = []
    coverage = 0.0

    for line in response.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        # METADATA 行
        if line.startswith("METADATA"):
            m = _re.search(r"coverage\s*=\s*([\d.]+)%?", line)
            if m:
                coverage = float(m.group(1))
                if coverage > 1.0:
                    coverage = coverage / 100.0
            continue

        # JSON Lines
        try:
            obj = _json.loads(line)
        except (_json.JSONDecodeError, ValueError):
            continue

        vid = int(obj.get("id", 0))
        status = str(obj.get("status", "UNVERIFIED")).upper()
        text = str(obj.get("text", ""))
        quote = str(obj.get("source_quote", ""))

        verified.append(VerifiedClaim(
            id=vid,
            status=status,
            text=text,
            source_quote=quote,
        ))

    # 从 verified 列表计算覆盖率（兜底）
    if not coverage and verified:
        confirmed_count = sum(1 for v in verified if v.status in ("CONFIRMED", "PARTIAL"))
        coverage = confirmed_count / len(verified) if verified else 0.0

    return verified, coverage


def verify_claims(
    claims: list[Claim],
    raw_sources: str,
    llm_call: Callable[..., str],
) -> tuple[list[VerifiedClaim], float]:
    """阶段 2：逐条比对来源验证声明。

    Args:
        claims: 阶段 1 提取的声明列表
        raw_sources: 原始搜索资料全文（用于比对）
        llm_call: LLM 调用函数

    Returns:
        (verified_claims, coverage) — verified_claims 为验证后声明列表，
        coverage 为来源覆盖率 (0.0~1.0)
    """
    if not claims:
        return [], 0.0

    # 构建验证输入
    claims_text = "\n".join(
        f'{{"id":{c.id},"text":"{c.text}","source":"{c.source_label}","certainty":"{c.certainty}"}}'
        for c in claims
    )

    prompt = (
        f"【待验证声明列表】\n{claims_text}\n\n"
        f"【原始资料（用于比对）】\n{raw_sources[:4000]}"
    )

    try:
        response = llm_call(
            _VERIFY_SYSTEM + "\n\n" + prompt,
            max_tokens=2000,
            temperature=0.1,
        )
        if not response:
            return [], 0.0
    except Exception:
        return [], 0.0

    verified, coverage = _safe_parse_verification(response)

    # 回填 source_label（从原始声明）
    claim_map = {c.id: c.source_label for c in claims}
    for v in verified:
        if not v.source_label:
            v.source_label = claim_map.get(v.id, "")

    return verified, coverage


# ═══════════════════════════════════════════════════════════════
# 阶段 2.5: Merge — 跨迭代声明合并（规则引擎，零 LLM）
# ═══════════════════════════════════════════════════════════════

# 合并相似度阈值（difflib.SequenceMatcher）
_MERGE_SIMILARITY_THRESHOLD = 0.5
# 极短声明（<10字）跳过分桶
_MERGE_MIN_CHARS_FOR_CLUSTER = 10


def _text_similarity(a: str, b: str) -> float:
    """计算两个中文文本的字符级相似度（基于 difflib.SequenceMatcher）。"""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def merge_claims(
    new_claims: list[VerifiedClaim],
    history_pool: Optional[ClaimsPool] = None,
) -> ClaimsPool:
    """阶段 2.5：跨迭代声明合并去重。

    规则（纯 Python stdlib，零 LLM 调用）：
    1. 精确匹配：声明 ID 相同 → 直接分桶
    2. 模糊匹配：difflib.SequenceMatcher.ratio() > 0.5 → 归入同桶
       （极端短声明 <10字跳过分桶，单独保留）
    3. 同桶内覆盖：新 CONFIRMED > 旧 CONFIRMED（最新胜出）
       → 新 CONFIRMED > 旧 PARTIAL / UNVERIFIED（等级提升）
       → 同来源不同文本 → 保留两者
    4. 排序：CONFIRMED 优先 → PARTIAL 居后 → 来源多样化降序

    Args:
        new_claims: 当前迭代阶段 2 的验证结果
        history_pool: 历史累积的声明池（首次为 None）

    Returns:
        ClaimsPool — 合并后的可用声明池
    """
    pool = history_pool or ClaimsPool()

    # 1. 所有声明汇总
    all_verified: list[VerifiedClaim] = list(pool.all_verified) + list(new_claims)
    if not all_verified:
        return pool

    # 2. 分桶
    buckets: list[list[VerifiedClaim]] = []
    assigned = set()

    for i, claim_i in enumerate(all_verified):
        if i in assigned:
            continue
        bucket = [claim_i]
        assigned.add(i)

        for j, claim_j in enumerate(all_verified):
            if j in assigned:
                continue
            # 精确匹配：ID 相同
            if claim_i.id == claim_j.id and claim_i.source_label == claim_j.source_label:
                bucket.append(claim_j)
                assigned.add(j)
                continue
            # 模糊匹配：文本相似度 + 短声明跳过
            text_i = claim_i.text
            text_j = claim_j.text
            if len(text_i) < _MERGE_MIN_CHARS_FOR_CLUSTER or len(text_j) < _MERGE_MIN_CHARS_FOR_CLUSTER:
                continue
            if _text_similarity(text_i, text_j) > _MERGE_SIMILARITY_THRESHOLD:
                bucket.append(claim_j)
                assigned.add(j)

        buckets.append(bucket)

    # 未分配的短声明单独成桶
    for i, claim_i in enumerate(all_verified):
        if i not in assigned:
            buckets.append([claim_i])

    # 3. 同桶内覆盖
    merged: list[VerifiedClaim] = []
    for bucket in buckets:
        if len(bucket) == 1:
            merged.append(bucket[0])
            continue

        # 按优先级排序: CONFIRMED(3) > PARTIAL(2) > UNVERIFIED(1)
        def _priority(c: VerifiedClaim) -> int:
            if c.status == "CONFIRMED":
                return 3
            if c.status == "PARTIAL":
                return 2
            return 1

        bucket.sort(key=_priority, reverse=True)
        best = bucket[0]

        # 同来源不同文本 → 保留
        seen_sources = set()
        for c in bucket:
            if c.source_label and c.source_label not in seen_sources:
                seen_sources.add(c.source_label)
                if c != best:
                    merged.append(c)

        merged.append(best)

    # 4. 分类 + 排序
    confirmed = sorted(
        [c for c in merged if c.status == "CONFIRMED"],
        key=lambda c: len(c.source_label), reverse=True,
    )
    partial = sorted(
        [c for c in merged if c.status == "PARTIAL"],
        key=lambda c: len(c.source_label), reverse=True,
    )
    unverified = [c for c in merged if c.status == "UNVERIFIED"]
    unverified_count = len(unverified)

    total = len(merged)
    verified_count = len(confirmed) + len(partial)
    coverage = verified_count / total if total > 0 else 0.0

    return ClaimsPool(
        confirmed=confirmed,
        partial=partial,
        total_claims=total,
        coverage=coverage,
    )


# ═══════════════════════════════════════════════════════════════
# 辅助: 从声明池生成研究缺口主题
# ═══════════════════════════════════════════════════════════════

def generate_knowledge_gap_query(
    pool: ClaimsPool,
    video_title: str,
    llm_call: Callable[..., str],
) -> str:
    """根据声明池的覆盖率缺口，生成补充搜索关键词。

    用于替代 B-1 临时修复的 extract_refined_query()，
    搜索方向从"查证具体编造"转为"拓宽核心主题的事实面"。

    Args:
        pool: 当前声明池
        video_title: 原始视频标题
        llm_call: LLM 调用函数

    Returns:
        搜索关键词（中文，10 字以内），失败返回空字符串
    """
    if pool.coverage >= 0.7:
        return ""  # 覆盖率已达标

    prompt = (
        f"以下是视频主题的已知事实声明:\n"
        f"确定事实: {'; '.join(c.text[:50] for c in pool.confirmed[:5]) or '无'}\n"
        f"部分事实: {'; '.join(p.text[:50] for p in pool.partial[:5]) or '无'}\n"
        f"来源覆盖率: {pool.coverage:.0%}\n"
        f"原始视频主题: {video_title[:100]}\n"
        f"请提炼 1 个关于该主题「目前缺少、需要补充搜索」的核心关键词"
        f"（中文，10 字以内，宽泛而非具体）。直接返回关键词，不要其他文字。"
    )

    try:
        result = llm_call(prompt, max_tokens=40, temperature=0.3)
        return result.strip().strip("。，,.;;\"'")
    except Exception:
        return ""
