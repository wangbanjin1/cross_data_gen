"""
对话渲染异常或离线兜底台词与动作类型规范化模块。
集中维护各模版（T1-2, X-1, T2-2, T2-5, T2-3, T2-4, T2-1, T1-1）的确定性行为。
"""

from src.templates.prompts.small_memory_prompt import (
    ambiguous_requirement,
    clarification_answer,
    clarification_question,
    co_occurrence_example,
    declaration_example,
)

def get_fallback_user_utterance(s_plan: dict, turn_idx: int, role: str) -> str:
    tp = s_plan["target_params"]
    aliases = s_plan.get("aliases", {})
    app_alias = (aliases.get("app_aliases") or [tp["application_name"]])[0]
    srv_alias = (aliases.get("service_aliases") or [tp["service_name"]])[0]
    res_alias = (aliases.get("resolution_aliases") or [tp["resolution"]])[0]
    rtt_alias = (aliases.get("rtt_aliases") or [tp["rtt"]])[0]
    dur_alias = (aliases.get("duration_aliases") or [tp["duration"]])[0]
    small_memory = s_plan.get("small_memory", {})
    small_alias = small_memory.get("value")
    small_declaration = declaration_example(small_memory)
    evidence_mode = s_plan.get("small_memory_evidence_mode", "explicit_declaration")

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
    b_type = s_plan.get("blueprint_type", "")

    if tid == "T1-2":
        return f"你好，现场这边网络好像有问题，能帮我安排师傅处理一下{ood_goal or '宽带光纤装维报修'}吗？"
    elif tid == "X-1":
        return f"帮我办理一下今天{tp['start_timestamp'].split('日')[-1]}的{app_alias}{srv_alias}网络保障，另外顺便帮我查询一下{ood_goal or '手机话费充值与账单查询'}。"
    elif tid in ["T2-2", "T3-1"]:
        if turn_idx == 1:
            return f"在{env}网络不太稳，帮我给{app}{srv}开个保障，时间从今天{tp['start_timestamp'].split('日')[-1]}开始。"
        elif evidence_mode == "cross_turn_clarification" and turn_idx == 2:
            fuzzy = ambiguous_requirement(small_memory)
            return f"{fuzzy}时延控制在{rtt}以内，预计持续{tp['duration']}。"
        elif evidence_mode == "cross_turn_clarification" and turn_idx == 3:
            return clarification_answer(small_memory)
        else:
            memory_sentence = f"{small_declaration}帮我记一下。" if small_declaration else ""
            return f"是{srv}业务，画质要{res}，时延控制在{rtt}以内，从今天{tp['start_timestamp'].split('日')[-1]}开始，预计持续{tp['duration']}。{memory_sentence}"
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
        if role == "reinforcement_session" and decl_mode == "implicit_induction" and s_plan.get("session_id", "").endswith("-03"):
            return f"今天又到{env}办事了，这次按上次的来。"
        elif role == "evidence_session":
            return f"你好，需要给{app}{srv}做一个网络保障，时间是今天{tp['start_timestamp'].split('日')[-1]}开始。"
        elif role in ["reinforcement_session", "reuse_session"]:
            memory_hints = {
                "application_alias": f"用{small_alias}做{srv}",
                "service_default_app": f"做{small_alias}，应用按默认的",
                "resolution_alias": f"用{app}做{srv}，画质按‘{small_alias}’",
                "rtt_alias": f"用{app}做{srv}，时延按‘{small_alias}’",
                "duration_alias": f"用{app}做{srv}，时长按‘{small_alias}’",
                "period_alias": f"按‘{small_alias}’的时间，用{app}做{srv}",
            }
            memory_hint = memory_hints.get(small_memory.get("type"), f"用{app}做{srv}")
            return f"老规矩，在{env}，{memory_hint}，帮我把保障开上。"
        else:
            return f"你好，需要给{app_alias}{srv_alias}做一个网络保障，时间是今天{tp['start_timestamp'].split('日')[-1]}开始。"
    else:
        if role == "evidence_session" and (decl_mode == "explicit_declaration" or b_type in ["sub_01", "sub_02"]):
            dur_text = f"，预计持续{dur_alias}（到{tp['end_timestamp'].split('日')[-1]}）"
            alias_intro = f"{small_declaration}" if small_declaration else ""
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
            return f"好的，画质用{res}，时延{rtt}以内，预计持续{dur_alias}。今天就按这个配置开通吧。"
        elif role == "reinforcement_session" and decl_mode == "implicit_induction" and s_plan.get("session_id", "").endswith("-03"):
            if evidence_mode == "co_occurrence":
                memory_sentence = co_occurrence_example(small_memory)
            else:
                memory_sentence = f"{small_declaration}帮我记一下。" if small_declaration else ""
            return f"对，就按这个标准来，以后这个场景也按这套配置。{memory_sentence}"
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
    small_memory = s_plan.get("small_memory", {})
    small_declaration = declaration_example(small_memory)
    evidence_mode = s_plan.get("small_memory_evidence_mode", "explicit_declaration")

    if tid == "T1-2":
        return f"抱歉，本智能助手仅提供手机移动网络加速与保障服务，暂不支持办理{ood_goal or '宽带光纤装维报修'}业务，建议您联系宽带专线处理。"
    elif tid == "X-1":
        return f"好的，已为您成功受理{app}{srv}网络保障（{res} / 时延≤{rtt}）；另外关于{ood_goal or '手机话费充值与账单查询'}，目前暂不支持在线代办，请前往掌上营业厅查看。"
    elif tid in ["T2-2", "T3-1"]:
        if turn_idx == 1:
            return f"收到，已确认是{app}{srv}保障。请问画质、时延和持续时长有什么具体要求？"
        elif evidence_mode == "cross_turn_clarification" and turn_idx == 2:
            return clarification_question(small_memory)
        elif evidence_mode == "cross_turn_clarification" and turn_idx == 3:
            return f"好的，已按您刚确认的含义记录，并为您开通{app}{srv}保障（{res} / 时延≤{rtt}）。祝您使用愉快！"
        else:
            memory_ack = f"并已记录您的习惯：{small_declaration}" if small_declaration else ""
            return f"好的，已为您开通{app}{srv}网络保障（{res} / 时延≤{rtt}），{memory_ack}祝您使用愉快！"
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
            return f"好的，已按您刚才的表达记录这个使用习惯，并为您开通本次保障。祝您使用愉快！"
        else:
            return f"好的，已为您成功受理{app}{srv}网络保障（{res} / 时延≤{rtt}），祝您使用愉快！"
    else:
        if role == "evidence_session":
            return f"收到，已为您锁定{app}{srv}保障，时间从{tp['start_timestamp'].split('日')[-1]}开始。请问您需要保障的清晰度、时延上限和预计持续时长分别是多少呢？"
        elif role == "reinforcement_session" and decl_mode == "implicit_induction" and s_plan.get("session_id", "").endswith("-03"):
            start_text = tp['start_timestamp'].split('日')[-1]
            end_text = tp['end_timestamp'].split('日')[-1]
            return f"我查到您上次在这个场景使用的是{app}{srv}，配置为{res}、时延{rtt}以内、持续{tp['duration']}。本次计划{start_text}至{end_text}，是否按这套配置开通？如果确认，我也可以将它设为以后这个场景的默认配置。"
        elif role in ["reinforcement_session", "reuse_session"]:
            start_text = tp['start_timestamp'].split('日')[-1]
            end_text = tp['end_timestamp'].split('日')[-1]
            return f"收到，我调取到之前登记的{app}{srv}配置：{res}、时延{rtt}以内，{start_text}开始、{end_text}结束，持续{tp['duration']}。确认按这套配置开通吗？"
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
    is_implicit_reinf = role == "reinforcement_session" and s_plan.get("declaration_mode") == "implicit_induction" and s_plan.get("session_id", "").endswith("-03")

    if tid == "T1-2":
        return ["Create_Intent_Request"], ["Reject_Request"]
    elif tid == "X-1":
        return ["Create_Intent_Request", "Inform_Slot"], ["Acknowledge", "Reject_Request"]
    elif tid in ["T2-2", "T3-1"]:
        if turn_idx == 1:
            return ["Create_Intent_Request", "Inform_Slot"], ["Request_Slot"]
        elif s_plan.get("small_memory_evidence_mode") == "cross_turn_clarification" and not is_last:
            return ["Inform_Slot"], ["Request_Disambiguation"]
        else:
            return (["Confirm_Slot"], ["Acknowledge"]) if turn_idx > 2 else (["Inform_Slot"], ["Acknowledge"])
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
            if is_implicit_reinf:
                u_acts = ["Create_Intent_Request"]
            elif not u_acts:
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
