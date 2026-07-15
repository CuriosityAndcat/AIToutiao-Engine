"""双主题 CSS Token 常量 — 从 engine_app._inject_css() 抽出。

由 ui/styles.py 的 _inject_css() 按 st.session_state.theme 选择注入。
"""

_TOKENS_DARK = """
            /* ── 暗色主题：深夜蓝底 + Indigo 蓝紫强调 ── */
            --bg-base: #0B1120;
            --bg-surface: #111827;
            --bg-elevated: #1F2937;
            --border: rgba(148,163,184,0.10);
            --border-soft: rgba(148,163,184,0.06);
            --border-hover: rgba(148,163,184,0.20);
            --border-accent: rgba(99,102,241,0.30);
            --accent: #6366F1;
            --accent-dark: #4F46E5;
            --accent-hover: #818CF8;
            --accent-muted: rgba(99,102,241,0.20);
            --accent-glow: rgba(99,102,241,0.20);
            --success: #10B981;
            --success-muted: rgba(16,185,129,0.12);
            --danger: #EF4444;
            --danger-muted: rgba(239,68,68,0.12);
            --warning: #F59E0B;
            --warning-muted: rgba(245,158,11,0.12);
            --info: #38BDF8;
            --text: #F1F5F9;
            --text-secondary: #94A3B8;
            --text-muted: #64748B;
            --text-inverse: #0B1120;
            --shadow-card: 0 1px 3px rgba(0,0,0,0.30);
            --shadow-panel: 0 1px 2px rgba(0,0,0,0.20);
            --shadow-lg: 0 4px 6px rgba(0,0,0,0.25), 0 10px 30px rgba(0,0,0,0.15);
            --shadow-elevated: 0 4px 6px rgba(0,0,0,0.25), 0 10px 30px rgba(0,0,0,0.15);
            --shadow-none: none;
            --space-1: 4px;  --space-2: 8px;  --space-3: 12px;
            --space-4: 16px; --space-5: 24px; --space-6: 32px;
            --radius-sm: 6px; --radius-md: 8px; --radius-lg: 12px; --radius-xl: 16px;
            --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', 'Segoe UI', sans-serif;
            --font-mono: 'JetBrains Mono', 'Consolas', 'Courier New', monospace;
"""

_TOKENS_LIGHT = """
            /* ── 浅色主题：暖灰白底 + Indigo 蓝紫强调 ── */
            --bg-base: #F8FAFC;
            --bg-surface: #FFFFFF;
            --bg-elevated: #F1F5F9;
            --border: rgba(148,163,184,0.25);
            --border-soft: rgba(148,163,184,0.15);
            --border-hover: rgba(148,163,184,0.40);
            --border-accent: rgba(79,70,229,0.30);
            --accent: #4F46E5;
            --accent-dark: #4338CA;
            --accent-hover: #6366F1;
            --accent-muted: rgba(79,70,229,0.12);
            --accent-glow: rgba(79,70,229,0.15);
            --success: #059669;
            --success-muted: rgba(5,150,105,0.10);
            --danger: #DC2626;
            --danger-muted: rgba(220,38,38,0.10);
            --warning: #D97706;
            --warning-muted: rgba(217,119,6,0.10);
            --info: #0284C7;
            --text: #0F172A;
            --text-secondary: #475569;
            --text-muted: #94A3B8;
            --text-inverse: #F8FAFC;
            --shadow-card: 0 1px 3px rgba(15,23,42,0.06);
            --shadow-panel: 0 1px 2px rgba(15,23,42,0.04);
            --shadow-lg: 0 4px 6px rgba(15,23,42,0.05), 0 10px 30px rgba(15,23,42,0.06);
            --shadow-elevated: 0 4px 6px rgba(15,23,42,0.05), 0 10px 30px rgba(15,23,42,0.06);
            --shadow-none: none;
            --space-1: 4px;  --space-2: 8px;  --space-3: 12px;
            --space-4: 16px; --space-5: 24px; --space-6: 32px;
            --radius-sm: 6px; --radius-md: 8px; --radius-lg: 12px; --radius-xl: 16px;
            --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', 'Segoe UI', sans-serif;
            --font-mono: 'JetBrains Mono', 'Consolas', 'Courier New', monospace;
"""


def get_theme_tokens(theme: str = "dark") -> str:
    """按主题名返回 CSS Token 变量块。"""
    return _TOKENS_LIGHT if theme == "light" else _TOKENS_DARK
