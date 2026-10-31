"""用户侧确定性兜底台词生成模块。"""

from __future__ import annotations

import re
from src.templates.prompts.small_memory_prompt import (
    ambiguous_requirement,
    clarification_answer,
    co_occurrence_example,
    declaration_example,
)
from src.templates.prompts.fallback_helpers import (
    _formal_and_temp_dur_info,
    _implicit_service_phrase,
    _paraphrase_env,
    _paraphrase_period,
    _sanitize_env,
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
            sh_t = (s_plan.get("nominal_start") or tp.get("start_timestamp", "")).split("日")[-1] or "15时00分"
            eh_t = (s_plan.get("nominal_end") or tp.get("end_timestamp", "")).split("日")[-1] or "17时00分"
            dur_val = s_plan.get("base_dur") or tp.get("duration", "120min")
            if turn_idx == 1:
                return f"帮我预约下周一（10月5日，正值国庆假期）例行周会的{app}{srv}意图保障单，时间从{sh_t}到{eh_t}（持续{dur_val}），画质要求{res}，时延控制在{rtt}以内。"
            elif turn_idx == 2:
                return "哎呀，10月5日还在放国庆假呢，那天不开会！帮我把日期顺延到节后上班第一天（10月8日）吧。"
            else:
                return "对，确认顺延到10月8日节后首个工作日办理。"
        elif exp_id == "EXP_MULTI_INTENT_PARTITION_01":
            sh_t = tp.get("start_timestamp", "").split("日")[-1] or "12时30分"
            new_eh_t = tp.get("end_timestamp", "").split("日")[-1] or "14时30分"
            dur_val = tp.get("duration", "120min")
            if turn_idx == 1:
                return f"今天在{env}，从{sh_t}到{new_eh_t}（持续{dur_val}）我先跟搭档对一下正式抖音直播的词和镜头机位，帮我开个画质{res}、时延{rtt}以内的意图保障单。"
            elif turn_idx == 2:
                return "嗨，我只是先跟搭档私下对一下词和看眼机位，还没正式开播呢！平时对词我们都是打微信视频电话，改成微信视频通话吧。"
            else:
                return "对，改成微信视频通话就对了，确认按此开通。"
        elif exp_id == "EXP_PREWARM_BUFFER_01":
            nom_sh_t = (s_plan.get("nominal_start") or tp.get("start_timestamp", "")).split("日")[-1]
            eh_t = tp["end_timestamp"].split("日")[-1]
            base_dur = s_plan.get("nominal_dur") or s_plan.get("base_dur") or tp.get("duration", "120min")
            if turn_idx == 1:
                return f"今天在{env}有重要现场保障，活动{nom_sh_t}正式开始，帮我开从{nom_sh_t}到{eh_t}（持续{base_dur}）的{app}{srv}意图保障单，画质要求{res}，时延控制在{rtt}以内。"
            elif turn_idx == 2:
                return "等等，大型活动现场还得提前进场调试设备呢，掐着点开来不及！帮我把开始时间往前提前半小时吧。"
            else:
                return "好的，确认按提前半小时预热的配置开通。"
        elif exp_id == "EXP_ORDER_QUALITY_DISAMBIGUATION_01":
            sh_t = tp['start_timestamp'].split('日')[-1]
            d_info = _formal_and_temp_dur_info(tp)
            if turn_idx == 1:
                return f"今天在{env}办正式客户远程路演，从{sh_t}开始开{app}{srv}（画质{res}、时延{rtt}以内），保障时长和结束时间就按我上次办的那笔意图保障单来。"
            elif turn_idx == 2:
                return f"不对，{d_info['temp_spoken']}不够！前天那笔只是我临时插空开的短会，今天是正式路演，得按上周那笔正式单改成{d_info['formal_spoken']}。"
            else:
                return f"对，就按上周那笔{d_info['formal_spoken']}的正式路演单规格开通。"
        elif exp_id == "EXP_OVERLAPPING_ORDER_RESOLUTION_01":
            sh_t = tp.get("start_timestamp", "").split("日")[-1] or "15时00分"
            eh_t = tp.get("end_timestamp", "").split("日")[-1] or "17时00分"
            dur_val = tp.get("duration", "120min")
            if turn_idx == 1:
                return f"今天在{env}，{sh_t}到{eh_t}（持续{dur_val}）我受邀进主会场的抖音直播间当连麦嘉宾互动，帮我把抖音的保障开上，画质要求{res}，时延控制在{rtt}以内。"
            elif turn_idx == 2:
                return "不对，我是去当连麦嘉宾、要开摄像头上麦发言的，不是光在下面看直播！把业务类型改成开直播吧。"
            else:
                return "对，改成抖音开直播就对了，确认按此开通。"
        else:
            sh_t = tp['start_timestamp'].split('日')[-1]
            eh_t = tp['end_timestamp'].split('日')[-1]
            if turn_idx == 1:
                return f"今天在{env}开{app}{srv}意图保障单，时间从{sh_t}到{eh_t}（持续{tp['duration']}），画质要求{res}，时延控制在{rtt}以内。"
            else:
                return "好的，直接办理开通吧。"
    elif s_plan.get("experience_citation", {}).get("experience_id") == "EXP_CALENDAR_HOLIDAY_EXCEPTION_01":
        sh_t = (s_plan.get("nominal_start") or tp.get("start_timestamp", "")).split("日")[-1] or "15时00分"
        eh_t = (s_plan.get("nominal_end") or tp.get("end_timestamp", "")).split("日")[-1] or "17时00分"
        dur_val = tp.get("duration", "120min")
        if turn_idx == 1:
            return f"帮我预约下周一（10月5日，正值国庆假期）例行周会的{app}{srv}意图保障单，时间从{sh_t}到{eh_t}（持续{dur_val}），画质要求{res}，时延控制在{rtt}以内。"
        else:
            return "太周到了，参考上次的做法正合适，就按顺延到10月8日开通意图保障单吧！"
    elif tid == "T2-4" or s_plan.get("experience_citation", {}).get("experience_id") == "EXP_MULTI_INTENT_PARTITION_01":
        tp = s_plan.get("target_params", {})
        sh_t = tp.get("start_timestamp", "").split("日")[-1] or "12时30分"
        new_eh_t = tp.get("end_timestamp", "").split("日")[-1] or "14时30分"
        dur_val = tp.get("duration", "120min")
        if turn_idx == 1:
            return f"今天在{env}，{sh_t}至{new_eh_t}（持续{dur_val}）我先跟搭档对一下正式抖音直播的词和镜头机位，帮我开个画质{res}、时延{rtt}以内的意图保障单。"
        else:
            return f"太懂我了！私下跟搭档对直播词、看镜头机位平时就是打【微信-视频通话】，不用真开抖音直播间，确认按微信视频通话开通意图保障单！"
    elif tid == "T2-9" or s_plan.get("experience_citation", {}).get("experience_id") == "EXP_PREWARM_BUFFER_01":
        nom_start = s_plan.get("nominal_start")
        nom_start_t = nom_start.split('日')[-1] if nom_start else tp['start_timestamp'].split('日')[-1]
        nom_dur = s_plan.get("nominal_dur") or s_plan.get("base_dur") or tp.get("duration", "120min")
        end_t = tp['end_timestamp'].split('日')[-1]
        if s_plan.get("is_counterexample"):
            if turn_idx == 1:
                return f"今天在{env}做原画级视频采录，必须保持{res}高清、时延控制在{rtt}以内，哪怕网络有波动也不能降画质，时间从{nom_start_t}到{end_t}（持续{nom_dur}），帮我开{app}{srv}意图保障单。"
            else:
                return f"确认不降画质，我就需要{res}，直接开通。"
        elif s_plan.get("round_count") == 3:
            if turn_idx == 1:
                return f"今天在{env}有重大活动保障，开{app}{srv}意图保障单，时间从{nom_start_t}到{end_t}（原定时长{nom_dur}），画质要求{res}，时延控制在{rtt}以内。"
            elif turn_idx == 2:
                return "提前半小时试机预热够充分吗？只要开场不卡顿就行。"
            else:
                return "行，听你的，就提前半小时预热开通意图保障单吧。"
        else:
            if turn_idx == 1:
                return f"今天在{env}有重大活动保障，帮我开{app}{srv}意图保障单，活动时间从{nom_start_t}到{end_t}（原定时长{nom_dur}），画质要求{res}，时延控制在{rtt}以内。"
            else:
                return "好的，提前半小时试机预热太重要了，按这个开通意图保障单！"
    elif s_plan.get("experience_citation", {}).get("experience_id") == "EXP_ORDER_QUALITY_DISAMBIGUATION_01":
        start_t = tp['start_timestamp'].split('日')[-1]
        end_t = tp['end_timestamp'].split('日')[-1]
        d_info = _formal_and_temp_dur_info(tp)
        if turn_idx == 1:
            return f"今天在{env}要办一场正式客户远程路演，{start_t}开始开{app}{srv}（画质{res}、时延{rtt}以内），保障时长和结束时间就按我上次办的那笔意图保障单来。"
        else:
            return f"太准了！前天那笔只是{d_info['temp_short']}临时短会，今天正式客户路演就得按上周那笔正式路演单保满{d_info['formal_spoken']}（{start_t}到{end_t}，持续{d_info['formal_dur']}），确认直接开通！"
    elif tid == "T2-10" or s_plan.get("experience_citation", {}).get("experience_id") == "EXP_OVERLAPPING_ORDER_RESOLUTION_01":
        sh_t = tp.get("start_timestamp", "").split("日")[-1] or "15时00分"
        eh_t = tp.get("end_timestamp", "").split("日")[-1] or "17时00分"
        dur_val = tp.get("duration", "120min")
        if turn_idx == 1:
            return f"今天在{env}，{sh_t}到{eh_t}（持续{dur_val}）我受邀进主会场的抖音直播间当连麦嘉宾互动，帮我把抖音的保障开上，画质要求{res}、时延控制在{rtt}以内。"
        else:
            return "太细节了！进别人直播间当连麦嘉宾要上麦发言，确实得按【抖音-开直播】保上传而不是看直播，确认按此开通意图保障单！"
    elif tid == "T2-5":
        if turn_idx == 1:
            if s_plan.get("retrieval_challenge_type") == "implicit_service_collocation":
                return f"今天在{env}，老规矩，用{app_alias}{_implicit_service_phrase(srv)}，帮我把保障开上。"
            return f"今天在{env}，老规矩，用{app_alias}做{srv_alias}，帮我把保障开上。"
        elif turn_idx == 2:
            return f"对，老规矩不变，不过今天现场活动延长了，帮我把保障时长延长到{tp['duration']}。"
        else:
            return f"好的，确认按延长后的{tp['duration']}配置开通。"
    elif tid == "T2-6":
        start_t = tp['start_timestamp'].split('日')[-1]
        end_t = tp['end_timestamp'].split('日')[-1]
        is_disambig = s_plan.get("is_disambiguation", False)
        if is_disambig:
            if turn_idx == 1:
                return f"今天在{env}，想按之前的意图保障单规格开{app}{srv}保障，时间从{start_t}到{end_t}（持续{tp['duration']}）。"
            elif turn_idx == 2:
                return "按最近那次开通的规格来就行。"
            else:
                return "对，确认按这个规格开通。"
        elif s_plan.get("working_memory_pointer", {}).get("inferred_delta_days", 7) >= 25:
            if turn_idx == 1:
                return f"今天在{env}，调一下上个月初在{env}办的那个意图保障单规格，今天也按那套来。"
            elif turn_idx == 2:
                return f"今天是从{start_t}到{end_t}，持续{tp['duration']}。"
            else:
                return "对，确认按这个配置开通。"
        else:
            if turn_idx == 1:
                return f"这次去{env}，还按上周在{env}办的那个意图保障单规格来。"
            elif turn_idx == 2:
                return f"今天是从{start_t}到{end_t}，持续{tp['duration']}。"
            else:
                return "对，确认按这个配置开通。"
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
            if s_plan.get("retrieval_challenge_type") == "negation_contrast" and s_plan.get("contrast_negated_app"):
                neg_a = s_plan.get("contrast_negated_app")
                neg_s = s_plan.get("contrast_negated_service") or "视频会议"
                return f"今天在{env}，不用{neg_a}做{neg_s}了，老规矩用{app}做{srv}，帮我把保障开上。"
            return f"今天在{env}，老规矩，用{app}做{srv}，帮我把保障开上。"
        elif turn_idx == 2:
            return f"对，不过今天现场特殊，画质临时调到{res}，时延压到{rtt}以内，今天临时按这个来。"
        else:
            return "好的，确认按这个临时调整的配置开通。"
    elif tid == "T1-1" or b_type == "distractor":
        start_t = tp['start_timestamp'].split('日')[-1]
        end_t = tp['end_timestamp'].split('日')[-1]
        if s_plan.get("retrieval_challenge_type") == "negation_contrast" and s_plan.get("contrast_negated_app"):
            neg_a = s_plan.get("contrast_negated_app")
            neg_s = s_plan.get("contrast_negated_service") or "开直播"
            return f"你好，今天不用{neg_a}做{neg_s}了，{start_t}到{end_t}改在{app}开{srv}（开{tp['duration']}），画质要{res}，时延控制在{rtt}以内，帮我开个保障。"
        return f"你好，今天{start_t}到{end_t}要在{app}开{srv}（开{tp['duration']}），画质要{res}，时延控制在{rtt}以内，帮我开个保障。"
    elif turn_idx == 1:
        if role == "reinforcement_session" and decl_mode == "implicit_induction" and s_plan.get("session_id", "").endswith("-03"):
            return f"今天在{env}，做{srv}，这次按上次的来。"
        elif role == "evidence_session":
            return f"你好，需要给{app}{srv}做一个网络保障，时间是今天{tp['start_timestamp'].split('日')[-1]}开始。"
        elif role in ["reinforcement_session", "reuse_session"]:
            challenge_type = s_plan.get("retrieval_challenge_type")
            if challenge_type == "negation_contrast" and s_plan.get("contrast_negated_app"):
                neg_a = s_plan.get("contrast_negated_app")
                neg_s = s_plan.get("contrast_negated_service") or "开直播"
                return f"今天不用{neg_a}做{neg_s}了，现在在{env}，老规矩改用{app}做{srv}，帮我把保障开上。"
            if challenge_type == "paraphrased_alias_scene":
                para_env = _paraphrase_env(env)
                para_period = _paraphrase_period(period_type)
                if trig_type == "time_periodic":
                    return f"老规矩，{para_period}，在{para_env}用{app}做{srv}，帮我把保障开上。"
                return f"老规矩，在{para_env}，用{app}做{srv}，帮我把保障开上。"
            if challenge_type == "implicit_service_collocation":
                imp_srv = _implicit_service_phrase(srv)
                if s_plan.get("agility_factor") == 1.0 and trig_type == "time_periodic":
                    time_prompt = "每天例行这个时候" if period_type == "daily" else ("每月例会这个时候" if period_type == "monthly" else "每周例行这个时候")
                    return f"老规矩，{time_prompt}，用{app}{imp_srv}，帮我把保障开上，别掉链子。"
                return f"老规矩，在{env}，用{app}{imp_srv}，帮我把保障开上。"
            if s_plan.get("agility_factor") == 1.0:
                if trig_type == "time_periodic":
                    time_prompt = "每天例行这个时候" if period_type == "daily" else ("每月例会这个时候" if period_type == "monthly" else "每周例行这个时候")
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
                p_text = "每天例行" if period_type == "daily" else ("每月例会" if period_type == "monthly" else "每周例行")
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

