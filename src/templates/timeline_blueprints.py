"""
15 会话生命周期时间线蓝图配置模块。
定义了包含 8 种模版（T2-4, T2-2, T2-1, T1-2, T2-5, X-1, T2-3, T1-1）的完整会话序列结构。
支持 daily / weekly / monthly 等多粒度周期与自定义起止时段的动态时间线计算。
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


def _generate_15_dates(storyline_trigger_type: str, period_type: str, days: list) -> list[str]:
    """
    根据触发类型、周期粒度与设定日子生成严格单调递增的 15 会话日期。
    """
    days_str = " ".join(days or []).lower()

    if storyline_trigger_type == "time_periodic":
        if period_type == "daily":
            # 日级别：连续 15 天覆盖完整生命周期
            return [
                "2026年10月10日", "2026年10月11日", "2026年10月12日", "2026年10月13日",
                "2026年10月14日", "2026年10月15日", "2026年10月16日", "2026年10月17日",
                "2026年10月18日", "2026年10月19日", "2026年10月20日", "2026年10月21日",
                "2026年10月22日", "2026年10月23日", "2026年10月24日"
            ]
        elif period_type == "monthly":
            # 月级别：跨 10月、11月、12月 的月度节点
            return [
                "2026年10月01日", "2026年10月02日", "2026年10月03日", "2026年10月08日",
                "2026年10月15日", "2026年10月22日", "2026年11月01日", "2026年11月02日",
                "2026年11月08日", "2026年11月12日", "2026年11月15日", "2026年11月18日",
                "2026年11月22日", "2026年11月26日", "2026年12月01日"
            ]
        else:
            # 周级别：根据设定星期灵活分布
            if "monday" in days_str or "friday" in days_str:
                # 周一与周五组合（10月5日为周一）
                return [
                    "2026年10月05日", "2026年10月07日", "2026年10月09日", "2026年10月11日",
                    "2026年10月13日", "2026年10月14日", "2026年10月16日", "2026年10月19日",
                    "2026年10月21日", "2026年10月25日", "2026年10月30日", "2026年11月02日",
                    "2026年11月04日", "2026年11月05日", "2026年11月06日"
                ]
            elif "tuesday" in days_str or "thursday" in days_str:
                # 周二与周四组合（10月6日为周二）
                return [
                    "2026年10月06日", "2026年10月07日", "2026年10月08日", "2026年10月10日",
                    "2026年10月12日", "2026年10月14日", "2026年10月15日", "2026年10月20日",
                    "2026年10月21日", "2026年10月25日", "2026年10月27日", "2026年10月29日",
                    "2026年11月01日", "2026年11月02日", "2026年11月03日"
                ]
            elif "saturday" in days_str or "sunday" in days_str:
                # 周末双休专场（10月10日为周六）
                return [
                    "2026年10月10日", "2026年10月11日", "2026年10月17日", "2026年10月18日",
                    "2026年10月20日", "2026年10月21日", "2026年10月24日", "2026年10月25日",
                    "2026年10月28日", "2026年10月29日", "2026年10月31日", "2026年11月01日",
                    "2026年11月04日", "2026年11月05日", "2026年11月07日"
                ]
            else:
                # 默认周三周六或其他周组合
                return [
                    "2026年10月07日", "2026年10月11日", "2026年10月14日", "2026年10月15日",
                    "2026年10月18日", "2026年10月21日", "2026年10月24日", "2026年10月28日",
                    "2026年10月29日", "2026年11月01日", "2026年11月04日", "2026年11月07日",
                    "2026年11月11日", "2026年11月15日", "2026年11月18日"
                ]

    # task_activity 或 location_environment
    return [
        "2026年10月07日", "2026年10月11日", "2026年10月14日", "2026年10月15日",
        "2026年10月18日", "2026年10月21日", "2026年10月24日", "2026年10月28日",
        "2026年10月29日", "2026年11月01日", "2026年11月04日", "2026年11月07日",
        "2026年11月11日", "2026年11月15日", "2026年11月18日"
    ]


def get_15_session_blueprints(
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
) -> list[dict]:
    """
    生成 15 会话的标准蓝图配置列表。
    动态结合主线设定的时间区间 (time_range) 与周期粒度 (period_type, days) 输出排期。
    """
    period_type = main_mt.get("period_type", "weekly")
    days = main_mt.get("days", [])
    time_range = main_mt.get("time_range", "14:00-16:00")

    sh_str, eh_str, ref_str, base_dur, ext_eh_str, ext_dur = _parse_time_range(time_range)
    dates = _generate_15_dates(storyline_trigger_type, period_type, days)

    # 格式化起止时间
    def _m_time(d_str, t_str):
        parts = t_str.split(":")
        return f"{d_str}{parts[0]}时{parts[1]}分"

    # 同步突发事件 evt_01 的起止日期至 S11 ~ S13 范围
    evt_01["start_time"] = f"{dates[10]}00时00分"
    evt_01["end_time"] = f"{dates[12]}23时59分"

    return [
        # 01: Main Evidence (T2-4 首次建联证据)
        {
            "idx": 1,
            "ref_time": _m_time(dates[0], ref_str),
            "template_id": "T2-4",
            "role": "evidence_session",
            "source": main_mt,
            "type": "main",
            "start": _m_time(dates[0], sh_str),
            "end": _m_time(dates[0], eh_str),
            "dur": base_dur,
            "env": main_env_desc,
            "action": "declare_explicit_rule" if decl_mode == "explicit_declaration" else "single_task_implicit_behavior",
            "declaration_mode": decl_mode,
            "storyline_trigger_type": storyline_trigger_type,
            "trigger_condition": main_trigger_desc,
        },
        # 02: Sub 1 Evidence (T2-2 歧义消解)
        {
            "idx": 2,
            "ref_time": f"{dates[1]}18时30分",
            "template_id": "T2-2",
            "role": "evidence_session",
            "source": sub_01,
            "type": "sub_01",
            "start": f"{dates[1]}18时45分",
            "end": f"{dates[1]}19时45分",
            "dur": "60min",
            "env": "大巴跨城转场高速公路",
            "action": "disambiguate_sub_storyline_1",
            "declaration_mode": "implicit_induction",
            "storyline_trigger_type": "location_environment",
            "trigger_condition": "大巴转场弱网环境",
        },
        # 03: Main Reinforcement (T2-1 主线强化/固化契机)
        {
            "idx": 3,
            "ref_time": _m_time(dates[2], ref_str),
            "template_id": "T2-1",
            "role": "reinforcement_session",
            "source": main_mt,
            "type": "main",
            "start": _m_time(dates[2], sh_str),
            "end": _m_time(dates[2], eh_str),
            "dur": base_dur,
            "env": main_env_desc,
            "action": "reinforce_explicit_memory" if decl_mode == "explicit_declaration" else "crystallize_implicit_memory",
            "declaration_mode": decl_mode,
            "storyline_trigger_type": storyline_trigger_type,
            "trigger_condition": main_trigger_desc,
        },
        # 04: Sub 2 Evidence (T2-1 支线2建联)
        {
            "idx": 4,
            "ref_time": f"{dates[3]}20时00分",
            "template_id": "T2-1",
            "role": "evidence_session",
            "source": sub_02,
            "type": "sub_02",
            "start": f"{dates[3]}20时15分",
            "end": f"{dates[3]}21时45分",
            "dur": "90min",
            "env": "驻地酒店休息区",
            "action": "establish_sub_storyline_2",
            "declaration_mode": "implicit_induction",
            "storyline_trigger_type": "location_environment",
            "trigger_condition": "驻地酒店休息区",
        },
        # 05: Distractor 1 (T1-2 纯域外拒绝，如宽带光纤报修)
        {
            "idx": 5,
            "ref_time": f"{dates[4]}10时00分",
            "template_id": "T1-2",
            "role": "distractor_session",
            "source": dist_01,
            "type": "distractor_ood",
            "start": f"{dates[4]}10时00分",
            "end": f"{dates[4]}10时30分",
            "dur": "30min",
            "env": "酒店临时办公区网络故障",
            "action": "reject_out_of_domain",
            "ood_goal": "宽带光纤装维报修",
        },
        # 06: Sub 1 Reinforcement (T2-1 支线1复用/强化)
        {
            "idx": 6,
            "ref_time": f"{dates[5]}18时40分",
            "template_id": "T2-1",
            "role": "reinforcement_session",
            "source": sub_01,
            "type": "sub_01",
            "start": f"{dates[5]}19时00分",
            "end": f"{dates[5]}20时00分",
            "dur": "60min",
            "env": "大巴转场途中",
            "action": "reinforce_sub_storyline_1",
        },
        # 07: Main Reuse (T2-5 变更延长时长)
        {
            "idx": 7,
            "ref_time": _m_time(dates[6], ref_str),
            "template_id": "T2-5",
            "role": "reuse_session",
            "source": main_mt,
            "type": "main",
            "start": _m_time(dates[6], sh_str),
            "end": _m_time(dates[6], ext_eh_str),
            "dur": ext_dur,
            "base_end": _m_time(dates[6], eh_str),
            "base_dur": base_dur,
            "env": main_env_desc,
            "action": "extend_duration_amend",
            "storyline_trigger_type": storyline_trigger_type,
            "trigger_condition": main_trigger_desc,
        },
        # 08: Main Reinforcement (T2-1 主线常规强化)
        {
            "idx": 8,
            "ref_time": _m_time(dates[7], ref_str),
            "template_id": "T2-1",
            "role": "reinforcement_session",
            "source": main_mt,
            "type": "main",
            "start": _m_time(dates[7], sh_str),
            "end": _m_time(dates[7], eh_str),
            "dur": base_dur,
            "env": main_env_desc,
            "action": "reinforce_main_memory",
            "storyline_trigger_type": storyline_trigger_type,
            "trigger_condition": main_trigger_desc,
        },
        # 09: Sub 2 Reinforcement (T2-1 支线2强化)
        {
            "idx": 9,
            "ref_time": f"{dates[8]}20时10分",
            "template_id": "T2-1",
            "role": "reinforcement_session",
            "source": sub_02,
            "type": "sub_02",
            "start": f"{dates[8]}20时30分",
            "end": f"{dates[8]}22时00分",
            "dur": "90min",
            "env": "驻地复盘业务",
            "action": "reinforce_sub_storyline_2",
        },
        # 10: Distractor 2 (X-1 混合诉求一办一拒)
        {
            "idx": 10,
            "ref_time": f"{dates[9]}12时30分",
            "template_id": "X-1",
            "role": "distractor_session",
            "source": dist_02,
            "type": "distractor_mixed",
            "start": f"{dates[9]}12时30分",
            "end": f"{dates[9]}13时30分",
            "dur": "60min",
            "env": "周末午休个人时间",
            "action": "mixed_in_out_domain",
            "ood_goal": "手机话费充值与账单查询",
        },
        # 11: Event Correction (T2-3 恶劣天气临时纠正覆盖)
        {
            "idx": 11,
            "ref_time": _m_time(dates[10], ref_str),
            "template_id": "T2-3",
            "role": "correction_session",
            "source": main_mt,
            "type": "event_override",
            "start": _m_time(dates[10], sh_str),
            "end": _m_time(dates[10], eh_str),
            "dur": base_dur,
            "env": evt_01.get("scene_description", "恶劣环境临时保障"),
            "action": "override_temporary_preference",
            "override": evt_01.get("preference_override", {}),
        },
        # 12: Event Reuse (T2-1 临时高规格复用)
        {
            "idx": 12,
            "ref_time": _m_time(dates[11], ref_str),
            "template_id": "T2-1",
            "role": "reuse_session",
            "source": main_mt,
            "type": "event_reuse",
            "start": _m_time(dates[11], sh_str),
            "end": _m_time(dates[11], eh_str),
            "dur": base_dur,
            "env": "特殊事件集结区",
            "action": "reuse_temporary_preference",
            "override": evt_01.get("preference_override", {}),
        },
        # 13: Sub 1 Reuse (T2-1 支线隔离验证)
        {
            "idx": 13,
            "ref_time": f"{dates[12]}18时35分",
            "template_id": "T2-1",
            "role": "reuse_session",
            "source": sub_01,
            "type": "sub_01",
            "start": f"{dates[12]}19时00分",
            "end": f"{dates[12]}20时00分",
            "dur": "60min",
            "env": "转场大巴途中",
            "action": "sub_memory_unaffected",
        },
        # 14: Distractor 1 (T1-1 单轮单次业务)
        {
            "idx": 14,
            "ref_time": f"{dates[13]}10时00分",
            "template_id": "T1-1",
            "role": "distractor_session",
            "source": dist_01,
            "type": "distractor",
            "start": f"{dates[13]}10时00分",
            "end": f"{dates[13]}10时30分",
            "dur": "30min",
            "env": "阶段工作总结会",
            "action": "distractor_no_memory",
        },
        # 15: Event Expiry & Main Recovery (T2-1 临时失效主线恢复)
        {
            "idx": 15,
            "ref_time": _m_time(dates[14], ref_str),
            "template_id": "T2-1",
            "role": "reuse_session",
            "source": main_mt,
            "type": "main_recovery",
            "start": _m_time(dates[14], sh_str),
            "end": _m_time(dates[14], eh_str),
            "dur": base_dur,
            "env": main_env_desc,
            "action": "recover_long_term_rule",
            "storyline_trigger_type": storyline_trigger_type,
            "trigger_condition": main_trigger_desc,
        },
    ]
