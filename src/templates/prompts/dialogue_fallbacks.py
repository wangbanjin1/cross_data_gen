"""
对话渲染异常或离线兜底台词与动作类型规范化模块。
集中维护各模版（T1-2, X-1, T2-2, T2-5, T2-3, T2-4, T2-1, T1-1）的确定性行为。
"""

def get_fallback_user_utterance(s_plan: dict, turn_idx: int, role: str) -> str:
    tp = s_plan["target_params"]
    aliases = s_plan.get("aliases", {})
    app_alias = (aliases.get("app_aliases") or [tp["application_name"]])[0]
    srv_alias = (aliases.get("service_aliases") or [tp["service_name"]])[0]
    res_alias = (aliases.get("resolution_aliases") or [tp["resolution"]])[0]
    rtt_alias = (aliases.get("rtt_aliases") or [tp["rtt"]])[0]
    dur_alias = (aliases.get("duration_aliases") or [tp["duration"]])[0]

    app = tp["application_name"]
    srv = tp["service_name"]
    res = tp["resolution"]
    rtt = tp["rtt"]
    tid = s_plan.get("template_id", "")
    ood_goal = s_plan.get("ood_goal", "")
    decl_mode = s_plan.get("declaration_mode", "explicit_declaration")
    trig_type = s_plan.get("storyline_trigger_type", "time_periodic")
    period_type = s_plan.get("period_type", "weekly")
    trig_cond = s_plan.get("trigger_condition", "")
    env = s_plan.get("scenario_env", "")

    if tid == "T1-2":
        return f"你好，现场这边网络好像有问题，能帮我安排师傅处理一下{ood_goal or '宽带光纤装维报修'}吗？"
    elif tid == "X-1":
        return f"帮我办理一下今天{tp['start_timestamp'].split('日')[-1]}的{app_alias}{srv_alias}网络保障，另外顺便帮我查询一下{ood_goal or '手机话费充值与账单查询'}。"
    elif tid == "T2-2":
        if turn_idx == 1:
            return f"在{env}网络不太稳，帮我把{app}保障一下。"
        else:
            alias_intro = f"我平时习惯叫它'{app_alias}'，帮我把这个习惯记好，别掉链子。" if app_alias != app else "帮我把这个习惯记好，别掉链子。"
            return f"是{srv_alias}业务，画质要{res_alias}，时延控制在{rtt_alias}以内，从今天{tp['start_timestamp'].split('日')[-1]}开始，预计持续{dur_alias}。{alias_intro}"
    elif tid == "T2-5":
        if turn_idx == 1:
            return f"今天在{env}，按老规矩给我开通{app_alias}{srv_alias}保障。"
        else:
            return f"对，不过今天现场活动延长了，帮我把保障时长延长到{tp['duration']}（持续到{tp['end_timestamp'].split('日')[-1]}）。"
    elif tid == "T2-3":
        if turn_idx == 1:
            return f"今天在{env}，帮我开通{app_alias}{srv_alias}保障。"
        else:
            return f"不对，今天现场特殊，画质调到{res_alias}，时延要求{rtt_alias}，临时按这个来。"
    elif turn_idx == 1:
        if role == "evidence_session" or (role == "reinforcement_session" and decl_mode == "implicit_induction" and s_plan.get("session_id", "").endswith("-03")):
            return f"你好，需要给{app}{srv}做一个网络保障，时间是今天{tp['start_timestamp'].split('日')[-1]}开始。"
        elif role in ["reinforcement_session", "reuse_session"]:
            return f"老规矩，在{env}要用{app_alias}{srv_alias}，帮我把保障开上。"
        else:
            return f"你好，需要给{app_alias}{srv_alias}做一个网络保障，时间是今天{tp['start_timestamp'].split('日')[-1]}开始。"
    else:
        if role == "evidence_session" and decl_mode == "explicit_declaration":
            dur_text = f"，预计持续{dur_alias}（到{tp['end_timestamp'].split('日')[-1]}）"
            alias_intro = f"我平时习惯叫它'{app_alias}'，" if app_alias != app else ""
            if trig_type == "task_activity":
                return f"好的，画质用{res}，时延{rtt}以内{dur_text}。{alias_intro}以后只要我提到执行【{trig_cond or env}】任务，就按老规矩来：{app}{srv}、{res}、{rtt}以内，帮我把这个习惯记好，别掉链子。"
            elif trig_type == "location_environment":
                return f"好的，画质用{res}，时延{rtt}以内{dur_text}。{alias_intro}以后只要我处于【{trig_cond or env}】，就按老规矩来：{app}{srv}、{res}、{rtt}以内，帮我把这个习惯记好，别掉链子。"
            elif period_type == "daily":
                return f"好的，画质用{res}，时延{rtt}以内{dur_text}。{alias_intro}以后我只要每天这个时段说'老规矩'，就按这个来：{app}{srv}、{res}、{rtt}以内，记住这个习惯哈，别掉链子。"
            elif period_type == "monthly":
                return f"好的，画质用{res}，时延{rtt}以内{dur_text}。{alias_intro}以后我只要在每月固定月度对账/例会说'老规矩'，就按这个来：{app}{srv}、{res}、{rtt}以内，把这个规矩记一下哈，别掉链子。"
            else:
                return f"好的，画质用{res}，时延{rtt}以内{dur_text}。{alias_intro}以后我只要在每周例行时段说'老规矩'，就按这个来：{app}{srv}、{res}、{rtt}以内，记住这个习惯哈，别掉链子。"
        elif role == "evidence_session" and decl_mode == "implicit_induction":
            alias_intro = f"我平时习惯叫它'{app_alias}'，" if app_alias != app else ""
            return f"好的，画质用{res}，时延{rtt}以内，预计持续{dur_alias}。{alias_intro}今天就按这个配置开通吧。"
        elif role == "reinforcement_session" and decl_mode == "implicit_induction" and s_plan.get("session_id", "").endswith("-03"):
            alias_intro = f"我平时习惯叫它'{app_alias}'，" if app_alias != app else ""
            return f"对，就按这个标准来。{alias_intro}以后我都这么用，帮我把这个习惯记好，别掉链子。"
        else:
            return "好的，确认按这个配置直接开通。"


def get_fallback_agent_utterance(s_plan: dict, turn_idx: int, role: str, is_last: bool) -> str:
    tp = s_plan["target_params"]
    app = tp["application_name"]
    srv = tp["service_name"]
    res = tp["resolution"]
    rtt = tp["rtt"]
    tid = s_plan.get("template_id", "")
    ood_goal = s_plan.get("ood_goal", "")
    decl_mode = s_plan.get("declaration_mode", "explicit_declaration")
    trig_type = s_plan.get("storyline_trigger_type", "time_periodic")
    period_type = s_plan.get("period_type", "weekly")
    trig_cond = s_plan.get("trigger_condition", "")
    env = s_plan.get("scenario_env", "")

    if tid == "T1-2":
        return f"抱歉，本智能助手仅提供手机移动网络加速与保障服务，暂不支持办理{ood_goal or '宽带光纤装维报修'}业务，建议您联系宽带专线处理。"
    elif tid == "X-1":
        return f"好的，已为您成功受理{app}{srv}网络保障（{res} / 时延≤{rtt}）；另外关于{ood_goal or '手机话费充值与账单查询'}，目前暂不支持在线代办，请前往掌上营业厅查看。"
    elif tid == "T2-2":
        if turn_idx == 1:
            return f"收到，请问您是要进行'{app}{srv}'还是其他业务的保障？画质、时延和持续时长有什么具体要求吗？"
        else:
            return f"好的，已为您开通{app}{srv}网络保障（{res} / 时延≤{rtt}），并已为您记录习惯'{app_alias}'，祝您使用愉快！"
    elif tid == "T2-5":
        if turn_idx == 1:
            return f"收到，请问是否按老规矩（{res} / 时延≤{rtt}）为您开通保障？"
        else:
            return f"好的，已为您将{app}{srv}保障时长延长至{tp['duration']}（至{tp['end_timestamp'].split('日')[-1]}），配置保持{res}/时延≤{rtt}，保障已生效！"
    elif tid == "T2-3":
        if turn_idx == 1:
            return f"收到，请问是否按老规矩标准（1080p / 时延≤50ms）为您开通？"
        else:
            return f"收到，已临时为您调整为画质{res}、时延上限{rtt}，保障已为您生效！"
    elif is_last:
        if role == "evidence_session" and decl_mode == "explicit_declaration":
            return f"好的，已为您成功受理本次保障，并已为您将该配置记录为长期老规矩，祝您使用愉快！"
        elif role == "reinforcement_session" and decl_mode == "implicit_induction" and s_plan.get("session_id", "").endswith("-03"):
            return f"好的，已为您将该配置固化为您的长期网络保障老规矩，祝您使用愉快！"
        else:
            return f"好的，已为您成功受理{app}{srv}网络保障（{res} / 时延≤{rtt}），祝您使用愉快！"
    else:
        if role == "evidence_session":
            return f"收到，已为您锁定{app}{srv}保障，时间从{tp['start_timestamp'].split('日')[-1]}开始。请问您需要保障的清晰度、时延上限和预计持续时长分别是多少呢？"
        elif role == "reinforcement_session" and decl_mode == "implicit_induction" and s_plan.get("session_id", "").endswith("-03"):
            return f"检测到您在【{trig_cond or env}】多次使用{app}{srv}保障，请问是否按上次标准（{res} / 时延≤{rtt}）为您开通并设为默认老规矩？"
        else:
            if trig_type == "time_periodic":
                if period_type == "daily":
                    p_desc = "每天固定时段"
                elif period_type == "monthly":
                    p_desc = "每月固定时段"
                else:
                    p_desc = "每周例行时段"
                return f"收到，检测到您在{p_desc}需要保障，请问{app}{srv}是否按老规矩标准（{res} / 时延≤{rtt}）为您开通？"
            return f"收到，请问{app}{srv}是否按分辨率{res}、时延上限{rtt}的标准来为您开通？"


def get_normalized_action_types(s_plan: dict, turn_idx: int, role: str, is_last: bool, raw_u_acts, raw_a_acts) -> tuple[list[str], list[str]]:
    tid = s_plan.get("template_id", "")

    if tid == "T1-2":
        return ["Create_Intent_Request"], ["Reject_Request"]
    elif tid == "X-1":
        return ["Create_Intent_Request", "Inform_Slot"], ["Acknowledge", "Reject_Request"]
    elif tid == "T2-2":
        if turn_idx == 1:
            return ["Create_Intent_Request", "Inform_Slot"], ["Request_Disambiguation"]
        else:
            return ["Inform_Slot"], ["Acknowledge"]
    elif tid == "T2-5":
        if turn_idx == 1:
            return ["Create_Intent_Request", "Inform_Slot"], ["Confirm_Slot"]
        else:
            return ["Confirm_Slot", "Modify_Request"], ["Acknowledge"]
    elif tid == "T2-3":
        if turn_idx == 1:
            return ["Create_Intent_Request", "Inform_Slot"], ["Confirm_Slot"]
        else:
            return ["Correct_Previous_Input", "Inform_Slot"], ["Acknowledge"]
    else:
        u_acts = raw_u_acts
        if turn_idx == 1:
            if not u_acts:
                u_acts = ["Create_Intent_Request", "Inform_Slot"]
            elif isinstance(u_acts, str):
                u_acts = [u_acts]
        else:
            if role in ["reinforcement_session", "reuse_session"]:
                u_acts = ["Confirm_Slot"]
            elif not u_acts:
                u_acts = ["Confirm_Slot"]
            elif isinstance(u_acts, str):
                u_acts = [u_acts]

        a_acts = raw_a_acts
        if is_last:
            a_acts = ["Acknowledge"]
        elif role in ["reinforcement_session", "reuse_session"]:
            a_acts = ["Confirm_Slot"]
        elif not a_acts:
            a_acts = ["Request_Slot"] if role == "evidence_session" else ["Confirm_Slot"]
        elif isinstance(a_acts, str):
            a_acts = [a_acts]

        return u_acts, a_acts
