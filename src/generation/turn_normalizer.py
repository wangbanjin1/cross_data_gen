"""单轮对话台词与动作后处理规范化器 (Turn Utterance & Action Normalizer)."""

from __future__ import annotations

import re
from src.templates.prompts import (
    get_fallback_agent_utterance,
    get_fallback_user_utterance,
    get_normalized_action_types,
)


def normalize_dialogue_turn(t_data: dict, turn_idx: int, role: str, is_last: bool, s_plan: dict) -> tuple[str, list[str], str, list[str]]:
    u_text = ""
    if isinstance(t_data, dict):
        u_text = (
            t_data.get("user_utterance")
            or t_data.get("user_query")
            or t_data.get("user_input")
            or (t_data.get("user", {}).get("utterance") if isinstance(t_data.get("user"), dict) else t_data.get("user"))
            or ""
        )
    if not u_text:
        u_text = get_fallback_user_utterance(s_plan, turn_idx, role)

    if turn_idx == 1 and role == "evidence_session":
        for kw in ["老规矩，", "老规矩、", "老规矩 ", "老规矩", "老时间，", "老时间、", "老时间 ", "老时间", "老样子，", "老样子、", "老样子 "]:
            u_text = u_text.replace(kw, "")
        u_text = u_text.strip("，, ")

    tp = s_plan.get("target_params", {})
    tid = s_plan.get("template_id", "T2-1")

    # 纯域外拒绝不能接受 LLM 渲染出的域内“老规矩”对话。
    if tid == "T1-2":
        u_text = get_fallback_user_utterance(s_plan, turn_idx, role)

    # 单轮干扰任务：必须清晰说全参数，严禁携带任何个性化表达/模糊词
    if tid == "T1-1" or s_plan.get("blueprint_type") == "distractor":
        if s_plan.get("retrieval_challenge_type") == "negation_contrast":
            neg_app = s_plan.get("contrast_negated_app") or ""
            if not (neg_app and neg_app in u_text and "不" in u_text):
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
        bad_dist_kws = ["清晰点就行", "不卡就行", "一会儿", "老规矩", "老时间", "照旧", "按习惯"]
        if any(kw in u_text for kw in bad_dist_kws) or tp.get("resolution", "") not in u_text or tp.get("rtt", "") not in u_text:
            u_text = get_fallback_user_utterance(s_plan, turn_idx, role)

    # 临时纠正覆盖：第1轮必须满足场景+应用+业务的最小表达，第2轮必须包含特殊现场与调整参数
    if tid == "T2-3" or s_plan.get("blueprint_type") == "event_override":
        app = tp.get("application_name", "")
        srv = tp.get("service_name", "")
        env = s_plan.get("scenario_env", "")
        if turn_idx == 1:
            has_app = app in u_text or any(a in u_text for a in s_plan.get("aliases", {}).get("app_aliases", []))
            has_srv = srv in u_text or any(a in u_text for a in s_plan.get("aliases", {}).get("service_aliases", []))
            has_env = env in u_text or "现场" in u_text
            if not (has_app and has_srv and has_env):
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
        elif turn_idx == 2:
            if tp.get("resolution", "") not in u_text or tp.get("rtt", "") not in u_text or "特殊" not in u_text:
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)

    # 时长延长会话(T2-5)：第1轮必须满足场景+应用+业务的最小表达，第2轮必须包含时长延长
    if tid == "T2-5":
        app = tp.get("application_name", "")
        srv = tp.get("service_name", "")
        env = s_plan.get("scenario_env", "")
        if turn_idx == 1:
            has_app = app in u_text or any(a in u_text for a in s_plan.get("aliases", {}).get("app_aliases", []))
            has_srv = srv in u_text or any(a in u_text for a in s_plan.get("aliases", {}).get("service_aliases", []))
            has_env = env in u_text or any(k in u_text for k in ["现场", "营地", "训练场", "岸线", "途中", "休息区", "研讨会"])
            if not (has_app and has_srv and has_env):
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
        elif turn_idx == 2:
            if tp.get("duration", "") not in u_text and "延长" not in u_text and "时长" not in u_text:
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)

    # 经验记忆负反例边界：必须坚持原画质，严禁降画质
    if s_plan.get("is_counterexample"):
        if tp.get("resolution", "1080p") not in u_text:
            u_text = get_fallback_user_utterance(s_plan, turn_idx, role)

    # 证据会话首轮必须包含标准应用、业务与开始时间，且严禁泄漏画质/时延/时长。
    if turn_idx == 1 and role == "evidence_session":
        app_ok = tp.get("application_name", "") in u_text
        srv_ok = tp.get("service_name", "") in u_text
        start_hm = tp.get("start_timestamp", "").split("日")[-1]
        time_ok = start_hm in u_text or start_hm.replace("时", ":").replace("分", "") in u_text or start_hm.replace("时", "点") in u_text
        leaked = any(k and k in u_text for k in [tp.get("resolution", ""), tp.get("rtt", ""), tp.get("duration", ""), "俩小时", "两小时", "一个钟头", "一个半小时", "三个小时", "60分钟", "90分钟", "120分钟", "150分钟", "180分钟"])
        if not (app_ok and srv_ok and time_ok) or leaked:
            u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
    if turn_idx == 2 and role == "evidence_session" and tid == "T2-1":
        dur_aliases = s_plan.get("aliases", {}).get("duration_aliases", [])
        has_dur = tp.get("duration", "") in u_text or any(da in u_text for da in dur_aliases)
        if tp.get("resolution", "") not in u_text or tp.get("rtt", "") not in u_text or not has_dur:
            u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
    if tid in ["T2-2", "T3-1"] and s_plan.get("small_memory_evidence_mode") == "cross_turn_clarification":
        u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
    if turn_idx == 2 and role == "reinforcement_session" and s_plan.get("small_memory_evidence_mode") == "co_occurrence" and s_plan.get("session_id", "").endswith("-03"):
        u_text = get_fallback_user_utterance(s_plan, turn_idx, role)

    # 规范化画质别名（严禁使用与数值冲突的'顶格清晰度'等词）
    for bad_word in ["顶格清晰度", "顶格画质", "最高画质", "极限画质", "最高清晰度"]:
        if bad_word in u_text:
            u_text = u_text.replace(bad_word, "1080p原画" if tp.get("resolution") == "1080p" else tp.get("resolution", ""))

    # 规范化时延别名（严禁使用失真夸大的'零卡顿'等词）
    for bad_word in ["零卡顿", "秒开", "极速响应"]:
        if bad_word in u_text:
            u_text = u_text.replace(bad_word, f"{tp.get('rtt', '')}以内")

    # 常规复用/强化会话第 1 轮：物理隔离拦截 memory_filled 槽位 (resolution / rtt) 提前泄露
    if turn_idx == 1 and role in ["reinforcement_session", "reuse_session"] and tid not in ["T2-3", "T2-5", "T2-6", "T2-7", "T2-8", "T2-9", "T2-10"]:
        patterns_to_strip = [
            r'，?(?:顶格清晰度|1080p原画|1080p|720p|4K|4k|超清|高清)[、，]?(?:零卡顿|\d+ms以内|\d+毫秒以内|\d+ms)[、，]?(?:俩小时|两小时|\d+分钟|\d+min)?',
            r'[、，]?(?:顶格清晰度|1080p原画|1080p|720p|4K|4k|超清|高清)',
            r'[、，]?(?:零卡顿|\d+ms以内|\d+毫秒以内|\d+ms)',
        ]
        for pat in patterns_to_strip:
            u_text = re.sub(pat, '', u_text)
        u_text = re.sub(r'，\s*，', '，', u_text).strip("，, ")
        if tp.get("resolution", "") and tp["resolution"] in u_text:
            u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
        if tp.get("rtt", "") and tp["rtt"] in u_text:
            u_text = get_fallback_user_utterance(s_plan, turn_idx, role)

    # 拦截清理误将后台规划长句拼入台词的异常
    if any(bad_kw in u_text for bad_kw in ["当上午", "进入道路", "触发现场", "办事了，", "弱网空间时", "固定外勤时段"]):
        u_text = get_fallback_user_utterance(s_plan, turn_idx, role)

    # 清除任何残留的后台规则词（如“触发用”、“触发”）
    u_text = u_text.replace("触发用", "用").replace("触发", "")

    # 检查并清除未经声明的幻觉别名
    sm_val = s_plan.get("small_memory", {}).get("value")
    def _clean_hallucinated_alias(match):
        alias_word = match.group(1)
        if alias_word in ["每天这个时候", "老规矩", "月初老规矩", "大半个下午"]:
            return match.group(0)
        if sm_val and alias_word == sm_val:
            return match.group(0)
        return ""

    u_text = re.sub(r'[，、]?(?:画质|时延|时长)?按[‘“\'\"]([^’度”\'\"]+)[’度”\'\"](?:来|开|算|处理)?', _clean_hallucinated_alias, u_text)
    u_text = re.sub(r'，\s*，', '，', u_text).strip("，, ")

    a_text = ""
    if isinstance(t_data, dict):
        a_text = (
            t_data.get("agent_utterance")
            or t_data.get("agent_response")
            or t_data.get("agent_reply")
            or t_data.get("assistant_utterance")
            or t_data.get("response")
            or (t_data.get("agent", {}).get("utterance") if isinstance(t_data.get("agent"), dict) else t_data.get("agent"))
            or ""
        )
    if not a_text:
        a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
    if tid == "T1-2":
        a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
    if tid == "T1-1" or s_plan.get("blueprint_type") == "distractor":
        if any(kw in a_text for kw in ["记忆理解", "理解为", "按‘", "按\""]):
            a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
    if tid in ["T2-2", "T3-1"] and s_plan.get("small_memory_evidence_mode") == "cross_turn_clarification":
        a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
    if tid == "T2-5" and turn_idx == 1:
        dur_str = tp.get("duration", "")
        dur_m = re.search(r'(\d+)\s*(?:min|分钟)', dur_str)
        if dur_m:
            num = dur_m.group(1)
            if f"{num}min" in a_text or f"{num}分钟" in a_text:
                a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
    elif tid == "T2-5" and turn_idx == 2 and not is_last:
        if "确认" not in a_text or "吗" not in a_text or tp.get("duration", "") not in a_text:
            a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
    elif tid == "T2-5" and turn_idx == 3:
        if any(k in u_text for k in ["延长", "min", "分钟", "小时"]) or not any(k in u_text for k in ["确认", "好", "对", "行", "可以"]):
            u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
    if (tid == "T2-3" or s_plan.get("blueprint_type") == "event_override") and turn_idx == 2 and not is_last:
        if "确认" not in a_text or "吗" not in a_text or tp.get("resolution", "") not in a_text or tp.get("rtt", "") not in a_text:
            a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
    elif (tid == "T2-3" or s_plan.get("blueprint_type") == "event_override") and turn_idx == 3:
        if any(k in u_text for k in ["特殊", "720p", "30ms", "临时调"]) or not any(k in u_text for k in ["确认", "好", "对", "行", "可以"]):
            u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
    if turn_idx == 2 and role == "reinforcement_session" and s_plan.get("small_memory_evidence_mode") == "co_occurrence" and s_plan.get("session_id", "").endswith("-03"):
        a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
    if s_plan.get("is_counterexample"):
        if "降" in a_text or ("原画" not in a_text and "1080p" not in a_text):
            a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
    if s_plan.get("is_disambiguation"):
        if turn_idx == 1:
            sh_t = tp.get("start_timestamp", "").split("日")[-1]
            eh_t = tp.get("end_timestamp", "").split("日")[-1]
            if sh_t not in u_text or eh_t not in u_text or tp.get("resolution", "") in u_text or tp.get("rtt", "") in u_text:
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
            if "哪" not in a_text and "意图保障单" not in a_text and "记录" not in a_text:
                a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
        elif turn_idx == 2:
            if "最近" not in u_text and "上次" not in u_text:
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
            if tp.get("resolution", "") not in a_text or tp.get("rtt", "") not in a_text:
                a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
        elif turn_idx == 3:
            if any(kw in u_text for kw in ["画面", "画质", "透亮", "清晰", "流畅", "时延", "延迟"]):
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
    elif tid == "T2-6" and not s_plan.get("experience_citation"):
        sh_t = tp.get("start_timestamp", "").split("日")[-1]
        eh_t = tp.get("end_timestamp", "").split("日")[-1]
        if turn_idx == 1:
            if tp.get("resolution", "") not in a_text or tp.get("rtt", "") not in a_text:
                a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
        elif turn_idx == 2:
            if sh_t not in u_text or eh_t not in u_text or tp.get("duration", "") not in u_text:
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
            if not is_last and ("确认" not in a_text or "吗" not in a_text):
                a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
        elif turn_idx == 3:
            if any(k in u_text for k in [sh_t, eh_t, "min", "分钟"]) or not any(k in u_text for k in ["确认", "好", "对", "行", "可以"]):
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
    elif tid == "T2-7":
        sh_t = tp.get("start_timestamp", "").split("日")[-1]
        eh_t = tp.get("end_timestamp", "").split("日")[-1]
        is_adv = s_plan.get("working_memory_pointer", {}).get("reschedule_direction") == "advance"
        if turn_idx == 1:
            if (is_adv and "提前" not in u_text) or (not is_adv and "推迟" not in u_text):
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
            if sh_t not in a_text or eh_t not in a_text:
                a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
    if turn_idx == 1 and role in ["reinforcement_session", "reuse_session"] and tid not in ["T2-3", "T2-5", "T2-6", "T2-7", "T2-8", "T2-9", "T2-10", "T2-4"] and not s_plan.get("experience_citation"):
        is_imp_s03 = (role == "reinforcement_session" and s_plan.get("declaration_mode") == "implicit_induction" and s_plan.get("session_id", "").endswith("-03"))
        challenge_type = s_plan.get("retrieval_challenge_type")
        if is_imp_s03:
            if tp.get("service_name", "") not in u_text or tp.get("application_name", "") in u_text:
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
        elif challenge_type == "negation_contrast":
            neg_app = s_plan.get("contrast_negated_app") or ""
            if not (neg_app and neg_app in u_text and "不" in u_text and tp.get("application_name", "") in u_text):
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
        elif challenge_type in ("paraphrased_alias_scene", "implicit_service_collocation"):
            u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
        else:
            sm_val = s_plan.get("small_memory", {}).get("value") or ""
            if sm_val and sm_val not in u_text and tp.get("application_name", "") not in u_text:
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
        if tp.get("resolution", "") not in a_text or tp.get("rtt", "") not in a_text:
            a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
        for bad_word in ["零卡顿", "秒开", "极速响应"]:
            if bad_word in u_text:
                u_text = u_text.replace(bad_word, f"{tp.get('rtt', '')}以内")
        for bad_word in ["顶格清晰度", "顶格画质", "最高画质", "极限画质", "最高清晰度"]:
            if bad_word in u_text:
                u_text = u_text.replace(bad_word, "1080p原画" if tp.get("resolution") == "1080p" else tp.get("resolution", ""))

    # 经验记忆全系场景（含学习铺垫轮与迁移测试轮）：严格采用高保真标准化 Fallback，确保 Turn 1 基础参数自包含且与双轨分支评测 Ground Truth 100% 严密对齐
    exp_id = s_plan.get("experience_id") or s_plan.get("experience_citation", {}).get("experience_id")
    if (
        tid in ["T2-4", "T2-9", "T2-10"]
        or s_plan.get("memory_tier") == "experiential_memory"
        or s_plan.get("blueprint_type") == "experience_learning"
        or bool(exp_id)
    ):
        u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
        a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)

    # 同样规范化客服台词中的画质与时延
    for bad_word in ["顶格清晰度", "顶格画质", "最高画质", "极限画质", "最高清晰度"]:
        if bad_word in a_text:
            a_text = a_text.replace(bad_word, "1080p原画" if tp.get("resolution") == "1080p" else tp.get("resolution", ""))
    for bad_word in ["零卡顿", "秒开", "极速响应"]:
        if bad_word in a_text:
            a_text = a_text.replace(bad_word, f"{tp.get('rtt', '')}以内")

    # 拦截当天生效会话中错误出现的“明天/后天”口语词，防止与真实标注日期产生矛盾
    ref_day = s_plan.get("reference_time", "").split("日")[0]
    start_day = tp.get("start_timestamp", "").split("日")[0]
    if ref_day and start_day and ref_day == start_day:
        for w in ["明天", "后天"]:
            if w in u_text:
                u_text = u_text.replace(w, "今天")
            if w in a_text:
                a_text = a_text.replace(w, "今天")

    raw_u_acts = t_data.get("user_action_types") if isinstance(t_data, dict) else None
    raw_a_acts = t_data.get("agent_action_types") if isinstance(t_data, dict) else None
    u_acts, a_acts = get_normalized_action_types(s_plan, turn_idx, role, is_last, raw_u_acts, raw_a_acts)

    return u_text, u_acts, a_text, a_acts
