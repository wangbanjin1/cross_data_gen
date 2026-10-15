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
    elif tid == "T2-9":
        start_t = tp['start_timestamp'].split('日')[-1]
        end_t = tp['end_timestamp'].split('日')[-1]
        if s_plan.get("is_counterexample"):
            if turn_idx == 1:
                return f"今天在{env}做原画级视频采录，必须保持1080p高清，哪怕网络有波动也不能降画质，时间从{start_t}到{end_t}，帮我开{app}{srv}保障。"
            else:
                return "确认不降画质，我就需要1080p，直接开通。"
        elif s_plan.get("round_count") == 3:
            if turn_idx == 1:
                return f"今天在{env}有重要活动，开{app}{srv}保障，时间从{start_t}到{end_t}，画质要求1080p。"
            elif turn_idx == 2:
                return "降到720p画质够清晰吗？如果能大幅降低卡顿丢包，可以考虑。"
            else:
                return "行，听你的专业建议，按720p和时延加固开通吧。"
        else:
            if turn_idx == 1:
                return f"今天在{env}有大型活动，需要开{app}{srv}保障，时间从{start_t}到{end_t}。"
            else:
                return "好的，按你的专业建议来，就用这个加固方案。"
    elif tid == "T2-10":
        start_t = tp['start_timestamp'].split('日')[-1]
        end_t = tp['end_timestamp'].split('日')[-1]
        if turn_idx == 1:
            return f"今天在{env}现场天气很恶劣，按上次恶劣天气的抗衰落加固方案配{app}{srv}，从{start_t}开始。"
        else:
            return "对，直接按这套加固方案开通。"
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
                return "老规矩开保障，别掉链子。"
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
    elif tid == "T2-9":
        exp = s_plan.get("experience_citation", {})
        exp_title = exp.get("title", "极值与高密环境主动降画质保抗丢包平稳度")
        if s_plan.get("is_counterexample"):
            if turn_idx == 1:
                return f"收到，根据专家经验库【{exp_title}】，虽然高密拥塞推荐降画质保平稳，但经验库反例规则明确指出：当用户明确要求原画采录/强画质优先时，不得强制降级。为您保持画质{res}、时延{rtt}以内，确认直接开通吗？"
            else:
                return f"好的，已按经验反例边界为您保留原画规格，开通{app}{srv}保障（{res} / 时延≤{rtt}）。祝您采录顺利！"
        elif s_plan.get("round_count") == 3:
            if turn_idx == 1:
                return f"收到，注意到{env}属于超高密度人流聚集现场。根据专家经验库【{exp_title}】，极度拥塞环境下盲目开超清易引发上行信道争抢与丢包，建议将画质微调为{res}、时延锁定在{rtt}以内以稳定性优先。请问是否考虑采纳该建议？"
            elif turn_idx == 2:
                return f"720p在移动端清晰度完全满足日常巡检与直播，且能将信道丢包率降低80%以上，时延稳定在{rtt}。确认按此加固规格开通吗？"
            else:
                return f"好的，已采纳高密防拥塞加固经验，为您成功开通{app}{srv}稳定性保障（{res} / 时延≤{rtt}）。祝您现场活动顺利！"
        else:
            if turn_idx == 1:
                return f"收到，注意到{env}属于超高密度人流聚集现场。根据专家经验库【{exp_title}】，极度拥塞环境下盲目开超清易引发上行信道争抢与丢包，建议将画质微调为{res}、时延锁定在{rtt}以内以稳定性优先。请问是否同意采纳该优化建议？"
            else:
                return f"好的，已采纳高密防拥塞加固经验，为您成功开通{app}{srv}稳定性保障（{res} / 时延≤{rtt}）。祝您现场活动顺利！"
    elif tid == "T2-10":
        exp = s_plan.get("experience_citation", {})
        exp_title = exp.get("title", "恶劣天气高衰减环境增强抗丢包加固策略")
        if turn_idx == 1:
            return f"收到，已为您调取应对极端恶劣天气的抗衰落加固方案【{exp_title}】：画质微降至{res}、时延收紧至{rtt}以内（持续{tp['duration']}），以抗丢包连续性优先。确认按此方案启动保障吗？"
        else:
            return f"好的，已为您启动恶劣天气加固网络保障（{res} / 时延≤{rtt}）。祝您外勤平安顺利！"
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
            return f"好的，已为您直接按老规矩开通{app}{srv}保障（{res} / 时延≤{rtt}），祝您使用愉快！"
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
