"""
声明式会话蓝图槽位规范模块 (Declarative Session Blueprint Specs).
基于画像特征种子 (seed_val) 动态规划经验配对槽位、多意图源组合与因果约束下的拓扑重排。
"""

from __future__ import annotations

import random
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
    rehearsal_mins = [30, 45, 60][(seed_val // 11) % 3]

    return {
        "seed_val": seed_val,
        "rehearsal_mins": rehearsal_mins,
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


def plan_experience_slot_pairs(selected_exp_ids: list[str] | None, seed_val: int = 1) -> tuple[dict[int, str], dict[int, str]]:
    """基于 seed_val 动态分配每个经验的 (learn_slot, test_slot) 配对，满足 learn_slot < test_slot。"""
    exps = list(selected_exp_ids or [])
    rng = random.Random(seed_val)
    learn_pool = [4, 5, 6, 7]
    test_pool = [8, 9, 10, 11, 12, 13, 14]
    rng.shuffle(learn_pool)
    rng.shuffle(test_pool)

    slot_learn_map: dict[int, str] = {}
    slot_test_map: dict[int, str] = {}
    chosen_learns = sorted(learn_pool[: len(exps)])
    chosen_tests = sorted(test_pool[: len(exps)])

    for idx, exp_id in enumerate(exps):
        l_slot = chosen_learns[idx]
        t_slot = max(chosen_tests[idx], l_slot + 2)
        while t_slot in slot_test_map or t_slot in slot_learn_map:
            t_slot += 1
        slot_learn_map[l_slot] = exp_id
        slot_test_map[t_slot] = exp_id
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


def make_experience_test_slot(exp_id: str, main_mt: dict, base_dur: str, ext_dur: str, main_env: str, reh_dur: str = "30min") -> dict:
    """根据经验 ID 动态构建对应的经验迁移测试轮槽位字典。"""
    if exp_id == "EXP_CALENDAR_HOLIDAY_EXCEPTION_01":
        return {
            "tag": "exp_holiday", "template_id": "T2-1", "memory_tier": "experiential_memory", "role": "reuse_session",
            "source": main_mt, "type": "proactive_experience", "dur": base_dur, "env": main_env,
            "action": "holiday_avoidance_reschedule", "experience_id": exp_id,
            "learning_source_session_tag": f"exp_learn_{exp_id}", "round_count": 2,
            "cold_hot_type": None, "agility_factor": None, "time_kind": "holiday",
        }
    if exp_id == "EXP_PREWARM_BUFFER_01":
        return {
            "tag": "exp_prewarm", "template_id": "T2-9", "memory_tier": "experiential_memory", "role": "reuse_session",
            "source": main_mt, "type": "proactive_experience", "dur": ext_dur, "base_dur": base_dur,
            "env": "奥林匹克体育中心多功能馆", "action": "prewarm_buffer_calculation", "experience_id": exp_id,
            "learning_source_session_tag": f"exp_learn_{exp_id}", "round_count": 2,
            "cold_hot_type": None, "agility_factor": None, "time_kind": "prewarm",
        }
    if exp_id == "EXP_MULTI_INTENT_PARTITION_01":
        return {
            "tag": "exp_multi_intent", "template_id": "T2-4", "memory_tier": "experiential_memory", "role": "reuse_session",
            "source": main_mt, "second_source": main_mt, "type": "multi_intent_experience", "multi_intent_mode": "heterogeneous",
            "dur": reh_dur, "base_dur": base_dur, "env": main_env, "action": "multi_intent_delay_isolation",
            "experience_id": exp_id, "learning_source_session_tag": f"exp_learn_{exp_id}",
            "round_count": 2, "cold_hot_type": None, "agility_factor": None, "time_kind": "multi_intent",
        }
    if exp_id == "EXP_ORDER_QUALITY_DISAMBIGUATION_01":
        return {
            "tag": "exp_quality", "template_id": "T2-6", "memory_tier": "experiential_memory", "role": "reuse_session",
            "source": main_mt, "type": "working_record_disambig", "dur": base_dur, "env": main_env,
            "action": "quality_log_disambiguation", "experience_id": exp_id,
            "learning_source_session_tag": f"exp_learn_{exp_id}", "round_count": 2,
            "cold_hot_type": None, "agility_factor": None, "time_kind": "main",
        }
    return {
        "tag": "exp_overlap", "template_id": "T2-10", "memory_tier": "experiential_memory", "role": "reuse_session",
        "source": main_mt, "type": "overlapping_experience", "dur": base_dur, "env": main_env,
        "action": "overlapping_order_handoff", "experience_id": exp_id,
        "learning_source_session_tag": f"exp_learn_{exp_id}", "round_count": 2,
        "cold_hot_type": None, "agility_factor": None, "time_kind": "overlap",
    }


def _build_foundational_slots(ctx: dict) -> list[dict]:
    """构建前 3 轮基础事实记忆建联与强化槽位（S-01 ~ S-03）。"""
    main_mt, sub_01, tc = ctx["main_mt"], ctx["sub_01"], ctx["tc"]
    decl_mode, trig_type = ctx["decl_mode"], ctx["storyline_trigger_type"]
    main_env, main_trig, base_dur = ctx["main_env_desc"], ctx["main_trigger_desc"], tc["base_dur"]
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
    ]


def _build_flexible_middle_pool(ctx: dict) -> list[dict]:
    """构建动态可重排的中段候选池（涵盖同类双意图 T1-3、非同类双意图 T2-4、混合意图 X-1、工作记忆及时长延长）。"""
    main_mt, sub_01, sub_02, dist_01, evt_01 = ctx["main_mt"], ctx["sub_01"], ctx["sub_02"], ctx["dist_01"], ctx["evt_01"]
    tc, test_map = ctx["tc"], ctx["slot_test_map"]
    seed_val = tc.get("seed_val", 1)
    trig_type, main_env, main_trig = ctx["storyline_trigger_type"], ctx["main_env_desc"], ctx["main_trigger_desc"]
    base_dur, ext_dur = tc["base_dur"], tc["ext_dur"]

    homo_sources = [(main_mt, main_env), (sub_01, tc["sub1_env"]), (dist_01, tc["dn_env"])]
    homo_src, homo_env = homo_sources[seed_val % len(homo_sources)]
    hetero_pairs = [(sub_01, main_mt, tc["sub1_env"]), (main_mt, sub_01, main_env), (dist_01, main_mt, tc["dn_env"]), (sub_02, main_mt, tc["sub2_env"])]
    het_src1, het_src2, het_env = hetero_pairs[(seed_val // 3) % len(hetero_pairs)]
    ov_pref = evt_01.get("preference_override", {"resolution": "720p", "rtt_max": "30ms"})

    pool: list[dict] = [
        {"tag": "wm_reuse", "template_id": "T2-6", "memory_tier": "working_memory", "role": "reuse_session", "source": main_mt, "type": "working_record_reuse", "dur": base_dur, "env": main_env, "action": "retrieve_working_record_reuse", "round_count": 3, "cold_hot_type": None, "agility_factor": None, "time_kind": "main"},
        {"tag": "wm_reschedule", "template_id": "T2-7", "memory_tier": "working_memory", "role": "reuse_session", "source": main_mt, "type": "working_record_reschedule", "dur": base_dur, "env": main_env, "action": "reschedule_working_record", "round_count": 2, "cold_hot_type": None, "agility_factor": None, "time_kind": "main"},
        {"tag": "main_amend", "template_id": "T2-5", "memory_tier": "factual_memory", "role": "reuse_session", "source": main_mt, "type": "main", "dur": ext_dur, "base_dur": base_dur, "env": main_env, "action": "extend_duration_amend", "storyline_trigger_type": trig_type, "trigger_condition": main_trig, "round_count": 3, "cold_hot_type": "hot_start", "agility_factor": 0.5, "time_kind": "main_amend"},
        {"tag": "multi_intent_homo", "template_id": "T1-3", "memory_tier": "factual_memory", "role": "distractor_session", "source": homo_src, "second_source": dist_01, "type": "multi_intent_homogeneous", "multi_intent_mode": "homogeneous", "dur": tc["dn_dur"], "env": homo_env, "action": "parallel_homogeneous_multi_intent", "round_count": 1, "cold_hot_type": None, "agility_factor": None, "time_kind": "multi_intent_homo"},
        {"tag": "dist_mixed", "template_id": "X-1", "memory_tier": "factual_memory", "role": "distractor_session", "source": main_mt, "type": "distractor_mixed", "dur": tc["dn_dur"], "env": tc["dn_env"], "action": "handle_normal_and_reject_ood", "ood_goal": tc["ood_goal"], "round_count": 1, "cold_hot_type": None, "agility_factor": None, "time_kind": "dist_mixed"},
        {"tag": "wm_reschedule_2", "template_id": "T2-7", "memory_tier": "working_memory", "role": "reuse_session", "source": main_mt, "type": "working_record_reschedule", "dur": base_dur, "env": main_env, "action": "reschedule_working_record", "round_count": 2, "cold_hot_type": None, "agility_factor": None, "time_kind": "main"},
        {"tag": "evt_correct", "template_id": "T2-3", "memory_tier": "factual_memory", "role": "correction_session", "source": main_mt, "type": "event_override", "dur": base_dur, "env": "沿海暴雨强对流前沿现场", "action": "override_temporary_preference", "override": ov_pref, "round_count": 3, "cold_hot_type": "hot_start", "agility_factor": 0.5, "time_kind": "main"},
        {"tag": "evt_reuse", "template_id": "T2-1", "memory_tier": "factual_memory", "role": "reuse_session", "source": main_mt, "type": "event_reuse", "dur": base_dur, "env": main_env, "action": "reuse_long_term_rule_after_correction", "round_count": 2, "cold_hot_type": "hot_start", "agility_factor": 0.5, "time_kind": "main"},
    ]
    if "EXP_MULTI_INTENT_PARTITION_01" not in test_map.values():
        pool[5] = {
            "tag": "sub1_reuse_10", "template_id": "T2-4", "memory_tier": "factual_memory", "role": "reuse_session",
            "source": het_src1, "second_source": het_src2, "type": "multi_intent_heterogeneous", "multi_intent_mode": "heterogeneous",
            "dur": tc["sub1_dur"], "base_dur": base_dur, "env": het_env,
            "action": "reuse_sub_storyline_1", "round_count": 2, "cold_hot_type": "hot_start", "agility_factor": 0.5, "time_kind": "multi_intent_hetero",
        }
    return pool


def _build_tail_slots(ctx: dict) -> list[dict]:
    """构建尾部槽位（工作记忆多候选消歧 + 拓展会话 17~20）。"""
    main_mt, sub_02, dist_01, tc = ctx["main_mt"], ctx["sub_02"], ctx["dist_01"], ctx["tc"]
    trig_type, main_env, main_trig, base_dur = ctx["storyline_trigger_type"], ctx["main_env_desc"], ctx["main_trigger_desc"], tc["base_dur"]
    return [
        {"tag": "wm_disambig", "template_id": "T2-6", "memory_tier": "working_memory", "role": "reuse_session", "source": main_mt, "type": "working_record_disambig", "dur": base_dur, "env": main_env, "action": "disambiguate_working_record", "round_count": 3, "cold_hot_type": None, "agility_factor": None, "time_kind": "main"},
        {"tag": "dist_ood", "template_id": "T1-2", "memory_tier": "factual_memory", "role": "distractor_session", "source": main_mt, "type": "distractor_ood", "dur": tc["ood_dur"], "env": tc["ood_env"], "action": "reject_out_of_domain", "ood_goal": tc["ood_goal"], "round_count": 1, "cold_hot_type": None, "agility_factor": None, "time_kind": "dist_ood"},
        {"tag": "sub2", "template_id": "T2-1", "memory_tier": "factual_memory", "role": "evidence_session", "source": sub_02, "type": "sub_02", "dur": tc["sub2_dur"], "env": tc["sub2_env"], "action": "establish_sub_storyline_2", "declaration_mode": "implicit_induction", "storyline_trigger_type": "location_environment", "trigger_condition": tc["sub2_env"], "round_count": 3, "cold_hot_type": "cold_start", "agility_factor": 0.0, "time_kind": "sub2"},
        {"tag": "sub2_reuse", "template_id": "T2-1", "memory_tier": "factual_memory", "role": "reuse_session", "source": sub_02, "type": "sub_02", "dur": tc["sub2_dur"], "env": tc["sub2_env"], "action": "reuse_sub_storyline_2", "storyline_trigger_type": "location_environment", "trigger_condition": tc["sub2_env"], "round_count": 2, "cold_hot_type": "hot_start", "agility_factor": 0.5, "time_kind": "sub2"},
        {"tag": "dist_normal", "template_id": "T1-1", "memory_tier": "factual_memory", "role": "distractor_session", "source": dist_01, "type": "distractor_normal", "dur": tc["dn_dur"], "env": tc["dn_env"], "action": "single_standard_assurance", "round_count": 1, "cold_hot_type": None, "agility_factor": None, "time_kind": "dist_normal"},
        {"tag": "main_final", "template_id": "T2-1", "memory_tier": "factual_memory", "role": "reuse_session", "source": main_mt, "type": "main_recovery", "dur": base_dur, "env": main_env, "action": "recover_long_term_rule", "storyline_trigger_type": trig_type, "trigger_condition": main_trig, "round_count": 1, "cold_hot_type": "hot_start", "agility_factor": 1.0, "time_kind": "main"},
    ]


def build_raw_blueprint_specs(ctx: dict) -> list[dict]:
    """动态排布并组合完整认知演进蓝图（打破固定 Slot 序号，保证因果拓扑约束）。"""
    main_mt, sub_01, tc = ctx["main_mt"], ctx["sub_01"], ctx["tc"]
    learn_map, test_map = ctx["slot_learn_map"], ctx["slot_test_map"]
    base_dur, ext_dur, main_env = tc["base_dur"], tc["ext_dur"], ctx["main_env_desc"]
    reh_dur = f"{tc.get('rehearsal_mins', 30)}min"

    foundational = _build_foundational_slots(ctx)
    middle_pool = _build_flexible_middle_pool(ctx)
    tail_slots = _build_tail_slots(ctx)

    evt_pair = [s for s in middle_pool if s["tag"] in ("evt_correct", "evt_reuse")]
    free_items = [s for s in middle_pool if s["tag"] not in ("evt_correct", "evt_reuse")]
    rng = random.Random(tc.get("seed_val", 1))
    rng.shuffle(free_items)

    insert_pos = rng.randint(1, max(1, len(free_items) - 1))
    ordered_free = free_items[:insert_pos] + evt_pair + free_items[insert_pos:]

    slots_4_to_15: list[dict] = []
    free_iter = iter(ordered_free)
    for slot_num in range(4, 16):
        if slot_num in learn_map:
            slots_4_to_15.append(make_experience_learn_slot(learn_map[slot_num], main_mt, sub_01, base_dur, ext_dur, main_env))
        elif slot_num in test_map:
            slots_4_to_15.append(make_experience_test_slot(test_map[slot_num], main_mt, base_dur, ext_dur, main_env, reh_dur=reh_dur))
        else:
            nxt = next(free_iter, None)
            if nxt is not None:
                slots_4_to_15.append(nxt)

    for rem in free_iter:
        slots_4_to_15.append(rem)

    return foundational + slots_4_to_15[:12] + tail_slots
