"""信息隔离的双向渲染视图构建器 (Information-Isolated Dual Views)."""

from __future__ import annotations


def _resolve_user_private_slots(s_plan: dict, role: str, tid: str, b_type: str, tp: dict, env: str, is_single_turn_full: bool, is_implicit_reinf_s03: bool) -> tuple[dict, dict, list[str]]:
    if tid == "T1-2":
        return (
            {"ood_goal": s_plan.get("ood_goal") or "宽带光纤装维报修"},
            {},
            [v for v in (tp.get("application_name"), tp.get("service_name"), tp.get("resolution"), tp.get("rtt"), tp.get("duration")) if v],
        )
    if is_single_turn_full:
        return (
            {
                "scenario_env": env,
                "application_name": tp.get("application_name"),
                "service_name": tp.get("service_name"),
                "start_timestamp": tp.get("start_timestamp"),
                "end_timestamp": tp.get("end_timestamp"),
                "duration": tp.get("duration"),
                "resolution": tp.get("resolution"),
                "rtt": tp.get("rtt"),
            },
            {},
            [],
        )
    if role == "evidence_session":
        return (
            {
                "scenario_env": env,
                "application_name": tp.get("application_name"),
                "service_name": tp.get("service_name"),
                "start_timestamp": tp.get("start_timestamp"),
            },
            {
                "resolution": tp.get("resolution"),
                "rtt": tp.get("rtt"),
                "duration": tp.get("duration"),
                "end_timestamp": tp.get("end_timestamp"),
            },
            [v for v in (tp.get("resolution"), tp.get("rtt"), tp.get("duration")) if v],
        )
    if is_implicit_reinf_s03:
        return (
            {"scenario_env": env, "service_name": tp.get("service_name")},
            {"confirm_history_candidate": True, "small_memory": s_plan.get("small_memory", {})},
            [v for v in (tp.get("application_name"), tp.get("resolution"), tp.get("rtt"), tp.get("duration")) if v],
        )
    if tid == "T2-3" or b_type == "event_override":
        return (
            {"scenario_env": env, "application_name": tp.get("application_name"), "service_name": tp.get("service_name")},
            {"temporary_resolution": tp.get("resolution"), "temporary_rtt": tp.get("rtt")},
            [v for v in (tp.get("resolution"), tp.get("rtt")) if v],
        )
    if tid == "T2-5":
        return (
            {"scenario_env": env, "application_name": tp.get("application_name"), "service_name": tp.get("service_name")},
            {"extended_duration": tp.get("duration"), "end_timestamp": tp.get("end_timestamp")},
            [v for v in (tp.get("resolution"), tp.get("rtt"), tp.get("duration")) if v],
        )
    return (
        {
            "scenario_env": env,
            "application_name": tp.get("application_name"),
            "service_name": tp.get("service_name"),
            "primary_alias": (s_plan.get("small_memory") or {}).get("value") or tp.get("application_name"),
        },
        {"confirm_memory_slots": True},
        [v for v in (tp.get("resolution"), tp.get("rtt")) if v],
    )


def build_isolated_views(s_plan: dict, snapshot_before: dict) -> dict:
    """
    构建信息隔离的双向渲染视图 (Information-Isolated Dual Views):
    1. user_private_view: 物理剥离 Turn 1 禁止提前说出的槽位 (memory_filled / turn2_disambiguated)，
       仅保留 turn1_allowed_slots 与 turn2_reveal_slots。
    2. agent_observable_view: 物理屏蔽未公开的 Ground-Truth 答案字典，
       Agent 在 Turn 1 仅可见 snapshot_before 与用户已说出的表层信息。
    """
    role = s_plan.get("memory_role", "")
    tid = s_plan.get("template_id", "T2-1")
    b_type = s_plan.get("blueprint_type", "")
    tp = dict(s_plan.get("target_params") or {})
    env = s_plan.get("scenario_env", "")
    exp_id = s_plan.get("experience_id") or (s_plan.get("experience_citation") or {}).get("experience_id")

    is_single_turn_full = (
        tid in ("T1-1", "T1-3", "T2-4", "X-1")
        or b_type == "distractor"
        or tid in ("T2-9", "T2-10")
        or s_plan.get("memory_tier") == "experiential_memory"
        or b_type == "experience_learning"
        or bool(exp_id)
    )
    is_implicit_reinf_s03 = (
        role == "reinforcement_session"
        and s_plan.get("declaration_mode") == "implicit_induction"
        and str(s_plan.get("session_id", "")).endswith("-03")
    )
    user_turn1_allowed, user_turn2_reveal, user_turn1_forbidden_values = _resolve_user_private_slots(
        s_plan, role, tid, b_type, tp, env, is_single_turn_full, is_implicit_reinf_s03
    )

    agent_turn1_forbidden_values: list[str] = []
    if role == "evidence_session":
        agent_turn1_forbidden_values = [v for v in (tp.get("resolution"), tp.get("rtt"), tp.get("duration")) if v]
    elif tid == "T2-5" and tp.get("duration"):
        agent_turn1_forbidden_values = [tp["duration"]]

    return {
        "user_private_view": {
            "turn1_allowed_slots": user_turn1_allowed,
            "turn2_reveal_slots": user_turn2_reveal,
            "turn1_forbidden_values": user_turn1_forbidden_values,
        },
        "agent_observable_view": {
            "snapshot_before": snapshot_before or {},
            "turn1_observable_slots": user_turn1_allowed,
            "turn1_forbidden_values": agent_turn1_forbidden_values,
        },
    }
