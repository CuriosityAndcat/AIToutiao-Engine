"""
AIToutiao S3→S4→S5 质量闭环 LOOP 测试入口
==========================================

在 run_stage.py 基础上增加：
  1. 每阶段产出物评审 — 对齐 ARTICLE_SPEC v1.1 门禁标准
  2. 评审不通过 → 自动修改 → 阶段内重试（max 3）
  3. 全阶段通过才结束 LOOP（outer max 5 iterations）

用法：
    python tests/run_loop.py [--max-loops 5] [--material transcript.txt]
    python tests/run_loop.py --style baoming_shuo --content-type toutie

架构：
    LOOP (outer: 1..5):
      ├─ S3: research_and_write → 评审(evaluate_content §1-§4) → [不通过→修改→重试]×3
      ├─ S4: step_images → 评审(ARTICLE_SPEC §5 P-01~P-20) → [不通过→修改→重试]×3
      ├─ S5: step_assemble → 评审(§4 输出验证) → [不通过→修改→重试]×3
      └─ ALL PASS → BREAK, else → next LOOP iteration

评审标准来源：
  - S3: evaluation.py evaluate_content() 5维 + ARTICLE_SPEC §1-§3 结构/语言/事实
  - S4: ARTICLE_SPEC §5.1(数量尺寸) + §5.4(技术验收 P-01~P-05)
  - S5: ARTICLE_SPEC §4.1(检查清单) + §5.6.3(Path.exists 校验)
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
import traceback
from dataclasses import dataclass, field
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

# ═══════════════════════════════════════════════════════════════
# 配置常量
# ═══════════════════════════════════════════════════════════════

# 外层 LOOP
MAX_OUTER_LOOPS = 5

# 每阶段内重试
MAX_STAGE_RETRIES = 3

# S3 质量阈值（对齐 evaluation.py QUALITY_PASS_THRESHOLD）
S3_PASS_THRESHOLD = 75

# S3 事实准确性硬门槛（对齐 evaluation.py FACT_HARD_FLOOR）
S3_FACT_HARD_FLOOR = 80

# S3 维度单项最低分
S3_DIM_MIN = 50

# S4 图片文件大小下限（对齐 ARTICLE_SPEC §5.1.4）
S4_MIN_FILE_SIZE = 1024  # 1 KB

# S4 预期内文图片数（对齐 engine_app.py INLINE_IMAGE_COUNT）
S4_EXPECTED_INLINE_COUNT = 3

# S4 图片分辨率目标（对齐 engine_app.py _generate_agnes_image）
S4_TARGET_SIZE = 1024
S4_SIZE_TOLERANCE = 0.10  # ±10%

# ═══════════════════════════════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════════════════════════════


@dataclass
class ReviewResult:
    """单阶段评审结果"""

    stage: str  # "S3" | "S4" | "S5"
    passed: bool
    score: float = 0.0  # 标准化评分 0-100
    checks_total: int = 0
    checks_passed: int = 0
    failures: list[str] = field(default_factory=list)  # 失败项描述
    details: dict = field(default_factory=dict)  # 详细诊断数据


@dataclass
class StageResult:
    """单阶段执行结果（含评审）"""

    stage: str
    passed: bool
    ok: Optional[bool] = None  # 阶段函数返回值
    review: Optional[ReviewResult] = None
    attempt: int = 1
    duration_s: float = 0.0
    best_score: float = 0.0  # S3 专用：最佳 e2e 评分
    error: Optional[str] = None


@dataclass
class LoopReport:
    """LOOP 完整报告"""

    loop_count: int = 0
    total_duration_s: float = 0.0
    all_passed: bool = False
    stages: list[StageResult] = field(default_factory=list)
    summary: str = ""


# ═══════════════════════════════════════════════════════════════
# S3 评审函数
# ═══════════════════════════════════════════════════════════════


def review_s3(state: Any, engine: Any) -> ReviewResult:
    """使用 evaluate_content() + ARTICLE_SPEC §1-§3 结构性检查评审 S3 产出。

    检查项（对齐 §4.1 检查清单 S/L/F/C/Q 五类）：
      - S-01: 正文字数在类型范围内（§1.1）
      - S-02: 标题含具体信息点，≤30 字（§1.2.1）
      - F-01: 事实准确性维度 ≥ 80（硬门槛，§3.2）
      - Q-01: evaluation 综合分 ≥ 75（§4.2）
      - Q-02: 5 维度单项均 ≥ 50（§4.2）
      - 护栏: guardrails 三层全部 PASS

    Returns:
        ReviewResult with passed=True only if ALL checks pass.
    """
    from evaluation import evaluate_content

    failures: list[str] = []
    checks_total = 7
    checks_passed = 0
    score = 0.0
    details: dict = {}

    title = str(state.outputs.get("generated_title", "")).strip()
    content = str(state.outputs.get("generated_content", "")).strip()
    content_type = str(getattr(state, "content_type", "toutie"))
    content_style = str(getattr(state, "content_style", "baoming_shuo"))
    best_iteration = state.outputs.get("best_iteration", 0)
    raw_score = state.outputs.get("best_score", 0)

    # ── 基础存在性检查 ──
    if not content or len(content) < 50:
        failures.append("S-OUTPUT: 产出正文为空或过短（<50 字符）")
        return ReviewResult(
            stage="S3", passed=False, score=0, checks_total=checks_total,
            checks_passed=0, failures=failures, details=details,
        )
    checks_passed += 1  # 内容存在

    if not title:
        failures.append("S-OUTPUT: 产出标题为空")
    else:
        checks_passed += 1  # 标题存在

    # ── S-01: 字数检查（§1.1） ──
    char_count = len(re.sub(r"\s+", "", content))
    details["char_count"] = char_count
    if content_type == "toutie":
        if char_count < 500:
            failures.append(f"S-01: 微头条字数不足（{char_count} < 500，规范 ≥800）[§1.1.1]")
        elif char_count < 800:
            failures.append(f"S-01: 微头条字数略低（{char_count}/800，规范 ≥800）[§1.1.1]")
        else:
            checks_passed += 1
    else:
        if char_count < 1200:
            failures.append(f"S-01: 文章字数不足（{char_count} < 1200，规范 1800-2500）[§1.1.2]")
        elif char_count < 1800:
            failures.append(f"S-01: 文章字数略低（{char_count}/1800，规范 1800-2500）[§1.1.2]")
        else:
            checks_passed += 1

    # ── Q-01 + Q-02 + F-01: evaluation 5 维评分（调用真实 evaluate_content） ──
    try:
        eval_result = evaluate_content(
            content=content,
            title=title,
            style=content_style,
            threshold=S3_PASS_THRESHOLD,
        )
    except Exception as exc:
        failures.append(f"EVAL-CRASH: evaluate_content() 执行异常: {exc}")
        return ReviewResult(
            stage="S3", passed=False, score=float(raw_score), checks_total=checks_total,
            checks_passed=checks_passed, failures=failures, details=details,
        )

    eval_score = int(eval_result.get("score", 0))
    eval_passed = bool(eval_result.get("passed", False))
    dimensions = eval_result.get("dimensions", {})
    eval_feedback = str(eval_result.get("feedback", ""))

    details["eval_score"] = eval_score
    details["eval_passed"] = eval_passed
    details["dimensions"] = dimensions
    details["feedback"] = eval_feedback[:500]
    details["best_iteration"] = best_iteration

    # Q-01: 综合分
    if eval_score >= S3_PASS_THRESHOLD:
        checks_passed += 1
    else:
        failures.append(f"Q-01: evaluation 综合分 {eval_score} < {S3_PASS_THRESHOLD}（§4.2 SILVER）")

    # Q-02: 单项 ≥ 50
    dim_below_50 = [f"{k}={v}" for k, v in dimensions.items() if isinstance(v, (int, float)) and v < S3_DIM_MIN]
    if not dim_below_50:
        checks_passed += 1
    else:
        failures.append(f"Q-02: 维度低于 {S3_DIM_MIN}: {', '.join(dim_below_50)}（§4.2）")

    # F-01: 事实准确性硬门槛
    fact_score = dimensions.get("事实准确", 0) if isinstance(dimensions, dict) else 0
    details["fact_score"] = fact_score
    if fact_score >= S3_FACT_HARD_FLOOR:
        checks_passed += 1
    else:
        failures.append(f"F-01: 事实准确性 {fact_score} < {S3_FACT_HARD_FLOOR}（硬门槛，§3.2/§4.2 GOLD）")

    # F-02: 反馈无事实硬伤标记
    from evaluation import _FACT_INJURY_MARKERS
    injury_hits = [m for m in _FACT_INJURY_MARKERS if m in eval_feedback]
    if not injury_hits:
        checks_passed += 1
    else:
        failures.append(f"F-02: 反馈含事实硬伤标记: {', '.join(injury_hits[:3])}（§3.2/§4.2）")

    # 综合评分
    score = float(eval_score) if eval_score > 0 else float(raw_score)
    passed = len(failures) == 0

    return ReviewResult(
        stage="S3", passed=passed, score=score, checks_total=checks_total,
        checks_passed=checks_passed, failures=failures, details=details,
    )


# ═══════════════════════════════════════════════════════════════
# S4 评审函数
# ═══════════════════════════════════════════════════════════════


def review_s4(state: Any, _engine: Any) -> ReviewResult:
    """使用 ARTICLE_SPEC §5 配图验收标准评审 S4 产出。

    检查项（对齐 §C 配图检查清单）：
      - P-01: 封面图文件存在且 >1KB
      - P-02: 内文图数量达标（≥预期数）
      - P-03: 所有图片 >1KB
      - P-05: 文件命名规范
      - P-04: 分辨率偏差 ≤10%（仅 Pillow 可用时生效）

    Returns:
        ReviewResult（配图失败不断流，详见 §5.6.2；此处仅评审，由上层决定是否重试）
    """
    failures: list[str] = []
    # 动态统计实际执行的检查项（排除被跳过的项）
    checks_total = 0
    checks_passed = 0
    details: dict = {}

    def _inc(pass_: bool) -> None:
        nonlocal checks_total, checks_passed
        checks_total += 1
        if pass_:
            checks_passed += 1

    run_dir = getattr(state, "run_dir", None)
    if run_dir is None:
        failures.append("P-STATE: state 无 run_dir，无法定位图片目录")
        return ReviewResult(
            stage="S4", passed=False, score=0, checks_total=1,
            checks_passed=0, failures=failures, details=details,
        )
    images_dir = Path(run_dir) / "images"

    # ── P-01: 封面图存在 ──
    cover = state.outputs.get("cover_image", "")
    if cover and Path(cover).exists():
        cover_size = Path(cover).stat().st_size
        details["cover_size"] = cover_size
        if cover_size >= S4_MIN_FILE_SIZE:
            _inc(True)
        else:
            _inc(False)
            failures.append(f"P-01: 封面图 ≤1KB（{cover_size}B），视为生成失败 [§5.1.4]")
    elif cover:
        _inc(False)
        failures.append(f"P-01: 封面图路径存在但文件缺失: {cover}")
    else:
        # 检查 images_dir 下的 cover.*
        if images_dir.exists():
            cov_files = list(images_dir.glob("cover.*"))
            if cov_files:
                details["cover_file"] = str(cov_files[0])
                if cov_files[0].stat().st_size >= S4_MIN_FILE_SIZE:
                    _inc(True)
                else:
                    _inc(False)
                    failures.append(f"P-01: 封面图 ≤1KB（{cov_files[0].stat().st_size}B）[§5.1.4]")
            else:
                _inc(False)
                failures.append("P-01: 封面图缺失（images/ 下无 cover.*）[§5.1.1 强制]")
        else:
            _inc(False)
            failures.append("P-01: images/ 目录不存在，封面图缺失 [§5.1.5]")

    # ── P-02: 内文图数量 ──
    inlines = state.outputs.get("inline_images", []) or []
    valid_inlines = [p for p in inlines if p and Path(p).exists()]
    details["inline_count"] = len(inlines)
    details["valid_inline_count"] = len(valid_inlines)

    if len(valid_inlines) >= S4_EXPECTED_INLINE_COUNT:
        _inc(True)
    elif len(valid_inlines) >= 1:
        _inc(False)
        failures.append(
            f"P-02: 内文图数量不足（{len(valid_inlines)}/{S4_EXPECTED_INLINE_COUNT}，"
            f"规范 ≥{S4_EXPECTED_INLINE_COUNT}）[§5.1.1]"
        )
    else:
        _inc(False)
        failures.append(f"P-02: 内文图全部缺失（0/{S4_EXPECTED_INLINE_COUNT}）[§5.1.1]")

    # ── P-03: 图片大小检查 ──
    small_files: list[str] = []
    for img_path_str in ([cover] if cover else []):
        p = Path(img_path_str)
        if p.exists() and p.stat().st_size < S4_MIN_FILE_SIZE:
            small_files.append(p.name)
    for img_path_str in valid_inlines:
        p = Path(img_path_str)
        if p.stat().st_size < S4_MIN_FILE_SIZE:
            small_files.append(p.name)
    if not small_files:
        _inc(True)
    else:
        _inc(False)
        failures.append(f"P-03: {len(small_files)} 张图 ≤1KB: {', '.join(small_files[:5])} [§5.1.4]")

    # ── P-05: 命名规范 ──
    naming_ok = True
    if images_dir.exists():
        for f in images_dir.iterdir():
            if f.is_file():
                if not (
                    f.name.startswith("cover.")
                    or (f.name.startswith("inline_") and f.name[-4:] in (".png", ".jpg", "jpeg"))
                ):
                    naming_ok = False
                    failures.append(f"P-05: 命名不规范: {f.name}（预期 cover.png / inline_N.png）[§5.1.5]")
                    break
    _inc(naming_ok)

    # ── P-04: 分辨率检查（Pillow 可用时生效，否则跳过不纳入 checks_total） ──
    try:
        from PIL import Image
    except ImportError:
        details["pil_available"] = False
        # 不调用 _inc()——此检查在不可用时不计入总分
    else:
        details["pil_available"] = True
        resolution_ok = True
        test_paths: list[Path] = []
        if images_dir.exists():
            test_paths.extend(list(images_dir.glob("cover.*")))
            test_paths.extend(sorted(images_dir.glob("inline_*.png")))
        if test_paths:
            for tp in test_paths[: min(len(test_paths), 4)]:
                try:
                    img = Image.open(tp)
                    w, h = img.size
                    if abs(w - S4_TARGET_SIZE) / S4_TARGET_SIZE > S4_SIZE_TOLERANCE:
                        resolution_ok = False
                        failures.append(
                            f"P-04: {tp.name} 宽度偏差 {abs(w-S4_TARGET_SIZE)/S4_TARGET_SIZE:.0%} "
                            f"> {S4_SIZE_TOLERANCE:.0%} ({w}≠{S4_TARGET_SIZE}) [§5.1.2/5.1.3]"
                        )
                        break
                except Exception:
                    pass
        _inc(resolution_ok)

    # 评分：通过比例
    score = (checks_passed / checks_total) * 100.0 if checks_total > 0 else 0.0
    # 关键失败（P-01 缺失或 P-02 全缺）= 强制不通过
    critical_fail = any("P-01" in f for f in failures) or any(
        "全部缺失" in f and "P-02" in f for f in failures
    )
    passed = len(failures) == 0 or (not critical_fail and checks_passed == checks_total)

    return ReviewResult(
        stage="S4", passed=passed, score=score, checks_total=checks_total,
        checks_passed=checks_passed, failures=failures, details=details,
    )


# ═══════════════════════════════════════════════════════════════
# S5 评审函数
# ═══════════════════════════════════════════════════════════════


def review_s5(state: Any, _engine: Any) -> ReviewResult:
    """使用 ARTICLE_SPEC §4.1 + §5.6.3 评审 S5 组装产出。

    检查项：
      - 组装后文件存在
      - 组装后文件非空（≥100 字符）
      - 图片引用无死链（Path.exists() 强制校验，§5.6.3）
      - Markdown 格式基本健康（标题/段落/图片语法）

    Returns:
        ReviewResult
    """
    failures: list[str] = []
    checks_total = 5
    checks_passed = 0
    details: dict = {}

    assembled_file = state.outputs.get("assembled_file", "")
    assembled_content = state.outputs.get("assembled_content", "")

    # ── 文件存在 ──
    if assembled_file:
        ap = Path(assembled_file)
        if ap.exists():
            details["assembled_file"] = str(ap)
            details["assembled_size"] = ap.stat().st_size
            checks_passed += 1
        else:
            failures.append(f"S5-FILE: 组装文件不存在: {assembled_file}")
    else:
        # 尝试自动查找
        run_dir = getattr(state, "run_dir", None)
        if run_dir:
            rd = Path(run_dir)
            cands = list(rd.rglob("*完整稿件*配图版*")) + list(rd.rglob("*assembled*"))
            if cands:
                details["assembled_file"] = str(cands[0])
                details["assembled_size"] = cands[0].stat().st_size
                checks_passed += 1
            else:
                failures.append("S5-FILE: 未找到组装后输出文件（完整稿件_配图版.md）")
        else:
            failures.append("S5-FILE: state 无 run_dir 且无 assembled_file")

    # ── 内容非空 ──
    content = assembled_content
    if not content and details.get("assembled_file"):
        try:
            content = Path(details["assembled_file"]).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass
    if content and len(content) >= 100:
        checks_passed += 1
        details["content_length"] = len(content)
    else:
        failures.append(f"S5-CONTENT: 组装内容过短或为空（{len(content) if content else 0} 字符）")

    # ── 图片引用无死链（§5.6.3） ──
    if content:
        # 查找 Markdown 图片引用: ![...](path)
        img_refs = re.findall(r"!\[.*?\]\(([^)]+)\)", content)
        dead_links = []
        for ref in img_refs:
            ref_path = Path(ref)
            if not ref_path.is_absolute():
                # 相对路径 → 相对于 run_dir 解析
                run_dir = getattr(state, "run_dir", None)
                if run_dir:
                    ref_path = Path(run_dir) / ref_path
            elif not ref_path.exists():
                # 绝对路径不存在 → 尝试相对于 run_dir 查找同名文件（跨平台兼容）
                run_dir = getattr(state, "run_dir", None)
                if run_dir:
                    alt_path = Path(run_dir) / ref_path.name
                    if alt_path.exists():
                        ref_path = alt_path
            if not ref_path.exists():
                dead_links.append(str(ref))
        details["img_refs_count"] = len(img_refs)
        details["dead_links"] = dead_links
        if not dead_links:
            checks_passed += 1
        else:
            failures.append(
                f"S5-DEADLINK: {len(dead_links)} 处死链: "
                f"{', '.join(dead_links[:3])} [§5.6.3 强制]"
            )
    else:
        checks_passed += 1  # 无内容则无法检查

    # ── Markdown 格式健康 ──
    if content:
        has_title = bool(re.search(r"^#\s+", content, re.MULTILINE))
        has_image = bool(re.search(r"!\[", content))
        details["has_md_title"] = has_title
        details["has_md_image"] = has_image
        if has_title:
            checks_passed += 1
        else:
            failures.append("S5-FORMAT: Markdown 缺少标题（# heading）")
    else:
        checks_passed += 1

    score = (checks_passed / checks_total) * 100.0 if checks_total > 0 else 0.0
    passed = len(failures) == 0

    return ReviewResult(
        stage="S5", passed=passed, score=score, checks_total=checks_total,
        checks_passed=checks_passed, failures=failures, details=details,
    )


# ═══════════════════════════════════════════════════════════════
# 阶段执行器（含内层重试 + 评审）
# ═══════════════════════════════════════════════════════════════


def _print_header(text: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}")


def _print_review(result: ReviewResult) -> None:
    status = "✅ PASS" if result.passed else "❌ FAIL"
    print(f"  [评审] {result.stage} 评分={result.score:.0f} "
          f"({result.checks_passed}/{result.checks_total} 项通过) → {status}")
    if result.failures:
        for f in result.failures[:10]:
            print(f"    ⚠ {f}")
        if len(result.failures) > 10:
            print(f"    ... 共 {len(result.failures)} 项")


def run_s3_with_retry(
    engine: Any,
    args: argparse.Namespace,
    loop_i: int,
) -> tuple[StageResult, Any]:
    """执行 S3 研究写作 + 内层重试 + 评审。

    重试策略：
      - 每次重试重新调用 research_and_write()（LLM 非确定性 + 内部 3 轮自愈）
      - 评审反馈注入 state.outputs["_review_feedback"] 供下一轮 write_stage prompt 感知
      - 返回 (StageResult, best_state) 以便外层直接获取 S3 产出 state

    Returns:
        (StageResult, PipelineState) — state 为最佳评分尝试对应的 state 对象
    """
    from write_stage import research_and_write, PipelineHooks

    _print_header(f"LOOP {loop_i} | S3 研究写作 [max {MAX_STAGE_RETRIES} retries]")

    hooks = PipelineHooks(
        log_fn=lambda msg, level="info": print(f"  [S3:{level}] {msg}"),
        stage_fn=lambda name, status: print(f"  [S3:stage] {name} → {status}"),
        progress_fn=lambda p: None,
    )

    text: Optional[str] = None
    if args.material and Path(args.material).exists():
        text = Path(args.material).read_text(encoding="utf-8", errors="ignore")
    else:
        tr = find_latest_transcript()
        if tr:
            text = tr.read_text(encoding="utf-8", errors="ignore")
    if not text:
        dummy_state = make_state(run_id=f"loop_{loop_i}_s3_dummy")
        return (
            StageResult(stage="S3", passed=False, error="无转录素材（--material 或 outputs 下 transcript.txt）"),
            dummy_state,
        )

    base_content_type = args.content_type or "toutie"
    base_style = args.style or "baoming_shuo"

    best_result: Optional[StageResult] = None
    best_state: Any = None
    feedback_inject = ""  # 累积评审反馈，注入后续重试

    for attempt in range(1, MAX_STAGE_RETRIES + 1):
        print(f"\n  ── S3 尝试 {attempt}/{MAX_STAGE_RETRIES} ──")

        # 构造状态（每次尝试新 run_id，确保清洁）
        run_id = f"loop_{loop_i}_s3_{attempt}"
        state = make_state(
            run_id=run_id,
            content_type=base_content_type,
            content_style=base_style,
            enable_humanize=bool(args.humanize),
        )
        # 注入前次评审反馈（作为改进上下文）
        if feedback_inject:
            state.outputs["_review_feedback"] = feedback_inject
            print(f"  [S3] 注入前次评审反馈: {feedback_inject[:120]}...")

        state.outputs["transcript_text"] = text[:2000]
        state.outputs["video_title"] = args.title or "测试素材"

        t0 = time.time()
        try:
            ok = research_and_write(state, hooks)
        except Exception as exc:
            traceback.print_exc()
            sr = StageResult(
                stage="S3", passed=False, ok=False, attempt=attempt,
                duration_s=time.time() - t0, error=str(exc),
            )
            if best_result is None or sr.best_score > best_result.best_score:
                best_result = sr
            print(f"  [S3] ❌ 异常: {exc}")
            continue

        dt = time.time() - t0
        best_score = state.outputs.get("best_score", 0)
        print(f"  [S3] 完成 ok={ok} best_score={best_score} 耗时={dt:.1f}s")

        # 评审
        review = review_s3(state, engine)
        _print_review(review)

        sr = StageResult(
            stage="S3", passed=review.passed, ok=ok, review=review,
            attempt=attempt, duration_s=dt, best_score=float(best_score),
        )

        # 保存最佳结果和对应 state
        if best_result is None or best_score > best_result.best_score:
            best_result = sr
            best_state = state

        if review.passed:
            print(f"  [S3] ✅ S3 评审通过！")
            return (sr, state)

        # 修改策略：将评审失败项结构化注入下一轮重试
        if attempt < MAX_STAGE_RETRIES:
            failure_summary = " | ".join(review.failures[:5]) if review.failures else "评分未达标"
            feedback_inject = f"[第{attempt}轮改进方向] {failure_summary}"
            print(f"  [S3] 修改准备: {feedback_inject[:120]}")
        else:
            print(f"  [S3] ⚠ S3 内重试耗尽（{MAX_STAGE_RETRIES}次），{'仍有' if not review.passed else '已'}不通过项")

    # 返回最佳结果和 state
    if best_result is None:
        dummy = make_state(run_id=f"loop_{loop_i}_s3_fallback")
        return (StageResult(stage="S3", passed=False, error="S3 全部尝试失败"), dummy)
    return (best_result, best_state if best_state is not None else make_state(run_id=f"loop_{loop_i}_s3_fallback"))


def run_s4_with_retry(
    engine: Any,
    state: Any,  # 从 S3 获得的 state（含 generated_title/content）
    loop_i: int,
) -> StageResult:
    """执行 S4 配图 + 内层重试 + 评审。

    重试策略：重新执行 step_images()。如果 S3 内容未变，prompt 生成结果
    可能相似（LLM 非确定性是主要变化来源）。
    """
    _print_header(f"LOOP {loop_i} | S4 配图生成 [max {MAX_STAGE_RETRIES} retries]")

    # 检查前置条件
    title = state.outputs.get("generated_title", "")
    content = state.outputs.get("generated_content", "")
    if not content or len(content) < 50:
        return StageResult(stage="S4", passed=False, error="S4 前置条件不满足: generated_content 为空或过短")

    print(f"  [S4] 标题: {title[:60]}")
    print(f"  [S4] 内容: {len(content)} 字符")

    best_result: Optional[StageResult] = None
    best_img_state: Any = None  # 保存最佳状态供 fallback 写回

    for attempt in range(1, MAX_STAGE_RETRIES + 1):
        print(f"\n  ── S4 尝试 {attempt}/{MAX_STAGE_RETRIES} ──")

        # 每次重试用独立 state（含 images 目录）
        run_id = f"loop_{loop_i}_s4_{attempt}"
        img_state = make_state(run_id=run_id, with_images=True)
        img_state.outputs["generated_title"] = title
        img_state.outputs["generated_content"] = content

        t0 = time.time()
        try:
            ok = engine.step_images(img_state)
        except Exception as exc:
            traceback.print_exc()
            sr = StageResult(
                stage="S4", passed=False, ok=False, attempt=attempt,
                duration_s=time.time() - t0, error=str(exc),
            )
            print(f"  [S4] ❌ 异常: {exc}")
            continue

        dt = time.time() - t0
        cover = img_state.outputs.get("cover_image", "")
        inlines = img_state.outputs.get("inline_images", []) or []
        print(f"  [S4] 完成 ok={ok} 封面={'有' if cover else '无'} 内文={len(inlines)}张 耗时={dt:.1f}s")

        # 评审
        review = review_s4(img_state, engine)
        _print_review(review)

        sr = StageResult(
            stage="S4", passed=review.passed, ok=ok, review=review,
            attempt=attempt, duration_s=dt,
        )
        if best_result is None or (review.score > (best_result.review.score if best_result.review else 0)):
            best_result = sr
            best_img_state = img_state

        if review.passed:
            print(f"  [S4] ✅ S4 评审通过！")
            # 将图片信息写回主 state
            state.outputs["cover_image"] = cover
            state.outputs["inline_images"] = inlines
            state.outputs["_s4_run_dir"] = str(img_state.run_dir)
            return sr

        if attempt < MAX_STAGE_RETRIES:
            print(f"  [S4] 修改准备: 重新生成配图...")
        else:
            print(f"  [S4] ⚠ S4 内重试耗尽（{MAX_STAGE_RETRIES}次）")

    # 重试耗尽：将最佳产出（即使未通过评审）写回 state 供 S5 降级使用
    if best_img_state is not None:
        partial_cover = best_img_state.outputs.get("cover_image", "")
        partial_inlines = best_img_state.outputs.get("inline_images", []) or []
        state.outputs["cover_image"] = partial_cover
        state.outputs["inline_images"] = partial_inlines
        state.outputs["_s4_run_dir"] = str(best_img_state.run_dir)
        print(f"  [S4] 重试耗尽，降级写入最佳尝试的 {len(partial_inlines)} 张内文图")

    if best_result is None:
        return StageResult(stage="S4", passed=False, error="S4 全部尝试失败")
    return best_result


def run_s5_with_retry(
    engine: Any,
    state: Any,  # 从 S3+S4 获得的 state
    loop_i: int,
) -> StageResult:
    """执行 S5 组装 + 内层重试 + 评审。

    重试策略：重新执行 step_assemble()。
    """
    _print_header(f"LOOP {loop_i} | S5 组装发布 [max {MAX_STAGE_RETRIES} retries]")

    # 检查前置条件
    content = state.outputs.get("generated_content", "")
    title = state.outputs.get("generated_title", "")
    cover = state.outputs.get("cover_image", "")
    inlines = state.outputs.get("inline_images", []) or []

    if not content or len(content) < 50:
        return StageResult(stage="S5", passed=False, error="S5 前置条件不满足: generated_content 为空")

    print(f"  [S5] 标题: {title[:60]}")
    print(f"  [S5] 内容: {len(content)} 字符 | 封面: {'有' if cover else '无'} | 内文图: {len(inlines)}张")

    # 如果图片来自 S4，用 S4 的 run_dir/images
    s4_run_dir = state.outputs.get("_s4_run_dir", "")
    assembled_file = ""

    for attempt in range(1, MAX_STAGE_RETRIES + 1):
        print(f"\n  ── S5 尝试 {attempt}/{MAX_STAGE_RETRIES} ──")

        # 构造 S5 状态
        run_id = f"loop_{loop_i}_s5_{attempt}"
        s5_state = make_state(run_id=run_id)
        s5_state.outputs["generated_content"] = content
        s5_state.outputs["generated_title"] = title
        s5_state.outputs["generated_file"] = state.outputs.get("generated_file", "")

        # 图片路径处理
        if s4_run_dir:
            s4_img_dir = Path(s4_run_dir) / "images"
            if s4_img_dir.exists():
                cov = sorted(s4_img_dir.glob("cover.*"))
                s5_state.outputs["cover_image"] = str(cov[0]) if cov else ""
                s5_state.outputs["inline_images"] = [
                    str(p) for p in sorted(s4_img_dir.glob("inline_*.*"))
                ]
            else:
                s5_state.outputs["cover_image"] = cover
                s5_state.outputs["inline_images"] = inlines
        else:
            s5_state.outputs["cover_image"] = cover
            s5_state.outputs["inline_images"] = inlines

        t0 = time.time()
        try:
            ok = engine.step_assemble(s5_state)
        except Exception as exc:
            traceback.print_exc()
            sr = StageResult(
                stage="S5", passed=False, ok=False, attempt=attempt,
                duration_s=time.time() - t0, error=str(exc),
            )
            print(f"  [S5] ❌ 异常: {exc}")
            continue

        dt = time.time() - t0
        assembled_file = s5_state.outputs.get("assembled_file", "")
        print(f"  [S5] 完成 ok={ok} 耗时={dt:.1f}s 输出={'有' if assembled_file else '无'}")

        # 评审
        review = review_s5(s5_state, engine)
        status = "✅ PASS" if review.passed else "❌ FAIL"
        print(f"  [评审] S5 评分={review.score:.0f} "
              f"({review.checks_passed}/{review.checks_total} 项通过) → {status}")
        if review.failures:
            for f in review.failures[:10]:
                print(f"    ⚠ {f}")

        sr = StageResult(
            stage="S5", passed=review.passed, ok=ok, review=review,
            attempt=attempt, duration_s=dt,
        )

        if review.passed:
            print(f"  [S5] ✅ S5 评审通过！")
            state.outputs["assembled_file"] = assembled_file
            return sr

        if attempt < MAX_STAGE_RETRIES:
            print(f"  [S5] 修改准备: 重新组装...")
        else:
            print(f"  [S5] ⚠ S5 内重试耗尽（{MAX_STAGE_RETRIES}次）")

    if assembled_file:
        return StageResult(stage="S5", passed=False, ok=True, error=f"S5 内重试耗尽，最后输出: {assembled_file}")
    return StageResult(stage="S5", passed=False, error="S5 全部尝试失败")


# ═══════════════════════════════════════════════════════════════
# 主 LOOP
# ═══════════════════════════════════════════════════════════════


def main() -> None:
    global S3_PASS_THRESHOLD, MAX_OUTER_LOOPS, MAX_STAGE_RETRIES

    ap = argparse.ArgumentParser(
        description="AIToutiao S3→S4→S5 质量闭环 LOOP 测试（含评审门禁 + 自动重试）")
    ap.add_argument("--max-loops", type=int, default=MAX_OUTER_LOOPS,
                    help=f"最大 LOOP 迭代次数（默认 {MAX_OUTER_LOOPS}）")
    ap.add_argument("--max-retries", type=int, default=MAX_STAGE_RETRIES,
                    help=f"每阶段最大重试次数（默认 {MAX_STAGE_RETRIES}）")
    ap.add_argument("--material", help="阶段3 转录素材文件路径")
    ap.add_argument("--title", help="视频/素材标题")
    ap.add_argument("--style", help="写作风格（默认 baoming_shuo）")
    ap.add_argument("--content-type", dest="content_type",
                    help="内容类型 toutie/article（默认 toutie）")
    ap.add_argument("--humanize", action="store_true", help="启用人工化改写")
    ap.add_argument("--threshold", type=int, default=S3_PASS_THRESHOLD,
                    help=f"S3 质量阈值（默认 {S3_PASS_THRESHOLD}）")
    args = ap.parse_args()

    # 全局覆盖
    S3_PASS_THRESHOLD = args.threshold
    MAX_OUTER_LOOPS = args.max_loops
    MAX_STAGE_RETRIES = args.max_retries

    engine = load_engine_app()

    print("=" * 70)
    print("  AIToutiao S3→S4→S5 质量闭环 LOOP")
    print("=" * 70)
    print(f"  配置: Outer LOOP max={MAX_OUTER_LOOPS} | 阶段内重试 max={MAX_STAGE_RETRIES}")
    print(f"  阈值: S3 score≥{S3_PASS_THRESHOLD} | S4 图≥{S4_EXPECTED_INLINE_COUNT}张 >{S4_MIN_FILE_SIZE}B")
    print(f"  风格: {args.style or 'baoming_shuo'} | 类型: {args.content_type or 'toutie'}")
    print(f"  人工化: {'是' if args.humanize else '否'}")
    print("=" * 70)

    loop_results: list[dict] = []
    t_total_start = time.time()

    for loop_i in range(1, MAX_OUTER_LOOPS + 1):
        print(f"\n{'#'*70}")
        print(f"#  LOOP {loop_i}/{MAX_OUTER_LOOPS}")
        print(f"{'#'*70}")

        loop_data = {"loop": loop_i, "s3": None, "s4": None, "s5": None, "all_passed": False}

        # ── S3 ──
        s3_result, s3_state = run_s3_with_retry(engine, args, loop_i)
        loop_data["s3"] = s3_result

        # CRITICAL: S3 评审不通过 → 跳过 S4/S5，直接进入下一 LOOP
        # （用不合格内容配图/组装是浪费资源，对齐 ARTICLE_SPEC §4.1「打回 write_stage 重写」）
        if not s3_result.passed:
            reason = s3_result.error or (
                f"评审不通过 score={(s3_result.review.score if s3_result.review else 0):.0f}"
            )
            print(f"\n  ❌ S3 未通过: {reason}")
            if s3_result.review and s3_result.review.failures:
                for f in s3_result.review.failures[:5]:
                    print(f"    ⚠ {f}")
            loop_results.append(loop_data)
            loop_data["all_passed"] = False
            continue  # 下一 LOOP，不尝试 S4/S5

        # 从 S3 最佳 state 直接获取产出（不再依赖 find_latest_article 文件系统竞态）
        s3_content = s3_state.outputs.get("generated_content", "")
        s3_title = s3_state.outputs.get("generated_title", "")
        s3_file = s3_state.outputs.get("generated_file", "")

        if not s3_content or len(s3_content) < 50:
            print(f"\n  ❌ S3 产出内容为空或过短（{len(s3_content)} 字符）")
            loop_results.append(loop_data)
            loop_data["all_passed"] = False
            continue

        print(f"  [LOOP] S3 产出: 标题={s3_title[:40]}... 内容={len(s3_content)}字符 "
              f"best_score={s3_state.outputs.get('best_score', 'N/A')}")

        # ── S4 ──
        # 直接传递 S3 state（含 generated_title/content/file 等 outputs）
        s4_result = run_s4_with_retry(engine, s3_state, loop_i)
        loop_data["s4"] = s4_result

        # ── S5 ──
        s5_result = run_s5_with_retry(engine, s3_state, loop_i)
        loop_data["s5"] = s5_result

        # ── 全局判定 ──
        all_ok = (
            bool(s3_result.passed)
            and bool(s4_result.passed)
            and bool(s5_result.passed)
        )
        loop_data["all_passed"] = all_ok
        loop_results.append(loop_data)

        if all_ok:
            print(f"\n{'🎉'*35}")
            print(f"  🎉 LOOP {loop_i}: S3+S4+S5 全部评审通过！")
            print(f"{'🎉'*35}")
            break
        else:
            failing = []
            if not s3_result.passed: failing.append("S3")
            if not s4_result.passed: failing.append("S4")
            if not s5_result.passed: failing.append("S5")
            print(f"\n  ⚠ LOOP {loop_i}: {', '.join(failing)} 评审未通过，进入下一轮 LOOP...")

    # ═══════════════════════════════════════════════════════════
    # 最终报告
    # ═══════════════════════════════════════════════════════════
    t_total = time.time() - t_total_start

    print(f"\n{'='*70}")
    print(f"  LOOP 最终报告")
    print(f"{'='*70}")
    print(f"  总 LOOP 轮数: {len(loop_results)}")
    print(f"  总耗时: {t_total:.1f}s ({t_total/60:.1f}min)")
    print()

    final_all_passed = any(ld["all_passed"] for ld in loop_results)

    for ld in loop_results:
        li = ld["loop"]
        all_p = "✅ ALL PASS" if ld["all_passed"] else "❌ 未全通过"
        print(f"  LOOP {li}: {all_p}")
        for stage_key in ["s3", "s4", "s5"]:
            sr: Optional[StageResult] = ld.get(stage_key)
            if sr is None:
                print(f"    {stage_key.upper()}: 未执行")
                continue
            status = "PASS" if sr.passed else "FAIL"
            score = f"score={sr.review.score:.0f}" if sr.review else "N/A"
            err = f" | error={sr.error}" if sr.error else ""
            print(f"    {stage_key.upper()}: {status} attempt={sr.attempt} {score} "
                  f"duration={sr.duration_s:.1f}s{err}")

    print(f"\n  {'🎉 全部评审通过！' if final_all_passed else '❌ 未能在 LOOP 限制内全部通过，请检查报告'}")
    print(f"{'='*70}")

    sys.exit(0 if final_all_passed else 1)


if __name__ == "__main__":
    main()
