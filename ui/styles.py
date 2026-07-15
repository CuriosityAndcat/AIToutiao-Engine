"""CSS 注入函数 — 从 engine_app.py 抽出（P1-1 CSS 分离）。

样式文件: ui/styles.css (~535 行)
Token 文件: ui/theme_tokens.py (暗色/浅色双主题)
"""

from pathlib import Path
import streamlit as st

from ui.theme_tokens import get_theme_tokens

# CSS 文件路径（相对于 ui/styles.py）
_CSS_PATH = Path(__file__).resolve().parent / "styles.css"


def _inject_css():
    """注入全局样式。从 styles.css 读取 CSS，按 session_state.theme 替换 Token。"""
    _css_raw = _CSS_PATH.read_text(encoding="utf-8")
    theme = st.session_state.get("theme", "dark")
    tokens = get_theme_tokens(theme)
    _css = _css_raw.replace("/*THEME_TOKENS*/", tokens)
    st.markdown(f"<style>{_css}</style>", unsafe_allow_html=True)
