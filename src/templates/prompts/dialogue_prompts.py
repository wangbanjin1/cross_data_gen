"""多轮与单轮对话提示词组装模块。"""

from __future__ import annotations

import json
from src.templates.prompts.prompt_constants import (
    BATCH_DIALOGUE_RULES_BLOCK,
    SINGLE_DIALOGUE_RULES_TEMPLATE,
)
from src.templates.prompts.small_memory_prompt import SMALL_MEMORY_GUIDE


def build_batch_dialogue_prompt(prompt_items: list[dict], identity: str, speech: dict) -> str:
    """
    构建批量渲染多轮对话的完整 Prompt。
    包含 8 种会话模版（T2-4, T2-2, T2-1, T1-2, T2-5, X-1, T2-3, T1-1）的动作规范与生成要求。
    """
    items_json = json.dumps(prompt_items, ensure_ascii=False, indent=2)
    return (
        "请根据以下人物画像背景与这组会话要求，为每个会话渲染真实、口语化的网络保障交互对话。\n\n"
        f"{SMALL_MEMORY_GUIDE}\n\n"
        "【人物风格】:\n"
        f"- 身份描述: {identity}\n"
        f"- 语气风格: {speech.get('tone')}\n"
        f"- 口头禅/表达习惯: {speech.get('catchphrases')} | {speech.get('typical_habits')}\n\n"
        "【待生成会话列表（含每个会话的精确参数基准 reference_turns）】:\n"
        f"{items_json}\n\n"
        f"{BATCH_DIALOGUE_RULES_BLOCK}\n"
    )


def _format_memory_snapshot_context(snapshot_before: dict) -> str:
    if not snapshot_before:
        return "当前记忆快照为空（首次建联会话，尚无已形成的长期记忆）。\n"
    lines = ["当前已建立的记忆快照 (Memory Snapshot Before):"]
    for mid, mval in snapshot_before.items():
        if isinstance(mval, dict) and "application_name" in mval:
            lines.append(
                f"  - [{mid}] 应用: {mval.get('application_name')}, 业务: {mval.get('service_name')}, "
                f"画质: {mval.get('resolution')}, 时延: {mval.get('rtt_max')}, 状态: {mval.get('status')}"
            )
    return "\n".join(lines) + "\n"


def _format_slot_visibility(role: str, tid: str, tp: dict) -> str:
    if role == "evidence_session":
        return (
            f"- Turn 1 允许提及的表层槽位 (turn1_allowed_slots): 应用={tp['application_name']}, 业务={tp['service_name']}, 开始时间={tp['start_timestamp']}\n"
            f"- Turn 2 才允许揭晓的参数 (turn2_reveal_slots, 严禁在 Turn 1 提前泄露): 分辨率={tp['resolution']}, 时延上限={tp['rtt']}, 结束时间={tp['end_timestamp']} (时长{tp['duration']})"
        )
    if role in ("reinforcement_session", "reuse_session") and tid not in ("T2-3", "T2-5", "T2-9", "T2-10"):
        return (
            f"- Turn 1 用户侧允许提及 (user_private_view.turn1_allowed_slots): 应用={tp['application_name']}, 业务={tp['service_name']} (严禁用户在 Turn 1 说出画质/时延/时长，必须由 Agent 从 active_memory 检索补全)\n"
            f"- Agent 侧可从记忆快照补全的参数 (agent_observable_view): 分辨率={tp['resolution']}, 时延上限={tp['rtt']}, 时段={tp['start_timestamp']} 至 {tp['end_timestamp']} (时长{tp['duration']})"
        )
    return (
        f"- 目标保障业务: 应用={tp['application_name']}, 业务={tp['service_name']}, 分辨率={tp['resolution']}, "
        f"时延上限={tp['rtt']}, 时段={tp['start_timestamp']} 至 {tp['end_timestamp']} (时长{tp['duration']})"
    )


def build_single_dialogue_prompt(s_plan: dict, persona: dict, snapshot_before: dict) -> str:
    """单会话渲染兜底 Prompt。"""
    role = s_plan["memory_role"]
    b_type = s_plan["blueprint_type"]
    tp = s_plan["target_params"]
    env = s_plan["scenario_env"]
    speech = persona["static_profile"]["speech_style"]
    identity = persona["static_profile"]["identity"]
    round_count = s_plan["round_count"]
    tid = s_plan.get("template_id", "T2-1")
    ood_goal = s_plan.get("ood_goal", "")

    memory_context_str = _format_memory_snapshot_context(snapshot_before)
    slot_visibility_str = _format_slot_visibility(role, tid, tp)
    ood_line = f"- 域外诉求目标: {ood_goal}\n" if ood_goal else ""
    rules_block = SINGLE_DIALOGUE_RULES_TEMPLATE.format(
        app_name=tp["application_name"],
        srv_name=tp["service_name"],
        resolution=tp["resolution"],
        rtt=tp["rtt"],
        duration=tp["duration"],
        start_ts=tp["start_timestamp"],
        end_ts=tp["end_timestamp"],
        trigger_task=s_plan.get("trigger_condition", "该任务"),
        trigger_loc=s_plan.get("trigger_condition", env),
        env=env,
        round_count=round_count,
    )

    return (
        "请根据以下人物背景、场景环境和记忆规则，渲染一段真实、口语化的多轮人机交互对话。\n\n"
        f"{SMALL_MEMORY_GUIDE}\n\n"
        "【人物画像】:\n"
        f"- 身份描述: {identity}\n"
        f"- 语气风格: {speech.get('tone')}\n"
        f"- 口头禅/表达习惯: {speech.get('catchphrases')} | {speech.get('typical_habits')}\n\n"
        "【当前生效的历史记忆 (Memory Snapshot)】:\n"
        f"{memory_context_str}\n"
        "【当前场景与信息隔离视图 (Information-Isolated Views)】:\n"
        f"- 会话模版: {tid} (角色: {role}, 类型: {b_type})\n"
        f"- 发生时间: {s_plan['reference_time']}\n"
        f"- 现场环境: {env}\n"
        f"- 偏好模式: {s_plan.get('declaration_mode', 'explicit_declaration')}\n"
        f"- 触发类型: {s_plan.get('storyline_trigger_type', 'time_periodic')} (触发条件: {s_plan.get('trigger_condition', env)})\n"
        f"{slot_visibility_str}\n"
        f"{ood_line}\n"
        f"{rules_block}\n"
    )
