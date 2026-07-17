"""直连测试：上传草稿（跳过 state.json 检查，直接用 browser_profile 中的 cookie）。"""
import sys, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "toutiao-auto-publisher" / "backend"))
from publisher_service import publish_article

md_file = Path(r"outputs/20260717/20260717_111558/完整稿件_配图版.md")
content = md_file.read_text(encoding="utf-8")
title_match = re.match(r'^#\s*(.+)', content)
title = title_match.group(1).strip() if title_match else "无标题"

cover = Path(r"outputs/20260717/20260717_111558/images/cover.png")

print(f"标题: {title[:50]}")
print(f"正文字数: {len(content)} 字符")
print(f"封面: {'有' if cover.exists() else '无'}")
print("启动浏览器上传草稿（仅填充不发布）...\n")

result = publish_article(
    title=title,
    content=content,
    cover_path=str(cover) if cover.exists() else None,
    content_base_dir=str(md_file.parent),  # 用于解析 markdown 中的相对图片路径
    auto_publish=False,
    headless=False,
)

print(f"\n成功: {result.get('success')}")
print(f"消息: {result.get('message')}")
if result.get("success"):
    print("\n请到 https://mp.toutiao.com 查看草稿箱")
