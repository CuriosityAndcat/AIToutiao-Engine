"""
Agnes Video V2.0 军事视频生成（玉渊谭天CG风格）
参考 docs/军事视频参考数据/风格参考图.png

风格核心：
- CG数字绘/3A游戏过场动画质感（Uncharted/Last of Us 级别）
- 明亮高对比，正午强烈日光，橙红烈焰在晴空下燃烧
- 淡灰烟雾与明亮日光交织，废墟场景
- 所有物体在正午阳光下清晰可见
- 战火废墟/末日场景

用法: python agnes_video_gen.py

重要: 纯文字锚定，不参考配图
- IMAGES_DIR 仅保留占位，不在 Prompt 中使用任何图片引用（@Image1 等）
- 所有视频 Prompt 严格锚定原文文字内容

画面比例: 16:9横屏（1280x720）
- 横向构图空间充裕，前中远景三层纵深
- 适合广角远景、横移镜头、大规模场景
- 构图策略：左右分置元素，充分利用横宽

装备策略: 物理准确，分层渲染
- 远距（200m+）：剪影即可，轮廓正确
- 中距（50-200m）：可见关键识别特征，不需座舱铆钉
- 近距特写：仅用于无法失真的元素（火焰/浓烟/沙尘/履带印/弹坑/爆炸冲击波）
- 装备词典（通用军事术语，不用品牌名）：
  * 战斗机：「后掠翼双垂尾战斗机」「三角翼截击机」
  * 坦克：「低矮轮廓主战坦克，棱角炮塔，长管滑膛炮」
  * 运输机：「大型运输机，高T尾，四发引擎」
  * 导弹：「弹道导弹，圆柱形弹体，圆锥形弹头，尾部稳定翼」
  * 雷达：「球形雷达天线罩」
- 失真兜底：若装备可能失真，用环境元素（烟/火/尘/光）承担80%视觉重量

禁止: split-screen/分裂画面，所有段落为单一连续画面

# v3.0 新增约束 (2026-07-18):
# - 移除所有文字元素（无标签、无字幕、无数字标注）
# - 场景光线从黄昏改为正午明亮日光
# - 人物剪影仅限肩部轮廓，无面部细节，不超出活动框架
# - 所有物体物理位置合理（飞机空中/船水面/天线楼顶）
# - 肖像合规：用剪影替代可识别人脸
"""

import os, sys, json, time, requests
from pathlib import Path

# ── 配置 ────────────────────────────────────────────────────
API_KEY = os.getenv("AGNES_API_KEY", "")
if not API_KEY:
    env_path = Path(__file__).parents[3] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("AGNES_API_KEY="):
                API_KEY = line.split("=", 1)[1].strip()
                break

API_BASE = os.getenv("AGNES_API_BASE", "https://apihub.agnes-ai.com/v1")
MODEL = "agnes-video-v2.0"

OUTPUT_DIR = Path(__file__).parents[3] / "outputs" / "agnes_video"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

IMAGES_DIR = Path(__file__).parents[3] / "outputs" / "20260718" / "20260718_081556" / "images"

# 公共风格前缀（所有段落共用）
STYLE_PREFIX = (
    "3A级游戏过场动画级别的CG数字绘风格，"
    "电影感明亮高对比，正午强烈日光，"
    "橙红色烈焰在晴空下燃烧，淡灰烟雾与明亮日光交织，"
    "废墟场景，所有物体在正午阳光下清晰可见，"
    "前中远景三层纵深构图，"
    "概念艺术级画面质感，"
    "镜头带有电影感运动和轻微景深虚化，"
    "整体氛围紧张震撼"
)

STYLE_NEGATIVE = (
    "实拍照片、纪录片、监控画面、过曝、欠曝、"
    "卡通、动漫、低龄化、平面化、"
    "黄昏逆光、暗调、"
    "任何文字、字幕、数字标签、文本、字符、"
    "人物面部特征、可识别人脸、"
    "舰船畸形部位、物体位置错乱、"
    "实体文字、水印、logo、签名"
)

# ── 4 段 Prompt（v3.0 文章锚定式模板体系，2026-07-18）───
# 原文: 美军再打伊朗能打多久
# 画面比例: 16:9横屏（1280x720），前中远景三层纵深，左右分置元素
# 导演声音: Kinetic Visceral 战争动能派 + CG数字绘质感
# 核心叙事弧线: 虚张声势被揭穿 → 家底耗尽证据累积 → 指挥大脑被摘除 → 内外交困只能谈判
# 光色弧线: 正午晴空+航母疲惫空旷 → 日光直射空荡弹药架 → 爆炸红光vs正午日光柱 → 油价红色曲线→正午日光空桌
# 模式断裂点: Clip 03（唯一直接暴力撞击镜头——无人机撞指挥中心）
# v3.0 关键改动:
#   - 移除所有文字元素（无标签、无字幕、无数字标注、无文字碎片）
#   - 场景光线从黄昏/残阳/夕照改为正午强烈日光
#   - 人物剪影仅限肩部轮廓，无面部细节，不超出活动框架
#   - 所有物体物理位置合理（飞机空中/船水面/天线楼顶）
#   - 肖像合规：用「指挥官剪影」替代具体名字，用背光/轮廓规避肖像权
# 装备策略: 分层渲染——远距剪影/中距可辨特征/近距仅用于不可失真元素（火烟尘光）
#   装备词典（通用军事术语，不用品牌名）:
#     航母: 「大型平顶航母，斜角甲板，舰岛靠右」
#     加油机: 「大型四发加油机，翼尖加油吊舱，输油管从机尾垂下」
#     预警机: 「大型预警机，机背圆盘形雷达天线罩」
#     精确制导弹药: 「圆柱形弹体，前部激光导引头圆窗，后部梯形稳定翼」
#     伊朗无人机: 「三角翼无人机，沙色涂装，机头尖锐，翼尖上翘」
#   失真兜底: 环境元素（烟/火/尘/光）承担80%视觉重量
# 构图策略: 全程禁止split-screen，所有段落为单一连续画面
# 色调约束: 禁止暗蓝夜/冷蓝月光/全黑/大面积黑暗/熄灭/黄昏逆光，统一为正午明亮日光
SEGMENTS = [
    {
        "name": "01_开场_虚张声势",
        "duration": 10,
        "num_frames": 241,
        "prompt": (
            STYLE_PREFIX + "。"
            "正午波斯湾晴空万里，强烈日光直射海面，"
            "一艘大型平顶航母孤零零停在海面上——"
            "舰岛靠右的斜角甲板上仅稀疏停着几架折叠翼舰载机，"
            "甲板大部分区域空旷，超期部署的疲惫通过空旷的甲板无声传达。"
            "画面左上方一座CG半透明讲台剪影——"
            "一位指挥官轮廓站在讲台后方，肩线清晰但无面部细节，"
            "后梳发型轮廓暗示身份，背光照亮剪影边缘轮廓，"
            "静态站立姿态，不超出讲台范围。"
            "镜头从讲台后方缓缓推入波斯湾海面，"
            "航母在正午日光中拉出清晰倒影，"
            "远处伊朗方向地平线上一道薄烟在晴空中缓缓升腾。"
            "飞机在空中正常飞行，航母在水面正常浮航，舰体形态完整物理合理。"
            "CG数字绘风格，无任何文字/标签/字幕，无人物面部特写。"
        ),
    },
    {
        "name": "02_家底耗尽_三种打不起",
        "duration": 12,
        "num_frames": 289,
        "prompt": (
            STYLE_PREFIX + "。"
            "正午强烈日光斜射中东沙漠美军空军基地，连续横移长镜头缓慢扫过三个空间——"
            "首先：跑道尽头一架大型四发加油机孤零零停着，翼尖加油吊舱清晰可辨，"
            "输油管从机尾耷拉垂地，机翼蒙上厚厚沙尘——远程奔袭已被锁死。"
            "接着：停机坪上一架大型预警机，机背圆盘形雷达天线罩被击穿一个大洞，"
            "边缘焦黑扭曲，日光从洞口漏出刺目光斑——空中预警体系已经变瞎。"
            "最后：弹药库混凝土掩体内，精确制导弹药架一排排空荡，"
            "仅剩零星弹体——圆柱形弹体前部激光导引头圆窗反射日光微光，"
            "空荡的弹药架比爆炸更刺眼——生产周期数月，每打一发就少一发。"
            "风卷沙尘掠过空旷停机坪。"
            "CG数字绘风格，无人物无文字无国旗。"
        ),
    },
    {
        "name": "03_体系被摧毁_第五舰队指挥中心",
        "duration": 12,
        "num_frames": 289,
        "prompt": (
            STYLE_PREFIX + "。"
            "正午波斯湾岛屿上的巴林美军基地——低矮混凝土指挥中心建筑群，"
            "屋顶布满天线和球形卫星通信罩。"
            "一架三角翼沙色涂装无人机从画面右侧高速飞入，机头尖锐，翼尖上翘，"
            "直冲向建筑群中央的指挥中心大楼。"
            "撞击瞬间橙红爆炸火光炸开，建筑中部混凝土结构塌陷，"
            "屋顶通信天线拦腰折断坠落，球形卫星罩翻滚着被浓烟吞没。"
            "内部屏幕墙全部变红闪烁故障信号，电火花从断裂电缆溅射。"
            "正午日光从炸开的屋顶缺口倾泻形成冷白光柱，穿透翻涌尘埃，"
            "红光警报与白日光柱极致对冲——指挥大脑被摘除。"
            "镜头从无人机跟拍撞击后缓慢拉远，展现建筑群塌陷全貌。"
            "CG数字绘风格，无真实人脸、无国旗、无任何文字。"
        ),
    },
    {
        "name": "04_谈判宿命_内外交困",
        "duration": 15,
        "num_frames": 361,
        "prompt": (
            STYLE_PREFIX + "。"
            "第一阶段：CG数据可视化界面——国际油价表急剧飙升，"
            "红色曲线一路上扬，经济数据图表剧烈波动——通胀压力逼人。"
            "第二阶段：画面切入CG白宫内部，一位指挥官剪影站在落地窗前背对镜头，"
            "肩部轮廓清晰但无面部细节，窗外远方中东地平线上隐约火光与浓烟——"
            "决策者清楚已经打不下去了，"
            "国会限制动武的文件散落在身后桌上，无任何文字可辨识。"
            "第三阶段：画面淡入一间空谈判室，正午明亮日光从窗外射入，"
            "在空无一物的长桌表面画出清晰的明暗分界线，"
            "两侧椅子空着，光柱中细微尘埃缓慢浮动——"
            "停火谈判是唯一出口，战场上得不到的，谈判桌上也别想得到。"
            "CG数字绘风格，无任何文字/标签/字幕，无真实人脸特写。"
        ),
    },
]


def create_video_task(segment: dict) -> dict:
    """创建 Agnes Video V2.0 视频生成任务"""
    url = f"{API_BASE}/videos"

    payload = {
        "model": MODEL,
        "prompt": segment["prompt"],
        "negative_prompt": STYLE_NEGATIVE,
        "num_frames": segment.get("num_frames", 241),
        "frame_rate": 24,
        "width": 1280,
        "height": 720,  # 横屏 16:9
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

    print(f"\n[agnes] 创建视频任务: {segment['name']}")
    print(f"[agnes] 时长: ~{segment['duration']}秒 ({payload['num_frames']}帧 @24fps)")
    print(f"[agnes] 风格: 玉渊谭天CG战火风")
    print(f"[agnes] prompt: {segment['prompt'][:80]}...")

    resp = requests.post(url, headers=headers, json=payload, timeout=30)

    if resp.status_code != 200:
        print(f"[agnes] 任务创建失败: HTTP {resp.status_code}")
        print(f"[agnes] 响应: {resp.text[:500]}")
        return None

    data = resp.json()
    print(f"[agnes] 任务创建成功!")
    print(f"   task_id: {data.get('task_id')}")
    print(f"   video_id: {data.get('video_id')}")
    print(f"   status: {data.get('status')}")
    return data


def poll_video_result(task_data: dict, max_wait: int = 600) -> str:
    """轮询视频生成结果, 返回视频URL"""
    video_id = task_data.get("video_id") or task_data.get("id")
    if not video_id:
        print("[agnes] 无 video_id")
        return None

    query_url = f"https://apihub.agnes-ai.com/agnesapi?video_id={video_id}"
    headers = {"Authorization": f"Bearer {API_KEY}"}

    print(f"\n[agnes] 轮询视频结果 (video_id={video_id})...")
    start = time.time()
    poll_interval = 10

    while time.time() - start < max_wait:
        elapsed = int(time.time() - start)
        try:
            resp = requests.get(query_url, headers=headers, timeout=15)
            data = resp.json()
            status = data.get("status", "unknown")
            progress = data.get("progress", 0)

            print(f"\r[agnes] [{elapsed}s] 进度: {progress}%  状态: {status}  ", end="")

            if status == "completed":
                video_url = data.get("url")
                if video_url:
                    print(f"\n[agnes] 视频生成完成!")
                    print(f"[agnes] 视频URL: {video_url}")
                    print(f"[agnes] 时长: {data.get('seconds')}s")
                    print(f"[agnes] 分辨率: {data.get('size')}")
                    return video_url
                else:
                    print(f"\n[agnes] 完成但无URL")
                    return None

            elif status == "failed":
                error = data.get("error", "未知错误")
                print(f"\n[agnes] 生成失败: {error}")
                return None

        except Exception as e:
            print(f"\n[agnes] 查询异常: {e}")

        time.sleep(poll_interval)
        if poll_interval < 30:
            poll_interval += 5

    print(f"\n[agnes] 轮询超时 ({max_wait}s)")
    return None


def download_video(url: str, output_path: Path) -> bool:
    """下载视频到本地"""
    print(f"\n[agnes] 下载视频到: {output_path.name}")
    try:
        resp = requests.get(url, timeout=300, stream=True)
        resp.raise_for_status()

        total_size = int(resp.headers.get("content-length", 0))
        downloaded = 0

        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    pct = downloaded * 100 // total_size
                    print(f"\r[agnes] 下载中: {pct}% ({downloaded/1024/1024:.1f}MB)", end="")

        file_size = output_path.stat().st_size
        print(f"\n[agnes] 下载完成: {file_size/1024/1024:.1f}MB")
        return True
    except Exception as e:
        print(f"\n[agnes] 下载失败: {e}")
        return False


def generate_single_segment(segment: dict) -> bool:
    """生成单个视频段落"""
    print("\n" + "=" * 60)
    print(f"  {segment['name']} (~{segment['duration']}秒)")
    print("=" * 60)

    task_data = create_video_task(segment)
    if not task_data:
        return False

    video_url = poll_video_result(task_data, max_wait=600)
    if not video_url:
        return False

    output_file = OUTPUT_DIR / f"{segment['name']}.mp4"
    return download_video(video_url, output_file)


def main():
    """默认生成第1段，用户可指定--all生成全部"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="生成全部4段视频")
    parser.add_argument("--index", type=int, default=1, help="生成第N段(1-4)")
    args = parser.parse_args()

    print("=" * 60)
    print("  Agnes Video V2.0 军事视频生成")
    print("  风格: 玉渊谭天CG战火风")
    print(f"  API Key: {API_KEY[:8]}...{API_KEY[-4:]}")
    print(f"  输出目录: {OUTPUT_DIR}")
    print("=" * 60)

    if args.all:
        print(f"\n将生成全部 {len(SEGMENTS)} 段视频...")
        results = []
        for i, seg in enumerate(SEGMENTS, 1):
            print(f"\n--- 进度: {i}/{len(SEGMENTS)} ---")
            success = generate_single_segment(seg)
            results.append((seg["name"], success))
            if not success:
                print(f"\n[WARNING] {seg['name']} 生成失败，继续下一段")

        print("\n" + "=" * 60)
        print("  生成结果汇总")
        print("=" * 60)
        for name, success in results:
            status = "OK" if success else "FAIL"
            print(f"  [{status}] {name}")
    else:
        idx = max(0, min(args.index - 1, len(SEGMENTS) - 1))
        segment = SEGMENTS[idx]
        success = generate_single_segment(segment)
        if success:
            print(f"\n[OK] 视频已生成: {OUTPUT_DIR / segment['name']}.mp4")
            print("  后续步骤: 导入剪映 -> 加AI配音 + BGM + 字幕 -> 导出发布抖音")
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
