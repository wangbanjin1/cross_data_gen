"""
对话渲染异常或离线兜底台词与动作类型规范化模块。
集中维护各模版（T1-2, X-1, T2-2, T2-5, T2-3, T2-4, T2-1, T1-1）的确定性行为。
"""

def get_fallback_user_utterance(s_plan: dict, turn_idx: int, role: str) -> str:
    tp = s_plan["target_params"]
    app = tp["application_name"]
    srv = tp["service_name"]
    res = tp["resolution"]
    rtt = tp["rtt"]
    tid = s_plan.get("template_id", "")
    ood_goal = s_plan.get("ood_goal", "")
    decl_mode = s_plan.get("declaration_mode", "explicit_declaration")
    trig_type = s_plan.get("storyline_trigger_type", "time_periodic")
    trig_cond = s_plan.get("trigger_condition", "")
    env = s_plan.get("scenario_env", "")

    if tid == "T1-2":
        return f"你好，现场这边网络好像有问题，能帮我安排师傅处理一下{ood_goal or '宽带光纤装维报修'}吗？"
    elif tid == "X-1":
        return f"帮我办理一下今天{tp['start_timestamp'].split('日')[-1]}的{app}{srv}网络保障，另外顺便帮我查询一下{ood_goal or '手机话费充值与账单查询'}。"
    elif tid == "T2-2":
        if turn_idx == 1:
            return f"在{env}网络不太稳，帮我把{app}保障一下。"
        else:
            return f"是{srv}业务，画质要求{res}，时延控制在{rtt}以内就行。"
    elif tid == "T2-5":
        if turn_idx == 1:
            return f"今天在{env}，按老规矩给我开通{app}{srv}保障。"
        else:
            return f"对，不过今天现场活动延长了，帮我把保障时长延长到3小时（持续180分钟，到17点结束）。"
    elif tid == "T2-3":
        if turn_idx == 1:
            return f"今天在{env}，帮我开通{app}{srv}保障。"
        else:
            return f"不对，今天现场特殊，画质调到{res}，时延要求{rtt}以内，临时按这个来。"
    elif turn_idx == 1:
        return f"你好，需要给{app}{srv}做一个网络保障，时间是今天{tp['start_timestamp'].split('日')[-1]}开始，持续{tp['duration']}。"
    else:
        if role == "evidence_session" and decl_mode == "explicit_declaration":
            if trig_type == "task_activity":
                return f"好的，确认按这个配置直接开通。以后只要我提到执行【{trig_cond or env}】任务，就按老规矩来：{app}{srv}、{res}、{rtt}以内，记一下长期偏好，别掉链子。"
            elif trig_type == "location_environment":
                return f"好的，确认按这个配置直接开通。以后只要我处于【{trig_cond or env}】，就按老规矩来：{app}{srv}、{res}、{rtt}以内，记一下长期偏好，别掉链子。"
            else:
                return f"好的，确认按这个配置直接开通。以后我在{env}只要说'下午大直播，老规矩'，就按这个来：{app}{srv}、{res}、{rtt}以内，记一下长期偏好，别掉链子。"
        elif role == "evidence_session" and decl_mode == "implicit_induction":
            return "好的，今天就按这个配置开通吧。"
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
    trig_cond = s_plan.get("trigger_condition", "")
    env = s_plan.get("scenario_env", "")

    if tid == "T1-2":
        return f"抱歉，本智能助手仅提供手机移动网络加速与保障服务，暂不支持办理{ood_goal or '宽带光纤装维报修'}业务，建议您联系宽带专线处理。"
    elif tid == "X-1":
        return f"好的，已为您成功受理{app}{srv}网络保障（{res} / 时延≤{rtt}）；另外关于{ood_goal or '手机话费充值与账单查询'}，目前暂不支持在线代办，请前往掌上营业厅查看。"
    elif tid == "T2-2":
        if turn_idx == 1:
            return f"收到，请问您是要进行'{app}{srv}'还是其他业务的保障？画质和时延有什么具体要求吗？"
        else:
            return f"好的，已为您开通{app}{srv}网络保障（{res} / 时延≤{rtt}），祝您使用愉快！"
    elif tid == "T2-5":
        if turn_idx == 1:
            return f"收到，请问是否按老规矩（{res} / 时延≤{rtt}）为您开通2小时保障？"
        else:
            return f"好的，已为您将{app}{srv}保障时长延长至180分钟（至17:00），配置保持{res}/时延≤{rtt}，保障已生效！"
    elif tid == "T2-3":
        if turn_idx == 1:
            return f"收到，请问是否按老规矩标准（1080p / 时延≤50ms）为您开通？"
        else:
            return f"收到，已临时为您调整为画质{res}、时延上限{rtt}，保障已为您生效！"
    elif is_last:
        if role == "evidence_session" and decl_mode == "explicit_declaration":
            return f"好的，已为您成功受理本次保障，并已为您将该配置记录为长期老规矩，祝您使用愉快！"
        else:
            return f"好的，已为您成功受理{app}{srv}网络保障（{res} / 时延≤{rtt}），祝您使用愉快！"
    else:
        if role == "reinforcement_session" and decl_mode == "implicit_induction" and s_plan.get("session_id", "").endswith("-03"):
            return f"检测到您在【{trig_cond or env}】多次使用{app}{srv}保障，请问是否按上次标准（{res} / 时延≤{rtt}）为您开通并设为默认老规矩？"
        else:
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
