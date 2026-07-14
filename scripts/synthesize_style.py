"""
风格聚合与文档生成（Agentic Workflow · Phase 2.2 / 2.3）

- 聚合每位作者 10 篇分析的结构化统计（钩子/结构/关键词/去AI味分/人称/金句…）
- 调用 DeepSeek 为每位作者撰写《仿写风格指南》Markdown（含可直接复制的仿写 Prompt）
- 用 Python 构建《四作者对比矩阵.md》与《仿写Prompt模板.md》
产出目录：docs/风格分析/
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(r"d:/AIToutiao-Engine")
OUT = ROOT / "docs" / "风格分析"
AUTHORS = ["包明说", "听风的蚕", "晋说", "全球档案馆"]


def load_env() -> dict:
    d = {}
    p = ROOT / "lib" / "toutiao-auto-publisher" / "backend" / ".env"
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def load_analyses(author: str) -> list[dict]:
    raw = OUT / author / "raw"
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(raw.glob("*.json"))]


def lst(x):
    """把可能为 list/dict/str/None 的字段统一安全转为 list。"""
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        return list(x.values())
    return [x]


def _sub(d: dict, key: str, sub: str = None):
    """安全取嵌套字段：d[key] 可能是 dict/str/其他。"""
    v = d.get(key)
    if isinstance(v, dict) and sub:
        return v.get(sub, "?")
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        return next(iter(v.values()), "?")
    return "?"


def aggregate(analyses: list[dict]) -> dict:
    hook, struct, kw, persons, curves = Counter(), Counter(), Counter(), Counter(), Counter()
    scores, golds = [], []
    for a in analyses:
        hook[_sub(a, "title_hook", "type")] += 1
        struct[_sub(a, "narrative_structure", "type")] += 1
        kw.update(lst(a.get("style_keywords")))
        try:
            scores.append(float(a["humanize_score"]["score"]))
        except Exception:
            try:
                scores.append(float(_sub(a, "humanize_score", "score")))
            except Exception:
                pass
        persons[_sub(a, "person_usage", "reader_address")] += 1
        curves[_sub(a, "emotion_curve", "curve")[:24]] += 1
        golds.extend(lst(a.get("golden_sentences")))
    return {
        "hook": hook.most_common(3),
        "struct": struct.most_common(3),
        "kw": kw.most_common(8),
        "avg_humanize": round(sum(scores) / len(scores), 1) if scores else 0,
        "person": persons.most_common(2),
        "curve": curves.most_common(2),
        "golds": golds[:15],
        "n": len(analyses),
    }


def condensed(analyses: list[dict]) -> str:
    lines = []
    for a in analyses:
        m = a.get("_meta", {})
        lines.append(
            f"- 《{m.get('title','?')}》 钩子={_sub(a,'title_hook','type')} "
            f"结构={_sub(a,'narrative_structure','type')} "
            f"去AI味={_sub(a,'humanize_score','score')}\n"
            f"  金句: {' | '.join(str(g) for g in lst(a.get('golden_sentences'))[:3])}\n"
            f"  人称: {_sub(a,'person_usage','reader_address')}  "
            f"情绪: {_sub(a,'emotion_curve','curve')}\n"
            f"  关键词: {', '.join(str(k) for k in lst(a.get('style_keywords'))[:6])}"
        )
    return "\n".join(lines)


GUIDE_SYS = (
    "你是一位顶尖的中文自媒体写作教练，擅长把多位作者的风格分析，"
    "沉淀为可落地的《仿写风格指南》。你输出结构清晰的 Markdown。"
)

GUIDE_USER = """以下是「{author}」的 {n} 篇本人原创文章的风格分析摘要：

{condensed}

请基于以上数据，撰写一份《{author} 仿写风格指南》Markdown 文档，必须包含以下章节：
# {author} 仿写风格指南
## 一、风格画像（一句话定位 + 核心特征）
## 二、标题公式（给出 2-3 个可套用模板，并举例）
## 三、开篇模板（2 个可直接套用的开篇句式）
## 四、叙事结构（总结其最常用的结构，给出骨架）
## 五、金句库（提炼 5-8 个该作者高频句式模板，如"不是…而是…"）
## 六、人称与互动（对读者怎么称呼、怎么收尾互动）
## 七、情感曲线（典型情绪推进路径）
## 八、去AI味要点（如何写得像他而不是机器）
## 九、仿写检查清单（写完后对照的自检 5 条）
## 十、仿写Prompt（可直接复制给 AI 的指令）
文档末尾用如下标记包裹一段可直接复制给 AI 写作工具的仿写 Prompt：
<<PROMPT>>
（这里写一段完整的、可直接使用的仿写 Prompt，要求 AI 以"{author}"的风格写一篇新的同类文章）
<</PROMPT>>

要求：具体到可操作，多用该作者的真实句式举例；不要空话。只输出 Markdown。"""


def build_guide(author: str, analyses: list[dict], client) -> tuple[str, str]:
    stats = aggregate(analyses)
    prompt = GUIDE_USER.format(
        author=author, n=stats["n"], condensed=condensed(analyses)
    )
    md = client.generate(prompt=prompt, system_prompt=GUIDE_SYS, temperature=0.5, max_tokens=3000)
    m = re.search(r"<<PROMPT>>(.*?)<</PROMPT>>", md, re.S)
    imitation = m.group(1).strip() if m else ""
    return md, imitation


def main():
    env = load_env()
    sys.path.insert(0, str(ROOT))
    from agent.llm_client import LLMClient

    client = LLMClient(
        api_key=env["AI_API_KEY"], base_url=env["AI_BASE_URL"],
        model=env["AI_MODEL"], temperature=0.5, max_tokens=3000,
    )

    guides: dict[str, str] = {}
    prompts: dict[str, str] = {}
    stats_all: dict[str, dict] = {}

    for a in AUTHORS:
        analyses = load_analyses(a)
        stats_all[a] = aggregate(analyses)
        print(f"生成 {a} 风格指南 ...")
        md, imitation = build_guide(a, analyses, client)
        (OUT / f"{a}_风格指南.md").write_text(md, encoding="utf-8")
        guides[a] = md
        prompts[a] = imitation or f"请以「{a}」的写作风格，写一篇同类主题的新文章。参考其风格画像：{stats_all[a]['kw']}"
        print(f"  [OK] {a}_风格指南.md")

    # 四作者对比矩阵（Python 确定性构建）
    matrix = ["# 四作者写作风格对比矩阵\n",
              "> 基于每位作者 10 篇本人原创文本的风格分析聚合。\n",
              "| 维度 | " + " | ".join(AUTHORS) + " |",
              "| --- | " + " | ".join(["---"] * len(AUTHORS)) + " |"]
    matrix.append("| 样本量 | " + " | ".join(str(stats_all[a]["n"]) for a in AUTHORS) + " |")
    matrix.append("| 高频标题钩子 | " + " | ".join(
        "、".join(f"{k}({v})" for k, v in stats_all[a]["hook"]) for a in AUTHORS) + " |")
    matrix.append("| 常用叙事结构 | " + " | ".join(
        "、".join(f"{k}({v})" for k, v in stats_all[a]["struct"]) for a in AUTHORS) + " |")
    matrix.append("| 平均去AI味分 | " + " | ".join(
        str(stats_all[a]["avg_humanize"]) for a in AUTHORS) + " |")
    matrix.append("| 对读者称呼 | " + " | ".join(
        "、".join(f"{k}({v})" for k, v in stats_all[a]["person"]) for a in AUTHORS) + " |")
    matrix.append("| 典型情绪曲线 | " + " | ".join(
        "、".join(f"{k}({v})" for k, v in stats_all[a]["curve"]) for a in AUTHORS) + " |")
    matrix.append("| Top 风格关键词 | " + " | ".join(
        "、".join(k for k, _ in stats_all[a]["kw"][:5]) for a in AUTHORS) + " |")
    (OUT / "四作者对比矩阵.md").write_text("\n".join(matrix) + "\n", encoding="utf-8")
    print("[OK] 四作者对比矩阵.md")

    # 仿写 Prompt 模板
    tpl = ["# 仿写 Prompt 模板（可直接复制给 AI 写作工具）\n",
           "> 对应 docs/风格分析/ 下各作者的《仿写风格指南》。\n"]
    for a in AUTHORS:
        tpl.append(f"\n## {a}\n")
        tpl.append(prompts[a])
        tpl.append("")
    tpl.append("\n---\n")
    tpl.append("使用说明：将上述某作者的 Prompt 复制进 AIWriter（lib/toutiao-auto-publisher/backend）"
               "或任意支持 DeepSeek 的对话，替换主题即可生成同风格新文。"
               "若接入生产流水线，可将本风格沉淀为 models.py 的 ContentStyle 枚举（如 GLOBAL_ARCHIVE）。")
    (OUT / "仿写Prompt模板.md").write_text("\n".join(tpl), encoding="utf-8")
    print("[OK] 仿写Prompt模板.md")
    print("\n风格文档生成完成。")


if __name__ == "__main__":
    main()
