"""
缺失标题补救脚本（Agentic Workflow · 外部补救，不改动任何引擎程序）

根因：ai_writer.generate_toutie() 恒返回 "title": ""，write_stage.py 第203行用该空值
覆盖了对 video_title 的引用，导致所有「微头条(toutie)」产出的 generated_title 为空，
markdown 首行退化为空 H1 ("# ")。本脚本在引擎之外补救：

  1) 对 generated_title 为空的产出目录，用 LLMClient(DeepSeek) 生成风格化标题；
  2) 回退策略：若 LLM 失败，清洗 video_title 作标题；
  3) 将目录下所有 markdown 首行的空 "# " 改写为 "# {标题}"；
  4) 回填 pipeline_state.json 的 outputs.generated_title（字段名不变，下游无需改）。

用法:
    python scripts/fix_missing_title.py                        # 扫描 outputs/ 下全部产出
    python scripts/fix_missing_title.py <某个产出目录绝对路径>   # 仅补救指定目录
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(r"d:/AIToutiao-Engine")
OUT_BASE = ROOT / "outputs"
ENV_PATH = ROOT / "lib" / "toutiao-auto-publisher" / "backend" / ".env"

STYLE_LABEL = {
    "baoming_shuo": "包明说",
    "global_archive": "全球档案馆",
    "tingfengdecan": "听风的蚕",
    "jinshuo": "晋说",
}


def load_env() -> dict:
    d = {}
    if not ENV_PATH.exists():
        return d
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def make_client():
    env = load_env()
    api_key = env.get("AI_API_KEY", "")
    if not api_key:
        return None
    sys.path.insert(0, str(ROOT / "agent"))
    from llm_client import LLMClient

    return LLMClient(
        api_key=api_key,
        base_url=env.get("AI_BASE_URL", "https://api.deepseek.com/v1"),
        model=env.get("AI_MODEL", "deepseek-chat"),
        temperature=0.6,
        max_tokens=64,
    )


def clean_video_title(vt: str) -> str:
    if not vt:
        return ""
    t = vt
    t = re.sub(r"^抖音独家___", "", t)
    t = re.sub(r"#.*$", "", t)           # 去掉话题标签
    t = t.replace("___", "——").strip()
    t = t.strip(" _-|")
    return t


def gen_title(client, content: str, style: str) -> str:
    if client is None:
        return ""
    label = STYLE_LABEL.get(style, "军事自媒体")
    sys_prompt = (
        "你是一位资深头条/公众号军事自媒体标题专家，擅长「" + label +
        "」式反差+数字+悬念标题。你只输出标题文本，不输出任何解释。"
    )
    user_prompt = (
        "根据下面文章起一个标题，要求：\n"
        "1) 不超过28字；\n"
        "2) 含反差或数字或悬念，军事硬核向；\n"
        "3) 只输出标题文本本身，不要引号、不要#、不要平台标签(如#xxx)。\n\n"
        "文章：\n" + content[:1500]
    )
    try:
        resp = client.generate(prompt=user_prompt, system_prompt=sys_prompt)
        return resp.strip().strip('"').strip("'").strip("#").strip()
    except Exception:
        return ""


def patch_markdown(md: Path, title: str) -> bool:
    text = md.read_text(encoding="utf-8")
    lines = text.split("\n")
    if lines and lines[0].rstrip() in ("#", "# "):
        lines[0] = f"# {title}"
        md.write_text("\n".join(lines), encoding="utf-8")
        return True
    return False


def fix_run(run_dir: Path) -> str | None:
    state_file = run_dir / "pipeline_state.json"
    if not state_file.exists():
        return None
    state = json.loads(state_file.read_text(encoding="utf-8"))
    title = (state.get("outputs", {}).get("generated_title", "") or "").strip()
    if title:
        return "(已有标题，跳过)"

    content = (
        state.get("outputs", {}).get("generated_content")
        or state.get("outputs", {}).get("humanized_content")
        or ""
    ).strip()
    if not content:
        return "(无正文，跳过)"

    style = state.get("content_style", "")
    client = make_client()
    new_title = gen_title(client, content, style)
    if not new_title:
        new_title = clean_video_title(state.get("outputs", {}).get("video_title", ""))
    if not new_title:
        return "(无法生成标题，跳过)"

    patched = 0
    for md in sorted(run_dir.glob("*.md")):
        if patch_markdown(md, new_title):
            patched += 1

    state["outputs"]["generated_title"] = new_title
    state_file.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return f"[OK] 标题={new_title} | 改写md={patched} | 回填json=1"


def main():
    args = sys.argv[1:]
    if args:
        targets = [Path(a) for a in args if Path(a).exists()]
    else:
        targets = [p.parent for p in OUT_BASE.rglob("pipeline_state.json")]

    if not targets:
        print("未找到任何产出目录。")
        return

    print(f"待补救目录数: {len(targets)}")
    for d in targets:
        try:
            res = fix_run(d)
        except Exception as e:
            res = f"[ERR] {e}"
        print(f"  {d.name}: {res}")


if __name__ == "__main__":
    main()
