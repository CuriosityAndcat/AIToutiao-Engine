"""
头条作者风格分析（Agentic Workflow · Phase 2.1）

对 docs/采集/{作者}/ 下每作者体量最大的 10 篇本人原创文本，调用 DeepSeek 做 10 维写作风格拆解，
结果存 docs/风格分析/{作者}/raw/{标题}.json。复用 agent/llm_client.LLMClient + backend/.env。

用法:
    python scripts/analyze_style.py            # 分析全部 4 作者
    python scripts/analyze_style.py 包明说      # 仅分析某作者
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(r"d:/AIToutiao-Engine")
COLLECT = ROOT / "docs" / "采集"
OUT = ROOT / "docs" / "风格分析"
OUT.mkdir(parents=True, exist_ok=True)
PER_AUTHOR = 10

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


SYS_PROMPT = (
    "你是一位资深的中文爆款内容拆解专家，擅长从军事/时政/文化类自媒体文章中，"
    "抽取可复用的写作风格要素。你会严格输出合法可解析的 JSON，不输出任何额外说明文字。"
)

USER_TMPL = """请分析下面这篇由「{author}」撰写的自媒体文章，从 10 个维度抽取其写作风格要素。
要求：
1. 只输出一个 JSON 对象，不要代码块标记，不要任何解释文字。
2. 该 JSON 必须能被程序直接解析：字符串值内不得出现未转义的双引号（如需引用请用中文引号「」或『』），
   不得出现真实换行（多行内容用 \\n 表示），不得使用制表符。
3. 每个维度给出具体、可引用的证据（引用原文短句，用中文引号包裹）。
4. 维度定义如下：
- title_hook: 标题钩子类型（悬念/反差/震惊/提问/算账/数字），句式特征，情绪词。
- opening: 开篇前3句的叙事手法（是否用"家人们/各位"等唤醒词，是否抛冲突）。
- narrative_structure: 整体结构（如 七层递进/起承转合/设问-论证-收束），段落功能。
- paragraph_rhythm: 平均段落字数估计，长短句比例，断句风格。
- golden_sentences: 标志性句式模板（如"不是…而是…""最X的是"），列举3-5个并附原文引用。
- person_usage: 人称（第一/二/三人称），对读者称呼（家人们/兄弟们/各位），作者自我指代方式。
- emotion_curve: 情绪曲线（开篇→中段→结尾 的情绪走向，如 震惊→紧张→愤怒→升华）。
- evidence_density: 每千字的大致证据密度（具体数据/人名/地名/武器型号/时间点 数量）。
- interaction_design: 互动设计（是否提问式结尾、CTA、标签），模板提取。
- humanize_score: 去AI味指数 0-100（口语化占比、个性化用词、机器腔程度），并说明依据。
4. 额外字段：
- style_keywords: 5-8 个风格关键词数组。
- one_line_summary: 一句话总结该作者此文的风格画像。

【文章标题】：{title}
【文章内容】：
{content}
"""


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        idx = text.find("\n---", 3)
        if idx != -1:
            return text[idx + 4:].strip()
    return text.strip()


def parse_json(resp: str) -> dict:
    s = resp.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s)
    m = re.search(r"\{.*\}", s, re.S)
    blob = m.group(0) if m else s
    # 净化字符串值内的原始控制字符（换行/回车/制表），避免 Invalid control character
    blob = blob.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    return json.loads(blob)


def analyze_author(author: str, client) -> int:
    adir = COLLECT / author
    raw = OUT / author / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    files = sorted(adir.glob("*.md"), key=lambda x: -x.stat().st_size)[:PER_AUTHOR]
    print(f"\n=== {author} ({len(files)} 篇) ===")
    done = 0
    for f in files:
        out_path = raw / (f.stem + ".json")
        if out_path.exists():
            print(f"  - 已分析，跳过: {f.name}")
            done += 1
            continue
        content = strip_frontmatter(f.read_text(encoding="utf-8"))
        if len(content) < 200:
            print(f"  - 文本过短跳过: {f.name}")
            continue
        title = f.stem.replace(author + "_", "")
        prompt = USER_TMPL.format(author=author, title=title, content=content[:6000])
        try:
            resp = client.generate(
                prompt=prompt,
                system_prompt=SYS_PROMPT,
                response_format={"type": "json_object"},
            )
            data = parse_json(resp)
            data["_meta"] = {
                "author": author,
                "title": title,
                "source_file": str(f),
                "content_len": len(content),
            }
            out_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"  [OK] {title}  -> {out_path.name}")
            done += 1
        except Exception as e:
            print(f"  [FAIL] {title}: {e}")
        time.sleep(1.5)
    print(f"  {author} 本批分析 {done} 篇")
    return done


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    env = load_env()
    sys.path.insert(0, str(ROOT))
    from agent.llm_client import LLMClient

    client = LLMClient(
        api_key=env["AI_API_KEY"],
        base_url=env["AI_BASE_URL"],
        model=env["AI_MODEL"],
        temperature=0.3,
        max_tokens=3000,
    )
    targets = [arg] if arg else AUTHORS
    for a in targets:
        analyze_author(a, client)
    print("\n分析完成。")


if __name__ == "__main__":
    main()
