"""
AIToutiao 各阶段功能测试入口（直接调用项目真实函数，非 LLM 模拟）
===============================================================

用法（在仓库根目录执行）：
    python tests/run_stage.py --stage 4
    python tests/run_stage.py --stage 3 --material outputs/20260713/.../transcript.txt
    python tests/run_stage.py --stage 2 --media lib/sensevoice-asr/models/xxx.mp3
    python tests/run_stage.py --stage 1 --url https://...
    python tests/run_stage.py --stage 5 [--article path/to/article.md]

退出码：0=PASS/SKIP，1=FAIL。
测试产物落在 outputs/test_sta/<run_id>/ 下。
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_HERE, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _harness import (  # noqa: E402
    load_engine_app,
    make_state,
    find_latest_article,
    find_latest_transcript,
)


def _print_log(msg: str, level: str = "info") -> None:
    print(f"  [log:{level}] {msg}")


def _print_stage(name: str, status: str) -> None:
    print(f"  [stage] {name} -> {status}")


# ───────────────────────── 阶段1：下载 ─────────────────────────
def run_stage1(engine: Any, args: argparse.Namespace) -> Optional[bool]:
    state = make_state(input_url=args.url or "")
    if not state.input_url:
        print("[阶段1] 跳过：未提供 --url <视频链接>")
        return None
    print(f"[阶段1] 真实调用 step_download，目标: {state.input_url[:60]}...")
    return engine.step_download(state)


# ───────────────────────── 阶段2：转录 ─────────────────────────
def run_stage2(engine: Any, args: argparse.Namespace) -> Optional[bool]:
    media = args.media
    if not media:
        base = Path(_ROOT) / "lib" / "sensevoice-asr" / "models"
        cands = sorted(base.rglob("*.mp3"))
        zh = [c for c in cands if "zh" in c.name.lower()]
        media = str(zh[0] if zh else (cands[0] if cands else None))
    if not media or not Path(media).exists():
        print("[阶段2] 跳过：未提供 --media <音频/视频文件> 且无内置示例")
        return None
    state = make_state()
    state.outputs["video_files"] = [media]
    print(f"[阶段2] 真实调用 step_transcribe，输入: {Path(media).name}")
    return engine.step_transcribe(state)


# ─────────────────────── 阶段3：研究写作 ───────────────────────
def run_stage3(engine: Any, args: argparse.Namespace) -> Optional[bool]:
    from write_stage import research_and_write, PipelineHooks

    state = make_state(
        content_type=args.content_type or "toutie",
        content_style=args.style or "baoming_shuo",
        enable_humanize=bool(args.humanize),
    )

    text: Optional[str] = None
    if args.material and Path(args.material).exists():
        text = Path(args.material).read_text(encoding="utf-8", errors="ignore")
    else:
        tr = find_latest_transcript()
        if tr:
            text = tr.read_text(encoding="utf-8", errors="ignore")
    if not text:
        print("[阶段3] 跳过：无转录素材（--material 或 outputs 下 transcript.txt）")
        return None

    state.outputs["transcript_text"] = text[:2000]
    state.outputs["video_title"] = args.title or "测试素材"

    hooks = PipelineHooks(
        log_fn=_print_log,
        stage_fn=_print_stage,
        progress_fn=lambda p: None,
    )
    print(f"[阶段3] 真实调用 research_and_write（风格={state.content_style}）...")
    ok = research_and_write(state, hooks)
    if ok:
        print(f"[阶段3] 标题: {state.outputs.get('generated_title', '')[:60]}")
        print(f"[阶段3] 字符数: {state.outputs.get('char_count')} "
              f"最佳评分: {state.outputs.get('best_score')}")
    return ok


# ───────────────────────── 阶段4：配图 ─────────────────────────
def run_stage4(engine: Any, args: argparse.Namespace) -> Optional[bool]:
    state = make_state(with_images=True)
    path = Path(args.article) if args.article else find_latest_article()
    if not path or not path.exists():
        print("[阶段4] 跳过：未找到成稿（--article 或 outputs 下 *_ai_raw.md）")
        return None
    content = path.read_text(encoding="utf-8", errors="ignore")
    title = content.split("\n", 1)[0].strip()[:80]
    state.outputs["generated_title"] = title
    state.outputs["generated_content"] = content
    print(f"[阶段4] 真实调用 step_images（Agnes），成稿: {path.name}（{len(content)} 字符）")
    ok = engine.step_images(state)
    cover = state.outputs.get("cover_image")
    inlines = state.outputs.get("inline_images", []) or []
    print(f"[阶段4] step_images 返回={ok} | 封面: {cover or '无'} | 内文图: {len(inlines)} 张")
    generated = bool(cover or inlines)
    if not generated:
        print("[阶段4] ⚠️ 未实际产出图片（Agnes 可能超时/未配置），视为 FAIL")
    return bool(ok) and generated


# ───────────────────────── 阶段5：组装 ─────────────────────────
def run_stage5(engine: Any, args: argparse.Namespace) -> Optional[bool]:
    state = make_state()
    path = Path(args.article) if args.article else find_latest_article()
    if not path or not path.exists():
        print("[阶段5] 跳过：未找到成稿（--article 或 outputs 下 *_ai_raw.md）")
        return None
    content = path.read_text(encoding="utf-8", errors="ignore")
    state.outputs["generated_content"] = content
    state.outputs["generated_title"] = content.split("\n", 1)[0].strip()[:80]
    state.outputs["generated_file"] = str(path)

    # 尝试复用同 run 目录下的阶段4图片
    images_dir = state.run_dir / "images"
    cover = None
    inlines: list[str] = []
    if images_dir.exists():
        cov = sorted(images_dir.glob("cover.*"))
        cover = str(cov[0]) if cov else None
        inlines = [str(p) for p in sorted(images_dir.glob("inline_*.*"))]
    state.outputs["cover_image"] = cover or ""
    state.outputs["inline_images"] = inlines

    print(f"[阶段5] 真实调用 step_assemble（封面={bool(cover)} 内文={len(inlines)}）")
    return engine.step_assemble(state)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="AIToutiao 各阶段功能测试入口（直接调用项目真实函数）")
    ap.add_argument("--stage", required=True, choices=["1", "2", "3", "4", "5"],
                    help="要测试的阶段")
    ap.add_argument("--url", help="阶段1 视频链接")
    ap.add_argument("--media", help="阶段2 音频/视频文件")
    ap.add_argument("--material", help="阶段3 转录素材文件")
    ap.add_argument("--title", help="阶段3 视频标题")
    ap.add_argument("--style", help="阶段3 风格（默认 baoming_shuo）")
    ap.add_argument("--content-type", dest="content_type",
                    help="阶段3 内容类型 toutie/article")
    ap.add_argument("--humanize", action="store_true", help="阶段3 启用人工化")
    ap.add_argument("--article", help="阶段4/5 成稿 md 路径")
    args = ap.parse_args()

    engine = load_engine_app()
    dispatch = {
        "1": run_stage1,
        "2": run_stage2,
        "3": run_stage3,
        "4": run_stage4,
        "5": run_stage5,
    }

    t0 = time.time()
    result = dispatch[args.stage](engine, args)
    dt = time.time() - t0

    if result is None:
        print(f"[结果] 阶段{args.stage} 跳过（SKIP），用时 {dt:.1f}s")
        sys.exit(0)
    status = "PASS" if result else "FAIL"
    print(f"[结果] 阶段{args.stage} {status}，用时 {dt:.1f}s")
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
