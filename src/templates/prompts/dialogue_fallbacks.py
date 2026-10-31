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
        ("奥林匹克", "奥体中心多功能馆"),
        ("奥体中心", "奥体中心多功能馆"),
        ("会展中心", "国际会展中心"),
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
        ("酒店", "驻地酒店商务中心"),
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

    if len(env) > 14 or any(kw in env for kw in ["当", "进入", "触发", "身处", "。"]):
        return "外勤保障现场"
    return env.strip("，, 。. ")

def _paraphrase_env(env: str) -> str:
    if "大巴" in env or "转场" in env:
        return "坐大巴车转场的路上"
    if "驻地" in env or "酒店" in env:
        return "外勤驻地酒店这边商务中心"
    if "现场" in env:
        return env.replace("现场", "活动这边现场")
    return f"{env}这边"


def _paraphrase_period(period_type: str) -> str:
    if period_type == "daily":
        return "按咱们中午那个例行档期"
    if period_type == "monthly":
        return "按咱们每月那个固定例会档期"
    return "按咱们每周那个固定例行档期"


def _implicit_service_phrase(srv: str) -> str:
    if any(k in srv for k in ("开直播", "转播", "带货", "推流")):
        return "上麦开播推流"
    if "看直播" in srv:
        return "蹲直播间看直播"
    if any(k in srv for k in ("会议", "开会", "视讯")):
        return "搞个线上投屏远程碰头会"
    if any(k in srv for k in ("游戏", "排位", "手游", "开黑")):
        return "上号打把排位赛"
    if "通话" in srv:
        return "连线打个视频通话"
    if "短视频" in srv:
        return "刷会儿短视频"
    return f"开启{srv}"


def _dur_cn_labels(mins: int) -> tuple[str, str]:
    mapping = {
        30: ("半小时", "半小时"),
        60: ("1个小时", "1小时"),
        90: ("1个半小时", "1.5小时"),
        120: ("2个小时", "2小时"),
        150: ("2个半小时", "2.5小时"),
        180: ("3个小时", "3小时"),
    }
    return mapping.get(mins, (f"{mins}分钟", f"{mins}分钟"))


def _formal_and_temp_dur_info(tp: dict) -> dict:
    formal_dur = str(tp.get("duration") or "120min")
    m_dur = re.search(r"(\d+)", formal_dur)
    formal_min = int(m_dur.group(1)) if m_dur else 120
    temp_min = 30 if formal_min <= 60 else 60
    temp_dur = f"{temp_min}min"
    formal_spoken, formal_short = _dur_cn_labels(formal_min)
    temp_spoken, temp_short = _dur_cn_labels(temp_min)
    sh_t = str(tp.get("start_timestamp") or "").split("日")[-1] or "14时00分"
    m_hm = re.search(r"(\d{1,2})时(\d{1,2})分", sh_t)
    if m_hm:
        tot = (int(m_hm.group(1)) * 60 + int(m_hm.group(2)) + temp_min) % (24 * 60)
        temp_end_t = f"{tot // 60:02d}时{tot % 60:02d}分"
    else:
        temp_end_t = "15时00分"
    return {
        "formal_dur": formal_dur,
        "formal_spoken": formal_spoken,
        "formal_short": formal_short,
        "temp_dur": temp_dur,
        "temp_spoken": temp_spoken,
        "temp_short": temp_short,
        "temp_end_t": temp_end_t,
    }


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
            sh_t = (s_plan.get("nominal_start") or tp.get("start_timestamp", "")).split("日")[-1] or "15时00分"
            eh_t = (s_plan.get("nominal_end") or tp.get("end_timestamp", "")).split("日")[-1] or "17时00分"
            if turn_idx == 1:
                return f"收到，已为您准备好下周一（10月5日）{sh_t}至{eh_t}的例行周会意图保障单（{res} / 时延≤{rtt}），确认按此时段预约吗？"
            elif turn_idx == 2 and not is_last:
                return f"明白！10月5日确实处于国庆法定假期。已为您将例行周会意图保障单顺延调整至节后首个工作日（10月8日）{sh_t}至{eh_t}（{res} / 时延≤{rtt}），确认按此顺延方案预约吗？"
            else:
                return f"好的，已为您将本次例行周会意图保障单顺延调整至国庆节后首个工作日（10月8日）同时段办理（{res} / 时延≤{rtt}），并记下这条节假日避让顺延经验，祝您假期愉快！"
        elif exp_id == "EXP_MULTI_INTENT_PARTITION_01":
            sh_t = tp.get("start_timestamp", "").split("日")[-1] or "12时30分"
            new_eh_t = tp.get("end_timestamp", "").split("日")[-1] or "14时30分"
            dur_val = tp.get("duration", "120min")
            if turn_idx == 1:
                return f"收到，已为您准备好{sh_t}至{new_eh_t}（持续{dur_val}）的【抖音-开直播】意图保障单（{res} / 时延≤{rtt}），确认直接为您开通吗？"
            elif turn_idx == 2 and not is_last:
                return f"明白！原来私下跟搭档对直播词、看镜头机位平时都是用【微信-视频通话】沟通。已为您将意图保障单修正为【微信-视频通话】（{sh_t}至{new_eh_t}，持续{dur_val}，{res} / 时延≤{rtt}），确认按修改后的配置开通吗？"
            else:
                return f"好的，已为您成功开通【微信-视频通话】意图保障单（{sh_t}至{new_eh_t}，持续{dur_val}，{res} / 时延≤{rtt}），并记下这条日常对词试机位经验，祝您对词顺利！"
        elif exp_id == "EXP_PREWARM_BUFFER_01":
            nom_sh_t = (s_plan.get("nominal_start") or tp.get("start_timestamp", "")).split("日")[-1]
            pw_sh_t = tp["start_timestamp"].split("日")[-1]
            eh_t = tp["end_timestamp"].split("日")[-1]
            if turn_idx == 1:
                return f"收到，已为您准备好{nom_sh_t}至{eh_t}的现场意图保障单配置（{res} / 时延≤{rtt}），确认直接开通吗？"
            elif turn_idx == 2 and not is_last:
                return f"明白！大型场馆重大活动现场设备调试确实需要预留试机时间。已为您将意图保障单起保时间提前30分钟调整为{pw_sh_t}至{eh_t}（总时长扩充至{tp['duration']}，{res} / 时延≤{rtt}），确认按调整后的预热方案开通吗？"
            else:
                return f"好的，已按提前30分钟预热方案为您开通{app}{srv}意图保障单（{pw_sh_t}至{eh_t}，持续{tp['duration']}，{res} / 时延≤{rtt}），并记下这条大型活动提前预热试机的日常经验，祝现场活动顺利！"
        elif exp_id == "EXP_ORDER_QUALITY_DISAMBIGUATION_01":
            sh_t = tp['start_timestamp'].split('日')[-1]
            eh_t = tp['end_timestamp'].split('日')[-1]
            d_info = _formal_and_temp_dur_info(tp)
            if turn_idx == 1:
                return f"收到，已按您最近一笔（前天）的记录，为您准备好{sh_t}至{d_info['temp_end_t']}（持续{d_info['temp_dur']}）的{app}{srv}意图保障单（{res} / 时延≤{rtt}），确认按此开通吗？"
            elif turn_idx == 2 and not is_last:
                return f"明白！已为您过滤前天的{d_info['temp_short']}临时短单，改按上周正式客户路演单为您排满{d_info['formal_short']}（{sh_t}至{eh_t}，持续{d_info['formal_dur']}，{res} / 时延≤{rtt}），确认按此正式规格开通吗？"
            else:
                return f"好的，已按上周正式客户路演单规格为您排满{d_info['formal_short']}（{sh_t}至{eh_t}，持续{d_info['formal_dur']}，{res} / 时延≤{rtt}），并记下这条经验，祝您路演顺畅！"
        elif exp_id == "EXP_OVERLAPPING_ORDER_RESOLUTION_01":
            sh_t = tp.get("start_timestamp", "").split("日")[-1] or "15时00分"
            eh_t = tp.get("end_timestamp", "").split("日")[-1] or "17时00分"
            dur_val = tp.get("duration", "120min")
            if turn_idx == 1:
                return f"收到，已为您准备好{sh_t}至{eh_t}（持续{dur_val}）的【抖音-看直播】意图保障单（{res} / 时延≤{rtt}），确认按此直接开通吗？"
            elif turn_idx == 2 and not is_last:
                return f"明白！进他人直播间当连麦嘉宾需要上麦发言推流，确实应当按【开直播】保障上行。已为您修正为【抖音-开直播】意图保障单（{sh_t}至{eh_t}，持续{dur_val}，{res} / 时延≤{rtt}），确认按修改后的配置开通吗？"
            else:
                return f"好的，已为您成功开通【抖音-开直播】意图保障单（{sh_t}至{eh_t}，持续{dur_val}，{res} / 时延≤{rtt}），并记下这条日常经验，祝您连麦互动顺利！"
        else:
            if turn_idx == 1:
                return f"收到，已为您配置好意图保障单方案（{res} / 时延≤{rtt}），确认直接开通吗？"
            elif turn_idx == 2 and not is_last:
                return f"明白，已按您的要求更新意图保障单配置（{res} / 时延≤{rtt}），确认按修改后的方案开通吗？"
            else:
                return f"好的，已为您成功受理本次意图保障单（{res} / 时延≤{rtt}），祝您工作顺利！"
    elif s_plan.get("experience_citation", {}).get("experience_id") == "EXP_CALENDAR_HOLIDAY_EXCEPTION_01":
        learn_sid = s_plan.get("learning_source_session")
        learn_prefix = f"参考此前在 {learn_sid} 的处理做法，" if learn_sid else "参考此前的处理经验，"
        if turn_idx == 1:
            return f"收到，识别到下周一（10月5日）恰逢国庆节法定长假，办公区全员放假。{learn_prefix}已主动为您将例行周会意图保障单顺延至节后首个工作日（10月8日）同时段办理，避免放假期间在空办公室空跑产生费用，确认按此顺延办理吗？"
        else:
            return f"好的，已为您将例行周会意图保障单顺延至10月8日办理（{res} / 时延≤{rtt}），祝您假期愉快！"
    elif tid == "T2-4" or s_plan.get("experience_citation", {}).get("experience_id") == "EXP_MULTI_INTENT_PARTITION_01":
        learn_sid = s_plan.get("learning_source_session")
        learn_prefix = f"参考此前在 {learn_sid} 的日常对词试机位经验，" if learn_sid else "参考此前的日常对词试机位经验，"
        tp = s_plan.get("target_params", {})
        sh_t = tp.get("start_timestamp", "").split("日")[-1] or "12时30分"
        new_eh_t = tp.get("end_timestamp", "").split("日")[-1] or "14时30分"
        dur_val = tp.get("duration", "120min")
        if turn_idx == 1:
            return f"识别到您是在正式开播前先跟搭档私下对直播词和看镜头机位，还未正式公开开播。{learn_prefix}私下对词试机位平时都是用微信视频连线，已主动为您匹配【微信-视频通话】意图保障单（{sh_t}至{new_eh_t}，持续{dur_val}，{res} / 时延≤{rtt}），确认按此开通吗？"
        else:
            return f"好的，已为您成功开通【微信-视频通话】意图保障单（{sh_t}至{new_eh_t}，持续{dur_val}，{res} / 时延≤{rtt}），祝您和搭档对词试机位顺利！"
    elif tid == "T2-9" or s_plan.get("experience_citation", {}).get("experience_id") == "EXP_PREWARM_BUFFER_01":
        pw_start_t = tp['start_timestamp'].split('日')[-1]
        end_t = tp['end_timestamp'].split('日')[-1]
        learn_sid = s_plan.get("learning_source_session")
        learn_prefix = f"参考此前在 {learn_sid} 的处理做法，" if learn_sid else "参考此前的处理经验，"
        if s_plan.get("is_counterexample"):
            if turn_idx == 1:
                return f"收到，{env}现场人比较多，一般建议优先保流畅；不过既然您明确需要原画采录，已按您的要求保持{res}画质、时延{rtt}以内，确认直接开通意图保障单吗？"
            else:
                return f"好的，已按原画要求为您开通{app}{srv}意图保障单（{res} / 时延≤{rtt}），祝您录制顺利！"
        elif s_plan.get("round_count") == 3:
            if turn_idx == 1:
                return f"收到，{env}现场属于大型场馆重大活动，建议将意图保障单起保时间提前30分钟推算为{pw_start_t}至{end_t}进行试机预热。您看这样合适吗？"
            elif turn_idx == 2:
                return f"预留30分钟试机能够确保开场推流平稳流畅，画质{res}、时延稳定在{rtt}。确认按这个开通意图保障单吗？"
            else:
                return f"好的，已为您开通{app}{srv}意图保障单（{pw_start_t}至{end_t}，{res} / 时延≤{rtt}），祝您现场活动顺利！"
        else:
            if turn_idx == 1:
                return f"收到！大型场馆重大活动现场设备调试与连线建议提前预热试机。{learn_prefix}为您将意图保障单起保时间自动提前30分钟推算为{pw_start_t}至{end_t}（保障时长扩充至{tp['duration']}，{res} / 时延≤{rtt}），确认直接开通吗？"
            else:
                return f"好的，已为您成功受理{app}{srv}意图保障单（{pw_start_t}至{end_t}，持续{tp['duration']}，{res} / 时延≤{rtt}），预留30分钟预热试机，祝现场顺利！"
    elif s_plan.get("experience_citation", {}).get("experience_id") == "EXP_ORDER_QUALITY_DISAMBIGUATION_01":
        start_t = tp['start_timestamp'].split('日')[-1]
        end_t = tp['end_timestamp'].split('日')[-1]
        d_info = _formal_and_temp_dur_info(tp)
        learn_sid = s_plan.get("learning_source_session")
        learn_prefix = f"参考此前在 {learn_sid} 的历史单据时长优选经验，" if learn_sid else "参考此前的历史单据时长优选经验，"
        if turn_idx == 1:
            return f"检索到您历史账本中有两笔记录（前天{d_info['temp_short']}临时短单{d_info['temp_dur']} vs 上周正式客户路演单{d_info['formal_dur']}）。{learn_prefix}识别到您今天是办正式客户远程路演，已自动为您过滤前天那笔{d_info['temp_short']}临时短单，按上周正式路演单为您排满{d_info['formal_short']}（{start_t}至{end_t}，持续{tp['duration']}，{res} / 时延≤{rtt}），确认直接开通吗？"
        else:
            return f"好的，已按上周{d_info['formal_short']}正式路演单时长（{start_t}至{end_t}，持续{tp['duration']}，{res} / 时延≤{rtt}）为您成功受理{app}{srv}意图保障单，祝您路演顺畅！"
    elif tid == "T2-10" or s_plan.get("experience_citation", {}).get("experience_id") == "EXP_OVERLAPPING_ORDER_RESOLUTION_01":
        start_t = tp['start_timestamp'].split('日')[-1]
        end_t = tp['end_timestamp'].split('日')[-1]
        learn_sid = s_plan.get("learning_source_session")
        learn_prefix = f"参考此前在 {learn_sid} 的连麦嘉宾业务选择经验，" if learn_sid else "参考此前的连麦嘉宾业务选择经验，"
        if turn_idx == 1:
            return f"识别到您是受邀进主会场抖音直播间当连麦嘉宾互动，需要开摄像头上麦发言推流，不能按普通观众【看直播】受理。{learn_prefix}已主动为您匹配【抖音-开直播】意图保障单（{start_t}至{end_t}，持续{tp['duration']}，{res} / 时延≤{rtt}），确认按此开通吗？"
        else:
            return f"好的，已为您成功开通【抖音-开直播】意图保障单（{start_t}至{end_t}，持续{tp['duration']}，{res} / 时延≤{rtt}），祝您连麦互动圆满顺利！"
    elif tid == "T2-5":
        start_t = tp['start_timestamp'].split('日')[-1]
        end_t = tp['end_timestamp'].split('日')[-1]
        if turn_idx == 1:
            return f"收到，我调取到之前登记的{app}{srv}配置：画质{res}、时延{rtt}以内，从{start_t}开始保障，确认按这套配置开通吗？"
        elif turn_idx == 2 and not is_last:
            return f"收到，已为您将{app}{srv}保障时长延长至{tp['duration']}（时段更新为{start_t}至{end_t}，画质保持{res}、时延≤{rtt}），确认按延长后的配置开通吗？"
        else:
            return f"好的，已按老规矩为您开通{app}{srv}保障：画质保持{res}、时延上限{rtt}，时长已延长至{tp['duration']}（{start_t}至{end_t}）。祝您活动顺利！"
    elif tid == "T2-6":
        start_t = tp['start_timestamp'].split('日')[-1]
        end_t = tp['end_timestamp'].split('日')[-1]
        is_disambig = s_plan.get("is_disambiguation", False)
        if is_disambig:
            cand_ids = s_plan.get("working_memory_pointer", {}).get("candidate_record_ids", [])
            cand_str = "、".join(cand_ids) if cand_ids else "意图保障单A和意图保障单B"
            if turn_idx == 1:
                return f"收到，查询到您此前在{env}有多次{app}{srv}历史意图保障单（包括 {cand_str}），配置规格略有差异。请问您今天是指按哪一次的规格来开通呢？"
            elif turn_idx == 2:
                return f"明白，已精准锁定最近一次意图保障单规格（{res} / 时延≤{rtt}），时段为{start_t}至{end_t}，确认直接开通吗？"
            else:
                return f"好的，已按您确认的历史意图保障单规格成功开通今日{app}{srv}保障（{res} / 时延≤{rtt}，时段{start_t}至{end_t}）。祝您工作顺利！"
        elif s_plan.get("working_memory_pointer", {}).get("inferred_delta_days", 7) >= 25:
            if turn_idx == 1:
                return f"收到，已为您跨期调取到上个月在{env}的{app}{srv}历史意图保障单（画质{res}、时延≤{rtt}）。请问今天具体的保障时间是几点到几点呢？"
            elif turn_idx == 2 and not is_last:
                return f"收到，已为您锁定今日{start_t}至{end_t}（持续{tp['duration']}）的{app}{srv}保障（继承上月历史意图保障单规格：画质{res}、时延≤{rtt}），确认按此配置开通吗？"
            else:
                return f"好的，已按一个月前历史意图保障单规格为您开通今日{app}{srv}保障（{res} / 时延≤{rtt}，时段{start_t}至{end_t}）。祝您工作顺利！"
        else:
            if turn_idx == 1:
                return f"收到，已为您在历史意图保障单账本中找到上周在{env}的{app}{srv}意图保障单（画质{res}、时延≤{rtt}）。请问今天具体的保障时间是几点到几点呢？"
            elif turn_idx == 2 and not is_last:
                return f"收到，已为您锁定今日{start_t}至{end_t}（持续{tp['duration']}）的{app}{srv}保障（继承上周历史意图保障单规格：画质{res}、时延≤{rtt}），确认按此配置开通吗？"
            else:
                return f"好的，已按您引用的历史意图保障单规格为您成功开通今日{app}{srv}保障（{res} / 时延≤{rtt}，时段{start_t}至{end_t}）。祝您工作顺利！"
    elif tid == "T2-7":
        start_t = tp['start_timestamp'].split('日')[-1]
        end_t = tp['end_timestamp'].split('日')[-1]
        is_advance = s_plan.get("working_memory_pointer", {}).get("reschedule_direction") == "advance"
        if is_advance:
            if turn_idx == 1:
                return f"收到，已找到您此前预约的{app}{srv}意图保障单。提前一小时后，新的保障时段为{start_t}至{end_t}，确认进行提前改期吗？"
            else:
                return f"好的，已为您成功办理意图保障单提前生效变更，保障时段已更新为{start_t}至{end_t}生效。祝您使用顺利！"
        else:
            if turn_idx == 1:
                return f"收到，已找到您此前预约的{app}{srv}意图保障单。往后推迟一小时后，新的保障时段为{start_t}至{end_t}，确认进行改期吗？"
            else:
                return f"好的，已为您成功办理意图保障单延期变更，保障时段已更新为{start_t}至{end_t}生效。祝您使用顺利！"
    elif tid == "T2-8":
        query_info = s_plan.get("working_memory_query", {})
        total_orders = query_info.get("total_orders", 3)
        total_mins = query_info.get("total_duration_minutes", 300)
        scope = query_info.get("reconcile_scope", "")
        if "全月" in scope:
            return f"已为您生成全月历史意图保障单总对账报表：本月您累计成功办理了 {total_orders} 次移动网络保障，累计保障总时长达 {total_mins} 分钟，涵盖各类重点场景，所有意图保障单全部履约闭环。"
        return f"已为您查询到本周历史意图保障单流水账：本周您共成功办理了 {total_orders} 次移动网络保障，累计保障时长达 {total_mins} 分钟，涵盖{app}{srv}等场景，所有意图保障单均已按期履约。"
    elif tid == "T2-3":
        start_t = tp['start_timestamp'].split('日')[-1]
        end_t = tp['end_timestamp'].split('日')[-1]
        base_res = s_plan.get("base_resolution") or "1080p"
        base_rtt = s_plan.get("base_rtt") or "50ms"
        if turn_idx == 1:
            return f"收到，我调取到之前登记的{app}{srv}配置：画质{base_res}、时延{base_rtt}以内，{start_t}至{end_t}（持续{tp['duration']}），确认按这套配置开通吗？"
        elif turn_idx == 2 and not is_last:
            return f"明白，已针对今日现场特殊情况为您临时调整{app}{srv}保障参数：画质{res}、时延{rtt}以内，时段{start_t}至{end_t}（持续{tp['duration']}），确认按此临时配置开通吗？"
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
            return ["Create_Intent_Request", "Inform_Slot"], ["Confirm_Slot"]
        elif turn_idx == 2 and not is_last:
            return ["Correct_Previous_Input", "Modify_Request"], ["Confirm_Slot"]
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
        elif turn_idx == 2 and not is_last:
            return ["Confirm_Slot", "Modify_Request"], ["Confirm_Slot"]
        else:
            return ["Confirm_Slot"], ["Acknowledge"]
    elif tid == "T2-6":
        is_disambig = s_plan.get("is_disambiguation", False)
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
            elif turn_idx == 2 and not is_last:
                return ["Inform_Slot"], ["Confirm_Slot"]
            else:
                return ["Confirm_Slot"], ["Acknowledge"]
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
        elif turn_idx == 2 and not is_last:
            return ["Correct_Previous_Input", "Inform_Slot"], ["Confirm_Slot"]
        else:
            return ["Confirm_Slot"], ["Acknowledge"]
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
