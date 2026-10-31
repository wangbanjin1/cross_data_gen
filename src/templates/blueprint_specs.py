"""
声明式会话蓝图槽位规范模块 (Declarative Session Blueprint Specs).
将 20 轮认知演进蓝图的预设时区、经验配对计划与各阶段槽位字典从时间线计算器中彻底解耦。
"""

from __future__ import annotations

from src.templates.blueprint_helpers import _parse_time_range

SUB1_TIME_PRESETS: list[tuple[str, str, str, str, str, str]] = [
    ("18:30", "19:15", "18:15", "45min", "大巴跨城转场高速公路", "大巴转场弱网环境"),
    ("18:45", "19:45", "18:30", "60min", "大巴跨城转场高速公路", "大巴转场弱网环境"),
    ("17:30", "19:00", "17:15", "90min", "城际高铁移动车厢", "城际高铁转场环境"),
    ("19:00", "20:00", "18:45", "60min", "机场摆渡候机长廊", "候机转场弱网环境"),
    ("12:30", "13:15", "12:15", "45min", "园区通勤班车途中", "通勤班车移动环境"),
]

SUB2_TIME_PRESETS: list[tuple[str, str, str, str, str]] = [
    ("20:00", "21:00", "19:45", "60min", "驻地酒店商务中心"),
    ("20:15", "21:45", "20:00", "90min", "驻地酒店商务中心"),
    ("20:30", "22:30", "20:15", "120min", "异地差旅酒店会议室"),
    ("19:30", "20:15", "19:15", "45min", "联合办公共享会议间"),
    ("21:00", "22:30", "20:45", "90min", "驻地公寓商务工作间"),
]

OOD_PRESETS: list[tuple[str, str, str, str, str]] = [
    ("10:00", "10:30", "30min", "市政政务便民大厅", "宽带光纤装维报修"),
    ("09:30", "10:15", "45min", "社区便民综合服务站", "家庭路由器上门组网调试"),
    ("11:00", "12:00", "60min", "政企营业厅前台", "手机国际漫游套餐退订与账单申诉"),
    ("14:30", "15:00", "30min", "园区物业服务中心", "地下车库宽带专线移机办理"),
    ("16:00", "16:45", "45min", "街道综合服务中心", "固话座机故障报修与移机"),
]

DIST_NORM_PRESETS: list[tuple[str, str, str, str]] = [
    ("10:00", "10:30", "30min", "街区便民服务站"),
    ("10:30", "11:15", "45min", "临街咖啡厅休息区"),
    ("11:00", "12:00", "60min", "商场中庭公共休息区"),
    ("15:30", "16:30", "60min", "园区商务访客洽谈室"),
    ("16:30", "18:00", "90min", "市民中心便民等候区"),
]

NATURAL_TEST_SLOTS: dict[str, int] = {
    "EXP_CALENDAR_HOLIDAY_EXCEPTION_01": 6,
    "EXP_PREWARM_BUFFER_01": 8,
    "EXP_MULTI_INTENT_PARTITION_01": 10,
    "EXP_ORDER_QUALITY_DISAMBIGUATION_01": 12,
    "EXP_OVERLAPPING_ORDER_RESOLUTION_01": 13,
}


def resolve_blueprint_time_context(
    main_mt: dict,
    sub_01: dict,
    sub_02: dict,
    dist_01: dict,
    dist_02: dict,
    main_env_desc: str,
) -> dict:
    """解析主线、支线与干扰项的确定性时区与环境上下文。"""
    time_range = main_mt.get("time_range", "14:00-15:30")
    seed_str = f"{main_mt.get('name', '')}|{time_range}|{main_env_desc}|{sub_01.get('name', '')}|{sub_02.get('name', '')}"
    seed_val = sum((idx + 1) * ord(ch) for idx, ch in enumerate(seed_str))

    ext_add_choices = [30, 60, 90]
    ext_add_mins = main_mt.get("ext_add_minutes") or ext_add_choices[seed_val % len(ext_add_choices)]
    sh_str, eh_str, ref_str, base_dur, ext_eh_str, ext_dur = _parse_time_range(time_range, ext_add_minutes=ext_add_mins)

    sub1_s, sub1_e, sub1_ref, sub1_dur, sub1_default_env, sub1_default_trig = SUB1_TIME_PRESETS[seed_val % len(SUB1_TIME_PRESETS)]
    if sub_01.get("time_range"):
        sub1_s, sub1_e, sub1_ref, sub1_dur, _, _ = _parse_time_range(sub_01["time_range"])
    sub1_env = sub_01.get("env") or sub1_default_env
    sub1_trig = sub_01.get("trigger_condition") or sub1_default_trig

    sub2_s, sub2_e, sub2_ref, sub2_dur, sub2_default_env = SUB2_TIME_PRESETS[(seed_val // 3) % len(SUB2_TIME_PRESETS)]
    if sub_02.get("time_range"):
        sub2_s, sub2_e, sub2_ref, sub2_dur, _, _ = _parse_time_range(sub_02["time_range"])
    sub2_env = sub_02.get("env") or sub2_default_env

    ood_s, ood_e, ood_dur, ood_env, ood_goal_default = OOD_PRESETS[(seed_val // 5) % len(OOD_PRESETS)]
    dn_s, dn_e, dn_dur, dn_env = DIST_NORM_PRESETS[(seed_val // 7) % len(DIST_NORM_PRESETS)]

    sh_val, sm_val = map(int, sh_str.split(":"))
    eh_val, em_val = map(int, eh_str.split(":"))
    base_mins_val = (eh_val * 60 + em_val) - (sh_val * 60 + sm_val)
    if base_mins_val <= 0:
        base_mins_val = 120
    pw_sh_tot = (sh_val * 60 + sm_val) - 30
    if pw_sh_tot < 0:
        pw_sh_tot += 24 * 60

    return {
        "sh_str": sh_str,
        "eh_str": eh_str,
        "ref_str": ref_str,
        "base_dur": base_dur,
        "ext_eh_str": ext_eh_str,
        "ext_dur": ext_dur,
        "pw_s_str": f"{pw_sh_tot // 60:02d}:{pw_sh_tot % 60:02d}",
        "pw_dur_str": f"{base_mins_val + 30}min",
        "sub1_s": sub1_s,
        "sub1_e": sub1_e,
        "sub1_ref": sub1_ref,
        "sub1_dur": sub1_dur,
        "sub1_env": sub1_env,
        "sub1_trig": sub1_trig,
        "sub2_s": sub2_s,
        "sub2_e": sub2_e,
        "sub2_ref": sub2_ref,
        "sub2_dur": sub2_dur,
        "sub2_env": sub2_env,
        "ood_s": ood_s,
        "ood_e": ood_e,
        "ood_dur": ood_dur,
        "ood_env": ood_env,
        "ood_goal": dist_02.get("ood_goal") or ood_goal_default,
        "dn_s": dn_s,
        "dn_e": dn_e,
        "dn_dur": dn_dur,
        "dn_env": dist_01.get("env") or dn_env,
    }


def plan_experience_slot_pairs(selected_exp_ids: list[str] | None) -> tuple[dict[int, str], dict[int, str]]:
    """建立每个被挑选经验的 (学习铺垫轮 learn_slot, 迁移测试轮 test_slot) 配对映射。"""
    sorted_exps = sorted(selected_exp_ids or [], key=lambda x: NATURAL_TEST_SLOTS.get(x, 99))
    exp_plan: dict[str, dict[str, int]] = {}
    if len(sorted_exps) == 1:
        e1 = sorted_exps[0]
        t1 = NATURAL_TEST_SLOTS.get(e1, 8)
        exp_plan[e1] = {"learn_slot": 4 if t1 == 6 else 5, "test_slot": t1}
    elif len(sorted_exps) >= 2:
        e1, e2 = sorted_exps[0], sorted_exps[1]
        t1 = NATURAL_TEST_SLOTS.get(e1, 8)
        t2 = NATURAL_TEST_SLOTS.get(e2, 10)
        if t1 == 6 and t2 == 8:
            exp_plan[e1] = {"learn_slot": 4, "test_slot": 6}
            exp_plan[e2] = {"learn_slot": 5, "test_slot": 8}
        elif t1 == 6:
            exp_plan[e1] = {"learn_slot": 5, "test_slot": 6}
            exp_plan[e2] = {"learn_slot": 8, "test_slot": t2}
        else:
            exp_plan[e1] = {"learn_slot": 5, "test_slot": t1}
            exp_plan[e2] = {"learn_slot": 6, "test_slot": t2}

    slot_learn_map = {v["learn_slot"]: k for k, v in exp_plan.items()}
    slot_test_map = {v["test_slot"]: k for k, v in exp_plan.items()}
    return slot_learn_map, slot_test_map


def make_experience_learn_slot(exp_id: str, main_mt: dict, sub_01: dict, base_dur: str, ext_dur: str, main_env_desc: str) -> dict:
    """构建经验记忆学习铺垫轮槽位字典。"""
    time_kind_map = {
        "EXP_CALENDAR_HOLIDAY_EXCEPTION_01": "holiday",
        "EXP_MULTI_INTENT_PARTITION_01": "multi_intent",
        "EXP_OVERLAPPING_ORDER_RESOLUTION_01": "overlap",
        "EXP_PREWARM_BUFFER_01": "prewarm",
    }
    t_kind = time_kind_map.get(exp_id, "main")
    dur_val = ext_dur if exp_id == "EXP_MULTI_INTENT_PARTITION_01" else base_dur
    return {
        "tag": f"exp_learn_{exp_id}",
        "template_id": "T2-1",
        "memory_tier": "experiential_memory",
        "role": "learning_session",
        "source": main_mt,
        "second_source": sub_01 if exp_id == "EXP_MULTI_INTENT_PARTITION_01" else None,
        "type": "experience_learning",
        "dur": dur_val,
        "base_dur": base_dur,
        "env": main_env_desc,
        "action": "crystallize_experience_pitfall",
        "experience_id": exp_id,
        "round_count": 3,
        "cold_hot_type": None,
        "agility_factor": None,
        "time_kind": t_kind,
    }


def _build_phase1_slots(ctx: dict) -> list[dict]:
    """构建第 1~7 轮（主线建联、支线1建联、主线强化、早期工作/经验记忆与时长延长）蓝图槽位。"""
    main_mt, sub_01 = ctx["main_mt"], ctx["sub_01"]
    tc, learn_map, test_map = ctx["tc"], ctx["slot_learn_map"], ctx["slot_test_map"]
    decl_mode, trig_type = ctx["decl_mode"], ctx["storyline_trigger_type"]
    main_env, main_trig = ctx["main_env_desc"], ctx["main_trigger_desc"]
    base_dur, ext_dur = tc["base_dur"], tc["ext_dur"]

    s4 = make_experience_learn_slot(learn_map[4], main_mt, sub_01, base_dur, ext_dur, main_env) if 4 in learn_map else {
        "tag": "wm_reuse", "template_id": "T2-6", "memory_tier": "working_memory", "role": "reuse_session",
        "source": main_mt, "type": "working_record_reuse", "dur": base_dur, "env": main_env,
        "action": "retrieve_working_record_reuse", "round_count": 3, "cold_hot_type": None, "agility_factor": None, "time_kind": "main",
    }
    s5 = make_experience_learn_slot(learn_map[5], main_mt, sub_01, base_dur, ext_dur, main_env) if 5 in learn_map else {
        "tag": "wm_reschedule", "template_id": "T2-7", "memory_tier": "working_memory", "role": "reuse_session",
        "source": main_mt, "type": "working_record_reschedule", "dur": base_dur, "env": main_env,
        "action": "reschedule_working_record", "round_count": 2, "cold_hot_type": None, "agility_factor": None, "time_kind": "main",
    }
    if 6 in learn_map:
        s6 = make_experience_learn_slot(learn_map[6], main_mt, sub_01, base_dur, ext_dur, main_env)
    elif 6 in test_map:
        s6 = {
            "tag": "exp_holiday", "template_id": "T2-1", "memory_tier": "experiential_memory", "role": "reuse_session",
            "source": main_mt, "type": "proactive_experience", "dur": base_dur, "env": main_env,
            "action": "holiday_avoidance_reschedule", "experience_id": "EXP_CALENDAR_HOLIDAY_EXCEPTION_01",
            "learning_source_session_tag": "exp_learn_EXP_CALENDAR_HOLIDAY_EXCEPTION_01",
            "round_count": 2, "cold_hot_type": None, "agility_factor": None, "time_kind": "holiday",
        }
    else:
        s6 = {
            "tag": "wm_reuse_6", "template_id": "T2-6", "memory_tier": "working_memory", "role": "reuse_session",
            "source": main_mt, "type": "working_record_reuse", "dur": base_dur, "env": main_env,
            "action": "retrieve_working_record_reuse", "round_count": 3, "cold_hot_type": None, "agility_factor": None, "time_kind": "main",
        }

    return [
        {
            "tag": "main_evidence", "template_id": "T2-1", "memory_tier": "factual_memory", "role": "evidence_session",
            "source": main_mt, "type": "main", "dur": base_dur, "env": main_env,
            "action": "declare_explicit_rule" if decl_mode == "explicit_declaration" else "single_task_implicit_behavior",
            "declaration_mode": decl_mode, "storyline_trigger_type": trig_type, "trigger_condition": main_trig,
            "round_count": 3, "cold_hot_type": "cold_start", "agility_factor": 0.0, "time_kind": "main",
        },
        {
            "tag": "sub1_evidence", "template_id": "T3-1", "memory_tier": "factual_memory", "role": "evidence_session",
            "source": sub_01, "type": "sub_01", "dur": tc["sub1_dur"], "env": tc["sub1_env"],
            "action": "disambiguate_sub_storyline_1", "declaration_mode": "implicit_induction",
            "storyline_trigger_type": "location_environment", "trigger_condition": tc["sub1_trig"],
            "round_count": 3, "cold_hot_type": "cold_start", "agility_factor": 0.0, "time_kind": "sub1",
        },
        {
            "tag": "main_reinf_1", "template_id": "T2-1", "memory_tier": "factual_memory", "role": "reinforcement_session",
            "source": main_mt, "type": "main", "dur": base_dur, "env": main_env,
            "action": "reinforce_explicit_memory" if decl_mode == "explicit_declaration" else "crystallize_implicit_memory",
            "declaration_mode": decl_mode, "storyline_trigger_type": trig_type, "trigger_condition": main_trig,
            "round_count": 2, "cold_hot_type": "hot_start", "agility_factor": 0.5, "time_kind": "main",
        },
        s4,
        s5,
        s6,
        {
            "tag": "main_amend", "template_id": "T2-5", "memory_tier": "factual_memory", "role": "reuse_session",
            "source": main_mt, "type": "main", "dur": ext_dur, "base_dur": base_dur, "env": main_env,
            "action": "extend_duration_amend", "storyline_trigger_type": trig_type, "trigger_condition": main_trig,
            "round_count": 3, "cold_hot_type": "hot_start", "agility_factor": 0.5, "time_kind": "main_amend",
        },
    ]


def _build_phase2_slots(ctx: dict) -> list[dict]:
    """构建第 8~14 轮（经验迁移测试、突发事件临时纠正与恢复、工作记忆改期）蓝图槽位。"""
    main_mt, sub_01, evt_01 = ctx["main_mt"], ctx["sub_01"], ctx["evt_01"]
    tc, learn_map, test_map = ctx["tc"], ctx["slot_learn_map"], ctx["slot_test_map"]
    decl_mode, trig_type = ctx["decl_mode"], ctx["storyline_trigger_type"]
    main_env, main_trig = ctx["main_env_desc"], ctx["main_trigger_desc"]
    base_dur, ext_dur = tc["base_dur"], tc["ext_dur"]

    if 8 in learn_map:
        s8 = make_experience_learn_slot(learn_map[8], main_mt, sub_01, base_dur, ext_dur, main_env)
    elif 8 in test_map:
        s8 = {
            "tag": "exp_prewarm", "template_id": "T2-9", "memory_tier": "experiential_memory", "role": "reuse_session",
            "source": main_mt, "type": "proactive_experience", "dur": ext_dur, "base_dur": base_dur,
            "env": "奥林匹克体育中心多功能馆", "action": "prewarm_buffer_calculation", "experience_id": "EXP_PREWARM_BUFFER_01",
            "learning_source_session_tag": "exp_learn_EXP_PREWARM_BUFFER_01", "round_count": 2,
            "cold_hot_type": None, "agility_factor": None, "time_kind": "prewarm",
        }
    else:
        s8 = {
            "tag": "main_reinf_8", "template_id": "T2-1", "memory_tier": "factual_memory", "role": "reinforcement_session",
            "source": main_mt, "type": "main", "dur": base_dur, "env": main_env,
            "action": "reinforce_explicit_memory" if decl_mode == "explicit_declaration" else "crystallize_implicit_memory",
            "declaration_mode": decl_mode, "storyline_trigger_type": trig_type, "trigger_condition": main_trig,
            "round_count": 2, "cold_hot_type": "hot_start", "agility_factor": 0.5, "time_kind": "main",
        }
    s10 = {
        "tag": "exp_multi_intent", "template_id": "T2-4", "memory_tier": "experiential_memory", "role": "reuse_session",
        "source": main_mt, "second_source": sub_01, "type": "multi_intent_experience", "dur": ext_dur, "base_dur": base_dur,
        "env": main_env, "action": "multi_intent_delay_isolation", "experience_id": "EXP_MULTI_INTENT_PARTITION_01",
        "learning_source_session_tag": "exp_learn_EXP_MULTI_INTENT_PARTITION_01", "round_count": 2,
        "cold_hot_type": None, "agility_factor": None, "time_kind": "multi_intent",
    } if 10 in test_map else {
        "tag": "sub1_reuse_10", "template_id": "T2-1", "memory_tier": "factual_memory", "role": "reuse_session",
        "source": sub_01, "type": "sub_01", "dur": tc["sub1_dur"], "env": tc["sub1_env"],
        "action": "reuse_sub_storyline_1", "round_count": 2, "cold_hot_type": "hot_start", "agility_factor": 0.5, "time_kind": "sub1",
    }
    s12 = {
        "tag": "exp_quality", "template_id": "T2-6", "memory_tier": "experiential_memory", "role": "reuse_session",
        "source": main_mt, "type": "working_record_disambig", "dur": base_dur, "env": main_env,
        "action": "quality_log_disambiguation", "experience_id": "EXP_ORDER_QUALITY_DISAMBIGUATION_01",
        "learning_source_session_tag": "exp_learn_EXP_ORDER_QUALITY_DISAMBIGUATION_01", "round_count": 2,
        "cold_hot_type": None, "agility_factor": None, "time_kind": "main",
    } if 12 in test_map else {
        "tag": "wm_reuse_12", "template_id": "T2-6", "memory_tier": "working_memory", "role": "reuse_session",
        "source": main_mt, "type": "working_record_reuse", "dur": base_dur, "env": main_env,
        "action": "retrieve_working_record_reuse", "round_count": 3, "cold_hot_type": None, "agility_factor": None, "time_kind": "main",
    }
    s13 = {
        "tag": "exp_overlap", "template_id": "T2-10", "memory_tier": "experiential_memory", "role": "reuse_session",
        "source": main_mt, "type": "overlapping_experience", "dur": base_dur, "env": main_env,
        "action": "overlapping_order_handoff", "experience_id": "EXP_OVERLAPPING_ORDER_RESOLUTION_01",
        "learning_source_session_tag": "exp_learn_EXP_OVERLAPPING_ORDER_RESOLUTION_01", "round_count": 2,
        "cold_hot_type": None, "agility_factor": None, "time_kind": "overlap",
    } if 13 in test_map else {
        "tag": "wm_reschedule_13", "template_id": "T2-7", "memory_tier": "working_memory", "role": "reuse_session",
        "source": main_mt, "type": "working_record_reschedule", "dur": base_dur, "env": main_env,
        "action": "reschedule_working_record", "round_count": 2, "cold_hot_type": None, "agility_factor": None, "time_kind": "main",
    }
    ov_pref = evt_01.get("preference_override", {"resolution": "720p", "rtt_max": "30ms"})
    s9 = {"tag": "evt_correct", "template_id": "T2-3", "memory_tier": "factual_memory", "role": "correction_session", "source": main_mt, "type": "event_override", "dur": base_dur, "env": "沿海暴雨强对流前沿现场", "action": "override_temporary_preference", "override": ov_pref, "round_count": 3, "cold_hot_type": "hot_start", "agility_factor": 0.5, "time_kind": "main"}
    s11 = {"tag": "evt_reuse", "template_id": "T2-1", "memory_tier": "factual_memory", "role": "reuse_session", "source": main_mt, "type": "event_reuse", "dur": base_dur, "env": main_env, "action": "reuse_long_term_rule_after_correction", "round_count": 2, "cold_hot_type": "hot_start", "agility_factor": 0.5, "time_kind": "main"}
    s14 = {"tag": "wm_reschedule_2", "template_id": "T2-7", "memory_tier": "working_memory", "role": "reuse_session", "source": main_mt, "type": "working_record_reschedule", "dur": base_dur, "env": main_env, "action": "reschedule_working_record", "round_count": 2, "cold_hot_type": None, "agility_factor": None, "time_kind": "main"}
    return [s8, s9, s10, s11, s12, s13, s14]


def _build_phase3_slots(ctx: dict) -> list[dict]:
    """构建第 15~20 轮（域外拒识、工作记忆多候选消歧、支线2建联与复用、单次干扰、终局极速闭环）蓝图槽位。"""
    main_mt, sub_02, dist_01 = ctx["main_mt"], ctx["sub_02"], ctx["dist_01"]
    tc = ctx["tc"]
    trig_type = ctx["storyline_trigger_type"]
    main_env, main_trig = ctx["main_env_desc"], ctx["main_trigger_desc"]
    base_dur = tc["base_dur"]

    return [
        {
            "tag": "dist_ood", "template_id": "T1-2", "memory_tier": "factual_memory", "role": "distractor_session",
            "source": main_mt, "type": "distractor_ood", "dur": tc["ood_dur"], "env": tc["ood_env"],
            "action": "reject_out_of_domain", "ood_goal": tc["ood_goal"], "round_count": 1,
            "cold_hot_type": None, "agility_factor": None, "time_kind": "dist_ood",
        },
        {
            "tag": "wm_disambig", "template_id": "T2-6", "memory_tier": "working_memory", "role": "reuse_session",
            "source": main_mt, "type": "working_record_disambig", "dur": base_dur, "env": main_env,
            "action": "disambiguate_working_record", "round_count": 3, "cold_hot_type": None, "agility_factor": None, "time_kind": "main",
        },
        {
            "tag": "sub2", "template_id": "T2-1", "memory_tier": "factual_memory", "role": "evidence_session",
            "source": sub_02, "type": "sub_02", "dur": tc["sub2_dur"], "env": tc["sub2_env"],
            "action": "establish_sub_storyline_2", "declaration_mode": "implicit_induction",
            "storyline_trigger_type": "location_environment", "trigger_condition": tc["sub2_env"],
            "round_count": 3, "cold_hot_type": "cold_start", "agility_factor": 0.0, "time_kind": "sub2",
        },
        {
            "tag": "sub2_reuse", "template_id": "T2-1", "memory_tier": "factual_memory", "role": "reuse_session",
            "source": sub_02, "type": "sub_02", "dur": tc["sub2_dur"], "env": tc["sub2_env"],
            "action": "reuse_sub_storyline_2", "storyline_trigger_type": "location_environment", "trigger_condition": tc["sub2_env"],
            "round_count": 2, "cold_hot_type": "hot_start", "agility_factor": 0.5, "time_kind": "sub2",
        },
        {
            "tag": "dist_normal", "template_id": "T1-1", "memory_tier": "factual_memory", "role": "distractor_session",
            "source": dist_01, "type": "distractor_normal", "dur": tc["dn_dur"], "env": tc["dn_env"],
            "action": "single_standard_assurance", "round_count": 1, "cold_hot_type": None, "agility_factor": None, "time_kind": "dist_normal",
        },
        {
            "tag": "main_final", "template_id": "T2-1", "memory_tier": "factual_memory", "role": "reuse_session",
            "source": main_mt, "type": "main_recovery", "dur": base_dur, "env": main_env,
            "action": "recover_long_term_rule", "storyline_trigger_type": trig_type, "trigger_condition": main_trig,
            "round_count": 1, "cold_hot_type": "hot_start", "agility_factor": 1.0, "time_kind": "main",
        },
    ]


def build_raw_blueprint_specs(ctx: dict) -> list[dict]:
    """组合全部 3 个演化阶段的声明式蓝图槽位规范列表。"""
    return _build_phase1_slots(ctx) + _build_phase2_slots(ctx) + _build_phase3_slots(ctx)
