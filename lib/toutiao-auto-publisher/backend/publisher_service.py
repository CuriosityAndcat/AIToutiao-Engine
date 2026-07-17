"""
发布服务模块 — 今日头条浏览器自动化发布
基于 Playwright 实现，不依赖外部脚本模块
"""
import time
import os
import sys
import json
import re
import random
import subprocess
import platform as _platform
from pathlib import Path
from typing import Optional, Dict, Any, List

from patchright.sync_api import sync_playwright, Playwright, BrowserContext, Page

# ===== 配置常量 =====
TOUTIAO_LOGIN_URL = "https://mp.toutiao.com/auth/page/login"
TOUTIAO_PUBLISH_URL = "https://mp.toutiao.com/profile_v4/graphic/publish"
TOUTIAO_HOME_URL = "https://mp.toutiao.com/"

# 路径配置
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
BROWSER_STATE_DIR = DATA_DIR / "browser_state"
BROWSER_PROFILE_DIR = BROWSER_STATE_DIR / "browser_profile"
STATE_FILE = BROWSER_STATE_DIR / "state.json"
AUTH_INFO_FILE = DATA_DIR / "auth_info.json"

# 浏览器参数
BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--no-first-run",
    "--no-default-browser-check",
]
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
BROWSER_STATE_DIR.mkdir(parents=True, exist_ok=True)


# ===== 浏览器工厂 =====
class BrowserFactory:
    """工厂类：创建配置好的浏览器上下文（反检测）"""

    @staticmethod
    def launch_persistent_context(
        playwright: Playwright,
        headless: bool = True,
        user_data_dir: str = str(BROWSER_PROFILE_DIR),
    ) -> BrowserContext:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="chrome",
            headless=headless,
            no_viewport=True,
            ignore_default_args=["--enable-automation"],
            user_agent=USER_AGENT,
            args=BROWSER_ARGS,
        )
        # Cookie 注入（解决 Playwright session cookie 持久化 bug）
        BrowserFactory._inject_cookies(context)
        return context

    @staticmethod
    def _inject_cookies(context: BrowserContext):
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r") as f:
                    state = json.load(f)
                    if "cookies" in state and len(state["cookies"]) > 0:
                        context.add_cookies(state["cookies"])
            except Exception as e:
                print(f"  ⚠️ Cookie 注入失败：{e}")


# ===== 认证管理器 =====
class AuthManager:
    """管理今日头条登录认证"""

    def __init__(self):
        self.state_file = STATE_FILE
        self.auth_info_file = AUTH_INFO_FILE
        self.browser_state_dir = BROWSER_STATE_DIR

    def is_authenticated(self) -> bool:
        return self.state_file.exists()

    def get_auth_info(self) -> Dict[str, Any]:
        info = {
            "authenticated": self.is_authenticated(),
            "state_exists": self.state_file.exists(),
        }
        if self.auth_info_file.exists():
            try:
                with open(self.auth_info_file, "r") as f:
                    info.update(json.load(f))
            except Exception:
                pass
        if info["state_exists"]:
            age_hours = (time.time() - self.state_file.stat().st_mtime) / 3600
            info["state_age_hours"] = round(age_hours, 1)
        return info

    def setup_auth(self, headless: bool = False, timeout_minutes: int = 10) -> bool:
        """打开浏览器让用户扫码登录"""
        print("🔐 启动登录流程...")
        try:
            with sync_playwright() as p:
                context = BrowserFactory.launch_persistent_context(p, headless=headless)
                page = context.new_page()
                page.goto(TOUTIAO_LOGIN_URL, wait_until="domcontentloaded")

                # 检查是否已登录
                if ("mp.toutiao.com" in page.url and
                        "auth/page/login" not in page.url):
                    print("  ✅ 已登录！")
                    self._save_browser_state(context)
                    self._save_auth_info()
                    context.close()
                    return True

                print("  ⏳ 请扫码登录...")
                start_time = time.time()
                while time.time() - start_time < (timeout_minutes * 60):
                    for p in context.pages:
                        try:
                            url = p.url
                            # 跳过 SSO 中转页（正在跳转中，不算失败也不算成功）
                            if "sso.toutiao.com" in url:
                                continue
                            # ── URL 检测 ──
                            if ("profile_v4" in url or
                                    ("mp.toutiao.com" in url and "auth/page/login" not in url)):
                                print("  ✅ 登录成功！(URL)")
                                time.sleep(2)
                                self._save_browser_state(context)
                                self._save_auth_info()
                                context.close()
                                return True
                            # ── DOM 检测兜底（页面已显示发布入口但 URL 未命中模式）──
                            try:
                                body = p.evaluate("document.body.innerText")
                                if isinstance(body, str) and len(body) > 100:
                                    has_publish = "发布" in body
                                    has_login_form = "登录" in body or "扫码" in body
                                    has_user_menu = ("内容管理" in body or
                                                     "数据统计" in body or
                                                     "创作中心" in body)
                                    if (has_publish or has_user_menu) and not has_login_form:
                                        print("  ✅ 登录成功！(DOM)")
                                        time.sleep(2)
                                        self._save_browser_state(context)
                                        self._save_auth_info()
                                        context.close()
                                        return True
                            except Exception:
                                pass
                        except Exception:
                            continue
                    time.sleep(1)

                print("  ❌ 登录超时")
                context.close()
                return False
        except Exception as e:
            print(f"  ❌ 登录失败：{e}")
            return False

    def _save_browser_state(self, context: BrowserContext):
        try:
            context.storage_state(path=str(self.state_file))
            print(f"  💾 登录状态已保存：{self.state_file}")
        except Exception as e:
            print(f"  ❌ 保存状态失败：{e}")

    def _save_auth_info(self):
        try:
            info = {
                "authenticated_at": time.time(),
                "authenticated_at_iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            with open(self.auth_info_file, "w") as f:
                json.dump(info, f, indent=2)
        except Exception:
            pass

    def clear_auth(self) -> bool:
        try:
            if self.state_file.exists():
                self.state_file.unlink()
            if self.auth_info_file.exists():
                self.auth_info_file.unlink()
            if self.browser_state_dir.exists():
                import shutil
                shutil.rmtree(self.browser_state_dir)
                self.browser_state_dir.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"  ❌ 清除认证失败：{e}")
            return False


# ===== Markdown 转 HTML（含图片→占位符） =====

IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def _resolve_image_path(raw_path: str, base_dir: str = None) -> str:
    """将 markdown 图片路径解析为绝对路径。"""
    cleaned = raw_path.strip().strip("<>").strip("\"'")
    if cleaned.startswith(("http://", "https://", "data:")):
        return cleaned
    base = Path(base_dir or ".")
    image_path = Path(cleaned)
    if not image_path.is_absolute():
        image_path = base / image_path
    return str(image_path.resolve())


def convert_with_images(text: str, base_dir: str = None) -> tuple:
    """
    将 Markdown 转为 HTML（兼容头条 ProseMirror），并提取正文中的图片。

    图片 `![alt](path)` 被替换为占位符 TTIMGPH_N，后续通过剪贴板粘贴还原。

    Returns:
        (html: str, images: list[dict{placeholder, path, alt}])
    """
    images = []
    lines = []
    in_code_block = False

    for line in text.split("\n"):
        stripped = line.strip()

        # 代码块
        if stripped.startswith("```"):
            if in_code_block:
                lines.append("</code></pre>")
                in_code_block = False
            else:
                lines.append("<pre><code>")
                in_code_block = True
            continue
        if in_code_block:
            import html as _html
            lines.append(f"{_html.escape(line)}<br>")
            continue

        # 图片 → 占位符
        line = IMAGE_PATTERN.sub(
            lambda m: _make_image_placeholder(m, images, base_dir), line
        )
        stripped = line.strip()

        # 标题
        if line.startswith("#"):
            level = min(len(line.split()[0]), 6)
            content_text = line[level:].strip()
            lines.append(f"<h{level}>{content_text}</h{level}>")
            continue

        # 列表
        if stripped.startswith("* ") or stripped.startswith("- "):
            content_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", stripped[2:])
            lines.append(f"<li>{content_text}</li>")
            continue

        # 段落
        if stripped:
            line_content = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", stripped)
            lines.append(f"<p>{line_content}</p>")

    return "\n".join(lines), images


def _make_image_placeholder(match, images: list, base_dir: str = None) -> str:
    """生成唯一占位符并记录图片信息。"""
    placeholder = f"TTIMGPH_{len(images)}"
    images.append({
        "placeholder": placeholder,
        "path": _resolve_image_path(match.group(2), base_dir),
        "alt": match.group(1).strip(),
    })
    return placeholder


def convert_markdown_to_html(text: str) -> str:
    """兼容旧接口：纯 HTML 转换（无图片处理）。"""
    return convert_with_images(text)[0]


# ===== 发布核心逻辑 =====
def _copy_image_to_clipboard(image_path: str) -> bool:
    """Windows 下将图片复制到剪贴板"""
    system = _platform.system()
    image_path = str(Path(image_path).resolve())

    if system == "Windows":
        escaped = image_path.replace("'", "''")
        ps = (
            "Add-Type -AssemblyName System.Windows.Forms;"
            "Add-Type -AssemblyName System.Drawing;"
            f"$img = [System.Drawing.Image]::FromFile('{escaped}');"
            "[System.Windows.Forms.Clipboard]::SetImage($img);"
            "$img.Dispose()"
        )
        result = os.system(f'powershell.exe -NoProfile -Sta -Command "{ps}"')
        return result == 0
    return False


def _paste_from_clipboard(page: Page) -> bool:
    """模拟 Ctrl+V 粘贴剪贴板内容到编辑器。"""
    try:
        page.keyboard.press("Control+V")
        return True
    except Exception as e:
        print(f"  ⚠️ Paste failed: {e}")
        return False


def _select_placeholder(page: Page, placeholder: str, retries: int = 3) -> bool:
    """在 ProseMirror 编辑器中选中占位符文本。"""
    for attempt in range(1, retries + 1):
        selected = page.evaluate(
            """(placeholder) => {
            const editor = document.querySelector('.ProseMirror');
            if (!editor) return false;
            const walker = document.createTreeWalker(editor, NodeFilter.SHOW_TEXT);
            let node;
            while ((node = walker.nextNode())) {
                const text = node.textContent || '';
                const idx = text.indexOf(placeholder);
                if (idx !== -1) {
                    node.parentElement?.scrollIntoView({ block: 'center' });
                    const range = document.createRange();
                    range.setStart(node, idx);
                    range.setEnd(node, idx + placeholder.length);
                    const selection = window.getSelection();
                    selection.removeAllRanges();
                    selection.addRange(range);
                    editor.focus();
                    return true;
                }
            }
            return false;
        }""",
            placeholder,
        )
        if selected:
            selected_text = page.evaluate("window.getSelection()?.toString() || ''")
            if selected_text.strip() == placeholder:
                return True
        if attempt < retries:
            time.sleep(0.5)
    return False


def _insert_content_images(page: Page, images: list) -> bool:
    """将占位符逐一替换为剪贴板粘贴的实际图片。

    三层加固：
    1. 增量计数检测 — 粘贴前记录 img 数量，粘贴后验证数量 +1
    2. 3 次粘贴重试 — 递增 backoff (2s/4s/6s)
    3. 占位符恢复 — 全部重试失败后在光标位置恢复占位符文本
    """
    if not images:
        return True

    MAX_RETRIES = 3
    RETRY_BACKOFFS = [2, 4, 6]

    print(f"🖼️ 插入 {len(images)} 张正文图片...")
    success = True

    for index, img in enumerate(images, start=1):
        placeholder = img["placeholder"]
        image_path = img["path"]
        print(f"  [{index}/{len(images)}] 替换 {placeholder}...")

        if image_path.startswith(("http://", "https://", "data:")):
            print(f"  ⚠️ 跳过非本地图片: {image_path}")
            success = False
            continue

        if not os.path.exists(image_path):
            print(f"  ⚠️ 图片文件不存在: {image_path}")
            success = False
            continue

        # ── 记录粘贴前图片数量（增量检测基准）──
        img_count_before = page.locator(".ProseMirror img").count()

        if not _copy_image_to_clipboard(image_path):
            print("  ⚠️ 复制到剪贴板失败")
            success = False
            continue

        if not _select_placeholder(page, placeholder):
            print(f"  ⚠️ 无法选中占位符: {placeholder}")
            success = False
            continue

        # ── 粘贴 + 增量检测 + 重试循环 ──
        inserted = False
        for retry in range(MAX_RETRIES):
            if retry == 0:
                # 首次：删除占位符 → 粘贴
                page.keyboard.press("Backspace")
                time.sleep(0.3)
            else:
                # 重试：重新聚焦编辑器 → 重新粘贴
                print(f"    🔄 重试 {retry}/{MAX_RETRIES}...")
                page.locator(".ProseMirror").first.click()
                time.sleep(0.5)

            _paste_from_clipboard(page)
            backoff = RETRY_BACKOFFS[retry]

            # 增量检测：等待 img 数量增加
            start = time.time()
            while time.time() - start < backoff:
                if page.locator(".ProseMirror img").count() > img_count_before:
                    inserted = True
                    break
                time.sleep(0.5)

            if inserted:
                break

        if inserted:
            print("  ✅ 图片已插入")
            # 轮询等待自动保存完成，避免下一张图操作与本次保存竞态冲突
            save_ok = False
            for _ in range(15):
                try:
                    if page.get_by_text("草稿已保存").is_visible():
                        print("    ✅ 草稿已保存")
                        save_ok = True
                        break
                except:
                    pass
                time.sleep(1)
            if save_ok:
                time.sleep(1)   # 保存完成后额外等 1 秒确保落盘
            else:
                print("    ⚠️ 未检测到草稿保存，继续下一张...")
                time.sleep(3)   # 降级盲等
        else:
            print("  ⚠️ 图片插入失败（3 次重试耗尽），恢复占位符")
            # 在光标位置恢复占位符，避免段落丢失
            page.evaluate(
                """(placeholder) => {
                    const editor = document.querySelector('.ProseMirror');
                    if (editor) {
                        editor.focus();
                        document.execCommand('insertText', false, placeholder);
                    }
                }""",
                placeholder,
            )
            success = False
            time.sleep(1)

    # 检查残留占位符
    remaining = page.evaluate(
        """() => {
        const text = document.querySelector('.ProseMirror')?.innerText || '';
        return Array.from(text.matchAll(/TTIMGPH_\\d+/g)).map(m => m[0]);
    }"""
    )
    if remaining:
        print(f"  ⚠️ 残留占位符: {', '.join(remaining)}")
        success = False

    return success


def _select_single_cover_mode(page: Page) -> bool:
    """将封面模式设为单图（头条检测到正文≥3张图时默认是"三图"）。

    封面图已在正文中（TTIMGPH_0 已粘贴的首张图），切换模式后头条自动取正文首图。

    三层策略：
    Layer 1: 精确 JS 定位 — 枚举所有"单图"文本节点，筛选在可见可交互容器中的、最像选项的那个，再验证
    Layer 2: UI 点击展开面板后重试 Layer 1
    Layer 3: TreeWalker 兜底
    """
    def _click_single_js(page) -> bool:
        """JS 精确定位"单图"选项：在 cover 相关容器内、非 hidden、优先找 radio/tab 样式元素。"""
        return page.evaluate("""() => {
            const candidates = [];

            // 收集所有包含"单图"文本的叶子节点
            const walker = document.createTreeWalker(document.body, 4);
            let node;
            while (node = walker.nextNode()) {
                if (node.textContent?.trim() === '单图' && node.parentElement?.offsetParent) {
                    const p = node.parentElement;
                    // 优先：父级是 label/span/div 且不在隐藏区域
                    const rect = p.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        // 得分：越靠近含有 cover/封面 class 的祖先越高分
                        let score = 0;
                        let el = p;
                        for (let i = 0; i < 5 && el; i++) {
                            const cls = (el.className || '') + (el.id || '');
                            if (/cover|封面/i.test(cls)) score += 3;
                            if (/tab|option|radio|switch|select/i.test(cls)) score += 2;
                            if (/label|wrap|item/i.test(cls)) score += 1;
                            el = el.parentElement;
                        }
                        // 附近有三图/自动字样的加分（封面选择器区域特征）
                        const nearText = (p.parentElement?.textContent || '') + (p.textContent || '');
                        if (/三图/.test(nearText) && /自动/.test(nearText)) score += 3;
                        candidates.push({ el: p, score, rect });
                    }
                }
            }

            if (candidates.length === 0) return 'not_found';

            // 按得分降序，选最佳候选
            candidates.sort((a, b) => b.score - a.score);
            const best = candidates[0];

            // 验证：检查被点击元素是否是 disabled/hidden
            if (best.el.disabled || best.el.style.display === 'none' || best.el.getAttribute('aria-disabled') === 'true') {
                return 'disabled';
            }

            // 确保在视口内
            best.el.scrollIntoView({ behavior: 'instant', block: 'center' });
            // 触发鼠标/点击事件
            best.el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
            best.el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
            best.el.click();
            return 'clicked_' + best.score;
        }""")

    try:
        # ── Layer 1: JS 精确定位 ──
        result = _click_single_js(page)
        if result and result.startswith('clicked'):
            time.sleep(0.8)
            # 验证：检查页面上是否出现"单图"被选中的 UI 特征
            # 三图面板应该消失或折叠，单图应高亮
            print(f"  ✅ 封面模式已切换为：单图（JS 精确定位，score={result.split('_')[1]}）")
            return True

        # ── Layer 2: 点击封面区域展开面板后重试 ──
        for cover_sel in [
            "div.article-cover-add",
            "div.article-cover-pic",
            "div.cover-wrapper",
            "div.article-cover",
        ]:
            try:
                el = page.locator(cover_sel).first
                if el.is_visible(timeout=1000):
                    el.click()
                    time.sleep(1.2)
                    break
            except:
                continue
        else:
            # 选择器不可见，尝试文本匹配
            for txt in ["封面", "添加封面", "设置封面"]:
                try:
                    btn = page.locator(f"text={txt}").first
                    if btn.is_visible(timeout=1000):
                        btn.click()
                        time.sleep(1.2)
                        break
                except:
                    continue

        # 重试 JS 定位
        result = _click_single_js(page)
        if result and result.startswith('clicked'):
            time.sleep(0.8)
            print(f"  ✅ 封面模式已切换为：单图（展开后 JS 定位）")
            return True

        # ── Layer 3: TreeWalker 兜底（仅选在 cover 容器内的"单图"）──
        clicked = page.evaluate("""() => {
            const walker = document.createTreeWalker(document.body, 4);
            let node;
            while (node = walker.nextNode()) {
                const t = node.textContent?.trim() || '';
                if (t === '单图' && node.parentElement?.offsetParent) {
                    const p = node.parentElement;
                    // 仅当父级附近有三图/自动字样时才视为有效选项
                    const ctx = (p.parentElement?.textContent || '') + (p.textContent || '');
                    if (/三图/.test(ctx) || /封面/.test(ctx) || /cover/i.test(ctx)) {
                        p.scrollIntoView({ block: 'center' });
                        p.click();
                        return true;
                    }
                }
            }
            // 没有带上下文限制的单图，退而求其次
            const walker2 = document.createTreeWalker(document.body, 4);
            let node2;
            while (node2 = walker2.nextNode()) {
                if (node2.textContent?.trim() === '单图' && node2.parentElement?.offsetParent) {
                    node2.parentElement.scrollIntoView({ block: 'center' });
                    node2.parentElement.click();
                    return 'fallback';
                }
            }
            return false;
        }""")
        if clicked:
            print("  ✅ 封面模式已切换为：单图（TreeWalker 带上下文过滤）" if clicked is True else "  ⚠️ 单图已点击（无上下文限制降级）")
            time.sleep(0.5)
            return True

        print("  ⚠️ 未找到单图选项（可能已是单图）")
        return True
    except Exception as e:
        print(f"  ⚠️ 封面模式设置异常: {e}")
        return True


def _set_location(page: Page, location: str = "上海") -> bool:
    """设置文章位置为指定城市（三层降级定位）。"""
    try:
        # Layer 1: 已知选择器
        for sel in [
            "div.location-selector input",
            "div.article-location input",
            "input[placeholder*=位置]",
            "div.location-picker",
            "div.location-trigger",
        ]:
            el = page.locator(sel).first
            if el.is_visible(timeout=1500):
                el.click()
                time.sleep(0.5)
                # 搜索框输入后选第一个结果
                search_input = page.locator("input[placeholder*=搜索]").first
                if search_input.is_visible(timeout=2000):
                    search_input.fill(location)
                    time.sleep(0.8)
                    # 点击搜索结果
                    result_option = page.locator(f"text={location}").first
                    if result_option.is_visible(timeout=2000):
                        result_option.click()
                        time.sleep(0.3)
                        print(f"  ✅ 位置已设为：{location}")
                        return True
                # 如果无搜索框，直接选可见选项
                location_opt = page.locator(f"text={location}").first
                if location_opt.is_visible(timeout=2000):
                    location_opt.click()
                    time.sleep(0.3)
                    print(f"  ✅ 位置已设为：{location}")
                    return True

        # Layer 2: 文本匹配"添加位置"
        for label_text in ["添加位置", "选择位置", "所在位置"]:
            btn = page.locator(f"text={label_text}").first
            if btn.is_visible(timeout=1500):
                btn.click()
                time.sleep(0.5)
                # 搜索输入
                search_input = page.locator("input[placeholder*=搜索]").first
                if search_input.is_visible(timeout=2000):
                    search_input.fill(location)
                    time.sleep(0.8)
                    result_option = page.locator(f"text={location}").first
                    if result_option.is_visible(timeout=2000):
                        result_option.click()
                        time.sleep(0.3)
                        print(f"  ✅ 位置已设为：{location}")
                        return True

        # Layer 3: TreeWalker 兜底
        clicked = page.evaluate("""(loc) => {
            // 找 "添加位置" 按钮
            const walker = document.createTreeWalker(document.body, 4);
            let node;
            while (node = walker.nextNode()) {
                const t = node.textContent?.trim() || '';
                if (t === '添加位置' || t === '选择位置' || t === '所在位置') {
                    node.parentElement?.click();
                    return 'clicked';
                }
            }
            return 'not_found';
        }""", location)
        if clicked == 'clicked':
            time.sleep(0.8)
            # 尝试键盘输入后回车
            focused = page.evaluate("document.activeElement?.tagName || ''")
            if focused in ('INPUT', 'TEXTAREA'):
                page.keyboard.type(location)
                time.sleep(0.5)
                page.keyboard.press("Enter")
            print(f"  ⚠️ TreeWalker 点击了位置按钮，尝试输入 {location}")
            return True

        print("  ⚠️ 未找到位置设置项")
        return True
    except Exception as e:
        print(f"  ⚠️ 位置设置失败: {e}")
        return True


def _enable_ad_monetization(page: Page) -> bool:
    """开启投放广告赚收益（三层降级）。"""
    try:
        # Layer 1: 已知选择器
        for sel in [
            "div.switch-wrap",
            "div.ad-switch",
            "span.switch",
            "div.byte-switch",
            "label.byte-switch",
        ]:
            el = page.locator(sel).first
            if el.is_visible(timeout=1500):
                el.click()
                time.sleep(0.3)
                print("  ✅ 已开启：投放广告赚收益")
                return True

        # Layer 2: 文本匹配"投放广告"附近
        ad_label = page.locator("text=投放广告").first
        if ad_label.is_visible(timeout=2000):
            # 点击标签或其相邻开关
            ad_label.click()
            time.sleep(0.3)
            # 尝试找附近的 switch/checkbox
            nearby = page.locator("text=投放广告").first
            parent = nearby.locator("xpath=..")
            switch = parent.locator("div.switch, span.switch, input[type=checkbox]").first
            if switch.is_visible(timeout=1000):
                switch.click()
                time.sleep(0.3)
            print("  ✅ 已开启：投放广告赚收益")
            return True

        # Layer 2b: 完整文案
        for text in ["投放广告赚收益", "投放广告", "广告分成"]:
            el = page.locator(f"text={text}").first
            if el.is_visible(timeout=1000):
                el.click()
                time.sleep(0.3)
                print(f"  ✅ 已开启：{text}")
                return True

        # Layer 3: TreeWalker 兜底 — 找包含"广告"的开关
        toggled = page.evaluate("""() => {
            const walker = document.createTreeWalker(document.body, 4);
            let node;
            while (node = walker.nextNode()) {
                const t = node.textContent?.trim() || '';
                if (t.includes('广告') && t.includes('收益')) {
                    // 点击附近的 switch/checkbox
                    const p = node.parentElement;
                    if (!p) continue;
                    const sw = p.querySelector('.switch, .byte-switch, [class*=switch], input[type=checkbox]');
                    if (sw) { sw.click(); return true; }
                    // 否则点击文本所在容器
                    p.click();
                    return true;
                }
            }
            return false;
        }""")
        if toggled:
            print("  ✅ 已开启：投放广告赚收益（TreeWalker）")
            time.sleep(0.3)
            return True

        print("  ⚠️ 未找到广告收益开关")
        return True
    except Exception as e:
        print(f"  ⚠️ 广告收益设置失败: {e}")
        return True


def _set_toutiao_original(page: Page) -> bool:
    """声明为头条首发（三层降级）。"""
    try:
        # Layer 1: 文本精确匹配 "头条首发"
        for text in ["头条首发", "头条首发（推荐）"]:
            tab = page.locator(f"text={text}").first
            if tab.is_visible(timeout=2000):
                tab.click()
                time.sleep(0.3)
                print(f"  ✅ 已声明：{text}")
                return True

        # Layer 1b: 查找声明区域中的 radio/option
        for sel in [
            "div.original-declare input[type=radio]",
            "div.declare-radio input",
            "div.article-original input",
            "div.original-option",
        ]:
            radios = page.locator(sel)
            count = radios.count()
            if count > 0:
                # 第一个 radio 通常是"头条首发"
                radios.first.click()
                time.sleep(0.3)
                print("  ✅ 已声明：头条首发（radio 选择器）")
                return True

        # Layer 2: 查找声明/原创区域
        for label_text in ["声明", "原创声明", "收费声明"]:
            section = page.locator(f"text={label_text}").first
            if section.is_visible(timeout=1500):
                parent = section.locator("xpath=..")
                # 在该区域内找所有可选选项，选第一个（头条首发）
                options = parent.locator("label, div.option, span.option, div.radio-item")
                if options.count() > 0:
                    options.first.click()
                    time.sleep(0.3)
                    print("  ✅ 已声明：头条首发（声明区域选项）")
                    return True

        # Layer 3: TreeWalker 兜底
        clicked = page.evaluate("""() => {
            const walker = document.createTreeWalker(document.body, 4);
            let node;
            while (node = walker.nextNode()) {
                const t = node.textContent?.trim() || '';
                if (t === '头条首发' && node.parentElement?.offsetParent) {
                    // 确保点击的是可交互元素（不是被 disabled 的）
                    const target = node.parentElement.querySelector('input, label, span, div') || node.parentElement;
                    target.click();
                    return true;
                }
            }
            return false;
        }""")
        if clicked:
            print("  ✅ 已声明：头条首发（TreeWalker）")
            time.sleep(0.3)
            return True

        print("  ⚠️ 未找到头条首发选项")
        return True
    except Exception as e:
        print(f"  ⚠️ 头条首发设置失败: {e}")
        return True


def _click_publish_buttons(page: Page) -> bool:
    """点击发布按钮的两步流程"""
    try:
        # Step 1: 点击"预览并发布"
        initial_btn = page.locator("button").filter(has_text="预览并发布").last
        if not initial_btn.is_visible():
            initial_btn = page.locator("button").filter(has_text="发布").last

        if initial_btn.is_visible() and initial_btn.is_enabled():
            initial_btn.click()
            print("  ✅ 初始发布按钮已点击")
        else:
            page.evaluate("document.querySelector('.publish-btn')?.click()")

        time.sleep(8)

        # Step 2: 点击最终确认按钮
        final_btn = page.locator(".publish-btn-last").first
        if final_btn.is_visible():
            final_btn.click()
        else:
            modal_confirm = (
                page.locator(".byte-modal .byte-btn-primary")
                .filter(has_text="确定")
                .or_(page.locator(".byte-modal .byte-btn-primary").filter(has_text="确认发布"))
                .last
            )
            if modal_confirm.is_visible():
                modal_confirm.click()

        time.sleep(5)

        # 检查成功提示
        for text in ["发布成功", "主页查看", "已发布"]:
            try:
                if page.get_by_text(text).is_visible():
                    print(f"  ✨ 发布成功！找到提示：{text}")
                    return True
            except:
                pass
        return True
    except Exception as e:
        print(f"  ❌ 发布按钮点击失败：{e}")
        return False


def publish_article(
    title: str,
    content: str,
    cover_path: Optional[str] = None,
    content_base_dir: Optional[str] = None,
    headless: bool = False,
) -> Dict[str, Any]:
    """
    填写内容到今日头条编辑器（插入封面+内文图后关闭页面，不点击发布）

    Args:
        title: 文章标题（2-30字）
        content: 文章内容（支持 Markdown）
        cover_path: 封面图片路径
        headless: 是否无头模式

    Returns:
        dict: {"success": bool, "message": str}
    """
    result = {"success": False, "message": ""}

    # 标题长度处理
    if title and len(title) > 30:
        title = title[:30]
    if title and len(title) < 2:
        title = f"{title}..."

    # ── 预处理：从 markdown 提取标题（如未提供）──
    title = title or ""
    if not title:
        title_match = re.match(r'^#\s+(.+?)(?:\n|$)', content)
        if title_match:
            title = title_match.group(1).strip()
            print(f"  📌 从 markdown 提取标题：{title[:30]}...")
    # 剥离正文首行 # 标题（避免与 title 字段重复）
    content = re.sub(r'^#\s+.+?\n', '', content, count=1)

    # ── Markdown 转 HTML（含图片→占位符提取）──
    print("🔄 转换内容格式...")
    content_html, content_images = convert_with_images(content, base_dir=content_base_dir)
    if content_images:
        print(f"  📸 检测到 {len(content_images)} 张正文图片")

    print(f"🚀 启动浏览器（Headless: {headless}）...")

    with sync_playwright() as p:
        context = BrowserFactory.launch_persistent_context(p, headless=headless)
        page = context.pages[0] if context.pages else context.new_page()

        try:
            # 导航到发布页面
            print(f"🌐 正在访问发布页面...")
            try:
                page.goto(TOUTIAO_PUBLISH_URL, timeout=60000)
                page.wait_for_load_state("domcontentloaded")
            except Exception as e:
                print(f"  ⚠️ 导航警告：{e}")

            # 检查登录状态
            if "auth/page/login" in page.url or "sso.toutiao.com" in page.url:
                result["message"] = "未登录或登录已过期，请先登录"
                print("  ❌ 需要登录")
                return result

            print("  ✅ 发布页面已加载")
            time.sleep(3)

            # 处理遮罩层
            for sel in [".byte-drawer-mask", ".ai-assistant-drawer", ".byte-modal-mask"]:
                try:
                    if page.locator(sel).is_visible():
                        page.evaluate(f"document.querySelector('{sel}')?.remove()")
                except:
                    pass

            # 1. 填写标题
            if title:
                print(f"  ✍️ 填写标题：{title[:20]}...")
                try:
                    title_input = page.locator("textarea").first
                    if title_input.count() > 0:
                        title_input.fill(title)
                    else:
                        page.get_by_placeholder("标题", exact=False).first.fill(title)
                    print("    标题填写完成")
                except Exception as e:
                    print(f"  ⚠️ 标题填写失败：{e}")

            # 2. 填写正文
            print("  📝 填写正文内容...")
            try:
                page.wait_for_selector(".ProseMirror", timeout=5000)
            except:
                pass

            editor = page.locator(".ProseMirror").first
            if editor.count() > 0:
                editor.click()
                editor.clear()
                time.sleep(0.5)

                page.evaluate(
                    """(data) => {
                        const editor = document.querySelector('.ProseMirror');
                        if (editor) {
                            editor.focus();
                            document.execCommand('insertHTML', false, data.html);
                        }
                    }""",
                    {"html": content_html},
                )
                print("    正文填写完成")
                time.sleep(2)

                # 检查保存状态
                for _ in range(10):
                    try:
                        if page.get_by_text("草稿已保存").is_visible():
                            print("  ✅ 草稿已保存")
                            break
                    except:
                        pass
                    time.sleep(1)

            # ── 2.5：粘贴正文图片（占位符→剪贴板）──
            # 等待 2 秒确保自动保存完成，避免与图片粘贴操作产生竞态冲突
            if content_images:
                print("  ⏳ 等待自动保存完成...")
                time.sleep(2)
                _insert_content_images(page, content_images)

            # 3. 内容填写完成，等待 10 秒后关闭页面
            result["success"] = True
            result["message"] = "内容已填写（封面+内文图已插入），页面将在 10 秒后关闭"
            print("  ✅ 内容填写完成，10 秒后关闭页面...")
            time.sleep(10)

        except Exception as e:
            result["message"] = f"发布出错：{str(e)}"
            print(f"  ❌ 错误：{e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                context.close()
            except:
                pass

    return result


def check_login_status() -> Dict[str, Any]:
    """检查登录状态"""
    result = {
        "authenticated": False,
        "auth_age_hours": None,
        "warning": None,
    }

    if not STATE_FILE.exists():
        result["warning"] = "未找到登录状态，请先登录"
        return result

    age_hours = (time.time() - STATE_FILE.stat().st_mtime) / 3600
    result["auth_age_hours"] = round(age_hours, 1)

    if age_hours > 168:
        result["warning"] = f"登录状态已 {age_hours:.1f} 小时，可能已过期"

    # 实际验证
    try:
        with sync_playwright() as p:
            context = BrowserFactory.launch_persistent_context(p, headless=True)
            page = context.new_page()
            page.goto(TOUTIAO_HOME_URL, wait_until="domcontentloaded", timeout=30000)

            if "auth/page/login" in page.url or "sso.toutiao.com" in page.url:
                result["authenticated"] = False
                result["warning"] = "登录已失效"
            else:
                result["authenticated"] = True
            context.close()
    except Exception as e:
        result["warning"] = f"验证失败：{str(e)}"
        result["authenticated"] = age_hours < 168  # 保守判断

    return result


def launch_login_browser(headless: bool = False, timeout_minutes: int = 10) -> bool:
    """启动浏览器让用户登录"""
    auth_manager = AuthManager()
    return auth_manager.setup_auth(headless=headless, timeout_minutes=timeout_minutes)
