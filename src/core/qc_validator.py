import json
import re
from pathlib import Path
from src.config.settings import Config

class QCValidator:
    """
    质量检查与规则验证器 (Quality Control & Rule Checker)
    自动对生成的 Session 序列进行严格的结构与语义检查，输出质检报告。
    """

    TEMPLATE_SPEC = {
        "T1-1": [(1, 1)], "T1-2": [(1, 1)], "T1-3": [(1, 2)], "T1-4": [(1, 1)],
        "T2-1": [(1, 1), (2, 1), (3, 1)], "T2-2": [(2, 1)], "T2-3": [(2, 1)], "T2-4": [(2, 1), (2, 2)],
        "T2-5": [(2, 1)], "T2-6": [(2, 1), (3, 1)], "T2-7": [(2, 1)], "T2-8": [(1, 1)],
        "T2-9": [(2, 1), (3, 1)], "T2-10": [(2, 1)],
        "T3-1": [(3, 1)], "T3-2": [(3, 1)], "T3-3": [(3, 1)], "T3-4": [(3, 1)],
        "X-1": [(1, 2)], "X-2": [(3, 3)],
    }

    @classmethod
    def validate_sessions(cls, sessions: list[dict], memory_traces: list[dict] = None) -> dict:
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
                "template_spec_check": True
            },
            "issues": []
        }

        for idx, s in enumerate(sessions, start=1):
            sid = s.get("session_id", f"idx_{idx}")
            role = s.get("session_meta", {}).get("memory_role", "unknown")
            tid = s.get("session_meta", {}).get("template_id", "")
            events = s.get("event_sequence", [])
            s_passed = True

            # 1. 验证必须以 Agent 结束，动作必须包含 Acknowledge 或 Reject_Request
            if not events or "agent" not in events[-1] or not events[-1]["agent"].get("utterance"):
                report["issues"].append(f"[{sid}] 缺少 Agent 最终答复")
                report["rule_checks"]["agent_ending_check"] = False
                s_passed = False
            elif not any(act in events[-1]["agent"].get("action_types", []) for act in ["Acknowledge", "Reject_Request"]):
                report["issues"].append(f"[{sid}] Agent 最终答复动作必须为 Acknowledge 或 Reject_Request")
                report["rule_checks"]["agent_ending_check"] = False
                s_passed = False

            # 2. 验证强化/复用：常规稳健(α<=0.5)必须 ≥ 2 轮确认；极致敏捷(α=1.0)支持 1 轮极速闭环
            if role in ["reinforcement_session", "reuse_session"]:
                is_extreme_agile = (s.get("session_meta", {}).get("agility_factor") == 1.0)
                if not is_extreme_agile:
                    if len(events) < 2:
                        report["issues"].append(f"[{sid}] 强化/复用会话轮数不足2轮 (实际: {len(events)})")
                        report["rule_checks"]["multi_turn_confirmation_check"] = False
                        s_passed = False
                    else:
                        t1_a_acts = events[0].get("agent", {}).get("action_types", [])
                        if not any(act in t1_a_acts for act in ["Confirm_Slot", "Request_Slot", "Request_Disambiguation"]):
                            report["issues"].append(f"[{sid}] 第1轮 Agent 未执行反问确认动作")
                            report["rule_checks"]["multi_turn_confirmation_check"] = False
                            s_passed = False

            # 3. 验证会话必需字段完整性
            required_keys = ['session_id', 'user_id', 'reference_time', 'session_meta', 'event_sequence', 'intents', 'relations', 'slot_updates']
            for k in required_keys:
                if k not in s:
                    report["issues"].append(f"[{sid}] 缺失会话必需字段 {k}")
                    report["rule_checks"]["source_type_integrity_check"] = False
                    s_passed = False

            # 4. 验证白名单合规性（域外拒绝意图与对账核查除外）
            intents = s.get("intents", [])
            if intents and intents[0].get("status") != "rejected" and s.get("session_meta", {}).get("template_id") != "T2-8":
                app_val = intents[0].get("params", {}).get("application_name", {}).get("value")
                srv_val = intents[0].get("params", {}).get("service_name", {}).get("value")
                if not app_val or not srv_val:
                    report["issues"].append(f"[{sid}] 意图参数缺失应用或业务值")
                    report["rule_checks"]["whitelist_compliance_check"] = False
                    s_passed = False

            # 5. 验证 Turn 级意图隔离性（Turn-level Intent Isolation）与无未来信息泄漏
            for ev_idx, ev in enumerate(events):
                if "turn_intents" not in ev:
                    report["issues"].append(f"[{sid}] Turn {ev_idx+1} 缺少 turn_intents 字段")
                    report["rule_checks"]["turn_intent_isolation_check"] = False
                    s_passed = False
                if "requested_params" not in ev:
                    report["issues"].append(f"[{sid}] Turn {ev_idx+1} 缺少 requested_params 字段")
                    report["rule_checks"]["turn_intent_isolation_check"] = False
                    s_passed = False

            if role == "evidence_session" and len(events) >= 2:
                # 检查第 1 轮 requested_params
                t1_req = events[0].get("requested_params", [])
                if "resolution" not in t1_req:
                    report["issues"].append(f"[{sid}] 证据会话第1轮 requested_params 缺失 resolution")
                    report["rule_checks"]["turn_intent_isolation_check"] = False
                    s_passed = False

                t1_intents = events[0].get("turn_intents", [])
                if t1_intents:
                    t1_params = t1_intents[0].get("params", {})
                    t1_ts = t1_params.get("timestamp", {})
                    if "resolution" in t1_params or "rtt" in t1_params:
                        report["issues"].append(f"[{sid}] 证据会话第1轮意图答案泄漏了未提及的参数(resolution/rtt)")
                        report["rule_checks"]["turn_intent_isolation_check"] = False
                        s_passed = False
                    if "end_timestamp" in t1_ts or "duration" in t1_ts:
                        report["issues"].append(f"[{sid}] 证据会话第1轮意图答案泄漏了未提及的结束时间/时长(end_timestamp/duration)")
                        report["rule_checks"]["turn_intent_isolation_check"] = False
                        s_passed = False

                # 检查 slot_updates 第1轮不能包含未提及的参数
                for su in s.get("slot_updates", []):
                    for tu in su.get("turn_updates", []):
                        if tu.get("turn") == 1:
                            p = tu.get("params", {})
                            p_ts = p.get("timestamp", {})
                            if "resolution" in p or "rtt" in p:
                                report["issues"].append(f"[{sid}] 证据会话第1轮 slot_updates 泄漏了未提及的参数(resolution/rtt)")
                                report["rule_checks"]["turn_intent_isolation_check"] = False
                                s_passed = False
                            if "end_timestamp" in p_ts or "duration" in p_ts:
                                report["issues"].append(f"[{sid}] 证据会话第1轮 slot_updates 泄漏了未提及的结束时间/时长(end_timestamp/duration)")
                                report["rule_checks"]["turn_intent_isolation_check"] = False
                                s_passed = False

                # 若为 3 轮跨轮澄清证据会话（T3-1）：第 2 轮也严禁泄漏 resolution
                if tid == "T3-1" and len(events) >= 3:
                    t2_req = events[1].get("requested_params", [])
                    if "resolution" not in t2_req:
                        report["issues"].append(f"[{sid}] 3轮证据会话第2轮 requested_params 缺失 resolution")
                        report["rule_checks"]["turn_intent_isolation_check"] = False
                        s_passed = False

                    t2_intents = events[1].get("turn_intents", [])
                    if t2_intents:
                        t2_params = t2_intents[0].get("params", {})
                        if "resolution" in t2_params:
                            report["issues"].append(f"[{sid}] 3轮证据会话第2轮意图答案泄漏了未确认的清晰度(resolution)")
                            report["rule_checks"]["turn_intent_isolation_check"] = False
                            s_passed = False

                    for su in s.get("slot_updates", []):
                        for tu in su.get("turn_updates", []):
                            if tu.get("turn") == 2:
                                p = tu.get("params", {})
                                if "resolution" in p:
                                    report["issues"].append(f"[{sid}] 3轮证据会话第2轮 slot_updates 泄漏了未确认的清晰度(resolution)")
                                    report["rule_checks"]["turn_intent_isolation_check"] = False
                                    s_passed = False

            # 6. 验证用户台词自然口语化（严禁系统/学术术语出戏，如“长期偏好”、“元指令”等），验证相对时间一致性
            ref_day = s.get("reference_time", "").split("日")[0]
            for ev_idx, ev in enumerate(events):
                u_utt = ev.get("user", {}).get("utterance", "")
                if any(bad in u_utt for bad in ["长期偏好", "元指令", "意图槽位"]):
                    report["issues"].append(f"[{sid}] Turn {ev_idx+1} 用户台词包含非自然研发术语(长期偏好/元指令/意图槽位): '{u_utt}'")
                    report["rule_checks"]["natural_dialogue_check"] = False
                    s_passed = False
                # 检查若规划为当天保障，台词中严禁出现“明天/后天”导致日期与标注矛盾
                if ref_day and ("明天" in u_utt or "后天" in u_utt):
                    report["issues"].append(f"[{sid}] Turn {ev_idx+1} 当天会话台词出现'明天/后天'与真实日期矛盾: '{u_utt}'")
                    report["rule_checks"]["natural_dialogue_check"] = False
                    s_passed = False

            # 7. 验证模板与轮数、意图个数强对应 (T1=1轮, T2=2轮, T3=3轮; 单意图/双意图/三意图)
            meta = s.get("session_meta", {})
            tid = meta.get("template_id")
            rc = meta.get("round_count")
            ic = meta.get("intent_count")
            if tid in cls.TEMPLATE_SPEC:
                allowed_specs = cls.TEMPLATE_SPEC[tid]
                valid = any(rc == exp_rc and len(events) == exp_rc and ic == exp_ic and len(s.get("intents", [])) == exp_ic for exp_rc, exp_ic in allowed_specs)
                if not valid:
                    report["issues"].append(f"[{sid}] 模板 {tid} 轮数或意图数不匹配: meta.round_count={rc}, 实际轮数={len(events)}, meta.intent_count={ic}")
                    report["rule_checks"]["template_spec_check"] = False
                    s_passed = False
                sig = meta.get("skeleton_signature", "")
                if not any(sig.startswith(f"{tid}|{exp_rc}|{exp_ic}|") for exp_rc, exp_ic in allowed_specs):
                    report["issues"].append(f"[{sid}] skeleton_signature 前缀与模板规范不符: '{sig}'")
                    report["rule_checks"]["template_spec_check"] = False
                    s_passed = False

            # 8. T1-2 必须在自然语言层面也确实是域外请求与明确拒绝，不能只靠结构标注伪装。
            if s.get("session_meta", {}).get("template_id") == "T1-2" and events:
                ood_goal = s.get("intents", [{}])[0].get("intent", "")
                user_text = events[0].get("user", {}).get("utterance", "")
                agent_text = events[0].get("agent", {}).get("utterance", "")
                reject_markers = ["不支持", "无法", "不能", "暂不", "抱歉", "建议联系"]
                if ood_goal and ood_goal not in user_text:
                    report["issues"].append(f"[{sid}] T1-2 用户台词未表达规划的域外诉求: {ood_goal}")
                    report["rule_checks"]["template_semantic_alignment_check"] = False
                    s_passed = False
                if not any(marker in agent_text for marker in reject_markers):
                    report["issues"].append(f"[{sid}] T1-2 Agent 台词缺少明确拒绝语义")
                    report["rule_checks"]["template_semantic_alignment_check"] = False
                    s_passed = False

            # 9. T1-1 干扰会话必须明确表达全量参数，严禁调用未建立的个性化表达或模糊词
            b_type = s.get("session_meta", {}).get("scenario", {}).get("blueprint_type", "")
            if (tid == "T1-1" or b_type == "distractor") and events:
                u_text = events[0].get("user", {}).get("utterance", "")
                a_text = events[0].get("agent", {}).get("utterance", "")
                bad_alias = ["清晰点就行", "不卡就行", "一会儿", "老规矩", "老时间", "照旧", "按习惯"]
                for ba in bad_alias:
                    if ba in u_text:
                        report["issues"].append(f"[{sid}] T1-1 干扰会话用户台词违规出现未建立的个性化表达: '{ba}'")
                        report["rule_checks"]["natural_dialogue_check"] = False
                        s_passed = False
                if "记忆理解" in a_text or "按‘" in a_text or "按\"" in a_text:
                    report["issues"].append(f"[{sid}] T1-1 干扰会话 Agent 台词违规出现记忆调取话术")
                    report["rule_checks"]["natural_dialogue_check"] = False
                    s_passed = False

            # 10. T2-3 临时纠正覆盖会话：首轮必须满足“场景＋应用＋业务”最小表达，次轮包含特殊现场与调整
            if (tid == "T2-3" or b_type == "event_override") and len(events) >= 2:
                u1 = events[0].get("user", {}).get("utterance", "")
                u2 = events[1].get("user", {}).get("utterance", "")
                p0 = s.get("intents", [{}])[0].get("params", {})
                app = p0.get("application_name", {}).get("value", "")
                srv = p0.get("service_name", {}).get("value", "")
                valid_apps = [app, "微信", "钉钉", "腾讯会议", "哔哩哔哩", "抖音", "快手", "企鹅会议", "阿抖", "小破站", "某信", "绿泡泡", "v信", "WX", "企微"]
                valid_srvs = [srv, "直播", "会议", "通话", "短视频", "开播", "视讯", "对齐开会", "推流"]
                has_app = any(a in u1 for a in valid_apps if a)
                has_srv = any(s in u1 for s in valid_srvs if s)
                has_scene = any(k in u1 for k in ["现场", "营地", "训练场", "岸线", "途中", "休息区", "通勤", "活动"]) or (s.get("session_meta", {}).get("scenario", {}).get("environment", "") in u1)
                if not (has_app and has_srv and has_scene):
                    report["issues"].append(f"[{sid}] T2-3 首轮台词跌破最小表达或缺失场景: '{u1}'")
                    report["rule_checks"]["natural_dialogue_check"] = False
                    s_passed = False
                if "特殊" not in u2 and "人流" not in u2 and "拥塞" not in u2 and "网络" not in u2:
                    report["issues"].append(f"[{sid}] T2-3 次轮台词缺失现场特殊情况说明: '{u2}'")
                    report["rule_checks"]["natural_dialogue_check"] = False
                    s_passed = False

            # 11. T2-5 时长延长会话：首轮必须满足“场景＋应用＋业务”最小表达，次轮包含时长延长说明，首轮Agent禁止提前泄露延长后时长
            if tid == "T2-5" and len(events) >= 2:
                u1 = events[0].get("user", {}).get("utterance", "")
                a1 = events[0].get("agent", {}).get("utterance", "")
                u2 = events[1].get("user", {}).get("utterance", "")
                p0 = s.get("intents", [{}])[0].get("params", {})
                app = p0.get("application_name", {}).get("value", "")
                srv = p0.get("service_name", {}).get("value", "")
                valid_apps = [app, "微信", "钉钉", "腾讯会议", "哔哩哔哩", "抖音", "快手", "企鹅会议", "阿抖", "小破站", "企微"]
                valid_srvs = [srv, "直播", "会议", "通话", "短视频", "开播", "视讯", "对齐开会", "推流", "看直播", "开直播"]
                has_app = any(a in u1 for a in valid_apps if a)
                has_srv = any(s in u1 for s in valid_srvs if s)
                has_scene = any(k in u1 for k in ["现场", "营地", "训练场", "岸线", "途中", "休息区", "通勤", "活动", "研讨会", "交流会", "车间"]) or (s.get("session_meta", {}).get("scenario", {}).get("environment", "") in u1)
                if not (has_app and has_srv and has_scene):
                    report["issues"].append(f"[{sid}] T2-5 首轮台词跌破最小表达或缺失场景: '{u1}'")
                    report["rule_checks"]["natural_dialogue_check"] = False
                    s_passed = False
                dur_str = p0.get("timestamp", {}).get("duration", {}).get("value", "")
                dur_m = re.search(r'(\d+)\s*(?:min|分钟)', dur_str)
                if dur_m:
                    num = dur_m.group(1)
                    if f"{num}min" in a1 or f"{num}分钟" in a1:
                        report["issues"].append(f"[{sid}] T2-5 第1轮客服台词提前泄露次轮修改后时长({num}): '{a1}'")
                        report["rule_checks"]["natural_dialogue_check"] = False
                        s_passed = False
                if "延长" not in u2 and "时长" not in u2 and "min" not in u2 and "分钟" not in u2 and "小时" not in u2:
                    report["issues"].append(f"[{sid}] T2-5 次轮台词缺失时长延长说明: '{u2}'")
                    report["rule_checks"]["natural_dialogue_check"] = False
                    s_passed = False
                if "半天" in u2 or "大半天" in u2 or "一上午" in u2:
                    report["issues"].append(f"[{sid}] T2-5 次轮台词包含有歧义的时长表达('半天'): '{u2}'")
                    report["rule_checks"]["natural_dialogue_check"] = False
                    s_passed = False

            # 12. X-1 混合诉求检查：
            # (1) 如果 reference_time 为工作日（周一至周五），用户台词严禁包含“周末”
            # (2) 单轮自闭环检查：用户台词必须明确包含具体时刻点（如 12:30 或 12点30分）以及明确时长（如 60分钟）
            if tid == "X-1" and events:
                ref_time_str = s.get("reference_time", "")
                m_d = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', ref_time_str)
                u_t = events[0].get("user", {}).get("utterance", "")
                if m_d:
                    from datetime import datetime
                    dt_check = datetime(int(m_d.group(1)), int(m_d.group(2)), int(m_d.group(3)))
                    if dt_check.weekday() < 5 and "周末" in u_t:
                        report["issues"].append(f"[{sid}] X-1 工作日会话台词违规出现'周末': '{u_t}'")
                        report["rule_checks"]["natural_dialogue_check"] = False
                        s_passed = False

                has_tp = bool(re.search(r'(\d{1,2}[:：点时]\d{0,2})', u_t))
                has_dur = bool(re.search(r'(\d+|两|俩|半)(分钟|min|小时|分)', u_t))
                if not has_tp:
                    report["issues"].append(f"[{sid}] X-1 单轮会话用户台词缺失明确起止时刻点: '{u_t}'")
                    report["rule_checks"]["natural_dialogue_check"] = False
                    s_passed = False
                if not has_dur:
                    report["issues"].append(f"[{sid}] X-1 单轮会话用户台词缺失明确时长: '{u_t}'")
                    report["rule_checks"]["natural_dialogue_check"] = False
                    s_passed = False

            # 13. 隐式偏好 Session 3 检查：第1轮台词必须包含业务名锚点，避免跨会话App歧义
            if idx == 3 and role == "reinforcement_session" and len(events) >= 1:
                p0 = s.get("intents", [{}])[0].get("params", {})
                srv = p0.get("service_name", {}).get("value", "")
                u1 = events[0].get("user", {}).get("utterance", "")
                if srv and srv not in u1 and ("上次" in u1):
                    report["issues"].append(f"[{sid}] 隐式偏好Session 3台词缺失业务名锚点'{srv}': '{u1}'")
                    report["rule_checks"]["natural_dialogue_check"] = False
                    s_passed = False

            # 14. 全量台词检查：禁止包含后台规划词'触发'
            for turn in events:
                u_text = turn.get("user", {}).get("utterance", "")
                a_text = turn.get("agent", {}).get("utterance", "")
                if "触发" in u_text or "触发" in a_text:
                    report["issues"].append(f"[{sid}] 台词违规包含后台规划词'触发'")
                    report["rule_checks"]["natural_dialogue_check"] = False
                    s_passed = False
            if s_passed:
                report["passed_sessions"] += 1
            else:
                report["failed_sessions"] += 1

        if memory_traces is not None:
            for t in memory_traces:
                t_sid = t.get("session_id", "unknown")
                if "snapshot_before" not in t or "memory_events" not in t or "gold_state_after" not in t:
                    report["issues"].append(f"[{t_sid}] memory_traces 缺失 snapshot_before/memory_events/gold_state_after 字段")
                    report["rule_checks"]["memory_trace_fields_check"] = False

        # 计算冷热启动指标与敏捷度调控 (TCG 指标 - 严格按事实记忆演进规范评估)
        cold_turns = []
        hot_turns = []
        cold_leakage_violations = 0
        for s in sessions:
            sm = s.get("session_meta", {})
            tier = sm.get("memory_tier", "factual_memory")
            cht = sm.get("cold_hot_type")
            rc = sm.get("round_count", len(s.get("event_sequence", [])))
            # 仅对事实记忆体系(Factual Profile Memory)计算冷热启动轮数与 TCG
            if tier == "factual_memory" or (cht in ["cold_start", "hot_start"] and tier is None):
                if cht == "cold_start":
                    cold_turns.append(rc)
                    ev0 = s.get("event_sequence", [{}])[0]
                    p0 = ev0.get("turn_intents", [{}])[0].get("params", {}) if ev0.get("turn_intents") else {}
                    if any("resolution" in p or "rtt" in p for p in p0):
                        cold_leakage_violations += 1
                elif cht == "hot_start":
                    hot_turns.append(rc)

        t_cold_avg = sum(cold_turns) / len(cold_turns) if cold_turns else 3.0
        t_hot_avg = sum(hot_turns) / len(hot_turns) if hot_turns else 1.5
        tcg = ((t_cold_avg - t_hot_avg) / t_cold_avg * 100.0) if t_cold_avg > 0 else 0.0

        report["metrics"] = {
            "t_cold_avg": round(t_cold_avg, 2),
            "t_hot_avg": round(t_hot_avg, 2),
            "tcg_percentage": round(tcg, 2),
            "tcg_target_met": (tcg >= 40.0),
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
            }
        }

        report["pass_rate"] = f"{(report['passed_sessions'] / report['total_sessions']) * 100:.1f}%" if report['total_sessions'] > 0 else "0%"
        return report
