"""信息隔离的双向渲染视图构建器 (Information-Isolated Dual Views)."""

from __future__ import annotations


def _resolve_user_private_slots(
    s_plan: dict,
    role: str,
    tid: str,
    b_type: str,
    tp: dict,
    env: str,
    is_single_turn_full: bool,
    is_implicit_reinf_s03: bool,
) -> tuple[dict, dict, list[str]]:
    exp_id = s_plan.get("experience_id") or (s_plan.get("experience_citation") or {}).get("experience_id")
    if tid == "T1-2":
        return (
            {"ood_goal": s_plan.get("ood_goal") or "宽带光纤装维报修"},
            {},
            [v for v in (tp.get("application_name"), tp.get("service_name"), tp.get("resolution"), tp.get("rtt"), tp.get("duration")) if v],
        )
    if is_single_turn_full:
        allowed = {
            "scenario_env": env,
            "application_name": tp.get("application_name"),
            "service_name": tp.get("service_name"),
            "start_timestamp": tp.get("start_timestamp"),
            "end_timestamp": tp.get("end_timestamp"),
            "duration": tp.get("duration"),
            "resolution": tp.get("resolution"),
            "rtt": tp.get("rtt"),
        }
        if s_plan.get("ood_goal"):
            allowed["ood_goal"] = s_plan["ood_goal"]
        if s_plan.get("second_target_params"):
            allowed["second_target_params"] = s_plan["second_target_params"]
        return (allowed, {}, [])
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
    if role == "reinforcement_session" or is_implicit_reinf_s03:
        return (
            {
                "scenario_env": env,
                "application_name": tp.get("application_name"),
                "service_name": tp.get("service_name"),
                "start_timestamp": tp.get("start_timestamp"),
            },
            {
                "confirm_history_candidate": True,
                "resolution": tp.get("resolution"),
                "rtt": tp.get("rtt"),
                "duration": tp.get("duration"),
                "end_timestamp": tp.get("end_timestamp"),
                "small_memory": s_plan.get("small_memory", {}),
            },
            [v for v in (tp.get("resolution"), tp.get("rtt"), tp.get("duration")) if v],
        )
    if tid == "T2-3" or b_type == "event_override":
        return (
            {"scenario_env": env, "application_name": tp.get("application_name"), "service_name": tp.get("service_name")},
            {"temporary_resolution": tp.get("resolution"), "temporary_rtt": tp.get("rtt")},
            [v for v in (tp.get("resolution"), tp.get("rtt")) if v],
        )
    if tid == "T2-4":
        sec_tp = s_plan.get("second_target_params") or {}
        s2 = s_plan.get("start2") or sec_tp.get("start_timestamp")
        e2 = s_plan.get("end2") or sec_tp.get("end_timestamp")
        d2 = s_plan.get("dur2") or sec_tp.get("duration")
        if b_type == "multi_intent_experience" or exp_id == "EXP_MULTI_INTENT_PARTITION_01":
            return (
                {
                    "scenario_env": env,
                    "first_stage_rehearsal_task": "跟搭档私下对一下抖音直播的词和看镜头机位",
                    "first_stage_start": tp.get("start_timestamp"),
                    "first_stage_end": tp.get("end_timestamp"),
                    "first_stage_duration": tp.get("duration"),
                    "first_stage_resolution": tp.get("resolution"),
                    "first_stage_rtt": tp.get("rtt"),
                    "second_stage_app": sec_tp.get("application_name"),
                    "second_stage_service": sec_tp.get("service_name"),
                    "second_stage_start": s2,
                    "second_stage_end": e2,
                    "second_stage_duration": d2,
                    "second_stage_resolution": sec_tp.get("resolution"),
                    "second_stage_rtt": sec_tp.get("rtt"),
                },
                {
                    "confirm_partitioned_dual_intents": True,
                    "first_stage_params": tp,
                    "second_stage_params": sec_tp,
                },
                [],
            )
        return (
            {
                "scenario_env": env,
                "first_stage_app": tp.get("application_name"),
                "first_stage_service": tp.get("service_name"),
                "first_stage_start": tp.get("start_timestamp"),
                "first_stage_end": tp.get("end_timestamp"),
                "first_stage_duration": tp.get("duration"),
                "second_stage_app": sec_tp.get("application_name"),
                "second_stage_service": sec_tp.get("service_name"),
                "second_stage_start": s2,
                "second_stage_end": e2,
                "second_stage_duration": d2,
                "second_stage_resolution": sec_tp.get("resolution"),
                "second_stage_rtt": sec_tp.get("rtt"),
            },
            {
                "confirm_partitioned_dual_intents": True,
                "first_stage_resolution": tp.get("resolution"),
                "first_stage_rtt": tp.get("rtt"),
                "first_stage_params": tp,
                "second_stage_params": sec_tp,
            },
            [],
        )
    if tid == "T2-5":
        return (
            {"scenario_env": env, "application_name": tp.get("application_name"), "service_name": tp.get("service_name"), "start_timestamp": tp.get("start_timestamp")},
            {"extended_duration": tp.get("duration"), "end_timestamp": tp.get("end_timestamp")},
            [v for v in (tp.get("resolution"), tp.get("rtt"), tp.get("duration")) if v],
        )
    if tid == "T2-6":
        wm_ptr = s_plan.get("working_memory_pointer") or {}
        if wm_ptr.get("is_disambiguation") or exp_id == "EXP_ORDER_QUALITY_DISAMBIGUATION_01":
            return (
                {"scenario_env": env, "application_name": tp.get("application_name"), "service_name": tp.get("service_name"), "start_timestamp": tp.get("start_timestamp")},
                {"selected_record_id": wm_ptr.get("target_record_id"), "duration": tp.get("duration"), "resolution": tp.get("resolution"), "rtt": tp.get("rtt")},
                [],
            )
        return (
            {"scenario_env": env, "reference_record_id": wm_ptr.get("target_record_id")},
            {"start_timestamp": tp.get("start_timestamp"), "end_timestamp": tp.get("end_timestamp"), "duration": tp.get("duration")},
            [v for v in (tp.get("start_timestamp"), tp.get("end_timestamp")) if v],
        )
    if tid == "T2-7" or b_type == "working_record_reschedule":
        wm_ptr = s_plan.get("working_memory_pointer") or {}
        return (
            {"scenario_env": env, "reference_record_id": wm_ptr.get("target_record_id"), "reschedule_direction": wm_ptr.get("reschedule_direction", "delay")},
            {"start_timestamp": tp.get("start_timestamp"), "end_timestamp": tp.get("end_timestamp")},
            [],
        )
    if role == "learning_session" or b_type == "experience_learning":
        return (
            {"scenario_env": env, "application_name": tp.get("application_name"), "service_name": tp.get("service_name"), "start_timestamp": s_plan.get("nominal_start") or tp.get("start_timestamp"), "end_timestamp": s_plan.get("nominal_end") or tp.get("end_timestamp"), "duration": s_plan.get("nominal_dur") or tp.get("duration")},
            {"resolution": tp.get("resolution"), "rtt": tp.get("rtt"), "start_timestamp": tp.get("start_timestamp"), "end_timestamp": tp.get("end_timestamp"), "duration": tp.get("duration")},
            [],
        )
    if tid == "T2-9" or exp_id in ("EXP_PREWARM_BUFFER_01", "EXP_CALENDAR_HOLIDAY_EXCEPTION_01"):
        nom_s = s_plan.get("nominal_start") or tp.get("start_timestamp")
        nom_e = s_plan.get("nominal_end") or tp.get("end_timestamp")
        nom_d = s_plan.get("nominal_dur") or tp.get("duration")
        forbidden = [v for v in (tp.get("start_timestamp"), tp.get("duration")) if v and v not in (nom_s, nom_d)]
        return (
            {"scenario_env": env, "application_name": tp.get("application_name"), "service_name": tp.get("service_name"), "start_timestamp": nom_s, "end_timestamp": nom_e, "duration": nom_d, "resolution": tp.get("resolution"), "rtt": tp.get("rtt")},
            {"start_timestamp": tp.get("start_timestamp"), "end_timestamp": tp.get("end_timestamp"), "duration": tp.get("duration")},
            forbidden,
        )
    if tid == "T2-10" or exp_id == "EXP_OVERLAPPING_ORDER_RESOLUTION_01":
        return (
            {"scenario_env": env, "application_name": tp.get("application_name"), "service_name": "看直播", "start_timestamp": tp.get("start_timestamp"), "end_timestamp": tp.get("end_timestamp"), "duration": tp.get("duration")},
            {"service_name": tp.get("service_name", "开直播")},
            [],
        )
    return (
        {
            "scenario_env": env,
            "application_name": tp.get("application_name"),
            "service_name": tp.get("service_name"),
            "start_timestamp": tp.get("start_timestamp"),
            "primary_alias": (s_plan.get("small_memory") or {}).get("value") or tp.get("application_name"),
        },
        {"confirm_memory_slots": True, "resolution": tp.get("resolution"), "rtt": tp.get("rtt"), "duration": tp.get("duration"), "end_timestamp": tp.get("end_timestamp")},
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
    rc = int(s_plan.get("round_count", 2) or 2)

    is_single_turn_full = (
        tid in ("T1-1", "T1-3", "X-1", "T2-8")
        or b_type.startswith("distractor")
        or (rc == 1 and s_plan.get("agility_factor") != 1.0)
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
            "working_memory_pointer": s_plan.get("working_memory_pointer") or {},
            "experience_citation": s_plan.get("experience_citation") or {},
            "turn1_observable_slots": user_turn1_allowed,
            "turn1_forbidden_values": agent_turn1_forbidden_values,
        },
    }
