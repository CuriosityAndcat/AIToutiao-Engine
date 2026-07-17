# 阶段6：上传今日头条草稿 — 规划方案 [NEXUS-Sprint]

> 创建：2026-07-17 | 项目经理 | 纯方案，不执行

## 需求摘要

**原始需求**：在配图(S4)→组装(S5)完成后，增加阶段6——将完整稿件（含封面）上传为今日头条草稿（不自动发布）。

**模式判定**：[NEXUS-Sprint] — 功能级 MVP：新增阶段 + 进度条 + UI配置 + 测试入口

**现有能力**：`publisher_service.py` 已完整实现 Playwright 浏览器自动化发布（标题填写、正文注入、封面上传、草稿自动保存、发布按钮点击），`publish_article(auto_publish=False)` 即可实现「填内容+存草稿但不发布」。

---

## 现状分析

### 阶段体系（现有5阶段）
```
S1 下载 → S2 转录 → S3 研究写作 → S4 配图 → S5 组装
stages = [
    ("download",         "下载",     step_download),
    ("transcribe",       "转录",     step_transcribe),
    ("write",            "研究写作",  _run_research_and_write),
    ("generate_images",  "配图",     step_images),
    ("assemble",         "组装",     step_assemble),
    # ← S6 插入此处
]
```

### publisher_service.py 能力矩阵
| 能力 | 函数 | 状态 |
|---|---|---|
| 登录状态检查 | `check_login_status()` | ✅ 已实现 |
| 扫码登录 | `launch_login_browser()` | ✅ 已实现 |
| 标题填写 | `publish_article()` 内 | ✅ |
| 正文注入（MD→HTML） | `publish_article()` 内 `ProseMirror` | ✅ |
| 封面上传 | `publish_article()` 内 | ✅ |
| 草稿自动保存 | 编辑器自动触发 + 循环检测 toast | ✅ |
| 点击发布 | `_click_publish_buttons()` | ✅ |
| dry_run 模式 | `dry_run=True` | ✅ |
| Cookie 持久化 | `BrowserFactory._inject_cookies()` | ✅ |

**关键发现**：`publish_article(auto_publish=False)` 会执行「填标题→填正文→上传封面→等待草稿保存」完整流程，但**不点击发布按钮**。这正是"上传草稿"所需的行为。

---

## 设计方案

### 新增阶段定义

```python
# engine_app.py

def step_publish_draft(state: PipelineState) -> bool:
    """阶段6：将完整稿件上传为今日头条草稿（不自动发布）。"""
    from publisher_service import publish_article, check_login_status, launch_login_browser

    set_stage("发布草稿", "running")
    add_log("阶段6/6: 上传今日头条草稿", "stage")

    # 1. 检查登录状态
    login_status = check_login_status()
    if not login_status.get("authenticated"):
        add_log("未登录今日头条，请先在配置面板登录", "warning")
        set_stage("发布草稿", "failed")
        return False

    # 2. 读取 S5 产出
    assembled_file = state.run_dir / "完整稿件_配图版.md"
    if not assembled_file.exists():
        add_log("未找到组装后的稿件，请先完成阶段5", "error")
        set_stage("发布草稿", "failed")
        return False

    content = assembled_file.read_text(encoding="utf-8")
    title = state.outputs.get("generated_title", "")
    cover_path = state.outputs.get("cover_image", "")

    # 3. 上传草稿（auto_publish=False → 仅填内容不点发布）
    log_sink.set_progress(_PROGRESS_MAP["publish_start"])
    result = publish_article(
        title=title,
        content=content,
        cover_path=cover_path if Path(cover_path).exists() else None,
        auto_publish=False,
        headless=False,   # 草稿上传建议非headless，避免反爬
    )

    if result.get("success"):
        add_log("草稿已上传今日头条，请到 mp.toutiao.com 查看", "success")
        set_stage("发布草稿", "done")
        state.mark_done("publish_draft")
        return True
    else:
        add_log(f"草稿上传失败: {result.get('message', '未知错误')}", "error")
        set_stage("发布草稿", "failed")
        return False
```

### 改动清单（7 处）

| # | 文件 | 改动 | 行数 |
|---|------|------|------|
| 1 | `engine_app.py` | 新增 `step_publish_draft()` 函数 | ~50 行 |
| 2 | `engine_app.py` | `_PROGRESS_MAP` 新增 `publish_start:0.82` `publish_done:0.92` | +2 行 |
| 3 | `engine_app.py` | `execute_pipeline()` 的 `stages` 列表追加新阶段 | +1 行 |
| 4 | `engine_app.py` | 日志文案："阶段5/5"→"阶段5/6"（所有阶段编号文案需review） | ~5 处 |
| 5 | `engine_app.py` | UI 配置面板：新增"上传草稿"checkbox（默认勾选） | +3 行 |
| 6 | `engine_app.py` | `PipelineState.__init__` 新增 `upload_draft: bool` 参数 | +3 行 |
| 7 | `tests/run_stage.py` | 新增 `--stage 6` 入口：`step_publish_draft` | ~10 行 |

### 进度条分配（调整后）

```
S1 下载:        0.05 → 0.17
S2 转录:        0.18 → 0.28
S3 研究写作:    0.30 → 0.57
S4 配图:        0.58 → 0.67
S5 组装:        0.70 → 0.80
S6 发布草稿:    0.82 → 0.92    ← 新增
完成:           1.00
```

### UI 配置面板

在现有「配图生成」checkbox 下方新增：

```
☑ 上传今日头条草稿 (阶段6)
   （勾选后自动将完整稿件+封面填充到头条编辑器并保存草稿，不发布）
```

### 登出/登录流程

1. 首次使用：用户需在配置面板点击「登录今日头条」→ 弹浏览器扫码 → 登录状态持久化到 `data/browser_state/`
2. 之后每次 S6 自动检测登录有效性，过期则提示重新登录
3. 现有 `check_login_status()` + `launch_login_browser()` 已覆盖

---

## 风险与边界

| 风险 | 缓解 |
|---|---|
| 头条反爬升级 | 已有反检测参数（`--disable-blink-features`、自定义 UA），Playwright 浏览器仿真度高 |
| 登录态过期 | `check_login_status()` 自动检测，S6 前置拦截 |
| headless 模式被封 | S6 强制 `headless=False`（可看到浏览器操作过程） |
| 编辑器 DOM 变更 | selector 在 `publisher_service.py` 中集中管理，单点维护 |
| 已有用户习惯 | S6 可通过 UI checkbox 关闭，不影响只想跑 S1-S5 的用户 |

### 不在此方案范围（明确排除）

- ❌ 不自动发布（用户要求"草稿"）
- ❌ 不改 `publisher_service.py` 核心逻辑（已有能力完全满足）
- ❌ 不接入微信公众号（本次仅头条）
- ❌ 不批量发布（单篇上传）

---

## 执行顺序

```
1. 新增 step_publish_draft() → 2. 更新 _PROGRESS_MAP
    → 3. 更新 stages 列表 → 4. 更新阶段编号文案
    → 5. 更新 UI 配置面板 → 6. 更新 PipelineState
    → 7. 更新 tests/run_stage.py
```
