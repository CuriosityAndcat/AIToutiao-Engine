"""
阶段测试 Harness
================
用最小 streamlit stub 注入后直接 import engine_app，从而在不启动 Streamlit
Web 服务的前提下，直接调用各阶段真实函数做功能测试（非 LLM 模拟）。

各阶段真实入口：
  阶段1 下载     -> engine_app.step_download(state)        [需 --url]
  阶段2 转录     -> engine_app.step_transcribe(state)      [需 --media 音频/视频]
  阶段3 研究写作 -> write_stage.research_and_write(state)  [读 transcript_text]
  阶段4 配图     -> engine_app.step_images(state)          [读 generated_title/content]
  阶段5 组装     -> engine_app.step_assemble(state)        [读 成稿 + 图片]

测试产物统一落在 outputs/test_sta/<run_id>/ 下，便于清理与复核。
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any, Optional

ENGINE_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ENGINE_ROOT / "lib" / "toutiao-auto-publisher" / "backend"
SENSEVOICE_DIR = ENGINE_ROOT / "lib" / "sensevoice-asr"
OUTPUTS_DIR = ENGINE_ROOT / "outputs"


class _AttrDict(dict):
    """dict + 属性访问混合，兼容 st.session_state 的 dict/属性混合用法。"""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, val):
        self[name] = val

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            raise AttributeError(name)


def _noop(*_a, **_k):
    return None


class _StreamlitStub(types.ModuleType):
    """最小 streamlit 桩：session_state 用真实容器，其余 API 一律 no-op。"""

    def __init__(self):
        super().__init__("streamlit")
        # session_state：预置阶段函数实际会用到的键
        object.__setattr__(self, "session_state", _AttrDict(
            logs=[],
            progress_pct=0,
            stage_status={},
            current_stage="",
            theme="dark",
        ))
        # runtime.scriptrunner 子模块（engine_app 顶层 from import 需要）
        rt = types.ModuleType("streamlit.runtime")
        rs = types.ModuleType("streamlit.runtime.scriptrunner")
        rs.add_script_run_ctx = _noop
        rs.get_script_run_ctx = _noop
        object.__setattr__(self, "runtime", rt)
        rt.scriptrunner = rs
        sys.modules["streamlit.runtime"] = rt
        sys.modules["streamlit.runtime.scriptrunner"] = rs

    def __getattr__(self, name):
        # 任意未知 streamlit API（markdown/sidebar/set_page_config 等）-> no-op
        return _noop


def _install_streamlit_stub() -> None:
    """注入一个最小 streamlit 桩，使 engine_app 能在无 Web 服务环境下被 import。"""
    if "streamlit" in sys.modules:
        return
    sys.modules["streamlit"] = _StreamlitStub()


def load_engine_app():
    """注入 streamlit stub 并 import engine_app，返回模块对象。"""
    if "engine_app" in sys.modules:
        return sys.modules["engine_app"]
    _install_streamlit_stub()
    for p in (str(ENGINE_ROOT), str(BACKEND_DIR), str(SENSEVOICE_DIR)):
        if p not in sys.path:
            sys.path.insert(0, p)
    import engine_app  # noqa: E402
    return engine_app


def make_state(run_id: str = "test_sta_000", **overrides) -> Any:
    """构造最小可用的 PipelineState（run_dir 落在 outputs/test_sta/ 下）。"""
    engine = load_engine_app()
    return engine.PipelineState(run_id=run_id, **overrides)


def find_latest_article() -> Optional[Path]:
    if not OUTPUTS_DIR.exists():
        return None
    cands: list[Path] = []
    for pat in ("*_ai_raw.md", "文章_*.md", "微头条_*.md"):
        cands.extend(OUTPUTS_DIR.rglob(pat))
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def find_latest_transcript() -> Optional[Path]:
    if not OUTPUTS_DIR.exists():
        return None
    cands = list(OUTPUTS_DIR.rglob("transcript.txt"))
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None
