"""
质量检查与信息隔离验证模块 (QCValidator & PrematureDisclosureValidator).
自动对生成的 Session 序列进行严格的结构、信息隔离与语义检查，输出质检报告。
"""

from __future__ import annotations

import re
from datetime import datetime


class PrematureDisclosureValidator:
    """
    信息隔离与防提前泄露验证器 (Premature Disclosure Validator):
    校验多轮会话 Turn 1 台词是否违反信息隔离边界。
    """

    @classmethod
    def check_session(cls, session: dict) -> list[str]:
        issues: list[str] = []
        sid = session.get("session_id", "unknown")
        meta = session.get("session_meta", {})
        role = meta.get("memory_role", "unknown")
        tid = meta.get("template_id", "")
        b_type = (meta.get("scenario") or {}).get("blueprint_type", "")
        events = session.get("event_sequence", [])
        if len(events) < 2:
            return issues

        u1 = events[0].get("user", {}).get("utterance", "")
        a1 = events[0].get("agent", {}).get("utterance", "")
        intents = session.get("intents", [])
        p0 = intents[0].get("params", {}) if intents else {}
        res_val = (p0.get("resolution") or {}).get("value", "")
        rtt_val = (p0.get("rtt") or {}).get("value", "")
        dur_val = ((p0.get("timestamp") or {}).get("duration") or {}).get("value", "")

        if role == "evidence_session":
            for label, val in (("resolution", res_val), ("rtt", rtt_val), ("duration", dur_val)):
                if val and val in u1:
                    issues.append(f"[{sid}] User Turn 1 违反信息隔离，提前泄露次轮槽位 {label}={val}: '{u1}'")
                if val and val in a1:
                    issues.append(f"[{sid}] Agent Turn 1 违反信息隔离，无先验记忆却提前说出 {label}={val}: '{a1}'")
        elif (
            role in ("reinforcement_session", "reuse_session")
            and tid not in ("T2-3", "T2-4", "T2-5", "T2-6", "T2-7", "T2-8", "T2-9", "T2-10")
            and meta.get("memory_tier", "factual_memory") == "factual_memory"
        ):
            for label, val in (("resolution", res_val), ("rtt", rtt_val)):
                if val and val in u1:
                    issues.append(f"[{sid}] User Turn 1 违反信息隔离，提前说出应由记忆补全的 {label}={val}: '{u1}'")
        elif tid == "T2-3" or b_type == "event_override":
            for label, val in (("resolution", res_val), ("rtt", rtt_val)):
                if val and val in u1:
                    issues.append(f"[{sid}] T2-3 User Turn 1 提前泄露次轮临时调整参数 {label}={val}: '{u1}'")

        return issues


_VALID_APP_MARKERS = [
    "微信", "钉钉", "腾讯会议", "哔哩哔哩", "抖音", "快手", "飞书", "企鹅会议",
    "会议通", "阿抖", "小破站", "某信", "绿泡泡", "v信", "WX", "企微",
    "weixin", "douyin", "tencentmeeting", "bilibili",
]
_VALID_SRV_MARKERS = [
    "直播", "会议", "通话", "短视频", "开播", "视讯", "对齐开会", "推流",
    "看直播", "开直播", "碰头会", "连线", "连麦",
]
_SCENE_MARKERS = ["现场", "营地", "训练场", "岸线", "途中", "休息区", "通勤", "活动", "研讨会", "交流会", "车间"]


class QCValidator:
    """质量检查与规则验证器 (Quality Control & Rule Checker)."""

    TEMPLATE_SPEC = {
        "T1-1": [(1, 1)], "T1-2": [(1, 1)], "T1-3": [(1, 2)], "T1-4": [(1, 1)],
        "T2-1": [(1, 1), (2, 1), (3, 1)], "T2-2": [(2, 1)], "T2-3": [(2, 1), (3, 1)], "T2-4": [(2, 1), (2, 2)],
        "T2-5": [(2, 1), (3, 1)], "T2-6": [(2, 1), (3, 1)], "T2-7": [(2, 1)], "T2-8": [(1, 1)],
        "T2-9": [(2, 1), (3, 1)], "T2-10": [(2, 1)],
        "T3-1": [(3, 1)], "T3-2": [(3, 1)], "T3-3": [(3, 1)], "T3-4": [(3, 1)],
        "X-1": [(1, 2)], "X-2": [(3, 3)],
    }

    @classmethod
    def _validate_session_structure(cls, s: dict, sid: str, role: str, tid: str, events: list, report: dict) -> bool:
        passed = True
        if not events or "agent" not in events[-1] or not events[-1]["agent"].get("utterance"):
            report["issues"].append(f"[{sid}] 缺少 Agent 最终答复")
            report["rule_checks"]["agent_ending_check"] = False
            passed = False
        elif not any(act in events[-1]["agent"].get("action_types", []) for act in ["Acknowledge", "Reject_Request"]):
            report["issues"].append(f"[{sid}] Agent 最终答复动作必须为 Acknowledge 或 Reject_Request")
            report["rule_checks"]["agent_ending_check"] = False
            passed = False

        if role in ["reinforcement_session", "reuse_session"] and s.get("session_meta", {}).get("agility_factor") != 1.0:
            if len(events) < 2:
                report["issues"].append(f"[{sid}] 强化/复用会话轮数不足2轮 (实际: {len(events)})")
                report["rule_checks"]["multi_turn_confirmation_check"] = False
                passed = False
            else:
                t1_a_acts = events[0].get("agent", {}).get("action_types", [])
                if not any(act in t1_a_acts for act in ["Confirm_Slot", "Request_Slot", "Request_Disambiguation"]):
                    report["issues"].append(f"[{sid}] 第1轮 Agent 未执行反问确认动作")
                    report["rule_checks"]["multi_turn_confirmation_check"] = False
                    passed = False

        if len(events) == 3:
            t2_a_acts = events[1].get("agent", {}).get("action_types", [])
            if "Acknowledge" in t2_a_acts or not any(act in t2_a_acts for act in ["Confirm_Slot", "Request_Slot", "Request_Disambiguation"]):
                report["issues"].append(f"[{sid}] 3轮会话第2轮 Agent 必须执行反问确认，不得提前 Acknowledge 结束 (实际: {t2_a_acts})")
                report["rule_checks"]["multi_turn_confirmation_check"] = False
                passed = False

        req_keys = ["session_id", "user_id", "reference_time", "session_meta", "event_sequence", "intents", "relations", "slot_updates"]
        for k in req_keys:
            if k not in s:
                report["issues"].append(f"[{sid}] 缺失会话必需字段 {k}")
                report["rule_checks"]["source_type_integrity_check"] = False
                passed = False

        intents = s.get("intents", [])
        if intents and intents[0].get("status") != "rejected" and tid != "T2-8":
            app_val = intents[0].get("params", {}).get("application_name", {}).get("value")
            srv_val = intents[0].get("params", {}).get("service_name", {}).get("value")
            if not app_val or not srv_val:
                report["issues"].append(f"[{sid}] 意图参数缺失应用或业务值")
                report["rule_checks"]["whitelist_compliance_check"] = False
                passed = False
        return passed

    @classmethod
    def _validate_memory_causality(cls, s: dict, sid: str, role: str, tid: str, events: list, report: dict) -> bool:
        passed = True
        for ev_idx, ev in enumerate(events):
            if "turn_intents" not in ev or "requested_params" not in ev:
                missing_field = "turn_intents" if "turn_intents" not in ev else "requested_params"
                report["issues"].append(f"[{sid}] Turn {ev_idx+1} 缺少 {missing_field} 字段")
                report["rule_checks"]["turn_intent_isolation_check"] = False
                passed = False

        if role != "evidence_session" or len(events) < 2:
            return passed

        if "resolution" not in events[0].get("requested_params", []):
            report["issues"].append(f"[{sid}] 证据会话第1轮 requested_params 缺失 resolution")
            report["rule_checks"]["turn_intent_isolation_check"] = False
            passed = False

        t1_intents = events[0].get("turn_intents", [])
        if t1_intents:
            t1_params = t1_intents[0].get("params", {})
            t1_ts = t1_params.get("timestamp", {})
            if "resolution" in t1_params or "rtt" in t1_params:
                report["issues"].append(f"[{sid}] 证据会话第1轮意图答案泄漏了未提及的参数(resolution/rtt)")
                report["rule_checks"]["turn_intent_isolation_check"] = False
                passed = False
            if "end_timestamp" in t1_ts or "duration" in t1_ts:
                report["issues"].append(f"[{sid}] 证据会话第1轮意图答案泄漏了未提及的结束时间/时长(end_timestamp/duration)")
                report["rule_checks"]["turn_intent_isolation_check"] = False
                passed = False

        for su in s.get("slot_updates", []):
            for tu in su.get("turn_updates", []):
                if tu.get("turn") == 1:
                    p, p_ts = tu.get("params", {}), tu.get("params", {}).get("timestamp", {})
                    if "resolution" in p or "rtt" in p or "end_timestamp" in p_ts or "duration" in p_ts:
                        report["issues"].append(f"[{sid}] 证据会话第1轮 slot_updates 泄漏了未提及的参数")
                        report["rule_checks"]["turn_intent_isolation_check"] = False
                        passed = False
                elif tid == "T3-1" and len(events) >= 3 and tu.get("turn") == 2 and "resolution" in tu.get("params", {}):
                    report["issues"].append(f"[{sid}] 3轮证据会话第2轮 slot_updates 泄漏了未确认的清晰度(resolution)")
                    report["rule_checks"]["turn_intent_isolation_check"] = False
                    passed = False

        if tid == "T3-1" and len(events) >= 3:
            if "resolution" not in events[1].get("requested_params", []):
                report["issues"].append(f"[{sid}] 3轮证据会话第2轮 requested_params 缺失 resolution")
                report["rule_checks"]["turn_intent_isolation_check"] = False
                passed = False
            t2_intents = events[1].get("turn_intents", [])
            if t2_intents and "resolution" in t2_intents[0].get("params", {}):
                report["issues"].append(f"[{sid}] 3轮证据会话第2轮意图答案泄漏了未确认的清晰度(resolution)")
                report["rule_checks"]["turn_intent_isolation_check"] = False
                passed = False
        return passed

    @classmethod
    def _validate_turn_constraints_and_forbidden(cls, s: dict, sid: str, tid: str, b_type: str, events: list, report: dict) -> bool:
        passed = True
        meta = s.get("session_meta", {})
        rc, ic = meta.get("round_count"), meta.get("intent_count")
        if tid in cls.TEMPLATE_SPEC:
            allowed = cls.TEMPLATE_SPEC[tid]
            if not any(rc == exp_rc and len(events) == exp_rc and ic == exp_ic and len(s.get("intents", [])) == exp_ic for exp_rc, exp_ic in allowed):
                report["issues"].append(f"[{sid}] 模板 {tid} 轮数或意图数不匹配: meta.round_count={rc}, 实际轮数={len(events)}, meta.intent_count={ic}")
                report["rule_checks"]["template_spec_check"] = False
                passed = False
            sig = meta.get("skeleton_signature", "")
            if not any(sig.startswith(f"{tid}|{exp_rc}|{exp_ic}|") for exp_rc, exp_ic in allowed):
                report["issues"].append(f"[{sid}] skeleton_signature 前缀与模板规范不符: '{sig}'")
                report["rule_checks"]["template_spec_check"] = False
                passed = False

        if tid == "T1-2" and events:
            ood_goal = s.get("intents", [{}])[0].get("intent", "")
            u_text, a_text = events[0].get("user", {}).get("utterance", ""), events[0].get("agent", {}).get("utterance", "")
            if ood_goal and ood_goal not in u_text:
                report["issues"].append(f"[{sid}] T1-2 用户台词未表达规划的域外诉求: {ood_goal}")
                report["rule_checks"]["template_semantic_alignment_check"] = False
                passed = False
            if not any(m in a_text for m in ["不支持", "无法", "不能", "暂不", "抱歉", "建议联系"]):
                report["issues"].append(f"[{sid}] T1-2 Agent 台词缺少明确拒绝语义")
                report["rule_checks"]["template_semantic_alignment_check"] = False
                passed = False

        if (tid == "T1-1" or b_type == "distractor") and events:
            u_text, a_text = events[0].get("user", {}).get("utterance", ""), events[0].get("agent", {}).get("utterance", "")
            for ba in ["清晰点就行", "不卡就行", "一会儿", "老规矩", "老时间", "照旧", "按习惯"]:
                if ba in u_text:
                    report["issues"].append(f"[{sid}] T1-1 干扰会话用户台词违规出现未建立的个性化表达: '{ba}'")
                    report["rule_checks"]["natural_dialogue_check"] = False
                    passed = False
            if "记忆理解" in a_text or "按‘" in a_text or '按"' in a_text:
                report["issues"].append(f"[{sid}] T1-1 干扰会话 Agent 台词违规出现记忆调取话术")
                report["rule_checks"]["natural_dialogue_check"] = False
                passed = False
        return passed

    @classmethod
    def _validate_closure_and_utterances(cls, s: dict, idx: int, sid: str, role: str, tid: str, b_type: str, events: list, report: dict) -> bool:
        passed = True
        ref_day = s.get("reference_time", "").split("日")[0]
        for ev_idx, ev in enumerate(events):
            u_utt = ev.get("user", {}).get("utterance", "")
            a_utt = ev.get("agent", {}).get("utterance", "")
            if any(bad in u_utt for bad in ["长期偏好", "元指令", "意图槽位"]):
                report["issues"].append(f"[{sid}] Turn {ev_idx+1} 用户台词包含非自然研发术语: '{u_utt}'")
                report["rule_checks"]["natural_dialogue_check"] = False
                passed = False
            if ref_day and ("明天" in u_utt or "后天" in u_utt):
                report["issues"].append(f"[{sid}] Turn {ev_idx+1} 当天会话台词出现'明天/后天'与真实日期矛盾: '{u_utt}'")
                report["rule_checks"]["natural_dialogue_check"] = False
                passed = False
            if "触发" in u_utt or "触发" in a_utt:
                report["issues"].append(f"[{sid}] 台词违规包含后台规划词'触发'")
                report["rule_checks"]["natural_dialogue_check"] = False
                passed = False

        if (tid in ("T2-3", "T2-5") or b_type == "event_override") and len(events) >= 2:
            passed = cls._check_t2_3_and_t2_5_utterances(s, sid, tid, b_type, events, report) and passed

        if tid == "X-1" and events:
            passed = cls._check_x1_utterances(s, sid, events, report) and passed

        if idx == 3 and role == "reinforcement_session" and events:
            srv = s.get("intents", [{}])[0].get("params", {}).get("service_name", {}).get("value", "")
            u1 = events[0].get("user", {}).get("utterance", "")
            if srv and srv not in u1 and "上次" in u1:
                report["issues"].append(f"[{sid}] 隐式偏好Session 3台词缺失业务名锚点'{srv}': '{u1}'")
                report["rule_checks"]["natural_dialogue_check"] = False
                passed = False

        disclosure_issues = PrematureDisclosureValidator.check_session(s)
        if disclosure_issues:
            report["issues"].extend(disclosure_issues)
            report["rule_checks"]["premature_disclosure_check"] = False
            passed = False
        return passed

    @classmethod
    def _check_t2_3_and_t2_5_utterances(cls, s: dict, sid: str, tid: str, b_type: str, events: list, report: dict) -> bool:
        passed = True
        u1, a1, u2 = events[0].get("user", {}).get("utterance", ""), events[0].get("agent", {}).get("utterance", ""), events[1].get("user", {}).get("utterance", "")
        p0 = s.get("intents", [{}])[0].get("params", {})
        app, srv = p0.get("application_name", {}).get("value", ""), p0.get("service_name", {}).get("value", "")
        env = s.get("session_meta", {}).get("scenario", {}).get("environment", "")
        has_app = any(a in u1 for a in [app, *_VALID_APP_MARKERS] if a)
        has_srv = any(sv in u1 for sv in [srv, *_VALID_SRV_MARKERS] if sv)
        has_scene = any(k in u1 for k in _SCENE_MARKERS) or (bool(env) and env in u1)
        if not (has_app and has_srv and has_scene):
            report["issues"].append(f"[{sid}] {tid} 首轮台词跌破最小表达或缺失场景: '{u1}'")
            report["rule_checks"]["natural_dialogue_check"] = False
            passed = False
        if tid == "T2-3" or b_type == "event_override":
            if not any(k in u2 for k in ["特殊", "人流", "拥塞", "网络"]):
                report["issues"].append(f"[{sid}] T2-3 次轮台词缺失现场特殊情况说明: '{u2}'")
                report["rule_checks"]["natural_dialogue_check"] = False
                passed = False
        if tid == "T2-5":
            dur_m = re.search(r'(\d+)\s*(?:min|分钟)', p0.get("timestamp", {}).get("duration", {}).get("value", ""))
            if dur_m and (f"{dur_m.group(1)}min" in a1 or f"{dur_m.group(1)}分钟" in a1):
                report["issues"].append(f"[{sid}] T2-5 第1轮客服台词提前泄露次轮修改后时长({dur_m.group(1)}): '{a1}'")
                report["rule_checks"]["natural_dialogue_check"] = False
                passed = False
            if not any(k in u2 for k in ["延长", "时长", "min", "分钟", "小时"]) or any(k in u2 for k in ["半天", "大半天", "一上午"]):
                report["issues"].append(f"[{sid}] T2-5 次轮台词时长延长表达不合规: '{u2}'")
                report["rule_checks"]["natural_dialogue_check"] = False
                passed = False
        return passed

    @classmethod
    def _check_x1_utterances(cls, s: dict, sid: str, events: list, report: dict) -> bool:
        passed = True
        m_d = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', s.get("reference_time", ""))
        u_t = events[0].get("user", {}).get("utterance", "")
        if m_d and datetime(int(m_d.group(1)), int(m_d.group(2)), int(m_d.group(3))).weekday() < 5 and "周末" in u_t:
            report["issues"].append(f"[{sid}] X-1 工作日会话台词违规出现'周末': '{u_t}'")
            report["rule_checks"]["natural_dialogue_check"] = False
            passed = False
        if not re.search(r'(\d{1,2}[:：点时]\d{0,2})', u_t) or not re.search(r'(\d+|两|俩|半)(分钟|min|小时|分)', u_t):
            report["issues"].append(f"[{sid}] X-1 单轮会话用户台词缺失明确起止时刻点或时长: '{u_t}'")
            report["rule_checks"]["natural_dialogue_check"] = False
            passed = False
        return passed

    @classmethod
    def _compute_tcg_metrics(cls, sessions: list[dict]) -> dict:
        cold_turns, hot_turns = [], []
        cold_leakage_violations = 0
        for s in sessions:
            sm = s.get("session_meta", {})
            tier = sm.get("memory_tier", "factual_memory")
            cht = sm.get("cold_hot_type")
            rc = sm.get("round_count", len(s.get("event_sequence", [])))
            if tier == "factual_memory" or (cht in ["cold_start", "hot_start"] and tier is None):
                if cht == "cold_start":
                    cold_turns.append(rc)
                    ev0 = s.get("event_sequence", [{}])[0]
                    p0 = ev0.get("turn_intents", [{}])[0].get("params", {}) if ev0.get("turn_intents") else {}
                    if any("resolution" in p or "rtt" in p for p in p0):
                        cold_leakage_violations += 1
                elif cht == "hot_start" and sm.get("template_id") not in ("T2-3", "T2-5"):
                    hot_turns.append(rc)

        t_cold_avg = sum(cold_turns) / len(cold_turns) if cold_turns else 3.0
        t_hot_avg = sum(hot_turns) / len(hot_turns) if hot_turns else 1.5
        tcg = ((t_cold_avg - t_hot_avg) / t_cold_avg * 100.0) if t_cold_avg > 0 else 0.0
        return {
            "t_cold_avg": round(t_cold_avg, 2),
            "t_hot_avg": round(t_hot_avg, 2),
            "tcg_percentage": round(tcg, 2),
            "tcg_target_met": tcg >= 40.0,
            "cold_start_zero_leakage_rate": 100.0 if cold_leakage_violations == 0 else 0.0,
            "agility_distribution": {
                "alpha_0_0_cold": len(cold_turns),
                "alpha_0_5_steady": sum(1 for s in sessions if s.get("session_meta", {}).get("agility_factor") == 0.5),
                "alpha_1_0_agile": sum(1 for s in sessions if s.get("session_meta", {}).get("agility_factor") == 1.0),
            },
            "tier_counts": {
                "factual_memory": sum(1 for s in sessions if s.get("session_meta", {}).get("memory_tier") == "factual_memory"),
                "working_memory": sum(1 for s in sessions if s.get("session_meta", {}).get("memory_tier") == "working_memory"),
                "experiential_memory": sum(1 for s in sessions if s.get("session_meta", {}).get("memory_tier") == "experiential_memory"),
            },
        }

    @classmethod
    def validate_sessions(cls, sessions: list[dict], memory_traces: list[dict] | None = None) -> dict:
        report = {
            "total_sessions": len(sessions),
            "passed_sessions": 0,
            "failed_sessions": 0,
            "rule_checks": {
                "agent_ending_check": True,
                "multi_turn_confirmation_check": True,
                "source_type_integrity_check": True,
                "memory_trace_fields_check": True,
                "whitelist_compliance_check": True,
                "turn_intent_isolation_check": True,
                "natural_dialogue_check": True,
                "template_semantic_alignment_check": True,
                "template_spec_check": True,
                "premature_disclosure_check": True,
            },
            "issues": [],
        }

        for idx, s in enumerate(sessions, start=1):
            sid = s.get("session_id", f"idx_{idx}")
            meta = s.get("session_meta", {})
            role = meta.get("memory_role", "unknown")
            tid = meta.get("template_id", "")
            b_type = (meta.get("scenario") or {}).get("blueprint_type", "")
            events = s.get("event_sequence", [])

            c1 = cls._validate_session_structure(s, sid, role, tid, events, report)
            c2 = cls._validate_memory_causality(s, sid, role, tid, events, report)
            c3 = cls._validate_turn_constraints_and_forbidden(s, sid, tid, b_type, events, report)
            c4 = cls._validate_closure_and_utterances(s, idx, sid, role, tid, b_type, events, report)

            if c1 and c2 and c3 and c4:
                report["passed_sessions"] += 1
            else:
                report["failed_sessions"] += 1

        if memory_traces is not None:
            for t in memory_traces:
                t_sid = t.get("session_id", "unknown")
                if "snapshot_before" not in t or "memory_events" not in t or "gold_state_after" not in t:
                    report["issues"].append(f"[{t_sid}] memory_traces 缺失 snapshot_before/memory_events/gold_state_after 字段")
                    report["rule_checks"]["memory_trace_fields_check"] = False

        report["metrics"] = cls._compute_tcg_metrics(sessions)
        report["pass_rate"] = f"{(report['passed_sessions'] / report['total_sessions']) * 100:.1f}%" if report["total_sessions"] > 0 else "0%"
        return report
