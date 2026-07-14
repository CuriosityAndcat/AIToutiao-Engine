"""
AI 内容生成模块
支持微头条和文章两种内容类型，支持 4 种微头条内容风格（对标 docs/风格分析 作者）：
  - baoming_shuo:    包明说（反差悬念型，默认）
  - jin_shuo:        晋说（乡愁叙事型）
  - global_archive:  全球档案馆（馆长悬疑型）
  - story_narrative: 听风的蚕（评书故事型）
  - general:         通用风格（代码层回退，不在 UI 暴露）
通过 STYLE_ROUTER 字典实现 O(1) 风格路由。
调用 OpenAI 兼容接口（DeepSeek API）。

注：所有风格 / 通用 / 改写 Prompt 常量已拆分至 prompts 包（见 prompts/__init__.py），
本文件只保留业务逻辑与风格路由，调用方（engine_app.py / main.py 等）无需改动。
"""
import sys
import time
from pathlib import Path
from openai import OpenAI

# ── 确保 backend 目录在 Python 路径中 ──
# 当 ai_writer.py 被独立导入时（如 streamlit_app.py 或 CLI 脚本），需要 backend 目录在路径中
# 以正确解析 from config import settings 和 from models import ...
_backend_dir = Path(__file__).parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from config import settings
from models import ContentType, ContentStyle

# ============================================================
# 风格 / 通用 / 改写 Prompt 集合
# 已从本文件拆分至 prompts 包（prompts/__init__.py 统一导出），
# 一行导入替代原 800+ 行内联 Prompt 常量定义。
# ============================================================

from prompts import (
    TOUTIE_PROMPT,
    SYSTEM_PROMPT_BAOMING_SHUO,
    BAOMING_SHUO_TOUTIE_PROMPT,
    SYSTEM_PROMPT_JIN_SHUO,
    JIN_SHUO_TOUTIE_PROMPT,
    SYSTEM_PROMPT_GLOBAL_ARCHIVE,
    GLOBAL_ARCHIVE_TOUTIE_PROMPT,
    SYSTEM_PROMPT_STORY_NARRATIVE,
    STORY_NARRATIVE_PROMPT,
    MILITARY_RED_LINES,
    HUMANIZE_SYSTEM_PROMPT,
    HUMANIZE_USER_PROMPT,
    GLOBAL_ARCHIVE_HUMANIZE_SYSTEM_PROMPT,
    GLOBAL_ARCHIVE_HUMANIZE_USER_PROMPT,
    ARTICLE_PROMPT,
    COVER_KEYWORD_PROMPT,
)


# ============================================================
# 全局事实边界（系统级注入，优先级高于风格指令）
# 防止 LLM 为满足风格要求而编造具体日期/人名/数据。
# 注入位置：generate_toutie / generate_article 的 system_prompt 前缀。
# 注意：Claim-Pipeline 模式跳过此注入（声明池约束更强）。
# ============================================================

_FACT_BOUNDARY_SYSTEM = (
    "【最高优先级：事实边界 — 违反将导致内容不合格】\n"
    "1. 你只能使用用户消息中提供的「信息来源」和「网络背景资料」中的事实写作\n"
    "2. 严禁编造：具体日期（如\"5月8日\"）、人名、地名、协议名称、精确数字\n"
    "   → 如果来源中只有概括描述，请保持概括，不要自行补细节\n"
    "3. 信息来源中不存在的细节 → 不要写；不确定的信息 → 用\"据报道\"\"据分析\"标记\n"
    "4. 信息不足以支撑详细论述时，用分析性/推理性语言替代\n"
    "   （如\"这可能意味着…\"\"不排除…的可能性\"\"值得关注的是…\"）\n"
    "5. 时间表述：来源中的未来计划（如\"计划在2026年部署\"）不要写成已发生事件\n"
    "6. 以上规则优先于任何风格要求。风格指令中如有数据要求但来源无具体数据，\n"
    "   则用分析性/推理性语言替代，而非编造数字\n"
)

# ============================================================
# 风格路由字典
# ============================================================

STYLE_ROUTER = {
    # (system_prompt, user_prompt, temperature)
    ContentStyle.BAOMING_SHUO:     (SYSTEM_PROMPT_BAOMING_SHUO,     BAOMING_SHUO_TOUTIE_PROMPT,    0.7),
    ContentStyle.JIN_SHUO:         (SYSTEM_PROMPT_JIN_SHUO,         JIN_SHUO_TOUTIE_PROMPT,        0.7),
    ContentStyle.GLOBAL_ARCHIVE:   (SYSTEM_PROMPT_GLOBAL_ARCHIVE,   GLOBAL_ARCHIVE_TOUTIE_PROMPT,  0.75),
    ContentStyle.STORY_NARRATIVE:  (SYSTEM_PROMPT_STORY_NARRATIVE,  STORY_NARRATIVE_PROMPT,        0.85),
    ContentStyle.GENERAL:          (None,                           TOUTIE_PROMPT,                 0.7),
}


class AIWriter:
    """AI 内容生成器"""

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_BASE_URL or None,
        )
        self.model = settings.AI_MODEL

    def _call_ai(
        self,
        prompt: str,
        system_prompt: str = None,
        max_tokens: int = None,
        temperature: float = None,
    ) -> str:
        """
        调用 AI 接口。

        Args:
            prompt: 用户消息内容
            system_prompt: 系统消息内容（用于固化角色和风格约束）
            max_tokens: 最大输出 token 数
            temperature: 温度参数，默认使用配置值
        """
        if not settings.AI_API_KEY:
            raise ValueError("未配置 AI_API_KEY，请在 .env 文件中设置")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens or settings.AI_MAX_TOKENS,
            temperature=temperature if temperature is not None else settings.AI_TEMPERATURE,
        )
        return response.choices[0].message.content.strip()

    def generate_toutie(
        self,
        topic: str,
        max_chars: int = 800,
        content_style: ContentStyle = ContentStyle.GENERAL,
    ) -> dict:
        """
        生成微头条内容，通过 STYLE_ROUTER 字典路由到对应风格。

        Args:
            topic: 主题文本（转录原文或关键词）
            max_chars: 最大字数
            content_style: 内容风格（支持 4 种：baoming_shuo/jin_shuo/global_archive/story_narrative，外加 general 回退）
        """
        # 字典路由：O(1) 查找 → 获取 (system_prompt, user_prompt_template, temperature)
        system_prompt, user_template, temperature = STYLE_ROUTER.get(
            content_style,
            STYLE_ROUTER[ContentStyle.GENERAL],  # 未知风格回退到通用
        )

        # 系统级事实边界：放在风格 system_prompt 之前，优先级最高
        if system_prompt:
            system_prompt = _FACT_BOUNDARY_SYSTEM + "\n\n" + system_prompt
        else:
            system_prompt = _FACT_BOUNDARY_SYSTEM

        # 格式化 User Prompt
        user_prompt = user_template.format(topic=topic, max_chars=max_chars)

        # 调用 AI（自动处理 system_prompt 为 None 的情况）
        content = self._call_ai(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=max_chars * 2,
            temperature=temperature,
        )

        # 解析标题：各风格 toutie prompt 已统一要求输出「标题：xxx」格式
        # （对齐 generate_article 的解析逻辑，根治微头条内容缺失标题的问题）
        title = ""
        body = content
        if "标题：" in content:
            _parts = content.split("标题：", 1)
            if len(_parts) > 1:
                _after = _parts[1]
                _end = _after.find("\n")
                if _end != -1:
                    title = _after[:_end].strip()
                    body = _after[_end:].strip()
                else:
                    title = _after.strip()
                    body = _after.strip()

        return {
            "title": title,
            "content": body,
            "char_count": len(body),
        }

    def compose_from_claims(
        self,
        claims_pool,  # ClaimsPool (from fact_pipeline)
        style,        # ContentStyle
        transcript: str,
        max_chars: int = 1200,
    ) -> dict:
        """阶段 3 Compose：从已验证声明池 + 风格路由生成微头条正文。

        关键差异 vs generate_toutie()：
        - **跳过 _FACT_BOUNDARY_SYSTEM 注入**（声明池本身是更强的约束，
          叠加会造成指令冗余/潜在措辞冲突）
        - 输入是结构化声明池而非自由文本 topic
        - 区分「确定事实」和「部分事实」，后者自动带不确定性标记

        Args:
            claims_pool: 阶段 2.5 合并后的 ClaimsPool
            style: 内容风格（枚举值或字符串）
            transcript: 视频转录摘要
            max_chars: 最大字数

        Returns:
            dict: {"title": str, "content": str, "char_count": int}
        """
        # 风格路由
        if isinstance(style, str):
            try:
                style = ContentStyle(style)
            except ValueError:
                style = ContentStyle.BAOMING_SHUO

        system_prompt, user_template, temperature = STYLE_ROUTER.get(
            style,
            STYLE_ROUTER[ContentStyle.GENERAL],
        )

        # 构建 Compose prompt（区分确定/部分事实）
        claims_text = claims_pool.to_prompt_text()
        compose_prompt = (
            f"{claims_text}\n\n"
            f"【写作要求】\n"
            f"基于以上事实，按指定风格写一篇微头条。\n"
            f"- 可以调整语言风格、句式、结构\n"
            f"- 「确定事实」可直接引用；「部分事实」必须带不确定性标记\n"
            f"- 不能新增以下信息：具体日期（日/月）、具体人名（非公众人物）、"
            f"具体数字（人数/金额等）\n"
            f"  → 除非在「确定事实」中有明确记录\n"
            f"- 如果事实不足以支撑丰富内容，用分析性/推理性语言填充\n\n"
            f"【视频摘要】\n{transcript[:2000]}\n\n"
            f"【输出】\n标题: ...\n正文: ..."
        )

        # 用风格 user_template 格式包装
        user_prompt = compose_prompt
        if "{topic}" in user_template:
            user_prompt = user_template.format(
                topic=compose_prompt, max_chars=max_chars,
            )

        content = self._call_ai(
            prompt=user_prompt,
            system_prompt=system_prompt,  # 跳过 _FACT_BOUNDARY_SYSTEM
            max_tokens=max_chars * 2,
            temperature=temperature,
        )

        # 解析标题
        title = ""
        body = content
        if "标题：" in content:
            _parts = content.split("标题：", 1)
            if len(_parts) > 1:
                _after = _parts[1]
                _end = _after.find("\n")
                if _end != -1:
                    title = _after[:_end].strip()
                    body = _after[_end:].strip()
                else:
                    title = _after.strip()
                    body = _after.strip()

        return {
            "title": title,
            "content": body,
            "char_count": len(body),
        }

    def generate_article(
        self,
        topic: str,
        max_chars: int = 2000,
        tone: str = "专业且易懂",
    ) -> dict:
        """生成文章内容"""
        prompt = ARTICLE_PROMPT.format(topic=topic, max_chars=max_chars, tone=tone)
        result = self._call_ai(prompt, system_prompt=_FACT_BOUNDARY_SYSTEM, max_tokens=max_chars * 2)

        # 解析标题和正文
        title = ""
        content = result

        if "标题：" in result:
            parts = result.split("标题：", 1)
            if len(parts) > 1:
                title_and_rest = parts[1]
                title_end = title_and_rest.find("\n")
                if title_end != -1:
                    title = title_and_rest[:title_end].strip()
                    content = title_and_rest[title_end:].strip()
                else:
                    title = title_and_rest.strip()
                    content = title_and_rest.strip()

        # 清理正文前缀
        if content.startswith("正文："):
            content = content[3:].strip()

        return {
            "title": title,
            "content": content,
            "char_count": len(content),
        }

    def generate(
        self,
        topic: str,
        content_type: ContentType,
        **kwargs,
    ) -> dict:
        """
        统一入口：根据内容类型生成。

        额外支持参数：
            content_style: ContentStyle = ContentStyle.GENERAL
            max_chars: int
            tone: str
        """
        if content_type == ContentType.TOUTIE:
            max_chars = kwargs.get("max_chars") or 1000
            content_style = kwargs.get("content_style", ContentStyle.GENERAL)
            # 确保 content_style 是枚举类型
            if isinstance(content_style, str):
                content_style = ContentStyle(content_style)
            return self.generate_toutie(topic, max_chars, content_style)
        else:
            max_chars = kwargs.get("max_chars") or 5000
            tone = kwargs.get("tone", "专业且易懂")
            return self.generate_article(topic, max_chars, tone)

    # ═══════════════════════════════════════════════════════════
    # Humanize 风格路由表
    # ═══════════════════════════════════════════════════════════
    _HUMANIZE_ROUTER = {
        ContentStyle.GLOBAL_ARCHIVE: (
            GLOBAL_ARCHIVE_HUMANIZE_SYSTEM_PROMPT,
            GLOBAL_ARCHIVE_HUMANIZE_USER_PROMPT,
            0.75,  # 馆长风格温度略低，保持专业稳定
        ),
    }

    def humanize(self, text: str, content_style=None) -> dict:
        """
        人工化改写：去除 AI 味，变成真人手笔。

        用于对 AI 生成内容进行二次处理，消除机器腔，注入口语化表达、
        节奏不规则性、个人态度等真人写作特征，同时确保符合今日头条平台规则。

        风格感知：传入 content_style 可触发风格专属 Humanize 提示词，
        避免通用 Humanize 破坏特定风格的独特性（如全球档案馆的馆长口吻）。

        Args:
            text: 待改写的原始文本（AI 生成或初稿）
            content_style: 可选，内容风格（ContentStyle 枚举或字符串）

        Returns:
            dict: {"content": 改写后的微头条正文, "char_count": 字数}
        """
        # 风格路由：有专属 humanize 则用专属，否则走通用
        system_prompt = HUMANIZE_SYSTEM_PROMPT
        user_template = HUMANIZE_USER_PROMPT
        temperature = 0.8

        if content_style is not None:
            if isinstance(content_style, str):
                try:
                    content_style = ContentStyle(content_style)
                except ValueError:
                    content_style = None
            if content_style is not None:
                route = self._HUMANIZE_ROUTER.get(content_style)
                if route:
                    system_prompt, user_template, temperature = route

        user_prompt = user_template.format(text=text)
        content = self._call_ai(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=len(text) * 2,
            temperature=temperature,
        )
        return {
            "content": content,
            "char_count": len(content),
        }

    def suggest_cover_keywords(self, title: str, content: str) -> str:
        """根据标题和内容建议封面图搜索关键词"""
        prompt = COVER_KEYWORD_PROMPT.format(
            title=title,
            content=content[:500],
        )
        return self._call_ai(prompt, max_tokens=100)

    # ============================================================
    # 图片生成方法（串联 Builder → Sanitizer → Checker → ImageGen）
    # ============================================================

    def generate_cover_image(
        self,
        title: str,
        content: str,
        output_dir: str,
        content_style: str = "baoming_shuo",
        prompt_lang: str = "cn",
    ) -> dict:
        """
        生成封面图（清洗 prompt + 合规审查 + 调用图片生成）。

        工作流程：
          1. CoverPromptBuilder 提取视觉隐喻 → 构建 prompt（中文或英文）
          2. PromptSanitizer 剥离标签 + 追加禁文字指令
          3. ComplianceChecker 扫描敏感词 + 自动替换
          4. 调用 image_gen 生成图片

        Args:
            title: 文章标题
            content: 文章正文
            output_dir: 图片输出目录
            content_style: 内容风格（baoming_shuo/jin_shuo/global_archive/story_narrative/general）
            prompt_lang: Prompt 语言模式
                        'cn': 中文军事视觉隐喻（推荐，默认）
                        'en': 英文新闻摄影风

        Returns:
            dict: {"path": 图片路径, "prompt": 使用的 prompt, "warnings": [...], "visual_metaphor": ...}
        """
        try:
            # --- 添加 wewrite-main/toolkit 到路径 ---
            toolkit_dir = str(
                Path(__file__).parent.parent.parent / "wewrite-main" / "toolkit"
            )
            if toolkit_dir not in sys.path:
                sys.path.insert(0, toolkit_dir)

            from cover_prompt_builder import CoverPromptBuilder
            from image_gen import generate_image
            from image_reviewer import review_image, detect_watermark, crop_watermark

            MAX_REVIEW_RETRIES = 3

            # 1. 构建 prompt（清洗 + 合规已内置）
            style = content_style.replace("ContentStyle.", "")
            if hasattr(content_style, 'value'):
                style = content_style.value
            builder = CoverPromptBuilder(style=style, prompt_lang=prompt_lang)
            result = builder.build_cover(title, content[:500])

            clean_prompt = result["prompt"]
            expected_elements = result.get("expected_elements", [])
            warnings = result.get("compliance", {}).get("warnings", [])

            # 2. 确保输出目录存在
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            cover_file = output_path / "cover.png"

            # 3. 图片生成 + 审核重试循环
            review_log = []
            final_image_path = None
            current_prompt = clean_prompt
            watermark_handled = False

            for attempt in range(MAX_REVIEW_RETRIES + 1):
                # 3a. 生成图片
                image_path = generate_image(
                    prompt=current_prompt,
                    output_path=str(cover_file),
                    size="cover",
                )

                if attempt == 0 and MAX_REVIEW_RETRIES == 0:
                    final_image_path = image_path
                    break

                # 3b. 审核元素完整性
                passed, missing, suggestion = review_image(
                    image_path, expected_elements
                )

                review_entry = {
                    "attempt": attempt + 1,
                    "passed": passed,
                    "missing": missing,
                    "suggestion": suggestion,
                }
                review_log.append(review_entry)

                if passed:
                    final_image_path = image_path
                    break

                if attempt < MAX_REVIEW_RETRIES:
                    # 调整 Prompt 重试
                    current_prompt = self._adjust_prompt_for_retry(
                        current_prompt, missing, suggestion
                    )
                    warnings.append(
                        f"🔄 审核不通过(第{attempt+1}次)，缺失{'、'.join(missing)}，已调整Prompt重试"
                    )

            # 4. 水印检测与处理
            if final_image_path and not watermark_handled:
                has_wm, wm_text = detect_watermark(final_image_path)
                if has_wm:
                    # 策略：先尝试用更强禁水印 Prompt 重新生成
                    anti_wm_prompt = (
                        current_prompt
                        + "\n\nCRITICAL: DO NOT render ANY text, watermark, logo, "
                        + "signature, label, or typography on the image. Pure visual, "
                        + "zero text elements. 严格禁止任何文字和水印。"
                    )
                    try:
                        retry_file = output_path / "cover_no_wm.png"
                        anti_wm_path = generate_image(
                            prompt=anti_wm_prompt,
                            output_path=str(retry_file),
                            size="cover",
                        )
                        has_wm2, _ = detect_watermark(anti_wm_path)
                        if not has_wm2:
                            final_image_path = anti_wm_path
                            warnings.append("🔁 水印已通过强化Prompt重新生成消除")
                        else:
                            # 降级：裁剪
                            crop_watermark(anti_wm_path, crop_ratio=0.07)
                            final_image_path = anti_wm_path
                            warnings.append("✂ 水印已通过裁剪方式去除（底部7%区域）")
                    except Exception:
                        # 裁剪兜底
                        crop_watermark(final_image_path, crop_ratio=0.07)
                        warnings.append("✂ 水印已通过裁剪方式去除（底部7%区域）")
                watermark_handled = True

            return {
                "path": final_image_path or image_path,
                "prompt": clean_prompt,
                "visual_metaphor": result["visual_metaphor"],
                "expected_elements": expected_elements,
                "style": style,
                "warnings": warnings,
                "review_log": review_log,
                "retry_count": len(review_log) - 1 if review_log and review_log[-1]["passed"] else len(review_log),
            }

        except ImportError as e:
            return {
                "path": None,
                "error": f"图片生成模块不可用: {e}",
                "hint": "请确保 wewrite-main/toolkit/image_gen.py 可导入且 API key 已配置",
            }
        except Exception as e:
            return {"path": None, "error": str(e)}

    def _adjust_prompt_for_retry(
        self,
        original_prompt: str,
        missing_elements: list,
        suggestion: str,
    ) -> str:
        """
        根据审核反馈调整 Prompt，强化缺失元素的描述。

        Args:
            original_prompt: 原始 Prompt
            missing_elements: 缺失的元素列表
            suggestion: 审核模型给出的改进建议

        Returns:
            调整后的 Prompt
        """
        # 在 Prompt 开头追加强调指令
        emphasis = (
            f"\n\n【重试指令 - 请务必在画面中明确体现以下缺失元素】\n"
            f"CRITICAL: The following visual elements MUST be clearly visible in the image: "
            f"{', '.join(missing_elements)}. "
            f"These are NOT optional. Render them as prominent visual symbols in the composition.\n"
        )
        return emphasis + original_prompt

    def generate_inline_images(
        self,
        content: str,
        output_dir: str,
        num_images: int = 3,
        content_style: str = "baoming_shuo",
        prompt_lang: str = "cn",
    ) -> list:
        """
        生成内文配图列表（根据叙事节点自动分配）。

        工作流程：同 generate_cover_image，但针对内文段落。

        Args:
            prompt_lang: Prompt 语言模式，'cn'=中文军事视觉（推荐），'en'=英文新闻摄影

        Returns:
            list[dict]: [{"path": ..., "prompt": ..., "narrative_point": ..., "index": 0}, ...]
        """
        results = []
        try:
            toolkit_dir = str(
                Path(__file__).parent.parent.parent / "wewrite-main" / "toolkit"
            )
            if toolkit_dir not in sys.path:
                sys.path.insert(0, toolkit_dir)

            from cover_prompt_builder import CoverPromptBuilder
            from image_gen import generate_image

            style = content_style.replace("ContentStyle.", "")
            if hasattr(content_style, 'value'):
                style = content_style.value
            builder = CoverPromptBuilder(style=style, prompt_lang=prompt_lang)
            prompts = builder.build_inline_prompts(content, num_images)

            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            for item in prompts:
                image_file = output_path / f"inline_{item['index'] + 1}.png"
                try:
                    image_path = generate_image(
                        prompt=item["prompt"],
                        output_path=str(image_file),
                        size="article",
                    )
                    results.append({
                        "path": image_path,
                        "prompt": item["prompt"],
                        "narrative_point": item["narrative_point"],
                        "index": item["index"],
                        "warnings": item.get("warnings", []),
                    })
                except Exception as e:
                    results.append({
                        "path": None,
                        "error": str(e),
                        "narrative_point": item["narrative_point"],
                        "index": item["index"],
                    })

        except ImportError as e:
            return [{"path": None, "error": f"ImportError: {e}"}]
        except Exception as e:
            return [{"path": None, "error": str(e)}]

        return results

    def generate_all_images(
        self,
        title: str,
        content: str,
        output_dir: str,
        content_style: str = "baoming_shuo",
        num_inline: int = 3,
        prompt_lang: str = "cn",
    ) -> dict:
        """
        一次性生成封面 + 内文配图。

        Args:
            prompt_lang: Prompt 语言模式，'cn'=中文军事视觉（推荐），'en'=英文新闻摄影

        Returns:
            {"cover": {...}, "inline": [...], "output_dir": str}
        """
        cover_result = self.generate_cover_image(
            title=title,
            content=content,
            output_dir=output_dir,
            content_style=content_style,
            prompt_lang=prompt_lang,
        )
        inline_results = self.generate_inline_images(
            content=content,
            output_dir=output_dir,
            num_images=num_inline,
            content_style=content_style,
            prompt_lang=prompt_lang,
        )

        return {
            "cover": cover_result,
            "inline": inline_results,
            "output_dir": str(Path(output_dir)),
        }
