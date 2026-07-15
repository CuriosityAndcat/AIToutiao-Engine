"""线程安全的 UI 状态/日志同步槽。

engine_app.py 的后台线程不能直接写 st.session_state（Streamlit 的 SafeSessionState
不是线程安全的，更新会丢失甚至引发死锁）。本模块提供：

- 一个后台线程可安全写入的共享状态（UISync）。
- 一个 stderr → 日志文件 的 Tee（只安装一次，避免 Streamlit 多次 rerun 重复包装）。
- 主线程 / fragment 在每次刷新时把共享状态回写到 st.session_state，从而更新前端。
"""

from __future__ import annotations

import queue
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# ── 共享 UI 状态（后台线程写，主线程/fragment 读）────────────────────────
_DEFAULT_STAGE_STATUS = {
    "下载": "pending",
    "转录": "pending",
    "研究写作": "pending",
    "配图": "pending",
    "组装": "pending",
}

_MAX_UI_LOGS = 500
_LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


class UISync:
    """线程安全的 UI 状态缓存。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._state: Dict[str, Any] = {
            "is_running": False,
            "pipeline_done": False,
            "pipeline_error": None,
            "result_data": None,
            "run_id": "",
            "current_stage": "",
            "stage_status": dict(_DEFAULT_STAGE_STATUS),
            "progress_pct": 0.0,
            "logs": [],
            "elapsed_seconds": 0.0,
            "awaiting_next": False,
        }

    def update(self, **kwargs: Any) -> None:
        with self._lock:
            for k, v in kwargs.items():
                if k == "stage_status" and isinstance(v, dict):
                    self._state["stage_status"].update(v)
                elif k == "log" and isinstance(v, dict):
                    self._state["logs"].append(v)
                    if len(self._state["logs"]) > _MAX_UI_LOGS:
                        self._state["logs"] = self._state["logs"][-_MAX_UI_LOGS:]
                else:
                    self._state[k] = v

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                **self._state,
                "stage_status": dict(self._state["stage_status"]),
                "logs": list(self._state["logs"]),
            }

    def reset(self) -> None:
        with self._lock:
            self._state.update(
                {
                    "is_running": False,
                    "pipeline_done": False,
                    "pipeline_error": None,
                    "result_data": None,
                    "run_id": "",
                    "current_stage": "",
                    "stage_status": dict(_DEFAULT_STAGE_STATUS),
                    "progress_pct": 0.0,
                    "logs": [],
                    "elapsed_seconds": 0.0,
                    "awaiting_next": False,
                }
            )


UI_SYNC = UISync()


# ── stderr → 日志文件三通（只安装一次）────────────────────────────────────
class _TeeStderr:
    """把 stderr 同时镜像到日志文件。

    保持文件句柄打开，避免每行 open/flush/close。
    add_log 的 [HH:MM:SS] 行会由 add_log 自己带 [LEVEL] 写入文件，这里跳过避免重复。
    """

    _lock = threading.Lock()

    def __init__(self, orig, log_path: str):
        self._orig = orig
        self._log_path = log_path
        self._file: Optional[Any] = None
        self._aitoutiao_tee = True
        self._open_file()

    def _open_file(self):
        if self._log_path:
            try:
                self._file = open(self._log_path, "a", encoding="utf-8")
            except Exception:
                self._file = None

    def set_log_path(self, p: str):
        with self._lock:
            if self._file:
                try:
                    self._file.close()
                except Exception:
                    pass
            self._log_path = p
            self._file = None
            self._open_file()

    def __del__(self):
        if self._file:
            try:
                self._file.close()
            except Exception:
                pass

    @staticmethod
    def _is_addlog_line(data: str) -> bool:
        s = data.lstrip()
        return (
            s.startswith("[")
            and len(s) >= 9
            and s[1:3].isdigit()
            and s[3] == ":"
            and s[6] == ":"
        )

    def write(self, data):
        try:
            self._orig.write(data)
        except Exception:
            pass
        if self._is_addlog_line(data):
            return
        fh = self._file
        if fh:
            try:
                fh.write(data)
                fh.flush()
            except Exception:
                pass

    def flush(self):
        try:
            self._orig.flush()
        except Exception:
            pass


_LOG_FILE_PATH: str = ""


def install(log_path: str) -> None:
    """安装/更新 stderr Tee。多次调用不会重复包装。"""
    global _LOG_FILE_PATH
    _LOG_FILE_PATH = log_path
    if hasattr(sys.stderr, "_aitoutiao_tee"):
        try:
            sys.stderr.set_log_path(log_path)
        except Exception:
            pass
    else:
        try:
            sys.stderr = _TeeStderr(sys.stderr, log_path)
        except Exception:
            pass


def _rotate_logs(log_path: Path):
    """日志轮转：当前 >10MB 时备份为 .1/.2/.3。"""
    backup3 = log_path.with_suffix(".3")
    if backup3.exists():
        backup3.unlink()
    for i in range(2, 0, -1):
        src = log_path.with_suffix(f".{i}")
        dst = log_path.with_suffix(f".{i + 1}")
        if src.exists():
            src.rename(dst)
    backup1 = log_path.with_suffix(".1")
    log_path.rename(backup1)


# ── 后台线程可用的写接口 ────────────────────────────────────────────────
def add_log(msg: str, level: str = "info") -> None:
    """添加日志：stderr + 文件 + UI 状态缓存。"""
    now = datetime.now()
    time_short = now.strftime("%H:%M:%S")
    time_full = now.strftime("%Y-%m-%d %H:%M:%S")

    # 通道 1：stderr（CMD / Streamlit）
    try:
        sys.stderr.write(f"[{time_short}] {msg}\n")
        sys.stderr.flush()
    except Exception:
        pass

    # 通道 2：UI 状态缓存
    UI_SYNC.update(log={"time": time_short, "msg": msg, "level": level})

    # 通道 3：日志文件
    try:
        path = _LOG_FILE_PATH
        if path:
            p = Path(path)
            with _TeeStderr._lock:
                if p.exists() and p.stat().st_size > _LOG_MAX_BYTES:
                    _rotate_logs(p)
                with open(path, "a", encoding="utf-8") as f:
                    f.write(f"[{time_full}] [{level.upper()}] {msg}\n")
                    f.flush()
    except Exception:
        pass


def set_stage(name: str, status: str) -> None:
    """更新阶段状态。"""
    UI_SYNC.update(stage_status={name: status}, current_stage=name)


def set_progress(pct: float) -> None:
    """更新进度百分比。"""
    UI_SYNC.update(progress_pct=float(pct))


def set_running(value: bool) -> None:
    UI_SYNC.update(is_running=bool(value))


def set_pipeline_done(error: Optional[str] = None) -> None:
    UI_SYNC.update(pipeline_done=True, pipeline_error=error, is_running=False)


def set_pipeline_started(run_id: str) -> None:
    UI_SYNC.update(is_running=True, pipeline_done=False, pipeline_error=None, run_id=run_id)


def set_result(result: Dict[str, Any], elapsed_seconds: float) -> None:
    UI_SYNC.update(result_data=result, elapsed_seconds=elapsed_seconds)


def reset() -> None:
    UI_SYNC.reset()


def snapshot() -> Dict[str, Any]:
    """主线程/fragment 调用，获取当前 UI 状态快照。"""
    return UI_SYNC.snapshot()
