"""经验记忆快/慢路径双轨评测场景分支构建模块。"""

from __future__ import annotations

import re


def _make_turn_params(
    app: str, app_ref: str, srv: str, srv_ref: str, res: str, rtt: str,
    start: str, start_ref: str, end: str, end_ref: str, dur: str, dur_ref: str
) -> dict:
    return {
        "application_name": {"value": app, "source_type": "Turn", "source_ref": app_ref},
        "service_name": {"value": srv, "source_type": "Turn", "source_ref": srv_ref},
        "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}},
        "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}},
        "timestamp": {
            "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": start_ref},
            "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": end_ref},
            "duration": {"value": dur, "source_type": "Turn", "source_ref": dur_ref},
        },
    }


def _build_slow_event_sequence(
    tree: list[dict],
    t1_closure: str,
    t1_intent_name: str,
    t1_params: dict,
    t2_closure: str,
    t2_intent_name: str,
    t2_params: dict,
) -> list[dict]:
    """根据 3 轮模拟器对话树生成标准慢路径完整事件序列。"""
    return [
        {
            "turn": 1,
            "user": {"utterance": tree[0]["simulator_user_prompt"], "action_types": ["Create_Intent_Request", "Inform_Slot"]},
            "agent": {"thought": tree[0]["agent_hypothesis"], "utterance": tree[0]["baseline_agent_flawed_response"], "action_types": ["Confirm_Slot"]},
            "related_intent_ids": ["I1"],
            "requested_params": [],
            "turn_intents": [{"intent_id": "I1", "status": "in_progress", "closure_path": t1_closure, "expression_level": 1, "intent": t1_intent_name, "params": t1_params}],
        },
        {
            "turn": 2,
            "user": {"utterance": tree[1]["simulator_user_prompt"], "action_types": ["Revise_Intent_Request", "Inform_Slot"]},
            "agent": {"thought": tree[1]["agent_hypothesis"], "utterance": tree[1]["expected_agent_correction"], "action_types": ["Confirm_Slot"]},
            "related_intent_ids": ["I1"],
            "requested_params": [],
            "turn_intents": [{"intent_id": "I1", "status": "in_progress", "closure_path": t2_closure, "expression_level": 1, "intent": t2_intent_name, "params": t2_params}],
        },
        {
            "turn": 3,
            "user": {"utterance": tree[2]["simulator_user_prompt"], "action_types": ["Confirm_Slot"]},
            "agent": {"thought": tree[2]["agent_hypothesis"], "utterance": tree[2]["expected_agent_correction"], "action_types": ["Acknowledge"]},
            "related_intent_ids": ["I1"],
            "requested_params": [],
            "turn_intents": [{"intent_id": "I1", "status": "resolved", "closure_path": "clarification_after_correction", "expression_level": 1, "intent": t2_intent_name, "params": t2_params}],
        },
    ]


def _branch_multi_intent_partition(
    user_prompt: str, app: str, srv: str, res: str, rtt: str, start: str, end: str, dur: str
) -> tuple[str, str, dict, str, str, list[dict], list[dict], str, str]:
    flawed_app, flawed_srv = "抖音", "开直播"
    app, srv = "微信", "视频通话"
    fast_cond = "Agent识别用户是在正式开播前私下跟搭档对直播词与看镜头机位，未机械提取字面‘抖音直播’，主动匹配【微信-视频通话】意图保障单，2轮快速闭环"
    slow_cond = "Agent未启用日常对词试机位经验，被字面‘抖音直播’误导提取为【抖音-开直播】，经用户澄清指正后在3轮完成闭环"
    gate = {
        "eval_turn": 1,
        "decision_type": "pre_stream_partner_rehearsal_app_selection_check",
        "pass_condition": "Agent识别私下跟搭档对直播词看机位使用【微信-视频通话】而非公开【抖音-开直播】 (EXP_MULTI_INTENT_PARTITION_01)",
        "fail_condition": "Agent被字面‘抖音直播’误导，错误提取为【抖音-开直播】",
        "key_slot_assertions": {"target_intent_id": "I1", "checked_slots": ["application_name", "service_name"], "expected_action": "select_wechat_video_call_for_partner_rehearsal"},
        "pass_route": "fast_path",
        "fail_route": "slow_path",
    }
    slot_err_reply = "嗨，我只是先跟搭档私下对一下词和看眼机位，还没正式开播呢！平时对词我们都是打微信视频电话，把应用和业务改成微信视频通话就行。"
    goal_match_reply = "好的，改成微信视频通话就对了，确认按此开通。"
    gt_slots = {"I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}}
    flawed_slots = {"I1": {"application_name": flawed_app, "service_name": flawed_srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}}
    t1_corr = f"收到，识别到您是在正式开播前先跟搭档私下对直播词和看镜头机位，结合日常经验已主动为您匹配【{app}-{srv}】意图保障单（{start}至{end}，持续{dur}，{res} / 时延≤{rtt}），确认按此办理吗？"
    tree = [
        {
            "turn": 1, "speaker": "user", "simulator_user_prompt": user_prompt,
            "agent_hypothesis": "Agent缺乏日常对词试机位经验，被字面‘抖音直播’误导提取为【抖音-开直播】",
            "baseline_agent_flawed_response": f"收到，已为您准备好{start}至{end}（持续{dur}）的【{flawed_app}-{flawed_srv}】意图保障单（{res} / 时延≤{rtt}），确认按此开通吗？",
            "expected_agent_correction": t1_corr, "expected_agent_response": t1_corr,
            "flaw_type": "literal_douyin_keyword_app_misattribution",
            "flaw_description": "未区分正式开播与私下找搭档对词看机位，被字面‘抖音直播’误导提取为抖音-开直播",
            "agent_action_types": ["Confirm_Slot"], "expected_slots_gt": gt_slots, "baseline_flawed_slots": flawed_slots,
            "delta_from_gt": {"has_error": True, "error_details": [f"I1.application_name: expected '{app}', got '{flawed_app}'", f"I1.service_name: expected '{srv}', got '{flawed_srv}'"], "triggered_reaction": "on_slot_error"},
        },
        {
            "turn": 2, "speaker": "user_simulator", "simulator_user_prompt": slot_err_reply,
            "agent_hypothesis": "Agent收到用户澄清指正后，将保障应用与业务修正为【微信-视频通话】",
            "expected_agent_correction": f"非常抱歉！原来是开播前私下跟搭档对词看机位，已为您将意图保障单由【{flawed_app}-{flawed_srv}】修正为【{app}-{srv}】（{start}至{end}，持续{dur}，画质{res}、时延≤{rtt}），确认现在为您开通吗？",
            "agent_action_types": ["Confirm_Slot"], "expected_slots_gt": gt_slots,
            "delta_from_gt": {"has_error": False, "error_details": [], "triggered_reaction": "on_goal_matched"},
        },
        {
            "turn": 3, "speaker": "user_simulator", "simulator_user_prompt": goal_match_reply,
            "agent_hypothesis": "Agent完成【微信-视频通话】意图保障单闭环出单",
            "expected_agent_correction": f"好的，已为您成功开通{start}至{end}（持续{dur}）的【{app}-{srv}】意图保障单（{res} / 时延≤{rtt}），祝您和搭档对词试机位顺利！",
            "agent_action_types": ["Acknowledge"], "expected_slots_gt": gt_slots,
        },
    ]
    t1_p = _make_turn_params(flawed_app, "U1", flawed_srv, "U1", res, rtt, start, "U1", end, "U1", dur, "U1")
    t2_p = _make_turn_params(app, "U2", srv, "U2", res, rtt, start, "U1", end, "U1", dur, "U1")
    slow_seq = _build_slow_event_sequence(tree, "literal_douyin_keyword_app_misattribution", f"{flawed_app}{flawed_srv}保障", t1_p, "rehearsal_app_corrected", f"{app}{srv}保障", t2_p)
    return fast_cond, slow_cond, gate, slot_err_reply, goal_match_reply, tree, slow_seq, app, srv


def _compute_nominal_prewarm(start: str, dur: str) -> tuple[str, str]:
    nom_start = start
    m_s = re.search(r'^(.*?)(\d{1,2})时(\d{2})分$', start)
    if m_s:
        pfx, hh, mm = m_s.group(1), int(m_s.group(2)), int(m_s.group(3))
        tot = hh * 60 + mm + 30
        nom_start = f"{pfx}{(tot // 60) % 24:02d}时{tot % 60:02d}分"
    else:
        m_s2 = re.search(r'^(.*?)(\d{1,2}):(\d{2})$', start)
        if m_s2:
            pfx, hh, mm = m_s2.group(1), int(m_s2.group(2)), int(m_s2.group(3))
            tot = hh * 60 + mm + 30
            nom_start = f"{pfx}{(tot // 60) % 24:02d}:{tot % 60:02d}"
    m_d = re.search(r'(\d+)', dur)
    nom_dur = f"{max(30, int(m_d.group(1)) - 30)}min" if m_d else "120min"
    return nom_start, nom_dur


def _branch_prewarm_buffer(
    user_prompt: str, app: str, srv: str, res: str, rtt: str, start: str, end: str, dur: str
) -> tuple[str, str, dict, str, str, list[dict], list[dict], str, str]:
    fast_cond = "自主识别大型场馆重大活动并执行提前30分钟预热时间差推算（start_timestamp提前30分钟，duration扩充30分钟），2轮确认极速闭环"
    slow_cond = "机械按活动原定时间掐点预约，未预留调试时间触发on_slot_error，经用户模拟器纠偏后在3轮完成闭环"
    gate = {
        "eval_turn": 1, "decision_type": "prewarm_buffer_check",
        "pass_condition": "Agent识别大型场馆重大活动并主动将 start_timestamp 提前 30 分钟预热，同时 duration 扩充 30 分钟 (EXP_PREWARM_BUFFER_01)",
        "fail_condition": "Agent机械按用户口语活动时间掐点预约，未预留调试与预热时间",
        "key_slot_assertions": {"target_intent_id": "I1", "checked_slot": "timestamp.start_timestamp", "expected_adjustment": "-30min_prewarm_offset"},
        "pass_route": "fast_path", "fail_route": "slow_path",
    }
    nom_start, nom_dur = _compute_nominal_prewarm(start, dur)
    slot_err_reply = "等等，大型活动现场还得提前进场调试设备呢，掐着点开来不及！帮我把开始时间往前提前半小时就行。"
    goal_match_reply = "好的，规格时间都对了，确认按此开通。"
    gt_slots = {"I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}}
    flawed_slots = {"I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": nom_start, "end_timestamp": end, "duration": nom_dur}}}
    t1_corr = f"收到，识别到大型场馆重大活动现场设备需提前预热试机，已为您将意图保障单起保时间自动提前30分钟至{start}（至{end}，总时长{dur}，{res} / 时延≤{rtt}），确认直接开通吗？"
    tree = [
        {
            "turn": 1, "speaker": "user", "simulator_user_prompt": user_prompt,
            "agent_hypothesis": "Agent按活动开始时间掐点预约，未做提前30分钟预热试机推算",
            "baseline_agent_flawed_response": f"收到，已按活动起止时间为您锁定{app}{srv}意图保障单（{nom_start}至{end}，持续{nom_dur}，{res} / 时延≤{rtt}），确认直接为您开通吗？",
            "expected_agent_correction": t1_corr, "expected_agent_response": t1_corr,
            "flaw_type": "missing_prewarm_buffer", "flaw_description": "未对大型场馆重大活动现场设备调试进行前置30分钟时间差推算",
            "agent_action_types": ["Confirm_Slot"], "expected_slots_gt": gt_slots, "baseline_flawed_slots": flawed_slots,
            "delta_from_gt": {"has_error": True, "error_details": [f"I1.timestamp.start_timestamp: expected '{start}', got '{nom_start}'", f"I1.timestamp.duration: expected '{dur}', got '{nom_dur}'"], "triggered_reaction": "on_slot_error"},
        },
        {
            "turn": 2, "speaker": "user_simulator", "simulator_user_prompt": slot_err_reply,
            "agent_hypothesis": "Agent收到纠偏后将起保时间提前30分钟并更新总时长",
            "expected_agent_correction": f"抱歉！已为您重新推算意图保障单时间，将起保时间提前30分钟调整为{start}至{end}（总时长扩充至{dur}，画质{res}、时延≤{rtt}），确认按此提前开通吗？",
            "agent_action_types": ["Confirm_Slot"], "expected_slots_gt": gt_slots,
            "delta_from_gt": {"has_error": False, "error_details": [], "triggered_reaction": "on_goal_matched"},
        },
        {
            "turn": 3, "speaker": "user_simulator", "simulator_user_prompt": goal_match_reply,
            "agent_hypothesis": "Agent完成提前预热试机意图保障单受理",
            "expected_agent_correction": f"好的，已为您成功受理提前30分钟预热试机意图保障单（{start}至{end}，持续{dur}，{res} / 时延≤{rtt}），预祝活动圆满顺利！",
            "agent_action_types": ["Acknowledge"], "expected_slots_gt": gt_slots,
        },
    ]
    t1_p = _make_turn_params(app, "U1", srv, "U1", res, rtt, nom_start, "U1", end, "U1", nom_dur, "U1")
    t2_p = _make_turn_params(app, "U1", srv, "U1", res, rtt, start, "U2", end, "U1", dur, "U2")
    slow_seq = _build_slow_event_sequence(tree, "missing_prewarm_buffer", f"{app}{srv}保障", t1_p, "prewarm_correction", f"{app}{srv}保障", t2_p)
    return fast_cond, slow_cond, gate, slot_err_reply, goal_match_reply, tree, slow_seq, app, srv


def _branch_holiday_exception(
    user_prompt: str, app: str, srv: str, res: str, rtt: str, start: str, end: str, dur: str
) -> tuple[str, str, dict, str, str, list[dict], list[dict], str, str]:
    fast_cond = "识别10月5日恰逢国庆法定假期冲突，主动将例行周会意图保障单顺延至节后首个工作日（10月8日）同时段，2轮极速出单"
    slow_cond = "Agent缺乏节假日避让经验，机械按10月5日放假当天预约触发on_slot_error，经用户模拟器纠偏后在3轮完成闭环"
    gate = {
        "eval_turn": 1, "decision_type": "holiday_conflict_deferral_check",
        "pass_condition": "Agent识别下周一（10月05日）为国庆法定节假日，主动顺延至节后首个工作日2026年10月08日同时段 (EXP_CALENDAR_HOLIDAY_EXCEPTION_01)",
        "fail_condition": "Agent缺乏日历假期避让经验，直接在10月05日放假当天预约",
        "key_slot_assertions": {"target_intent_id": "I1", "checked_slot": "timestamp.start_timestamp", "expected_deferral": "post_holiday_workday_20261008"},
        "pass_route": "fast_path", "fail_route": "slow_path",
    }
    holiday_start = re.sub(r'\d{4}年\d{1,2}月\d{1,2}日', '2026年10月05日', start)
    holiday_end = re.sub(r'\d{4}年\d{1,2}月\d{1,2}日', '2026年10月05日', end)
    slot_err_reply = "哎呀，10月5日还在放国庆假呢，那天不开会！帮我把日期顺延到节后上班第一天（10月8日）就行。"
    goal_match_reply = "好的，规格时间都对了，确认按此开通。"
    gt_slots = {"I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}}
    flawed_slots = {"I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": holiday_start, "end_timestamp": holiday_end, "duration": dur}}}
    t1_corr = f"收到，识别到10月5日为国庆法定长假，办公室全员放假。参考前序避让经验，已主动为您将例行周会意图保障单顺延至节后首个工作日（{start}至{end}，持续{dur}，{res} / 时延≤{rtt}），确认按此顺延生效吗？"
    tree = [
        {
            "turn": 1, "speaker": "user", "simulator_user_prompt": user_prompt,
            "agent_hypothesis": "Agent未识别下周一（10月5日）为国庆节法定假期，直接在放假当天机械预约",
            "baseline_agent_flawed_response": f"收到，已为您预约下周一（{holiday_start}至{holiday_end}，持续{dur}）的{app}{srv}意图保障单（{res} / 时延≤{rtt}），确认直接按此开通吗？",
            "expected_agent_correction": t1_corr, "expected_agent_response": t1_corr,
            "flaw_type": "unaware_of_holiday_conflict", "flaw_description": "未对法定节假日冲突避让进行推断，在办公室全员放假时机械预约",
            "agent_action_types": ["Confirm_Slot"], "expected_slots_gt": gt_slots, "baseline_flawed_slots": flawed_slots,
            "delta_from_gt": {"has_error": True, "error_details": [f"I1.timestamp.start_timestamp: expected '{start}', got '{holiday_start}'", f"I1.timestamp.end_timestamp: expected '{end}', got '{holiday_end}'"], "triggered_reaction": "on_slot_error"},
        },
        {
            "turn": 2, "speaker": "user_simulator", "simulator_user_prompt": slot_err_reply,
            "agent_hypothesis": "Agent收到用户纠偏后将意图保障单顺延至2026年10月08日同时段并发起确认",
            "expected_agent_correction": f"非常抱歉！已为您撤销10月5日放假期间的排期，并将例行周会{app}{srv}意图保障单顺延至节后首个工作日{start}至{end}（持续{dur}，{res} / 时延≤{rtt}），确认按此顺延生效吗？",
            "agent_action_types": ["Confirm_Slot"], "expected_slots_gt": gt_slots,
            "delta_from_gt": {"has_error": False, "error_details": [], "triggered_reaction": "on_goal_matched"},
        },
        {
            "turn": 3, "speaker": "user_simulator", "simulator_user_prompt": goal_match_reply,
            "agent_hypothesis": "Agent完成节后首个工作日顺延办理并出单",
            "expected_agent_correction": f"好的，已成功将例行周会{app}{srv}意图保障单顺延至{start}至{end}办理（{res} / 时延≤{rtt}），祝您假期愉快！",
            "agent_action_types": ["Acknowledge"], "expected_slots_gt": gt_slots,
        },
    ]
    t1_p = _make_turn_params(app, "U1", srv, "U1", res, rtt, holiday_start, "U1", holiday_end, "U1", dur, "U1")
    t2_p = _make_turn_params(app, "U1", srv, "U1", res, rtt, start, "U2", end, "U2", dur, "U1")
    slow_seq = _build_slow_event_sequence(tree, "unaware_of_holiday_conflict", f"{app}{srv}保障", t1_p, "holiday_deferral_confirm", f"{app}{srv}保障", t2_p)
    return fast_cond, slow_cond, gate, slot_err_reply, goal_match_reply, tree, slow_seq, app, srv


def _compute_short_flawed_duration(start: str, dur: str) -> tuple[str, str, str, str, str, str]:
    d_prefix = start.split("日")[0] + "日" if "日" in start else "2026年10月21日"
    m_f_dur = re.search(r"(\d+)", str(dur or "120min"))
    f_mins = int(m_f_dur.group(1)) if m_f_dur else 120
    t_mins = 30 if f_mins <= 60 else 60
    short_flawed_dur = f"{t_mins}min"
    sh_part = start.split("日")[-1] if "日" in start else start
    m_sh = re.search(r"(\d{1,2})[时:](\d{1,2})", sh_part)
    if m_sh:
        t_end_tot = (int(m_sh.group(1)) * 60 + int(m_sh.group(2)) + t_mins) % (24 * 60)
        short_flawed_end = f"{d_prefix}{t_end_tot // 60:02d}时{t_end_tot % 60:02d}分" if "日" in start else f"{t_end_tot // 60:02d}:{t_end_tot % 60:02d}"
    else:
        short_flawed_end = f"{d_prefix}15时00分" if "日" in start else "15:00"
    lbl_map = {30: ("半小时", "半小时"), 60: ("1个小时", "1小时"), 90: ("1个半小时", "1.5小时"), 120: ("2个小时", "2小时"), 180: ("3个小时", "3小时")}
    f_spoken, f_short = lbl_map.get(f_mins, (f"{f_mins}分钟", f"{f_mins}分钟"))
    t_spoken, t_short = lbl_map.get(t_mins, (f"{t_mins}分钟", f"{t_mins}分钟"))
    return short_flawed_dur, short_flawed_end, f_spoken, f_short, t_spoken, t_short


def _branch_quality_disambiguation(
    user_prompt: str, app: str, srv: str, res: str, rtt: str, start: str, end: str, dur: str
) -> tuple[str, str, dict, str, str, list[dict], list[dict], str, str]:
    short_flawed_dur, short_flawed_end, f_spoken, f_short, t_spoken, t_short = _compute_short_flawed_duration(start, dur)
    fast_cond = f"识别正式客户路演场景，自动过滤前天{t_short}({short_flawed_dur})临时短单，优选匹配上周{f_short}({dur})正式路演单时长，2轮快速闭环"
    slow_cond = f"Agent未启用历史单据时长消歧经验，按最近邻偏见调取前天{t_short}({short_flawed_dur})临时短单，经用户澄清指正后在3轮闭环"
    gate = {
        "eval_turn": 1, "decision_type": "historical_order_duration_disambiguation_check",
        "pass_condition": f"Agent在正式客户路演场景下过滤前天{short_flawed_dur}临时短单，按上周正式路演单排满{dur} (EXP_ORDER_QUALITY_DISAMBIGUATION_01)",
        "fail_condition": f"Agent因最近邻偏见机械照搬前天那笔{short_flawed_dur}临时短会单时长",
        "key_slot_assertions": {"target_intent_id": "I1", "checked_source": "Experience", "expected_duration_filter": f"prefer_formal_roadshow_{dur}_order"},
        "pass_route": "fast_path", "fail_route": "slow_path",
    }
    slot_err_reply = f"不对，{t_spoken}不够！你调成前天我临时开的短单了，今天是正式路演，得按上周那笔正式单把时长改成{f_spoken}。"
    goal_match_reply = f"好的，保满{f_spoken}就对了，确认按此开通。"
    gt_slots = {"I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}}
    flawed_slots = {"I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": short_flawed_end, "duration": short_flawed_dur}}}
    t1_corr = f"收到，识别到今日为正式客户远程路演，已自动过滤前天1小时临时短单，按上周正式客户路演单为您排满2小时（{start}至{end}，持续{dur}，{res} / 时延≤{rtt}），确认开通吗？"
    tree = [
        {
            "turn": 1, "speaker": "user", "simulator_user_prompt": user_prompt,
            "agent_hypothesis": "Agent受最近邻偏见影响，机械调取前天那笔1小时（60min）临时短单",
            "baseline_agent_flawed_response": f"收到，已为您按最近一笔（前天）的历史意图保障单时长配置，今日{start}至{short_flawed_end}（持续{short_flawed_dur}）为您开通{app}{srv}意图保障单（{res} / 时延≤{rtt}），确认吗？",
            "expected_agent_correction": t1_corr, "expected_agent_response": t1_corr,
            "flaw_type": "recency_bias_short_temporary_order", "flaw_description": "未区分前天1小时临时短会与上周2小时正式客户路演，因最近邻偏见误排为60min",
            "agent_action_types": ["Confirm_Slot"], "expected_slots_gt": gt_slots, "baseline_flawed_slots": flawed_slots,
            "delta_from_gt": {"has_error": True, "error_details": [f"I1.timestamp.end_timestamp: expected '{end}', got '{short_flawed_end}'", f"I1.timestamp.duration: expected '{dur}', got '{short_flawed_dur}'"], "triggered_reaction": "on_slot_error"},
        },
        {
            "turn": 2, "speaker": "user_simulator", "simulator_user_prompt": slot_err_reply,
            "agent_hypothesis": "Agent收到用户澄清指正后过滤前天60min短单，改按上周120min正式路演单排期",
            "expected_agent_correction": f"非常抱歉！已为您过滤前天的1小时临时短单，改按上周正式客户路演单排满2小时（{start}至{end}，持续{dur}，画质{res}、时延≤{rtt}），确认按此开通吗？",
            "agent_action_types": ["Confirm_Slot"], "expected_slots_gt": gt_slots,
            "delta_from_gt": {"has_error": False, "error_details": [], "triggered_reaction": "on_goal_matched"},
        },
        {
            "turn": 3, "speaker": "user_simulator", "simulator_user_prompt": goal_match_reply,
            "agent_hypothesis": "Agent按2小时正式客户路演单成功出单",
            "expected_agent_correction": f"好的，已按上周2小时正式路演单时长（{start}至{end}，持续{dur}，{res} / 时延≤{rtt}）为您成功受理{app}{srv}意图保障单，祝您路演顺畅！",
            "agent_action_types": ["Acknowledge"], "expected_slots_gt": gt_slots,
        },
    ]
    t1_p = _make_turn_params(app, "U1", srv, "U1", res, rtt, start, "U1", short_flawed_end, "U1", short_flawed_dur, "U1")
    t2_p = _make_turn_params(app, "U1", srv, "U1", res, rtt, start, "U1", end, "U2", dur, "U2")
    slow_seq = _build_slow_event_sequence(tree, "recency_bias_short_temporary_order", f"{app}{srv}保障", t1_p, "formal_roadshow_120min_selected", f"{app}{srv}保障", t2_p)
    return fast_cond, slow_cond, gate, slot_err_reply, goal_match_reply, tree, slow_seq, app, srv


def _branch_overlapping_resolution(
    user_prompt: str, app: str, srv: str, res: str, rtt: str, start: str, end: str, dur: str
) -> tuple[str, str, dict, str, str, list[dict], list[dict], str, str]:
    app, srv, flawed_srv = "抖音", "开直播", "看直播"
    fast_cond = "识别用户受邀进主会场抖音直播间当连麦嘉宾需上麦推流，未按字面‘进直播间’误判为看直播，主动匹配【抖音-开直播】，2轮快速闭环"
    slow_cond = "Agent未启用连麦嘉宾业务选择经验，看到‘进别人直播间’误判为【抖音-看直播】，经用户澄清指正后在3轮完成闭环"
    gate = {
        "eval_turn": 1, "decision_type": "guest_cohost_service_selection_check",
        "pass_condition": "Agent识别受邀进直播间当连麦嘉宾需上麦推流，将 service_name 设为【开直播】而非【看直播】 (EXP_OVERLAPPING_ORDER_RESOLUTION_01)",
        "fail_condition": "Agent看到‘进主会场直播间’字眼，机械将连麦嘉宾归类为普通观众【看直播】",
        "key_slot_assertions": {"target_intent_id": "I1", "checked_strategy": "guest_cohost_uplink_openlive", "expected_action": "select_openlive_instead_of_watchlive"},
        "pass_route": "fast_path", "fail_route": "slow_path",
    }
    slot_err_reply = "不对，我是去当连麦嘉宾、要开摄像头上麦发言的，不是光在下面看直播！把业务类型改成开直播就行。"
    goal_match_reply = "好的，改成抖音开直播就对了，确认按此开通。"
    gt_slots = {"I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}}
    flawed_slots = {"I1": {"application_name": app, "service_name": flawed_srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}}
    t1_corr = f"收到，识别到您是受邀进主会场抖音直播间当连麦嘉宾互动，上麦发言需保障上行推流，已主动为您匹配【{app}-{srv}】意图保障单（{start}至{end}，持续{dur}，{res} / 时延≤{rtt}），确认按此开通吗？"
    tree = [
        {
            "turn": 1, "speaker": "user", "simulator_user_prompt": user_prompt,
            "agent_hypothesis": "Agent缺乏连麦嘉宾业务选择经验，看到‘进主会场抖音直播间’机械提取为【抖音-看直播】",
            "baseline_agent_flawed_response": f"收到，已为您准备好{start}至{end}（持续{dur}）的【{app}-{flawed_srv}】意图保障单（{res} / 时延≤{rtt}），确认直接开通吗？",
            "expected_agent_correction": t1_corr, "expected_agent_response": t1_corr,
            "flaw_type": "guest_cohost_misclassified_as_watch_live", "flaw_description": "未区分普通观众看直播与连麦嘉宾上麦发言，将service_name误提为看直播",
            "agent_action_types": ["Confirm_Slot"], "expected_slots_gt": gt_slots, "baseline_flawed_slots": flawed_slots,
            "delta_from_gt": {"has_error": True, "error_details": [f"I1.service_name: expected '{srv}', got '{flawed_srv}'"], "triggered_reaction": "on_slot_error"},
        },
        {
            "turn": 2, "speaker": "user_simulator", "simulator_user_prompt": slot_err_reply,
            "agent_hypothesis": "Agent收到用户澄清指正后，将业务类型由【看直播】修正为【开直播】",
            "expected_agent_correction": f"非常抱歉！您作为连麦嘉宾上麦互动确实需要上行推流保障，已为您将意图保障单由【{app}-{flawed_srv}】修正为【{app}-{srv}】（{start}至{end}，持续{dur}，画质{res}、时延≤{rtt}），确认按此开通吗？",
            "agent_action_types": ["Confirm_Slot"], "expected_slots_gt": gt_slots,
            "delta_from_gt": {"has_error": False, "error_details": [], "triggered_reaction": "on_goal_matched"},
        },
        {
            "turn": 3, "speaker": "user_simulator", "simulator_user_prompt": goal_match_reply,
            "agent_hypothesis": "Agent完成【抖音-开直播】连麦嘉宾意图保障单出单",
            "expected_agent_correction": f"好的，已为您成功开通{start}至{end}（持续{dur}）的【{app}-{srv}】意图保障单（{res} / 时延≤{rtt}），祝您连麦互动顺利！",
            "agent_action_types": ["Acknowledge"], "expected_slots_gt": gt_slots,
        },
    ]
    t1_p = _make_turn_params(app, "U1", flawed_srv, "U1", res, rtt, start, "U1", end, "U1", dur, "U1")
    t2_p = _make_turn_params(app, "U1", srv, "U2", res, rtt, start, "U1", end, "U1", dur, "U1")
    slow_seq = _build_slow_event_sequence(tree, "guest_cohost_misclassified_as_watch_live", f"{app}{flawed_srv}保障", t1_p, "guest_cohost_openlive_corrected", f"{app}{srv}保障", t2_p)
    return fast_cond, slow_cond, gate, slot_err_reply, goal_match_reply, tree, slow_seq, app, srv


_SCENARIO_BRANCH_BUILDERS = {
    "multi_intent_partition": _branch_multi_intent_partition,
    "prewarm_buffer": _branch_prewarm_buffer,
    "holiday_exception": _branch_holiday_exception,
    "quality_disambiguation": _branch_quality_disambiguation,
    "overlapping_resolution": _branch_overlapping_resolution,
}


def build_scenario_branch_nodes(
    scenario_type: str,
    user_prompt: str,
    app: str,
    srv: str,
    res: str,
    rtt: str,
    start: str,
    end: str,
    dur: str,
) -> tuple[str, str, dict, str, str, list[dict], list[dict], str, str]:
    """Construct simulator dialogue tree and slow-path event sequence for each experience scenario."""
    builder = _SCENARIO_BRANCH_BUILDERS.get(scenario_type)
    if builder is not None:
        return builder(user_prompt, app, srv, res, rtt, start, end, dur)

    fast_cond = "Agent应用经验策略达成高效闭环"
    slow_cond = "Agent缺乏经验导致交互拉扯"
    gate = {"eval_turn": 1, "pass_condition": "命中经验", "fail_condition": "未命中经验", "pass_route": "fast_path", "fail_route": "slow_path"}
    return fast_cond, slow_cond, gate, "参数不对，请重新核实。", "好的，规格时间都对了，确认按此开通。", [], [], app, srv
