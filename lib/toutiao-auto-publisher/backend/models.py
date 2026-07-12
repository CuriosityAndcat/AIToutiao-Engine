"""
Pydantic 数据模型 — 请求/响应结构
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class ContentType(str, Enum):
    TOUTIE = "toutie"       # 微头条
    ARTICLE = "article"     # 文章


class ContentStyle(str, Enum):
    """内容风格枚举 — 对标 docs/风格分析 中 4 位头部作者（去AI味仿写方案）。

    默认风格为 BAOMING_SHUO（包明说，去AI味评分最高 85.0）。
    GENERAL 仅作代码层回退（未知风格 / 文章通用），不在 UI 选择器暴露。
    """
    BAOMING_SHUO = "baoming_shuo"            # 🔥 包明说：反差+悬念+短句机枪感+数据佐证（默认）
    JIN_SHUO = "jin_shuo"                    # 📚 晋说：悬念+数字+乡愁叙事+口语吐槽
    GLOBAL_ARCHIVE = "global_archive"        # 🏛️ 全球档案馆：自称馆长、悬念+数据+情绪推演
    STORY_NARRATIVE = "story_narrative"      # 📖 听风的蚕：军事评书，悬念铺陈+通俗比喻
    GENERAL = "general"                      # 📝 通用风格（代码层回退，不在 UI 暴露）


def style_label(style_value) -> str:
    """将 style 标识符转为中文标签。

    兼容 'baoming_shuo' / ContentStyle.BAOMING_SHUO（枚举） / 'ContentStyle.baoming_shuo' 等形式。
    """
    s = style_value.value if hasattr(style_value, "value") else str(style_value)
    mapping = {
        "baoming_shuo": "包明说（反差悬念型）",
        "jin_shuo": "晋说（乡愁叙事型）",
        "global_archive": "全球档案馆（馆长悬疑型）",
        "story_narrative": "听风的蚕（评书故事型）",
        "general": "通用风格",
    }
    key = s.split(".")[-1] if "." in s else s
    return mapping.get(key, s)


class GenerateRequest(BaseModel):
    topic: str = Field(..., description="主题或关键词")
    content_type: ContentType = ContentType.ARTICLE
    max_chars: Optional[int] = Field(None, description="最大字数（微头条默认1000，文章默认5000）")
    tone: str = Field("专业且易懂", description="语调风格")
    content_style: ContentStyle = Field(ContentStyle.GENERAL, description="内容风格（military/general）")
    include_title: bool = True


class GenerateResponse(BaseModel):
    success: bool
    title: Optional[str] = None
    content: str
    content_type: ContentType
    char_count: int
    error: Optional[str] = None


class PublishRequest(BaseModel):
    title: str
    content: str
    cover_path: Optional[str] = None
    auto_publish: bool = True
    content_type: ContentType = ContentType.ARTICLE


class PublishResponse(BaseModel):
    success: bool
    message: str
    task_id: Optional[str] = None
    error: Optional[str] = None


class LoginStatusResponse(BaseModel):
    authenticated: bool
    auth_age_hours: Optional[float] = None
    warning: Optional[str] = None


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class TaskInfo(BaseModel):
    task_id: str
    task_type: str  # "generate" or "publish"
    status: TaskStatus
    message: str = ""
    result: Optional[dict] = None
    created_at: str
