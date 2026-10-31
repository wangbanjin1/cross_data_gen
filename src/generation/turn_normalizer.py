"""单轮对话台词与动作后处理规范化器 (Turn Utterance & Action Normalizer)."""

from __future__ import annotations

import re
from src.templates.prompts import (
    get_fallback_agent_utterance,
    get_fallback_user_utterance,
    get_normalized_action_types,
)


def _extract_raw_utterances(t_data: dict, turn_idx: int, role: str, is_last: bool, s_plan: dict) -> tuple[str, str]:
    u_text = ""
    a_text = ""
    if isinstance(t_data, dict):
        u_text = (
            t_data.get("user_utterance")
            or t_data.get("user_query")
            or t_data.get("user_input")
            or (t_data.get("user", {}).get("utterance") if isinstance(t_data.get("user"), dict) else t_data.get("user"))
            or ""
        )
        a_text = (
            t_data.get("agent_utterance")
            or t_data.get("agent_response")
            or t_data.get("agent_reply")
            or t_data.get("assistant_utterance")
            or t_data.get("response")
            or (t_data.get("agent", {}).get("utterance") if isinstance(t_data.get("agent"), dict) else t_data.get("agent"))
            or ""
        )
    if not u_text:
        u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
    if not a_text:
        a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
    return u_text, a_text


def _normalize_user_template_constraints(u_text: str, turn_idx: int, role: str, s_plan: dict) -> str:
    if turn_idx == 1 and role == "evidence_session":
        for kw in ["老规矩，", "老规矩、", "老规矩 ", "老规矩", "老时间，", "老时间、", "老时间 ", "老时间", "老样子，", "老样子、", "老样子 "]:
            u_text = u_text.replace(kw, "")
        u_text = u_text.strip("，, ")

    tp = s_plan.get("target_params", {})
    tid = s_plan.get("template_id", "T2-1")
    if tid == "T1-2":
        return get_fallback_user_utterance(s_plan, turn_idx, role)

    if tid == "T1-1" or s_plan.get("blueprint_type") == "distractor":
        if s_plan.get("retrieval_challenge_type") == "negation_contrast":
            neg_app = s_plan.get("contrast_negated_app") or ""
            if not (neg_app and neg_app in u_text and "不" in u_text):
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
        bad_dist_kws = ["清晰点就行", "不卡就行", "一会儿", "老规矩", "老时间", "照旧", "按习惯"]
        if any(kw in u_text for kw in bad_dist_kws) or tp.get("resolution", "") not in u_text or tp.get("rtt", "") not in u_text:
            u_text = get_fallback_user_utterance(s_plan, turn_idx, role)

    if tid in ["T2-3", "T2-5"] or s_plan.get("blueprint_type") == "event_override":
        app, srv, env = tp.get("application_name", ""), tp.get("service_name", ""), s_plan.get("scenario_env", "")
        if turn_idx == 1:
            has_app = app in u_text or any(a in u_text for a in s_plan.get("aliases", {}).get("app_aliases", []))
            has_srv = srv in u_text or any(a in u_text for a in s_plan.get("aliases", {}).get("service_aliases", []))
            env_kws = ["现场"] if tid != "T2-5" else ["现场", "营地", "训练场", "岸线", "途中", "休息区", "研讨会"]
            has_env = env in u_text or any(k in u_text for k in env_kws)
            if not (has_app and has_srv and has_env):
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
        elif turn_idx == 2:
            if tid == "T2-5":
                if tp.get("duration", "") not in u_text and "延长" not in u_text and "时长" not in u_text:
                    u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
            elif tp.get("resolution", "") not in u_text or tp.get("rtt", "") not in u_text or "特殊" not in u_text:
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)

    if s_plan.get("is_counterexample") and tp.get("resolution", "1080p") not in u_text:
        u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
    return u_text


def _normalize_user_evidence_and_leakage(u_text: str, turn_idx: int, role: str, s_plan: dict) -> str:
    tp = s_plan.get("target_params", {})
    tid = s_plan.get("template_id", "T2-1")
    if turn_idx == 1 and role == "evidence_session":
        app_ok = tp.get("application_name", "") in u_text
        srv_ok = tp.get("service_name", "") in u_text
        start_hm = tp.get("start_timestamp", "").split("日")[-1]
        time_ok = start_hm in u_text or start_hm.replace("时", ":").replace("分", "") in u_text or start_hm.replace("时", "点") in u_text
        leaked = any(
            k and k in u_text
            for k in [
                tp.get("resolution", ""), tp.get("rtt", ""), tp.get("duration", ""),
                "俩小时", "两小时", "一个钟头", "一个半小时", "三个小时",
                "60分钟", "90分钟", "120分钟", "150分钟", "180分钟",
            ]
        )
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

    for bad_word in ["顶格清晰度", "顶格画质", "最高画质", "极限画质", "最高清晰度"]:
        if bad_word in u_text:
            u_text = u_text.replace(bad_word, "1080p原画" if tp.get("resolution") == "1080p" else tp.get("resolution", ""))
    for bad_word in ["零卡顿", "秒开", "极速响应"]:
        if bad_word in u_text:
            u_text = u_text.replace(bad_word, f"{tp.get('rtt', '')}以内")

    if turn_idx == 1 and role in ["reinforcement_session", "reuse_session"] and tid not in ["T2-3", "T2-5", "T2-6", "T2-7", "T2-8", "T2-9", "T2-10"]:
        patterns_to_strip = [
            r'，?(?:顶格清晰度|1080p原画|1080p|720p|4K|4k|超清|高清)[、，]?(?:零卡顿|\d+ms以内|\d+毫秒以内|\d+ms)[、，]?(?:俩小时|两小时|\d+分钟|\d+min)?',
            r'[、，]?(?:顶格清晰度|1080p原画|1080p|720p|4K|4k|超清|高清)',
            r'[、，]?(?:零卡顿|\d+ms以内|\d+毫秒以内|\d+ms)',
        ]
        for pat in patterns_to_strip:
            u_text = re.sub(pat, "", u_text)
        u_text = re.sub(r"，\s*，", "，", u_text).strip("，, ")
        if (tp.get("resolution", "") and tp["resolution"] in u_text) or (tp.get("rtt", "") and tp["rtt"] in u_text):
            u_text = get_fallback_user_utterance(s_plan, turn_idx, role)

    if any(bad_kw in u_text for bad_kw in ["当上午", "进入道路", "触发现场", "办事了，", "弱网空间时", "固定外勤时段"]):
        u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
    u_text = u_text.replace("触发用", "用").replace("触发", "")
    sm_val = s_plan.get("small_memory", {}).get("value")

    def _clean_hallucinated_alias(match):
        alias_word = match.group(1)
        if alias_word in ["每天这个时候", "老规矩", "月初老规矩", "大半个下午"] or (sm_val and alias_word == sm_val):
            return match.group(0)
        return ""

    u_text = re.sub(r'[，、]?(?:画质|时延|时长)?按[‘“\'\"]([^’度”\'\"]+)[’度”\'\"](?:来|开|算|处理)?', _clean_hallucinated_alias, u_text)
    return re.sub(r"，\s*，", "，", u_text).strip("，, ")


def _normalize_agent_and_working_memory(u_text: str, a_text: str, turn_idx: int, role: str, is_last: bool, s_plan: dict) -> tuple[str, str]:
    tp = s_plan.get("target_params", {})
    tid = s_plan.get("template_id", "T2-1")
    if tid == "T1-2" or (tid in ["T2-2", "T3-1"] and s_plan.get("small_memory_evidence_mode") == "cross_turn_clarification"):
        a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
    if (tid == "T1-1" or s_plan.get("blueprint_type") == "distractor") and any(kw in a_text for kw in ["记忆理解", "理解为", "按‘", "按\""]):
        a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
    if tid == "T2-5" and turn_idx == 1:
        dur_m = re.search(r"(\d+)\s*(?:min|分钟)", tp.get("duration", ""))
        if dur_m and (f"{dur_m.group(1)}min" in a_text or f"{dur_m.group(1)}分钟" in a_text):
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
    if s_plan.get("is_counterexample") and ("降" in a_text or ("原画" not in a_text and "1080p" not in a_text)):
        a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
    return _normalize_working_memory_turns(u_text, a_text, turn_idx, role, is_last, s_plan)


def _normalize_working_memory_turns(u_text: str, a_text: str, turn_idx: int, role: str, is_last: bool, s_plan: dict) -> tuple[str, str]:
    tp = s_plan.get("target_params", {})
    tid = s_plan.get("template_id", "T2-1")
    sh_t = tp.get("start_timestamp", "").split("日")[-1]
    eh_t = tp.get("end_timestamp", "").split("日")[-1]
    if s_plan.get("is_disambiguation"):
        if turn_idx == 1:
            if sh_t not in u_text or eh_t not in u_text or tp.get("resolution", "") in u_text or tp.get("rtt", "") in u_text:
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
            if "哪" not in a_text and "意图保障单" not in a_text and "记录" not in a_text:
                a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
        elif turn_idx == 2:
            if "最近" not in u_text and "上次" not in u_text:
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
            if tp.get("resolution", "") not in a_text or tp.get("rtt", "") not in a_text:
                a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
        elif turn_idx == 3 and any(kw in u_text for kw in ["画面", "画质", "透亮", "清晰", "流畅", "时延", "延迟"]):
            u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
    elif tid == "T2-6" and not s_plan.get("experience_citation"):
        if turn_idx == 1 and (tp.get("resolution", "") not in a_text or tp.get("rtt", "") not in a_text):
            a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
        elif turn_idx == 2:
            if sh_t not in u_text or eh_t not in u_text or tp.get("duration", "") not in u_text:
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
            if not is_last and ("确认" not in a_text or "吗" not in a_text):
                a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
        elif turn_idx == 3:
            if any(k in u_text for k in [sh_t, eh_t, "min", "分钟"]) or not any(k in u_text for k in ["确认", "好", "对", "行", "可以"]):
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
    elif tid == "T2-7" and turn_idx == 1:
        is_adv = s_plan.get("working_memory_pointer", {}).get("reschedule_direction") == "advance"
        if (is_adv and "提前" not in u_text) or (not is_adv and "推迟" not in u_text):
            u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
        if sh_t not in a_text or eh_t not in a_text:
            a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
    return u_text, a_text


def _finalize_turn_utterances(u_text: str, a_text: str, turn_idx: int, role: str, is_last: bool, s_plan: dict) -> tuple[str, str]:
    tp = s_plan.get("target_params", {})
    tid = s_plan.get("template_id", "T2-1")
    if turn_idx == 1 and role in ["reinforcement_session", "reuse_session"] and tid not in ["T2-3", "T2-5", "T2-6", "T2-7", "T2-8", "T2-9", "T2-10", "T2-4"] and not s_plan.get("experience_citation"):
        is_imp_s03 = role == "reinforcement_session" and s_plan.get("declaration_mode") == "implicit_induction" and s_plan.get("session_id", "").endswith("-03")
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

    exp_id = s_plan.get("experience_id") or s_plan.get("experience_citation", {}).get("experience_id")
    if tid in ["T1-3", "T2-4", "T2-9", "T2-10"] or s_plan.get("memory_tier") == "experiential_memory" or s_plan.get("blueprint_type") == "experience_learning" or bool(exp_id):
        u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
        a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)

    for bad_word in ["顶格清晰度", "顶格画质", "最高画质", "极限画质", "最高清晰度"]:
        if bad_word in a_text:
            a_text = a_text.replace(bad_word, "1080p原画" if tp.get("resolution") == "1080p" else tp.get("resolution", ""))
    for bad_word in ["零卡顿", "秒开", "极速响应"]:
        if bad_word in a_text:
            a_text = a_text.replace(bad_word, f"{tp.get('rtt', '')}以内")

    ref_day = s_plan.get("reference_time", "").split("日")[0]
    start_day = tp.get("start_timestamp", "").split("日")[0]
    if ref_day and start_day and ref_day == start_day:
        for w in ["明天", "后天"]:
            u_text = u_text.replace(w, "今天")
            a_text = a_text.replace(w, "今天")
    return u_text, a_text


def normalize_dialogue_turn(t_data: dict, turn_idx: int, role: str, is_last: bool, s_plan: dict) -> tuple[str, list[str], str, list[str]]:
    u_text, a_text = _extract_raw_utterances(t_data, turn_idx, role, is_last, s_plan)
    u_text = _normalize_user_template_constraints(u_text, turn_idx, role, s_plan)
    u_text = _normalize_user_evidence_and_leakage(u_text, turn_idx, role, s_plan)
    u_text, a_text = _normalize_agent_and_working_memory(u_text, a_text, turn_idx, role, is_last, s_plan)
    u_text, a_text = _finalize_turn_utterances(u_text, a_text, turn_idx, role, is_last, s_plan)
    raw_u_acts = t_data.get("user_action_types") if isinstance(t_data, dict) else None
    raw_a_acts = t_data.get("agent_action_types") if isinstance(t_data, dict) else None
    u_acts, a_acts = get_normalized_action_types(s_plan, turn_idx, role, is_last, raw_u_acts, raw_a_acts)
    return u_text, u_acts, a_text, a_acts
