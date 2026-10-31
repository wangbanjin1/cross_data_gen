"""
对话渲染异常或离线兜底台词与动作类型规范化门面模块。
子模块拆分至 fallback_helpers.py、fallback_user.py 与 fallback_agent.py。
"""

from __future__ import annotations

from src.templates.prompts.fallback_agent import (
    get_fallback_agent_utterance,
    get_normalized_action_types,
)
from src.templates.prompts.fallback_helpers import (
    _dur_cn_labels,
    _formal_and_temp_dur_info,
    _implicit_service_phrase,
    _paraphrase_env,
    _paraphrase_period,
    _sanitize_env,
)
from src.templates.prompts.fallback_user import get_fallback_user_utterance

__all__ = [
    "_dur_cn_labels",
    "_formal_and_temp_dur_info",
    "_implicit_service_phrase",
    "_paraphrase_env",
    "_paraphrase_period",
    "_sanitize_env",
    "get_fallback_agent_utterance",
    "get_fallback_user_utterance",
    "get_normalized_action_types",
]
