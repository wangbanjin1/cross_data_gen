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

import re

def _sanitize_env(env: str, time_str: str = "") -> str:
    if not env:
        return "现场"
    # 优先匹配特定现场
    patterns = [
        ("公益赛事", "公益赛事活动现场"),
        ("外业调查", "外业调查实验现场"),
        ("音乐节", "城市音乐节现场"),
        ("联合执法", "联合执法执勤现场"),
        ("金融展会", "跨境商贸展会现场"),
        ("社区宣传", "社区宣传走访现场"),
        ("设计展", "设计展提案现场"),
        ("道路巡逻", "道路巡逻现场"),
        ("巡逻线", "道路巡逻现场"),
        ("社区走访", "社区走访现场"),
        ("走访", "社区走访现场"),
        ("晚间户外", "晚间户外活动现场"),
        ("街区采访", "街区采访现场"),
        ("沿海", "沿海巡逻岸线"),
        ("高山", "高山露天训练场"),
        ("大巴", "大巴转场途中"),
        ("酒店", "驻地酒店休息区"),
    ]
    for kw, loc in patterns:
        if kw in env:
            env = loc
            break

    # 时段防冲突检查：如果时间是 11:00 以后的午间/下午/晚上，严禁出现“早高峰/早间/晨间”
    if time_str:
        m = re.search(r'(\d{1,2})[时:]', time_str)
        if m:
            hour = int(m.group(1))
            if hour >= 11:
                env = env.replace("早高峰", "外勤").replace("早间", "日间").replace("晨间", "日间")
            if hour < 17:
                env = env.replace("晚间", "日间").replace("夜间", "日间")

    if len(env) > 10 or any(kw in env for kw in ["当", "进入", "触发", "身处", "。"]):
        return "外勤保障现场"
    return env.strip("，, 。. ")

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
    env = _sanitize_env(s_plan.get("scenario_env", ""), tp.get("start_timestamp", ""))
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
            return f"{fuzzy}，时延控制在{rtt}以内，预计持续{tp['duration']}。"
        elif evidence_mode == "cross_turn_clarification" and turn_idx == 3:
            return clarification_answer(small_memory)
        else:
            memory_sentence = f"{small_declaration}帮我记一下。" if small_declaration else ""
            return f"是{srv}业务，画质要{res}，时延控制在{rtt}以内，从今天{tp['start_timestamp'].split('日')[-1]}开始，预计持续{tp['duration']}。{memory_sentence}"
    elif b_type == "experience_learning":
        exp_id = s_plan.get("experience_id") or s_plan.get("experience_citation", {}).get("experience_id")
        if exp_id == "EXP_CALENDAR_HOLIDAY_EXCEPTION_01":
            if turn_idx == 1:
                return f"今天在{env}，帮我安排下周例行的{app}{srv}保障。对了，上次中秋放假，系统还在空荡荡的办公室空跑保障扣费，太浪费了！这次千万别再搞出节假日空跑这种事！"
            else:
                return "好的，有这个避让经验就好，这次直接开通吧。"
        elif exp_id == "EXP_MULTI_INTENT_PARTITION_01":
            if turn_idx == 1:
                return f"今天在{env}，帮我把上午的{app}{srv}保障开通一下。上次让你们延期上午任务，结果把下午的保障也给顺延搞砸了，这次多任务可千万别互相串扰！"
            else:
                return "行，这次分清楚就好，直接开通吧。"
        elif exp_id == "EXP_PREWARM_BUFFER_01":
            if turn_idx == 1:
                return f"今天在{env}有重要活动，开{app}{srv}保障。上次开场掐着点才起保，结果设备调试连线卡了十几分钟差点耽误事！大型现场这次必须吸取教训！"
            else:
                return "对，现场提前试机才稳妥，确认开通。"
        elif exp_id == "EXP_ORDER_QUALITY_DISAMBIGUATION_01":
            if turn_idx == 1:
                return f"今天在{env}，帮我按之前的配置开通{app}{srv}保障。上次调了有丢包抖动的异常工单来复用，导致推流也跟着受影响，这次可别乱复用有问题的单据！"
            else:
                return "好的，能自动甄别高质量工单就行，开通吧。"
        elif exp_id == "EXP_OVERLAPPING_ORDER_RESOLUTION_01":
            if turn_idx == 1:
                return f"今天在{env}需要开个紧急{app}{srv}保障。上次临时加塞任务，和原来的日常保障时间撞车重叠，系统直接报错冲突，这次可得把时间协调好！"
            else:
                return "很好，按时序让路衔接就行，开通吧。"
        else:
            if turn_idx == 1:
                return f"今天在{env}开{app}{srv}保障，上次踩坑的教训一定要记牢，严格按经验策略规范执行！"
            else:
                return "好的，按经验开通吧。"
    elif s_plan.get("experience_citation", {}).get("experience_id") == "EXP_CALENDAR_HOLIDAY_EXCEPTION_01":
        if turn_idx == 1:
            return f"今天在{env}，帮我把例行周会的{app}{srv}保障开上，时间是下周一。"
        else:
            return "好的，太周到了，就顺延到10月8日开通吧。"
    elif tid == "T2-4" or s_plan.get("experience_citation", {}).get("experience_id") == "EXP_MULTI_INTENT_PARTITION_01":
        if turn_idx == 1:
            return f"帮我改一下上午的{app}{srv}保障，临时通知延误了推迟到12:00结束；下午的保障千万别动，保持原样。"
        else:
            return "对，确认修改上午保障，下午锁定不动。"
    elif tid == "T2-9" or s_plan.get("experience_citation", {}).get("experience_id") == "EXP_PREWARM_BUFFER_01":
        nom_start = s_plan.get("nominal_start")
        nom_start_t = nom_start.split('日')[-1] if nom_start else tp['start_timestamp'].split('日')[-1]
        end_t = tp['end_timestamp'].split('日')[-1]
        if s_plan.get("is_counterexample"):
            if turn_idx == 1:
                return f"今天在{env}做原画级视频采录，必须保持1080p高清，哪怕网络有波动也不能降画质，时间从{nom_start_t}到{end_t}，帮我开{app}{srv}保障。"
            else:
                return "确认不降画质，我就需要1080p，直接开通。"
        elif s_plan.get("round_count") == 3:
            if turn_idx == 1:
                return f"今天在{env}有重要活动直播，开{app}{srv}保障，时间从{nom_start_t}到{end_t}，画质要求1080p。"
            elif turn_idx == 2:
                return "提前半小时试机预热够充分吗？只要开场不卡顿就行。"
            else:
                return "行，听你的，就提前半小时预热开通吧。"
        else:
            if turn_idx == 1:
                return f"今天在{env}有重大活动直播，帮我开{app}{srv}保障，时间从{nom_start_t}到{end_t}。"
            else:
                return "好的，提前半小时试机预热太重要了，按这个开通！"
    elif s_plan.get("experience_citation", {}).get("experience_id") == "EXP_ORDER_QUALITY_DISAMBIGUATION_01":
        if turn_idx == 1:
            return f"今天在{env}，帮我开个{app}{srv}保障，就按上周办得好的那次规格来办。"
        else:
            return "对，就按那次办，直接开通。"
    elif tid == "T2-10" or s_plan.get("experience_citation", {}).get("experience_id") == "EXP_OVERLAPPING_ORDER_RESOLUTION_01":
        start_t = tp['start_timestamp'].split('日')[-1]
        end_t = tp['end_timestamp'].split('日')[-1]
        if turn_idx == 1:
            return f"下午要在{env}开个紧急{app}{srv}保障，但刚才系统里还有笔日常单子时间重叠撞车了，能直接接上吗？"
        else:
            return "太好了，就按这个让路方案开通！"
    elif tid == "T2-5":
        if turn_idx == 1:
            return f"今天在{env}，老规矩，用{app_alias}做{srv_alias}，帮我把保障开上。"
        else:
            return f"对，老规矩不变，不过今天现场活动延长了，帮我把保障时长延长到{tp['duration']}。"
    elif tid == "T2-6":
        start_t = tp['start_timestamp'].split('日')[-1]
        end_t = tp['end_timestamp'].split('日')[-1]
        is_disambig = s_plan.get("is_disambiguation", False) or s_plan.get("round_count") == 3
        if is_disambig:
            if turn_idx == 1:
                return f"今天在{env}，想按之前的工单规格开{app}{srv}保障，时间从{start_t}到{end_t}。"
            elif turn_idx == 2:
                return "按最近那次开通的规格来就行。"
            else:
                return "对，确认按这个规格开通。"
        elif s_plan.get("working_memory_pointer", {}).get("inferred_delta_days", 7) >= 25:
            if turn_idx == 1:
                return f"今天在{env}，调一下上个月初在{env}办的那个工单规格，今天也按那套来。"
            else:
                return f"今天是从{start_t}到{end_t}，持续{tp['duration']}。"
        else:
            if turn_idx == 1:
                return f"这次去{env}，还按上周在{env}办的那个规格来。"
            else:
                return f"今天是从{start_t}到{end_t}，持续{tp['duration']}。"
    elif tid == "T2-7":
        start_t = tp['start_timestamp'].split('日')[-1]
        is_advance = s_plan.get("working_memory_pointer", {}).get("reschedule_direction") == "advance"
        if is_advance:
            if turn_idx == 1:
                return f"把昨天预约的{app}{srv}保障提前一个小时开始。"
            else:
                return "对，确认提前并按新时间修改。"
        else:
            if turn_idx == 1:
                return f"把昨天预约的{app}{srv}保障往后推迟一个小时。"
            else:
                return "对，确认修改。"
    elif tid == "T2-8":
        scope = s_plan.get("working_memory_query", {}).get("reconcile_scope", "")
        if "全月" in scope:
            return "帮我做个全月保障总对账，查下这一个月总共开了几次保障，累计多长时间？"
        return f"帮我查下这周总共开了几次保障，一共多长时间？"
    elif tid == "T2-3":
        if turn_idx == 1:
            return f"今天在{env}，老规矩，用{app}做{srv}，帮我把保障开上。"
        else:
            return f"对，不过今天现场特殊，画质临时调到{res}，时延压到{rtt}以内，今天临时按这个来。"
    elif tid == "T1-1" or b_type == "distractor":
        start_t = tp['start_timestamp'].split('日')[-1]
        end_t = tp['end_timestamp'].split('日')[-1]
        return f"你好，今天{start_t}到{end_t}要在{app}开{srv}（开{tp['duration']}），画质要{res}，时延控制在{rtt}以内，帮我开个保障。"
    elif turn_idx == 1:
        if role == "reinforcement_session" and decl_mode == "implicit_induction" and s_plan.get("session_id", "").endswith("-03"):
            return f"今天在{env}，做{srv}，这次按上次的来。"
        elif role == "evidence_session":
            return f"你好，需要给{app}{srv}做一个网络保障，时间是今天{tp['start_timestamp'].split('日')[-1]}开始。"
        elif role in ["reinforcement_session", "reuse_session"]:
            if s_plan.get("agility_factor") == 1.0:
                if trig_type == "time_periodic":
                    time_prompt = "午间例行这个时候" if period_type == "daily" else ("每月例会这个时候" if period_type == "monthly" else "每周例行这个时候")
                    return f"老规矩，{time_prompt}，用{app}做{srv}，帮我把保障开上，别掉链子。"
                else:
                    return f"老规矩，在{env}，用{app}做{srv}，帮我把保障开上，别掉链子。"
            memory_hints = {
                "application_alias": f"用{small_alias}做{srv}",
                "service_default_app": f"做{small_alias}，应用按默认的",
                "resolution_alias": f"用{app}做{srv}，画质按‘{small_alias}’",
                "rtt_alias": f"用{app}做{srv}，时延按‘{small_alias}’",
                "duration_alias": f"用{app}做{srv}，时长按‘{small_alias}’",
                "period_alias": f"按‘{small_alias}’的时间，用{app}做{srv}",
            }
            memory_hint = memory_hints.get(small_memory.get("type"), f"用{app}做{srv}")
            if trig_type == "time_periodic":
                p_text = "午间例行" if period_type == "daily" else ("每月例会" if period_type == "monthly" else "每周例行")
                return f"老规矩，{p_text}，在{env}，{memory_hint}，帮我把保障开上。"
            else:
                return f"老规矩，在{env}，{memory_hint}，帮我把保障开上。"
        else:
            return f"你好，需要给{app_alias}{srv_alias}做一个网络保障，时间是今天{tp['start_timestamp'].split('日')[-1]}开始。"
    else:
        if role == "evidence_session" and turn_idx == 3:
            return "对，确认直接开通。"
        elif role == "evidence_session" and (decl_mode == "explicit_declaration" or b_type in ["sub_01", "sub_02"]):
            dur_text = f"，预计持续{dur_alias}（到{tp['end_timestamp'].split('日')[-1]}）"
            alias_intro = f"{small_declaration}" if small_declaration else ""
            trig_desc = env if len(trig_cond) > 10 else (trig_cond or env)
            if trig_type == "task_activity":
                return f"好的，画质用{res}，时延{rtt}以内{dur_text}。{alias_intro}以后只要我提到执行【{trig_desc}】任务，就按老规矩来：{app}{srv}、{res}、{rtt}以内，帮我把这个习惯记好，别掉链子。"
            elif trig_type == "location_environment":
                return f"好的，画质用{res}，时延{rtt}以内{dur_text}。{alias_intro}以后只要我处于【{env}】，就按老规矩来：{app}{srv}、{res}、{rtt}以内，帮我把这个习惯记好，别掉链子。"
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
    b_type = s_plan.get("blueprint_type", "")
    ood_goal = s_plan.get("ood_goal", "")
    decl_mode = s_plan.get("declaration_mode", "explicit_declaration")
    trig_type = s_plan.get("storyline_trigger_type", "time_periodic")
    period_type = s_plan.get("period_type", "weekly")
    trig_cond = s_plan.get("trigger_condition", "")
    env = _sanitize_env(s_plan.get("scenario_env", ""), tp.get("start_timestamp", ""))
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
    elif b_type == "experience_learning":
        exp_id = s_plan.get("experience_id") or s_plan.get("experience_citation", {}).get("experience_id")
        if exp_id == "EXP_CALENDAR_HOLIDAY_EXCEPTION_01":
            if turn_idx == 1:
                return "非常抱歉上次放假期间未能智能识别法定假日，导致例行保障空跑！我们已深刻复盘并沉淀【节假日与调休避让经验】。今后遇到法定假日，系统将主动提醒并顺延至节后首个工作日办理，绝不让您承担空跑费用。当前例行保障已为您配置就绪，确认直接开通吗？"
            else:
                return f"好的，已为您开通本次例行网络保障（{res} / 时延≤{rtt}），同时已将节假日避让规则沉淀至经验记忆库中，祝您工作顺利！"
        elif exp_id == "EXP_MULTI_INTENT_PARTITION_01":
            if turn_idx == 1:
                return "非常抱歉上次多任务调整时未能做好因果隔离，导致上午任务的延后误伤了下午的配置！我们已沉淀【多任务因果隔离经验】，对多意图进行原子锁定时序隔离，绝不会交叉污染。本次上午保障已为您配置就绪，确认按此开通吗？"
            else:
                return f"好的，已为您成功受理本次保障（{res} / 时延≤{rtt}），多意图因果隔离规则已稳固沉淀至经验库，祝现场一切顺利！"
        elif exp_id == "EXP_PREWARM_BUFFER_01":
            if turn_idx == 1:
                return f"非常抱歉上次掐点起保导致缺少预热缓冲时间！我们已深刻总结并沉淀【重大活动预热试机缓冲经验】。对于大型场馆及展会，系统会智能识别并建议将保障提前30分钟提前起保试机。当前保障已配置就绪，确认直接开通吗？"
            else:
                return f"好的，已为您开通本次保障（{res} / 时延≤{rtt}），并已将提前30分钟预热试机策略正式纳入经验记忆库，祝活动圆满成功！"
        elif exp_id == "EXP_ORDER_QUALITY_DISAMBIGUATION_01":
            if turn_idx == 1:
                return "非常抱歉！上次盲目复用了存在抖动隐患的工单。我们已汲取教训并建立【历史工单网络质量评估经验】，今后复用时将自动调取质差分析日志，仅锁定全程无丢包的最优质量工单。本次配置已为您准备就绪，确认开通吗？"
            else:
                return f"好的，已按优质标准为您开通本次保障（{res} / 时延≤{rtt}），质量甄选经验已正式写入经验库，祝您使用顺畅！"
        elif exp_id == "EXP_OVERLAPPING_ORDER_RESOLUTION_01":
            if turn_idx == 1:
                return "非常抱歉上次工单时段重叠时处理生硬！我们已针对性沉淀【工单时序重叠仲裁经验】。当新旧保障重叠时，系统会自动在冲突节点让原工单提前让路结单、新保障准时接管。当前配置已就绪，确认开通吗？"
            else:
                return f"好的，已为您开通本次保障（{res} / 时延≤{rtt}），工单时钟让路仲裁规则已沉淀至经验记忆库，祝您工作顺利！"
        else:
            if turn_idx == 1:
                return f"非常抱歉此前在保障执行中出现偏差！我们已复盘并沉淀经验规则，当前保障已为您配置完毕，确认直接开通吗？"
            else:
                return f"好的，已为您成功受理本次保障（{res} / 时延≤{rtt}），经验策略已沉淀至经验库！"
    elif s_plan.get("experience_citation", {}).get("experience_id") == "EXP_CALENDAR_HOLIDAY_EXCEPTION_01":
        learn_sid = s_plan.get("learning_source_session")
        learn_prefix = f"根据此前在 {learn_sid} 总结沉淀的" if learn_sid else "根据此前总结沉淀的"
        if turn_idx == 1:
            return f"收到，识别到下周一恰逢国庆节法定长假第一天，办公区全员放假。{learn_prefix}节假日避让经验，为您将保障顺延至节后首个工作日（10月8日）同时段办理，避免放假期间空跑产生费用，确认按此顺延办理吗？"
        else:
            return f"好的，已为您将例行周会网络保障顺延至10月8日办理（{res} / 时延≤{rtt}），祝您假期愉快！"
    elif tid == "T2-4" or s_plan.get("experience_citation", {}).get("experience_id") == "EXP_MULTI_INTENT_PARTITION_01":
        learn_sid = s_plan.get("learning_source_session")
        learn_prefix = f"根据此前在 {learn_sid} 总结沉淀的" if learn_sid else "根据此前总结沉淀的"
        if turn_idx == 1:
            return f"收到！已针对上午保障任务进行局部调整，结束时间顺延至12:00并重算时长；{learn_prefix}多意图因果隔离经验，下午任务已严格锁定冻结不变，防止相互干扰，确认按此生效吗？"
        else:
            return f"好的，已完成多任务时序因果隔离调整，上午保障已延长至12:00，下午任务维持原配置不变！"
    elif tid == "T2-9" or s_plan.get("experience_citation", {}).get("experience_id") == "EXP_PREWARM_BUFFER_01":
        pw_start_t = tp['start_timestamp'].split('日')[-1]
        end_t = tp['end_timestamp'].split('日')[-1]
        learn_sid = s_plan.get("learning_source_session")
        learn_prefix = f"根据此前在 {learn_sid} 总结沉淀的" if learn_sid else "根据此前总结沉淀的"
        if s_plan.get("is_counterexample"):
            if turn_idx == 1:
                return f"收到，{env}现场人比较多，一般建议优先保流畅；不过既然您明确需要原画采录，已按您的要求保持{res}画质、时延{rtt}以内，确认直接开通吗？"
            else:
                return f"好的，已按原画要求为您开通{app}{srv}保障（{res} / 时延≤{rtt}），祝您录制顺利！"
        elif s_plan.get("round_count") == 3:
            if turn_idx == 1:
                return f"收到，{env}现场人特别多，建议将保障时间提前30分钟推算为{pw_start_t}至{end_t}进行试机预热。您看这样合适吗？"
            elif turn_idx == 2:
                return f"预留30分钟试机能够确保开场推流平稳流畅，画质{res}、时延稳定在{rtt}。确认按这个开通吗？"
            else:
                return f"好的，已为您开通{app}{srv}保障（{pw_start_t}至{end_t}，{res} / 时延≤{rtt}），祝您现场活动顺利！"
        else:
            if turn_idx == 1:
                return f"收到！大型现场设备调试与连线建议提前预热试机。{learn_prefix}重大活动起保经验，为您将保障时间自动提前30分钟推算为{pw_start_t}至{end_t}（保障时长扩至{tp['duration']}），确认直接开通吗？"
            else:
                return f"好的，已为您成功受理{app}{srv}网络保障（{pw_start_t}至{end_t}，{res} / 时延≤{rtt}），预留30分钟预热试机，祝现场顺利！"
    elif s_plan.get("experience_citation", {}).get("experience_id") == "EXP_ORDER_QUALITY_DISAMBIGUATION_01":
        learn_sid = s_plan.get("learning_source_session")
        learn_prefix = f"根据此前在 {learn_sid} 总结沉淀的" if learn_sid else "根据此前总结沉淀的"
        if turn_idx == 1:
            return f"已为您调取历史工单网络质量评估日志，查到上周存在多次记录，其中周四单据曾有时延波动，而周二工单全程无丢包、质量最优。{learn_prefix}高质量工单甄选经验，已为您锁定该高质量工单（{res} / 时延≤{rtt}），确认直接开通吗？"
        else:
            return f"好的，已按优质历史工单为您成功受理{app}{srv}网络保障，祝您使用顺畅！"
    elif tid == "T2-10" or s_plan.get("experience_citation", {}).get("experience_id") == "EXP_OVERLAPPING_ORDER_RESOLUTION_01":
        learn_sid = s_plan.get("learning_source_session")
        learn_prefix = f"根据此前在 {learn_sid} 总结沉淀的" if learn_sid else "根据此前总结沉淀的"
        if turn_idx == 1:
            return f"检测到新申请的保障与已预约的日常工单存在时段重叠。{learn_prefix}工单时序仲裁经验，协调原工单在冲突交界点提前结单让路，新保障准时无缝激活接管，避免重复计费，确认按此开通吗？"
        else:
            return f"好的，已完成工单时钟让路仲裁，原工单提前结单，新保障将于准时无缝接续生效！"
    elif tid == "T2-5":
        start_t = tp['start_timestamp'].split('日')[-1]
        if turn_idx == 1:
            return f"收到，我调取到之前登记的{app}{srv}配置：画质{res}、时延{rtt}以内，从{start_t}开始保障，确认按这套配置开通吗？"
        else:
            return f"好的，已按老规矩为您开通{app}{srv}保障：画质保持{res}、时延上限{rtt}，时长已延长至{tp['duration']}。祝您活动顺利！"
    elif tid == "T2-6":
        start_t = tp['start_timestamp'].split('日')[-1]
        end_t = tp['end_timestamp'].split('日')[-1]
        is_disambig = s_plan.get("is_disambiguation", False) or s_plan.get("round_count") == 3
        if is_disambig:
            cand_ids = s_plan.get("working_memory_pointer", {}).get("candidate_record_ids", [])
            cand_str = "、".join(cand_ids) if cand_ids else "工单A和工单B"
            if turn_idx == 1:
                return f"收到，查询到您此前在{env}有多次{app}{srv}保障工单（包括 {cand_str}），配置规格略有差异。请问您今天是指按哪一次的规格来开通呢？"
            elif turn_idx == 2:
                return f"明白，已精准锁定最近一次工单规格（{res} / 时延≤{rtt}），时段为{start_t}至{end_t}，确认直接开通吗？"
            else:
                return f"好的，已按您确认的历史工单规格成功开通今日{app}{srv}保障（{res} / 时延≤{rtt}，时段{start_t}至{end_t}）。祝您工作顺利！"
        elif s_plan.get("working_memory_pointer", {}).get("inferred_delta_days", 7) >= 25:
            if turn_idx == 1:
                return f"收到，已为您跨期调取到上个月在{env}的{app}{srv}历史工单（画质{res}、时延≤{rtt}）。请问今天具体的保障时间是几点到几点呢？"
            else:
                return f"好的，已按一个月前历史工单规格为您开通今日{app}{srv}保障（{res} / 时延≤{rtt}，时段{start_t}至{end_t}）。祝您工作顺利！"
        else:
            if turn_idx == 1:
                return f"收到，已为您在历史工单账本中找到上周在{env}的{app}{srv}保障单（画质{res}、时延≤{rtt}）。请问今天具体的保障时间是几点到几点呢？"
            else:
                return f"好的，已按您引用的历史工单规格为您成功开通今日{app}{srv}保障（{res} / 时延≤{rtt}，时段{start_t}至{end_t}）。祝您工作顺利！"
    elif tid == "T2-7":
        start_t = tp['start_timestamp'].split('日')[-1]
        end_t = tp['end_timestamp'].split('日')[-1]
        is_advance = s_plan.get("working_memory_pointer", {}).get("reschedule_direction") == "advance"
        if is_advance:
            if turn_idx == 1:
                return f"收到，已找到您此前预约的{app}{srv}保障工单。提前一小时后，新的保障时段为{start_t}至{end_t}，确认进行提前改期吗？"
            else:
                return f"好的，已为您成功办理工单提前生效变更，保障时段已更新为{start_t}至{end_t}生效。祝您使用顺利！"
        else:
            if turn_idx == 1:
                return f"收到，已找到您此前预约的{app}{srv}保障工单。往后推迟一小时后，新的保障时段为{start_t}至{end_t}，确认进行改期吗？"
            else:
                return f"好的，已为您成功办理工单延期变更，保障时段已更新为{start_t}至{end_t}生效。祝您使用顺利！"
    elif tid == "T2-8":
        query_info = s_plan.get("working_memory_query", {})
        total_orders = query_info.get("total_orders", 3)
        total_mins = query_info.get("total_duration_minutes", 300)
        scope = query_info.get("reconcile_scope", "")
        if "全月" in scope:
            return f"已为您生成全月历史工单总对账报表：本月您累计成功办理了 {total_orders} 次移动网络保障，累计保障总时长达 {total_mins} 分钟，涵盖各类重点场景，所有工单全部履约闭环。"
        return f"已为您查询到本周历史工单流水账：本周您共成功办理了 {total_orders} 次移动网络保障，累计保障时长达 {total_mins} 分钟，涵盖{app}{srv}等场景，所有工单均已按期履约。"
    elif tid == "T2-3":
        start_t = tp['start_timestamp'].split('日')[-1]
        end_t = tp['end_timestamp'].split('日')[-1]
        if turn_idx == 1:
            return f"收到，我调取到之前登记的{app}{srv}配置：画质1080p、时延50ms以内，{start_t}至{end_t}（持续{tp['duration']}），确认按这套配置开通吗？"
        else:
            return f"好的，已按现场特殊情况为您临时调整开通{app}{srv}保障：画质{res}、时延上限{rtt}，时段{start_t}至{end_t}。祝您现场顺利！"
    elif tid == "T1-1" or b_type == "distractor":
        return f"收到，已为您开通{app}{srv}网络保障：画质{res}，时延上限{rtt}，保障时间{tp['start_timestamp']}至{tp['end_timestamp']}（共{tp['duration']}）。祝您使用顺利！"
    elif is_last:
        if s_plan.get("agility_factor") == 1.0 and role in ["reinforcement_session", "reuse_session"]:
            start_t = tp['start_timestamp'].split('日')[-1]
            end_t = tp['end_timestamp'].split('日')[-1]
            return f"好的，已按老规矩为您开通{app}{srv}网络保障（{res} / 时延≤{rtt}，时段{start_t}至{end_t}），祝您使用愉快！"
        elif role == "evidence_session" and decl_mode == "explicit_declaration":
            return f"好的，已为您成功受理本次保障，并已为您将该配置记录为长期老规矩，祝您使用愉快！"
        elif role == "reinforcement_session" and decl_mode == "implicit_induction" and s_plan.get("session_id", "").endswith("-03"):
            return f"好的，已按您刚才的表达记录这个使用习惯，并为您开通本次保障。祝您使用愉快！"
        else:
            return f"好的，已为您成功受理{app}{srv}网络保障（{res} / 时延≤{rtt}），祝您使用愉快！"
    else:
        if role == "evidence_session":
            if turn_idx == 1:
                return f"收到，已为您锁定{app}{srv}保障，时间从{tp['start_timestamp'].split('日')[-1]}开始。请问您需要保障的清晰度、时延上限和预计持续时长分别是多少呢？"
            else:
                return f"收到，已为您登记老规矩习惯。确认按{res}、{rtt}以内立即为您开通本次保障吗？"
        elif role == "reinforcement_session" and decl_mode == "implicit_induction" and s_plan.get("session_id", "").endswith("-03"):
            start_text = tp['start_timestamp'].split('日')[-1]
            end_text = tp['end_timestamp'].split('日')[-1]
            loc_text = f"在{env}" if env and env != "现场" else "在上次场景"
            return f"我查到您上次{loc_text}使用的是{app}{srv}，配置为{res}、时延{rtt}以内、持续{tp['duration']}。本次计划{start_text}至{end_text}，是否按这套配置开通？如果确认，我也可以将它设为以后该场景的默认配置。"
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
    b_type = s_plan.get("blueprint_type", "")
    is_implicit_reinf = role == "reinforcement_session" and s_plan.get("declaration_mode") == "implicit_induction" and s_plan.get("session_id", "").endswith("-03")

    if b_type == "experience_learning":
        if turn_idx == 1:
            return ["Create_Intent_Request", "Inform_Slot"], ["Confirm_Slot", "Request_Slot"]
        else:
            return ["Confirm_Slot"], ["Acknowledge"]
    elif tid == "T1-2":
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
    elif tid == "T2-6":
        is_disambig = s_plan.get("is_disambiguation", False) or s_plan.get("round_count") == 3
        if is_disambig:
            if turn_idx == 1:
                return ["Create_Intent_Request", "Inform_Slot"], ["Request_Disambiguation"]
            elif turn_idx == 2:
                return ["Confirm_Slot", "Inform_Slot"], ["Confirm_Slot"]
            else:
                return ["Confirm_Slot"], ["Acknowledge"]
        else:
            if turn_idx == 1:
                return ["Create_Intent_Request", "Inform_Slot"], ["Confirm_Slot", "Request_Slot"]
            else:
                return ["Confirm_Slot", "Inform_Slot"], ["Acknowledge"]
    elif tid == "T2-7":
        if turn_idx == 1:
            return ["Modify_Request", "Inform_Slot"], ["Confirm_Slot"]
        else:
            return ["Confirm_Slot"], ["Acknowledge"]
    elif tid == "T2-8":
        return ["Create_Intent_Request"], ["Acknowledge"]
    elif tid == "T2-9":
        if s_plan.get("round_count") == 3:
            if turn_idx == 1:
                return ["Create_Intent_Request", "Inform_Slot"], ["Confirm_Slot"]
            elif turn_idx == 2:
                return ["Inform_Slot"], ["Confirm_Slot"]
            else:
                return ["Confirm_Slot"], ["Acknowledge"]
        else:
            if turn_idx == 1:
                return ["Create_Intent_Request", "Inform_Slot"], ["Confirm_Slot"]
            else:
                return ["Confirm_Slot"], ["Acknowledge"]
    elif tid == "T2-10":
        if turn_idx == 1:
            return ["Create_Intent_Request", "Inform_Slot"], ["Confirm_Slot"]
        else:
            return ["Confirm_Slot"], ["Acknowledge"]
    elif tid == "T2-3":
        if turn_idx == 1:
            return ["Create_Intent_Request", "Inform_Slot"], ["Confirm_Slot"]
        else:
            return ["Correct_Previous_Input", "Inform_Slot"], ["Acknowledge"]
    else:
        if role == "evidence_session" and s_plan.get("round_count") == 3:
            if turn_idx == 1:
                return ["Create_Intent_Request", "Inform_Slot"], ["Request_Slot"]
            elif turn_idx == 2:
                return ["Inform_Slot"], ["Confirm_Slot"]
            else:
                return ["Confirm_Slot"], ["Acknowledge"]
        elif s_plan.get("agility_factor") == 1.0 and s_plan.get("round_count") == 1:
            return ["Create_Intent_Request", "Inform_Slot"], ["Acknowledge"]

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
