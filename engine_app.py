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
def _inject_css():
    """注入全局样式。统一 token 体系（颜色/间距/圆角/字体/阴影/动效），
    支持浅色主题切换（原生 Streamlit 控件 + session_state，无 JS 注入）。
    v2: Google Fonts 加持、玻璃态卡片、统一过渡动效、无障碍焦点环、响应式增强。"""
    _css = (
        """
    <style>
        /* ── Google Fonts ── */
        @import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600;6..72,700&family=Roboto:wght@300;400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');

        /* ═══════════════════════════════════════════
           设计 Token（暗色 / 浅色按 session_state 注入）
           ═══════════════════════════════════════════ */
        :root {
            /*THEME_TOKENS*/
            /* ── 动效时长 ── */
            --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
            --transition-base: 250ms cubic-bezier(0.4, 0, 0.2, 1);
            --transition-slow: 400ms cubic-bezier(0.4, 0, 0.2, 1);
            /* ── 玻璃态 ── */
            --glass-bg: rgba(22, 27, 34, 0.65);
            --glass-border: rgba(255, 255, 255, 0.06);
            --glass-blur: 12px;
            /* ── 层级 ── */
            --z-dropdown: 100; --z-sticky: 200; --z-overlay: 300; --z-modal: 400; --z-toast: 500;
        }

        /* ═══════════════════════════════════════════
           基础重置
           ═══════════════════════════════════════════ */
        .stApp, .stApp .main, [data-testid="stAppViewContainer"] {
            background-color: var(--bg-base);
            color: var(--text);
            transition: background-color var(--transition-base), color var(--transition-base);
        }
        footer { visibility: hidden; }

        /* ── 全局滚动条美化 ── */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 3px;
            transition: background var(--transition-fast);
        }
        ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

        /* ── 全局选择颜色 ── */
        ::selection { background: var(--accent-glow); color: var(--text); }

        /* ── 全局焦点环（无障碍） ── */
        :focus-visible {
            outline: 2px solid var(--accent) !important;
            outline-offset: 2px !important;
            border-radius: var(--radius-sm);
        }

        /* ═══════════════════════════════════════════
           主标题 — 渐变文字
           ═══════════════════════════════════════════ */
        .main-header {
            background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dark) 60%, var(--info) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-family: var(--font-heading);
            font-size: clamp(22px, 4vw, 32px);
            font-weight: 700;
            text-align: center;
            padding: 12px 0 6px;
            margin-bottom: 4px;
            letter-spacing: -0.02em;
        }

        /* ═══════════════════════════════════════════
           状态药丸
           ═══════════════════════════════════════════ */
        .status-pill {
            display: inline-flex; align-items: center; gap: 6px;
            font-size: 13px; font-weight: 500;
            padding: 4px 16px; border-radius: 999px;
            margin-bottom: var(--space-4);
            font-family: var(--font-sans);
            transition: all var(--transition-base);
            backdrop-filter: blur(var(--glass-blur));
            -webkit-backdrop-filter: blur(var(--glass-blur));
        }
        .status-pill::before {
            content: ""; display: inline-block; width: 8px; height: 8px; border-radius: 50%;
        }
        .status-pill.running {
            color: var(--warning); background: var(--bg-elevated);
            border: 1px solid var(--warning);
        }
        .status-pill.running::before {
            background: var(--warning);
            animation: pulse-dot 1.2s ease-in-out infinite;
        }
        .status-pill.done {
            color: var(--success); background: var(--bg-elevated);
            border: 1px solid var(--success);
        }
        .status-pill.done::before { background: var(--success); }
        .status-pill.ready {
            color: var(--text-muted); background: var(--bg-elevated);
            border: 1px solid var(--border);
        }
        .status-pill.ready::before { background: var(--text-muted); }
        @keyframes pulse-dot { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.75); } }

        /* ═══════════════════════════════════════════
           阶段流程（灯 + 连接线）
           ═══════════════════════════════════════════ */
        .stage-flow {
            display: flex; align-items: flex-start; justify-content: space-between;
            margin: var(--space-4) 0 var(--space-5);
            gap: var(--space-1);
        }
        .stage-step {
            flex: 1; text-align: center; position: relative;
            transition: transform var(--transition-base);
        }
        .stage-step:not(:last-child)::after {
            content: ""; position: absolute; top: 11px; left: 55%; width: 90%;
            height: 2px; background: var(--border);
            z-index: 0; border-radius: 1px;
            transition: background var(--transition-slow);
        }
        .stage-step.done:not(:last-child)::after {
            background: linear-gradient(90deg, var(--success), var(--border));
        }
        .stage-step .dot {
            position: relative; z-index: 1;
            display: inline-flex; align-items: center; justify-content: center;
            width: 22px; height: 22px; border-radius: 50%;
            border: 2px solid var(--border);
            background: var(--bg-surface);
            font-size: 10px; line-height: 1; font-weight: 700;
            color: var(--text-muted);
            transition: all var(--transition-base);
        }
        .stage-step.pending .dot { color: var(--text-muted); }
        .stage-step.done .dot {
            background: var(--success); border-color: var(--success);
            color: #fff; box-shadow: 0 0 8px rgba(63, 185, 80, 0.35);
        }
        .stage-step.running .dot {
            background: var(--accent); border-color: var(--accent);
            color: #fff;
            animation: pulse-dot 1.2s ease-in-out infinite;
            box-shadow: 0 0 12px var(--accent-glow);
        }
        .stage-step.failed .dot {
            background: var(--danger); border-color: var(--danger);
            color: #fff; box-shadow: 0 0 8px rgba(248, 81, 73, 0.35);
        }
        .stage-step .label {
            font-size: 11px; color: var(--text-muted); margin-top: 5px;
            font-family: var(--font-sans); font-weight: 500;
            transition: color var(--transition-base);
        }
        .stage-step.done .label { color: var(--text); }
        .stage-step.running .label { color: var(--accent); font-weight: 600; }
        .stage-step .state {
            font-size: 10px; margin-top: 1px; font-family: var(--font-sans);
            font-weight: 500; transition: color var(--transition-base);
        }
        .stage-step.done .state { color: var(--success); }
        .stage-step.running .state { color: var(--accent); }
        .stage-step.failed .state { color: var(--danger); }
        .stage-step.pending .state { color: var(--text-muted); }

        /* ═══════════════════════════════════════════
           日志容器（终端风格）
           ═══════════════════════════════════════════ */
        .log-container {
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: var(--space-3);
            max-height: 340px;
            overflow-y: auto;
            font-family: var(--font-mono);
            font-size: 12.5px;
            color: var(--text);
            line-height: 1.7;
            box-shadow: var(--shadow-panel);
            position: relative;
        }
        .log-container::before {
            content: "";
            position: sticky; top: 0; left: 0; right: 0; z-index: 2;
            display: block; height: var(--space-2);
            background: linear-gradient(180deg, var(--bg-surface) 0%, transparent 100%);
            pointer-events: none;
            margin: calc(-1 * var(--space-3)) calc(-1 * var(--space-3)) 0;
            padding: 0 var(--space-3) 0;
        }
        .log-line {
            padding: 1px 0;
            border-left: 2px solid transparent;
            padding-left: var(--space-2);
            transition: border-color var(--transition-fast);
        }
        .log-line.info { color: var(--text); }
        .log-line.success { color: var(--success); border-left-color: var(--success); }
        .log-line.error { color: var(--danger); border-left-color: var(--danger); }
        .log-line.warning { color: var(--warning); border-left-color: var(--warning); }
        .log-line.stage { color: var(--info); border-left-color: var(--info); font-weight: 500; }

        /* ═══════════════════════════════════════════
           卡片 / 面板（玻璃态增强）
           ═══════════════════════════════════════════ */
        .result-card {
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: var(--space-5);
            margin-top: var(--space-4);
            box-shadow: var(--shadow-card);
            transition: box-shadow var(--transition-base), border-color var(--transition-base);
            animation: fadeInUp 0.35s ease-out both;
        }
        .result-card:hover {
            box-shadow: var(--shadow-lg);
            border-color: var(--border-soft);
        }
        .panel {
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: var(--space-4);
            box-shadow: var(--shadow-panel);
            margin-bottom: var(--space-4);
            transition: box-shadow var(--transition-base), border-color var(--transition-base);
            animation: fadeInUp 0.3s ease-out both;
        }
        .panel:hover {
            box-shadow: var(--shadow-card);
            border-color: var(--border-soft);
        }
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* ── 统计徽章 ── */
        .stat-badge {
            display: inline-flex; align-items: center; gap: 4px;
            background: var(--bg-elevated);
            border: 1px solid var(--border-soft);
            border-radius: var(--radius-sm);
            padding: 5px 12px; font-size: 12px; color: var(--text-muted);
            margin-right: 8px; margin-bottom: 6px;
            font-family: var(--font-sans); font-weight: 500;
            transition: all var(--transition-fast);
        }
        .stat-badge:hover { color: var(--text); border-color: var(--border); }

        /* ═══════════════════════════════════════════
           按钮系统
           ═══════════════════════════════════════════ */
        button[kind="primary"] {
            background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dark) 100%) !important;
            border: none !important;
            font-weight: 600 !important;
            letter-spacing: 0.01em;
            transition: all var(--transition-fast) !important;
            box-shadow: 0 2px 8px var(--accent-glow) !important;
        }
        button[kind="primary"]:hover:not(:disabled) {
            transform: translateY(-1px);
            box-shadow: 0 4px 16px var(--accent-glow) !important;
            filter: brightness(1.08);
        }
        button[kind="primary"]:active:not(:disabled) { transform: translateY(0); }
        button[kind="primary"]:disabled {
            opacity: 0.5 !important;
            cursor: not-allowed !important;
            box-shadow: none !important;
        }

        /* ── 普通按钮 ── */
        button:not([kind="primary"]) {
            transition: all var(--transition-fast) !important;
            border-radius: var(--radius-md) !important;
        }
        button:not([kind="primary"]):hover:not(:disabled) {
            border-color: var(--accent) !important;
            color: var(--accent) !important;
        }

        /* ═══════════════════════════════════════════
           输入框
           ═══════════════════════════════════════════ */
        input[type="text"], textarea, .stTextInput input {
            background: var(--bg-surface) !important;
            border: 1px solid var(--border) !important;
            color: var(--text) !important;
            border-radius: var(--radius-md) !important;
            transition: all var(--transition-fast) !important;
            font-family: var(--font-sans);
        }
        .stTextInput > div > div > input:focus,
        input[type="text"]:focus, textarea:focus {
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 3px var(--accent-glow) !important;
        }
        .stTextInput > div > div > input::placeholder {
            color: var(--text-muted) !important; opacity: 0.7;
        }

        /* ═══════════════════════════════════════════
           Tab 栏美化
           ═══════════════════════════════════════════ */
        [data-testid="stTabs"] {
            margin-top: var(--space-2);
        }
        [data-testid="stTabs"] [role="tablist"] {
            gap: var(--space-1);
        }
        [data-testid="stTabs"] button[role="tab"] {
            font-family: var(--font-sans);
            font-weight: 500;
            font-size: 14px;
            padding: 8px 20px;
            border-radius: var(--radius-md) var(--radius-md) 0 0;
            transition: all var(--transition-fast);
            border: 1px solid transparent;
            color: var(--text-muted);
        }
        [data-testid="stTabs"] button[role="tab"]:hover {
            color: var(--text);
            background: var(--bg-elevated);
        }
        [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            color: var(--accent);
            border-bottom: 2px solid var(--accent);
            background: transparent;
            font-weight: 600;
        }

        /* ═══════════════════════════════════════════
           侧栏
           ═══════════════════════════════════════════ */
        div[data-testid="stSidebar"] {
            background-color: var(--bg-base);
            border-right: 1px solid var(--border-soft);
        }
        div[data-testid="stSidebar"] * { color: var(--text); }
        div[data-testid="stSidebar"] .stSelectbox label,
        div[data-testid="stSidebar"] .stRadio label {
            font-weight: 500; font-size: 13px;
        }
        div[data-testid="stSidebar"] hr {
            border-color: var(--border);
        }
        div[data-testid="stSidebar"] .stToggle {
            padding: 4px 0;
        }

        /* ═══════════════════════════════════════════
           Expander / 折叠面板
           ═══════════════════════════════════════════ */
        .stExpander {
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-md) !important;
            background: var(--bg-surface) !important;
            margin-bottom: var(--space-3);
            transition: border-color var(--transition-fast);
        }
        .stExpander:hover { border-color: var(--text-muted) !important; }
        .stExpander > div:first-child {
            font-weight: 600; font-size: 14px;
        }

        /* ═══════════════════════════════════════════
           进度条
           ═══════════════════════════════════════════ */
        .stProgress > div > div > div {
            background: linear-gradient(90deg, var(--accent-dark), var(--accent), var(--info)) !important;
            border-radius: var(--radius-sm);
            transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .stProgress > div > div {
            background: var(--bg-elevated) !important;
            border-radius: var(--radius-sm);
            height: 8px !important;
        }

        /* ═══════════════════════════════════════════
           Metric 指标卡
           ═══════════════════════════════════════════ */
        [data-testid="stMetric"] {
            background: var(--bg-elevated);
            border: 1px solid var(--border-soft);
            border-radius: var(--radius-md);
            padding: var(--space-3);
            transition: all var(--transition-fast);
        }
        [data-testid="stMetric"]:hover {
            border-color: var(--border);
            box-shadow: var(--shadow-panel);
        }
        [data-testid="stMetric"] label {
            font-weight: 500 !important;
            font-size: 12px !important;
            color: var(--text-muted) !important;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        [data-testid="stMetricValue"] {
            font-size: 24px !important;
            font-weight: 700 !important;
            font-family: var(--font-heading);
        }

        /* ═══════════════════════════════════════════
           Dataframe / 表格
           ═══════════════════════════════════════════ */
        .stDataFrame {
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-md) !important;
            overflow: hidden;
        }
        .stDataFrame [data-testid="stTable"] th {
            background: var(--bg-elevated) !important;
            font-weight: 600 !important;
            font-size: 12px !important;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }

        /* ═══════════════════════════════════════════
           标题分级
           ═══════════════════════════════════════════ */
        .section-title {
            font-size: 16px; font-weight: 600; color: var(--text);
            margin-bottom: var(--space-3); font-family: var(--font-sans);
            display: flex; align-items: center; gap: 6px;
        }
        .section-title::after {
            content: "";
            flex: 1; height: 1px;
            background: linear-gradient(90deg, var(--border), transparent);
            margin-left: var(--space-2);
        }

        /* ═══════════════════════════════════════════
           空状态 / 引导
           ═══════════════════════════════════════════ */
        .empty-state {
            text-align: center; padding: var(--space-6) var(--space-4);
            color: var(--text-muted); font-size: 14px;
        }

        /* ═══════════════════════════════════════════
           成功 / 错误 / 警告 / 信息横幅
           ═══════════════════════════════════════════ */
        [data-testid="stSuccess"], [data-testid="stError"],
        [data-testid="stWarning"], [data-testid="stInfo"] {
            border-radius: var(--radius-md) !important;
            font-weight: 500;
        }

        /* ═══════════════════════════════════════════
           响应式 — 1440+ 宽屏
           ═══════════════════════════════════════════ */
        @media (min-width: 1440px) {
            .result-card { padding: var(--space-6); }
            .panel { padding: var(--space-5); }
            .log-container { max-height: 400px; }
        }

        /* ═══════════════════════════════════════════
           响应式 — 平板 (≤1024px)
           ═══════════════════════════════════════════ */
        @media (max-width: 1024px) {
            .stage-step .label { font-size: 10px; }
            .stage-step .dot { width: 18px; height: 18px; font-size: 8px; }
            .stage-flow { gap: 2px; }
        }

        /* ═══════════════════════════════════════════
           响应式 — 小平板 (≤768px)
           ═══════════════════════════════════════════ */
        @media (max-width: 768px) {
            .main-header { font-size: 20px; padding: 8px 0; }
            .result-card { padding: var(--space-4); }
            .log-container { max-height: 260px; font-size: 11px; }
            div[data-testid="stSidebar"] { min-width: 200px !important; }
            .stage-step .label { font-size: 9px; }
            .stage-step .dot { width: 16px; height: 16px; font-size: 8px; }
            .status-pill { font-size: 12px; padding: 3px 12px; }
            [data-testid="stTabs"] button[role="tab"] { font-size: 12px; padding: 6px 14px; }
            [data-testid="stMetricValue"] { font-size: 20px !important; }
        }

        /* ═══════════════════════════════════════════
           响应式 — 手机 (≤540px)
           ═══════════════════════════════════════════ */
        @media (max-width: 540px) {
            .main-header { font-size: 18px; }
            .stTextInput > div > div > input { font-size: 14px; padding: 6px 10px; }
            button { font-size: 13px !important; }
            .result-card { padding: var(--space-3); }
            .stat-badge { font-size: 11px; padding: 3px 8px; }
            .log-container { max-height: 200px; }
            .stage-flow { flex-wrap: wrap; gap: var(--space-2); }
            .stage-step { flex: 1 1 auto; min-width: 60px; }
            .stage-step:not(:last-child)::after { display: none; }
            .stage-step .label { font-size: 9px; }
            .stage-step .dot { width: 14px; height: 14px; font-size: 7px; }
            [data-testid="stMetric"] { padding: var(--space-2); }
            [data-testid="stMetricValue"] { font-size: 18px !important; }
            .my-actions .stHorizontalBlock > div { flex: 1 1 100% !important; }
            [data-testid="stTabs"] button[role="tab"] { font-size: 11px; padding: 5px 10px; }
        }

        /* ═══════════════════════════════════════════
           响应式 — 极小屏 (≤375px)
           ═══════════════════════════════════════════ */
        @media (max-width: 375px) {
            .main-header { font-size: 16px; }
            button { font-size: 12px !important; padding: 4px 8px !important; }
            .status-pill { font-size: 11px; padding: 2px 10px; }
        }

        /* ═══════════════════════════════════════════
           无障碍：尊重用户动效偏好
           ═══════════════════════════════════════════ */
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }
    </style>
    """
    )

    # 主题 Token：按 session_state.theme 动态选择（暗色默认 / 浅色），取代原 JS 注入
    theme = st.session_state.get("theme", "dark")
    _TOKENS_DARK = """
            /* ── 暗色主题：深蓝灰底 + 暖橙强调 ── */
            --bg-base: #0A0E14;
            --bg-surface: #131820;
            --bg-elevated: #1C2330;
            --border: #2A3342;
            --border-soft: #1E2735;
            --accent: #FF6B35;
            --accent-dark: #E85D04;
            --success: #3FB950;
            --danger: #F85149;
            --warning: #D29922;
            --info: #58A6FF;
            --text: #E6EDF3;
            --text-muted: #7D8799;
            --accent-glow: rgba(255,107,53,0.28);
            --shadow-card: 0 1px 3px rgba(0,0,0,0.5), 0 4px 16px rgba(0,0,0,0.25);
            --shadow-panel: 0 1px 2px rgba(0,0,0,0.4);
            --shadow-lg: 0 4px 8px rgba(0,0,0,0.5), 0 8px 24px rgba(0,0,0,0.3);
            --space-1: 4px;  --space-2: 8px;  --space-3: 12px;
            --space-4: 16px; --space-5: 24px; --space-6: 32px;
            --radius-sm: 6px; --radius-md: 8px; --radius-lg: 12px;
            --font-heading: 'Newsreader', 'PingFang SC', 'Microsoft YaHei', 'Noto Serif SC', serif;
            --font-sans: 'Roboto', -apple-system, 'PingFang SC', 'Microsoft YaHei', 'Segoe UI', sans-serif;
            --font-mono: 'JetBrains Mono', 'Consolas', 'Courier New', monospace;
    """
    _TOKENS_LIGHT = """
            /* ── 浅色主题：暖白底 + 深橙强调 ── */
            --bg-base: #F8F9FB;
            --bg-surface: #FFFFFF;
            --bg-elevated: #EDF0F5;
            --border: #D1D5DC;
            --border-soft: #E2E6ED;
            --accent: #E0561C;
            --accent-dark: #C24A12;
            --success: #1A7F37;
            --danger: #CF222E;
            --warning: #9A6700;
            --info: #0969DA;
            --text: #1A1D23;
            --text-muted: #5C6270;
            --accent-glow: rgba(224,86,28,0.16);
            --shadow-card: 0 1px 3px rgba(26,29,35,0.08), 0 4px 14px rgba(26,29,35,0.06);
            --shadow-panel: 0 1px 2px rgba(26,29,35,0.06);
            --shadow-lg: 0 4px 8px rgba(26,29,35,0.10), 0 8px 24px rgba(26,29,35,0.08);
            --space-1: 4px;  --space-2: 8px;  --space-3: 12px;
            --space-4: 16px; --space-5: 24px; --space-6: 32px;
            --radius-sm: 6px; --radius-md: 8px; --radius-lg: 12px;
            --font-heading: 'Newsreader', 'PingFang SC', 'Microsoft YaHei', 'Noto Serif SC', serif;
            --font-sans: 'Roboto', -apple-system, 'PingFang SC', 'Microsoft YaHei', 'Segoe UI', sans-serif;
            --font-mono: 'JetBrains Mono', 'Consolas', 'Courier New', monospace;
    """
    _tokens = _TOKENS_LIGHT if theme == "light" else _TOKENS_DARK
    st.markdown(_css.replace("/*THEME_TOKENS*/", _tokens), unsafe_allow_html=True)

    # ── 主题切换控件：注入一次，仅改 <html data-theme> 属性 ──
    #    不改动 Streamlit 管理节点，避免闪烁；状态持久化到 localStorage。
    _theme_toggle = """
    <script>
    (function() {
      const root = document.documentElement;
      const saved = localStorage.getItem('engine_theme') || 'dark';
      root.setAttribute('data-theme', saved);
      function ensure() {
        if (!document.getElementById('theme-switch')) {
          const box = document.querySelector('[data-testid="stSidebarNav"]') || document.querySelector('[data-testid="stSidebar"]');
          if (!box) return;
          const wrap = document.createElement('div');
          wrap.id = 'theme-switch';
          wrap.style.cssText = 'padding:10px 12px;margin-top:8px;';
          const btn = document.createElement('button');
          btn.textContent = (root.getAttribute('data-theme') === 'light') ? '🌙 暗色' : '☀️ 浅色';
          btn.style.cssText = 'width:100%;padding:7px 10px;border-radius:8px;border:1px solid #8884;background:#8882;color:inherit;cursor:pointer;font-size:13px;font-weight:500;transition:all 0.2s ease;';
          btn.onmouseenter = function() { btn.style.background = '#8883'; };
          btn.onmouseleave = function() { btn.style.background = '#8882'; };
          btn.onclick = function() {
            const next = (root.getAttribute('data-theme') === 'light') ? 'dark' : 'light';
            root.setAttribute('data-theme', next);
            localStorage.setItem('engine_theme', next);
            btn.textContent = (next === 'light') ? '🌙 暗色' : '☀️ 浅色';
          };
          wrap.appendChild(btn);
          box.insertBefore(wrap, box.firstChild);
        }
      }
      ensure();
      const obs = new MutationObserver(ensure);
      obs.observe(document.body, {childList: true, subtree: true});
    })();
    </script>
    """


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
    # Cookies 相关已不再需要 — 使用 Playwright 浏览器全自动下载
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── 进度里程碑常量（消除魔法数字）──
_PROGRESS_MAP = {
    "download_start": 0.05,       # 下载阶段起点锚
    "transcribe_start": 0.18,
    "transcribe_done": 0.28,
    "images_start": 0.58,         # 配图阶段起点锚（原 research_write_start，命名纠正）
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

# ── stderr 镜像到日志文件：让「日志文件 = CMD 窗口」完整一致 ──
#    各阶段里大量诊断日志（[download]/[node-env]/[yt-dlp] 等）直接用
#    sys.stderr.write 输出到 CMD 窗口，但原本没进日志文件，导致日志遗漏。
#    包装 sys.stderr 为 Tee：所有 stderr 同时落盘；其中 add_log 的
#    时间戳行已由 add_log 通道3 带 [LEVEL] 写入文件，这里跳过以免重复。
class _TeeStderr:
    _lock = threading.Lock()
    def __init__(self, orig, log_path):
        self._orig = orig
        self._log_path = log_path
    def set_log_path(self, p):
        with self._lock:
            self._log_path = p
    @staticmethod
    def _is_addlog_line(data: str) -> bool:
        # add_log 通道1 格式： [HH:MM:SS] msg
        s = data.lstrip()
        return (s.startswith("[") and len(s) >= 9
                and s[1:3].isdigit() and s[3] == ":" and s[6] == ":")
    def write(self, data):
        try:
            self._orig.write(data)
        except Exception:
            pass
        if self._is_addlog_line(data):
            return  # 已由 add_log 通道3 带 LEVEL 写入文件，避免重复
        with self._lock:
            lp = self._log_path
        if lp:
            try:
                with open(lp, "a", encoding="utf-8") as f:
                    f.write(data)
                    f.flush()
            except Exception:
                pass
    def flush(self):
        try:
            self._orig.flush()
        except Exception:
            pass

if isinstance(sys.stderr, _TeeStderr):
    sys.stderr.set_log_path(st.session_state.log_file_path)
else:
    sys.stderr = _TeeStderr(sys.stderr, st.session_state.log_file_path)


# ============================================================
# 辅助函数
# ============================================================
def add_log(msg: str, level: str = "info"):
    """添加日志条目，自动裁剪到 500 行。
    三通道输出：stderr（CMD 窗口） + session_state（Web UI） + 日志文件（持久化）。"""
    now = datetime.now()
    time_short = now.strftime("%H:%M:%S")
    time_full = now.strftime("%Y-%m-%d %H:%M:%S")
    # 通道 1：stderr → CMD 窗口始终可见（诊断兜底）
    sys.stderr.write(f"[{time_short}] {msg}\n")
    sys.stderr.flush()
    # 通道 2：session_state → Web UI 实时日志
    entry = {"time": time_short, "msg": msg, "level": level}
    try:
        st.session_state.logs.append(entry)
        if len(st.session_state.logs) > 500:
            st.session_state.logs = st.session_state.logs[-500:]
    except Exception:
        pass  # session_state 不可用时静默忽略
    # 通道 3：日志文件 → 本地持久化（同步写入，确保不丢失）
    try:
        _log_path = st.session_state.get("log_file_path", "")
        if _log_path:
            with open(_log_path, "a", encoding="utf-8") as _f:
                _f.write(f"[{time_full}] [{level.upper()}] {msg}\n")
                _f.flush()
    except Exception:
        pass  # 文件写入失败不影响主流程


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
    """更新阶段状态。"""
    st.session_state.stage_status[name] = status
    st.session_state.current_stage = name


def _emoji_for_level(level: str) -> str:
    return {"info": "📝", "success": "✅", "error": "❌", "warning": "⚠️", "stage": "🔷"}.get(
        level, "📝"
    )


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
            add_log(f"npm install 失败: {e.stderr.decode()[:300] if e.stderr else '未知错误'}", "warning")
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


def _download_via_node(state: PipelineState) -> Optional[Dict[str, Any]]:
    """使用 Node.js Playwright 脚本下载视频（全自动，无需 cookies）。
    返回 {'video_files': [...], 'title': '...', 'description': '...'} 或 None。
    """
    import subprocess as sp

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
    add_log(f"  自动打开页面拦截视频流，无需 cookies", "info")

    try:
        result = sp.run(
            cmd,
            cwd=str(_VIDEO_DL_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        stdout = result.stdout or ""
        if result.returncode != 0:
            stderr = (result.stderr or "")[:500]
            add_log(f"Node.js 下载返回非零: {result.returncode}", "warning")
            if stderr:
                add_log(f"  stderr: {stderr}", "warning")
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

    except sp.TimeoutExpired:
        add_log("Node.js 下载超时（>5分钟）", "warning")
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
            st.session_state.progress_pct = (
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
            # 无 cookie 时尝试 Chrome 自动检测
            _sys.stderr.write("[yt-dlp] 尝试 cookiesfrombrowser=chrome\n"); _sys.stderr.flush()
            ydl_opts["cookiesfrombrowser"] = ("chrome",)
            add_log("🍪 尝试从 Chrome 浏览器自动提取 Cookies", "info")

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

    st.session_state.progress_pct = _PROGRESS_MAP["transcribe_start"]

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
    st.session_state.progress_pct = _PROGRESS_MAP["transcribe_done"]
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
    st.session_state.progress_pct = _PROGRESS_MAP["transcribe_done"]
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

# 系统指令：专为 Agnes/ERNIE 中文模型优化（写实纪录片/新闻摄影风格，避免插画/3D 渲染）
_IMAGE_PROMPT_SYSTEM = """你是一个专业的AI配图提示词工程师，专为中文图像生成模型优化。

核心原则：
- 用中文写提示词（模型底层是中文语义理解，英文反而降低质量）。
- 军事内容要具体到真实装备、地点、事件，不能用"军事装备"这种泛词。
- 地图/地缘政治场景用"卫星地图插图"风格，并点名真实地区（如东亚、日本、中国沿海）。
- 风格：真实照片、纪录片摄影、新闻摄影、阅兵场实拍。避免"电影/3D渲染/概念艺术/cinematic"等让模型偏插画的词。
- 构图：主体放在上方85%区域，底部15%留空（后续裁剪用）。
- 硬性禁止：无文字、无字母、无水印、无Logo、无座舱特写。
- 每条提示词不超过300字。纯中文，无解释、无markdown。"""

# 用户指令模板
_IMAGE_PROMPT_USER = """文章标题：{title}
文章内容（节选）：{content}

为这篇军事新闻文章生成配图提示词：
- 1 条封面提示词：文章核心主题最震撼的视觉画面。
- {inline_count} 条内文提示词：不同角度的辅助场景（如地缘地图视角、装备/编队视角）。

严格按以下格式返回（每行一条，不要多余文字）：
COVER: <提示词>
INLINE_1: <提示词>
INLINE_2: <提示词>

每条提示词：纯中文，不超过300字，无文字/水印/Logo，主体在上方85%区域。"""


def _generate_image_prompts_via_llm(title: str, content: str, count: int = 2) -> dict:
    """调用 DeepSeek LLM 生成配图 prompt（封面 + 内文）。

    返回 {'cover': str|None, 'inline': [str,...]}。
    任何异常（无 Key / 超时 / 解析失败）都向上抛出，由调用方 fallback 到硬编码模板。
    """
    from ai_writer import AIWriter

    inline_count = max(1, count)
    user_prompt = _IMAGE_PROMPT_USER.format(
        title=title[:80],
        content=content[:1500].replace("\n", " "),
        inline_count=inline_count,
    )

    writer = AIWriter()
    raw = writer._call_ai(
        user_prompt,
        system_prompt=_IMAGE_PROMPT_SYSTEM,
        max_tokens=800,
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
             f"高细节，锐利对焦，自然光线，无文字，无水印")
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
        st.session_state.progress_pct = _PROGRESS_MAP["images_skipped"]
        return True

    # 检查 Agnes API Key
    agnes_cfg = _get_agnes_config()
    if not agnes_cfg["api_key"]:
        _sys.stderr.write("[images] AGNES_API_KEY 未配置，跳过配图\n"); _sys.stderr.flush()
        add_log("跳过阶段4: AGNES_API_KEY 未配置（请在 .env 或配置面板中设置）", "warning")
        set_stage("配图", "done")
        state.mark_done("generate_images")
        state.outputs["images_injected"] = False
        st.session_state.progress_pct = _PROGRESS_MAP["images_skipped"]
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
    st.session_state.progress_pct = _PROGRESS_MAP["images_start"]

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

        st.session_state.progress_pct = _PROGRESS_MAP["images_cover_done"]

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

        st.session_state.progress_pct = _PROGRESS_MAP["images_all_done"]

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
    st.session_state.progress_pct = _PROGRESS_MAP["assembly_start"]

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

    # ── 注入封面图（极简，无说明文字）──
    if cover_path:
        cover_file = Path(cover_path)
        if cover_file.exists():
            cover_rel = f"images/{cover_file.name}"
            lines = content.split("\n")
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("# "):
                    insert_idx = i + 1
                    while insert_idx < len(lines) and lines[insert_idx].strip() == "":
                        insert_idx += 1
                    break
            if insert_idx > 0:
                # 标题后插入封面图，并保留与正文之间的空行
                lines.insert(insert_idx, f"![封面]({cover_rel})")
                lines.insert(insert_idx + 1, "")
                content = "\n".join(lines)
        else:
            import sys as _sys
            _sys.stderr.write(f"[assemble] 封面图文件缺失，跳过注入: {cover_file.name}\n"); _sys.stderr.flush()
            add_log(f"封面图文件缺失: {cover_file.name}，跳过注入", "warning")

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

    st.session_state.progress_pct = _PROGRESS_MAP["assembly_done"]

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
    st.session_state.progress_pct = _PROGRESS_MAP["pipeline_complete"]
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
                    st.session_state.awaiting_next = True
                    st.session_state.stage_event.wait()  # 阻塞至用户点击
                    st.session_state.awaiting_next = False
                    st.session_state.stage_event.clear()
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
    st.session_state.pipeline_error = None

    try:
        # 始终从零开始新建运行状态（不复用历史记录）
        state = PipelineState(
            input_url=url, content_type=content_type,
            content_style=style, enable_humanize=enable_humanize,
            with_images=with_images,
        )

        st.session_state.pipeline_state = state
        st.session_state.run_id = state.run_id
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
        st.session_state.result_data = result
        elapsed = round(time.time() - t_start, 1)
        st.session_state.elapsed_seconds = elapsed
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
        st.session_state.pipeline_error = str(e)
    finally:
        st.session_state.is_running = False
        st.session_state.pipeline_done = True


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
        "research_notes": research_notes,
    }





# ============================================================
# UI 侧边栏
# ============================================================
def render_sidebar():
    """渲染侧边栏核心配置开关（风格 / 类型 / 人工化 / 配图）。"""
    with st.sidebar:
        # ── 侧栏标题 ──
        st.markdown(
            '<div style="display:flex;align-items:center;gap:8px;padding:4px 0 12px;">'
            '<span style="font-size:20px;">⚙️</span>'
            '<span style="font-weight:600;font-size:16px;font-family:var(--font-sans);">内容配置</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        style = st.selectbox(
            "内容风格",
            options=[
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
            key="sidebar_content_type",
        )

        light_mode = st.toggle("☀️ 浅色主题", value=st.session_state.get("theme", "dark") == "light",
                               help="切换浅色 / 暗色界面（原生控件，无需刷新）")
        st.session_state.theme = "light" if light_mode else "dark"

        humanize = st.toggle("✍️ 人工化改写", value=True, help="去除 AI 味，输出更像真人手笔")
        with_images = st.toggle("🖼️ AI 配图生成", value=True,
                                help="AI 生成封面图 + 内文配图（需配置图片 API Key）")

        st.divider()
        st.markdown(
            '<div style="display:flex;align-items:center;gap:8px;padding:8px 0 4px;">'
            '<span style="font-size:16px;">🎯</span>'
            '<span style="font-weight:600;font-size:14px;font-family:var(--font-sans);">执行范围</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        stop_at = st.selectbox(
            "执行到阶段",
            options=[
                ("全部", "全部阶段（分步执行，每阶段需点「下一步」）"),
                ("download", "下载"),
                ("transcribe", "转录"),
                ("write", "研究写作"),
                ("generate_images", "配图"),
                ("assemble", "组装（输出完整稿件）"),
            ],
            format_func=lambda x: x[1],
            key="sidebar_stop_at",
            help="选择「一次生成到哪一步」：选「下载」只执行下载，选「转录」执行到转录完成即停。具体阶段为连续执行，不等待「下一步」。",
        )

        return style[0], content_type[0], humanize, with_images, stop_at[0]


def render_config_panel():
    """配置 Tab：API 密钥、下载设置、快捷参考（从侧栏迁移，减轻臃肿）。"""
    st.markdown('<div class="section-title">⚙️ 高级配置</div>', unsafe_allow_html=True)

    with st.expander("🔑 API 密钥设置", expanded=True):
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
        # Agnes 配图 API Key
        st.markdown("---")
        st.caption("🖼️ 配图模型（Agnes Image 2.0 Flash）")
        agnes_key = st.text_input(
            "Agnes API Key",
            value=os.getenv("AGNES_API_KEY", ""),
            type="password",
            placeholder="ak-...",
            help="https://apihub.agnes-ai.com 获取，当前 $0/张",
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

    with st.expander("📥 下载设置", expanded=True):
        st.caption("抖音：Playwright 真实浏览器自动拦截视频流，全自动无需 cookies。")
        st.caption("其他平台：yt-dlp 直连下载。")
        st.caption(f"依赖：Node.js + Playwright Chromium（首次自动安装）")

    st.markdown('<div class="section-title">📖 快捷参考</div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="overflow-x:auto;font-size:12px;">'
        '<table style="width:100%;border-collapse:collapse;font-family:var(--font-sans);">'
        '<thead><tr style="border-bottom:2px solid var(--border);">'
        '<th style="text-align:left;padding:6px 8px;color:var(--text);font-weight:600;">风格</th>'
        '<th style="text-align:right;padding:6px 8px;color:var(--text);font-weight:600;">字数</th>'
        '<th style="text-align:left;padding:6px 8px;color:var(--text);font-weight:600;">特点</th>'
        '</tr></thead><tbody>'
        '<tr style="border-bottom:1px solid var(--border-soft);">'
        '<td style="padding:5px 8px;">评书故事型</td><td style="text-align:right;padding:5px 8px;">800-1200</td><td style="padding:5px 8px;">河南方言，评书韵味</td>'
        '</tr>'
        '<tr style="border-bottom:1px solid var(--border-soft);">'
        '<td style="padding:5px 8px;">军事深度</td><td style="text-align:right;padding:5px 8px;">800-1200</td><td style="padding:5px 8px;">七层递进法，证据驱动</td>'
        '</tr>'
        '<tr style="border-bottom:1px solid var(--border-soft);">'
        '<td style="padding:5px 8px;">冷静克制冷</td><td style="text-align:right;padding:5px 8px;">800-1200</td><td style="padding:5px 8px;">事实为主，独到视角</td>'
        '</tr>'
        '<tr style="border-bottom:1px solid var(--border-soft);">'
        '<td style="padding:5px 8px;">硬核论证型</td><td style="text-align:right;padding:5px 8px;">800-1200</td><td style="padding:5px 8px;">数据驱动，逻辑严密</td>'
        '</tr>'
        '<tr style="border-bottom:1px solid var(--border-soft);">'
        '<td style="padding:5px 8px;">快讯速报型</td><td style="text-align:right;padding:5px 8px;">300-500</td><td style="padding:5px 8px;">3段讲清，零铺垫</td>'
        '</tr>'
        '<tr>'
        '<td style="padding:5px 8px;">互动讨论型</td><td style="text-align:right;padding:5px 8px;">500-800</td><td style="padding:5px 8px;">开放式提问，撩互动</td>'
        '</tr>'
        '</tbody></table></div>',
        unsafe_allow_html=True,
    )


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
        for k, v in updated.items():
            if stripped.startswith(f"{k}=") and k not in found:
                new_lines.append(f"{k}={v}")
                found.add(k)
                break
        else:
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
        f'<div style="text-align:center;"><span class="status-pill {status_state}">{status_text}</span></div>',
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
        for k in ("logs", "result_data", "pipeline_state", "run_id", "processed_url",
                  "pipeline_error", "pipeline_done"):
            st.session_state[k] = _DEFAULTS[k]
        for s_name in st.session_state.stage_status:
            st.session_state.stage_status[s_name] = "pending"
        st.session_state.progress_pct = 0.0
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
# UI 结果展示
# ============================================================
def render_results():
    """渲染结果展示区（质检整宽 + 封面/统计卡 + 稿件 + 响应式操作）。"""
    result = st.session_state.result_data
    if not result:
        return

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
            f'<span class="stat-badge">🆔 {result.get("run_id", "")}</span>',
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

def main():
    style, content_type, humanize, with_images, stop_at = render_sidebar()

    # ── Track 1：顶部 Tab 三分（运行监控 / 成果展示 / 配置） ──
    tab_monitor, tab_results, tab_config = st.tabs(
        ["🚀 运行监控", "📄 成果展示", "⚙️ 配置"]
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
                    # 初始化运行状态
                    st.session_state.is_running = True
                    st.session_state.pipeline_done = False
                    st.session_state.pipeline_error = None
                    st.session_state.logs = []
                    st.session_state.stage_event = threading.Event()   # 分步控制器
                    st.session_state.awaiting_next = False

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
                            if not st.session_state.pipeline_error:
                                st.session_state.pipeline_error = f"致命错误({type(e).__name__}): {e}"
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
        if st.session_state.is_running and not st.session_state.pipeline_done:
            @st.fragment(run_every=3)
            def _live_logs():
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
                            st.session_state.stage_event.set()
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

    with tab_results:
        render_results()

    with tab_config:
        render_config_panel()


if __name__ == "__main__":
    main()
