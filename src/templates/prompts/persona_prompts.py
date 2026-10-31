"""画像骨架生成提示词构建模块。"""

from __future__ import annotations

import json
from src.templates.prompts.prompt_constants import (
    PERSONA_SKELETON_CONSTRAINTS_TEMPLATE,
    PERSONA_SKELETON_SCHEMA_TEMPLATE,
)


def build_persona_skeleton_prompt(
    raw_persona: dict,
    forced_decl_mode: str,
    forced_trig_type: str,
    trig_instruction: str,
    period_type_hint: str = "weekly",
    days_hint: list | None = None,
    time_range_hint: str = "14:00-16:00",
) -> str:
    """
    构建用于将原始画像扩充为解耦画像骨架的 Prompt。
    支持日级/周级/月级多粒度周期与6大核心参数口语别名配置。
    """
    days_repr = json.dumps(days_hint or ["Monday", "Friday"], ensure_ascii=False)
    raw_json = json.dumps(raw_persona, ensure_ascii=False, indent=2)
    persona_id = str(raw_persona.get("persona_id", "P_001"))
    evidence_pattern = "显式口述固定偏好" if forced_decl_mode == "explicit_declaration" else "隐式单次保障并随后固化"

    constraints_block = PERSONA_SKELETON_CONSTRAINTS_TEMPLATE.format(
        forced_decl_mode=forced_decl_mode,
        forced_trig_type=forced_trig_type,
        trig_instruction=trig_instruction,
        period_type_hint=period_type_hint,
        days_repr=days_repr,
        time_range_hint=time_range_hint,
    )
    schema_block = PERSONA_SKELETON_SCHEMA_TEMPLATE.format(
        persona_id=persona_id,
        category=raw_persona.get("category", ""),
        persona_summary=raw_persona.get("persona_summary", ""),
        user_id=f"USER_{persona_id.split('_')[-1]}",
        forced_trig_type=forced_trig_type,
        period_type_hint=period_type_hint,
        days_repr=days_repr,
        time_range_hint=time_range_hint,
        forced_decl_mode=forced_decl_mode,
        evidence_pattern=evidence_pattern,
    )

    return (
        "你是一个核心网通信与长程记忆专家。请将以下粗粒度的人物网络画像，扩充为结构化的【解耦画像骨架】。\n\n"
        f"【输入原始画像】:\n{raw_json}\n\n"
        f"{constraints_block}\n\n"
        f"{schema_block}\n"
    )
