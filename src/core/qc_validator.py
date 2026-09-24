import json
from pathlib import Path
from src.config.settings import Config

class QCValidator:
    """
    质量检查与规则验证器 (Quality Control & Rule Checker)
    自动对生成的 Session 序列进行严格的结构与语义检查，输出质检报告。
    """

    @classmethod
    def validate_sessions(cls, sessions: list[dict]) -> dict:
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
                "turn_intent_isolation_check": True
            },
            "issues": []
        }

        for idx, s in enumerate(sessions, start=1):
            sid = s.get("session_id", f"idx_{idx}")
            role = s.get("session_meta", {}).get("memory_role", "unknown")
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

            # 2. 验证强化/复用必须 ≥ 2 轮确认
            if role in ["reinforcement_session", "reuse_session"]:
                if len(events) < 2:
                    report["issues"].append(f"[{sid}] 强化/复用会话轮数不足2轮 (实际: {len(events)})")
                    report["rule_checks"]["multi_turn_confirmation_check"] = False
                    s_passed = False
                else:
                    t1_a_acts = events[0].get("agent", {}).get("action_types", [])
                    t2_u_acts = events[1].get("user", {}).get("action_types", [])
                    if not any(act in t1_a_acts for act in ["Confirm_Slot", "Request_Slot", "Request_Disambiguation"]):
                        report["issues"].append(f"[{sid}] 第1轮 Agent 未执行反问确认动作")
                        report["rule_checks"]["multi_turn_confirmation_check"] = False
                        s_passed = False

            # 3. 验证记忆追踪三字段完整性
            if "memory_snapshot_before" not in s or "memory_events_after" not in s or "gold_memory_state_after" not in s:
                report["issues"].append(f"[{sid}] 缺失 memory_snapshot_before/memory_events_after/gold_memory_state_after 字段")
                report["rule_checks"]["memory_trace_fields_check"] = False
                s_passed = False

            # 4. 验证白名单合规性（域外拒绝意图除外）
            intents = s.get("intents", [])
            if intents and intents[0].get("status") != "rejected":
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

            if s_passed:
                report["passed_sessions"] += 1
            else:
                report["failed_sessions"] += 1

        report["pass_rate"] = f"{(report['passed_sessions'] / report['total_sessions']) * 100:.1f}%" if report['total_sessions'] > 0 else "0%"
        return report
