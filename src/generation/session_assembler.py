import re
import json
"""
会话组装器 (SessionAssembler)
负责根据 official pilot100 模版规范（T2-4, T2-2, T2-1, T1-2, T2-5, X-1, T2-3, T1-1）
装配最终标准的 Session JSON 对象，包括 intents、slot_updates、skeleton_signature 与 scenario 元数据。
"""

class SessionAssembler:

    @classmethod
    def assemble(
        cls,
        s_plan: dict,
        snapshot_before: dict,
        memory_events: list[dict],
        gold_after: dict,
        event_sequence: list[dict],
    ) -> dict:
        sid = s_plan["session_id"]
        uid = s_plan["user_id"]
        ref_time = s_plan["reference_time"]
        tid = s_plan["template_id"]
        role = s_plan["memory_role"]
        b_type = s_plan["blueprint_type"]
        tp = s_plan["target_params"]
        env = s_plan["scenario_env"]
        act = s_plan["memory_action"]
        ood_goal = s_plan.get("ood_goal", "")

        app_name = tp["application_name"]
        srv_name = tp["service_name"]
        res_val = tp["resolution"]
        rtt_val = tp["rtt"]
        start_ts = tp["start_timestamp"]
        end_ts = tp["end_timestamp"]
        dur_val = tp["duration"]

        if tid == "T1-2":
            res = cls._assemble_t1_2(
                sid, uid, ref_time, tid, role, b_type, env, act, ood_goal,
                event_sequence, snapshot_before, memory_events, gold_after
            )
        elif tid == "X-1":
            res = cls._assemble_x_1(
                sid, uid, ref_time, tid, role, b_type, env, act, ood_goal,
                app_name, srv_name, res_val, rtt_val, start_ts, end_ts, dur_val,
                event_sequence, snapshot_before, memory_events, gold_after
            )
        elif tid in ["T2-2", "T3-1"]:
            res = cls._assemble_t2_2(
                sid, uid, ref_time, tid, role, b_type, env, act,
                app_name, srv_name, res_val, rtt_val, start_ts, end_ts, dur_val,
                event_sequence, snapshot_before, memory_events, gold_after,
                evidence_mode=s_plan.get("small_memory_evidence_mode", "explicit_declaration"),
            )
        elif tid == "T2-5":
            res = cls._assemble_t2_5(
                sid, uid, ref_time, tid, role, b_type, env, act,
                app_name, srv_name, res_val, rtt_val, start_ts, end_ts, dur_val,
                event_sequence, snapshot_before, memory_events, gold_after,
                base_end_ts=s_plan.get("base_end_timestamp"),
                base_dur=s_plan.get("base_duration")
            )
        elif tid == "T2-3":
            res = cls._assemble_t2_3(
                sid, uid, ref_time, tid, role, b_type, env, act,
                app_name, srv_name, res_val, rtt_val, start_ts, end_ts, dur_val,
                event_sequence, snapshot_before, memory_events, gold_after
            )
        elif tid == "T2-4":
            res = cls._assemble_t2_4(
                sid, uid, ref_time, tid, role, b_type, env, act,
                app_name, srv_name, res_val, rtt_val, start_ts, end_ts, dur_val,
                event_sequence, snapshot_before, memory_events, gold_after,
                experience_citation=s_plan.get("experience_citation", {}),
                second_source=s_plan.get("second_source"),
                learning_source_session=s_plan.get("learning_source_session"),
                base_end=s_plan.get("base_end") or s_plan.get("base_end_timestamp"),
                base_dur=s_plan.get("base_dur") or s_plan.get("base_duration"),
                start2=s_plan.get("start2"),
                end2=s_plan.get("end2"),
                dur2=s_plan.get("dur2")
            )
        elif tid == "T2-6":
            res = cls._assemble_t2_6(
                sid, uid, ref_time, tid, role, b_type, env, act,
                app_name, srv_name, res_val, rtt_val, start_ts, end_ts, dur_val,
                event_sequence, snapshot_before, memory_events, gold_after,
                working_memory_pointer=s_plan.get("working_memory_pointer", {}),
                experience_citation=s_plan.get("experience_citation", {}),
                learning_source_session=s_plan.get("learning_source_session")
            )
        elif tid == "T2-7":
            res = cls._assemble_t2_7(
                sid, uid, ref_time, tid, role, b_type, env, act,
                app_name, srv_name, res_val, rtt_val, start_ts, end_ts, dur_val,
                event_sequence, snapshot_before, memory_events, gold_after,
                working_memory_pointer=s_plan.get("working_memory_pointer", {})
            )
        elif tid == "T2-8":
            res = cls._assemble_t2_8(
                sid, uid, ref_time, tid, role, b_type, env, act,
                event_sequence, snapshot_before, memory_events, gold_after,
                working_memory_query=s_plan.get("working_memory_query", {})
            )
        elif tid == "T2-9":
            res = cls._assemble_t2_9(
                sid, uid, ref_time, tid, role, b_type, env, act,
                app_name, srv_name, res_val, rtt_val, start_ts, end_ts, dur_val,
                event_sequence, snapshot_before, memory_events, gold_after,
                experience_citation=s_plan.get("experience_citation", {}),
                learning_source_session=s_plan.get("learning_source_session")
            )
        elif tid == "T2-10":
            res = cls._assemble_t2_10(
                sid, uid, ref_time, tid, role, b_type, env, act,
                app_name, srv_name, res_val, rtt_val, start_ts, end_ts, dur_val,
                event_sequence, snapshot_before, memory_events, gold_after,
                experience_citation=s_plan.get("experience_citation", {}),
                learning_source_session=s_plan.get("learning_source_session")
            )
        else:
            res = cls._assemble_standard(
                sid, uid, ref_time, tid, role, b_type, env, act,
                app_name, srv_name, res_val, rtt_val, start_ts, end_ts, dur_val,
                event_sequence, snapshot_before, memory_events, gold_after,
                round_count=s_plan["round_count"],
                small_memory_type=(s_plan.get("small_memory") or {}).get("type"),
                experience_citation=s_plan.get("experience_citation", {}),
                learning_source_session=s_plan.get("learning_source_session")
            )

        if isinstance(res, dict) and "session_meta" in res:
            res["session_meta"]["memory_tier"] = s_plan.get("memory_tier", "factual_memory")
            res["session_meta"]["cold_hot_type"] = s_plan.get("cold_hot_type")
            res["session_meta"]["agility_factor"] = s_plan.get("agility_factor")
        return res

    @classmethod
    def _assemble_t1_2(cls, sid, uid, ref_time, tid, role, b_type, env, act, ood_goal, events, snap, mems, gold):
        goal_text = ood_goal or "宽带光纤装维报修"
        sig = f"T1-2|1|1|I1:{goal_text}/0/rejected/rejected|none|none|out_of_domain"
        intents = [
            {
                "intent_id": "I1",
                "status": "rejected",
                "closure_path": "rejected",
                "expression_level": 0,
                "intent": goal_text,
                "params": {},
            }
        ]
        if events and len(events) >= 1:
            events[0]["requested_params"] = []
            events[0]["turn_intents"] = intents
        return {
            "session_id": sid,
            "user_id": uid,
            "reference_time": ref_time,
            "session_meta": {
                "template_id": tid,
                "round_count": len(events),
                "intent_count": 1,
                "memory_role": role,
                "skeleton_signature": sig,
                "scenario": {
                    "environment": env,
                    "blueprint_type": b_type,
                    "memory_action": act,
                    "request_type": "life_service",
                },
            },
            "event_sequence": events,
            "intents": intents,
            "relations": [],
            "slot_updates": [],
        }

    @classmethod
    def _assemble_x_1(cls, sid, uid, ref_time, tid, role, b_type, env, act, ood_goal, app, srv, res, rtt, start, end, dur, events, snap, mems, gold):
        goal_text = ood_goal or "手机话费充值与账单查询"
        sig = f"X-1|1|2|I1:{app}/{srv}/1/direct/resolved;I2:{goal_text}/0/rejected/rejected|none|none|mixed_reject"
        intents = [
            {
                "intent_id": "I1",
                "status": "resolved",
                "closure_path": "direct",
                "expression_level": 1,
                "intent": f"{app}{srv}保障",
                "params": {
                    "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                    "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                    "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}},
                    "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}},
                    "timestamp": {
                        "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                        "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                        "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"},
                    },
                },
            },
            {
                "intent_id": "I2",
                "status": "rejected",
                "closure_path": "rejected",
                "expression_level": 0,
                "intent": goal_text,
                "params": {},
            },
        ]
        slot_updates = [
            {
                "intent_id": "I1",
                "turn_updates": [
                    {
                        "turn": 1,
                        "params": {
                            "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                            "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                            "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}},
                            "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}},
                            "timestamp": {
                                "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                                "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                                "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"},
                            },
                        },
                    }
                ],
            }
        ]
        if events and len(events) >= 1:
            events[0]["requested_params"] = []
            events[0]["turn_intents"] = intents
        return {
            "session_id": sid,
            "user_id": uid,
            "reference_time": ref_time,
            "session_meta": {
                "template_id": tid,
                "round_count": len(events),
                "intent_count": 2,
                "memory_role": role,
                "skeleton_signature": sig,
                "scenario": {"environment": env, "blueprint_type": b_type, "memory_action": act},
            },
            "event_sequence": events,
            "intents": intents,
            "relations": [],
            "slot_updates": slot_updates,
        }

    @classmethod
    def _assemble_t2_2(cls, sid, uid, ref_time, tid, role, b_type, env, act, app, srv, res, rtt, start, end, dur, events, snap, mems, gold, evidence_mode="explicit_declaration"):
        cross_turn = evidence_mode == "cross_turn_clarification" or len(events) == 3 or tid == "T3-1"
        actual_tid = "T3-1" if cross_turn else tid
        resolution_ref = "U3" if cross_turn else "U2"
        sig = f"{actual_tid}|{len(events)}|1|I1:{app}/{srv}/1/clarified/resolved|none"
        intents = [
            {
                "intent_id": "I1",
                "status": "resolved",
                "closure_path": "clarified",
                "expression_level": 1,
                "intent": f"{app}{srv}保障",
                "params": {
                    "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                    "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                    "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": resolution_ref}},
                    "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U2"}},
                    "timestamp": {
                        "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                        "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U2"},
                        "duration": {"value": dur, "source_type": "Turn", "source_ref": "U2"},
                    },
                },
            }
        ]
        slot_updates = [
            {
                "intent_id": "I1",
                "turn_updates": [
                    {
                        "turn": 1,
                        "params": {
                            "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                            "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                            "timestamp": {
                                "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                            },
                        },
                    },
                    {
                        "turn": 2,
                        "params": {
                            "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U2"}},
                            "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U2"}},
                            "timestamp": {
                                "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U2"},
                                "duration": {"value": dur, "source_type": "Turn", "source_ref": "U2"},
                            },
                        },
                    },
                ],
            }
        ]
        if cross_turn:
            slot_updates[0]["turn_updates"][1]["params"].pop("resolution", None)
            slot_updates[0]["turn_updates"].append({
                "turn": 3,
                "params": {
                    "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U3"}},
                },
            })
        if events and len(events) >= 2:
            events[0]["requested_params"] = ["resolution", "rtt", "duration"]
            events[0]["turn_intents"] = [
                {
                    "intent_id": "I1",
                    "status": "in_progress",
                    "closure_path": "clarify",
                    "expression_level": 1,
                    "intent": f"{app}{srv}保障",
                    "params": {
                        "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                        "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                        "timestamp": {
                            "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                        },
                    },
                }
            ]
            if cross_turn and len(events) >= 3:
                events[1]["requested_params"] = ["resolution"]
                events[1]["turn_intents"] = [{
                    "intent_id": "I1",
                    "status": "in_progress",
                    "closure_path": "clarify",
                    "expression_level": 1,
                    "intent": f"{app}{srv}保障",
                    "params": {
                        "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                        "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                        "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U2"}},
                        "timestamp": {
                            "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U2"},
                            "duration": {"value": dur, "source_type": "Turn", "source_ref": "U2"},
                        },
                    },
                }]
                events[2]["requested_params"] = []
                events[2]["turn_intents"] = intents
            else:
                events[1]["requested_params"] = []
                events[1]["turn_intents"] = intents
        return {
            "session_id": sid,
            "user_id": uid,
            "reference_time": ref_time,
            "session_meta": {
                "template_id": tid,
                "round_count": len(events),
                "intent_count": 1,
                "memory_role": role,
                "skeleton_signature": sig,
                "scenario": {"environment": env, "blueprint_type": b_type, "memory_action": act},
            },
            "event_sequence": events,
            "intents": intents,
            "relations": [],
            "slot_updates": slot_updates,
        }

    @classmethod
    def _assemble_t2_5(cls, sid, uid, ref_time, tid, role, b_type, env, act, app, srv, res, rtt, start, end, dur, events, snap, mems, gold, base_end_ts=None, base_dur=None):
        sig = f"T2-5|2|1|I1:{app}/{srv}/1/amend/resolved|none"
        if not base_end_ts:
            base_end_ts = end.replace("17时00分", "16时00分") if "17时00分" in end else end
        base_dur = base_dur or "120min"
        intents = [
            {
                "intent_id": "I1",
                "status": "resolved",
                "closure_path": "amend",
                "expression_level": 1,
                "intent": f"{app}{srv}保障",
                "params": {
                    "application_name": {"value": app, "source_type": "Memory", "source_ref": "MF_001"},
                    "service_name": {"value": srv, "source_type": "Memory", "source_ref": "MF_001"},
                    "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}},
                    "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}},
                    "timestamp": {
                        "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                        "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U2"},
                        "duration": {"value": dur, "source_type": "Turn", "source_ref": "U2"},
                    },
                },
            }
        ]
        slot_updates = [
            {
                "intent_id": "I1",
                "turn_updates": [
                    {
                        "turn": 1,
                        "params": {
                            "application_name": {"value": app, "source_type": "Memory", "source_ref": "MF_001"},
                            "service_name": {"value": srv, "source_type": "Memory", "source_ref": "MF_001"},
                            "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}},
                            "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}},
                            "timestamp": {
                                "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                                "end_timestamp": {"value": base_end_ts, "source_type": "Turn", "source_ref": "U1"},
                                "duration": {"value": base_dur, "source_type": "Context", "source_ref": "U1"},
                            },
                        },
                    },
                    {
                        "turn": 2,
                        "params": {
                            "timestamp": {
                                "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U2"},
                                "duration": {"value": dur, "source_type": "Turn", "source_ref": "U2"},
                            }
                        },
                    },
                ],
            }
        ]
        if events and len(events) >= 2:
            events[0]["requested_params"] = []
            events[0]["turn_intents"] = [
                {
                    "intent_id": "I1",
                    "status": "in_progress",
                    "closure_path": "amend",
                    "expression_level": 1,
                    "intent": f"{app}{srv}保障",
                    "params": {
                        "application_name": {"value": app, "source_type": "Memory", "source_ref": "MF_001"},
                        "service_name": {"value": srv, "source_type": "Memory", "source_ref": "MF_001"},
                        "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}},
                        "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}},
                        "timestamp": {
                            "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": base_end_ts, "source_type": "Turn", "source_ref": "U1"},
                            "duration": {"value": base_dur, "source_type": "Context", "source_ref": "U1"},
                        },
                    },
                }
            ]
            events[1]["requested_params"] = []
            events[1]["turn_intents"] = intents
        return {
            "session_id": sid,
            "user_id": uid,
            "reference_time": ref_time,
            "session_meta": {
                "template_id": tid,
                "round_count": len(events),
                "intent_count": 1,
                "memory_role": role,
                "skeleton_signature": sig,
                "scenario": {"environment": env, "blueprint_type": b_type, "memory_action": act},
            },
            "event_sequence": events,
            "intents": intents,
            "relations": [],
            "slot_updates": slot_updates,
        }

    @classmethod
    def _assemble_t2_3(cls, sid, uid, ref_time, tid, role, b_type, env, act, app, srv, res, rtt, start, end, dur, events, snap, mems, gold):
        sig = f"T2-3|2|1|I1:{app}/{srv}/4/correct/resolved|none"
        intents = [
            {
                "intent_id": "I1",
                "status": "resolved",
                "closure_path": "correct",
                "expression_level": 4,
                "intent": f"{app}{srv}保障",
                "params": {
                    "application_name": {"value": app, "source_type": "Memory", "source_ref": "MF_001"},
                    "service_name": {"value": srv, "source_type": "Memory", "source_ref": "MF_001"},
                    "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U2"}},
                    "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U2"}},
                    "timestamp": {
                        "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                        "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                        "duration": {"value": dur, "source_type": "Context", "source_ref": "U1"},
                    },
                },
            }
        ]
        mf_001 = snap.get("MF_001", {}) if snap else {}
        base_res = mf_001.get("resolution", "1080p")
        base_rtt = mf_001.get("rtt_max", "50ms")
        slot_updates = [
            {
                "intent_id": "I1",
                "turn_updates": [
                    {
                        "turn": 1,
                        "params": {
                            "application_name": {"value": app, "source_type": "Memory", "source_ref": "MF_001"},
                            "service_name": {"value": srv, "source_type": "Memory", "source_ref": "MF_001"},
                            "resolution": {"min_value": {"value": base_res, "source_type": "Memory", "source_ref": "MF_001"}},
                            "rtt": {"max_value": {"value": base_rtt, "source_type": "Memory", "source_ref": "MF_001"}},
                            "timestamp": {
                                "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                                "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                                "duration": {"value": dur, "source_type": "Context", "source_ref": "U1"},
                            },
                        },
                    },
                    {
                        "turn": 2,
                        "params": {
                            "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U2"}},
                            "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U2"}},
                        },
                    },
                ],
            }
        ]
        if events and len(events) >= 2:
            events[0]["requested_params"] = []
            events[0]["turn_intents"] = [
                {
                    "intent_id": "I1",
                    "status": "in_progress",
                    "closure_path": "correct",
                    "expression_level": 4,
                    "intent": f"{app}{srv}保障",
                    "params": {
                        "application_name": {"value": app, "source_type": "Memory", "source_ref": "MF_001"},
                        "service_name": {"value": srv, "source_type": "Memory", "source_ref": "MF_001"},
                        "resolution": {"min_value": {"value": base_res, "source_type": "Memory", "source_ref": "MF_001"}},
                        "rtt": {"max_value": {"value": base_rtt, "source_type": "Memory", "source_ref": "MF_001"}},
                        "timestamp": {
                            "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                            "duration": {"value": dur, "source_type": "Context", "source_ref": "U1"},
                        },
                    },
                }
            ]
            events[1]["requested_params"] = []
            events[1]["turn_intents"] = intents
        return {
            "session_id": sid,
            "user_id": uid,
            "reference_time": ref_time,
            "session_meta": {
                "template_id": tid,
                "round_count": len(events),
                "intent_count": 1,
                "memory_role": role,
                "skeleton_signature": sig,
                "scenario": {"environment": env, "blueprint_type": b_type, "memory_action": act},
            },
            "event_sequence": events,
            "intents": intents,
            "relations": [],
            "slot_updates": slot_updates,
        }

    @classmethod
    def _build_experience_branching(
        cls,
        scenario_type: str,
        exp_id: str,
        rule_title: str,
        learning_source_session: str,
        user_prompt: str,
        ctx: dict
    ) -> dict:
        """构建具备完整 3 轮可执行交互树与自动化仲裁门 (Branch Decision Gate) 的快速闭环与多轮澄清路径评测元数据"""
        app = ctx.get("app", "保障应用")
        srv = ctx.get("srv", "保障业务")
        res = ctx.get("res", "1080p")
        rtt = ctx.get("rtt", "50ms")
        start = ctx.get("start", "14:00")
        end = ctx.get("end", "16:00")
        dur = ctx.get("dur", "120min")

        if scenario_type == "multi_intent_partition":
            flawed_app = "抖音"
            flawed_srv = "开直播"
            app = "微信"
            srv = "视频通话"

            fast_cond = "Agent识别用户是在正式开播前私下跟搭档对直播词与看镜头机位，未机械提取字面‘抖音直播’，主动匹配【微信-视频通话】意图保障单，2轮快速闭环"
            slow_cond = "Agent未启用日常对词试机位经验，被字面‘抖音直播’误导提取为【抖音-开直播】，经用户澄清指正后在3轮完成闭环"

            gate = {
                "eval_turn": 1,
                "decision_type": "pre_stream_partner_rehearsal_app_selection_check",
                "pass_condition": "Agent识别私下跟搭档对直播词看机位使用【微信-视频通话】而非公开【抖音-开直播】 (EXP_MULTI_INTENT_PARTITION_01)",
                "fail_condition": "Agent被字面‘抖音直播’误导，错误提取为【抖音-开直播】",
                "key_slot_assertions": {
                    "target_intent_id": "I1",
                    "checked_slots": ["application_name", "service_name"],
                    "expected_action": "select_wechat_video_call_for_partner_rehearsal"
                },
                "pass_route": "fast_path",
                "fail_route": "slow_path"
            }

            slot_err_reply = (
                "嗨，我只是先跟搭档私下对一下词和看眼机位，还没正式开播呢！"
                "平时对词我们都是打微信视频电话，把应用和业务改成微信视频通话就行。"
            )
            goal_match_reply = "好的，改成微信视频通话就对了，确认按此开通。"

            tree = [
                {
                    "turn": 1,
                    "speaker": "user",
                    "simulator_user_prompt": user_prompt,
                    "agent_hypothesis": "Agent缺乏日常对词试机位经验，被字面‘抖音直播’误导提取为【抖音-开直播】",
                    "baseline_agent_flawed_response": f"收到，已为您准备好{start}至{end}（持续{dur}）的【{flawed_app}-{flawed_srv}】意图保障单（{res} / 时延≤{rtt}），确认按此开通吗？",
                    "expected_agent_correction": f"收到，识别到您是在正式开播前先跟搭档私下对直播词和看镜头机位，结合日常经验已主动为您匹配【{app}-{srv}】意图保障单（{start}至{end}，持续{dur}，{res} / 时延≤{rtt}），确认按此办理吗？",
                    "expected_agent_response": f"收到，识别到您是在正式开播前先跟搭档私下对直播词和看镜头机位，结合日常经验已主动为您匹配【{app}-{srv}】意图保障单（{start}至{end}，持续{dur}，{res} / 时延≤{rtt}），确认按此办理吗？",
                    "flaw_type": "literal_douyin_keyword_app_misattribution",
                    "flaw_description": "未区分正式开播与私下找搭档对词看机位，被字面‘抖音直播’误导提取为抖音-开直播",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    },
                    "baseline_flawed_slots": {
                        "I1": {"application_name": flawed_app, "service_name": flawed_srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    },
                    "delta_from_gt": {
                        "has_error": True,
                        "error_details": [
                            f"I1.application_name: expected '{app}', got '{flawed_app}'",
                            f"I1.service_name: expected '{srv}', got '{flawed_srv}'"
                        ],
                        "triggered_reaction": "on_slot_error"
                    }
                },
                {
                    "turn": 2,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": slot_err_reply,
                    "agent_hypothesis": "Agent收到用户澄清指正后，将保障应用与业务修正为【微信-视频通话】",
                    "expected_agent_correction": f"非常抱歉！原来是开播前私下跟搭档对词看机位，已为您将意图保障单由【{flawed_app}-{flawed_srv}】修正为【{app}-{srv}】（{start}至{end}，持续{dur}，画质{res}、时延≤{rtt}），确认现在为您开通吗？",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    },
                    "delta_from_gt": {
                        "has_error": False,
                        "error_details": [],
                        "triggered_reaction": "on_goal_matched"
                    }
                },
                {
                    "turn": 3,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": goal_match_reply,
                    "agent_hypothesis": "Agent完成【微信-视频通话】意图保障单闭环出单",
                    "expected_agent_correction": f"好的，已为您成功开通{start}至{end}（持续{dur}）的【{app}-{srv}】意图保障单（{res} / 时延≤{rtt}），祝您和搭档对词试机位顺利！",
                    "agent_action_types": ["Acknowledge"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    }
                }
            ]

            full_slow_seq = [
                {
                    "turn": 1,
                    "user": {"utterance": tree[0]["simulator_user_prompt"], "action_types": ["Create_Intent_Request", "Inform_Slot"]},
                    "agent": {"thought": tree[0]["agent_hypothesis"], "utterance": tree[0]["baseline_agent_flawed_response"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [
                        {"intent_id": "I1", "status": "in_progress", "closure_path": "literal_douyin_keyword_app_misattribution", "expression_level": 1, "intent": f"{flawed_app}{flawed_srv}保障", "params": {"application_name": {"value": flawed_app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": flawed_srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"}}}}
                    ]
                },
                {
                    "turn": 2,
                    "user": {"utterance": tree[1]["simulator_user_prompt"], "action_types": ["Revise_Intent_Request", "Inform_Slot"]},
                    "agent": {"thought": tree[1]["agent_hypothesis"], "utterance": tree[1]["expected_agent_correction"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [
                        {"intent_id": "I1", "status": "in_progress", "closure_path": "rehearsal_app_corrected", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U2"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U2"}, "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"}}}}
                    ]
                },
                {
                    "turn": 3,
                    "user": {"utterance": tree[2]["simulator_user_prompt"], "action_types": ["Confirm_Slot"]},
                    "agent": {"thought": tree[2]["agent_hypothesis"], "utterance": tree[2]["expected_agent_correction"], "action_types": ["Acknowledge"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [
                        {"intent_id": "I1", "status": "resolved", "closure_path": "clarification_after_correction", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U2"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U2"}, "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"}}}}
                    ]
                }
            ]

        elif scenario_type == "prewarm_buffer":
            fast_cond = "自主识别大型场馆重大活动并执行提前30分钟预热时间差推算（start_timestamp提前30分钟，duration扩充30分钟），2轮确认极速闭环"
            slow_cond = "机械按活动原定时间掐点预约，未预留调试时间触发on_slot_error，经用户模拟器纠偏后在3轮完成闭环"
            gate = {
                "eval_turn": 1,
                "decision_type": "prewarm_buffer_check",
                "pass_condition": "Agent识别大型场馆重大活动并主动将 start_timestamp 提前 30 分钟预热，同时 duration 扩充 30 分钟 (EXP_PREWARM_BUFFER_01)",
                "fail_condition": "Agent机械按用户口语活动时间掐点预约，未预留调试与预热时间",
                "key_slot_assertions": {
                    "target_intent_id": "I1",
                    "checked_slot": "timestamp.start_timestamp",
                    "expected_adjustment": "-30min_prewarm_offset"
                },
                "pass_route": "fast_path",
                "fail_route": "slow_path"
            }

            nom_start = start
            m_s = re.search(r'^(.*?)(\d{1,2})时(\d{2})分$', start)
            if m_s:
                pfx, hh, mm = m_s.group(1), int(m_s.group(2)), int(m_s.group(3))
                tot = hh * 60 + mm + 30
                nom_start = f"{pfx}{(tot // 60) % 24:02d}时{tot % 60:02d}分"
            else:
                m_s2 = re.search(r'^(.*?)(\d{1,2}):(\d{2})$', start)
                if m_s2:
                    pfx, hh, mm = m_s2.group(1), int(m_s2.group(2)), int(m_s2.group(3))
                    tot = hh * 60 + mm + 30
                    nom_start = f"{pfx}{(tot // 60) % 24:02d}:{tot % 60:02d}"

            m_d = re.search(r'(\d+)', dur)
            nom_dur = f"{max(30, int(m_d.group(1)) - 30)}min" if m_d else "120min"

            slot_err_reply = (
                "等等，大型活动现场还得提前进场调试设备呢，掐着点开来不及！"
                "帮我把开始时间往前提前半小时就行。"
            )
            goal_match_reply = "好的，规格时间都对了，确认按此开通。"

            tree = [
                {
                    "turn": 1,
                    "speaker": "user",
                    "simulator_user_prompt": user_prompt,
                    "agent_hypothesis": "Agent按活动开始时间掐点预约，未做提前30分钟预热试机推算",
                    "baseline_agent_flawed_response": f"收到，已按活动起止时间为您锁定{app}{srv}意图保障单（{nom_start}至{end}，持续{nom_dur}，{res} / 时延≤{rtt}），确认直接为您开通吗？",
                    "expected_agent_correction": f"收到，识别到大型场馆重大活动现场设备需提前预热试机，已为您将意图保障单起保时间自动提前30分钟至{start}（至{end}，总时长{dur}，{res} / 时延≤{rtt}），确认直接开通吗？",
                    "expected_agent_response": f"收到，识别到大型场馆重大活动现场设备需提前预热试机，已为您将意图保障单起保时间自动提前30分钟至{start}（至{end}，总时长{dur}，{res} / 时延≤{rtt}），确认直接开通吗？",
                    "flaw_type": "missing_prewarm_buffer",
                    "flaw_description": "未对大型场馆重大活动现场设备调试进行前置30分钟时间差推算",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    },
                    "baseline_flawed_slots": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": nom_start, "end_timestamp": end, "duration": nom_dur}}
                    },
                    "delta_from_gt": {
                        "has_error": True,
                        "error_details": [
                            f"I1.timestamp.start_timestamp: expected '{start}', got '{nom_start}'",
                            f"I1.timestamp.duration: expected '{dur}', got '{nom_dur}'"
                        ],
                        "triggered_reaction": "on_slot_error"
                    }
                },
                {
                    "turn": 2,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": slot_err_reply,
                    "agent_hypothesis": "Agent收到纠偏后将起保时间提前30分钟并更新总时长",
                    "expected_agent_correction": f"抱歉！已为您重新推算意图保障单时间，将起保时间提前30分钟调整为{start}至{end}（总时长扩充至{dur}，画质{res}、时延≤{rtt}），确认按此提前开通吗？",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    },
                    "delta_from_gt": {
                        "has_error": False,
                        "error_details": [],
                        "triggered_reaction": "on_goal_matched"
                    }
                },
                {
                    "turn": 3,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": goal_match_reply,
                    "agent_hypothesis": "Agent完成提前预热试机意图保障单受理",
                    "expected_agent_correction": f"好的，已为您成功受理提前30分钟预热试机意图保障单（{start}至{end}，持续{dur}，{res} / 时延≤{rtt}），预祝活动圆满顺利！",
                    "agent_action_types": ["Acknowledge"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    }
                }
            ]
            full_slow_seq = [
                {
                    "turn": 1,
                    "user": {"utterance": tree[0]["simulator_user_prompt"], "action_types": ["Create_Intent_Request", "Inform_Slot"]},
                    "agent": {"thought": tree[0]["agent_hypothesis"], "utterance": tree[0]["baseline_agent_flawed_response"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "in_progress", "closure_path": "missing_prewarm_buffer", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}}, "timestamp": {"start_timestamp": {"value": nom_start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": nom_dur, "source_type": "Turn", "source_ref": "U1"}}}}]
                },
                {
                    "turn": 2,
                    "user": {"utterance": tree[1]["simulator_user_prompt"], "action_types": ["Revise_Intent_Request", "Inform_Slot"]},
                    "agent": {"thought": tree[1]["agent_hypothesis"], "utterance": tree[1]["expected_agent_correction"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "in_progress", "closure_path": "prewarm_correction", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U2"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Turn", "source_ref": "U2"}}}}]
                },
                {
                    "turn": 3,
                    "user": {"utterance": tree[2]["simulator_user_prompt"], "action_types": ["Confirm_Slot"]},
                    "agent": {"thought": tree[2]["agent_hypothesis"], "utterance": tree[2]["expected_agent_correction"], "action_types": ["Acknowledge"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "resolved", "closure_path": "clarification_after_correction", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U2"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Turn", "source_ref": "U2"}}}}]
                }
            ]

        elif scenario_type == "holiday_exception":
            fast_cond = "识别10月5日恰逢国庆法定假期冲突，主动将例行周会意图保障单顺延至节后首个工作日（10月8日）同时段，2轮极速出单"
            slow_cond = "Agent缺乏节假日避让经验，机械按10月5日放假当天预约触发on_slot_error，经用户模拟器纠偏后在3轮完成闭环"
            gate = {
                "eval_turn": 1,
                "decision_type": "holiday_conflict_deferral_check",
                "pass_condition": "Agent识别下周一（10月05日）为国庆法定节假日，主动顺延至节后首个工作日2026年10月08日同时段 (EXP_CALENDAR_HOLIDAY_EXCEPTION_01)",
                "fail_condition": "Agent缺乏日历假期避让经验，直接在10月05日放假当天预约",
                "key_slot_assertions": {
                    "target_intent_id": "I1",
                    "checked_slot": "timestamp.start_timestamp",
                    "expected_deferral": "post_holiday_workday_20261008"
                },
                "pass_route": "fast_path",
                "fail_route": "slow_path"
            }

            holiday_start = re.sub(r'\d{4}年\d{1,2}月\d{1,2}日', '2026年10月05日', start)
            holiday_end = re.sub(r'\d{4}年\d{1,2}月\d{1,2}日', '2026年10月05日', end)
            holiday_dur = dur

            slot_err_reply = (
                "哎呀，10月5日还在放国庆假呢，那天不开会！"
                "帮我把日期顺延到节后上班第一天（10月8日）就行。"
            )
            goal_match_reply = "好的，规格时间都对了，确认按此开通。"

            tree = [
                {
                    "turn": 1,
                    "speaker": "user",
                    "simulator_user_prompt": user_prompt,
                    "agent_hypothesis": "Agent未识别下周一（10月5日）为国庆节法定假期，直接在放假当天机械预约",
                    "baseline_agent_flawed_response": f"收到，已为您预约下周一（{holiday_start}至{holiday_end}，持续{holiday_dur}）的{app}{srv}意图保障单（{res} / 时延≤{rtt}），确认直接按此开通吗？",
                    "expected_agent_correction": f"收到，识别到10月5日为国庆法定长假，办公室全员放假。参考前序避让经验，已主动为您将例行周会意图保障单顺延至节后首个工作日（{start}至{end}，持续{dur}，{res} / 时延≤{rtt}），确认按此顺延生效吗？",
                    "expected_agent_response": f"收到，识别到10月5日为国庆法定长假，办公室全员放假。参考前序避让经验，已主动为您将例行周会意图保障单顺延至节后首个工作日（{start}至{end}，持续{dur}，{res} / 时延≤{rtt}），确认按此顺延生效吗？",
                    "flaw_type": "unaware_of_holiday_conflict",
                    "flaw_description": "未对法定节假日冲突避让进行推断，在办公室全员放假时机械预约",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    },
                    "baseline_flawed_slots": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": holiday_start, "end_timestamp": holiday_end, "duration": holiday_dur}}
                    },
                    "delta_from_gt": {
                        "has_error": True,
                        "error_details": [
                            f"I1.timestamp.start_timestamp: expected '{start}', got '{holiday_start}'",
                            f"I1.timestamp.end_timestamp: expected '{end}', got '{holiday_end}'"
                        ],
                        "triggered_reaction": "on_slot_error"
                    }
                },
                {
                    "turn": 2,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": slot_err_reply,
                    "agent_hypothesis": "Agent收到用户纠偏后将意图保障单顺延至2026年10月08日同时段并发起确认",
                    "expected_agent_correction": f"非常抱歉！已为您撤销10月5日放假期间的排期，并将例行周会{app}{srv}意图保障单顺延至节后首个工作日{start}至{end}（持续{dur}，{res} / 时延≤{rtt}），确认按此顺延生效吗？",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    },
                    "delta_from_gt": {
                        "has_error": False,
                        "error_details": [],
                        "triggered_reaction": "on_goal_matched"
                    }
                },
                {
                    "turn": 3,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": goal_match_reply,
                    "agent_hypothesis": "Agent完成节后首个工作日顺延办理并出单",
                    "expected_agent_correction": f"好的，已成功将例行周会{app}{srv}意图保障单顺延至{start}至{end}办理（{res} / 时延≤{rtt}），祝您假期愉快！",
                    "agent_action_types": ["Acknowledge"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    }
                }
            ]
            full_slow_seq = [
                {
                    "turn": 1,
                    "user": {"utterance": tree[0]["simulator_user_prompt"], "action_types": ["Create_Intent_Request", "Inform_Slot"]},
                    "agent": {"thought": tree[0]["agent_hypothesis"], "utterance": tree[0]["baseline_agent_flawed_response"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "in_progress", "closure_path": "unaware_of_holiday_conflict", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}}, "timestamp": {"start_timestamp": {"value": holiday_start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": holiday_end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": holiday_dur, "source_type": "Turn", "source_ref": "U1"}}}}]
                },
                {
                    "turn": 2,
                    "user": {"utterance": tree[1]["simulator_user_prompt"], "action_types": ["Revise_Intent_Request", "Inform_Slot"]},
                    "agent": {"thought": tree[1]["agent_hypothesis"], "utterance": tree[1]["expected_agent_correction"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "in_progress", "closure_path": "holiday_deferral_confirm", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U2"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U2"}, "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"}}}}]
                },
                {
                    "turn": 3,
                    "user": {"utterance": tree[2]["simulator_user_prompt"], "action_types": ["Confirm_Slot"]},
                    "agent": {"thought": tree[2]["agent_hypothesis"], "utterance": tree[2]["expected_agent_correction"], "action_types": ["Acknowledge"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "resolved", "closure_path": "clarification_after_correction", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U2"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U2"}, "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"}}}}]
                }
            ]

        elif scenario_type == "quality_disambiguation":
            d_prefix = start.split("日")[0] + "日" if "日" in start else "2026年10月21日"
            short_flawed_end = f"{d_prefix}16时00分" if "日" in start else "16:00"
            short_flawed_dur = "60min"

            fast_cond = "识别正式客户路演场景，自动过滤前天1小时(60min)临时短单，优选匹配上周2小时(120min)正式路演单时长，2轮快速闭环"
            slow_cond = "Agent未启用历史单据时长消歧经验，按最近邻偏见调取前天1小时(60min)临时短单，经用户澄清指正后在3轮闭环"
            gate = {
                "eval_turn": 1,
                "decision_type": "historical_order_duration_disambiguation_check",
                "pass_condition": "Agent在正式客户路演场景下过滤前天60min临时短单，按上周正式路演单排满120min (EXP_ORDER_QUALITY_DISAMBIGUATION_01)",
                "fail_condition": "Agent因最近邻偏见机械照搬前天那笔60min临时短会单时长",
                "key_slot_assertions": {
                    "target_intent_id": "I1",
                    "checked_source": "Experience",
                    "expected_duration_filter": "prefer_formal_roadshow_120min_order"
                },
                "pass_route": "fast_path",
                "fail_route": "slow_path"
            }

            slot_err_reply = (
                "不对，1个小时不够！你调成前天我临时开的短单了，"
                "今天是正式路演，得按上周那笔正式单把时长改成2个小时。"
            )
            goal_match_reply = "好的，保满两个小时就对了，确认按此开通。"

            tree = [
                {
                    "turn": 1,
                    "speaker": "user",
                    "simulator_user_prompt": user_prompt,
                    "agent_hypothesis": "Agent受最近邻偏见影响，机械调取前天那笔1小时（60min）临时短单",
                    "baseline_agent_flawed_response": f"收到，已为您按最近一笔（前天）的历史意图保障单时长配置，今日{start}至{short_flawed_end}（持续{short_flawed_dur}）为您开通{app}{srv}意图保障单（{res} / 时延≤{rtt}），确认吗？",
                    "expected_agent_correction": f"收到，识别到今日为正式客户远程路演，已自动过滤前天1小时临时短单，按上周正式客户路演单为您排满2小时（{start}至{end}，持续{dur}，{res} / 时延≤{rtt}），确认开通吗？",
                    "expected_agent_response": f"收到，识别到今日为正式客户远程路演，已自动过滤前天1小时临时短单，按上周正式客户路演单为您排满2小时（{start}至{end}，持续{dur}，{res} / 时延≤{rtt}），确认开通吗？",
                    "flaw_type": "recency_bias_short_temporary_order",
                    "flaw_description": "未区分前天1小时临时短会与上周2小时正式客户路演，因最近邻偏见误排为60min",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    },
                    "baseline_flawed_slots": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": short_flawed_end, "duration": short_flawed_dur}}
                    },
                    "delta_from_gt": {
                        "has_error": True,
                        "error_details": [
                            f"I1.timestamp.end_timestamp: expected '{end}', got '{short_flawed_end}'",
                            f"I1.timestamp.duration: expected '{dur}', got '{short_flawed_dur}'"
                        ],
                        "triggered_reaction": "on_slot_error"
                    }
                },
                {
                    "turn": 2,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": slot_err_reply,
                    "agent_hypothesis": "Agent收到用户澄清指正后过滤前天60min短单，改按上周120min正式路演单排期",
                    "expected_agent_correction": f"非常抱歉！已为您过滤前天的1小时临时短单，改按上周正式客户路演单排满2小时（{start}至{end}，持续{dur}，画质{res}、时延≤{rtt}），确认按此开通吗？",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    },
                    "delta_from_gt": {
                        "has_error": False,
                        "error_details": [],
                        "triggered_reaction": "on_goal_matched"
                    }
                },
                {
                    "turn": 3,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": goal_match_reply,
                    "agent_hypothesis": "Agent按2小时正式客户路演单成功出单",
                    "expected_agent_correction": f"好的，已按上周2小时正式路演单时长（{start}至{end}，持续{dur}，{res} / 时延≤{rtt}）为您成功受理{app}{srv}意图保障单，祝您路演顺畅！",
                    "agent_action_types": ["Acknowledge"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    }
                }
            ]
            full_slow_seq = [
                {
                    "turn": 1,
                    "user": {"utterance": tree[0]["simulator_user_prompt"], "action_types": ["Create_Intent_Request", "Inform_Slot"]},
                    "agent": {"thought": tree[0]["agent_hypothesis"], "utterance": tree[0]["baseline_agent_flawed_response"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "in_progress", "closure_path": "recency_bias_short_temporary_order", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": short_flawed_end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": short_flawed_dur, "source_type": "Turn", "source_ref": "U1"}}}}]
                },
                {
                    "turn": 2,
                    "user": {"utterance": tree[1]["simulator_user_prompt"], "action_types": ["Revise_Intent_Request", "Inform_Slot"]},
                    "agent": {"thought": tree[1]["agent_hypothesis"], "utterance": tree[1]["expected_agent_correction"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "in_progress", "closure_path": "formal_roadshow_120min_selected", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U2"}, "duration": {"value": dur, "source_type": "Turn", "source_ref": "U2"}}}}]
                },
                {
                    "turn": 3,
                    "user": {"utterance": tree[2]["simulator_user_prompt"], "action_types": ["Confirm_Slot"]},
                    "agent": {"thought": tree[2]["agent_hypothesis"], "utterance": tree[2]["expected_agent_correction"], "action_types": ["Acknowledge"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "resolved", "closure_path": "clarification_after_correction", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U2"}, "duration": {"value": dur, "source_type": "Turn", "source_ref": "U2"}}}}]
                }
            ]

        elif scenario_type == "overlapping_resolution":
            app = "抖音"
            srv = "开直播"
            flawed_srv = "看直播"

            fast_cond = "识别用户受邀进主会场抖音直播间当连麦嘉宾需上麦推流，未按字面‘进直播间’误判为看直播，主动匹配【抖音-开直播】，2轮快速闭环"
            slow_cond = "Agent未启用连麦嘉宾业务选择经验，看到‘进别人直播间’误判为【抖音-看直播】，经用户澄清指正后在3轮完成闭环"
            gate = {
                "eval_turn": 1,
                "decision_type": "guest_cohost_service_selection_check",
                "pass_condition": "Agent识别受邀进直播间当连麦嘉宾需上麦推流，将 service_name 设为【开直播】而非【看直播】 (EXP_OVERLAPPING_ORDER_RESOLUTION_01)",
                "fail_condition": "Agent看到‘进主会场直播间’字眼，机械将连麦嘉宾归类为普通观众【看直播】",
                "key_slot_assertions": {
                    "target_intent_id": "I1",
                    "checked_strategy": "guest_cohost_uplink_openlive",
                    "expected_action": "select_openlive_instead_of_watchlive"
                },
                "pass_route": "fast_path",
                "fail_route": "slow_path"
            }

            slot_err_reply = (
                "不对，我是去当连麦嘉宾、要开摄像头上麦发言的，不是光在下面看直播！"
                "把业务类型改成开直播就行。"
            )
            goal_match_reply = "好的，改成抖音开直播就对了，确认按此开通。"

            tree = [
                {
                    "turn": 1,
                    "speaker": "user",
                    "simulator_user_prompt": user_prompt,
                    "agent_hypothesis": "Agent缺乏连麦嘉宾业务选择经验，看到‘进主会场抖音直播间’机械提取为【抖音-看直播】",
                    "baseline_agent_flawed_response": f"收到，已为您准备好{start}至{end}（持续{dur}）的【{app}-{flawed_srv}】意图保障单（{res} / 时延≤{rtt}），确认直接开通吗？",
                    "expected_agent_correction": f"收到，识别到您是受邀进主会场抖音直播间当连麦嘉宾互动，上麦发言需保障上行推流，已主动为您匹配【{app}-{srv}】意图保障单（{start}至{end}，持续{dur}，{res} / 时延≤{rtt}），确认按此开通吗？",
                    "expected_agent_response": f"收到，识别到您是受邀进主会场抖音直播间当连麦嘉宾互动，上麦发言需保障上行推流，已主动为您匹配【{app}-{srv}】意图保障单（{start}至{end}，持续{dur}，{res} / 时延≤{rtt}），确认按此开通吗？",
                    "flaw_type": "guest_cohost_misclassified_as_watch_live",
                    "flaw_description": "未区分普通观众看直播与连麦嘉宾上麦发言，将service_name误提为看直播",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    },
                    "baseline_flawed_slots": {
                        "I1": {"application_name": app, "service_name": flawed_srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    },
                    "delta_from_gt": {
                        "has_error": True,
                        "error_details": [
                            f"I1.service_name: expected '{srv}', got '{flawed_srv}'"
                        ],
                        "triggered_reaction": "on_slot_error"
                    }
                },
                {
                    "turn": 2,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": slot_err_reply,
                    "agent_hypothesis": "Agent收到用户澄清指正后，将业务类型由【看直播】修正为【开直播】",
                    "expected_agent_correction": f"非常抱歉！您作为连麦嘉宾上麦互动确实需要上行推流保障，已为您将意图保障单由【{app}-{flawed_srv}】修正为【{app}-{srv}】（{start}至{end}，持续{dur}，画质{res}、时延≤{rtt}），确认按此开通吗？",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    },
                    "delta_from_gt": {
                        "has_error": False,
                        "error_details": [],
                        "triggered_reaction": "on_goal_matched"
                    }
                },
                {
                    "turn": 3,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": goal_match_reply,
                    "agent_hypothesis": "Agent完成【抖音-开直播】连麦嘉宾意图保障单出单",
                    "expected_agent_correction": f"好的，已为您成功开通{start}至{end}（持续{dur}）的【{app}-{srv}】意图保障单（{res} / 时延≤{rtt}），祝您连麦互动顺利！",
                    "agent_action_types": ["Acknowledge"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    }
                }
            ]
            full_slow_seq = [
                {
                    "turn": 1,
                    "user": {"utterance": tree[0]["simulator_user_prompt"], "action_types": ["Create_Intent_Request", "Inform_Slot"]},
                    "agent": {"thought": tree[0]["agent_hypothesis"], "utterance": tree[0]["baseline_agent_flawed_response"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "in_progress", "closure_path": "guest_cohost_misclassified_as_watch_live", "expression_level": 1, "intent": f"{app}{flawed_srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": flawed_srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"}}}}]
                },
                {
                    "turn": 2,
                    "user": {"utterance": tree[1]["simulator_user_prompt"], "action_types": ["Revise_Intent_Request", "Inform_Slot"]},
                    "agent": {"thought": tree[1]["agent_hypothesis"], "utterance": tree[1]["expected_agent_correction"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "in_progress", "closure_path": "guest_cohost_openlive_corrected", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U2"}, "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"}}}}]
                },
                {
                    "turn": 3,
                    "user": {"utterance": tree[2]["simulator_user_prompt"], "action_types": ["Confirm_Slot"]},
                    "agent": {"thought": tree[2]["agent_hypothesis"], "utterance": tree[2]["expected_agent_correction"], "action_types": ["Acknowledge"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "resolved", "closure_path": "clarification_after_correction", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U2"}, "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"}}}}]
                }
            ]
        else:
            fast_cond = "Agent应用经验策略达成高效闭环"
            slow_cond = "Agent缺乏经验导致交互拉扯"
            gate = {"eval_turn": 1, "pass_condition": "命中经验", "fail_condition": "未命中经验", "pass_route": "fast_path", "fail_route": "slow_path"}
            tree = []
            full_slow_seq = []

        slow_rounds = len(tree) if tree else 3
        fast_rounds = 2

        # 构建声明式交互评测契约 (Interactive Evaluation Contract)
        target_gt = {
            "I1": {
                "intent": f"{app}{srv}保障",
                "slots": {
                    "application_name": app,
                    "service_name": srv,
                    "resolution": res,
                    "rtt": rtt,
                    "timestamp": {
                        "start_timestamp": start,
                        "end_timestamp": end,
                        "duration": dur
                    }
                }
            }
        }

        if scenario_type == "multi_intent_partition":
            reaction_matrix = {
                "on_slot_error": {
                    "description": "Agent被字面‘抖音直播’误导，将私下对词试机位误提为【抖音-开直播】而非【微信-视频通话】",
                    "trigger_condition": "agent_slots.get('application_name') != ground_truth['I1']['slots']['application_name'] or agent_slots.get('service_name') != ground_truth['I1']['slots']['service_name']",
                    "monitored_slots": ["I1.application_name", "I1.service_name"],
                    "user_action_types": ["Revise_Intent_Request", "Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_slot_missing": {
                    "description": "Agent遗漏意图保障单的时长或时段槽位",
                    "trigger_condition": "not agent_slots.get('timestamp.duration')",
                    "monitored_slots": ["I1.timestamp.duration"],
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_agent_inquiry": {
                    "description": "Agent向用户询问对词试机位使用的具体应用软件",
                    "trigger_condition": "agent_action in ['Request_Slot']",
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_goal_matched": {
                    "description": "【微信-视频通话】应用、业务与时段完全核准对齐，用户确认闭环出单",
                    "trigger_condition": "agent_slots_all_matched and agent_action in ['Confirm_Slot', 'Inform_Slot', 'Acknowledge']",
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": goal_match_reply
                }
            }
        elif scenario_type == "prewarm_buffer":
            reaction_matrix = {
                "on_slot_error": {
                    "description": "Agent机械按活动原定时间掐点预约，未执行提前30分钟试机预热推算",
                    "trigger_condition": "agent_slots.get('timestamp.start_timestamp') != ground_truth['I1']['slots']['timestamp']['start_timestamp']",
                    "monitored_slots": ["I1.timestamp.start_timestamp", "I1.timestamp.duration"],
                    "user_action_types": ["Revise_Intent_Request", "Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_slot_missing": {
                    "description": "Agent遗漏起保时间或总时长槽位",
                    "trigger_condition": "not agent_slots.get('timestamp.duration')",
                    "monitored_slots": ["I1.timestamp.duration"],
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_agent_inquiry": {
                    "description": "Agent主动询问用户预热起止时段或规格要求",
                    "trigger_condition": "agent_action in ['Request_Slot']",
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_goal_matched": {
                    "description": "提前预热起保时序与网络指标完全核准对齐，用户确认办理",
                    "trigger_condition": "agent_slots_all_matched and agent_action in ['Confirm_Slot', 'Inform_Slot', 'Acknowledge']",
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": goal_match_reply
                }
            }
        elif scenario_type == "holiday_exception":
            reaction_matrix = {
                "on_slot_error": {
                    "description": "Agent未识别国庆长假，机械在10月5日放假当天预约意图保障单",
                    "trigger_condition": "agent_slots.get('timestamp.start_timestamp') != ground_truth['I1']['slots']['timestamp']['start_timestamp']",
                    "monitored_slots": ["I1.timestamp.start_timestamp", "I1.timestamp.end_timestamp"],
                    "user_action_types": ["Revise_Intent_Request", "Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_agent_inquiry": {
                    "description": "Agent识别假期冲突后反问改期时间",
                    "trigger_condition": "agent_action in ['Request_Slot']",
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_slot_missing": {
                    "description": "Agent顺延了日期但遗漏时长或清晰度槽位",
                    "trigger_condition": "not agent_slots.get('timestamp.duration')",
                    "monitored_slots": ["I1.timestamp.duration", "I1.resolution"],
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_goal_matched": {
                    "description": "节后首个工作日顺延时序与规格核准，用户确认办理",
                    "trigger_condition": "agent_slots_all_matched and agent_action in ['Confirm_Slot', 'Inform_Slot', 'Acknowledge']",
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": goal_match_reply
                }
            }
        elif scenario_type == "quality_disambiguation":
            reaction_matrix = {
                "on_slot_error": {
                    "description": "Agent因最近邻偏见机械复用了前天1小时(60min)临时短单时长",
                    "trigger_condition": "agent_slots.get('timestamp.end_timestamp') != ground_truth['I1']['slots']['timestamp']['end_timestamp'] or agent_slots.get('timestamp.duration') != ground_truth['I1']['slots']['timestamp']['duration']",
                    "monitored_slots": ["I1.timestamp.end_timestamp", "I1.timestamp.duration"],
                    "user_action_types": ["Revise_Intent_Request", "Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_slot_missing": {
                    "description": "Agent遗漏核对今日意图保障单起止时序或时长",
                    "trigger_condition": "not agent_slots.get('timestamp.duration')",
                    "monitored_slots": ["I1.timestamp.end_timestamp", "I1.timestamp.duration"],
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_agent_inquiry": {
                    "description": "Agent询问历史意图保障单选择或具体保障时长",
                    "trigger_condition": "agent_action in ['Request_Slot', 'Request_Disambiguation']",
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_goal_matched": {
                    "description": "上周2小时(120min)正式路演单时长继承无误，用户确认受理",
                    "trigger_condition": "agent_slots_all_matched and agent_action in ['Confirm_Slot', 'Inform_Slot', 'Acknowledge']",
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": goal_match_reply
                }
            }
        elif scenario_type == "overlapping_resolution":
            reaction_matrix = {
                "on_slot_error": {
                    "description": "Agent看到‘进主会场抖音直播间’字眼，将连麦嘉宾误提为【看直播】而非【开直播】",
                    "trigger_condition": "agent_slots.get('service_name') != ground_truth['I1']['slots']['service_name']",
                    "monitored_slots": ["I1.service_name"],
                    "user_action_types": ["Revise_Intent_Request", "Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_slot_missing": {
                    "description": "Agent遗漏业务类型或保障时长",
                    "trigger_condition": "not agent_slots.get('service_name')",
                    "monitored_slots": ["I1.service_name"],
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_agent_inquiry": {
                    "description": "Agent询问连麦嘉宾具体业务类型",
                    "trigger_condition": "agent_action in ['Request_Slot']",
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_goal_matched": {
                    "description": "【抖音-开直播】业务类型与时段核准完成，用户确认办理",
                    "trigger_condition": "agent_slots_all_matched and agent_action in ['Confirm_Slot', 'Inform_Slot', 'Acknowledge']",
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": goal_match_reply
                }
            }
        else:
            reaction_matrix = {
                "on_slot_error": {
                    "description": "Agent提参错误，用户指正",
                    "trigger_condition": "agent_slots_mismatch",
                    "monitored_slots": [],
                    "user_action_types": ["Revise_Intent_Request"],
                    "simulator_reply": "参数不对，请重新核实。"
                },
                "on_agent_inquiry": {
                    "description": "Agent询问缺失参数，用户提供",
                    "trigger_condition": "agent_action == 'Request_Slot'",
                    "monitored_slots": [],
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": f"按规格{res}和时延≤{rtt}办理。"
                },
                "on_slot_missing": {
                    "description": "Agent遗漏必要参数",
                    "trigger_condition": "agent_slot_missing",
                    "monitored_slots": [],
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": "请核对时长和完整保障指标。"
                },
                "on_goal_matched": {
                    "description": "参数对齐闭环",
                    "trigger_condition": "agent_slots_all_matched",
                    "monitored_slots": [],
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": "好的，规格时间都对了，确认按此开通。"
                }
            }

        turn_level_gt = []
        for i, node in enumerate(tree):
            item = {
                "turn": node["turn"],
                "speaker": node["speaker"],
                "simulator_user_prompt": node.get("simulator_user_prompt", ""),
                "expected_agent_response": node.get("expected_agent_response", node.get("expected_agent_correction", "")),
                "expected_agent_correction": node.get("expected_agent_correction", ""),
                "expected_agent_action_types": node.get("agent_action_types", []),
                "expected_slots_gt": node.get("expected_slots_gt", {}),
                "intents_status": {
                    tint["intent_id"]: tint["status"]
                    for tint in (full_slow_seq[i].get("turn_intents", []) if i < len(full_slow_seq) else [])
                }
            }
            if "baseline_agent_flawed_response" in node:
                item["baseline_agent_flawed_response"] = node["baseline_agent_flawed_response"]
            if "baseline_flawed_action_types" in node:
                item["baseline_flawed_action_types"] = node["baseline_flawed_action_types"]
            if "baseline_flawed_slots" in node:
                item["baseline_flawed_slots"] = node["baseline_flawed_slots"]
            if "delta_from_gt" in node:
                item["delta_from_gt"] = node["delta_from_gt"]
            item["is_terminal"] = (i == len(tree) - 1)
            turn_level_gt.append(item)

        contract = {
            "version": "1.0",
            "contract_name": "DynamicGoalDeltaReactionContract",
            "scenario_type": scenario_type,
            "target_ground_truth": target_gt,
            "turn_level_ground_truth": turn_level_gt,
            "termination_conditions": {
                "max_turns": slow_rounds + 1,
                "required_status": "resolved",
                "early_stop_on_match": True
            },
            "delta_reaction_matrix": reaction_matrix,
            "evaluator_prompt_template": (
                "你作为通信网络保障评测环境中的用户模拟器（User Simulator）。"
                "每轮接收'联接'Agent输出的意图保障单提参结果与话术，对比 target_ground_truth 与 turn_level_ground_truth 计算参数差分（Delta）。"
                "若存在参数错误或越权修改，触发 on_slot_error 并发出包含明确目标真值槽位的纠偏提示；"
                "若'联接'Agent发起槽位追问，触发 on_agent_inquiry 提供真值槽位；"
                "若'联接'Agent遗漏关键槽位，触发 on_slot_missing 提醒核验；"
                "若所有参数均已正确命中且 Agent 提请确认，触发 on_goal_matched 确认闭环并收尾。"
            )
        }

        return {
            "learning_source_session": learning_source_session,
            "experience_id": exp_id,
            "rule_title": rule_title,
            "interactive_eval_contract": contract,
            "fast_path": {
                "round_count": fast_rounds,
                "closure_path": "fast_experience_closed_loop",
                "trigger_condition": fast_cond,
                "resolved_turn": fast_rounds,
                "key_params_source": {"source_type": "Experience", "source_ref": exp_id}
            },
            "slow_path": {
                "round_count": slow_rounds,
                "closure_path": "clarification_after_correction",
                "trigger_condition": slow_cond,
                "resolved_turn": slow_rounds,
                "redundant_rounds": slow_rounds - fast_rounds,
                "branch_decision_gate": gate,
                "interactive_eval_contract": contract,
                "turn_level_ground_truth": turn_level_gt,
                "simulator_dialogue_tree": tree,
                "full_slow_event_sequence": full_slow_seq
            }
        }

    @classmethod
    def _assemble_t2_4(cls, sid, uid, ref_time, tid, role, b_type, env, act, app, srv, res, rtt, start, end, dur, events, snap, mems, gold, second_source=None, experience_citation=None, base_end=None, base_dur=None, start2=None, end2=None, dur2=None, learning_source_session=None):
        """T2-4: 经验记忆开播前私下对词试机位应用选择会话 (2 轮 / 1 意图: 微信-视频通话)"""
        exp_c = experience_citation or {}
        exp_id = exp_c.get("experience_id") or "EXP_MULTI_INTENT_PARTITION_01"
        app = "微信"
        srv = "视频通话"

        sig = f"T2-4|{len(events)}|1|I1:{app}/{srv}/1/multi_intent_experience/resolved|none"

        intents = [
            {
                "intent_id": "I1",
                "status": "resolved",
                "closure_path": "multi_intent_experience",
                "expression_level": 1,
                "intent": f"{app}{srv}保障",
                "params": {
                    "application_name": {"value": app, "source_type": "Experience", "source_ref": exp_id},
                    "service_name": {"value": srv, "source_type": "Experience", "source_ref": exp_id},
                    "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}},
                    "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}},
                    "timestamp": {
                        "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                        "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                        "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"},
                    },
                },
            }
        ]

        slot_updates = [
            {
                "intent_id": "I1",
                "turn_updates": [
                    {
                        "turn": 1,
                        "params": {
                            "application_name": {"value": app, "source_type": "Experience", "source_ref": exp_id},
                            "service_name": {"value": srv, "source_type": "Experience", "source_ref": exp_id},
                            "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}},
                            "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}},
                            "timestamp": {
                                "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                                "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                                "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"},
                            },
                        },
                    },
                    {
                        "turn": 2,
                        "params": {},
                    },
                ],
            }
        ]

        if events and len(events) >= 2:
            events[0]["requested_params"] = []
            events[0]["turn_intents"] = [
                {
                    "intent_id": "I1",
                    "status": "in_progress",
                    "closure_path": "multi_intent_experience",
                    "expression_level": 1,
                    "intent": f"{app}{srv}保障",
                    "params": intents[0]["params"],
                }
            ]
            events[0]["experience_citation"] = exp_c
            events[1]["requested_params"] = []
            events[1]["turn_intents"] = intents
        elif events and len(events) == 1:
            events[0]["requested_params"] = []
            events[0]["turn_intents"] = intents
            events[0]["experience_citation"] = exp_c

        u_prompt = events[0]["user"]["utterance"] if events and "user" in events[0] else ""
        branching_info = cls._build_experience_branching(
            scenario_type="multi_intent_partition",
            exp_id=exp_id,
            rule_title=exp_c.get("title") or "直播前私下跟搭档对词与看镜头机位（使用微信视频通话而非抖音开直播）经验",
            learning_source_session=learning_source_session,
            user_prompt=u_prompt,
            ctx={
                "app": app, "srv": srv, "res": res, "rtt": rtt, "start": start, "end": end, "dur": dur
            }
        )

        return {
            "session_id": sid,
            "user_id": uid,
            "reference_time": ref_time,
            "session_meta": {
                "template_id": tid,
                "round_count": len(events),
                "intent_count": 1,
                "memory_role": role,
                "memory_tier": "experiential_memory",
                "skeleton_signature": sig,
                "scenario": {"environment": env, "blueprint_type": b_type, "memory_action": act},
                "experience_citation": exp_c,
                "experience_branching": branching_info,
            },
            "experience_citation": exp_c,
            "experience_branching": branching_info,
            "event_sequence": events,
            "intents": intents,
            "relations": [],
            "slot_updates": slot_updates,
        }

    @classmethod
    def _assemble_standard(cls, sid, uid, ref_time, tid, role, b_type, env, act, app, srv, res, rtt, start, end, dur, events, snap, mems, gold, round_count, small_memory_type=None, experience_citation=None, learning_source_session=None):
        closure_path = "direct"
        app_src, app_ref = "Turn", "U1"
        srv_src, srv_ref = "Turn", "U1"
        res_src, res_ref = "Turn", "U1"
        rtt_src, rtt_ref = "Turn", "U1"
        start_src, start_ref = "Turn", "U1"
        end_src, end_ref = "Turn", "U1"
        dur_src, dur_ref = "Context", "U1"

        exp_c = experience_citation or {}
        if exp_c.get("experience_id") == "EXP_CALENDAR_HOLIDAY_EXCEPTION_01" and b_type != "experience_learning":
            exp_id = exp_c["experience_id"]
            app_src, app_ref = "Turn", "U1"
            srv_src, srv_ref = "Turn", "U1"
            res_src, res_ref = "Turn", "U1"
            rtt_src, rtt_ref = "Turn", "U1"
            start_src, start_ref = "Experience", exp_id
            end_src, end_ref = "Experience", exp_id
            dur_src, dur_ref = "Turn", "U1"
            closure_path = "holiday_avoidance_deferral"
        elif b_type == "experience_learning":
            closure_path = "experience_crystallized"
            app_src, app_ref = "Turn", "U1"
            srv_src, srv_ref = "Turn", "U1"
            res_src, res_ref = "Turn", "U1"
            rtt_src, rtt_ref = "Turn", "U1"
            start_src, start_ref = "Turn", "U1"
            end_src, end_ref = "Turn", "U1"
            dur_src, dur_ref = "Turn", "U1"

        if b_type == "main":
            if role == "evidence_session":
                closure_path = "clarified"
                app_src, app_ref = "Turn", "U1"
                srv_src, srv_ref = "Turn", "U1"
                res_src, res_ref = "Turn", "U2"
                rtt_src, rtt_ref = "Turn", "U2"
            elif role in ["reinforcement_session", "reuse_session"]:
                # 会话开始前仍为 provisional 的隐式记忆只能作为历史候选使用。
                # 本轮确认完成后它才升级为 active，不能把 gold_after 的状态倒灌到 turn 1。
                mf_status_before = (snap.get("MF_001") or {}).get("status")
                if mf_status_before == "provisional":
                    closure_path = "history_filled"
                    source_type = "History"
                else:
                    closure_path = "memory_filled"
                    source_type = "Memory"
                app_src, app_ref = source_type, "MF_001"
                srv_src, srv_ref = source_type, "MF_001"
                res_src, res_ref = source_type, "MF_001"
                rtt_src, rtt_ref = source_type, "MF_001"
                start_src, start_ref = source_type, "MF_001"
                end_src, end_ref = source_type, "MF_001"
                dur_src, dur_ref = source_type, "MF_001"

        elif b_type == "sub_01":
            if role == "evidence_session":
                closure_path = "clarified"
                app_src, app_ref = "Turn", "U1"
                srv_src, srv_ref = "Turn", "U1"
                res_src, res_ref = "Turn", "U2"
                rtt_src, rtt_ref = "Turn", "U2"
            elif role in ["reinforcement_session", "reuse_session"]:
                closure_path = "memory_filled"
                app_src, app_ref = "Memory", "SUB_001"
                srv_src, srv_ref = "Memory", "SUB_001"
                res_src, res_ref = "Memory", "SUB_001"
                rtt_src, rtt_ref = "Memory", "SUB_001"
                start_src, start_ref = "Memory", "SUB_001"
                end_src, end_ref = "Context", "SUB_001"
                dur_src, dur_ref = "Memory", "SUB_001"

        elif b_type == "sub_02":
            if role == "evidence_session":
                closure_path = "clarified"
                app_src, app_ref = "Turn", "U1"
                srv_src, srv_ref = "Turn", "U1"
                res_src, res_ref = "Turn", "U2"
                rtt_src, rtt_ref = "Turn", "U2"
            elif role in ["reinforcement_session", "reuse_session"]:
                closure_path = "memory_filled"
                app_src, app_ref = "Memory", "SUB_002"
                srv_src, srv_ref = "Memory", "SUB_002"
                res_src, res_ref = "Memory", "SUB_002"
                rtt_src, rtt_ref = "Memory", "SUB_002"
                start_src, start_ref = "Memory", "SUB_002"
                end_src, end_ref = "Context", "SUB_002"
                dur_src, dur_ref = "Memory", "SUB_002"

        elif b_type in ["event_reuse", "main_recovery"]:
            closure_path = "memory_filled"
            app_src, app_ref = "Memory", "MF_001"
            srv_src, srv_ref = "Memory", "MF_001"
            res_src, res_ref = "Memory", "MF_001"
            rtt_src, rtt_ref = "Memory", "MF_001"
            start_src, start_ref = "Memory", "MF_001"
            end_src, end_ref = "Memory", "MF_001"
            dur_src, dur_ref = "Memory", "MF_001"

        # 复用会话仍需满足“应用＋业务”的最小表达。只有业务默认应用记忆可省略应用；
        # 应用别名通过记忆解析应用，但业务仍由本轮用户明确表达。
        if role in ["reinforcement_session", "reuse_session"] and b_type in ["main", "sub_01", "sub_02"]:
            is_provisional_main = b_type == "main" and (snap.get("MF_001") or {}).get("status") == "provisional"
            if not is_provisional_main:
                if small_memory_type == "service_default_app":
                    srv_src, srv_ref = "Turn", "U1"
                elif small_memory_type == "application_alias":
                    srv_src, srv_ref = "Turn", "U1"
                else:
                    app_src, app_ref = "Turn", "U1"
                    srv_src, srv_ref = "Turn", "U1"

        slot_updates_turn = []
        for t_idx in range(1, round_count + 1):
            if t_idx == 1:
                t_params = {
                    "application_name": {"value": app, "source_type": app_src, "source_ref": app_ref},
                    "service_name": {"value": srv, "source_type": srv_src, "source_ref": srv_ref},
                }
                if role == "evidence_session":
                    # 证据会话第 1 轮：用户仅明确开始时间（如“今晚8点”），结束时间与时长待第2轮澄清补充
                    t_params["timestamp"] = {
                        "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                    }
                else:
                    t_params["timestamp"] = {
                        "start_timestamp": {"value": start, "source_type": start_src, "source_ref": start_ref},
                        "end_timestamp": {"value": end, "source_type": end_src, "source_ref": end_ref},
                        "duration": {"value": dur, "source_type": dur_src, "source_ref": dur_ref},
                    }
                if role not in ["evidence_session", "correction_session"]:
                    t_params["resolution"] = {"min_value": {"value": res, "source_type": res_src, "source_ref": res_ref}}
                    t_params["rtt"] = {"max_value": {"value": rtt, "source_type": rtt_src, "source_ref": rtt_ref}}
                slot_updates_turn.append({"turn": 1, "params": t_params})
            elif t_idx == 2:
                t_params = {}
                if role in ["evidence_session", "correction_session"]:
                    t_params = {
                        "resolution": {"min_value": {"value": res, "source_type": res_src, "source_ref": res_ref}},
                        "rtt": {"max_value": {"value": rtt, "source_type": rtt_src, "source_ref": rtt_ref}},
                    }
                    if role == "evidence_session":
                        # 第 2 轮用户澄清补充结束时间与持续时长
                        t_params["timestamp"] = {
                            "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U2"},
                            "duration": {"value": dur, "source_type": "Turn", "source_ref": "U2"},
                        }
                slot_updates_turn.append({"turn": 2, "params": t_params})
            elif t_idx >= 3:
                slot_updates_turn.append({"turn": t_idx, "params": {}})

        sig = f"{tid}|{len(events)}|1|I1:{app}/{srv}/1/{closure_path}/resolved|none"
        if role == "evidence_session":
            end_src, end_ref = "Turn", "U2"
            dur_src, dur_ref = "Turn", "U2"
        intents = [
            {
                "intent_id": "I1",
                "status": "resolved",
                "closure_path": closure_path,
                "expression_level": 1,
                "intent": f"{app}{srv}保障",
                "params": {
                    "application_name": {"value": app, "source_type": app_src, "source_ref": app_ref},
                    "service_name": {"value": srv, "source_type": srv_src, "source_ref": srv_ref},
                    "resolution": {"min_value": {"value": res, "source_type": res_src, "source_ref": res_ref}},
                    "rtt": {"max_value": {"value": rtt, "source_type": rtt_src, "source_ref": rtt_ref}},
                    "timestamp": {
                        "start_timestamp": {"value": start, "source_type": start_src, "source_ref": start_ref},
                        "end_timestamp": {"value": end, "source_type": end_src, "source_ref": end_ref},
                        "duration": {"value": dur, "source_type": dur_src, "source_ref": dur_ref},
                    },
                },
            }
        ]

        if events and len(events) == 1:
            events[0]["requested_params"] = []
            events[0]["turn_intents"] = intents
        elif events and len(events) >= 2:
            if role == "evidence_session":
                events[0]["requested_params"] = ["resolution", "rtt", "duration"]
                events[0]["turn_intents"] = [
                    {
                        "intent_id": "I1",
                        "status": "in_progress",
                        "closure_path": "clarify",
                        "expression_level": 1,
                        "intent": f"{app}{srv}保障",
                        "params": {
                            "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                            "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                            "timestamp": {
                                "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                            },
                        },
                    }
                ]
                if len(events) >= 3:
                    events[1]["requested_params"] = []
                    events[1]["turn_intents"] = [
                        {
                            "intent_id": "I1",
                            "status": "in_progress",
                            "closure_path": "clarify",
                            "expression_level": 1,
                            "intent": f"{app}{srv}保障",
                            "params": {
                                "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                                "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                                "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U2"}},
                                "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U2"}},
                                "timestamp": {
                                    "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                                    "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U2"},
                                    "duration": {"value": dur, "source_type": "Turn", "source_ref": "U2"},
                                },
                            },
                        }
                    ]
                    events[2]["requested_params"] = []
                    events[2]["turn_intents"] = intents
                else:
                    events[1]["requested_params"] = []
                    events[1]["turn_intents"] = intents
            else:
                events[0]["requested_params"] = []
                events[0]["turn_intents"] = [
                    {
                        "intent_id": "I1",
                        "status": "in_progress",
                        "closure_path": closure_path,
                        "expression_level": 1,
                        "intent": f"{app}{srv}保障",
                        "params": {
                            "application_name": {"value": app, "source_type": app_src, "source_ref": app_ref},
                            "service_name": {"value": srv, "source_type": srv_src, "source_ref": srv_ref},
                            "resolution": {"min_value": {"value": res, "source_type": res_src, "source_ref": res_ref}},
                            "rtt": {"max_value": {"value": rtt, "source_type": rtt_src, "source_ref": rtt_ref}},
                            "timestamp": {
                                "start_timestamp": {"value": start, "source_type": start_src, "source_ref": start_ref},
                                "end_timestamp": {"value": end, "source_type": end_src, "source_ref": end_ref},
                                "duration": {"value": dur, "source_type": dur_src, "source_ref": dur_ref},
                            },
                        },
                    }
                ]
                if exp_c:
                    events[0]["experience_citation"] = exp_c
                if len(events) >= 3:
                    events[1]["requested_params"] = []
                    events[1]["turn_intents"] = [
                        {
                            "intent_id": "I1",
                            "status": "in_progress",
                            "closure_path": closure_path,
                            "expression_level": 1,
                            "intent": f"{app}{srv}保障",
                            "params": {
                                "application_name": {"value": app, "source_type": app_src, "source_ref": app_ref},
                                "service_name": {"value": srv, "source_type": srv_src, "source_ref": srv_ref},
                                "resolution": {"min_value": {"value": res, "source_type": res_src, "source_ref": res_ref}},
                                "rtt": {"max_value": {"value": rtt, "source_type": rtt_src, "source_ref": rtt_ref}},
                                "timestamp": {
                                    "start_timestamp": {"value": start, "source_type": start_src, "source_ref": start_ref},
                                    "end_timestamp": {"value": end, "source_type": end_src, "source_ref": end_ref},
                                    "duration": {"value": dur, "source_type": dur_src, "source_ref": dur_ref},
                                },
                            },
                        }
                    ]
                    events[2]["requested_params"] = []
                    events[2]["turn_intents"] = intents
                else:
                    events[1]["requested_params"] = []
                    events[1]["turn_intents"] = intents

        ret = {
            "session_id": sid,
            "user_id": uid,
            "reference_time": ref_time,
            "session_meta": {
                "template_id": tid,
                "round_count": len(events),
                "intent_count": 1,
                "memory_role": role,
                "skeleton_signature": sig,
                "scenario": {"environment": env, "blueprint_type": b_type, "memory_action": act},
            },
            "event_sequence": events,
            "intents": intents,
            "relations": [],
            "slot_updates": [{"intent_id": "I1", "turn_updates": slot_updates_turn}],
        }
        if exp_c:
            exp_id = exp_c.get("experience_id")
            ret["experience_citation"] = exp_c
            ret["session_meta"]["experience_citation"] = exp_c
            if b_type != "experience_learning" and exp_id == "EXP_CALENDAR_HOLIDAY_EXCEPTION_01":
                u_prompt = events[0]["user"]["utterance"] if events and "user" in events[0] else ""
                branching_info = cls._build_experience_branching(
                    scenario_type="holiday_exception",
                    exp_id=exp_id,
                    rule_title=exp_c.get("title") or "周期例行排期遇法定节假日自动顺延经验",
                    learning_source_session=learning_source_session,
                    user_prompt=u_prompt,
                    ctx={"app": app, "srv": srv, "res": res, "rtt": rtt, "start": start, "end": end, "dur": dur}
                )
                ret["experience_branching"] = branching_info
                ret["session_meta"]["experience_branching"] = branching_info
        return ret

    @classmethod
    def _assemble_t2_6(cls, sid, uid, ref_time, tid, role, b_type, env, act, app, srv, res, rtt, start, end, dur, events, snap, mems, gold, working_memory_pointer=None, experience_citation=None, learning_source_session=None):
        """T2-6: 工作记忆历史意图保障单跨期复用 (2 轮 / 3 轮消歧 / 经验记忆质量特征消歧)"""
        exp_c = experience_citation or {}
        exp_id = exp_c.get("experience_id")
        is_exp = bool(exp_c and exp_id == "EXP_ORDER_QUALITY_DISAMBIGUATION_01")

        wm_ptr = working_memory_pointer or {}
        rec_id = wm_ptr.get("target_record_id") or "REC_PRIOR"
        is_disambig = wm_ptr.get("is_disambiguation", False) or len(events) == 3

        if is_exp:
            closure_path = "quality_disambiguated_reuse"
            app_src, app_ref = "Turn", "U1"
            srv_src, srv_ref = "Turn", "U1"
            res_src, res_ref = "Turn", "U1"
            rtt_src, rtt_ref = "Turn", "U1"
            ts_ref = "U1"
            end_src, end_ref = "Experience", exp_id
            dur_src, dur_ref = "Experience", exp_id
        else:
            closure_path = "working_record_reuse"
            app_src, app_ref = "WorkingRecord", rec_id
            srv_src, srv_ref = "WorkingRecord", rec_id
            res_src, res_ref = "WorkingRecord", rec_id
            rtt_src, rtt_ref = "WorkingRecord", rec_id
            ts_ref = "U1" if is_disambig else "U2"
            end_src, end_ref = "Turn", ts_ref
            dur_src, dur_ref = "Turn", ts_ref

        sig = f"T2-6|{len(events)}|1|I1:{app}/{srv}/1/{closure_path}/resolved|none"

        intents = [
            {
                "intent_id": "I1",
                "status": "resolved",
                "closure_path": closure_path,
                "expression_level": 1,
                "intent": f"{app}{srv}保障",
                "params": {
                    "application_name": {"value": app, "source_type": app_src, "source_ref": app_ref},
                    "service_name": {"value": srv, "source_type": srv_src, "source_ref": srv_ref},
                    "resolution": {"min_value": {"value": res, "source_type": res_src, "source_ref": res_ref}},
                    "rtt": {"max_value": {"value": rtt, "source_type": rtt_src, "source_ref": rtt_ref}},
                    "timestamp": {
                        "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": ts_ref},
                        "end_timestamp": {"value": end, "source_type": end_src, "source_ref": end_ref},
                        "duration": {"value": dur, "source_type": dur_src, "source_ref": dur_ref},
                    },
                },
            }
        ]

        if is_exp:
            slot_updates = [
                {
                    "intent_id": "I1",
                    "turn_updates": [
                        {
                            "turn": 1,
                            "params": {
                                "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                                "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                                "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}},
                                "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}},
                                "timestamp": {
                                    "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                                    "end_timestamp": {"value": end, "source_type": "Experience", "source_ref": exp_id},
                                    "duration": {"value": dur, "source_type": "Experience", "source_ref": exp_id},
                                },
                            },
                        },
                        {
                            "turn": 2,
                            "params": {},
                        },
                    ],
                }
            ]
            if events and len(events) >= 2:
                events[0]["requested_params"] = []
                events[0]["turn_intents"] = [
                    {
                        "intent_id": "I1",
                        "status": "in_progress",
                        "closure_path": closure_path,
                        "expression_level": 1,
                        "intent": f"{app}{srv}保障",
                        "params": intents[0]["params"],
                    }
                ]
                events[0]["working_memory_pointer"] = wm_ptr
                events[0]["experience_citation"] = exp_c
                events[1]["requested_params"] = []
                events[1]["turn_intents"] = intents
            elif events and len(events) == 1:
                events[0]["requested_params"] = []
                events[0]["turn_intents"] = intents
                events[0]["working_memory_pointer"] = wm_ptr
                events[0]["experience_citation"] = exp_c
        elif is_disambig and len(events) >= 3:
            slot_updates = [
                {
                    "intent_id": "I1",
                    "turn_updates": [
                        {
                            "turn": 1,
                            "params": {
                                "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                                "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                                "timestamp": {
                                    "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                                    "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                                    "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"},
                                },
                            },
                        },
                        {
                            "turn": 2,
                            "params": {
                                "application_name": {"value": app, "source_type": "WorkingRecord", "source_ref": rec_id},
                                "service_name": {"value": srv, "source_type": "WorkingRecord", "source_ref": rec_id},
                                "resolution": {"min_value": {"value": res, "source_type": "WorkingRecord", "source_ref": rec_id}},
                                "rtt": {"max_value": {"value": rtt, "source_type": "WorkingRecord", "source_ref": rec_id}},
                            },
                        },
                        {
                            "turn": 3,
                            "params": {},
                        },
                    ],
                }
            ]
            events[0]["requested_params"] = ["target_record_id"]
            events[0]["turn_intents"] = [
                {
                    "intent_id": "I1",
                    "status": "in_progress",
                    "closure_path": "working_record_disambig",
                    "expression_level": 1,
                    "intent": f"{app}{srv}保障",
                    "params": {
                        "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                        "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                        "timestamp": {
                            "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                            "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"},
                        },
                    },
                }
            ]
            events[0]["working_memory_pointer"] = wm_ptr
            events[1]["requested_params"] = []
            events[1]["turn_intents"] = intents
            events[2]["requested_params"] = []
            events[2]["turn_intents"] = intents
        else:
            slot_updates = [
                {
                    "intent_id": "I1",
                    "turn_updates": [
                        {
                            "turn": 1,
                            "params": {
                                "application_name": {"value": app, "source_type": "WorkingRecord", "source_ref": rec_id},
                                "service_name": {"value": srv, "source_type": "WorkingRecord", "source_ref": rec_id},
                                "resolution": {"min_value": {"value": res, "source_type": "WorkingRecord", "source_ref": rec_id}},
                                "rtt": {"max_value": {"value": rtt, "source_type": "WorkingRecord", "source_ref": rec_id}},
                            },
                        },
                        {
                            "turn": 2,
                            "params": {
                                "timestamp": {
                                    "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U2"},
                                    "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U2"},
                                    "duration": {"value": dur, "source_type": "Turn", "source_ref": "U2"},
                                },
                            },
                        },
                    ],
                }
            ]

            if events and len(events) >= 2:
                events[0]["requested_params"] = ["timestamp"]
                events[0]["turn_intents"] = [
                    {
                        "intent_id": "I1",
                        "status": "in_progress",
                        "closure_path": "working_record_reuse",
                        "expression_level": 1,
                        "intent": f"{app}{srv}保障",
                        "params": {
                            "application_name": {"value": app, "source_type": "WorkingRecord", "source_ref": rec_id},
                            "service_name": {"value": srv, "source_type": "WorkingRecord", "source_ref": rec_id},
                            "resolution": {"min_value": {"value": res, "source_type": "WorkingRecord", "source_ref": rec_id}},
                            "rtt": {"max_value": {"value": rtt, "source_type": "WorkingRecord", "source_ref": rec_id}},
                        },
                    }
                ]
                events[0]["working_memory_pointer"] = wm_ptr
                events[1]["requested_params"] = []
                events[1]["turn_intents"] = intents
            elif events and len(events) == 1:
                events[0]["requested_params"] = []
                events[0]["turn_intents"] = intents
                events[0]["working_memory_pointer"] = wm_ptr

        ret = {
            "session_id": sid,
            "user_id": uid,
            "reference_time": ref_time,
            "session_meta": {
                "template_id": tid,
                "round_count": len(events),
                "intent_count": 1,
                "memory_role": role,
                "skeleton_signature": sig,
                "scenario": {"environment": env, "blueprint_type": b_type, "memory_action": act},
                "working_memory_pointer": wm_ptr,
            },
            "working_memory_pointer": wm_ptr,
            "event_sequence": events,
            "intents": intents,
            "relations": [],
            "slot_updates": slot_updates,
        }
        if is_exp:
            ret["experience_citation"] = exp_c
            ret["session_meta"]["experience_citation"] = exp_c
            u_prompt = events[0]["user"]["utterance"] if events and "user" in events[0] else ""
            branching_info = cls._build_experience_branching(
                scenario_type="quality_disambiguation",
                exp_id=exp_id,
                rule_title=exp_c.get("title") or "历史多笔意图保障单高规格优选消歧经验",
                learning_source_session=learning_source_session,
                user_prompt=u_prompt,
                ctx={"app": app, "srv": srv, "res": res, "rtt": rtt, "start": start, "end": end, "dur": dur}
            )
            ret["experience_branching"] = branching_info
            ret["session_meta"]["experience_branching"] = branching_info
        return ret

    @classmethod
    def _assemble_t2_7(cls, sid, uid, ref_time, tid, role, b_type, env, act, app, srv, res, rtt, start, end, dur, events, snap, mems, gold, working_memory_pointer=None):
        """T2-7: 工作记忆历史单据变更改期 (2 轮 / 1 意图)"""
        wm_ptr = working_memory_pointer or {}
        rec_id = wm_ptr.get("target_record_id") or "REC_PRIOR"
        sig = f"T2-7|{len(events)}|1|I1:{app}/{srv}/1/working_record_reschedule/resolved|none"

        intents = [
            {
                "intent_id": "I1",
                "status": "resolved",
                "closure_path": "working_record_reschedule",
                "expression_level": 1,
                "intent": f"{app}{srv}保障",
                "params": {
                    "application_name": {"value": app, "source_type": "WorkingRecord", "source_ref": rec_id},
                    "service_name": {"value": srv, "source_type": "WorkingRecord", "source_ref": rec_id},
                    "resolution": {"min_value": {"value": res, "source_type": "WorkingRecord", "source_ref": rec_id}},
                    "rtt": {"max_value": {"value": rtt, "source_type": "WorkingRecord", "source_ref": rec_id}},
                    "timestamp": {
                        "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                        "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                        "duration": {"value": dur, "source_type": "WorkingRecord", "source_ref": rec_id},
                    },
                },
            }
        ]

        slot_updates = [
            {
                "intent_id": "I1",
                "turn_updates": [
                    {
                        "turn": 1,
                        "params": {
                            "application_name": {"value": app, "source_type": "WorkingRecord", "source_ref": rec_id},
                            "service_name": {"value": srv, "source_type": "WorkingRecord", "source_ref": rec_id},
                            "resolution": {"min_value": {"value": res, "source_type": "WorkingRecord", "source_ref": rec_id}},
                            "rtt": {"max_value": {"value": rtt, "source_type": "WorkingRecord", "source_ref": rec_id}},
                            "timestamp": {
                                "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                                "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                                "duration": {"value": dur, "source_type": "WorkingRecord", "source_ref": rec_id},
                            },
                        },
                    },
                    {
                        "turn": 2,
                        "params": {},
                    },
                ],
            }
        ]

        if events and len(events) >= 2:
            events[0]["requested_params"] = []
            events[0]["turn_intents"] = [
                {
                    "intent_id": "I1",
                    "status": "in_progress",
                    "closure_path": "working_record_reschedule",
                    "expression_level": 1,
                    "intent": f"{app}{srv}保障",
                    "params": intents[0]["params"],
                }
            ]
            events[0]["working_memory_pointer"] = wm_ptr
            events[1]["requested_params"] = []
            events[1]["turn_intents"] = intents
        elif events and len(events) == 1:
            events[0]["requested_params"] = []
            events[0]["turn_intents"] = intents
            events[0]["working_memory_pointer"] = wm_ptr

        return {
            "session_id": sid,
            "user_id": uid,
            "reference_time": ref_time,
            "session_meta": {
                "template_id": tid,
                "round_count": len(events),
                "intent_count": 1,
                "memory_role": role,
                "skeleton_signature": sig,
                "scenario": {"environment": env, "blueprint_type": b_type, "memory_action": act},
                "working_memory_pointer": wm_ptr,
            },
            "working_memory_pointer": wm_ptr,
            "event_sequence": events,
            "intents": intents,
            "relations": [],
            "slot_updates": slot_updates,
        }

    @classmethod
    def _assemble_t2_8(cls, sid, uid, ref_time, tid, role, b_type, env, act, events, snap, mems, gold, working_memory_query=None):
        """T2-8: 工作记忆历史记录对账核查 (1 轮 / 1 意图)"""
        wm_qry = working_memory_query or {}
        sig = f"T2-8|{len(events)}|1|I1:历史意图保障单流水对账核查/0/direct/resolved|none"

        intents = [
            {
                "intent_id": "I1",
                "status": "resolved",
                "closure_path": "direct",
                "expression_level": 0,
                "intent": "历史意图保障单流水对账核查",
                "params": {},
            }
        ]

        if events and len(events) >= 1:
            events[0]["requested_params"] = []
            events[0]["turn_intents"] = intents
            events[0]["working_memory_query"] = wm_qry

        return {
            "session_id": sid,
            "user_id": uid,
            "reference_time": ref_time,
            "session_meta": {
                "template_id": tid,
                "round_count": len(events),
                "intent_count": 1,
                "memory_role": role,
                "skeleton_signature": sig,
                "scenario": {"environment": env, "blueprint_type": b_type, "memory_action": act},
                "working_memory_query": wm_qry,
            },
            "working_memory_query": wm_qry,
            "event_sequence": events,
            "intents": intents,
            "relations": [],
            "slot_updates": [],
        }

    @classmethod
    def _assemble_t2_9(cls, sid, uid, ref_time, tid, role, b_type, env, act, app, srv, res, rtt, start, end, dur, events, snap, mems, gold, experience_citation=None, learning_source_session=None):
        """T2-9: 经验记忆 ReasoningBank 主动经验提议 (2 轮 / 3 轮协商 / 负反例边界)"""
        exp_c = experience_citation or {}
        exp_id = exp_c.get("experience_id") or "EXP_PREWARM_BUFFER_01"
        is_prewarm = (exp_id == "EXP_PREWARM_BUFFER_01")
        is_counter = exp_c.get("counterexample_applied", False) or exp_c.get("strategy_type") == "negative_counterexample"

        if is_prewarm:
            closure_path = "proactive_prewarm"
            sig = f"T2-9|{len(events)}|1|I1:{app}/{srv}/1/{closure_path}/resolved|none"
            intents = [
                {
                    "intent_id": "I1",
                    "status": "resolved",
                    "closure_path": closure_path,
                    "expression_level": 1,
                    "intent": f"{app}{srv}保障",
                    "params": {
                        "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                        "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                        "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}},
                        "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}},
                        "timestamp": {
                            "start_timestamp": {"value": start, "source_type": "Experience", "source_ref": exp_id},
                            "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                            "duration": {"value": dur, "source_type": "Experience", "source_ref": exp_id},
                        },
                    },
                }
            ]
            slot_updates = [
                {
                    "intent_id": "I1",
                    "turn_updates": [
                        {
                            "turn": 1,
                            "params": {
                                "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                                "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                                "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}},
                                "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}},
                                "timestamp": {
                                    "start_timestamp": {"value": start, "source_type": "Experience", "source_ref": exp_id},
                                    "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                                    "duration": {"value": dur, "source_type": "Experience", "source_ref": exp_id},
                                },
                            },
                        },
                        {
                            "turn": 2,
                            "params": {},
                        },
                    ],
                }
            ]
            if events and len(events) >= 2:
                events[0]["requested_params"] = []
                events[0]["turn_intents"] = [
                    {
                        "intent_id": "I1",
                        "status": "in_progress",
                        "closure_path": closure_path,
                        "expression_level": 1,
                        "intent": f"{app}{srv}保障",
                        "params": intents[0]["params"],
                    }
                ]
                events[0]["experience_citation"] = exp_c
                events[1]["requested_params"] = []
                events[1]["turn_intents"] = intents
            elif events and len(events) == 1:
                events[0]["requested_params"] = []
                events[0]["turn_intents"] = intents
                events[0]["experience_citation"] = exp_c

            u_prompt = events[0]["user"]["utterance"] if events and "user" in events[0] else ""
            branching_info = cls._build_experience_branching(
                scenario_type="prewarm_buffer",
                exp_id=exp_id,
                rule_title=exp_c.get("title") or "重大活动与大型现场提前30分钟网络预热起保经验",
                learning_source_session=learning_source_session,
                user_prompt=u_prompt,
                ctx={"app": app, "srv": srv, "res": res, "rtt": rtt, "start": start, "end": end, "dur": dur}
            )
        else:
            sig = f"T2-9|{len(events)}|1|I1:{app}/{srv}/1/proactive_experience/resolved|none"
            res_src = "Turn" if is_counter else "Experience"
            res_ref = "U1" if is_counter else exp_id
            rtt_src = "Turn" if is_counter else "Experience"
            rtt_ref = "U1" if is_counter else exp_id

            intents = [
                {
                    "intent_id": "I1",
                    "status": "resolved",
                    "closure_path": "proactive_experience",
                    "expression_level": 1,
                    "intent": f"{app}{srv}保障",
                    "params": {
                        "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                        "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                        "resolution": {"min_value": {"value": res, "source_type": res_src, "source_ref": res_ref}},
                        "rtt": {"max_value": {"value": rtt, "source_type": rtt_src, "source_ref": rtt_ref}},
                        "timestamp": {
                            "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                            "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"},
                        },
                    },
                }
            ]

            if is_counter:
                slot_updates = [
                    {
                        "intent_id": "I1",
                        "turn_updates": [
                            {
                                "turn": 1,
                                "params": {
                                    "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                                    "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                                    "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}},
                                    "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}},
                                    "timestamp": {
                                        "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                                        "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                                        "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"},
                                    },
                                },
                            },
                            {
                                "turn": 2,
                                "params": {},
                            },
                        ],
                    }
                ]
                if events and len(events) >= 2:
                    events[0]["requested_params"] = []
                    events[0]["turn_intents"] = [
                        {
                            "intent_id": "I1",
                            "status": "in_progress",
                            "closure_path": "proactive_experience",
                            "expression_level": 1,
                            "intent": f"{app}{srv}保障",
                            "params": intents[0]["params"],
                        }
                    ]
                    events[0]["experience_citation"] = exp_c
                    events[1]["requested_params"] = []
                    events[1]["turn_intents"] = intents
            elif len(events) >= 3:
                slot_updates = [
                    {
                        "intent_id": "I1",
                        "turn_updates": [
                            {
                                "turn": 1,
                                "params": {
                                    "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                                    "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                                    "resolution": {"min_value": {"value": "1080p", "source_type": "Turn", "source_ref": "U1"}},
                                    "timestamp": {
                                        "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                                        "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                                        "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"},
                                    },
                                },
                            },
                            {
                                "turn": 2,
                                "params": {
                                    "resolution": {"min_value": {"value": res, "source_type": "Experience", "source_ref": exp_id}},
                                    "rtt": {"max_value": {"value": rtt, "source_type": "Experience", "source_ref": exp_id}},
                                },
                            },
                            {
                                "turn": 3,
                                "params": {},
                            },
                        ],
                    }
                ]
                events[0]["requested_params"] = []
                events[0]["turn_intents"] = [
                    {
                        "intent_id": "I1",
                        "status": "in_progress",
                        "closure_path": "proactive_experience",
                        "expression_level": 1,
                        "intent": f"{app}{srv}保障",
                        "params": {
                            "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                            "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                            "resolution": {"min_value": {"value": "1080p", "source_type": "Turn", "source_ref": "U1"}},
                            "timestamp": {
                                "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                                "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                                "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"},
                            },
                        },
                    }
                ]
                events[0]["experience_citation"] = exp_c
                events[1]["requested_params"] = []
                events[1]["turn_intents"] = intents
                events[2]["requested_params"] = []
                events[2]["turn_intents"] = intents
            else:
                slot_updates = [
                    {
                        "intent_id": "I1",
                        "turn_updates": [
                            {
                                "turn": 1,
                                "params": {
                                    "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                                    "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                                    "timestamp": {
                                        "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                                        "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                                        "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"},
                                    },
                                },
                            },
                            {
                                "turn": 2,
                                "params": {
                                    "resolution": {"min_value": {"value": res, "source_type": "Experience", "source_ref": exp_id}},
                                    "rtt": {"max_value": {"value": rtt, "source_type": "Experience", "source_ref": exp_id}},
                                },
                            },
                        ],
                    }
                ]
                if events and len(events) >= 2:
                    events[0]["requested_params"] = []
                    events[0]["turn_intents"] = [
                        {
                            "intent_id": "I1",
                            "status": "in_progress",
                            "closure_path": "proactive_experience",
                            "expression_level": 1,
                            "intent": f"{app}{srv}保障",
                            "params": {
                                "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                                "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                                "timestamp": {
                                    "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                                    "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                                    "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"},
                                },
                            },
                        }
                    ]
                    events[0]["experience_citation"] = exp_c
                    events[1]["requested_params"] = []
                    events[1]["turn_intents"] = intents
                elif events and len(events) == 1:
                    events[0]["requested_params"] = []
                    events[0]["turn_intents"] = intents
                    events[0]["experience_citation"] = exp_c

            u_prompt = events[0]["user"]["utterance"] if events and "user" in events[0] else ""
            branching_info = cls._build_experience_branching(
                scenario_type="prewarm_buffer",
                exp_id=exp_id,
                rule_title=exp_c.get("title") or "大型活动起保前置预热试机经验",
                learning_source_session=learning_source_session,
                user_prompt=u_prompt,
                ctx={"app": app, "srv": srv, "res": res, "rtt": rtt, "start": start, "end": end, "dur": dur}
            )

        return {
            "session_id": sid,
            "user_id": uid,
            "reference_time": ref_time,
            "session_meta": {
                "template_id": tid,
                "round_count": len(events),
                "intent_count": 1,
                "memory_role": role,
                "skeleton_signature": sig,
                "scenario": {"environment": env, "blueprint_type": b_type, "memory_action": act},
                "experience_citation": exp_c,
                "experience_branching": branching_info,
            },
            "experience_citation": exp_c,
            "experience_branching": branching_info,
            "event_sequence": events,
            "intents": intents,
            "relations": [],
            "slot_updates": slot_updates,
        }

    @classmethod
    def _assemble_t2_10(cls, sid, uid, ref_time, tid, role, b_type, env, act, app, srv, res, rtt, start, end, dur, events, snap, mems, gold, experience_citation=None, learning_source_session=None):
        """T2-10: 经验记忆 ReasoningBank 经验回溯与边界防线 (2 轮 / 1 意图 / 新旧意图保障单撞车让路接管)"""
        exp_c = experience_citation or {}
        exp_id = exp_c.get("experience_id") or "EXP_OVERLAPPING_ORDER_RESOLUTION_01"
        is_overlap = (exp_id == "EXP_OVERLAPPING_ORDER_RESOLUTION_01")

        if is_overlap:
            app = "抖音"
            srv = "开直播"
            closure_path = "overlapping_order_resolution"
            sig = f"T2-10|{len(events)}|1|I1:{app}/{srv}/1/{closure_path}/resolved|none"
            start_src, start_ref = "Turn", "U1"
            end_src, end_ref = "Turn", "U1"
            dur_src, dur_ref = "Turn", "U1"
            res_src, res_ref = "Turn", "U1"
            rtt_src, rtt_ref = "Turn", "U1"

            intents = [
                {
                    "intent_id": "I1",
                    "status": "resolved",
                    "closure_path": closure_path,
                    "expression_level": 1,
                    "intent": f"{app}{srv}保障",
                    "params": {
                        "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                        "service_name": {"value": srv, "source_type": "Experience", "source_ref": exp_id},
                        "resolution": {"min_value": {"value": res, "source_type": res_src, "source_ref": res_ref}},
                        "rtt": {"max_value": {"value": rtt, "source_type": rtt_src, "source_ref": rtt_ref}},
                        "timestamp": {
                            "start_timestamp": {"value": start, "source_type": start_src, "source_ref": start_ref},
                            "end_timestamp": {"value": end, "source_type": end_src, "source_ref": end_ref},
                            "duration": {"value": dur, "source_type": dur_src, "source_ref": dur_ref},
                        },
                    },
                }
            ]

            slot_updates = [
                {
                    "intent_id": "I1",
                    "turn_updates": [
                        {
                            "turn": 1,
                            "params": {
                                "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                                "service_name": {"value": srv, "source_type": "Experience", "source_ref": exp_id},
                                "resolution": {"min_value": {"value": res, "source_type": res_src, "source_ref": res_ref}},
                                "rtt": {"max_value": {"value": rtt, "source_type": rtt_src, "source_ref": rtt_ref}},
                                "timestamp": {
                                    "start_timestamp": {"value": start, "source_type": start_src, "source_ref": start_ref},
                                    "end_timestamp": {"value": end, "source_type": end_src, "source_ref": end_ref},
                                    "duration": {"value": dur, "source_type": dur_src, "source_ref": dur_ref},
                                },
                            },
                        },
                        {
                            "turn": 2,
                            "params": {},
                        },
                    ],
                }
            ]

            if events and len(events) >= 2:
                events[0]["requested_params"] = []
                events[0]["turn_intents"] = [
                    {
                        "intent_id": "I1",
                        "status": "in_progress",
                        "closure_path": closure_path,
                        "expression_level": 1,
                        "intent": f"{app}{srv}保障",
                        "params": intents[0]["params"],
                    }
                ]
                events[0]["experience_citation"] = exp_c
                events[1]["requested_params"] = []
                events[1]["turn_intents"] = intents
            elif events and len(events) == 1:
                events[0]["requested_params"] = []
                events[0]["turn_intents"] = intents
                events[0]["experience_citation"] = exp_c

            u_prompt = events[0]["user"]["utterance"] if events and "user" in events[0] else ""
            branching_info = cls._build_experience_branching(
                scenario_type="overlapping_resolution",
                exp_id=exp_id,
                rule_title=exp_c.get("title") or "新旧意图保障单时段撞车无缝让路与时序重叠仲裁经验",
                learning_source_session=learning_source_session,
                user_prompt=u_prompt,
                ctx={"app": app, "srv": srv, "res": res, "rtt": rtt, "start": start, "end": end, "dur": dur}
            )
        else:
            sig = f"T2-10|{len(events)}|1|I1:{app}/{srv}/1/empirical_recall/resolved|none"

            intents = [
                {
                    "intent_id": "I1",
                    "status": "resolved",
                    "closure_path": "empirical_recall",
                    "expression_level": 1,
                    "intent": f"{app}{srv}保障",
                    "params": {
                        "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                        "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                        "resolution": {"min_value": {"value": res, "source_type": "Experience", "source_ref": exp_id}},
                        "rtt": {"max_value": {"value": rtt, "source_type": "Experience", "source_ref": exp_id}},
                        "timestamp": {
                            "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                            "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"},
                        },
                    },
                }
            ]

            slot_updates = [
                {
                    "intent_id": "I1",
                    "turn_updates": [
                        {
                            "turn": 1,
                            "params": {
                                "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                                "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                                "resolution": {"min_value": {"value": res, "source_type": "Experience", "source_ref": exp_id}},
                                "rtt": {"max_value": {"value": rtt, "source_type": "Experience", "source_ref": exp_id}},
                                "timestamp": {
                                    "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                                    "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                                    "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"},
                                },
                            },
                        },
                        {
                            "turn": 2,
                            "params": {},
                        },
                    ],
                }
            ]

            if events and len(events) >= 2:
                events[0]["requested_params"] = []
                events[0]["turn_intents"] = [
                    {
                        "intent_id": "I1",
                        "status": "in_progress",
                        "closure_path": "empirical_recall",
                        "expression_level": 1,
                        "intent": f"{app}{srv}保障",
                        "params": intents[0]["params"],
                    }
                ]
                events[0]["experience_citation"] = exp_c
                events[1]["requested_params"] = []
                events[1]["turn_intents"] = intents
            elif events and len(events) == 1:
                events[0]["requested_params"] = []
                events[0]["turn_intents"] = intents
                events[0]["experience_citation"] = exp_c

            u_prompt = events[0]["user"]["utterance"] if events and "user" in events[0] else ""
            branching_info = cls._build_experience_branching(
                scenario_type="overlapping_resolution",
                exp_id=exp_id,
                rule_title=exp_c.get("title") or "新旧意图保障单时段撞车无缝让路与时序重叠仲裁经验",
                learning_source_session=learning_source_session,
                user_prompt=u_prompt,
                ctx={"app": app, "srv": srv, "res": res, "rtt": rtt, "start": start, "end": end, "dur": dur}
            )

        return {
            "session_id": sid,
            "user_id": uid,
            "reference_time": ref_time,
            "session_meta": {
                "template_id": tid,
                "round_count": len(events),
                "intent_count": 1,
                "memory_role": role,
                "skeleton_signature": sig,
                "scenario": {"environment": env, "blueprint_type": b_type, "memory_action": act},
                "experience_citation": exp_c,
                "experience_branching": branching_info,
            },
            "experience_citation": exp_c,
            "experience_branching": branching_info,
            "event_sequence": events,
            "intents": intents,
            "relations": [],
            "slot_updates": slot_updates,
        }
