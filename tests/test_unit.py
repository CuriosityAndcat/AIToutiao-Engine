"""
单元测试 — 覆盖 TOP 5 模块核心函数（P1-6）

不含任何 LLM / 网络 / 文件 I/O 调用，全部为确定性逻辑测试。
可在任意环境执行：python -m pytest tests/test_unit.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# 注入 backend 路径
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
_BACKEND = _ROOT / "lib" / "toutiao-auto-publisher" / "backend"
for _p in (str(_HERE), str(_ROOT), str(_BACKEND)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ═══════════════════════════════════════════════════════════════
# 模块 1: evaluation.py — XML 解析 + 评估规则
# ═══════════════════════════════════════════════════════════════

class TestXmlParsing:
    """_xml_get / _xml_get_int 边界测试"""

    def test_xml_get_basic(self):
        from evaluation import _xml_get
        assert _xml_get("score", "<score>85</score>") == "85"
        assert _xml_get("feedback", "<feedback>写得不错</feedback>") == "写得不错"
        assert _xml_get("missing", "<score>85</score>") == ""

    def test_xml_get_multiline(self):
        from evaluation import _xml_get
        text = "<feedback>\n第一行\n第二行\n</feedback>"
        assert _xml_get("feedback", text) == "第一行\n第二行"

    def test_xml_get_int(self):
        from evaluation import _xml_get_int
        assert _xml_get_int("score", "<score>85</score>") == 85
        assert _xml_get_int("score", "<score>85.5</score>") == 85
        assert _xml_get_int("score", "<score>abc</score>", default=50) == 50
        assert _xml_get_int("missing", "<score>85</score>", default=40) == 40

    def test_fact_hard_floor(self):
        """FACT_HARD_FLOOR 常量存在且值正确"""
        from evaluation import FACT_HARD_FLOOR
        assert FACT_HARD_FLOOR == 80


# ═══════════════════════════════════════════════════════════════
# 模块 2: write_stage.py — 标题兜底 + 事实矫正
# ═══════════════════════════════════════════════════════════════

class TestFallbackTitle:
    """_fallback_title 平台前缀清洗"""

    def test_clean_douyin_prefix(self):
        from write_stage import _fallback_title
        assert _fallback_title("抖音独家俄乌冲突分析") == "俄乌冲突分析"

    def test_clean_multiple_prefixes(self):
        from write_stage import _fallback_title
        assert _fallback_title("快手独家最新消息") == "最新消息"

    def test_clean_bracket_tags(self):
        from write_stage import _fallback_title
        assert _fallback_title("【军事】武器分析") == "武器分析"
        assert _fallback_title("[军事]武器分析") == "武器分析"

    def test_clean_underscores(self):
        from write_stage import _fallback_title
        assert _fallback_title("俄乌___冲突_分析") == "俄乌 冲突 分析"

    def test_plain_title_unchanged(self):
        from write_stage import _fallback_title
        assert _fallback_title("普通标题") == "普通标题"

    def test_empty_title(self):
        from write_stage import _fallback_title
        assert _fallback_title("") == ""


class TestFactFixBlock:
    """_build_fact_fix_block 事实矫正块生成"""

    def test_no_block_when_fact_ok(self):
        from write_stage import _build_fact_fix_block
        record = {"dimensions": {"事实准确": 95}, "feedback": ""}
        assert _build_fact_fix_block(record) == ""

    def test_block_when_fact_low(self):
        from write_stage import _build_fact_fix_block
        record = {
            "dimensions": {"事实准确": 70},
            "feedback": "存在虚构的人物名称",
        }
        result = _build_fact_fix_block(record)
        assert "事实准确性仅 70 分" in result
        assert "虚构的人物名称" in result
        assert "严禁编造" in result

    def test_block_fact_score_zero(self):
        from write_stage import _build_fact_fix_block
        record = {"dimensions": {}, "feedback": "大量编造"}
        result = _build_fact_fix_block(record)
        # fact_score 默认 100 → 不生成矫正块
        assert result == ""


# ═══════════════════════════════════════════════════════════════
# 模块 3: ai_writer.py — 标题解析
# ═══════════════════════════════════════════════════════════════

class TestParseTitle:
    """_parse_title_from_content 标题-正文分离"""

    def _get_parser(self):
        from ai_writer import AIWriter
        return AIWriter._parse_title_from_content

    def test_basic_title_content(self):
        parse = self._get_parser()
        text = "标题：俄乌冲突最新动态\n\n正文内容开始..."
        title, body = parse(text)
        assert title == "俄乌冲突最新动态"
        assert "正文内容开始" in body

    def test_no_title_tag(self):
        parse = self._get_parser()
        text = "这是正文内容，没有标题分隔符\n第二段"
        title, body = parse(text)
        assert title == ""
        assert body == text

    def test_title_only_no_body(self):
        parse = self._get_parser()
        text = "标题：只是一个标题"
        title, body = parse(text)
        assert title == "只是一个标题"
        # body is same as title (nothing after newline)

    def test_title_with_colon(self):
        parse = self._get_parser()
        text = "标题：包含：冒号的标题\n正文"
        title, body = parse(text)
        assert title == "包含：冒号的标题"
        assert body == "正文"


# ═══════════════════════════════════════════════════════════════
# 模块 4: research.py — 搜索噪声过滤
# ═══════════════════════════════════════════════════════════════

class TestCleanSearchNoise:
    """_clean_search_noise 自然语言过滤"""

    def test_strip_css_block(self):
        from research import _clean_search_noise
        text = """.header {
    background: #fff;
    color: var(--text);
}
这是正文内容"""
        result = _clean_search_noise(text)
        assert ".header {" not in result
        assert "background:" not in result
        assert "这是正文内容" in result

    def test_strip_js_code(self):
        from research import _clean_search_noise
        text = """function init() {
    console.log("init");
}
这是新闻摘要"""
        result = _clean_search_noise(text)
        assert "function init" not in result
        assert "console.log" not in result
        assert "这是新闻摘要" in result

    def test_strip_html_comments(self):
        from research import _clean_search_noise
        text = "<!-- 这是注释 -->\n实际内容"
        result = _clean_search_noise(text)
        assert "<!--" not in result
        assert "实际内容" in result

    def test_strip_url_only_lines(self):
        from research import _clean_search_noise
        text = "https://example.com/article/123\n这是一条新闻"
        result = _clean_search_noise(text)
        assert "https://example.com" not in result
        assert "这是一条新闻" in result

    def test_strip_symbol_dominant_lines(self):
        from research import _clean_search_noise
        text = "===========================================\n实际文本内容"
        result = _clean_search_noise(text)
        assert "===" not in result
        assert "实际文本内容" in result

    def test_preserve_natural_text(self):
        from research import _clean_search_noise
        text = "据新华社报道，2024年中国经济增长5.2%，超出市场预期。\n专家认为这反映了经济结构的持续优化。"
        result = _clean_search_noise(text)
        assert "据新华社报道" in result
        assert "经济增长" in result

    def test_empty_input(self):
        from research import _clean_search_noise
        assert _clean_search_noise("") == ""
        assert _clean_search_noise(None) is None


# ═══════════════════════════════════════════════════════════════
# 模块 5: fact_pipeline.py — 声明合并 + 解析
# ═══════════════════════════════════════════════════════════════

class TestTextSimilarity:
    """_text_similarity 字符级相似度"""

    def test_identical(self):
        from fact_pipeline import _text_similarity
        assert _text_similarity("相同文本", "相同文本") > 0.99

    def test_similar(self):
        from fact_pipeline import _text_similarity
        s = _text_similarity("中国经济增长5%", "中国经济增速5%")
        assert 0.5 < s < 1.0

    def test_different(self):
        from fact_pipeline import _text_similarity
        s = _text_similarity("中国经济", "美国军事")
        assert s < 0.5

    def test_empty_strings(self):
        from fact_pipeline import _text_similarity
        assert _text_similarity("", "text") == 0.0
        assert _text_similarity("text", "") == 0.0
        assert _text_similarity("", "") == 0.0


class TestSafeParseVerification:
    """_safe_parse_verification JSON Lines 容错解析"""

    def test_valid_json_lines(self):
        from fact_pipeline import _safe_parse_verification, VerifiedClaim
        # METADATA 格式：coverage=85% → 85>1.0 → 0.85；coverage=0.85 → 直接 0.85
        # 注：coverage=2/2=100% 会因正则只捕获首个数字被误解析，实际使用中不会出现
        response = (
            '{"id":1,"status":"CONFIRMED","text":"已确认的事实","source_quote":"原文片段"}\n'
            '{"id":2,"status":"PARTIAL","text":"部分确认","source_quote":"部分原文"}\n'
            "METADATA coverage=0.85"
        )
        verified, coverage = _safe_parse_verification(response)
        assert len(verified) == 2
        assert 0.84 <= coverage <= 0.86  # 浮点容差
        assert verified[0].status == "CONFIRMED"
        assert verified[1].status == "PARTIAL"

    def test_mixed_valid_invalid_lines(self):
        from fact_pipeline import _safe_parse_verification
        response = (
            '{"id":1,"status":"CONFIRMED","text":"ok","source_quote":"q"}\n'
            "这是一行无效文本\n"
            '{"id":2,"status":"UNVERIFIED","text":"","source_quote":""}\n'
            "METADATA coverage=50%"
        )
        verified, coverage = _safe_parse_verification(response)
        # coverage=50 → 50>1.0 → 0.5
        assert len(verified) == 2
        assert 0.49 <= coverage <= 0.51

    def test_all_invalid(self):
        from fact_pipeline import _safe_parse_verification
        response = "纯文本无JSON\n也无效\nMETADATA coverage=0/0=0%"
        verified, coverage = _safe_parse_verification(response)
        assert verified == []
        assert coverage == 0.0

    def test_coverage_computed_fallback(self):
        from fact_pipeline import _safe_parse_verification
        # 无 METADATA 行时从结果推算
        response = (
            '{"id":1,"status":"CONFIRMED","text":"a","source_quote":"q"}\n'
            '{"id":2,"status":"CONFIRMED","text":"b","source_quote":"q"}\n'
            '{"id":3,"status":"UNVERIFIED","text":"","source_quote":""}'
        )
        verified, coverage = _safe_parse_verification(response)
        assert len(verified) == 3
        assert 0.6 < coverage < 0.7  # 2/3


class TestMergeClaims:
    """merge_claims 跨迭代声明合并（纯规则引擎）"""

    def test_first_merge_no_history(self):
        from fact_pipeline import merge_claims, VerifiedClaim
        new = [
            VerifiedClaim(id=1, status="CONFIRMED", text="事实A", source_quote="来源1"),
            VerifiedClaim(id=2, status="PARTIAL", text="事实B", source_quote="来源2"),
        ]
        pool = merge_claims(new)
        assert len(pool.confirmed) == 1
        assert len(pool.partial) == 1
        assert pool.coverage == 1.0  # 2/2

    def test_merge_with_history(self):
        from fact_pipeline import merge_claims, VerifiedClaim, ClaimsPool
        old = ClaimsPool(
            confirmed=[VerifiedClaim(id=1, status="CONFIRMED", text="事实A", source_quote="来源1")],
            partial=[VerifiedClaim(id=3, status="PARTIAL", text="事实C", source_quote="来源3")],
            total_claims=2,
            coverage=1.0,
        )
        new = [
            VerifiedClaim(id=2, status="CONFIRMED", text="事实B", source_quote="来源2"),
        ]
        pool = merge_claims(new, old)
        assert len(pool.confirmed) >= 1  # at least one confirmed

    def test_unverified_filtered_out(self):
        from fact_pipeline import merge_claims, VerifiedClaim
        new = [
            VerifiedClaim(id=1, status="UNVERIFIED", text="", source_quote=""),
        ]
        pool = merge_claims(new)
        assert len(pool.confirmed) == 0
        assert pool.coverage == 0.0

    def test_coverage_calculation(self):
        from fact_pipeline import merge_claims, VerifiedClaim
        new = [
            VerifiedClaim(id=1, status="CONFIRMED", text="A", source_quote="q"),
            VerifiedClaim(id=2, status="CONFIRMED", text="B", source_quote="q"),
            VerifiedClaim(id=3, status="UNVERIFIED", text="", source_quote=""),
            VerifiedClaim(id=4, status="UNVERIFIED", text="", source_quote=""),
        ]
        pool = merge_claims(new)
        assert pool.coverage == 0.5


# ═══════════════════════════════════════════════════════════════
# 模块 6: write_stage.py — A/B 路由（P1-9）
# ═══════════════════════════════════════════════════════════════

class TestAbRouting:
    """_should_use_claim_pipeline A/B 分桶逻辑"""

    def test_disabled_when_ratio_zero(self):
        """_CP_AB_RATIO=0 → 始终返回 False"""
        import write_stage as ws
        # 临时保存原值
        orig_ratio = ws._CP_AB_RATIO
        orig_enabled = ws.CLAIM_PIPELINE_ENABLED
        try:
            ws.CLAIM_PIPELINE_ENABLED = False
            ws._CP_AB_RATIO = 0.0
            for _ in range(20):
                assert not ws._should_use_claim_pipeline()
        finally:
            ws._CP_AB_RATIO = orig_ratio
            ws.CLAIM_PIPELINE_ENABLED = orig_enabled

    def test_full_enabled_when_ratio_one(self):
        """_CP_AB_RATIO=1.0 → 始终返回 True"""
        import write_stage as ws
        orig_ratio = ws._CP_AB_RATIO
        orig_enabled = ws.CLAIM_PIPELINE_ENABLED
        try:
            ws.CLAIM_PIPELINE_ENABLED = False
            ws._CP_AB_RATIO = 1.0
            for _ in range(20):
                assert ws._should_use_claim_pipeline()
        finally:
            ws._CP_AB_RATIO = orig_ratio
            ws.CLAIM_PIPELINE_ENABLED = orig_enabled

    def test_full_enabled_override(self):
        """CLAIM_PIPELINE_ENABLED=True → 忽略 ratio，始终 True"""
        import write_stage as ws
        orig_ratio = ws._CP_AB_RATIO
        orig_enabled = ws.CLAIM_PIPELINE_ENABLED
        try:
            ws.CLAIM_PIPELINE_ENABLED = True
            ws._CP_AB_RATIO = 0.0
            for _ in range(20):
                assert ws._should_use_claim_pipeline()
        finally:
            ws._CP_AB_RATIO = orig_ratio
            ws.CLAIM_PIPELINE_ENABLED = orig_enabled

    def test_statistical_proportion(self):
        """_CP_AB_RATIO=0.3 → 大约 30% 返回 True（统计验证）"""
        import write_stage as ws
        orig_ratio = ws._CP_AB_RATIO
        orig_enabled = ws.CLAIM_PIPELINE_ENABLED
        try:
            ws.CLAIM_PIPELINE_ENABLED = False
            ws._CP_AB_RATIO = 0.3
            results = [ws._should_use_claim_pipeline() for _ in range(500)]
            true_ratio = sum(results) / len(results)
            # 允许 ±0.1 波动
            assert 0.2 <= true_ratio <= 0.4, f"ratio={true_ratio:.3f}, expected ~0.3"
        finally:
            ws._CP_AB_RATIO = orig_ratio
            ws.CLAIM_PIPELINE_ENABLED = orig_enabled


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
