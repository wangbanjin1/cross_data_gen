"""
单轮对话台词与动作轻量后处理校验器 (Turn Utterance & Action Normalizer).
-----------------------------------------------------------------------
设计原则：
1. 尊重并保留 Tau-Bench 双智能体 (User Simulator & Agent Simulator) 生成的自然口语对话，严禁粗暴覆盖为死板规则模板；
2. 仅执行物理信息隔离防泄漏擦除（如 Turn 1 误报次轮槽位）与违规词（如“触发”、当天说“明天”）轻量清理；
3. 仅当 LLM 返回空字符串或离线模式 (--offline) 时，才使用 fallback 兜底。
"""

from __future__ import annotations

from datetime import datetime
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
    return u_text.strip(), a_text.strip()


def _strip_turn1_leaked_slots(u_text: str, a_text: str, turn_idx: int, role: str, s_plan: dict) -> tuple[str, str]:
    """仅在 Turn 1 擦除违反信息隔离边界的泄露参数，保留其余自然口语表达。"""
    if turn_idx != 1:
        return u_text, a_text

    tp = s_plan.get("target_params", {})
    tid = s_plan.get("template_id", "T2-1")
    b_type = s_plan.get("blueprint_type", "")
    res_val = tp.get("resolution", "")
    rtt_val = tp.get("rtt", "")
    dur_val = tp.get("duration", "")

    if role == "evidence_session":
        for kw in ["老规矩，", "老规矩", "老时间，", "老时间", "老样子，", "老样子", "照旧，", "照旧"]:
            u_text = u_text.replace(kw, "")
        for val in (res_val, rtt_val, dur_val):
            if val and val in u_text:
                u_text = u_text.replace(val, "")
            if val and val in a_text:
                a_text = a_text.replace(val, "")
    elif (
        role in ("reinforcement_session", "reuse_session")
        and tid not in ("T2-3", "T2-4", "T2-5", "T2-6", "T2-7", "T2-8", "T2-9", "T2-10")
        and s_plan.get("memory_tier", "factual_memory") == "factual_memory"
    ):
        patterns_to_strip = [
            r"，?(?:顶格清晰度|1080p原画|1080p|720p|4K|4k)[、，]?(?:零卡顿|\d+ms以内|\d+毫秒以内|\d+ms)",
            r"[、，]?(?:顶格清晰度|1080p原画|1080p|720p|4K|4k)",
            r"[、，]?(?:零卡顿|\d+ms以内|\d+毫秒以内|\d+ms)",
        ]
        for pat in patterns_to_strip:
            u_text = re.sub(pat, "", u_text)
        for val in (res_val, rtt_val):
            if val and val in u_text:
                u_text = u_text.replace(val, "")
    elif tid == "T2-3" or b_type == "event_override":
        for val in (res_val, rtt_val):
            if val and val in u_text:
                u_text = u_text.replace(val, "")
    elif tid == "T2-5" and dur_val:
        dur_num = dur_val.replace("min", "")
        for token in (dur_val, f"{dur_num}分钟"):
            if token and token in a_text:
                a_text = a_text.replace(token, s_plan.get("base_duration", "原定时长"))

    return re.sub(r"，\s*，", "，", u_text).strip("，, "), re.sub(r"，\s*，", "，", a_text).strip("，, ")


def _sanitize_forbidden_words_and_dates(u_text: str, a_text: str, turn_idx: int, role: str, s_plan: dict) -> tuple[str, str]:
    """清理后台研发禁用词与日期指代矛盾，不破坏原句结构。"""
    tp = s_plan.get("target_params", {})
    tid = s_plan.get("template_id", "T2-1")
    b_type = s_plan.get("blueprint_type", "")

    for bad_term in ("长期偏好", "元指令", "意图槽位"):
        u_text = u_text.replace(bad_term, "平时习惯")
    u_text = u_text.replace("触发用", "用").replace("触发", "")
    a_text = a_text.replace("触发用", "用").replace("触发", "")

    ref_day = s_plan.get("reference_time", "").split("日")[0]
    if ref_day:
        for w in ("明天", "后天"):
            u_text = u_text.replace(w, "今天")
            a_text = a_text.replace(w, "今天")

    exp_id = s_plan.get("experience_id") or (s_plan.get("experience_citation") or {}).get("experience_id")
    if exp_id == "EXP_CALENDAR_HOLIDAY_EXCEPTION_01" and turn_idx == 1:
        nom_s = s_plan.get("nominal_start") or ""
        m_ns = re.search(r"(\d{1,2})月0?(\d{1,2})日", nom_s)
        if m_ns:
            mm, dd = m_ns.group(1), m_ns.group(2)
            if f"{mm}月{dd}" not in u_text and f"{mm}月0{dd}" not in u_text:
                if "今天" in u_text:
                    u_text = u_text.replace("今天", f"{mm}月{dd}日", 1)
                else:
                    u_text = f"{mm}月{dd}日" + u_text

    if tid == "X-1":
        m_d = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", s_plan.get("reference_time", ""))
        if m_d and datetime(int(m_d.group(1)), int(m_d.group(2)), int(m_d.group(3))).weekday() < 5:
            u_text = u_text.replace("周末", "工作日")
        sh_t = tp.get("start_timestamp", "").split("日")[-1]
        eh_t = tp.get("end_timestamp", "").split("日")[-1]
        if sh_t not in u_text or tp.get("duration", "") not in u_text or tp.get("resolution", "") not in u_text:
            u_text = get_fallback_user_utterance(s_plan, turn_idx, role)

    if tid == "T1-1" or b_type in ("distractor", "distractor_normal"):
        for ba in ("清晰点就行", "不卡就行", "一会儿", "老规矩", "老时间", "照旧", "按习惯"):
            u_text = u_text.replace(ba, "")
        for ma in ("记忆理解", "按‘", '按"'):
            a_text = a_text.replace(ma, "按您指定的")

    return u_text.strip("，, "), a_text.strip("，, ")


def normalize_dialogue_turn(
    t_data: dict, turn_idx: int, role: str, is_last: bool, s_plan: dict
) -> tuple[str, list[str], str, list[str]]:
    u_text, a_text = _extract_raw_utterances(t_data, turn_idx, role, is_last, s_plan)
    u_text, a_text = _strip_turn1_leaked_slots(u_text, a_text, turn_idx, role, s_plan)
    u_text, a_text = _sanitize_forbidden_words_and_dates(u_text, a_text, turn_idx, role, s_plan)
    raw_u_acts = t_data.get("user_action_types") if isinstance(t_data, dict) else None
    raw_a_acts = t_data.get("agent_action_types") if isinstance(t_data, dict) else None
    u_acts, a_acts = get_normalized_action_types(s_plan, turn_idx, role, is_last, raw_u_acts, raw_a_acts)
    return u_text, u_acts, a_text, a_acts
