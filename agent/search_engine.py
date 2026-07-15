"""
搜索引擎模块 — Bing API + 搜狗（国内可直连）

多引擎分层策略，按质量与可靠性排序：
  Bing Web Search API（结构化 JSON，零反爬风险）→ 搜狗（免费 fallback）→ 返回空。

使用示例:
    from agent.search_engine import search_web
    results = search_web("Python 最新版本", max_results=5)

环境变量:
    BING_API_KEY  — Microsoft Bing Web Search API v7 密钥（可选，未配置则跳过）
"""

from __future__ import annotations

import json as _json
import os as _os
import re as _re
import sys as _sys
import time as _time
import urllib.parse
import urllib.request
import urllib.error


# ── 通用 User-Agent（模拟正常浏览器） ──
_SEARCH_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def _random_ua() -> str:
    """返回随机 User-Agent 头"""
    import random as _random
    return _random.choice(_SEARCH_USER_AGENTS)


def _fetch_html(url: str, timeout: int = 15) -> str | None:
    """通用 HTTP GET 请求，返回 HTML 文本或 None"""
    headers = {
        "User-Agent": _random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            # 处理 gzip 编码
            content = resp.read()
            content_encoding = resp.headers.get("Content-Encoding", "")
            if "gzip" in content_encoding:
                import gzip
                content = gzip.decompress(content)
            html = content.decode("utf-8", errors="replace")
            return html
    except urllib.error.HTTPError as e:
        _sys.stderr.write(f"[search_engine] HTTP {e.code}: {url[:80]}\n")
        _sys.stderr.flush()
        # 429 限流 → 指数退避重试，404/403 → 立即返回空
        if e.code == 429:
            _time.sleep(2)
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    content = resp.read()
                    content_encoding = resp.headers.get("Content-Encoding", "")
                    if "gzip" in content_encoding:
                        import gzip
                        content = gzip.decompress(content)
                    html = content.decode("utf-8", errors="replace")
                    return html
            except Exception:
                pass
        return None
    except Exception as e:
        _sys.stderr.write(f"[search_engine] 请求异常: {e}\n")
        _sys.stderr.flush()
        return None


# ══════════════════════════════════════════════════════════════
#  Bing Web Search API（首选 — 结构化 JSON，零反爬风险）
# ══════════════════════════════════════════════════════════════

def _search_bing_api(query: str, max_results: int = 5) -> list[str]:
    """通过 Bing Web Search API v7 搜索，返回结构化结果摘要。

    免费层: 1000 次/月，国内可直连。
    需在 .env 中配置 BING_API_KEY（Azure 门户 → 创建 Bing Search 资源 → Keys and Endpoint）。
    """
    api_key = _os.environ.get("BING_API_KEY", "").strip()
    if not api_key:
        _sys.stderr.write("[search_engine] Bing API key 未配置，跳过\n")
        _sys.stderr.flush()
        return []

    encoded = urllib.parse.quote(query)
    url = (
        f"https://api.bing.microsoft.com/v7.0/search"
        f"?q={encoded}&count={max_results}&mkt=zh-CN&responseFilter=Webpages"
    )
    headers = {
        "Ocp-Apim-Subscription-Key": api_key,
        "User-Agent": _random_ua(),
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        _sys.stderr.write(f"[search_engine] Bing API HTTP {e.code}: {e.reason}\n")
        _sys.stderr.flush()
        return []
    except Exception as e:
        _sys.stderr.write(f"[search_engine] Bing API 异常: {e}\n")
        _sys.stderr.flush()
        return []

    results: list[str] = []
    web_pages = data.get("webPages", {}).get("value", [])
    for page in web_pages[:max_results]:
        name = page.get("name", "")
        snippet = page.get("snippet", "")
        url_str = page.get("url", "")
        # 组合「标题 + 摘要 + URL」为一条结果
        parts = []
        if name:
            parts.append(name)
        if snippet:
            parts.append(snippet)
        combined = " — ".join(parts)
        if not combined or len(combined) < 10:
            continue
        # 附加来源 URL（方便事实核实）
        if url_str:
            combined += f" [来源: {url_str}]"
        results.append(combined)

    _sys.stderr.write(f"[search_engine] Bing API 返回 {len(results)} 条\n")
    _sys.stderr.flush()
    return results


# ══════════════════════════════════════════════════════════════
#  百度搜索（保留但不再作为首选，结果以广告/采购为主）
# ══════════════════════════════════════════════════════════════

def _search_baidu(query: str, max_results: int = 5) -> list[str]:
    """通过 HTTP 抓取百度搜索结果摘要。

    解析百度搜索结果页面，提取每条结果的摘要文本。
    返回结果摘要列表。
    """
    encoded = urllib.parse.quote(query)
    url = f"https://www.baidu.com/s?wd={encoded}&ie=utf-8&rn={max_results}"

    html = _fetch_html(url, timeout=15)
    if not html:
        _sys.stderr.write("[search_engine] 百度返回空\n")
        _sys.stderr.flush()
        return []

    results: list[str] = []

    # ── 策略 1: 匹配百度结果摘要（新版百度页面结构） ──
    # 匹配 <span class="content-right_XXX"> 内的文本
    snippets = _re.findall(
        r'<span[^>]*class="[^"]*content-right[^"]*"[^>]*>(.*?)</span>',
        html, _re.DOTALL,
    )
    for s in snippets:
        clean = _strip_html(s)
        if clean and len(clean) > 15 and len(clean) < 2000:
            results.append(clean)

    # ── 策略 2: 匹配 c-abstract / c-span 等常见 class ──
    if len(results) < max_results:
        for pattern in [
            r'<span[^>]*class="[^"]*c-abstract[^"]*"[^>]*>(.*?)</span>',
            r'<div[^>]*class="[^"]*c-abstract[^"]*"[^>]*>(.*?)</div>',
        ]:
            extra = _re.findall(pattern, html, _re.DOTALL)
            for s in extra:
                clean = _strip_html(s)
                if clean and len(clean) > 15 and clean not in results:
                    results.append(clean)

    # ── 策略 3: 宽松匹配 — 匹配长文本片段 ──
    if len(results) < max_results:
        # 匹配 <em> 标签包围的高亮区域附近的文本
        blocks = _re.findall(
            r'<(?:span|div|p|font)[^>]*>(.{20,600}?)</(?:span|div|p|font)>',
            html, _re.DOTALL,
        )
        for b in blocks:
            clean = _strip_html(b)
            if clean and len(clean) > 20 and clean not in results:
                # 跳过明显的非内容文本（导航、时间、数字等）
                if not _is_noise_text(clean):
                    results.append(clean)

    _sys.stderr.write(f"[search_engine] 百度返回 {len(results[:max_results])} 条\n")
    _sys.stderr.flush()
    return results[:max_results]


# ══════════════════════════════════════════════════════════════
#  搜狗搜索
# ══════════════════════════════════════════════════════════════

def _search_sogou(query: str, max_results: int = 5) -> list[str]:
    """通过 HTTP 抓取搜狗搜索结果摘要。

    2026-07-15 修复：str_info / str-text 选择器已过期（0 命中），
    改用新版 DOM 模式 + <em> 高亮区块 + JSON 噪音过滤。
    """
    encoded = urllib.parse.quote(query)
    url = f"https://www.sogou.com/web?query={encoded}&ie=utf8"

    html = _fetch_html(url, timeout=15)
    if not html:
        _sys.stderr.write("[search_engine] 搜狗返回空\n")
        _sys.stderr.flush()
        return []

    # 预清除 <style> / <script> 块，避免 CSS/JS 噪音混入结果
    html = _re.sub(r'<style[^>]*>.*?</style>', '', html, flags=_re.DOTALL | _re.IGNORECASE)
    html = _re.sub(r'<script[^>]*>.*?</script>', '', html, flags=_re.DOTALL | _re.IGNORECASE)

    results: list[str] = []

    # ── 策略 1: 新版搜狗结果容器（vrwrap / result / rb） ──
    for pattern in [
        # vrwrap 容器内的文本块（新版搜狗）
        r'<div[^>]*class="[^"]*(?:vrwrap|vrwrap[^"]*)"[^>]*>(.*?)</div>\s*</div>\s*</div>',
        # rb 类结果块
        r'<div[^>]*class="[^"]*(?:rb|result)[^"]*"[^>]*>(.*?)</div>\s*</div>',
        # 通用摘要类
        r'<(?:p|div|span)[^>]*class="[^"]*(?:abstract|space-txt|summary|desc)[^"]*"[^>]*>(.*?)</(?:p|div|span)>',
    ]:
        snippets = _re.findall(pattern, html, _re.DOTALL)
        for s in snippets:
            clean = _strip_html(s)
            if clean and 15 < len(clean) < 2000:
                if not _is_noise_text(clean) and not _is_json_noise(clean):
                    if clean not in results:
                        results.append(clean)

    # ── 策略 2: <em> 高亮区块提取（搜狗最可靠信号） ──
    if len(results) < max_results:
        blocks = _re.findall(
            r'<(?:p|div|span|a|h\d)[^>]*>((?:(?!<(?:p|div|span|a|h\d)\b).)*?<em>.*?</em>.*?)</(?:p|div|span|a|h\d)>',
            html, _re.DOTALL,
        )
        for b in blocks:
            clean = _strip_html(b)
            if clean and len(clean) > 15 and clean not in results:
                if not _is_noise_text(clean) and not _is_json_noise(clean):
                    results.append(clean)

    # ── 策略 3: 宽松匹配 — 长文本块 ──
    if len(results) < max_results:
        blocks = _re.findall(
            r'<(?:p|div|span|font)[^>]*>(.{25,600}?)</(?:p|div|span|font)>',
            html, _re.DOTALL,
        )
        for b in blocks:
            clean = _strip_html(b)
            if clean and len(clean) > 20 and clean not in results:
                if not _is_noise_text(clean) and not _is_json_noise(clean):
                    results.append(clean)

    _sys.stderr.write(f"[search_engine] 搜狗返回 {len(results[:max_results])} 条\n")
    _sys.stderr.flush()
    return results[:max_results]


# ══════════════════════════════════════════════════════════════
#  工具函数
# ══════════════════════════════════════════════════════════════

def _strip_html(text: str) -> str:
    """移除 HTML 标签和实体引用，返回纯文本"""
    # 移除 HTML 标签
    clean = _re.sub(r'<[^>]+>', '', text)
    # 解码常见 HTML 实体
    clean = clean.replace("&amp;", "&")
    clean = clean.replace("&lt;", "<")
    clean = clean.replace("&gt;", ">")
    clean = clean.replace("&quot;", '"')
    clean = clean.replace("&#39;", "'")
    clean = clean.replace("&nbsp;", " ")
    clean = clean.replace("\u00a0", " ")  # non-breaking space
    # 清理多余空白
    clean = _re.sub(r'\s+', ' ', clean).strip()
    # 移除零宽字符
    clean = _re.sub(r'[\u200b\u200c\u200d\u2060\ufeff]', '', clean)
    return clean


def _is_noise_text(text: str) -> bool:
    """判断是否为噪音文本（导航、时间戳、纯数字等）"""
    if not text:
        return True
    # 纯数字、日期、时间格式
    if _re.match(r'^[\d\-\/:\.\s,，年月日时分秒]+$', text):
        return True
    # 纯导航类文字
    noise_patterns = [
        r'^(上一页|下一页|首页|末页|更多|搜索|百度|搜狗|登录|注册|下载)$',
        r'^\d{4}-\d{2}-\d{2}$',  # 日期格式
        r'^\d+分钟前$',          # 相对时间
        r'^\d+小时前$',
        r'^\d+天前$',
        r'^loading\.{3}$',
    ]
    for pat in noise_patterns:
        if _re.match(pat, text, _re.IGNORECASE):
            return True
    return False


def _is_json_noise(text: str) -> bool:
    """判断是否为 JSON / JS / CSS 数据噪音（搜狗页面常混入元数据或样式块）。

    检测特征：JSON 对象/数组字面量、大量转义引号、纯 JS 赋值表达式、
    CSS 规则块 (`.class { prop: val; }`)、或 `"key":` 模式开头的行。
    """
    if not text:
        return False
    stripped = text.strip()
    # JSON 对象开头
    if stripped.startswith("{") and ("\"classId\"" in stripped or "\"cardInfo\"" in stripped):
        return True
    # JSON 数组开头
    if stripped.startswith("[") and stripped.endswith("]"):
        return True
    # 大量转义字符（JSON 内嵌 HTML）
    escaped_count = stripped.count("\\\"") + stripped.count("\\\\")
    if escaped_count > 5 and len(stripped) > 100:
        return True
    # JS 赋值表达式（如 var xxx = {...}）
    if _re.match(r'^(?:var|let|const)\s+\w+\s*=\s*[\{\[]', stripped):
        return True
    # cardInfo / qqBrowser 等元数据 blob
    if any(kw in stripped for kw in ["cardInfo", "qqBrowserVersion", "isQB"]):
        return True
    # 纯 JS 函数/回调
    if _re.match(r'^(?:function|callback|window\.)', stripped):
        return True
    # CSS 规则块（.classname { property: value; }）
    if _re.search(r'\.[a-z][\w-]*\s*\{[^}]*\}', stripped):
        return True
    return False


# ══════════════════════════════════════════════════════════════
#  统一搜索入口
# ══════════════════════════════════════════════════════════════

def search_web(query: str, max_results: int = 5) -> str:
    """多引擎分层搜索，返回聚合的搜索结果摘要（纯文本）。

    策略：Bing API（首选，结构化 JSON）→ 搜狗（免费 fallback）→ 返回空字符串。

    Args:
        query: 搜索关键词
        max_results: 最大返回结果数

    Returns:
        用换行分隔的结果摘要文本，每行以 "- " 开头。
        如果所有引擎均失败，返回空字符串。
    """
    if not query or not query.strip():
        return ""

    query = query.strip()

    # ── 方案一：Bing Web Search API（首选 — 结构化 JSON，零反爬风险） ──
    try:
        _sys.stderr.write(f"[research] Bing API 搜索: {query[:60]}\n")
        _sys.stderr.flush()
        bing_results = _search_bing_api(query, max_results)
        if bing_results:
            formatted = "\n".join(f"- {r[:400]}" for r in bing_results[:max_results])
            return formatted
        _sys.stderr.write("[research] Bing API 无结果/未配置，尝试搜狗\n")
        _sys.stderr.flush()
    except Exception as e:
        _sys.stderr.write(f"[research] Bing API 异常: {e}，尝试搜狗\n")
        _sys.stderr.flush()

    # ── 方案二：搜狗搜索（免费 fallback） ──
    try:
        _time.sleep(0.5)  # 避免请求过快
        _sys.stderr.write(f"[research] 搜狗搜索: {query[:60]}\n")
        _sys.stderr.flush()
        sogou_results = _search_sogou(query, max_results)
        if sogou_results:
            formatted = "\n".join(f"- {r[:400]}" for r in sogou_results[:max_results])
            return formatted
    except Exception as e:
        _sys.stderr.write(f"[research] 搜狗异常: {e}\n")
        _sys.stderr.flush()

    _sys.stderr.write("[research] 所有搜索引擎均无结果\n")
    _sys.stderr.flush()
    return ""
