"""
动态会话生命周期时间线蓝图配置模块。
定义了包含 7 种核心模版（T2-1, T2-2, T1-2, T2-5, X-1, T2-3, T1-1）的完整会话序列结构。
支持 daily / weekly / monthly 等多粒度周期与自定义起止时段的动态时间线计算。
支持根据画像与情境自然浮动（12 ~ 16 轮）。
"""

import re
from datetime import datetime

def _parse_time_range(time_range_str: str) -> tuple[str, str, str, str, str, str]:
    """
    解析 time_range 字符串（如 '20:00-22:00', '08:30-10:00'），
    返回 (start_time_str, end_time_str, ref_time_str, base_dur_str, ext_end_time_str, ext_dur_str)。
    """
    m = re.search(r'(\d{1,2}:\d{2})\s*[-~至到]\s*(\d{1,2}:\d{2})', time_range_str or "")
    if m:
        s_part = m.group(1).zfill(5)
        e_part = m.group(2).zfill(5)
    else:
        s_part = "14:00"
        e_part = "16:00"

    sh, sm = map(int, s_part.split(":"))
    eh, em = map(int, e_part.split(":"))

    base_minutes = (eh * 60 + em) - (sh * 60 + sm)
    if base_minutes <= 0:
        base_minutes = 120
        eh = (sh + 2) % 24
        e_part = f"{eh:02d}:{sm:02d}"

    base_dur_str = f"{base_minutes}min"

    # ref_time 提前 15 分钟
    ref_tot = (sh * 60 + sm) - 15
    if ref_tot < 0:
        ref_tot += 24 * 60
    ref_time_str = f"{ref_tot // 60:02d}:{ref_tot % 60:02d}"

    # T2-5 延长 60 分钟
    ext_minutes = base_minutes + 60
    ext_dur_str = f"{ext_minutes}min"
    ext_end_tot = (sh * 60 + sm) + ext_minutes
    ext_end_time_str = f"{(ext_end_tot // 60) % 24:02d}:{ext_end_tot % 60:02d}"

    return s_part, e_part, ref_time_str, base_dur_str, ext_end_time_str, ext_dur_str


def _extract_clean_event_env(evt: dict, time_range: str = "") -> str:
    """结合事件名称与描述提炼 4~8 字短现场名，并严格进行时段一致性校验（防止早晚时段打架）。"""
    name = evt.get("name", "") if isinstance(evt, dict) else ""
    desc = evt.get("scene_description", "") if isinstance(evt, dict) else ""
    text = f"{name} {desc}"

    patterns = [
        (r'公益赛事|赛事集结|赛事周', "公益赛事活动现场"),
        (r'棒球|球场|客场赛事', "棒球赛事活动现场"),
        (r'外业调查|实验现场|数据回传', "外业调查实验现场"),
        (r'音乐节|演出周|舞台', "城市音乐节现场"),
        (r'联合执法|巡逻线|检查点', "联合执法执勤现场"),
        (r'金融展会|展会外摆|商贸展', "跨境商贸展会现场"),
        (r'社区宣传|社区走访', "社区宣传走访现场"),
        (r'设计展|现场提案', "设计展提案现场"),
        (r'街区突发|转场直播|街巷', "城市街区采访现场"),
        (r'应急集结|夜间事故|处置点', "应急处置现场"),
        (r'联合实践|实践地|教学现场', "校际实践教学现场"),
        (r'搜救游泳|海岸线|码头', "搜救选拔赛事现场"),
        (r'模型交流|展览现场', "模型交流展会现场"),
        (r'儿童阅读|巡展现场', "儿童阅读巡展现场"),
        (r'喀斯喀特|登山口|集结区', "山脉赛事集结区"),
        (r'敬拜现场|录制周', "敬拜现场录制区"),
        (r'立法调研|草案冲刺', "立法调研办公现场"),
        (r'地质勘查|地质考察|科考营地', "野外地质勘查区"),
        (r'露天训练|高山露天', "高山露天训练场"),
        (r'道路巡逻|移动执勤', "道路巡逻执勤现场"),
    ]
    extracted = None
    for pat, loc in patterns:
        if re.search(pat, text):
            extracted = loc
            break

    if not extracted:
        clean_name = re.sub(r'(?:周|跨城|跨区域|跨校|联合|现场|冲刺|保障|外业)', '', name)
        clean_name = re.sub(r'[^\u4e00-\u9fa5]', '', clean_name)
        extracted = f"{clean_name[:4]}活动现场" if clean_name else "外勤保障现场"

    start_hour = None
    if time_range and "-" in time_range:
        try:
            start_hour = int(time_range.split("-")[0].split(":")[0])
        except Exception:
            pass

    if start_hour is not None:
        if start_hour >= 11 and any(kw in extracted for kw in ["早间", "早高峰", "晨间"]):
            extracted = extracted.replace("早间", "日间").replace("早高峰", "日常").replace("晨间", "日间")
        if start_hour < 17 and any(kw in extracted for kw in ["晚间", "夜间"]):
            extracted = extracted.replace("晚间", "日间").replace("夜间", "日间")

    return extracted


def _generate_timeline_dates(storyline_trigger_type: str, period_type: str, days: list, count: int = 22) -> list[str]:
    """
    根据触发类型、周期粒度与设定日子生成严格单调递增的时间线日期列表（支持 30 个节点）。
    """
    days_str = " ".join(days or []).lower()

    if storyline_trigger_type == "time_periodic":
        if period_type == "daily":
            dates = [
                "2026年10月10日", "2026年10月11日", "2026年10月12日", "2026年10月13日",
                "2026年10月14日", "2026年10月15日", "2026年10月16日", "2026年10月17日",
                "2026年10月18日", "2026年10月19日", "2026年10月20日", "2026年10月21日",
                "2026年10月22日", "2026年10月23日", "2026年10月24日", "2026年10月25日",
                "2026年10月26日", "2026年10月27日", "2026年10月28日", "2026年10月29日",
                "2026年10月30日", "2026年10月31日", "2026年11月01日", "2026年11月02日",
                "2026年11月03日", "2026年11月04日", "2026年11月05日", "2026年11月06日",
                "2026年11月07日", "2026年11月08日"
            ]
        elif period_type == "monthly":
            dates = [
                "2026年10月01日", "2026年10月02日", "2026年10月03日", "2026年10月05日",
                "2026年10月08日", "2026年10月11日", "2026年10月15日", "2026年10月18日",
                "2026年10月22日", "2026年10月26日", "2026年10月29日", "2026年11月01日",
                "2026年11月02日", "2026年11月05日", "2026年11月08日", "2026年11月12日",
                "2026年11月15日", "2026年11月18日", "2026年11月22日", "2026年11月26日",
                "2026年12月01日", "2026年12月05日", "2026年12月08日", "2026年12月12日",
                "2026年12月15日", "2026年12月18日", "2026年12月20日", "2026年12月25日"
            ]
        else:
            if "monday" in days_str or "friday" in days_str:
                dates = [
                    "2026年10月05日", "2026年10月07日", "2026年10月09日", "2026年10月11日",
                    "2026年10月13日", "2026年10月14日", "2026年10月16日", "2026年10月19日",
                    "2026年10月21日", "2026年10月25日", "2026年10月30日", "2026年11月02日",
                    "2026年11月04日", "2026年11月05日", "2026年11月06日", "2026年11月09日",
                    "2026年11月11日", "2026年11月13日", "2026年11月16日", "2026年11月20日",
                    "2026年11月23日", "2026年11月25日", "2026年11月27日", "2026年11月30日",
                    "2026年12月02日", "2026年12月04日", "2026年12月07日", "2026年12月11日"
                ]
            elif "tuesday" in days_str or "thursday" in days_str:
                dates = [
                    "2026年10月06日", "2026年10月07日", "2026年10月08日", "2026年10月10日",
                    "2026年10月12日", "2026年10月14日", "2026年10月15日", "2026年10月20日",
                    "2026年10月21日", "2026年10月25日", "2026年10月27日", "2026年10月29日",
                    "2026年11月01日", "2026年11月02日", "2026年11月03日", "2026年11月05日",
                    "2026年11月07日", "2026年11月10日", "2026年11月12日", "2026年11月17日",
                    "2026年11月19日", "2026年11月24日", "2026年11月26日", "2026年12月01日",
                    "2026年12月03日", "2026年12月08日", "2026年12月10日", "2026年12月15日"
                ]
            elif "saturday" in days_str or "sunday" in days_str:
                dates = [
                    "2026年10月10日", "2026年10月11日", "2026年10月17日", "2026年10月18日",
                    "2026年10月20日", "2026年10月21日", "2026年10月24日", "2026年10月25日",
                    "2026年10月28日", "2026年10月29日", "2026年10月31日", "2026年11月01日",
                    "2026年11月04日", "2026年11月05日", "2026年11月07日", "2026年11月08日",
                    "2026年11月14日", "2026年11月15日", "2026年11月21日", "2026年11月22日",
                    "2026年11月28日", "2026年11月29日", "2026年12月05日", "2026年12月06日",
                    "2026年12月12日", "2026年12月13日", "2026年12月19日", "2026年12月20日"
                ]
            else:
                dates = [
                    "2026年10月07日", "2026年10月11日", "2026年10月14日", "2026年10月15日",
                    "2026年10月18日", "2026年10月21日", "2026年10月24日", "2026年10月28日",
                    "2026年10月29日", "2026年11月01日", "2026年11月04日", "2026年11月07日",
                    "2026年11月11日", "2026年11月15日", "2026年11月18日", "2026年11月20日",
                    "2026年11月22日", "2026年11月25日", "2026年11月28日", "2026年11月30日",
                    "2026年12月02日", "2026年12月05日", "2026年12月08日", "2026年12月12日",
                    "2026年12月15日", "2026年12月18日", "2026年12月20日", "2026年12月25日"
                ]
    else:
        dates = [
            "2026年10月07日", "2026年10月11日", "2026年10月14日", "2026年10月15日",
            "2026年10月18日", "2026年10月21日", "2026年10月24日", "2026年10月28日",
            "2026年10月29日", "2026年11月01日", "2026年11月04日", "2026年11月07日",
            "2026年11月11日", "2026年11月15日", "2026年11月18日", "2026年11月20日",
            "2026年11月22日", "2026年11月25日", "2026年11月28日", "2026年11月30日",
            "2026年12月02日", "2026年12月05日", "2026年12月08日", "2026年12月12日",
            "2026年12月15日", "2026年12月18日", "2026年12月20日", "2026年12月25日"
        ]

    return dates[:count]


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
    time_range = main_mt.get("time_range", "14:00-16:00")

    sh_str, eh_str, ref_str, base_dur, ext_eh_str, ext_dur = _parse_time_range(time_range)

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
        return {
            "tag": f"exp_learn_{exp_id}",
            "template_id": "T2-1",
            "memory_tier": "experiential_memory",
            "role": "learning_session",
            "source": main_mt,
            "type": "experience_learning",
            "dur": base_dur,
            "env": main_env_desc,
            "action": "crystallize_experience_pitfall",
            "experience_id": exp_id,
            "round_count": 2,
            "cold_hot_type": None,
            "agility_factor": None,
            "time_kind": "main"
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
            "dur": "60min",
            "env": "大巴跨城转场高速公路",
            "action": "disambiguate_sub_storyline_1",
            "declaration_mode": "implicit_induction",
            "storyline_trigger_type": "location_environment",
            "trigger_condition": "大巴转场弱网环境",
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
            "round_count": 2,
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
            "round_count": 2,
            "cold_hot_type": None,
            "agility_factor": None,
            "time_kind": "main"
        }),
        # 7: S07 Main Duration Amend (T2-5 事实记忆局部时长修改 α=0.5 - 2轮)
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
            "round_count": 2,
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
        # 9: S09 Event Correction (T2-3 恶劣天气临时纠正覆盖 - 作用域仅限于当前任务 - 2轮)
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
            "round_count": 2,
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
            "time_kind": "main"
        } if 10 in slot_test_map else {
            "tag": "sub1_reuse_10",
            "template_id": "T2-1",
            "memory_tier": "factual_memory",
            "role": "reuse_session",
            "source": sub_01,
            "type": "sub_01",
            "dur": "60min",
            "env": "大巴跨城转场高速公路",
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
        # 12: S12 Experiential Quality Disambiguation (历史工单质量消歧迁移测试) 或 降级为工单常规复用
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
            "round_count": 2,
            "cold_hot_type": None,
            "agility_factor": None,
            "time_kind": "main"
        }),
        # 13: S13 Experiential Overlapping Resolution (工单时序重叠仲裁迁移测试) 或 降级为工单变更
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
            "dur": "30min",
            "env": "市政政务便民大厅",
            "action": "reject_out_of_domain",
            "ood_goal": "宽带光纤装维报修",
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
            "dur": "90min",
            "env": "驻地酒店商务中心",
            "action": "establish_sub_storyline_2",
            "declaration_mode": "implicit_induction",
            "storyline_trigger_type": "location_environment",
            "trigger_condition": "驻地酒店商务中心",
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
            "dur": "90min",
            "env": "驻地酒店商务中心",
            "action": "reuse_sub_storyline_2",
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
            "dur": "30min",
            "env": "街区便民服务站",
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
    final_blueprints = []
    for i, s in enumerate(selected):
        d_str = dates[i]
        t_kind = s["time_kind"]
        item = dict(s)
        item["idx"] = i + 1

        if t_kind == "main":
            item["ref_time"] = _m_time(d_str, ref_str)
            item["start"] = _m_time(d_str, sh_str)
            item["end"] = _m_time(d_str, eh_str)
        elif t_kind == "main_amend":
            item["ref_time"] = _m_time(d_str, ref_str)
            item["start"] = _m_time(d_str, sh_str)
            item["end"] = _m_time(d_str, ext_eh_str)
            item["base_end"] = _m_time(d_str, eh_str)
        elif t_kind == "prewarm":
            item["ref_time"] = _m_time(d_str, ref_str)
            item["start"] = _m_time(d_str, pw_s_str)
            item["end"] = _m_time(d_str, eh_str)
            item["dur"] = pw_dur_str
            item["nominal_start"] = _m_time(d_str, sh_str)
            item["nominal_dur"] = base_dur
        elif t_kind == "holiday":
            # 顺延至国庆长假后首个工作日办理 (2026年10月08日)
            defer_date = "2026年10月08日"
            item["ref_time"] = _m_time(d_str, ref_str)
            item["start"] = _m_time(defer_date, sh_str)
            item["end"] = _m_time(defer_date, eh_str)
            item["nominal_start"] = _m_time(d_str, sh_str)
            item["nominal_end"] = _m_time(d_str, eh_str)
            item["holiday_defer_date"] = defer_date
        elif t_kind == "overlap":
            item["ref_time"] = f"{d_str}14时45分"
            item["start"] = f"{d_str}15时00分"
            item["end"] = f"{d_str}17时00分"
            item["dur"] = "120min"
        elif t_kind == "sub1":
            item["ref_time"] = f"{d_str}18时30分"
            item["start"] = f"{d_str}18时45分"
            item["end"] = f"{d_str}19时45分"
        elif t_kind == "sub2":
            item["ref_time"] = f"{d_str}20时00分"
            item["start"] = f"{d_str}20时15分"
            item["end"] = f"{d_str}21时45分"
        elif t_kind == "dist_ood":
            item["ref_time"] = f"{d_str}10时00分"
            item["start"] = f"{d_str}10时00分"
            item["end"] = f"{d_str}10时30分"
        elif t_kind == "dist_mixed":
            item["ref_time"] = f"{d_str}12时30分"
            item["start"] = f"{d_str}12时30分"
            item["end"] = f"{d_str}13时30分"
            m_date = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', d_str)
            if m_date:
                dt = datetime(int(m_date.group(1)), int(m_date.group(2)), int(m_date.group(3)))
                if dt.weekday() in [5, 6]:
                    item["env"] = "周末午休个人时间"
                else:
                    item["env"] = "工作日午休个人时间"
            else:
                item["env"] = "午休个人时间"
        elif t_kind == "dist_normal":
            item["ref_time"] = f"{d_str}10时00分"
            item["start"] = f"{d_str}10时00分"
            item["end"] = f"{d_str}10时30分"

        final_blueprints.append(item)

    return final_blueprints

# 兼容既有调用
get_15_session_blueprints = get_session_blueprints
