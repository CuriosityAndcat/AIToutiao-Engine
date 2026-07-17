#!/usr/bin/env python3
"""
AIToutiao 引擎模式 - 独立内容生成引擎
===========================================
基于 Streamlit 的 Web 界面，将视频下载→语音转录→AI写作→人工化改写→配图生成→图文组装
封装为一键式操作。完全独立于主项目，所有依赖内置于 engine_mode/ 目录。

端口：8502（与主项目 8501 隔离）
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import html
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import re

import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

# ── 修复 Windows GBK 编码 ──
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── 路径初始化 ──
ENGINE_ROOT = Path(__file__).parent
sys.path.insert(0, str(ENGINE_ROOT / "lib" / "toutiao-auto-publisher" / "backend"))
sys.path.insert(0, str(ENGINE_ROOT / "lib" / "wewrite-main" / "toolkit"))
sys.path.insert(0, str(ENGINE_ROOT / "lib" / "sensevoice-asr"))

OUTPUTS_DIR = ENGINE_ROOT / os.getenv("PIPELINE_OUTPUT_DIR", "outputs")

# ── 强行预加载 backend/config 模块 ──
# 防止 ai_writer.py 中的 from config import settings 错误解析到 wewrite-main/toolkit/config.py
import importlib.util
_backend_config_path = ENGINE_ROOT / "lib" / "toutiao-auto-publisher" / "backend" / "config.py"
_config_spec = importlib.util.spec_from_file_location("config", str(_backend_config_path))
_config_mod = importlib.util.module_from_spec(_config_spec)
sys.modules["config"] = _config_mod
_config_spec.loader.exec_module(_config_mod)
settings = _config_mod.settings

# ── 加载 .env ──
try:
    from dotenv import load_dotenv
    load_dotenv(ENGINE_ROOT / ".env")
except ImportError:
    pass

# ── 从 backend 导入（config 已在顶部预加载，避免路径冲突）──
try:
    from models import ContentType, ContentStyle
except Exception:
    ContentType = None
    ContentStyle = None

# ── Phase 3 编排层（已抽至 backend/write_stage.py）──
from write_stage import research_and_write as _research_and_write_impl, PipelineHooks as _PipelineHooks

# ── 发布服务（懒加载，避免 patchright 依赖阻断流水线）──
_publisher_imported = False


def _get_publisher():
    """懒加载发布服务模块（patchright/playwright 非流水线运行时必需）。"""
    global _publisher_imported
    if not _publisher_imported:
        from publisher_service import publish_article, check_login_status, launch_login_browser
        _publisher_imported = True
        return publish_article, check_login_status, launch_login_browser
    from publisher_service import publish_article, check_login_status, launch_login_browser
    return publish_article, check_login_status, launch_login_browser

# ── 页面配置 ──
st.set_page_config(
    page_title="AIToutiao 引擎模式",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── 慢导入懒加载（首次调用时导入并缓存，之后瞬间返回）──
_TORCH_MOD = None
_PIPELINE_FN = None

def _ensure_transcribe_imports():
    """懒加载 torch 和 transformers.pipeline。
    首次调用约 45 秒（模块级全局缓存，之后 O(1) 返回）。"""
    global _TORCH_MOD, _PIPELINE_FN
    if _TORCH_MOD is None:
        import torch as _TORCH_MOD
    if _PIPELINE_FN is None:
        from transformers import pipeline as _PIPELINE_FN
    return _TORCH_MOD, _PIPELINE_FN


# ============================================================
# 自定义 CSS（暗色新闻编辑风 · 含浅色双主题）
# ============================================================
# CSS 已提取到 ui/styles.css（P1-1），theme tokens → ui/theme_tokens.py
from ui.styles import _inject_css
from ui import log_sink

_inject_css()


# ============================================================
# Session State 初始化
# ============================================================
_DEFAULTS = {
    "logs": [],
    "progress_pct": 0.0,
    "current_stage": "",
    "stage_status": {
        "下载": "pending",
        "转录": "pending",
        "研究写作": "pending",
        "配图": "pending",
        "组装": "pending",
    },
    "pipeline_state": None,
    "result_data": None,
    "run_id": "",
    "is_running": False,
    "elapsed_seconds": 0.0,
    "processed_url": "",   # 单向数据通道：URL 提取 → 流水线执行
    "pipeline_error": None,  # 后台线程异常信息
    "pipeline_done": False,  # 后台线程完成标记
    "log_file_path": "",     # 本次运行的日志文件绝对路径（持久化落盘）
    # 发布状态
    "publish_result": None,       # 上次发布结果 dict
    "publish_running": False,     # 发布进行中标记
    "login_verified": None,       # 登录验证结果缓存（None=未检查）
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── 进度里程碑常量（消除魔法数字）──
_PROGRESS_MAP = {
    "download_start": 0.05,       # 下载阶段起点锚
    "transcribe_start": 0.18,
    "transcribe_done": 0.28,
    # 研究-写作阶段（对接 write_stage.py 进度语义）
    "research_start": 0.30,       # 初始搜索启动
    "research_search_done": 0.34,  # 初始搜索完成（对齐 research.py）
    "research_write_start": 0.35,  # 写作循环启动
    "research_iter_base": 0.35,    # 迭代进度基准（V2: +0.03/轮，CP: +0.04/轮）
    "research_eval_start": 0.45,   # 评估/Compose 阶段
    "research_humanize": 0.48,     # 人工化改写
    "research_humanize_done": 0.55,  # 改写完成
    "research_done": 0.57,         # 研究-写作完成
    "images_start": 0.58,         # 配图阶段起点锚
    "images_skipped": 0.65,
    "images_cover_done": 0.62,
    "images_all_done": 0.67,
    "assembly_start": 0.70,
    "assembly_done": 0.80,
    "pipeline_complete": 1.0,
}

# ── 日志文件持久化：每次启动生成独立日志文件 ──
if not st.session_state.log_file_path:
    _log_dir = ENGINE_ROOT / "log"
    _log_dir.mkdir(parents=True, exist_ok=True)
    _log_filename = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    st.session_state.log_file_path = str(_log_dir / _log_filename)

# 安装 stderr → 日志文件 Tee（只安装一次，避免 Streamlit 多次 rerun 重复包装）
log_sink.install(st.session_state.log_file_path)



# ============================================================
# 辅助函数
# ============================================================
def add_log(msg: str, level: str = "info"):
    """添加日志条目（线程安全）：stderr + UI 状态缓存 + 日志文件。"""
    log_sink.add_log(msg, level)


def _sync_ui_state_to_session():
    """把 ui.log_sink 的快照同步到 st.session_state（主线程/fragment 专用）。"""
    try:
        snap = log_sink.snapshot()
        st.session_state.is_running = snap["is_running"]
        st.session_state.pipeline_done = snap["pipeline_done"]
        st.session_state.pipeline_error = snap["pipeline_error"]
        st.session_state.result_data = snap["result_data"]
        st.session_state.run_id = snap["run_id"]
        st.session_state.current_stage = snap["current_stage"]
        st.session_state.stage_status = snap["stage_status"]
        log_sink.set_progress(snap["progress_pct"])
        st.session_state.logs = snap["logs"]
        st.session_state.elapsed_seconds = snap["elapsed_seconds"]
        st.session_state.awaiting_next = snap.get("awaiting_next", False)
    except Exception:
        pass



def _estimate_transcribe_time(video_path: str):
    """用 ffprobe 获取视频时长并估算 CPU 转录时间。"""
    try:
        import subprocess as sp
        probe = sp.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, timeout=10,
        )
        dur = int(float(probe.stdout.strip()))
        if dur < 60:
            add_log(f"视频约 {dur} 秒，转录预计 {dur * 3}~{dur * 5} 秒……", "warning")
        else:
            lo = dur * 3 // 60
            hi = dur * 5 // 60
            add_log(f"视频约 {dur} 秒，CPU 转录预计 {lo}~{hi} 分钟……", "warning")
    except Exception:
        pass  # ffprobe 不可用时静默跳过


def set_stage(name: str, status: str):
    """更新阶段状态（线程安全）。"""
    log_sink.set_stage(name, status)



# ── Emoji 映射常量（模块级，避免每次 add_log 重建字典）──
_EMOJI_MAP = {"info": "📝", "success": "✅", "error": "❌", "warning": "⚠️", "stage": "🔷"}


def _emoji_for_level(level: str) -> str:
    return _EMOJI_MAP.get(level, "📝")


# ── 日志轮转常量（10MB × 最多 3 个备份）──
# ============================================================
# PipelineState（轻量版，Streamlit 用）
# ============================================================

class PipelineState:
    """流水线状态管理，支持断点续跑。"""

    def __init__(
        self,
        run_id: str = "",
        input_url: str = "",
        content_type: str = "toutie",
        content_style: str = "baoming_shuo",
        enable_humanize: bool = False,
        with_images: bool = False,
        completed_stages: Optional[List[str]] = None,
        outputs: Optional[Dict[str, Any]] = None,
    ):
        self.run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.input_url = input_url
        self.content_type = content_type
        self.content_style = content_style
        self.enable_humanize = enable_humanize
        self.with_images = with_images
        self.completed_stages: List[str] = completed_stages or []
        self.outputs: Dict[str, Any] = outputs or {}

    @property
    def run_dir(self) -> Path:
        return OUTPUTS_DIR / self.run_id[:8] / self.run_id

    @property
    def state_file(self) -> Path:
        return self.run_dir / "pipeline_state.json"

    def is_done(self, stage: str) -> bool:
        return stage in self.completed_stages

    def mark_done(self, stage: str):
        if stage not in self.completed_stages:
            self.completed_stages.append(stage)

    def save(self):
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(
                {
                    "run_id": self.run_id,
                    "input_url": self.input_url,
                    "content_type": self.content_type,
                    "content_style": self.content_style,
                    "enable_humanize": self.enable_humanize,
                    "with_images": self.with_images,
                    "completed_stages": self.completed_stages,
                    "outputs": self.outputs,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, run_id: str) -> Optional["PipelineState"]:
        date_str = run_id[:8]
        sf = OUTPUTS_DIR / date_str / run_id / "pipeline_state.json"
        if sf.exists():
            data = json.loads(sf.read_text(encoding="utf-8"))
            # 向后兼容：旧版 state JSON 可能缺少 with_images 字段（2026-07-11 前生成）
            data.setdefault("with_images", False)
            return cls(**data)
        return None

    @classmethod
    def find_existing(cls, url: str) -> Optional["PipelineState"]:
        if not OUTPUTS_DIR.exists():
            return None
        for date_dir in sorted(OUTPUTS_DIR.iterdir(), reverse=True):
            if not date_dir.is_dir():
                continue
            for run_dir in sorted(date_dir.iterdir(), reverse=True):
                sf = run_dir / "pipeline_state.json"
                if sf.exists():
                    try:
                        data = json.loads(sf.read_text(encoding="utf-8"))
                        if data.get("input_url") == url:
                            return cls(**data)
                    except Exception:
                        continue
        return None


# ============================================================
# URL 提取工具
# ============================================================
def extract_douyin_url(raw_text: str) -> Optional[str]:
    """从用户粘贴的分享文本中提取抖音链接。

    用户从抖音复制分享链接时，粘贴的往往是整段描述文本，例如：
        "1.74 aAG:/ ... 抖音独家 | 普京急了... https://v.douyin.com/wPI_y-7jkO4/ 复制此链接..."
    此函数从中提取出真正的 URL。
    """
    import re

    raw_text = raw_text.strip()

    # 如果已经是纯 URL，直接返回
    if re.match(r'^https?://', raw_text):
        # 检查是否以 URL 开头但也有尾随文本，清理之
        m = re.match(r'^(https?://[^\s]+)', raw_text)
        if m:
            url = m.group(1).rstrip('.,;:!?。，；：！？')
            return url
        return raw_text

    # 从文本中提取 URL
    url_patterns = [
        r'https?://v\.douyin\.com/[^\s]+',
        r'https?://www\.douyin\.com/video/[^\s]+',
        r'https?://www\.douyin\.com/user/[^\s]+',
        r'https?://www\.iesdouyin\.com/[^\s]+',
        r'https?://[^\s]*douyin[^\s]*',
        r'https?://[^\s]+',  # 通用兜底
    ]

    for pattern in url_patterns:
        m = re.search(pattern, raw_text)
        if m:
            url = m.group(0).rstrip('.,;:!?。，；：！？')
            # 确保 URL 看起来有效
            if len(url) > 15 and ('douyin.com' in url or 'iesdouyin.com' in url):
                return url
            elif len(url) > 15:
                return url

    return None


# ============================================================
# 阶段1：视频下载（全自动，支持抖音/多平台）
# ============================================================
# ── 下载脚本目录（Playwright Node.js 方案）──
_VIDEO_DL_DIR = ENGINE_ROOT / "lib" / "video-batch-download-main"
_DOWNLOAD_SCRIPT = _VIDEO_DL_DIR / "scripts" / "download.mjs"
_SETUP_SCRIPT = _VIDEO_DL_DIR / "scripts" / "setup.mjs"

# 抖音域名特征
_DOUYIN_PATTERNS = ["douyin.com", "iesdouyin.com"]


def _is_douyin_url(url: str) -> bool:
    """判断是否为抖音链接。"""
    url_lower = url.lower()
    return any(p in url_lower for p in _DOUYIN_PATTERNS)


def _ensure_node_env() -> bool:
    """确保 Node.js + Playwright 环境就绪（自动安装）。返回是否就绪。"""
    import subprocess as sp

    # 1. 检查 Node.js
    try:
        sp.run(["node", "--version"], capture_output=True, check=True, timeout=10)
    except (FileNotFoundError, sp.CalledProcessError):
        add_log("❌ Node.js 未安装，Playwright 浏览器下载不可用", "error")
        add_log("   📥 安装 Node.js (>=20)：https://nodejs.org/ （选择 LTS 版本）", "info")
        add_log("   💡 安装后将自动启用最稳定的抖音下载方式", "info")
        return False

    # 2. 检查 Playwright npm 包
    pkg_json = _VIDEO_DL_DIR / "package.json"
    node_modules = _VIDEO_DL_DIR / "node_modules" / "playwright"
    if not node_modules.exists() and pkg_json.exists():
        add_log("📦 安装 Playwright 依赖...", "info")
        try:
            import sys as _sys
            _sys.stderr.write("[node-env] npm install 开始...\n"); _sys.stderr.flush()
            sp.run(["npm", "install"], cwd=str(_VIDEO_DL_DIR),
                   capture_output=True, check=True, timeout=120)
            _sys.stderr.write("[node-env] npm install 完成\n"); _sys.stderr.flush()
        except sp.CalledProcessError as e:
            add_log(f"npm install 失败: {e.stderr.decode(errors='replace')[:300] if e.stderr else '未知错误'}", "warning")
        except FileNotFoundError:
            add_log("npm 未找到（Node.js 可能安装不完整）", "warning")
            return False

    # 3. 检查/安装 Playwright Chromium
    if _SETUP_SCRIPT.exists():
        try:
            import sys as _sys
            _sys.stderr.write("[node-env] Playwright setup 开始...\n"); _sys.stderr.flush()
            result = sp.run(["node", str(_SETUP_SCRIPT)], cwd=str(_VIDEO_DL_DIR),
                           capture_output=True, text=True, timeout=180)
            _sys.stderr.write(f"[node-env] Playwright setup 完成, rc={result.returncode}\n"); _sys.stderr.flush()
            if result.returncode == 0:
                return True
            add_log(f"Playwright setup 失败: {result.stderr[:300]}", "warning")
        except sp.TimeoutExpired:
            add_log("Playwright Chromium 安装超时（>3分钟）", "warning")
        except Exception as e:
            add_log(f"Playwright setup 异常: {e}", "warning")

    # 即使 setup 没输出成功，只要脚本存在就尝试
    return _DOWNLOAD_SCRIPT.exists() and node_modules.exists()


def _kill_process_tree(pid: int) -> None:
    """Windows 下强制结束进程及其子进程。"""
    import subprocess as sp
    try:
        sp.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            timeout=15,
        )
    except Exception:
        pass


def _run_subprocess_with_timeout(
    cmd: List[str],
    cwd: Path,
    timeout: int = 300,
    log_prefix: str = "",
) -> tuple[int, str, str]:
    """运行子进程，带超时与进程树清理。

    实时把 stdout/stderr 输出到 add_log，避免 capture_output 在 Windows 上
    因孙进程（如 Chromium）未退出而永久阻塞。
    返回 (returncode, stdout_text, stderr_text)。
    """
    import subprocess as sp
    import threading as _threading

    proc = sp.Popen(
        cmd,
        cwd=str(cwd),
        stdout=sp.PIPE,
        stderr=sp.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=sp.CREATE_NEW_PROCESS_GROUP,
    )

    stdout_lines: List[str] = []
    stderr_lines: List[str] = []

    def _reader(stream, buf: List[str], level: str):
        try:
            for line in stream:
                txt = line.rstrip("\n")
                if txt:
                    buf.append(txt)
                    add_log(f"{log_prefix}{txt}", level)
        except Exception:
            pass

    t_out = _threading.Thread(target=_reader, args=(proc.stdout, stdout_lines, "info"))
    t_err = _threading.Thread(target=_reader, args=(proc.stderr, stderr_lines, "warning"))
    t_out.start()
    t_err.start()

    rc = -1
    try:
        rc = proc.wait(timeout=timeout)
    except sp.TimeoutExpired:
        add_log(f"{log_prefix}子进程超时（>{timeout}秒），强制终止", "warning")
        _kill_process_tree(proc.pid)
        try:
            rc = proc.wait(timeout=5)
        except Exception:
            rc = -1
    finally:
        # 主动关闭管道，解除 reader 线程阻塞
        try:
            proc.stdout.close()
        except Exception:
            pass
        try:
            proc.stderr.close()
        except Exception:
            pass
        t_out.join(timeout=5)
        t_err.join(timeout=5)

    return rc, "\n".join(stdout_lines), "\n".join(stderr_lines)


def _download_via_node(state: PipelineState) -> Optional[Dict[str, Any]]:
    """使用 Node.js Playwright 脚本下载视频（全自动，无需 cookies）。
    返回 {'video_files': [...], 'title': '...', 'description': '...'} 或 None。
    """
    state.run_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "node", str(_DOWNLOAD_SCRIPT),
        "--output", str(state.run_dir),
        "--no-transcribe",
        "--page-timeout", "60",
        "--media-wait", "30",
        state.input_url,
    ]

    add_log("🌐 Playwright 浏览器自动抓取中...", "info")
    add_log("  自动打开页面拦截视频流，无需 cookies", "info")

    try:
        rc, stdout, stderr = _run_subprocess_with_timeout(
            cmd, cwd=_VIDEO_DL_DIR, timeout=300, log_prefix="[node] "
        )
        if rc != 0:
            add_log(f"Node.js 下载返回非零: {rc}", "warning")
            if stderr:
                add_log(f"  stderr: {stderr[:500]}", "warning")
            return None

        # 从 stdout JSON 中提取元数据
        title = ""
        description = ""
        try:
            json_match = __import__("re").search(r'\{[\s\S]*"results"[\s\S]*\}', stdout)
            if json_match:
                data = json.loads(json_match.group())
                for r in data.get("results", []):
                    if r.get("title"):
                        title = r["title"]
                    if r.get("jsonPath"):
                        meta_path = Path(r["jsonPath"])
                        if meta_path.exists():
                            meta = json.loads(meta_path.read_text(encoding="utf-8"))
                            title = title or meta.get("title", "")
                            description = meta.get("description", "")
                    break
        except Exception:
            pass
        if not title:
            title = state.input_url.rsplit("/", 1)[-1][:50]

        # 查找下载的视频文件
        video_files = []
        for ext in ("*.mp4", "*.mkv", "*.webm", "*.mov", "*.flv"):
            video_files.extend(state.run_dir.glob(f"**/{ext}"))

        if not video_files:
            temp_dir = state.run_dir / ".temp"
            for ext in ("*.mp4", "*.mkv"):
                video_files.extend(temp_dir.glob(ext))

        if video_files:
            return {
                "video_files": [str(v) for v in video_files],
                "title": title,
                "description": description or "",
            }

        add_log("Node.js 下载完成但未找到视频文件", "warning")
        return None

    except FileNotFoundError:
        add_log("Node.js 不可用", "warning")
        return None
    except Exception as e:
        add_log(f"Node.js 下载异常: {e}", "warning")
        return None



def _download_via_ytdlp(state: PipelineState, temp_dir: Path) -> Optional[Dict[str, Any]]:
    """使用 yt-dlp 下载（非抖音平台，或作为后备）。
    返回 {'video_files': [...], 'title': '...', 'description': '...'} 或 None。
    """
    import sys as _sys
    _sys.stderr.write("[yt-dlp] 开始...\n"); _sys.stderr.flush()
    try:
        _sys.stderr.write("[yt-dlp] import yt_dlp...\n"); _sys.stderr.flush()
        import yt_dlp
        _sys.stderr.write("[yt-dlp] import 成功\n"); _sys.stderr.flush()
    except ImportError:
        add_log("yt-dlp 未安装，正在自动安装...", "warning")
        import subprocess as _sp
        _sp.check_call([sys.executable, "-m", "pip", "install", "yt-dlp", "-q"])
        import yt_dlp

    def _progress_hook(d):
        if d["status"] == "downloading":
            pct = d.get("_percent_str", "0%").strip("%")
            try:
                p = float(pct) / 100
            except ValueError:
                p = 0
            # 下载进度区间：download_start → transcribe_start（基于常量跨度，消除魔法数字）
            log_sink.set_progress(
                _PROGRESS_MAP["download_start"]

                + p * (_PROGRESS_MAP["transcribe_start"] - _PROGRESS_MAP["download_start"])
            )

    ydl_opts = {
        "outtmpl": str(temp_dir / "%(id)s.%(ext)s"),
        "progress_hooks": [_progress_hook],
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
    }

    # ── 抖音 Cookie 注入：优先浏览器 > 文件 > 无 cookie ──
    is_douyin = _is_douyin_url(state.input_url)
    if is_douyin:
        cookie_source = os.getenv("YOUTUBE_DL_COOKIE_SOURCE", "")
        cookie_file = os.getenv("YOUTUBE_DL_COOKIE_FILE", "")

        if cookie_source:
            # 方式1：从浏览器提取（如 "chrome", "firefox"）
            ydl_opts["cookiesfrombrowser"] = (cookie_source,)
            add_log(f"🍪 从浏览器 [{cookie_source}] 提取 Cookies", "info")
            _sys.stderr.write(f"[yt-dlp] cookiesfrombrowser={cookie_source}\n"); _sys.stderr.flush()
        elif cookie_file and Path(cookie_file).exists():
            # 方式2：从 Netscape 格式 cookie 文件
            ydl_opts["cookiefile"] = cookie_file
            add_log(f"🍪 使用 Cookie 文件: {cookie_file}", "info")
            _sys.stderr.write(f"[yt-dlp] cookiefile={cookie_file}\n"); _sys.stderr.flush()
        else:
            # 无 cookie 配置时，仅在用户明确开启「浏览器 Cookie」开关时自动提取
            _allow_cookies = st.session_state.get("use_browser_cookies", False)
            if _allow_cookies:
                _sys.stderr.write("[yt-dlp] 尝试 cookiesfrombrowser=chrome\n"); _sys.stderr.flush()
                ydl_opts["cookiesfrombrowser"] = ("chrome",)
                add_log("🍪 尝试从 Chrome 浏览器自动提取 Cookies（用户已授权）", "info")
            else:
                add_log("🔒 跳过 Cookie 提取（可在侧边栏开启「浏览器 Cookie」开关）", "info")

    try:
        _sys.stderr.write("[yt-dlp] extract_info 开始...\n"); _sys.stderr.flush()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(state.input_url, download=True)
        _sys.stderr.write("[yt-dlp] extract_info 完成\n"); _sys.stderr.flush()
    except Exception as e:
        err_msg = str(e).split(chr(10))[0][:200]
        add_log(f"yt-dlp 下载失败: {err_msg}", "warning")
        # 如果是 Cookie 相关错误，给出明确提示
        if "cookie" in str(e).lower() or "cookies" in str(e).lower():
            add_log("💡 Cookie 提取失败，请尝试以下方案：", "info")
            add_log("   1. 安装 Node.js 后重试（将自动使用 Playwright 下载）", "info")
            add_log("   2. 手动从浏览器导出 cookie 文件并设置环境变量 YOUTUBE_DL_COOKIE_FILE", "info")
        return None

    video_files = []
    for f in temp_dir.iterdir():
        if f.suffix in (".mp4", ".mkv", ".webm", ".mov", ".flv"):
            video_files.append(str(f))

    if video_files:
        return {
            "video_files": video_files,
            "title": info.get("title", ""),
            "description": info.get("description", ""),
        }
    return None


def step_download(state: PipelineState) -> bool:
    """全自动视频下载：抖音用 Playwright 浏览器拦截，其他用 yt-dlp。"""
    import sys as _sys
    _sys.stderr.write("[download] step_download 开始\n"); _sys.stderr.flush()
    set_stage("下载", "running")
    add_log(f"阶段1/5: 视频下载 - {state.input_url[:60]}...", "stage")

    temp_dir = state.run_dir / ".temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    _sys.stderr.write(f"[download] temp_dir={temp_dir}\n"); _sys.stderr.flush()

    is_douyin = _is_douyin_url(state.input_url)
    _sys.stderr.write(f"[download] is_douyin={is_douyin}\n"); _sys.stderr.flush()
    result = None

    # ── 抖音：Playwright 浏览器自动化（零人工干预）──
    if is_douyin:
        add_log("📱 检测到抖音链接，使用 Playwright 浏览器自动化下载", "info")
        _sys.stderr.write("[download] 调用 _ensure_node_env...\n"); _sys.stderr.flush()
        if _ensure_node_env():
            _sys.stderr.write("[download] Node 环境就绪，调用 _download_via_node...\n"); _sys.stderr.flush()
            result = _download_via_node(state)
        else:
            _sys.stderr.write("[download] Node 环境不完整\n"); _sys.stderr.flush()
            add_log("⚠️ Node.js/Playwright 环境不完整，回退到 yt-dlp", "warning")

    # ── 非抖音 / Node.js 失败 → yt-dlp ──
    if result is None:
        import sys as _sys
        _sys.stderr.write("[download] 回退到 yt-dlp...\n"); _sys.stderr.flush()
        if is_douyin:
            add_log("🔄 回退到 yt-dlp 下载...", "info")
        _sys.stderr.write("[download] 调用 _download_via_ytdlp...\n"); _sys.stderr.flush()
        result = _download_via_ytdlp(state, temp_dir)
        _sys.stderr.write(f"[download] yt-dlp 返回: {result is not None}\n"); _sys.stderr.flush()

    # ── 处理结果 ──
    if result and result.get("video_files"):
        state.outputs["video_files"] = result["video_files"]
        state.outputs["video_title"] = result.get("title", "")
        state.outputs["video_description"] = result.get("description", "")
        size_mb = sum(Path(vf).stat().st_size for vf in result["video_files"]) / (1024 * 1024)
        add_log(f"视频下载完成 ({size_mb:.1f} MB, {len(result['video_files'])} 个文件)", "success")
        set_stage("下载", "done")
        state.mark_done("download")
        return True

    # ── 兜底：检查缓存 ──
    existing = list(temp_dir.glob("*.mp4")) + list(temp_dir.glob("*.mkv"))
    existing += list(state.run_dir.glob("**/*.mp4")) + list(state.run_dir.glob("**/*.mkv"))
    if existing:
        state.outputs["video_files"] = [str(v) for v in existing]
        add_log(f"使用已缓存的视频文件 ({len(existing)} 个)", "warning")
        set_stage("下载", "done")
        state.mark_done("download")
        return True

    add_log("❌ 所有下载方式均失败", "error")
    set_stage("下载", "failed")
    return False


# ============================================================
# 阶段2：语音转录
# ============================================================
def step_transcribe(state: PipelineState) -> bool:
    """使用 faster-whisper、transformers 或 SenseVoice 转录视频音频。

    转录后端优先级（由 TRANSCRIBE_BACKEND 环境变量控制）：
      - "sensevoice"    → 使用 SenseVoiceSmall（阿里达摩院，中文最优）
      - "transformers"  → 直接使用 HuggingFace transformers（国内可配 HF_ENDPOINT 镜像）
      - "faster_whisper" → 使用 faster-whisper（CTranslate2，可能某些 Windows 环境不兼容）
      - 未设置/其他     → 优先 faster-whisper，失败回退 transformers
    """
    import sys as _sys
    _sys.stderr.write("[transcribe] step_transcribe 开始\n"); _sys.stderr.flush()
    set_stage("转录", "running")
    add_log("阶段2/5: 语音转录", "stage")

    # 查找视频文件
    video_files = state.outputs.get("video_files", [])
    _sys.stderr.write(f"[transcribe] video_files={len(video_files)}\n"); _sys.stderr.flush()
    if not video_files:
        temp_dir = state.run_dir / ".temp"
        video_files = [str(p) for p in temp_dir.glob("*.mp4")] + [str(p) for p in temp_dir.glob("*.mkv")]
        _sys.stderr.write(f"[transcribe] fallback video_files={len(video_files)}\n"); _sys.stderr.flush()

    if not video_files:
        # 尝试从描述兜底
        desc = state.outputs.get("video_description", "")
        title = state.outputs.get("video_title", "")
        if desc and len(desc) > 30:
            text = f"标题：{title}\n\n{desc}" if title else desc
            transcript_file = state.run_dir / "transcript.txt"
            transcript_file.write_text(text, encoding="utf-8")
            state.outputs["transcript_text"] = text
            state.outputs["transcript_files"] = [str(transcript_file)]
            add_log(f"无视频文件，使用视频描述作为文本 ({len(text)} 字符)", "warning")
            set_stage("转录", "done")
            state.mark_done("transcribe")
            return True
        add_log("没有找到视频文件且无视频描述文本", "error")
        set_stage("转录", "failed")
        return False

    video_path = video_files[0]
    _sys.stderr.write(f"[transcribe] video_path={video_path}\n"); _sys.stderr.flush()
    add_log(f"转录文件: {Path(video_path).name}", "info")

    # 确定转录后端
    backend = os.getenv("TRANSCRIBE_BACKEND", "faster_whisper").strip().lower()
    model = os.getenv("WHISPER_MODEL", "small")
    _sys.stderr.write(f"[transcribe] backend={backend} model={model}\n"); _sys.stderr.flush()

    # 对于 transformers 后端，使用短名映射
    MODEL_MAP = {"tiny": "openai/whisper-tiny", "small": "openai/whisper-small",
                 "base": "openai/whisper-base", "medium": "openai/whisper-medium"}

    log_sink.set_progress(_PROGRESS_MAP["transcribe_start"])

    # ── SenseVoice 转录（中文最优，唯一后端） ──
    _sys.stderr.write("[transcribe] 使用 SenseVoice 后端\n"); _sys.stderr.flush()
    add_log("使用 SenseVoice 后端（阿里达摩院，中文最优）", "info")
    try:
        return _transcribe_sensevoice(video_path, state)
    except Exception as e:
        add_log(f"SenseVoice 转录失败: {e}", "error")
        set_stage("转录", "failed")
        return False


def _extract_audio(video_path: str, run_dir: Path) -> str:
    """从视频提取 16kHz WAV 音频。"""
    import subprocess as sp

    audio_path = run_dir / "audio.wav"
    if audio_path.exists():
        return str(audio_path)

    ffmpeg_paths = ["ffmpeg", "ffmpeg.exe"]
    ffmpeg_exe = None
    for fp in ffmpeg_paths:
        try:
            sp.run([fp, "-version"], capture_output=True, timeout=5)
            ffmpeg_exe = fp
            break
        except Exception:
            continue

    if ffmpeg_exe:
        sp.run(
            [ffmpeg_exe, "-i", video_path, "-ar", "16000", "-ac", "1",
             "-f", "wav", str(audio_path), "-y", "-loglevel", "error"],
            check=True, timeout=300,
        )
        return str(audio_path)
    else:
        add_log("ffmpeg 未找到，直接转录视频文件（可能较慢）", "warning")
        return video_path


def _transcribe_transformers(video_path, backend, model, model_map, state):
    """使用 transformers 后端转录。"""
    if "HF_ENDPOINT" not in os.environ:
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

    hf_model = model_map.get(model, model)
    add_log(f"📦 模型: {hf_model}", "info")

    # 抑制 transformers 内部日志噪音
    import logging
    logging.getLogger("transformers").setLevel(logging.ERROR)

    # 导入转录引擎（首次约 45 秒，之后瞬间完成）
    add_log("⏳ 正在加载语音识别引擎（首次约 45 秒）……", "warning")
    torch_mod, pipeline_fn = _ensure_transcribe_imports()
    add_log("✅ 引擎加载完成，正在加载语音模型……", "info")

    # 加载语音识别模型（首次需下载 ~500MB，请耐心等待）
    pipe = pipeline_fn(
        "automatic-speech-recognition",
        model=hf_model,
        device="cpu",
        torch_dtype=torch_mod.float32,
    )

    add_log("✅ 模型就绪，正在从视频提取音频……", "info")
    audio_path = _extract_audio(video_path, state.run_dir)
    _estimate_transcribe_time(video_path)
    add_log("正在转录（CPU 推理中，请耐心等待……）", "info")
    result = pipe(audio_path, return_timestamps=True, generate_kwargs={"language": "zh", "task": "transcribe"})
    add_log("语音识别完成，正在处理文本……", "info")
    text = result["text"].strip()

    # 繁体转简体
    try:
        import opencc
        text = opencc.OpenCC("t2s").convert(text)
    except ImportError:
        pass

    # 清洗重复循环
    import re
    pattern = re.compile(r'(.{1,4}?)\1{5,}')
    match = pattern.search(text)
    if match:
        text = text[:match.start()].strip()
        add_log("检测到重复循环，已截断", "warning")

    transcript_file = state.run_dir / "transcript.txt"
    transcript_file.write_text(text, encoding="utf-8")

    state.outputs["transcript_text"] = text
    state.outputs["transcript_files"] = [str(transcript_file)]

    add_log(f"转录完成 ({len(text)} 字符)", "success")
    set_stage("转录", "done")
    state.mark_done("transcribe")
    log_sink.set_progress(_PROGRESS_MAP["transcribe_done"])
    return True


def _transcribe_sensevoice(video_path, state):
    """使用 SenseVoiceSmall 后端转录（阿里达摩院，中文 ASR 最优）。

    依赖: funasr + sentencepiece 0.2.0（非 0.2.1，有 Windows bug）
    模型: 从 SENSEVOICE_MODEL_DIR 环境变量指定或自动查找
    """
    add_log("📦 后端: SenseVoiceSmall（阿里达摩院）", "info")

    # 抑制日志噪音
    import logging
    logging.getLogger("funasr").setLevel(logging.WARNING)

    # 提取音频
    audio_path = _extract_audio(video_path, state.run_dir)
    _estimate_transcribe_time(video_path)
    add_log("正在加载 SenseVoice 模型（首次约 90 秒）……", "warning")

    # 导入转录模块
    from sensevoice_transcriber import transcribe

    # 模型目录自动探测：① 环境变量 → ② lib/ 内 → ③ 原始项目目录
    model_dir = os.getenv("SENSEVOICE_MODEL_DIR", "")
    if not model_dir:
        # 候选路径列表（按优先级）
        candidates = [
            ENGINE_ROOT / "lib" / "sensevoice-asr" / "models" / "iic" / "SenseVoiceSmall",
            Path(r"D:\AIToutiao\sensevoice-asr\models\iic\SenseVoiceSmall"),
        ]
        for p in candidates:
            if (p / "model.pt").exists():
                model_dir = str(p)
                add_log(f"🔍 自动检测到模型: {model_dir}", "info")
                break

    if not model_dir:
        # 所有候选都失败，放弃 SenseVoice，由上层 try/except 回退
        raise FileNotFoundError(
            "SenseVoice 模型未找到！请在 .env 中设置 SENSEVOICE_MODEL_DIR，"
            "或将模型放到 lib/sensevoice-asr/models/iic/SenseVoiceSmall/"
        )

    add_log("正在转录（CPU 推理中，请耐心等待……）", "info")
    text = transcribe(
        audio_path,
        language="zh",
        model_dir=model_dir or None,
        batch_size_s=15,
    )

    # 清洗重复循环（适配 SenseVoice 输出格式）
    import re
    pattern = re.compile(r'(.{1,4}?)\1{5,}')
    match = pattern.search(text)
    if match:
        text = text[:match.start()].strip()
        add_log("检测到重复循环，已截断", "warning")

    transcript_file = state.run_dir / "transcript.txt"
    transcript_file.write_text(text, encoding="utf-8")

    state.outputs["transcript_text"] = text
    state.outputs["transcript_files"] = [str(transcript_file)]

    add_log(f"转录完成 ({len(text)} 字符)", "success")
    set_stage("转录", "done")
    state.mark_done("transcribe")
    log_sink.set_progress(_PROGRESS_MAP["transcribe_done"])
    return True


# ============================================================
# Agnes Image 2.0 Flash 配图 API（替代 Pollinations，ERNIE 中文模型）
# ============================================================

def _get_agnes_config() -> dict:
    """获取 Agnes API 配置。

    优先使用模块级 ``settings``（pydantic 已从 .env 可靠加载，写入 .env 即生效，
    无需重启 Streamlit 进程）；仅当 settings 为空时 fallback 到 os.getenv，
    以兼容手动 ``export`` 的场景。解决旧实现依赖进程环境、面板填完不重启即失效的问题。
    """
    api_key = (getattr(settings, "AGNES_API_KEY", "") or "").strip()
    api_base = (getattr(settings, "AGNES_API_BASE", "") or "").strip()
    model = (getattr(settings, "AGNES_IMAGE_MODEL", "") or "").strip()

    if not api_key:
        api_key = os.getenv("AGNES_API_KEY", "").strip()
    if not api_base:
        api_base = os.getenv("AGNES_API_BASE", "https://apihub.agnes-ai.com/v1").strip()
    if not model:
        model = os.getenv("AGNES_IMAGE_MODEL", "agnes-image-2.0-flash").strip()

    return {"api_key": api_key, "api_base": api_base, "model": model}


def _generate_agnes_image(prompt: str, output_path: Path,
                           width: int = 1024, height: int = 1024,
                           timeout: int = 180,
                           max_retries: int = 3) -> Optional[str]:
    """调用 Agnes Image 2.0 Flash API 生成图片，保存到 output_path。

    Agnes 底层为 ERNIE-AIO-Turbo-fp8 + Z-Anime Checkpoint，
    中文 prompt 效果远优于英文。输出约 1.4–1.9 MB/1024×1024。

    内置指数退避重试（最多 max_retries 次），落盘后校验文件大小（>1KB）。
    成功返回文件路径字符串，失败返回 None。
    """
    import requests as _req
    import time as _time

    cfg = _get_agnes_config()
    api_key = cfg["api_key"]
    if not api_key:
        import sys as _sys
        _sys.stderr.write("[agnes] AGNES_API_KEY 未配置\n"); _sys.stderr.flush()
        return None

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    url = f"{cfg['api_base']}/images/generations"

    import sys as _sys

    last_error = ""
    for attempt in range(1, max_retries + 1):
        _sys.stderr.write(
            f"[agnes] 第{attempt}/{max_retries}次尝试: model={cfg['model']} "
            f"size={width}x{height} prompt={prompt[:80]}...\n"
        )
        _sys.stderr.flush()

        try:
            resp = _req.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                json={
                    "model": cfg["model"],
                    "prompt": prompt,
                    "size": f"{width}x{height}",
                    "n": 1,
                },
                timeout=timeout,
            )
            if resp.status_code != 200:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                _sys.stderr.write(f"[agnes] {last_error}\n"); _sys.stderr.flush()
                raise _req.RequestException(last_error)

            data = resp.json()
            image_url = (data.get("data", [{}])[0].get("url") or
                         data.get("url") or
                         data.get("image_url"))
            if not image_url:
                last_error = f"无图片 URL: {json.dumps(data, ensure_ascii=False)[:200]}"
                _sys.stderr.write(f"[agnes] {last_error}\n"); _sys.stderr.flush()
                raise ValueError(last_error)

            # 下载图片二进制
            img_resp = _req.get(image_url, timeout=120)
            img_resp.raise_for_status()
            output_path.write_bytes(img_resp.content)

            # ── 落盘校验：文件大小 > 1KB ──
            file_size = output_path.stat().st_size
            if file_size < 1024:
                last_error = f"文件过小 ({file_size} bytes)，可能为空/损坏"
                _sys.stderr.write(f"[agnes] {last_error}\n"); _sys.stderr.flush()
                raise ValueError(last_error)

            _sys.stderr.write(
                f"[agnes] 图片已保存: {output_path.name} ({file_size} bytes) [第{attempt}次成功]\n"
            ); _sys.stderr.flush()
            return str(output_path)

        except _req.Timeout:
            last_error = f"超时 ({timeout}s)"
            _sys.stderr.write(f"[agnes] {last_error}\n"); _sys.stderr.flush()
        except _req.RequestException as e:
            last_error = f"请求失败: {e}"
            _sys.stderr.write(f"[agnes] {last_error}\n"); _sys.stderr.flush()
        except Exception as e:
            last_error = f"异常: {e}"
            _sys.stderr.write(f"[agnes] {last_error}\n"); _sys.stderr.flush()

        # 非最后一次尝试时等待后重试
        if attempt < max_retries:
            wait = 2 ** attempt  # 2s, 4s, 8s
            _sys.stderr.write(f"[agnes] {wait}s后重试...\n"); _sys.stderr.flush()
            _time.sleep(wait)

    _sys.stderr.write(f"[agnes] {max_retries}次重试全部失败，放弃。最后错误: {last_error}\n"); _sys.stderr.flush()
    return None


# ============================================================
# 配图 Prompt 生成（LLM 驱动，DeepSeek / Pollinations flux 优化）
# ============================================================

# 系统指令：段落锚定式配图（封面全局抽象 + 内文严格按段落对应）
_IMAGE_PROMPT_SYSTEM = """你是一个专业的AI配图提示词工程师，专为中文图像生成模型优化。

## 封面-内文层级分工（核心纪律）

### COVER（封面图）
- 职责：描绘文章**全局抽象主题**的象征性画面。封面是"海报"，不是"剧照"。
- 主题来源：文章标题 + 全文概要（非任何具体段落）。
- 禁止：不得直接描绘任一段落的专属战斗场景或具体事件瞬间。
- 正确示例：文章讲"无人机撕破三层防线"，封面可画"阴云密布的战场上，廉价无人机群如蜂群涌向装甲车队"的全景——而非某一段的"油罐车爆炸"特写。

### INLINE_i（内文配图，i=1,2,3...）
- 职责：**严格对应第 i 个文章段落**的专属画面。读取 USER prompt 中标注的 `INLINE_i 对应段落`，只描绘该段内容。
- 禁止跨段引用：INLINE_1 不能画 INLINE_3 的场景，反之亦然。
- 抽象段落转化：若段落是分析/论述（如"制裁"），转化为视觉意象（如"集装箱港口冷清的航拍"）。

## 风格与美学
- 风格：真实照片、纪录片摄影、新闻摄影、战地摄影。避免"电影/3D渲染/概念艺术/cinematic"。
- 军事内容必须具体到真实装备、地点、事件，禁用"军事装备"等泛词。
- 光线：优先自然光、黄金时段光、阴天漫射光；夜战用微光夜视风格。
- 构图：单张完整统一构图，主体占据画面核心区域。底部空白为自然地面/海面/天空延伸。

## 硬性禁止
- 无文字、无字母、无水印、无Logo、无座舱特写。
- 单张完整照片，画面统一不可分割。禁止拼接与分割式构图。
- 禁止血腥/残肢/尸体特写。禁止真实可辨识个人面孔（用剪影/背影替代）。
- 禁止旗帜、徽章、宗教符号特写。
- 每条提示词不超过300字。纯中文，无解释、无markdown。"""

# 用户指令模板：段落锚定式（每张 INLINE 绑定对应段落原文）
_IMAGE_PROMPT_USER = """文章标题：{title}

全文概要（仅 COVER 参考，INLINE_i 不得使用）：{section_summary}

---
以下为段落→配图映射，每条 INLINE 严格对应所标注段落：
---

INLINE_1 对应段落：
{s1}

INLINE_2 对应段落：
{s2}

INLINE_3 对应段落：
{s3}

---
配图生成任务（1 封面 + 3 内文）：

## COVER
基于「标题」+「全文概要」输出一个全局抽象视觉意象（象征性构图、远景/氛围/地缘版图类画面），不得描绘任一段落的专属场景。

## INLINE_1 / INLINE_2 / INLINE_3
每条只基于上方标注的对应段落创作，提取该段核心场景/主体/情绪 → 转化为新闻摄影/战地摄影风格画面。禁止跨段引用。

## 格式（纯中文，每行一条，不超300字，不加解释）
COVER: <提示词>
INLINE_1: <提示词>
INLINE_2: <提示词>
INLINE_3: <提示词>"""


def _segment_article(content: str, n: int = 3) -> list:
    """将文章按自然段均分为 n 段（用于段落锚定配图）。

    预处理：按 \\n\\n 拆自然段 → 过滤标题/图片标记/引用块/空行 → 贪心均分。
    返回长度为 n 的字符串列表，每段约 total_chars/n 字。
    """
    raw = [p.strip() for p in content.split("\n\n") if p.strip()]
    body = [p for p in raw
            if not p.startswith("#") and not p.startswith("![") and not p.startswith(">")]
    if not body:
        return [content[:300]] * n  # 无可分段内容，全文复制为每段

    total = sum(len(p) for p in body)
    ideal = max(1, total // n)

    segments = []
    idx = 0
    for i in range(n):
        parts = []
        chars = 0
        limit = ideal if i < n - 1 else 10 ** 9  # 最后一段吃剩余
        while idx < len(body) and chars < limit:
            parts.append(body[idx])
            chars += len(body[idx])
            idx += 1
        txt = "\n\n".join(parts)
        segments.append(txt if txt else content[:300])

    return segments


def _build_section_summary(title: str, segments: list) -> str:
    """从标题 + 各段首句构建全文概要（仅 COVER 参考，~150 字）。"""
    parts = []
    for seg in segments:
        s = seg.split("。")[0].strip()
        if s and len(s) > 2:
            parts.append(s[:60])
    body = "。".join(parts[:2]) if parts else title
    return f"{title}。{body}。"[:250]


def _generate_image_prompts_via_llm(title: str, content: str, count: int = 2) -> dict:
    """段落锚定式配图 prompt 生成（封面 + 内文）。

    将文章分段 → USER prompt 显式标注 INLINE_i 对应段落原文 → LLM 逐段配图。
    签名不变 (title, content, count)，对调用方完全透明。

    返回 {'cover': str|None, 'inline': [str,...]}。
    任何异常向上抛出，由调用方 fallback。
    """
    from ai_writer import AIWriter

    inline_count = max(1, count)
    segments = _segment_article(content, n=inline_count)
    # 补齐到 inline_count（极短文章可能不足）
    while len(segments) < inline_count:
        segments.append(content[:300])
    summary = _build_section_summary(title, segments)

    # 组装分段锚定式 user prompt
    fmt = {"title": title[:100], "section_summary": summary}
    for i in range(inline_count):
        fmt[f"s{i+1}"] = segments[i][:600]
    # 补齐 s1/s2/s3 占位符（模板要求 3 个）
    for i in range(inline_count, 3):
        fmt[f"s{i+1}"] = "（无额外段落）"

    user_prompt = _IMAGE_PROMPT_USER.format(**fmt)

    writer = AIWriter()
    raw = writer._call_ai(
        user_prompt,
        system_prompt=_IMAGE_PROMPT_SYSTEM,
        max_tokens=1000,
        temperature=0.7,
    )

    return _parse_llm_image_prompts(raw, count)


def _parse_llm_image_prompts(raw: str, count: int = 2) -> dict:
    """解析 LLM 输出为 {'cover': str|None, 'inline': [str,...]}。"""
    result = {"cover": None, "inline": []}
    if not raw:
        return result

    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.upper().startswith("COVER:"):
            result["cover"] = line.split(":", 1)[1].strip()[:500]
        elif line.upper().startswith("INLINE_"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                p = parts[1].strip()[:500]
                if p:
                    result["inline"].append(p)

    return result


def _build_cover_prompt(title: str, context: str = "") -> str:
    """为文章标题构建封面图 prompt（中文，适配 Agnes/ERNIE 模型）。（LLM 失败时的兜底模板）"""
    base = (f"真实新闻摄影风格，纪录片质感，军事主题：{title}。"
            f"专业摄影灯光，高细节，锐利对焦，自然色彩。"
            f"无文字，无水印，无Logo，无签名")
    return base[:300]  # 防止 prompt 过长（中文上限 300 字）


def _build_inline_prompts(title: str, content: str, count: int = 2) -> list:
    """从文章正文提取关键词，构建内文配图 prompt 列表（中文，Agnes/ERNIE 优化）。"""
    # 简单策略：取正文前 300 字 + 后 200 字作为上下文
    body = content[:300] + (content[-200:] if len(content) > 400 else "")
    keywords = title[:60]
    if len(body) > 50:
        keywords = body[:80].replace("\n", " ")

    prompts = []
    themes = [
        ("军事战略俯瞰，卫星地图风格，地缘政治可视化，标注真实地理位置", "东亚地区"),
        ("军事演习场景，真实战地摄影，部队与装备编队，阅兵场实拍", "军事装备"),
        ("海军舰队海上编队，真实海洋摄影，军舰全景，壮观日落光线", "海军"),
    ]
    for i in range(min(count, len(themes))):
        p = (f"真实新闻摄影风格：{themes[i][0]}。"
             f"文章主题：{keywords[:80]}。"
             f"高细节，锐利对焦，自然光线，无文字，无水印。"
             f"单张完整照片，无分割构图，无多图拼接")
        prompts.append(p[:300])

    return prompts


# ============================================================
# 阶段4：配图生成（Agnes Image 2.0 Flash）
# ============================================================

# 内文配图数量：每篇文章至少 3 张
INLINE_IMAGE_COUNT = 3


def step_images(state: PipelineState) -> bool:
    """使用 Agnes Image 2.0 Flash API 生成封面和内文配图。
    与 Pollinations 相比：文件大小提升 25–30 倍（~1.5 MB vs ~50 KB），
    中文 prompt 理解更好（底层 ERNIE 中文模型），当前 $0/张。
    """
    import sys as _sys

    # 未启用配图
    if not state.with_images:
        _sys.stderr.write("[images] 配图未启用，跳过\n"); _sys.stderr.flush()
        add_log("跳过阶段4: 配图生成（未启用）", "info")
        set_stage("配图", "done")
        state.mark_done("generate_images")
        state.outputs["images_injected"] = False
        log_sink.set_progress(_PROGRESS_MAP["images_skipped"])
        return True

    # 检查 Agnes API Key
    agnes_cfg = _get_agnes_config()
    if not agnes_cfg["api_key"]:
        _sys.stderr.write("[images] AGNES_API_KEY 未配置，跳过配图\n"); _sys.stderr.flush()
        add_log("跳过阶段4: AGNES_API_KEY 未配置（请在 .env 或配置面板中设置）", "warning")
        set_stage("配图", "done")
        state.mark_done("generate_images")
        state.outputs["images_injected"] = False
        log_sink.set_progress(_PROGRESS_MAP["images_skipped"])
        return True

    _sys.stderr.write("[images] step_images 开始（Agnes Image 2.0 Flash）\n"); _sys.stderr.flush()
    set_stage("配图", "running")
    add_log("阶段4/5: AI 配图生成（Agnes Image 2.0 Flash）", "stage")

    title = state.outputs.get("generated_title", "")
    content = state.outputs.get("generated_content", "")
    if not content:
        _sys.stderr.write("[images] 无文章内容\n"); _sys.stderr.flush()
        add_log("无文章内容，跳过配图生成", "warning")
        set_stage("配图", "done")
        state.mark_done("generate_images")
        state.outputs["images_injected"] = False
        return True

    if not title and content:
        first_line = content.split("\n")[0].strip()
        if len(first_line) < 80:
            title = first_line

    images_dir = state.run_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    log_sink.set_progress(_PROGRESS_MAP["images_start"])

    cover_path = None
    inline_paths = []
    inline_prompts_used = []
    images_injected = False

    try:
        # ── 1. 生成配图 Prompt（优先 LLM，失败 fallback 硬编码）──
        llm_cover = None
        llm_inline = []
        try:
            _prompts = _generate_image_prompts_via_llm(title, content, count=INLINE_IMAGE_COUNT)
            llm_cover = _prompts.get("cover")
            llm_inline = _prompts.get("inline") or []
            add_log("配图 Prompt 由 DeepSeek LLM 生成（中文/Agnes 优化）", "success")
        except Exception as _e:
            _sys.stderr.write(f"[images] LLM prompt 生成失败，使用 fallback: {_e}\n"); _sys.stderr.flush()
            add_log("LLM 配图 Prompt 生成失败，使用内置模板兜底", "warning")

        cover_prompt = llm_cover or _build_cover_prompt(title, content[:200])
        add_log(f"封面 prompt: {cover_prompt[:80]}...", "info")
        cover_file = images_dir / "cover.png"
        _sys.stderr.write("[images] 生成封面图（Agnes）...\n"); _sys.stderr.flush()

        cover_path = _generate_agnes_image(
            cover_prompt, cover_file, width=1024, height=1024, timeout=180
        )

        if cover_path:
            add_log(f"封面图: {Path(cover_path).name}（Agnes）", "success")
            state.outputs["cover_image"] = cover_path
        else:
            add_log("封面图生成失败（Agnes 无响应或超时）", "warning")

        log_sink.set_progress(_PROGRESS_MAP["images_cover_done"])

        # ── 2. 生成内文配图 ──
        inline_prompts = llm_inline if llm_inline else _build_inline_prompts(title, content, count=INLINE_IMAGE_COUNT)
        add_log(f"计划生成 {len(inline_prompts)} 张内文配图", "info")

        for idx, iprompt in enumerate(inline_prompts):
            _sys.stderr.write(f"[images] 生成内文图 {idx+1}/{len(inline_prompts)}（Agnes）...\n"); _sys.stderr.flush()
            inline_file = images_dir / f"inline_{idx + 1}.png"
            result = _generate_agnes_image(
                iprompt, inline_file, width=1024, height=1024, timeout=180
            )
            if result:
                inline_paths.append(result)
                inline_prompts_used.append(iprompt)
                add_log(f"内文配图 {idx+1}: {Path(result).name}（Agnes）", "success")
            else:
                add_log(f"内文配图 {idx+1} 生成失败", "warning")

        log_sink.set_progress(_PROGRESS_MAP["images_all_done"])

        # ── 3. 汇总结果 ──
        success_count = len(inline_paths)
        add_log(f"配图汇总: 封面{'✅' if cover_path else '❌'} | 内文 {success_count}/{len(inline_prompts)}",
                "success" if (cover_path or success_count > 0) else "warning")

        state.outputs["inline_images"] = inline_paths
        state.outputs["image_gen_prompts"] = {
            "cover": cover_prompt,
            "inline": inline_prompts_used,
        }
        state.outputs["image_provider"] = "agnes"

        # ── 4. 阶段4 只负责「生成/下载图片」，不注入文章、不生成完整稿件。
        #    图文组装由阶段5 step_assemble 统一完成，避免阶段4还没结束就产出
        #    「完整稿件_配图版.md」的时序混乱。
        images_generated = bool(cover_path or inline_paths)

    except ImportError as e:
        _sys.stderr.write(f"[images] ImportError: {e}\n"); _sys.stderr.flush()
        add_log(f"图片生成依赖缺失: {e}。需要 requests 库（pip install requests）", "warning")
        state.outputs["images_injected"] = False
    except Exception as e:
        _sys.stderr.write(f"[images] Exception: {e}\n"); _sys.stderr.flush()
        traceback.print_exc()
        add_log(f"配图生成异常: {e}（已跳过配图，不影响后续阶段）", "warning")
        state.outputs["images_injected"] = False

    # 始终标记阶段完成（不阻断流水线），images_injected 在阶段5 组装后刷新
    state.outputs["images_injected"] = images_generated
    set_stage("配图", "done")
    state.mark_done("generate_images")
    log_sink.set_progress(_PROGRESS_MAP["assembly_start"])

    if not images_generated:
        add_log("⚠️ 本篇文章无配图，最终稿件将为纯文本版", "warning")

    _sys.stderr.write(f"[images] 完成, images_generated={images_generated}\n"); _sys.stderr.flush()
    return True


def _assemble_article_with_images(state, cover_path: Optional[str], inline_paths: list) -> bool:
    """阶段5 专用：将图片引用注入原始文章，生成「完整稿件_配图版.md」。

    设计约束：
    - 只在阶段5（step_assemble）调用，阶段4只产出图片文件；
    - 图片标记保持极简：无 "AI 生成封面配图"、无 "📸 配图X" 等说明文字，
      直接采用标准 Markdown 图片语法，确保复制到头条/公众号编辑器后干净；
    - 无图时 assembled_file 回退指向原始文章，保证下游始终有最终文件。

    返回 images_injected 布尔值。
    """
    generated_file = state.outputs.get("generated_file", "")
    if not generated_file:
        return False

    article_path = Path(generated_file)
    if not article_path.exists():
        return False

    content = article_path.read_text(encoding="utf-8")
    has_any_image = bool(cover_path or inline_paths)

    if not has_any_image:
        # 无图片：不生成配图版，assembled_file 指向原始文件
        state.outputs["assembled_file"] = str(article_path)
        return False

    # ── 注入内文配图（极简，无 "📸 配图X" 标签）──
    if inline_paths:
        # 过滤掉不存在的图片
        verified_inline = [p for p in inline_paths if Path(p).exists()]
        skipped = len(inline_paths) - len(verified_inline)
        if skipped > 0:
            import sys as _sys
            _sys.stderr.write(f"[assemble] {skipped}张内文图文件缺失，已跳过\n"); _sys.stderr.flush()
            add_log(f"{skipped}张内文配图文件缺失，已跳过注入", "warning")

        if not verified_inline:
            add_log("所有内文配图文件缺失，仅保留封面", "warning")

        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        body_start = 0
        for i, p in enumerate(paragraphs):
            if p.startswith("# ") or p.startswith("![") or p.startswith("> *"):
                body_start = i + 1
            else:
                break

        body = paragraphs[body_start:]
        if body and len(verified_inline) > 0:
            step_size = max(1, len(body) // (len(verified_inline) + 1))
            for img_idx, img_path in enumerate(verified_inline):
                img_rel = f"images/{Path(img_path).name}"
                pos = body_start + step_size * (img_idx + 1)
                if pos < len(paragraphs):
                    img_md = f"\n\n![内文配图]({img_rel})\n"
                    paragraphs[pos] = img_md.strip() + "\n\n" + paragraphs[pos]
            content = "\n\n".join(paragraphs)

    # ── 注入封面图（极简，置于开头钩子段落后）──
    if cover_path:
        cover_file = Path(cover_path)
        if cover_file.exists():
            cover_rel = f"images/{cover_file.name}"
            # 找到第一个自然段落结束位置（跳过标题 # 行）
            _lines = content.split("\n")
            _hook_end = 0
            _found_body = False
            for _i, _ln in enumerate(_lines):
                stripped = _ln.strip()
                if not _found_body:
                    if stripped and not stripped.startswith("# ") and not stripped.startswith("!["):
                        _found_body = True
                        _hook_end = _i
                    continue
                # 在正文中找段落结束（空行或 EOF）
                if not stripped:
                    _hook_end = _i
                    break
                _hook_end = _i
            # 在钩子段落之后、后续内容之前插入封面图
            # （_hook_end=0 且 _found_body=False：无钩子段落时封面置于标题后）
            _before = "\n".join(_lines[:_hook_end + 1])
            _after = "\n".join(_lines[_hook_end + 1:])
            content = _before.rstrip() + f"\n\n![封面]({cover_rel})\n\n" + _after.lstrip()
        else:
            import sys as _sys
            _sys.stderr.write(f"[assemble] 封面图文件缺失，跳过注入: {cover_file.name}\n"); _sys.stderr.flush()
            add_log(f"封面图文件缺失: {cover_file.name}，跳过注入", "warning")

    # ── 规整：剥离流水线元数据（# 标题保留，发布阶段 publisher_service 自行去重）──
    # (a) 剥离末尾 "---" 分隔 + "*第N轮 | 评分…*" 元数据块
    content = re.sub(r"\n*---\n*\*[^*\n]*\*", "", content)
    # (b) 剥离 LLM 在 S3 自发产生的整行话题标签（形如 "#无人机战争 #AI改变战场"，# 后无空格）
    content = re.sub(r"(?m)^\s*#\S+(?:\s+#\S+)*\s*$", "", content)
    # (c) 清理因删除标签行产生的连续空行（≥3 换行压成 2 个）
    content = re.sub(r"\n{3,}", "\n\n", content)

    # ── 写回：只在阶段5 生成「完整稿件_配图版.md」──
    assembled_file = state.run_dir / "完整稿件_配图版.md"
    assembled_file.write_text(content, encoding="utf-8")
    state.outputs["generated_content"] = content
    state.outputs["assembled_file"] = str(assembled_file)
    return True


# ============================================================
# 阶段5：图文组装（水印裁剪）
# ============================================================
def step_assemble(state: PipelineState) -> bool:
    """最终组装：将阶段4 生成的图片注入原始文章，生成完整稿件_配图版.md。"""
    set_stage("组装", "running")
    add_log("阶段5/5: 图文最终组装", "stage")

    log_sink.set_progress(_PROGRESS_MAP["assembly_done"])

    # ── 阶段5 真正执行图文组装：阶段4 只出图，不提前生成配图版 ──
    cover_image = state.outputs.get("cover_image", "")
    inline_images = state.outputs.get("inline_images", [])
    images_injected = _assemble_article_with_images(state, cover_image, inline_images)
    state.outputs["images_injected"] = images_injected

    # 确保有最终文件
    final_file = state.outputs.get("assembled_file") or state.outputs.get("generated_file")
    if not final_file or not Path(final_file).exists():
        add_log("没有找到最终稿件文件", "warning")
        set_stage("组装", "done")
        state.mark_done("assemble")
        return True

    add_log(f"最终稿件: {Path(final_file).name}", "success")

    # 文件清单
    file_list = []
    for f in state.run_dir.glob("**/*"):
        if f.is_file() and ".temp" not in str(f):
            size_kb = f.stat().st_size / 1024
            file_list.append({"name": f.name, "path": str(f), "size_kb": round(size_kb, 1)})

    state.outputs["file_list"] = file_list
    add_log(f"输出目录: {state.run_dir}", "info")
    add_log(f"共 {len(file_list)} 个文件", "info")

    set_stage("组装", "done")
    state.mark_done("assemble")
    log_sink.set_progress(_PROGRESS_MAP["pipeline_complete"])
    return True


# ── Phase 3 编排层包装：注入 Streamlit 钩子 ──
def _run_research_and_write(state):
    """包装：将 Streamlit 日志/阶段/进度钩子注入研究-写作编排层。

    实际逻辑已抽至 backend/write_stage.py 的 research_and_write。
    """
    _hooks = _PipelineHooks(
        log_fn=add_log,
        stage_fn=set_stage,
        progress_fn=lambda p: setattr(st.session_state, "progress_pct", p),
    )
    return _research_and_write_impl(state, _hooks)


# ============================================================
# 流水线总调度
# ============================================================
def _run_stages(stages: list, state, stop_at: str = "全部") -> bool:
    """按序执行各阶段，支持 stop_at 指定执行范围。

    - stop_at == "全部"：分步模式，每阶段完成后 await 用户点击「下一步」；
    - stop_at == 具体阶段 id：连续执行，到达该阶段完成即停（不 await、不跑后续）。

    返回是否全部阶段均完成。
    """
    import sys as _sys

    step_mode = (stop_at == "全部")

    for stage_id, stage_name, stage_fn in stages:
        if state.is_done(stage_id):
            set_stage(stage_name, "done")
            add_log(f"阶段 {stage_name}: 已完成，跳过", "info")
            continue

        try:
            _sys.stderr.write(f"[pipeline] 开始阶段: {stage_name}\n"); _sys.stderr.flush()
            success = stage_fn(state)
            state.save()
            _sys.stderr.write(f"[pipeline] 阶段 {stage_name} 完成, success={success}\n"); _sys.stderr.flush()

            if not success:
                add_log(f"阶段 {stage_name} 执行失败，流水线中止", "error")
                break

            # 指定范围：到达目标阶段即停（连续执行，不等待下一步）
            if not step_mode and stage_id == stop_at:
                add_log(f"🎯 已执行至目标阶段 [{stage_name}]，按设定范围停止流水线", "success")
                break

            # 分步模式：阶段完成后暂停，等待用户点击「下一步」
            if step_mode:
                remaining = any(not state.is_done(s[0]) for s in stages)
                if remaining:
                    add_log(f"⏸️ 阶段 [{stage_name}] 完成，等待用户点击 [下一步] 继续…", "info")
                    log_sink.UI_SYNC.update(awaiting_next=True)
                    _STAGE_EVENT.wait()  # 阻塞至用户点击
                    log_sink.UI_SYNC.update(awaiting_next=False)
                    _STAGE_EVENT.clear()

        except Exception as e:
            add_log(f"阶段 {stage_name} 异常: {e}", "error")
            traceback.print_exc()
            set_stage(stage_name, "failed")
            state.save()
            break

    return all(state.is_done(s[0]) for s in stages)


def execute_pipeline(url: str, style: str, enable_humanize: bool,
                     with_images: bool, content_type: str, stop_at: str = "全部"):
    """按序执行各阶段（同步阻塞执行）。

    stop_at 控制执行范围：
    - "全部" → 分步模式，每阶段完成后等待用户点击「下一步」；
    - 具体阶段 id → 连续执行，到达该阶段完成后即停（不等待「下一步」，不跑后续）。
    """
    import sys as _sys

    t_start = time.time()
    error: Optional[str] = None

    try:
        # 始终从零开始新建运行状态（不复用历史记录）
        state = PipelineState(
            input_url=url, content_type=content_type,
            content_style=style, enable_humanize=enable_humanize,
            with_images=with_images,
        )

        log_sink.set_pipeline_started(state.run_id)
        add_log(f"运行 ID: {state.run_id}", "info")
        add_log(f"输出目录: {state.run_dir}", "info")

        # 阶段列表（write + humanize 已合并为研究-写作循环）
        stages = [
            ("download", "下载", step_download),
            ("transcribe", "转录", step_transcribe),
            ("write", "研究写作", _run_research_and_write),
            ("generate_images", "配图", step_images),
            ("assemble", "组装", step_assemble),
        ]

        # 按执行范围（stop_at）逐阶段运行
        _run_stages(stages, state, stop_at)

        # 完成
        result = _build_result(state)
        elapsed = round(time.time() - t_start, 1)
        log_sink.set_result(result, elapsed)
        if all(state.is_done(s[0]) for s in stages):
            add_log(f"全部完成！耗时 {elapsed:.0f} 秒", "success")
        else:
            add_log(f"流水线未完全完成。可重新运行以断点续跑", "warning")
        _sys.stderr.write(f"[pipeline] 流水线结束, all_done={all(state.is_done(s[0]) for s in stages)}\n"); _sys.stderr.flush()

    except Exception as e:
        # 业务级异常兜底：单个阶段异常已在 execute_pipeline 内部 try/except 捕获并 break；
        # 此处仅兜底未预料的顶层异常（分层：阶段内异常 → 顶层致命异常）。
        _sys.stderr.write(f"[pipeline] 错误: {e}\n"); _sys.stderr.flush()
        add_log(f"流水线发生错误: {e}", "error")
        traceback.print_exc()
        error = str(e)
    finally:
        log_sink.set_pipeline_done(error)



def _build_result(state: PipelineState) -> dict:
    """从 PipelineState 构建结果数据。"""
    final_file = state.outputs.get("assembled_file") or state.outputs.get("generated_file")
    content = ""
    if final_file and Path(final_file).exists():
        content = Path(final_file).read_text(encoding="utf-8")

    cover_image = state.outputs.get("cover_image", "")
    inline_images = state.outputs.get("inline_images", [])
    file_list = state.outputs.get("file_list", [])
    eval_records = state.outputs.get("eval_records", [])
    research_notes = state.outputs.get("research_notes", [])

    return {
        "run_id": state.run_id,
        "run_dir": str(state.run_dir),
        "title": state.outputs.get("generated_title", ""),
        "content": content,
        "char_count": state.outputs.get("char_count", 0),
        "cover_image": cover_image,
        "inline_images": inline_images,
        "file_list": file_list,
        "eval_records": eval_records,
        "best_iteration": state.outputs.get("best_iteration", 0),
        "best_score": state.outputs.get("best_score", 0),
        "quality_warning": state.outputs.get("quality_warning", False),
        "research_notes": research_notes,
    }





# ============================================================
# UI 侧边栏
# ============================================================
def render_sidebar():
    """渲染侧边栏：内容配置 + API 密钥 + 执行范围 + 快捷参考（统一入口）。"""
    with st.sidebar:
        # ── 侧栏标题 ──
        st.markdown(
            '<div style="display:flex;align-items:center;gap:8px;padding:4px 0 12px;">'
            '<span style="font-size:20px;">⚙️</span>'
            '<span style="font-weight:600;font-size:16px;font-family:var(--font-sans);">控制面板</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        # ── 内容配置 ──
        st.caption("📝 内容配置")
        style = st.selectbox(
            "内容风格",
            options=[
                ("fenghuo_qingbao", "🗡️ 烽火情报（专业锐评型）"),
                ("baoming_shuo", "🔥 包明说（反差悬念型）"),
                ("jin_shuo", "📚 晋说（乡愁叙事型）"),
                ("global_archive", "🏛️ 全球档案馆（馆长悬疑型）"),
                ("story_narrative", "📖 听风的蚕（评书故事型）"),
            ],
            format_func=lambda x: x[1],
            key="sidebar_style",
        )

        content_type = st.radio(
            "内容类型",
            options=[("toutie", "微头条"), ("article", "文章")],
            format_func=lambda x: x[1],
            horizontal=True,
            index=1,                      # 默认选中「文章」
            key="sidebar_content_type",
        )

        humanize = st.toggle("✍️ 人工化改写", value=True, help="去除 AI 味，输出更像真人手笔")
        with_images = st.toggle("🖼️ AI 配图生成", value=True,
                                help="AI 生成封面图 + 内文配图（需配置图片 API Key）")
        use_browser_cookies = st.toggle("🍪 浏览器 Cookie", value=True,
                                        help="允许 yt-dlp 从 Chrome 浏览器提取 Cookie 用于抖音下载（仅下载阶段生效）")

        # ── 界面 ──
        st.caption("🎨 界面")
        light_mode = st.toggle("☀️ 浅色主题", value=st.session_state.get("theme", "dark") == "light",
                               help="切换浅色 / 暗色界面")
        st.session_state.theme = "light" if light_mode else "dark"

        st.divider()

        # ── 执行范围 ──
        st.caption("🎯 执行范围")
        stop_at = st.selectbox(
            "执行到阶段",
            options=[
                ("assemble", "组装（输出完整稿件）"),       # 默认：全流程连续执行
                ("全部", "全部阶段（分步执行）"),
                ("download", "下载"),
                ("transcribe", "转录"),
                ("write", "研究写作"),
                ("generate_images", "配图"),
            ],
            format_func=lambda x: x[1],
            key="sidebar_stop_at",
            help="默认全流程连续执行到底；选「全部」为分步执行，选具体阶段则连续执行到该阶段即停",
        )

        st.divider()

        # ── API 密钥 ──
        st.caption("🔑 API 密钥")
        api_key = st.text_input(
            "DeepSeek API Key",
            value=os.getenv("AI_API_KEY", ""),
            type="password",
            placeholder="sk-...",
        )
        api_base = st.text_input(
            "API Base URL",
            value=os.getenv("AI_BASE_URL", "https://api.deepseek.com/v1"),
        )
        api_model = st.text_input(
            "Model",
            value=os.getenv("AI_MODEL", "deepseek-chat"),
        )

        with st.expander("🖼️ 配图 API（Agnes）", expanded=False):
            agnes_key = st.text_input(
                "Agnes API Key",
                value=os.getenv("AGNES_API_KEY", ""),
                type="password",
                placeholder="ak-...",
                help="https://apihub.agnes-ai.com 获取",
            )
            agnes_base = st.text_input(
                "Agnes API Base",
                value=os.getenv("AGNES_API_BASE", "https://apihub.agnes-ai.com/v1"),
            )
            agnes_model = st.text_input(
                "Agnes Model",
                value=os.getenv("AGNES_IMAGE_MODEL", "agnes-image-2.0-flash"),
            )

        if st.button("💾 保存到 .env", use_container_width=True):
            _save_env(api_key, api_base, api_model, agnes_key, agnes_base, agnes_model)
            st.success("配置已保存！")

        st.divider()

        # ── 快捷参考（可折叠） ──
        with st.expander("📖 下载说明 & 快捷参考", expanded=False):
            st.caption("抖音：Playwright 真实浏览器自动拦截视频流。")
            st.caption("其他平台：yt-dlp 直连下载。")
            st.caption("依赖：Node.js + Playwright Chromium（首次自动安装）")
            st.markdown("---")
            st.caption("**各风格参考（旧系统遗留，仅作参考）**")
            st.markdown(
                '<div style="overflow-x:auto;font-size:11px;">'
                '<table style="width:100%;border-collapse:collapse;">'
                '<tr style="border-bottom:1px solid var(--border-soft);">'
                '<td>评书故事型</td><td style="text-align:right;">800-1200</td><td>河南方言</td>'
                '</tr><tr style="border-bottom:1px solid var(--border-soft);">'
                '<td>军事深度</td><td style="text-align:right;">800-1200</td><td>七层递进法</td>'
                '</tr><tr style="border-bottom:1px solid var(--border-soft);">'
                '<td>冷静克制冷</td><td style="text-align:right;">800-1200</td><td>事实为主</td>'
                '</tr><tr style="border-bottom:1px solid var(--border-soft);">'
                '<td>快讯速报型</td><td style="text-align:right;">300-500</td><td>3段讲清</td>'
                '</tr><tr>'
                '<td>互动讨论型</td><td style="text-align:right;">500-800</td><td>开放式提问</td>'
                '</tr></table></div>',
                unsafe_allow_html=True,
            )

        return style[0], content_type[0], humanize, with_images, stop_at[0], use_browser_cookies



def _save_env(api_key: str, api_base: str, api_model: str,
               agnes_key: str = "", agnes_base: str = "", agnes_model: str = ""):
    """保存配置到 .env 文件。"""
    env_path = ENGINE_ROOT / ".env"
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").split("\n")
    else:
        lines = []

    updated = {
        "AI_API_KEY": api_key, "AI_BASE_URL": api_base, "AI_MODEL": api_model,
        "AGNES_API_KEY": agnes_key, "AGNES_API_BASE": agnes_base,
        "AGNES_IMAGE_MODEL": agnes_model,
    }
    new_lines = []
    found = set()
    for line in lines:
        stripped = line.strip()
        replaced = False
        for k, v in updated.items():
            if stripped.startswith(f"{k}=") and k not in found:
                new_lines.append(f"{k}={v}")
                found.add(k)
                replaced = True
                break
        if not replaced:
            new_lines.append(line)

    for k, v in updated.items():
        if k not in found:
            new_lines.append(f"{k}={v}")

    env_path.write_text("\n".join(new_lines), encoding="utf-8")
    st.info("⚠️ API Key 已明文保存到 .env 文件。仅本地使用，请勿分享该文件。", icon="🔒")
    # 更新环境变量
    for k, v in updated.items():
        os.environ[k] = v


# ============================================================
# UI 主区域
# ============================================================
def render_main():
    """渲染主操作区。"""
    st.markdown('<div class="main-header">🚀 AIToutiao 引擎模式</div>',
                unsafe_allow_html=True)

    # 状态指示灯
    is_running = st.session_state.is_running
    has_result = st.session_state.result_data is not None

    status_state = "running" if is_running else ("done" if has_result else "ready")
    status_text = "● 运行中" if is_running else ("● 已完成" if has_result else "● 就绪")
    st.markdown(
        f'<div style="text-align:center;"><span class="status-pill {html.escape(status_state)}">{html.escape(status_text)}</span></div>',
        unsafe_allow_html=True,
    )

    # URL 输入行
    col1, col2, col3 = st.columns([5, 1.5, 1])
    with col1:
        url = st.text_input(
            "视频链接（抖音 / YouTube / B站 等）",
            key="url_input",
            placeholder="直接粘贴抖音复制的分享内容即可，自动提取链接",
            label_visibility="collapsed",
        )
    # 空状态引导（带视觉容器）
    if not url or not url.strip():
        st.markdown(
            '<div class="empty-state">'
            '<div style="font-size:40px;margin-bottom:12px;opacity:0.6;">🔗</div>'
            '<p style="margin:0 0 6px;font-size:14px;font-weight:500;color:var(--text);">在此粘贴视频链接或分享内容即可开始</p>'
            '<p style="margin:0;font-size:12px;color:var(--text-muted);">支持 抖音 / YouTube / B站 等平台</p>'
            '<p style="margin:4px 0 0;font-size:12px;color:var(--text-muted);">'
            '示例：<code style="background:var(--bg-elevated);padding:2px 6px;border-radius:4px;font-size:11px;">https://v.douyin.com/xxxx/</code> 或直接粘贴整段抖音分享文案</p>'
            '</div>',
            unsafe_allow_html=True,
        )
    # 实时 URL 检测提示（纯 UI 预览，不阻断流水线）
    if url and url.strip():
        raw = url.strip()
        detected = extract_douyin_url(raw)
        st.session_state.processed_url = detected or ""  # 单向数据通道：提取 → 执行
        if detected and detected != raw:
            st.caption(f"🔗 检测到链接：`{detected}`")
        elif detected is None:
            st.caption("⚠️ 未检测到有效链接，请粘贴视频分享内容或链接")

    with col2:
        generate_btn = st.button("▶ 一键生成", use_container_width=True,
                                  type="primary", disabled=is_running)
    with col3:
        clear_btn = st.button("🗑 清空", use_container_width=True, disabled=is_running)

    if clear_btn:
        log_sink.reset()
        for k in ("logs", "result_data", "pipeline_state", "run_id", "processed_url",
                  "pipeline_error", "pipeline_done",
                  "publish_result", "publish_running", "login_verified"):
            st.session_state[k] = _DEFAULTS[k]
        for s_name in st.session_state.stage_status:
            st.session_state.stage_status[s_name] = "pending"
        st.rerun()


    return url, generate_btn


# ============================================================
# UI 进度条 + 阶段指示灯
# ============================================================
def render_progress():
    """渲染阶段进度条和阶段流程指示灯（灯 + 连接线）。"""
    stages_order = ["下载", "转录", "研究写作", "配图", "组装"]

    # 阶段状态 → 文字标签（色盲友好：除颜色外提供文字状态）
    status_label = {"done": "完成", "running": "进行中", "failed": "失败", "pending": "待开始"}
    # 色盲友好增强：在状态点内叠加形状图标，与颜色 + 文字形成三重冗余
    # ✓ 完成 / ▶ 进行中 / ✕ 失败 / ○ 待开始 —— 仅凭形状即可区分四种状态
    status_icon = {"done": "✓", "running": "▶", "failed": "✕", "pending": "○"}

    # 阶段流程：灯 + 连接线（替代堆叠的 5 列指示灯，信息更对齐）
    steps_html = ['<div class="stage-flow">']
    for name in stages_order:
        status = st.session_state.stage_status.get(name, "pending")
        s_text = status_label.get(status, "待开始")
        steps_html.append(
            f'<div class="stage-step {status}">'
            f'<span class="dot">{status_icon.get(status, "○")}</span>'
            f'<div class="label">{name}</div>'
            f'<div class="state">{s_text}</div>'
            f'</div>'
        )
    steps_html.append('</div>')
    st.markdown("\n".join(steps_html), unsafe_allow_html=True)

    # 进度条 + 精确百分比（交互反馈增强）
    st.progress(st.session_state.progress_pct)
    st.caption(f"🔢 进度 {int(st.session_state.progress_pct * 100)}%")

    # 当前阶段描述
    if st.session_state.is_running:
        current = st.session_state.current_stage
        if current:
            st.caption(f"⏳ 正在执行：{current}")
    elif st.session_state.progress_pct >= 1.0:
        elapsed = st.session_state.get("elapsed_seconds", 0)
        st.caption(f"✅ 执行完成 | 耗时 {elapsed:.0f} 秒")


# ============================================================
# UI 运行日志
# ============================================================
def render_logs():
    """渲染运行日志区域。"""
    logs = st.session_state.logs
    if not logs:
        return

    # 构建日志 HTML
    html_lines = ['<div class="log-container">']
    for entry in logs:
        emoji = _emoji_for_level(entry["level"])
        html_lines.append(
            f'<div class="log-line {entry["level"]}">'
            f'[{entry["time"]}] {emoji} {html.escape(entry["msg"])}</div>'
        )
    html_lines.append("</div>")

    st.markdown("\n".join(html_lines), unsafe_allow_html=True)
    if len(logs) >= 500:
        st.caption("💡 界面仅显示最近 500 行，完整日志见 `log/` 目录")


# ============================================================
# UI 发布
# ============================================================
def render_publish():
    """渲染发布 Tab — 将流水线产出发布到今日头条。

    依赖 super-publisher 方案：Markdown 图片转为占位符 → 剪贴板 + Ctrl+V 粘贴，
    解决头条编辑器图片不渲染问题。正文不含 # 标题行（S5 已剥离）。
    """
    result = st.session_state.result_data

    if not result:
        st.markdown(
            '<div class="empty-state" style="padding:64px 16px;">'
            '<div style="font-size:48px;margin-bottom:16px;opacity:0.5;">🚀</div>'
            '<p style="margin:0 0 8px;font-size:16px;font-weight:600;color:var(--text);">暂无成果可发布</p>'
            '<p style="margin:0 0 4px;font-size:13px;color:var(--text-secondary);">'
            '在工作台生成文章后，</p>'
            '<p style="margin:0;font-size:13px;color:var(--text-secondary);">可在此一键发布到今日头条</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    title = result.get("title", "")
    content = result.get("content", "")
    run_dir = result.get("run_dir", "")
    cover_image = result.get("cover_image", "")

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🚀 发布到今日头条</div>', unsafe_allow_html=True)

    # ── 标题 + 封面预览 ──
    col1, col2 = st.columns([3, 1])
    with col1:
        st.text_input("文章标题", value=title, key="publish_title_preview",
                       disabled=True, label_visibility="collapsed",
                       placeholder="标题（由流水线 S3 生成）")
    with col2:
        if cover_image and Path(cover_image).exists():
            st.image(str(cover_image), caption="封面预览", use_container_width=True)

    # ── 内容预览 ──
    char_count = result.get("char_count", len(content))
    with st.expander(f"📄 内容预览（{char_count} 字符）", expanded=False):
        st.caption("正文不含标题行（已由 S5 阶段剥离，标题由 publish 阶段独立填写）")
        st.text(content[:800] + ("..." if len(content) > 800 else ""))

    # ── 发布选项 ──
    col1, col2 = st.columns(2)
    with col1:
        headless = st.checkbox(
            "无头模式", value=False, key="publish_headless",
            help="后台运行浏览器（不显示窗口），调试时建议关闭",
        )
    with col2:
        inline_count = len(result.get("inline_images", []))
        img_info = f"{inline_count + 1} 张图片" if inline_count else "仅封面"
        st.metric("配图", img_info)
        st.caption(f"Run: `{result.get('run_id', '')[:16]}...`")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── 登录状态检查 ──
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🔐 登录状态</div>', unsafe_allow_html=True)

    if st.button("🔍 验证登录状态", key="btn_check_login"):
        with st.spinner("正在验证登录..."):
            try:
                publish_article_fn, check_login_fn, launch_login_fn = _get_publisher()
                status = check_login_fn()
                st.session_state.login_verified = status.get("authenticated", False)
            except ImportError as e:
                st.error(f"缺少发布依赖: {e}。请 `pip install patchright`")
                st.session_state.login_verified = False
            except Exception as e:
                st.error(f"验证失败: {e}")
                st.session_state.login_verified = False

    login_ok = st.session_state.get("login_verified", None)

    if login_ok is True:
        st.success("✅ 已登录头条后台，可以发布")
    elif login_ok is False:
        st.warning("⚠️ 未登录或登录已过期")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔐 打开登录页面", use_container_width=True):
                try:
                    _, _, launch_login_fn = _get_publisher()
                    success = launch_login_fn(headless=False, timeout_minutes=5)
                    if success:
                        st.session_state.login_verified = True
                        st.rerun()
                    else:
                        st.error("登录失败或超时")
                except Exception as e:
                    st.error(f"登录失败: {e}")
    else:
        st.info("点击上方按钮验证登录状态")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── 发布按钮 ──
    st.markdown("---")
    publish_disabled = (
        st.session_state.get("publish_running", False)
        or not login_ok
        or not title
        or not content
    )
    hint = ""
    if not login_ok:
        hint = "（请先验证登录状态）"
    elif not content:
        hint = "（暂无可发布内容）"

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            f"📝 填写到头条编辑器 {hint}",
            type="primary",
            use_container_width=True,
            disabled=publish_disabled,
            key="btn_publish",
        ):
            st.session_state.publish_running = True
            st.session_state.publish_result = None

            with st.spinner("⏳ 启动浏览器，正在填写内容…（请勿关闭页面）"):
                try:
                    publish_article_fn, _, _ = _get_publisher()
                    pub_result = publish_article_fn(
                        title=title,
                        content=content,
                        cover_path=str(cover_image) if cover_image and Path(cover_image).exists() else None,
                        content_base_dir=run_dir,
                        headless=headless,
                    )
                    st.session_state.publish_result = pub_result
                except Exception as e:
                    st.session_state.publish_result = {"success": False, "message": f"发布异常: {e}"}
                finally:
                    st.session_state.publish_running = False

            st.rerun()

    # ── 发布结果展示 ──
    pub_result = st.session_state.get("publish_result")
    if pub_result:
        if pub_result.get("success"):
            st.success(f"✅ {pub_result.get('message', '发布成功')}")
            st.caption("请前往 [mp.toutiao.com](https://mp.toutiao.com) 查看草稿箱或已发布文章")
        else:
            st.error(f"❌ {pub_result.get('message', '发布失败')}")


# ============================================================
# UI 结果展示
# ============================================================
def render_results():
    """渲染结果展示区（质检整宽 + 封面/统计卡 + 稿件 + 响应式操作）。"""
    result = st.session_state.result_data
    if not result:
        # ── 空状态：引导用户去工作台 ──
        st.markdown(
            '<div class="empty-state" style="padding:64px 16px;">'
            '<div style="font-size:48px;margin-bottom:16px;opacity:0.5;">📊</div>'
            '<p style="margin:0 0 8px;font-size:16px;font-weight:600;color:var(--text);">暂无成果</p>'
            '<p style="margin:0 0 4px;font-size:13px;color:var(--text-secondary);">'
            '在工作台输入视频链接并启动流水线后，</p>'
            '<p style="margin:0;font-size:13px;color:var(--text-secondary);">完成的稿件将在此处展示</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── 质量警告横幅（D5-F：低于阈值不中断但展示警告）──
    if result.get("quality_warning"):
        best_score = result.get("best_score", 0)
        st.warning(
            f"⚠️ **质量警告**：AI 综合评分 {best_score}/100，低于质量阈值。"
            f"建议人工复核内容的事实准确性和表达质量后再发布。"
            f"原始 AI 生成文件 `*_ai_raw.md` 已保存，可查阅完整内容。"
        )

    import pandas as pd

    # ── 1. 成果概览（封面 + 统计 + 操作，卡片化） ──
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📦 成果概览</div>', unsafe_allow_html=True)
    ov_col1, ov_col2 = st.columns([1, 2])
    with ov_col1:
        cover = result.get("cover_image", "")
        if cover and Path(cover).exists():
            st.image(str(cover), caption="封面图（AI 生成）", use_container_width=True)
        inline = result.get("inline_images", [])
        if inline:
            st.markdown("#### 🖼️ 内文配图")
            for img_path in inline:
                if Path(img_path).exists():
                    st.image(str(img_path), use_container_width=True)
    with ov_col2:
        st.markdown("#### 📊 统计")
        st.markdown(
            f'<span class="stat-badge">📝 {result.get("char_count", 0)} 字符</span>'
            f'<span class="stat-badge">📁 {len(result.get("file_list", []))} 个文件</span>'
            f'<span class="stat-badge">🆔 {html.escape(str(result.get("run_id", "")))}</span>',
            unsafe_allow_html=True,
        )
        # 操作按钮（窄屏响应式降级）
        st.markdown("#### ⚡ 操作")
        st.markdown('<div class="my-actions">', unsafe_allow_html=True)
        btn_cols = st.columns(4)
        with btn_cols[0]:
            run_dir = result.get("run_dir", "")
            if run_dir and Path(run_dir).exists():
                if st.button("📂 打开目录", use_container_width=True):
                    os.startfile(run_dir) if sys.platform == "win32" else None
                    st.info(f"目录: {run_dir}")
        with btn_cols[1]:
            content = result.get("content", "")
            if content:
                st.download_button(
                    "📥 下载稿件", data=content,
                    file_name=f"AIToutiao_{result.get('run_id', 'output')}.md",
                    mime="text/markdown", use_container_width=True,
                )
        with btn_cols[2]:
            if content:
                if st.button("📋 复制内容", use_container_width=True):
                    try:
                        import pyperclip
                        pyperclip.copy(content)
                        st.success("已复制到剪贴板！")
                    except ImportError:
                        st.code(content, language="markdown")
                        st.info("请手动复制上方内容（安装 pyperclip 可支持一键复制）")
        with btn_cols[3]:
            raw_file = Path(result.get("run_dir", "")) / f"微头条_{result.get('run_id', '')}_ai_raw.md"
            if raw_file.exists():
                with st.expander("🔍 查看 AI 原始版本"):
                    st.markdown(raw_file.read_text(encoding="utf-8"))
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── 2. 质量评估仪表盘（整宽，dataframe 可横向滚动） ──
    eval_records = result.get("eval_records", [])
    if eval_records:
        best_iter = result.get("best_iteration", 0)
        best_score = result.get("best_score", 0)
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📊 质量评估仪表盘（AI 自评迭代历史）</div>', unsafe_allow_html=True)
        dashboard_cols = st.columns(4)
        with dashboard_cols[0]:
            st.metric("总计迭代", f"{len(eval_records)} 轮")
        with dashboard_cols[1]:
            st.metric("最佳轮次", f"第{best_iter}轮")
        with dashboard_cols[2]:
            st.metric("最高评分", f"{best_score}/100")
        with dashboard_cols[3]:
            pass_count = sum(1 for r in eval_records if r.get("passed"))
            st.metric("通过轮次", f"{pass_count}/{len(eval_records)}")

        rows = []
        for rec in eval_records:
            dims = rec.get("dimensions", {})
            rows.append({
                "轮次": rec.get("iteration", "?"),
                "综合分": rec.get("score", "?"),
                "事实准确": dims.get("事实准确", "?"),
                "信息完整": dims.get("信息完整", "?"),
                "结构清晰": dims.get("结构清晰", "?"),
                "风格一致": dims.get("风格一致", "?"),
                "去AI味": dims.get("去AI味", "?"),
                "状态": "✅" if rec.get("passed") else "❌",
                "反馈摘要": rec.get("feedback", "")[:40],
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True,
                     height=min(360, 40 * (len(rows) + 1)))

        # 搜索溯源
        search_entries = [
            (rec.get("iteration", "?"), q)
            for rec in eval_records
            for q in rec.get("search_queries", [])
        ]
        if search_entries:
            st.markdown("**🔍 搜索关键词溯源**")
            search_lines = [f"- 第{s_it}轮: `{s_query}`" for s_it, s_query in search_entries]
            st.markdown("\n".join(search_lines))
        # 最佳轮次反馈
        best_rec = next((r for r in eval_records if r.get("iteration") == best_iter), None)
        if best_rec and best_rec.get("feedback"):
            st.info(f"💡 最佳轮次反馈: {best_rec['feedback']}")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── 3. 生成的稿件 + 文件清单 ──
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📄 生成的稿件</div>', unsafe_allow_html=True)
    content = result.get("content", "")
    if content:
        with st.container(height=500):
            st.markdown(content)
    file_list = result.get("file_list", [])
    if file_list:
        with st.expander("📋 所有输出文件"):
            for f in file_list:
                st.caption(f"📄 {f['name']} ({f['size_kb']} KB)")
    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# 主入口
# ============================================================
# ── 流水线互斥锁：防止 Streamlit 多次 rerun 导致并发执行 ──
_PIPELINE_LOCK = threading.Lock()
# 分步模式控制器（跨线程安全）
_STAGE_EVENT = threading.Event()


def _new_log_file_path() -> str:
    """生成新的日志文件路径（每轮运行独立）。"""
    _log_dir = ENGINE_ROOT / "log"
    _log_dir.mkdir(parents=True, exist_ok=True)
    _log_filename = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    return str(_log_dir / _log_filename)


def main():

    style, content_type, humanize, with_images, stop_at, use_browser_cookies = render_sidebar()
    st.session_state.use_browser_cookies = use_browser_cookies

    # 把后台线程写入 ui.log_sink 的状态同步到 st.session_state（本 run 起点）
    _sync_ui_state_to_session()

    # ── 顶部 Tab：工作台 / 成果 / 发布（3 Tab，配置已归入 Sidebar） ──

    tab_monitor, tab_results, tab_publish = st.tabs(
        ["🎯 工作台", "📊 成果", "🚀 发布"]
    )

    with tab_monitor:
        url, generate_btn = render_main()

        # ── 情况 1：用户点击按钮，启动后台线程 ──
        if generate_btn and url.strip():
            processed = st.session_state.get("processed_url", "")
            if not processed:
                st.error("❌ 未在输入中找到有效的视频链接，请粘贴包含链接的分享内容")
            elif st.session_state.is_running:
                st.warning("⏳ 流水线正在执行中，请等待完成后再试")
            elif not _PIPELINE_LOCK.acquire(blocking=False):
                st.warning("⏳ 流水线已在另一个会话中执行，请等待完成后再试")
            else:
                try:
                    # 初始化运行状态：生成新日志文件，重置 UI 状态
                    _new_log = _new_log_file_path()
                    st.session_state.log_file_path = _new_log
                    log_sink.install(_new_log)
                    log_sink.reset()
                    log_sink.set_running(True)
                    _STAGE_EVENT.clear()

                    # 首启分阶段状态（Track 3：阶段性加载反馈，替代单行 spinner）
                    if _TORCH_MOD is None or _PIPELINE_FN is None:
                        with st.status("首次启动：初始化 AI 引擎", expanded=True) as _st:
                            _st.update(label="⏳ 加载 PyTorch / Transformers（约 45 秒）…")
                            _ensure_transcribe_imports()
                            _st.update(label="✅ 引擎就绪", state="complete")

                    def _run():
                        try:
                            execute_pipeline(processed, style, humanize, with_images, content_type, stop_at)
                        except BaseException as e:
                            # 必须捕获 BaseException：兜底线程级致命错误（含 KeyboardInterrupt），
                            # 并确保无论成功/失败/中断都释放 _PIPELINE_LOCK，防止锁泄漏导致后续无法启动。
                            log_sink.set_pipeline_done(
                                f"致命错误({type(e).__name__}): {e}"
                            )
                        finally:
                            _PIPELINE_LOCK.release()

                    thread = threading.Thread(target=_run, daemon=True)
                    add_script_run_ctx(thread, get_script_run_ctx())
                    thread.start()
                except Exception:
                    _PIPELINE_LOCK.release()
                    raise

        # ── 情况 2/3：进度 + 日志 ──
        #    运行中：fragment 仅刷新进度/日志/下一步按钮，不重绘标题与 URL 输入，消除整页闪烁
        #    判断条件读 UISync 实时快照（线程安全），避免 2162 行 sync 时 UISync 尚未 set_running 的时序死锁
        _snap = log_sink.snapshot()
        if _snap["is_running"] and not _snap["pipeline_done"]:

            @st.fragment(run_every=3)
            def _live_logs():
                _sync_ui_state_to_session()
                render_progress()
                render_logs()
                # 分步控制器按钮【必须放在 fragment 内部】
                st.markdown("---")
                if st.session_state.get("awaiting_next", False):
                    col1, col2, col3 = st.columns([2, 3, 2])
                    with col2:
                        st.info("⏸️ 当前阶段已完成，点击下方按钮继续下一阶段")
                        if st.button("▶ 下一步", use_container_width=True,
                                     type="primary", key="btn_next_stage"):
                            _STAGE_EVENT.set()
                            st.rerun()
                else:
                    col1, col2, col3 = st.columns([2, 3, 2])
                    with col2:
                        st.button("⏳ 执行中…", use_container_width=True,
                                 disabled=True, key="btn_waiting")
                if st.session_state.pipeline_done:
                    st.rerun()
            _live_logs()

        else:
            # 兜底：运行结束后把 UISync 最终状态（result_data/pipeline_done/stage_status）拉回 session_state
            _sync_ui_state_to_session()
            render_progress()
            render_logs()
            # 全部完成状态
            if st.session_state.pipeline_done and not st.session_state.pipeline_error:
                st.markdown("---")
                col1, col2, col3 = st.columns([2, 3, 2])
                with col2:
                    st.success("✅ 全部阶段已完成")
            if st.session_state.pipeline_error:
                st.error(f"流水线执行异常: {st.session_state.pipeline_error}")


    with tab_publish:
        render_publish()

    with tab_results:
        render_results()


if __name__ == "__main__":
    main()
