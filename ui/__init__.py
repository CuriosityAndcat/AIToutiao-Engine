"""ui 模块 — 从 engine_app.py 分离的 CSS/样式层 + 线程安全日志同步。

    styles.css:   全局 Streamlit 样式（~535行）
    theme_tokens: 暗色/浅色双主题 CSS 变量映射
    log_sink:     后台线程安全日志/阶段/进度同步
"""
from ui.styles import _inject_css
from ui import log_sink

__all__ = ["_inject_css", "log_sink"]

