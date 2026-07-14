"""
头条作者文章/微头条批量采集脚本（Agentic Workflow · Phase 1）

采集 4 位作者各 N 篇「高赞文本原文」，按 {作者}/{作者}_{标题}.md 落盘到 docs/采集/。
- 搜索结果页算法热度排序作为「高赞」代理信号（作者主页需登录，无法直接读点赞榜）
- 内容形态自适应：article 全文 / 微头条文本，frontmatter 标注 content_type
- 真实文章 URL 藏在 search/jump?...&url=<编码> 的 groupid 参数中，解码后构造
  https://www.toutiao.com/article/{groupid}/ （即已验证可用的详情页地址）
- 多 tab（synthesis/information/weitoutiao）兜底 + 加大滚动，尽量凑足每作者 10 篇
- 5s 间隔防风控；失败跳过不阻断

用法:
    python scripts/toutiao_collect.py            # 采集全部 4 作者各 10 篇
    python scripts/toutiao_collect.py 包明说 2    # 仅某作者，限 2 篇（冒烟测试用）
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(r"d:/AIToutiao-Engine")
OUT = ROOT / "docs" / "采集"
OUT.mkdir(parents=True, exist_ok=True)

AUTHORS = ["包明说", "听风的蚕", "晋说", "全球档案馆"]
PER_AUTHOR = 10
DELAY = 5  # 篇间间隔（秒），防风控
SCROLLS = 15


def normalize_title(t: str) -> str:
    t = re.sub(r'[\\/:*?"<>|\r\n]+', "_", t).strip().strip("_")
    return t[:60]


def real_url_from(target: str) -> str | None:
    """从解码后的 jump 目标里提取 groupid，构造真实文章详情页 URL。"""
    m = re.search(r"groupid=(\d+)", target)
    if m:
        return f"https://www.toutiao.com/article/{m.group(1)}/"
    m = re.search(r"m\.toutiao\.com/i(\d+)", target)
    if m:
        return f"https://www.toutiao.com/article/{m.group(1)}/"
    if re.search(r"toutiao\.com/(?:article|group)/\d", target):
        return target
    return None


def extract_cards(page) -> list[dict]:
    """抽取候选卡片：解码 search/jump 的 url 参数 → groupid → 真实详情页 URL。"""
    return page.evaluate(
        """() => {
            const cards = [];
            const links = Array.from(document.querySelectorAll('a[href]'));
            for (const a of links) {
                const href = a.href || '';
                let target = null;
                if (href.includes('search/jump')) {
                    try {
                        const u = new URL(href);
                        const enc = u.searchParams.get('url');
                        if (enc) target = decodeURIComponent(enc);
                    } catch (e) {}
                } else if (/toutiao\\.com\\/(?:article|group)\\d/i.test(href)) {
                    target = href;
                }
                if (!target) continue;
                // 解析真实 groupid
                let real = null;
                let m = target.match(/groupid=(\\d+)/);
                if (m) real = 'https://www.toutiao.com/article/' + m[1] + '/';
                else {
                    m = target.match(/m\\.toutiao\\.com\\/i(\\d+)/);
                    if (m) real = 'https://www.toutiao.com/article/' + m[1] + '/';
                    else if (/toutiao\\.com\\/(?:article|group)\\/\\d/i.test(target)) real = target;
                }
                if (!real) continue;
                const title = (a.innerText || '').replace(/\\s+/g, ' ').trim();
                cards.push({ title, href: real });
            }
            const seen = new Set();
            const out = [];
            for (const c of cards) {
                if (!seen.has(c.href)) { seen.add(c.href); out.push(c); }
            }
            return out;
        }"""
    )


def get_page_title(page) -> str:
    return page.evaluate(
        """() => {
            const h = document.querySelector('h1')
                  || document.querySelector('[class*="title" i]');
            if (h && h.innerText && h.innerText.trim().length > 2) return h.innerText.trim();
            return (document.title || '').trim();
        }"""
    )


def get_text(page):
    art = page.query_selector("article")
    if art:
        txt = art.inner_text()
        if len(txt.strip()) > 200:
            return txt.strip(), "article"
    txt = page.evaluate(
        """() => {
            const cands = Array.from(document.querySelectorAll('div, article, section'));
            let best = '', bestLen = 0;
            for (const el of cands) {
                const t = (el.innerText || '').replace(/\\s+/g, ' ').trim();
                if (t.length > bestLen) { bestLen = t.length; best = t; }
            }
            return best;
        }"""
    )
    return txt.strip(), "weitoutiao"


def collect_author(page, author: str, limit: int | None) -> int:
    adir = OUT / author
    adir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== {author} ===")

    collected = 0
    seen_titles: set[str] = set()

    for pd in ("synthesis", "information", "weitoutiao"):
        if limit and collected >= limit:
            break
        try:
            page.goto(
                f"https://so.toutiao.com/search?keyword={author}&pd={pd}",
                wait_until="domcontentloaded",
                timeout=30000,
            )
        except Exception as e:
            print(f"  [{pd}] 搜索页加载失败: {e}")
            continue
        time.sleep(3)
        for _ in range(SCROLLS):
            page.mouse.wheel(0, 2500)
            time.sleep(1.0)

        cards = extract_cards(page)
        print(f"  [{pd}] 候选卡片: {len(cards)}")
        scan = cards[: (limit * 3) if limit else None]

        for card in scan:
            if limit and collected >= limit:
                break
            url = card["href"]
            search_title = card["title"]
            if search_title in seen_titles:
                continue
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(2)
                for _ in range(3):
                    page.keyboard.press("PageDown")
                    time.sleep(0.8)
                txt, ctype = get_text(page)
                if len(txt) < 100:
                    print(f"    跳过(文本过短 {len(txt)}字): {search_title[:20]}")
                    continue
                real_title = get_page_title(page) or search_title
                fname = f"{author}_{normalize_title(real_title)}.md"
                fpath = adir / fname
                if fpath.exists():
                    print(f"  - 已存在，跳过: {real_title[:20]}")
                    collected += 1
                    seen_titles.add(search_title)
                    continue
                front = (
                    f"---\nsource: \"{url}\"\nauthor: \"{author}\"\n"
                    f"title: \"{real_title}\"\ncontent_type: \"{ctype}\"\n"
                    f"tab: \"{pd}\"\ncollected_at: \"{time.strftime('%Y-%m-%d %H:%M')}\"\n---\n\n"
                )
                fpath.write_text(front + txt, encoding="utf-8")
                print(f"  [OK] [{pd}/{ctype}] {real_title} ({len(txt)}字)")
                collected += 1
                seen_titles.add(search_title)
            except Exception as e:
                print(f"  [FAIL] {search_title[:20]}: {e}")
            time.sleep(DELAY)

    print(f"  {author} 本批采集 {collected} 篇")
    return collected


def main():
    arg_author = sys.argv[1] if len(sys.argv) > 1 else None
    arg_limit = int(sys.argv[2]) if len(sys.argv) > 2 else None

    targets = [arg_author] if arg_author else AUTHORS
    print(f"目标作者: {targets}  每作者上限: {arg_limit or PER_AUTHOR}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            locale="zh-CN",
        )
        page = ctx.new_page()
        page.set_default_timeout(30000)
        for author in targets:
            collect_author(page, author, arg_limit)
            time.sleep(2)
        browser.close()
    print("\n采集完成。")


if __name__ == "__main__":
    main()
