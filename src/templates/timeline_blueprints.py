"""
动态会话生命周期时间线蓝图配置模块。
定义了包含 7 种核心模版（T2-1, T2-2, T1-2, T2-5, X-1, T2-3, T1-1）的完整会话序列结构。
支持 daily / weekly / monthly 等多粒度周期与自定义起止时段的动态时间线计算。
支持根据画像与情境自然浮动（12 ~ 16 轮）。
"""

import re

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


def _generate_timeline_dates(storyline_trigger_type: str, period_type: str, days: list, count: int = 16) -> list[str]:
    """
    根据触发类型、周期粒度与设定日子生成严格单调递增的时间线日期列表（最多支持 20 个节点）。
    """
    days_str = " ".join(days or []).lower()

    if storyline_trigger_type == "time_periodic":
        if period_type == "daily":
            # 日级别：连续 20 天覆盖完整生命周期
            dates = [
                "2026年10月10日", "2026年10月11日", "2026年10月12日", "2026年10月13日",
                "2026年10月14日", "2026年10月15日", "2026年10月16日", "2026年10月17日",
                "2026年10月18日", "2026年10月19日", "2026年10月20日", "2026年10月21日",
                "2026年10月22日", "2026年10月23日", "2026年10月24日", "2026年10月25日",
                "2026年10月26日", "2026年10月27日", "2026年10月28日", "2026年10月29日"
            ]
        elif period_type == "monthly":
            # 月级别：跨 10月、11月、12月 的月度节点
            dates = [
                "2026年10月01日", "2026年10月02日", "2026年10月03日", "2026年10月08日",
                "2026年10月15日", "2026年10月22日", "2026年11月01日", "2026年11月02日",
                "2026年11月08日", "2026年11月12日", "2026年11月15日", "2026年11月18日",
                "2026年11月22日", "2026年11月26日", "2026年12月01日", "2026年12月05日",
                "2026年12月08日", "2026年12月12日", "2026年12月15日", "2026年12月20日"
            ]
        else:
            # 周级别：根据设定星期灵活分布
            if "monday" in days_str or "friday" in days_str:
                dates = [
                    "2026年10月05日", "2026年10月07日", "2026年10月09日", "2026年10月11日",
                    "2026年10月13日", "2026年10月14日", "2026年10月16日", "2026年10月19日",
                    "2026年10月21日", "2026年10月25日", "2026年10月30日", "2026年11月02日",
                    "2026年11月04日", "2026年11月05日", "2026年11月06日", "2026年11月09日",
                    "2026年11月11日", "2026年11月13日", "2026年11月16日", "2026年11月20日"
                ]
            elif "tuesday" in days_str or "thursday" in days_str:
                dates = [
                    "2026年10月06日", "2026年10月07日", "2026年10月08日", "2026年10月10日",
                    "2026年10月12日", "2026年10月14日", "2026年10月15日", "2026年10月20日",
                    "2026年10月21日", "2026年10月25日", "2026年10月27日", "2026年10月29日",
                    "2026年11月01日", "2026年11月02日", "2026年11月03日", "2026年11月05日",
                    "2026年11月07日", "2026年11月10日", "2026年11月12日", "2026年11月17日"
                ]
            elif "saturday" in days_str or "sunday" in days_str:
                dates = [
                    "2026年10月10日", "2026年10月11日", "2026年10月17日", "2026年10月18日",
                    "2026年10月20日", "2026年10月21日", "2026年10月24日", "2026年10月25日",
                    "2026年10月28日", "2026年10月29日", "2026年10月31日", "2026年11月01日",
                    "2026年11月04日", "2026年11月05日", "2026年11月07日", "2026年11月08日",
                    "2026年11月14日", "2026年11月15日", "2026年11月21日", "2026年11月22日"
                ]
            else:
                dates = [
                    "2026年10月07日", "2026年10月11日", "2026年10月14日", "2026年10月15日",
                    "2026年10月18日", "2026年10月21日", "2026年10月24日", "2026年10月28日",
                    "2026年10月29日", "2026年11月01日", "2026年11月04日", "2026年11月07日",
                    "2026年11月11日", "2026年11月15日", "2026年11月18日", "2026年11月20日",
                    "2026年11月22日", "2026年11月25日", "2026年11月28日", "2026年11月30日"
                ]
    else:
        # task_activity 或 location_environment
        dates = [
            "2026年10月07日", "2026年10月11日", "2026年10月14日", "2026年10月15日",
            "2026年10月18日", "2026年10月21日", "2026年10月24日", "2026年10月28日",
            "2026年10月29日", "2026年11月01日", "2026年11月04日", "2026年11月07日",
            "2026年11月11日", "2026年11月15日", "2026年11月18日", "2026年11月20日",
            "2026年11月22日", "2026年11月25日", "2026年11月28日", "2026年11月30日"
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
    target_count: int = 15,
) -> list[dict]:
    """
    根据目标数量（支持 12 ~ 16 轮动态浮动）生成自然时间线蓝图配置。
    动态结合主线设定的时间区间 (time_range) 与周期粒度 (period_type, days) 输出排期。
    """
    period_type = main_mt.get("period_type", "weekly")
    days = main_mt.get("days", [])
    time_range = main_mt.get("time_range", "14:00-16:00")

    sh_str, eh_str, ref_str, base_dur, ext_eh_str, ext_dur = _parse_time_range(time_range)

    # 格式化起止时间辅助函数
    def _m_time(d_str, t_str):
        parts = t_str.split(":")
        return f"{d_str}{parts[0]}时{parts[1]}分"

    # 全量 16 个候选骨架槽位
    candidate_slots = [
        # 1: Main Evidence (T2-1 首次建联证据 / 参数反问补全) - 核心必须
        {
            "tag": "main_evidence",
            "template_id": "T2-1",
            "role": "evidence_session",
            "source": main_mt,
            "type": "main",
            "dur": base_dur,
            "env": main_env_desc,
            "action": "declare_explicit_rule" if decl_mode == "explicit_declaration" else "single_task_implicit_behavior",
            "declaration_mode": decl_mode,
            "storyline_trigger_type": storyline_trigger_type,
            "trigger_condition": main_trigger_desc,
            "time_kind": "main"
        },
        # 2: Sub 1 Evidence (T2-2 歧义消解) - 核心必须
        {
            "tag": "sub1_evidence",
            "template_id": "T2-2",
            "role": "evidence_session",
            "source": sub_01,
            "type": "sub_01",
            "dur": "60min",
            "env": "大巴跨城转场高速公路",
            "action": "disambiguate_sub_storyline_1",
            "declaration_mode": "implicit_induction",
            "storyline_trigger_type": "location_environment",
            "trigger_condition": "大巴转场弱网环境",
            "time_kind": "sub1"
        },
        # 3: Main Reinforcement (T2-1 主线强化/固化契机) - 核心必须
        {
            "tag": "main_reinf_1",
            "template_id": "T2-1",
            "role": "reinforcement_session",
            "source": main_mt,
            "type": "main",
            "dur": base_dur,
            "env": main_env_desc,
            "action": "reinforce_explicit_memory" if decl_mode == "explicit_declaration" else "crystallize_implicit_memory",
            "declaration_mode": decl_mode,
            "storyline_trigger_type": storyline_trigger_type,
            "trigger_condition": main_trigger_desc,
            "time_kind": "main"
        },
        # 4: Sub 2 Evidence (T2-1 支线2建联) - 可选支线
        {
            "tag": "sub2",
            "template_id": "T2-1",
            "role": "evidence_session",
            "source": sub_02,
            "type": "sub_02",
            "dur": "90min",
            "env": "驻地酒店休息区",
            "action": "establish_sub_storyline_2",
            "declaration_mode": "implicit_induction",
            "storyline_trigger_type": "location_environment",
            "trigger_condition": "驻地酒店休息区",
            "time_kind": "sub2"
        },
        # 5: Distractor 1 (T1-2 纯域外拒绝，如宽带光纤报修) - 核心必须
        {
            "tag": "dist_ood",
            "template_id": "T1-2",
            "role": "distractor_session",
            "source": dist_01,
            "type": "distractor_ood",
            "dur": "30min",
            "env": "酒店临时办公区网络故障",
            "action": "reject_out_of_domain",
            "ood_goal": "宽带光纤装维报修",
            "time_kind": "dist_ood"
        },
        # 6: Sub 1 Reinforcement (T2-1 支线1复用/强化) - 核心必须
        {
            "tag": "sub1_reinf",
            "template_id": "T2-1",
            "role": "reinforcement_session",
            "source": sub_01,
            "type": "sub_01",
            "dur": "60min",
            "env": "大巴转场途中",
            "action": "reinforce_sub_storyline_1",
            "time_kind": "sub1"
        },
        # 7: Main Reuse (T2-5 变更延长时长) - 核心必须
        {
            "tag": "main_amend",
            "template_id": "T2-5",
            "role": "reuse_session",
            "source": main_mt,
            "type": "main",
            "dur": ext_dur,
            "base_dur": base_dur,
            "env": main_env_desc,
            "action": "extend_duration_amend",
            "storyline_trigger_type": storyline_trigger_type,
            "trigger_condition": main_trigger_desc,
            "time_kind": "main_amend"
        },
        # 8: Main Reinforcement 2 (T2-1 主线常规强化) - 核心必须
        {
            "tag": "main_reinf_2",
            "template_id": "T2-1",
            "role": "reinforcement_session",
            "source": main_mt,
            "type": "main",
            "dur": base_dur,
            "env": main_env_desc,
            "action": "reinforce_main_memory",
            "storyline_trigger_type": storyline_trigger_type,
            "trigger_condition": main_trigger_desc,
            "time_kind": "main"
        },
        # 9: Sub 2 Reinforcement (T2-1 支线2强化) - 可选支线
        {
            "tag": "sub2",
            "template_id": "T2-1",
            "role": "reinforcement_session",
            "source": sub_02,
            "type": "sub_02",
            "dur": "90min",
            "env": "驻地复盘业务",
            "action": "reinforce_sub_storyline_2",
            "time_kind": "sub2"
        },
        # 10: Distractor 2 (X-1 混合诉求一办一拒) - 核心必须
        {
            "tag": "dist_mixed",
            "template_id": "X-1",
            "role": "distractor_session",
            "source": dist_02,
            "type": "distractor_mixed",
            "dur": "60min",
            "env": "周末午休个人时间",
            "action": "mixed_in_out_domain",
            "ood_goal": "手机话费充值与账单查询",
            "time_kind": "dist_mixed"
        },
        # 11: Event Correction (T2-3 恶劣天气临时纠正覆盖) - 核心必须
        {
            "tag": "evt_correct",
            "template_id": "T2-3",
            "role": "correction_session",
            "source": main_mt,
            "type": "event_override",
            "dur": base_dur,
            "env": _extract_clean_event_env(evt_01, time_range),
            "action": "override_temporary_preference",
            "override": evt_01.get("preference_override", {}),
            "time_kind": "main"
        },
        # 12: Event Reuse (T2-1 临时纠正后恢复主线复用) - 核心必须
        {
            "tag": "evt_reuse",
            "template_id": "T2-1",
            "role": "reuse_session",
            "source": main_mt,
            "type": "event_reuse",
            "dur": base_dur,
            "env": _extract_clean_event_env(evt_01, time_range),
            "action": "reuse_long_term_rule_after_correction",
            "time_kind": "main"
        },
        # 13: Sub 1 Reuse (T2-1 支线隔离验证) - 核心必须
        {
            "tag": "sub1_reuse",
            "template_id": "T2-1",
            "role": "reuse_session",
            "source": sub_01,
            "type": "sub_01",
            "dur": "60min",
            "env": "转场大巴途中",
            "action": "sub_memory_unaffected",
            "time_kind": "sub1"
        },
        # 14: Distractor 3 (T1-1 单轮单次业务) - 可选单轮干扰
        {
            "tag": "dist_normal",
            "template_id": "T1-1",
            "role": "distractor_session",
            "source": dist_01,
            "type": "distractor",
            "dur": "30min",
            "env": "阶段工作总结会",
            "action": "distractor_no_memory",
            "time_kind": "dist_normal"
        },
        # 15: Event Expiry & Main Recovery (T2-1 临时失效主线恢复) - 核心必须
        {
            "tag": "main_recovery",
            "template_id": "T2-1",
            "role": "reuse_session",
            "source": main_mt,
            "type": "main_recovery",
            "dur": base_dur,
            "env": main_env_desc,
            "action": "recover_long_term_rule",
            "storyline_trigger_type": storyline_trigger_type,
            "trigger_condition": main_trigger_desc,
            "time_kind": "main"
        },
        # 16: Extra Main Reuse (T2-1 主线后续持续生效) - 可选第16轮
        {
            "tag": "extra_reuse",
            "template_id": "T2-1",
            "role": "reuse_session",
            "source": main_mt,
            "type": "main",
            "dur": base_dur,
            "env": main_env_desc,
            "action": "continuous_main_reuse",
            "storyline_trigger_type": storyline_trigger_type,
            "trigger_condition": main_trigger_desc,
            "time_kind": "main"
        }
    ]

    # 根据 target_count 精确过滤，保持结构合法与记忆因果完整性
    selected = []
    for slot in candidate_slots:
        tag = slot["tag"]
        if target_count <= 12:
            if tag in ["sub2", "dist_normal", "extra_reuse"]:
                continue
        elif target_count == 13:
            if tag in ["sub2", "extra_reuse"]:
                continue
        elif target_count == 14:
            if tag in ["dist_normal", "extra_reuse"]:
                continue
        elif target_count == 15:
            if tag in ["extra_reuse"]:
                continue
        selected.append(dict(slot))

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
        elif t_kind == "dist_normal":
            item["ref_time"] = f"{d_str}10时00分"
            item["start"] = f"{d_str}10时00分"
            item["end"] = f"{d_str}10时30分"

        final_blueprints.append(item)

    return final_blueprints

# 兼容既有调用
get_15_session_blueprints = get_session_blueprints
