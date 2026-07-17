"""
发布测试 — 对指定成稿直接调用 publish_article 发布到今日头条。

用法：
    python tests/test_publish.py

可选参数：
    --article  完整稿件路径（默认 outputs 下最新）
    --headless 无头模式（不显示浏览器界面）
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 控制台 UTF-8 编码（支持 emoji）
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
_BACKEND = _ROOT / "lib" / "toutiao-auto-publisher" / "backend"

for _p in (str(_ROOT), str(_BACKEND)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def find_article(path_hint: str | None = None) -> Path | None:
    if path_hint:
        p = Path(path_hint)
        if p.exists():
            return p
        print(f"[错误] 指定文件不存在: {p}")
        return None
    # 按修改时间找最新完整稿件
    cands = list((_ROOT / "outputs").rglob("完整稿件_配图版.md"))
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def main() -> None:
    ap = argparse.ArgumentParser(description="发布测试：直接调用 publish_article")
    ap.add_argument("--article", help="完整稿件_配图版.md 路径")
    ap.add_argument("--headless", action="store_true", help="无头模式（不显示浏览器界面）")
    args = ap.parse_args()

    article_path = find_article(args.article)
    if not article_path:
        print("[失败] 未找到完整稿件")
        sys.exit(1)

    print(f"文章: {article_path}")
    content = article_path.read_text(encoding="utf-8", errors="ignore")
    run_dir = article_path.parent

    # 提取标题（第1行 # Title）
    title = ""
    lines = content.split("\n", 1)
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
    print(f"标题: {title}")

    # 封面
    cover_image = run_dir / "images" / "cover.png"
    cover_path = str(cover_image) if cover_image.exists() else None
    print(f"封面: {cover_path or '无'}")

    print(f"\n{'='*50}")
    print(f"  即将启动浏览器填写头条编辑器")
    print(f"{'='*50}\n")

    from publisher_service import publish_article

    result = publish_article(
        title=title,
        content=content,
        cover_path=cover_path,
        content_base_dir=str(run_dir),
        headless=args.headless,
    )

    ok = result.get("success", False)
    print(f"\n[结果] {'成功' if ok else '失败'}: {result.get('message', '')}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
