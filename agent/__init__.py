"""
Agent 系统 v0.2

对齐框架:
    - LangGraph StateGraph API (graph.py)
    - OpenAI Agents SDK (agent.py, runner.py, config.py, tools.py, guardrails.py)
    - LangGraph Reflexion (types.py, graph.py)
    - DeepSeek LLM API (llm_client.py)

核心架构:
    ┌────────────┐     ┌──────────┐     ┌───────────┐     ┌──────────┐
    │   Agent     │───▶│  Runner   │───▶│ AgentGraph │───▶│ LLMClient │
    │ (身份/能力) │     │ (编排器)  │     │ (工作流图) │     │ (DeepSeek)│
    └────────────┘     └──────────┘     └───────────┘     └──────────┘

快速开始:
    from agent import Agent, Runner, RunConfig

    agent = Agent(
        name="DemoAgent",
        instructions="你是一个助手。",
    )

    result = Runner.run_sync(agent, "你的任务描述")
    print(result.final_output)
"""

# ─── 生产接入状态 ─────────────────────────────────────────────────
# ✅ 已接生产: guardrails, memory, search_engine (3 个模块)
# ⚠️ 未接生产: agent, runner, config, graph, tools, state (6 个模块，~1400 行)
#    详见 AGENTS.md「Harness 六组件在生产中的接入状态」+ 批次 C 立项
#    以下导入保留为框架层完整性，暂不删除；工具/状态模块可候选删除
# ──────────────────────────────────────────────────────────────────

# ─── 数据模型 ────────────────────────────────────────────────────
from agent.types import (
    AgentStatus,
    Reflection,
    AnswerQuestion,
    ReviseAnswer,
    ResearchQuery,
    SearchResult,
    TaskResult,
)

# ─── Agent 核心 ──────────────────────────────────────────────────
from agent.agent import Agent, default_evaluator

# ─── Runner ──────────────────────────────────────────────────────
from agent.runner import Runner, RunResult

# ─── 配置 ────────────────────────────────────────────────────────
from agent.config import RunConfig

# ─── 图构建器 ────────────────────────────────────────────────────
from agent.graph import AgentGraph

# ─── LLM 客户端 ───────────────────────────────────────────────────
from agent.llm_client import LLMClient

# ─── 工具系统 ────────────────────────────────────────────────────
from agent.tools import (
    function_tool,
    FunctionTool,
    ToolRegistry,
)

# ─── 护栏系统 ────────────────────────────────────────────────────
from agent.guardrails import (
    GuardrailResult,
    GuardrailPipeline,
    InputGuardrail,
    OutputGuardrail,
    PolicyGuardrail,
    BaseGuardrail,
)

# ─── 记忆管理 ────────────────────────────────────────────────────
from agent.memory import (
    ConversationMemory,
    ConversationTurn,
    WorkingMemory,
)

# ─── 状态定义 ────────────────────────────────────────────────────
from agent.state import AgentState

__all__ = [
    # Types
    "AgentStatus",
    "Reflection",
    "AnswerQuestion",
    "ReviseAnswer",
    "ResearchQuery",
    "SearchResult",
    "TaskResult",
    # Core
    "Agent",
    "Runner",
    "RunResult",
    # Config
    "RunConfig",
    # Graph
    "AgentGraph",
    # LLM
    "LLMClient",
    # Tools
    "function_tool",
    "FunctionTool",
    "ToolRegistry",
    # Guardrails
    "GuardrailResult",
    "GuardrailPipeline",
    "InputGuardrail",
    "OutputGuardrail",
    "PolicyGuardrail",
    "BaseGuardrail",
    # Memory
    "ConversationMemory",
    "ConversationTurn",
    "WorkingMemory",
    # State
    "AgentState",
    # Evaluator
    "default_evaluator",
]

__version__ = "0.2.0"
