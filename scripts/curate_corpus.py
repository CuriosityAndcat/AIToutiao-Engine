"""
语料策展（Agentic Workflow · Phase 1 质量修正）

非破坏性：把重复 / 非本人原创 / 低价值文件移入 docs/采集/_excluded/{作者}/，可回退。
- 按归一化标题去重（去掉标点空格后相同即视为重复，保留体积最大者）
- 听风的蚕：剔除关于他的专访/报道/简介（非其本人写作）
- 晋说：剔除图书馆活动通知类重复稿
保留每作者真正由本人撰写的优质文本，供 Phase 2 风格分析使用。
"""
import re
import shutil
from pathlib import Path

BASE = Path(r"d:/AIToutiao-Engine/docs/采集")
EXCL = BASE / "_excluded"
EXCL.mkdir(exist_ok=True)


def norm(t: str) -> str:
    # 去掉标点/空格/引号，保留中英文与数字，用于去重判重
    return re.sub(r"[^\w\u4e00-\u9fff]", "", t).lower()


# 听风的蚕：关于他的专访/报道/简介（非本人原创写作）——子串匹配更稳健
TING_OFFTOPIC = (
    "对话", "专访", "面孔", "我有一群AI", "掉粉", "平台称",
    "被禁止关注", "网络文明是我们每个人的事", "听风的蚕.md",
)

# 晋说：图书馆活动通知重复稿（全角引号，子串匹配）
JIN_OFFTOPIC = (
    "全民读书季", "省图全民读书季", "山西省图全民读书季",
)


def curate(author: str, off_seq):
    adir = BASE / author
    dest = EXCL / author
    dest.mkdir(parents=True, exist_ok=True)

    # 1) 显式剔除（子串匹配）
    moved = 0
    for f in list(adir.glob("*.md")):
        if any(sub in f.name for sub in off_seq):
            shutil.move(str(f), str(dest / f.name))
            moved += 1

    # 2) 归一化标题去重（保留体积最大）
    groups: dict[str, list[Path]] = {}
    for f in adir.glob("*.md"):
        key = norm(f.stem.replace(author + "_", ""))
        groups.setdefault(key, []).append(f)
    dup_moved = 0
    for key, files in groups.items():
        if len(files) > 1:
            files.sort(key=lambda x: -x.stat().st_size)
            for dup in files[1:]:
                shutil.move(str(dup), str(dest / dup.name))
                dup_moved += 1

    remain = len(list(adir.glob("*.md")))
    print(f"{author}: 剩余 {remain} 篇 (显式剔除 {moved}, 去重 {dup_moved})")


for a in ["包明说", "听风的蚕", "晋说", "全球档案馆"]:
    off = TING_OFFTOPIC if a == "听风的蚕" else (JIN_OFFTOPIC if a == "晋说" else set())
    curate(a, off)

print("\n策展完成。被剔除文件在 docs/采集/_excluded/ 可回退。")
