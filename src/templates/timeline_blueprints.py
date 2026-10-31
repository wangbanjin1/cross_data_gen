"""
动态会话生命周期时间线蓝图配置模块。
定义了包含 7 种核心模版（T2-1, T2-2, T1-2, T2-5, X-1, T2-3, T1-1）的完整会话序列结构。
支持 daily / weekly / monthly 等多粒度周期与自定义起止时段的动态时间线计算。
支持根据画像与情境自然浮动（12 ~ 16 轮）。
"""


from __future__ import annotations

from src.templates.blueprint_helpers import (
    _extract_clean_event_env,
    _generate_timeline_dates,
    _m_time,
    _parse_time_range,
    assign_blueprint_timestamps,
)


def get_session_blueprints(
    main_mt: dict,
    sub_01: dict,
    sub_02: dict,
    dist_01: dict,
    dist_02: dict,
    evt_01: dict,
    decl_mode: str,
    storyline_trigger_type: str,
    main_env_desc: str,
    main_trigger_desc: str,
    target_count: int = 22,
    selected_exp_ids: list[str] = None,
) -> list[dict]:
    """
    根据目标数量（支持 16 ~ 22 轮深层认知演进）生成自然时间线蓝图配置。
    动态结合主线设定的时间区间 (time_range) 与周期粒度 (period_type, days) 输出排期。
    动态结合画像适配的 1~2 个经验记忆卡片 (selected_exp_ids) 规划对应经验插槽。
    """
    if selected_exp_ids is None:
        selected_exp_ids = ["EXP_PREWARM_BUFFER_01", "EXP_MULTI_INTENT_PARTITION_01"]

    period_type = main_mt.get("period_type", "weekly")
    days = main_mt.get("days", [])
    time_range = main_mt.get("time_range", "14:00-15:30")

    # 根据主线与支线信息生成稳定但多样化的确定性种子，避免所有用户在时长增量、支线时段、干扰项上千篇一律
    seed_str = f"{main_mt.get('name', '')}|{time_range}|{main_env_desc}|{sub_01.get('name', '')}|{sub_02.get('name', '')}"
    seed_val = sum((idx + 1) * ord(ch) for idx, ch in enumerate(seed_str))

    ext_add_choices = [30, 60, 90]
    ext_add_mins = main_mt.get("ext_add_minutes") or ext_add_choices[seed_val % len(ext_add_choices)]
    sh_str, eh_str, ref_str, base_dur, ext_eh_str, ext_dur = _parse_time_range(time_range, ext_add_minutes=ext_add_mins)

    # 动态解析或派生支线1、支线2与干扰会话的灵活时段、时长与环境
    sub1_time_presets = [
        ("18:30", "19:15", "18:15", "45min", "大巴跨城转场高速公路", "大巴转场弱网环境"),
        ("18:45", "19:45", "18:30", "60min", "大巴跨城转场高速公路", "大巴转场弱网环境"),
        ("17:30", "19:00", "17:15", "90min", "城际高铁移动车厢", "城际高铁转场环境"),
        ("19:00", "20:00", "18:45", "60min", "机场摆渡候机长廊", "候机转场弱网环境"),
        ("12:30", "13:15", "12:15", "45min", "园区通勤班车途中", "通勤班车移动环境"),
    ]
    sub1_s, sub1_e, sub1_ref, sub1_dur, sub1_default_env, sub1_default_trig = sub1_time_presets[seed_val % len(sub1_time_presets)]
    if sub_01.get("time_range"):
        sub1_s, sub1_e, sub1_ref, sub1_dur, _, _ = _parse_time_range(sub_01["time_range"])
    sub1_env = sub_01.get("env") or sub1_default_env
    sub1_trig = sub_01.get("trigger_condition") or sub1_default_trig

    sub2_time_presets = [
        ("20:00", "21:00", "19:45", "60min", "驻地酒店商务中心"),
        ("20:15", "21:45", "20:00", "90min", "驻地酒店商务中心"),
        ("20:30", "22:30", "20:15", "120min", "异地差旅酒店会议室"),
        ("19:30", "20:15", "19:15", "45min", "联合办公共享会议间"),
        ("21:00", "22:30", "20:45", "90min", "驻地公寓商务工作间"),
    ]
    sub2_s, sub2_e, sub2_ref, sub2_dur, sub2_default_env = sub2_time_presets[(seed_val // 3) % len(sub2_time_presets)]
    if sub_02.get("time_range"):
        sub2_s, sub2_e, sub2_ref, sub2_dur, _, _ = _parse_time_range(sub_02["time_range"])
    sub2_env = sub_02.get("env") or sub2_default_env

    ood_presets = [
        ("10:00", "10:30", "30min", "市政政务便民大厅", "宽带光纤装维报修"),
        ("09:30", "10:15", "45min", "社区便民综合服务站", "家庭路由器上门组网调试"),
        ("11:00", "12:00", "60min", "政企营业厅前台", "手机国际漫游套餐退订与账单申诉"),
        ("14:30", "15:00", "30min", "园区物业服务中心", "地下车库宽带专线移机办理"),
        ("16:00", "16:45", "45min", "街道综合服务中心", "固话座机故障报修与移机"),
    ]
    ood_s, ood_e, ood_dur, ood_env, ood_goal_default = ood_presets[(seed_val // 5) % len(ood_presets)]

    dist_norm_presets = [
        ("10:00", "10:30", "30min", "街区便民服务站"),
        ("10:30", "11:15", "45min", "临街咖啡厅休息区"),
        ("11:00", "12:00", "60min", "商场中庭公共休息区"),
        ("15:30", "16:30", "60min", "园区商务访客洽谈室"),
        ("16:30", "18:00", "90min", "市民中心便民等候区"),
    ]
    dn_s, dn_e, dn_dur, dn_env = dist_norm_presets[(seed_val // 7) % len(dist_norm_presets)]

    def _m_time(d_str, t_str):
        parts = t_str.split(":")
        return f"{d_str}{parts[0]}时{parts[1]}分"

    # 建立每个被挑选经验的 (学习铺垫轮 learn_slot, 迁移测试轮 test_slot) 配对计划
    NATURAL_TEST_SLOTS = {
        "EXP_CALENDAR_HOLIDAY_EXCEPTION_01": 6,
        "EXP_PREWARM_BUFFER_01": 8,
        "EXP_MULTI_INTENT_PARTITION_01": 10,
        "EXP_ORDER_QUALITY_DISAMBIGUATION_01": 12,
        "EXP_OVERLAPPING_ORDER_RESOLUTION_01": 13,
    }
    sorted_exps = sorted(selected_exp_ids or [], key=lambda x: NATURAL_TEST_SLOTS.get(x, 99))
    exp_plan = {}
    if len(sorted_exps) == 1:
        e1 = sorted_exps[0]
        t1 = NATURAL_TEST_SLOTS.get(e1, 8)
        l1 = 4 if t1 == 6 else 5
        exp_plan[e1] = {"learn_slot": l1, "test_slot": t1}
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

    def _make_learn_slot(slot_idx, exp_id):
        if exp_id == "EXP_CALENDAR_HOLIDAY_EXCEPTION_01":
            t_kind = "holiday"
        elif exp_id == "EXP_MULTI_INTENT_PARTITION_01":
            t_kind = "multi_intent"
        elif exp_id == "EXP_OVERLAPPING_ORDER_RESOLUTION_01":
            t_kind = "overlap"
        elif exp_id == "EXP_PREWARM_BUFFER_01":
            t_kind = "prewarm"
        else:
            t_kind = "main"
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
            "time_kind": t_kind
        }

    candidate_slots = [
        # 1: S01 Main Evidence (T2-1 冷启动无记忆多轮澄清线 - 3轮反问澄清完整闭环)
        {
            "tag": "main_evidence",
            "template_id": "T2-1",
            "memory_tier": "factual_memory",
            "role": "evidence_session",
            "source": main_mt,
            "type": "main",
            "dur": base_dur,
            "env": main_env_desc,
            "action": "declare_explicit_rule" if decl_mode == "explicit_declaration" else "single_task_implicit_behavior",
            "declaration_mode": decl_mode,
            "storyline_trigger_type": storyline_trigger_type,
            "trigger_condition": main_trigger_desc,
            "round_count": 3,
            "cold_hot_type": "cold_start",
            "agility_factor": 0.0,
            "time_kind": "main"
        },
        # 2: S02 Sub 1 Evidence (T3-1 支线1冷启动跨轮消歧建联 - 3轮)
        {
            "tag": "sub1_evidence",
            "template_id": "T3-1",
            "memory_tier": "factual_memory",
            "role": "evidence_session",
            "source": sub_01,
            "type": "sub_01",
            "dur": sub1_dur,
            "env": sub1_env,
            "action": "disambiguate_sub_storyline_1",
            "declaration_mode": "implicit_induction",
            "storyline_trigger_type": "location_environment",
            "trigger_condition": sub1_trig,
            "round_count": 3,
            "cold_hot_type": "cold_start",
            "agility_factor": 0.0,
            "time_kind": "sub1"
        },
        # 3: S03 Main Reinforcement (T2-1 事实记忆常规稳健热启动 α=0.5 - 2轮)
        {
            "tag": "main_reinf_1",
            "template_id": "T2-1",
            "memory_tier": "factual_memory",
            "role": "reinforcement_session",
            "source": main_mt,
            "type": "main",
            "dur": base_dur,
            "env": main_env_desc,
            "action": "reinforce_explicit_memory" if decl_mode == "explicit_declaration" else "crystallize_implicit_memory",
            "declaration_mode": decl_mode,
            "storyline_trigger_type": storyline_trigger_type,
            "trigger_condition": main_trigger_desc,
            "round_count": 2,
            "cold_hot_type": "hot_start",
            "agility_factor": 0.5,
            "time_kind": "main"
        },
        # 4: S04 Working Memory Reuse 或 经验学习铺垫轮 (若配对计划命中)
        _make_learn_slot(4, slot_learn_map[4]) if 4 in slot_learn_map else {
            "tag": "wm_reuse",
            "template_id": "T2-6",
            "memory_tier": "working_memory",
            "role": "reuse_session",
            "source": main_mt,
            "type": "working_record_reuse",
            "dur": base_dur,
            "env": main_env_desc,
            "action": "retrieve_working_record_reuse",
            "round_count": 3,
            "cold_hot_type": None,
            "agility_factor": None,
            "time_kind": "main"
        },
        # 5: S05 经验学习铺垫轮 (踩坑反思沉淀) 或 工作记忆变更 (T2-7)
        _make_learn_slot(5, slot_learn_map[5]) if 5 in slot_learn_map else {
            "tag": "wm_reschedule",
            "template_id": "T2-7",
            "memory_tier": "working_memory",
            "role": "reuse_session",
            "source": main_mt,
            "type": "working_record_reschedule",
            "dur": base_dur,
            "env": main_env_desc,
            "action": "reschedule_working_record",
            "round_count": 2,
            "cold_hot_type": None,
            "agility_factor": None,
            "time_kind": "main"
        },
        # 6: S06 经验学习铺垫 / 节假日迁移测试 / 工作记忆复用
        _make_learn_slot(6, slot_learn_map[6]) if 6 in slot_learn_map else ({
            "tag": "exp_holiday",
            "template_id": "T2-1",
            "memory_tier": "experiential_memory",
            "role": "reuse_session",
            "source": main_mt,
            "type": "proactive_experience",
            "dur": base_dur,
            "env": main_env_desc,
            "action": "holiday_avoidance_reschedule",
            "experience_id": "EXP_CALENDAR_HOLIDAY_EXCEPTION_01",
            "learning_source_session_tag": "exp_learn_EXP_CALENDAR_HOLIDAY_EXCEPTION_01",
            "round_count": 2,
            "cold_hot_type": None,
            "agility_factor": None,
            "time_kind": "holiday"
        } if 6 in slot_test_map else {
            "tag": "wm_reuse_6",
            "template_id": "T2-6",
            "memory_tier": "working_memory",
            "role": "reuse_session",
            "source": main_mt,
            "type": "working_record_reuse",
            "dur": base_dur,
            "env": main_env_desc,
            "action": "retrieve_working_record_reuse",
            "round_count": 3,
            "cold_hot_type": None,
            "agility_factor": None,
            "time_kind": "main"
        }),
        # 7: S07 Main Duration Amend (T2-5 事实记忆局部时长修改 α=0.5 - 3轮修改再确认闭环)
        {
            "tag": "main_amend",
            "template_id": "T2-5",
            "memory_tier": "factual_memory",
            "role": "reuse_session",
            "source": main_mt,
            "type": "main",
            "dur": ext_dur,
            "base_dur": base_dur,
            "env": main_env_desc,
            "action": "extend_duration_amend",
            "storyline_trigger_type": storyline_trigger_type,
            "trigger_condition": main_trigger_desc,
            "round_count": 3,
            "cold_hot_type": "hot_start",
            "agility_factor": 0.5,
            "time_kind": "main_amend"
        },
        # 8: S08 经验学习铺垫 / 预热试机迁移测试 / 事实记忆强化
        _make_learn_slot(8, slot_learn_map[8]) if 8 in slot_learn_map else ({
            "tag": "exp_prewarm",
            "template_id": "T2-9",
            "memory_tier": "experiential_memory",
            "role": "reuse_session",
            "source": main_mt,
            "type": "proactive_experience",
            "dur": ext_dur,
            "base_dur": base_dur,
            "env": "奥林匹克体育中心多功能馆",
            "action": "prewarm_buffer_calculation",
            "experience_id": "EXP_PREWARM_BUFFER_01",
            "learning_source_session_tag": "exp_learn_EXP_PREWARM_BUFFER_01",
            "round_count": 2,
            "cold_hot_type": None,
            "agility_factor": None,
            "time_kind": "prewarm"
        } if 8 in slot_test_map else {
            "tag": "main_reinf_8",
            "template_id": "T2-1",
            "memory_tier": "factual_memory",
            "role": "reinforcement_session",
            "source": main_mt,
            "type": "main",
            "dur": base_dur,
            "env": main_env_desc,
            "action": "reinforce_explicit_memory" if decl_mode == "explicit_declaration" else "crystallize_implicit_memory",
            "declaration_mode": decl_mode,
            "storyline_trigger_type": storyline_trigger_type,
            "trigger_condition": main_trigger_desc,
            "round_count": 2,
            "cold_hot_type": "hot_start",
            "agility_factor": 0.5,
            "time_kind": "main"
        }),
        # 9: S09 Event Correction (T2-3 恶劣天气临时纠正覆盖 - 作用域仅限于当前任务 - 3轮纠偏再确认闭环)
        {
            "tag": "evt_correct",
            "template_id": "T2-3",
            "memory_tier": "factual_memory",
            "role": "correction_session",
            "source": main_mt,
            "type": "event_override",
            "dur": base_dur,
            "env": "沿海暴雨强对流前沿现场",
            "action": "override_temporary_preference",
            "override": evt_01.get("preference_override", {"resolution": "720p", "rtt_max": "30ms"}),
            "round_count": 3,
            "cold_hot_type": "hot_start",
            "agility_factor": 0.5,
            "time_kind": "main"
        },
        # 10: S10 Experiential Multi-Intent Partition (多任务因果隔离迁移测试) 或 降级为支线1复用
        ({
            "tag": "exp_multi_intent",
            "template_id": "T2-4",
            "memory_tier": "experiential_memory",
            "role": "reuse_session",
            "source": main_mt,
            "second_source": sub_01,
            "type": "multi_intent_experience",
            "dur": ext_dur,
            "base_dur": base_dur,
            "env": main_env_desc,
            "action": "multi_intent_delay_isolation",
            "experience_id": "EXP_MULTI_INTENT_PARTITION_01",
            "learning_source_session_tag": "exp_learn_EXP_MULTI_INTENT_PARTITION_01",
            "round_count": 2,
            "cold_hot_type": None,
            "agility_factor": None,
            "time_kind": "multi_intent"
        } if 10 in slot_test_map else {
            "tag": "sub1_reuse_10",
            "template_id": "T2-1",
            "memory_tier": "factual_memory",
            "role": "reuse_session",
            "source": sub_01,
            "type": "sub_01",
            "dur": sub1_dur,
            "env": sub1_env,
            "action": "reuse_sub_storyline_1",
            "round_count": 2,
            "cold_hot_type": "hot_start",
            "agility_factor": 0.5,
            "time_kind": "sub1"
        }),
        # 11: S11 Event Reuse & Scope Isolation (T2-1 事实记忆长期老规矩自动恢复 - 隔离检验 α=0.5 - 2轮)
        {
            "tag": "evt_reuse",
            "template_id": "T2-1",
            "memory_tier": "factual_memory",
            "role": "reuse_session",
            "source": main_mt,
            "type": "event_reuse",
            "dur": base_dur,
            "env": main_env_desc,
            "action": "reuse_long_term_rule_after_correction",
            "round_count": 2,
            "cold_hot_type": "hot_start",
            "agility_factor": 0.5,
            "time_kind": "main"
        },
        # 12: S12 Experiential Quality Disambiguation (历史意图保障单高规格优选消歧迁移测试) 或 降级为意图保障单常规复用
        ({
            "tag": "exp_quality",
            "template_id": "T2-6",
            "memory_tier": "experiential_memory",
            "role": "reuse_session",
            "source": main_mt,
            "type": "working_record_disambig",
            "dur": base_dur,
            "env": main_env_desc,
            "action": "quality_log_disambiguation",
            "experience_id": "EXP_ORDER_QUALITY_DISAMBIGUATION_01",
            "learning_source_session_tag": "exp_learn_EXP_ORDER_QUALITY_DISAMBIGUATION_01",
            "round_count": 2,
            "cold_hot_type": None,
            "agility_factor": None,
            "time_kind": "main"
        } if 12 in slot_test_map else {
            "tag": "wm_reuse_12",
            "template_id": "T2-6",
            "memory_tier": "working_memory",
            "role": "reuse_session",
            "source": main_mt,
            "type": "working_record_reuse",
            "dur": base_dur,
            "env": main_env_desc,
            "action": "retrieve_working_record_reuse",
            "round_count": 3,
            "cold_hot_type": None,
            "agility_factor": None,
            "time_kind": "main"
        }),
        # 13: S13 Experiential Overlapping Resolution (意图保障单时序重叠仲裁迁移测试) 或 降级为意图保障单变更
        ({
            "tag": "exp_overlap",
            "template_id": "T2-10",
            "memory_tier": "experiential_memory",
            "role": "reuse_session",
            "source": main_mt,
            "type": "overlapping_experience",
            "dur": base_dur,
            "env": main_env_desc,
            "action": "overlapping_order_handoff",
            "experience_id": "EXP_OVERLAPPING_ORDER_RESOLUTION_01",
            "learning_source_session_tag": "exp_learn_EXP_OVERLAPPING_ORDER_RESOLUTION_01",
            "round_count": 2,
            "cold_hot_type": None,
            "agility_factor": None,
            "time_kind": "overlap"
        } if 13 in slot_test_map else {
            "tag": "wm_reschedule_13",
            "template_id": "T2-7",
            "memory_tier": "working_memory",
            "role": "reuse_session",
            "source": main_mt,
            "type": "working_record_reschedule",
            "dur": base_dur,
            "env": main_env_desc,
            "action": "reschedule_working_record",
            "round_count": 2,
            "cold_hot_type": None,
            "agility_factor": None,
            "time_kind": "main"
        }),
        # 14: S14 Working Memory Reschedule Advance (T2-7 第二次预约变更 - 提前开始 - 2轮)
        {
            "tag": "wm_reschedule_2",
            "template_id": "T2-7",
            "memory_tier": "working_memory",
            "role": "reuse_session",
            "source": main_mt,
            "type": "working_record_reschedule",
            "dur": base_dur,
            "env": main_env_desc,
            "action": "reschedule_working_record",
            "round_count": 2,
            "cold_hot_type": None,
            "agility_factor": None,
            "time_kind": "main"
        },
        # 15: S15 Out of Domain Distractor (T1-2 域外诉求拒识 - 1轮)
        {
            "tag": "dist_ood",
            "template_id": "T1-2",
            "memory_tier": "factual_memory",
            "role": "distractor_session",
            "source": main_mt,
            "type": "distractor_ood",
            "dur": ood_dur,
            "env": ood_env,
            "action": "reject_out_of_domain",
            "ood_goal": dist_02.get("ood_goal") or ood_goal_default,
            "round_count": 1,
            "cold_hot_type": None,
            "agility_factor": None,
            "time_kind": "dist_ood"
        },
        # 16: S16 Working Memory Disambiguation (T2-6 工作记忆多候选消歧 - 3轮深度交互)
        {
            "tag": "wm_disambig",
            "template_id": "T2-6",
            "memory_tier": "working_memory",
            "role": "reuse_session",
            "source": main_mt,
            "type": "working_record_disambig",
            "dur": base_dur,
            "env": main_env_desc,
            "action": "disambiguate_working_record",
            "round_count": 3,
            "cold_hot_type": None,
            "agility_factor": None,
            "time_kind": "main"
        },
        # 17: S17 Sub 2 Evidence (T2-1 支线2冷启动建联 - 3轮)
        {
            "tag": "sub2",
            "template_id": "T2-1",
            "memory_tier": "factual_memory",
            "role": "evidence_session",
            "source": sub_02,
            "type": "sub_02",
            "dur": sub2_dur,
            "env": sub2_env,
            "action": "establish_sub_storyline_2",
            "declaration_mode": "implicit_induction",
            "storyline_trigger_type": "location_environment",
            "trigger_condition": sub2_env,
            "round_count": 3,
            "cold_hot_type": "cold_start",
            "agility_factor": 0.0,
            "time_kind": "sub2"
        },
        # 18: S18 Sub 2 Reuse (T2-1 支线2常规复用 - 2轮)
        {
            "tag": "sub2_reuse",
            "template_id": "T2-1",
            "memory_tier": "factual_memory",
            "role": "reuse_session",
            "source": sub_02,
            "type": "sub_02",
            "dur": sub2_dur,
            "env": sub2_env,
            "action": "reuse_sub_storyline_2",
            "storyline_trigger_type": "location_environment",
            "trigger_condition": sub2_env,
            "round_count": 2,
            "cold_hot_type": "hot_start",
            "agility_factor": 0.5,
            "time_kind": "sub2"
        },
        # 19: S19 Distractor Normal (T1-1 单轮单次业务干扰 - 1轮)
        {
            "tag": "dist_normal",
            "template_id": "T1-1",
            "memory_tier": "factual_memory",
            "role": "distractor_session",
            "source": dist_01,
            "type": "distractor_normal",
            "dur": dn_dur,
            "env": dist_01.get("env") or dn_env,
            "action": "single_standard_assurance",
            "round_count": 1,
            "cold_hot_type": None,
            "agility_factor": None,
            "time_kind": "dist_normal"
        },
        # 20: S20 Main Final Verification (T2-1 终局极致敏捷终检 α=1.0 - 1轮极速闭环)
        {
            "tag": "main_final",
            "template_id": "T2-1",
            "memory_tier": "factual_memory",
            "role": "reuse_session",
            "source": main_mt,
            "type": "main_recovery",
            "dur": base_dur,
            "env": main_env_desc,
            "action": "recover_long_term_rule",
            "storyline_trigger_type": storyline_trigger_type,
            "trigger_condition": main_trigger_desc,
            "round_count": 1,
            "cold_hot_type": "hot_start",
            "agility_factor": 1.0,
            "time_kind": "main"
        }
    ]

    selected = [dict(slot) for slot in candidate_slots[:target_count]]

    # 计算预热试机提前30分钟参数 (用于 S08 EXP_PREWARM_BUFFER_01)
    sh_val, sm_val = map(int, sh_str.split(":"))
    eh_val, em_val = map(int, eh_str.split(":"))
    base_mins_val = (eh_val * 60 + em_val) - (sh_val * 60 + sm_val)
    if base_mins_val <= 0:
        base_mins_val = 120
    pw_sh_tot = (sh_val * 60 + sm_val) - 30
    if pw_sh_tot < 0:
        pw_sh_tot += 24 * 60
    pw_s_str = f"{pw_sh_tot // 60:02d}:{pw_sh_tot % 60:02d}"
    pw_dur_str = f"{base_mins_val + 30}min"

    # 生成严格匹配数量的日期列表
    dates = _generate_timeline_dates(storyline_trigger_type, period_type, days, count=len(selected))

    # 查找事件纠正与复用的日期并更新 evt_01 起止
    evt_corr_idx = next((i for i, s in enumerate(selected) if s["tag"] == "evt_correct"), 10)
    evt_reuse_idx = next((i for i, s in enumerate(selected) if s["tag"] == "evt_reuse"), evt_corr_idx + 1)
    if evt_corr_idx < len(dates):
        evt_01["start_time"] = f"{dates[evt_corr_idx]}00时00分"
    if evt_reuse_idx < len(dates):
        evt_01["end_time"] = f"{dates[evt_reuse_idx]}23时59分"

    # 填充具体起止时间与流水编号
    return assign_blueprint_timestamps(
        selected=selected,
        dates=dates,
        ref_str=ref_str,
        sh_str=sh_str,
        eh_str=eh_str,
        ext_eh_str=ext_eh_str,
        base_dur=base_dur,
        pw_s_str=pw_s_str,
        pw_dur_str=pw_dur_str,
        sub1_ref=sub1_ref,
        sub1_s=sub1_s,
        sub1_e=sub1_e,
        sub2_ref=sub2_ref,
        sub2_s=sub2_s,
        sub2_e=sub2_e,
        ood_s=ood_s,
        ood_e=ood_e,
        dn_s=dn_s,
        dn_e=dn_e,
    )

# 兼容既有调用
get_15_session_blueprints = get_session_blueprints
