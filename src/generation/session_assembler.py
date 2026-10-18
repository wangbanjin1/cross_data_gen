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
                learning_source_session=s_plan.get("learning_source_session")
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
    def _assemble_t2_4(
        cls, sid, uid, ref_time, tid, role, b_type, env, act,
        app, srv, res, rtt, start, end, dur,
        events, snap, mems, gold,
        experience_citation=None, second_source=None,
        learning_source_session=None
    ):
        """T2-4: 经验记忆 ReasoningBank 多意图局部突发延误隔离 (2 轮, 2 意图)"""
        exp_c = experience_citation or {}
        exp_id = exp_c.get("experience_id") or "EXP_MULTI_INTENT_PARTITION_01"

        app2 = second_source.get("application_name", "抖音") if second_source else "抖音"
        srv2 = second_source.get("service_name", "直播") if second_source else "直播"

        d_str = ref_time.split("日")[0] + "日" if "日" in ref_time else "2026年10月24日"
        start2 = f"{d_str}14时00分"
        end2 = f"{d_str}16时00分"
        dur2 = "120min"

        sig = f"T2-4|{len(events)}|2|I1:{app}/{srv}/1/multi_intent_experience/resolved|I2:{app2}/{srv2}/1/locked_intact/resolved|none"

        intents = [
            {
                "intent_id": "I1",
                "status": "resolved",
                "closure_path": "multi_intent_experience",
                "expression_level": 1,
                "intent": f"{app}{srv}保障",
                "params": {
                    "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                    "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                    "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}},
                    "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}},
                    "timestamp": {
                        "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                        "end_timestamp": {"value": end, "source_type": "Experience", "source_ref": exp_id},
                        "duration": {"value": dur, "source_type": "Experience", "source_ref": exp_id},
                    },
                },
            },
            {
                "intent_id": "I2",
                "status": "resolved",
                "closure_path": "locked_intact",
                "expression_level": 1,
                "intent": f"{app2}{srv2}保障",
                "params": {
                    "application_name": {"value": app2, "source_type": "Memory", "source_ref": "SUB_001"},
                    "service_name": {"value": srv2, "source_type": "Memory", "source_ref": "SUB_001"},
                    "resolution": {"min_value": {"value": "1080p", "source_type": "Memory", "source_ref": "SUB_001"}},
                    "rtt": {"max_value": {"value": "50ms", "source_type": "Memory", "source_ref": "SUB_001"}},
                    "timestamp": {
                        "start_timestamp": {"value": start2, "source_type": "Memory", "source_ref": "SUB_001"},
                        "end_timestamp": {"value": end2, "source_type": "Memory", "source_ref": "SUB_001"},
                        "duration": {"value": dur2, "source_type": "Memory", "source_ref": "SUB_001"},
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
                                "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                            },
                        },
                    },
                    {
                        "turn": 2,
                        "params": {
                            "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}},
                            "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}},
                            "timestamp": {
                                "duration": {"value": dur, "source_type": "Experience", "source_ref": exp_id},
                            },
                        },
                    },
                ],
            },
            {
                "intent_id": "I2",
                "turn_updates": [
                    {
                        "turn": 1,
                        "params": {
                            "application_name": {"value": app2, "source_type": "Memory", "source_ref": "SUB_001"},
                            "service_name": {"value": srv2, "source_type": "Memory", "source_ref": "SUB_001"},
                            "resolution": {"min_value": {"value": "1080p", "source_type": "Memory", "source_ref": "SUB_001"}},
                            "rtt": {"max_value": {"value": "50ms", "source_type": "Memory", "source_ref": "SUB_001"}},
                            "timestamp": {
                                "start_timestamp": {"value": start2, "source_type": "Memory", "source_ref": "SUB_001"},
                                "end_timestamp": {"value": end2, "source_type": "Memory", "source_ref": "SUB_001"},
                                "duration": {"value": dur2, "source_type": "Memory", "source_ref": "SUB_001"},
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
                    "params": {
                        "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                        "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
                        "timestamp": {
                            "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                        },
                    },
                },
                intents[1]
            ]
            events[0]["experience_citation"] = exp_c
            events[1]["requested_params"] = []
            events[1]["turn_intents"] = intents
        elif events and len(events) == 1:
            events[0]["requested_params"] = []
            events[0]["turn_intents"] = intents
            events[0]["experience_citation"] = exp_c

        branching_info = {
            "learning_source_session": learning_source_session,
            "experience_id": exp_id,
            "rule_title": exp_c.get("title") or "多任务并行局部调整与时序因果隔离经验",
            "fast_path": {
                "round_count": 2,
                "closure_path": "fast_experience_closed_loop",
                "trigger_condition": "Agent应用多意图隔离经验，锁定I1局部调整，I2完全冻结保护，避免交叉污染",
                "resolved_turn": 2,
                "key_params_source": {"source_type": "Experience", "source_ref": exp_id}
            },
            "slow_path": {
                "round_count": 4,
                "closure_path": "clarification_after_correction",
                "trigger_condition": "Agent缺乏隔离经验，错误将I1延误扩散至I2，导致下午直播被意外篡改，经多轮纠偏澄清才收尾",
                "resolved_turn": 4,
                "redundant_rounds": 2,
                "simulator_dialogue_tree": [
                    {
                        "turn": 1,
                        "agent_hypothesis": "Agent将上午任务延期扩散至下午任务，将下午保障一并推迟",
                        "simulator_user_prompt": "不对啊！我只让你把上午的会议延长到12点，怎么把下午的直播也往后推迟了？下午的时间绝对不能动！",
                        "expected_agent_correction": "非常抱歉！已纠正错误，上午保障已单独延长至12:00，下午直播保障已严格锁定恢复原时段不变，请您核对！"
                    },
                    {
                        "turn": 2,
                        "agent_hypothesis": "Agent仍向用户重复确认下午任务参数",
                        "simulator_user_prompt": "行，下午别乱改就行，按这样开通吧。",
                        "expected_agent_correction": "好的，已完成多任务时序因果隔离确认，上午延长至12:00，下午维持原有时段不变！"
                    }
                ]
            }
        }

        return {
            "session_id": sid,
            "user_id": uid,
            "reference_time": ref_time,
            "session_meta": {
                "template_id": tid,
                "round_count": len(events),
                "intent_count": 2,
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
            "relations": [
                {
                    "source_intent_id": "I1",
                    "target_intent_id": "I2",
                    "relation_type": "temporal_sequential_isolated",
                    "notes": "两任务独立隔离，I1延期不污染I2配置"
                }
            ],
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
            app_src, app_ref = "Memory", "MF_001"
            srv_src, srv_ref = "Memory", "MF_001"
            res_src, res_ref = "Memory", "MF_001"
            rtt_src, rtt_ref = "Memory", "MF_001"
            start_src, start_ref = "Experience", exp_id
            end_src, end_ref = "Experience", exp_id
            dur_src, dur_ref = "Memory", "MF_001"
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
                branching_info = {
                    "learning_source_session": learning_source_session,
                    "experience_id": exp_id,
                    "rule_title": exp_c.get("title") or "节假日避坑顺延经验",
                    "fast_path": {
                        "round_count": 2,
                        "closure_path": "fast_experience_closed_loop",
                        "trigger_condition": "日历引擎识别国庆假期冲突，主动在大白话回复中顺延至节后首个工作日，2轮优雅出单",
                        "resolved_turn": 2,
                        "key_params_source": {"source_type": "Experience", "source_ref": exp_id}
                    },
                    "slow_path": {
                        "round_count": 4,
                        "closure_path": "clarification_after_correction",
                        "trigger_condition": "Agent缺乏节假日经验，机械按放假当天开通导致白白扣费，用户投诉退单，经历取消、重算、改期4轮拉扯",
                        "resolved_turn": 4,
                        "redundant_rounds": 2,
                        "simulator_dialogue_tree": [
                            {
                                "turn": 1,
                                "agent_hypothesis": "Agent未识别法定假期，直接在10月1日国庆长假当天预约保障",
                                "simulator_user_prompt": "等等，下周一不是国庆长假第一天全员放假吗？办公室都没人，怎么还给我排在10月1号？",
                                "expected_agent_correction": "抱歉！识别到10月1日为法定假日，已为您将例行保障顺延至节后首个工作日（10月8日）同时段办理，避免空跑产生费用，您看可以吗？"
                            },
                            {
                                "turn": 2,
                                "agent_hypothesis": "Agent未主动核实节后时段",
                                "simulator_user_prompt": "对，放假千万别空跑，就顺延到10月8日开通吧。",
                                "expected_agent_correction": "好的，已成功将保障顺延至10月8日办理（1080p / 时延≤50ms），祝您假期愉快！"
                            }
                        ]
                    }
                }
                ret["experience_branching"] = branching_info
                ret["session_meta"]["experience_branching"] = branching_info
        return ret

    @classmethod
    def _assemble_t2_6(cls, sid, uid, ref_time, tid, role, b_type, env, act, app, srv, res, rtt, start, end, dur, events, snap, mems, gold, working_memory_pointer=None, experience_citation=None, learning_source_session=None):
        """T2-6: 工作记忆历史工单跨期复用 (2 轮 / 3 轮消歧 / 经验记忆质量特征消歧)"""
        exp_c = experience_citation or {}
        exp_id = exp_c.get("experience_id")
        is_exp = bool(exp_c and exp_id == "EXP_ORDER_QUALITY_DISAMBIGUATION_01")

        wm_ptr = working_memory_pointer or {}
        rec_id = wm_ptr.get("target_record_id") or "REC_PRIOR"
        is_disambig = wm_ptr.get("is_disambiguation", False) or len(events) == 3

        if is_exp:
            closure_path = "quality_disambiguated_reuse"
            res_src, res_ref = "Experience", exp_id
            rtt_src, rtt_ref = "Experience", exp_id
            ts_ref = "U1"
        else:
            closure_path = "working_record_reuse"
            res_src, res_ref = "WorkingRecord", rec_id
            rtt_src, rtt_ref = "WorkingRecord", rec_id
            ts_ref = "U1" if is_disambig else "U2"

        sig = f"T2-6|{len(events)}|1|I1:{app}/{srv}/1/{closure_path}/resolved|none"

        intents = [
            {
                "intent_id": "I1",
                "status": "resolved",
                "closure_path": closure_path,
                "expression_level": 1,
                "intent": f"{app}{srv}保障",
                "params": {
                    "application_name": {"value": app, "source_type": "WorkingRecord", "source_ref": rec_id},
                    "service_name": {"value": srv, "source_type": "WorkingRecord", "source_ref": rec_id},
                    "resolution": {"min_value": {"value": res, "source_type": res_src, "source_ref": res_ref}},
                    "rtt": {"max_value": {"value": rtt, "source_type": rtt_src, "source_ref": rtt_ref}},
                    "timestamp": {
                        "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": ts_ref},
                        "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": ts_ref},
                        "duration": {"value": dur, "source_type": "Turn", "source_ref": ts_ref},
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
                                "application_name": {"value": app, "source_type": "WorkingRecord", "source_ref": rec_id},
                                "service_name": {"value": srv, "source_type": "WorkingRecord", "source_ref": rec_id},
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
            branching_info = {
                "learning_source_session": learning_source_session,
                "experience_id": exp_id,
                "rule_title": exp_c.get("title") or "模糊多候选历史工单质量特征消歧经验",
                "fast_path": {
                    "round_count": 2,
                    "closure_path": "fast_experience_closed_loop",
                    "trigger_condition": "调取工单质量运行日志，过滤掉网络波动单据，精准锁定历史无丢包优质工单并直接调取规格，2轮完成参数继承与闭环",
                    "resolved_turn": 2,
                    "key_params_source": {"source_type": "Experience", "source_ref": exp_id}
                },
                "slow_path": {
                    "round_count": 4,
                    "closure_path": "clarification_after_correction",
                    "trigger_condition": "Agent缺乏经验按盲猜选错单据或向用户全盘追问报菜名，用户严厉纠偏，拉扯4轮才办妥",
                    "resolved_turn": 4,
                    "redundant_rounds": 2,
                    "simulator_dialogue_tree": [
                        {
                            "turn": 1,
                            "agent_hypothesis": "Agent盲猜复用了上周四发生丢包抖动的异常工单",
                            "simulator_user_prompt": "你复用的这是哪天的工单？上周四那单网络有抖动丢包，千万别按那天的参数配，要按无丢包最好的那次配！",
                            "expected_agent_correction": "抱歉！已重新调取质量日志，过滤掉存在抖动的工单，已为您切换并锁定全程无丢包的高质量工单配置，确认按此生效吗？"
                        },
                        {
                            "turn": 2,
                            "agent_hypothesis": "Agent追问具体是哪一天",
                            "simulator_user_prompt": "没错，就按无丢包的那单开通。",
                            "expected_agent_correction": "好的，已按优质历史工单为您成功受理保障，祝您网络体验顺畅！"
                        }
                    ]
                }
            }
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
        sig = f"T2-8|{len(events)}|1|I1:历史工单流水对账核查/0/direct/resolved|none"

        intents = [
            {
                "intent_id": "I1",
                "status": "resolved",
                "closure_path": "direct",
                "expression_level": 0,
                "intent": "历史工单流水对账核查",
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
                        "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}},
                        "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}},
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
                                "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}},
                                "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}},
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

            branching_info = {
                "learning_source_session": learning_source_session,
                "experience_id": exp_id,
                "rule_title": exp_c.get("title") or "重大活动提前30分钟网络预热起保经验",
                "fast_path": {
                    "round_count": 2,
                    "closure_path": "fast_experience_closed_loop",
                    "trigger_condition": "自主识别重大活动并执行推流预热时间差推算（提前30分钟起保，总时长扩充），2轮确认极速闭环",
                    "resolved_turn": 2,
                    "key_params_source": {"source_type": "Experience", "source_ref": exp_id}
                },
                "slow_path": {
                    "round_count": 4,
                    "closure_path": "clarification_after_correction",
                    "trigger_condition": "机械按活动时间开通，未预留调试时间导致用户纠偏改单，拉扯4轮才收尾",
                    "resolved_turn": 4,
                    "redundant_rounds": 2,
                    "simulator_dialogue_tree": [
                        {
                            "turn": 1,
                            "agent_hypothesis": "Agent按活动开始时间掐点预约，未预留30分钟预热试机缓冲",
                            "simulator_user_prompt": "等等，这是大型场馆活动，现场设备调试很多，掐着点开通根本来不及试机！必须提前半小时起保！",
                            "expected_agent_correction": "抱歉！已为您重新推算时间，将保障开始时间自动提前30分钟作为预热试机缓冲，总时长扩至对应时长，确认按此开通吗？"
                        },
                        {
                            "turn": 2,
                            "agent_hypothesis": "Agent询问是否确定提前",
                            "simulator_user_prompt": "对，提前半小时才稳妥，确认开通。",
                            "expected_agent_correction": "好的，已为您成功受理提前30分钟预热试机网络保障，预祝大型现场活动圆满顺利！"
                        }
                    ]
                }
            }
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

            branching_info = {
                "learning_source_session": learning_source_session,
                "experience_id": exp_id,
                "rule_title": exp_c.get("title") or "大型活动起保前置预热试机经验",
                "fast_path": {
                    "round_count": 2,
                    "closure_path": "fast_experience_closed_loop",
                    "trigger_condition": "识别大型场馆与展会，主动提议提前30分钟起保作为试机缓冲，2轮完成参数推算与闭环",
                    "resolved_turn": 2,
                    "key_params_source": {"source_type": "Experience", "source_ref": exp_id}
                },
                "slow_path": {
                    "round_count": 4,
                    "closure_path": "clarification_after_correction",
                    "trigger_condition": "Agent缺乏经验按字面掐点起保，用户纠偏要求提前半小时调试，经修改重算后才闭环",
                    "resolved_turn": 4,
                    "redundant_rounds": 2,
                    "simulator_dialogue_tree": [
                        {
                            "turn": 1,
                            "agent_hypothesis": "Agent按活动开始时间掐点预约，未预留30分钟预热试机缓冲",
                            "simulator_user_prompt": "等等，这是大型场馆活动，现场设备调试很多，掐着点开通根本来不及试机！必须提前半小时起保！",
                            "expected_agent_correction": "抱歉！已为您重新推算时间，将保障开始时间自动提前30分钟作为预热试机缓冲，总时长扩至对应时长，确认按此开通吗？"
                        },
                        {
                            "turn": 2,
                            "agent_hypothesis": "Agent询问是否确定提前",
                            "simulator_user_prompt": "对，提前半小时才稳妥，确认开通。",
                            "expected_agent_correction": "好的，已为您成功受理提前30分钟预热试机网络保障，预祝大型现场活动圆满顺利！"
                        }
                    ]
                }
            }

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
        """T2-10: 经验记忆 ReasoningBank 经验回溯与边界防线 (2 轮 / 1 意图 / 新旧工单撞车让路接管)"""
        exp_c = experience_citation or {}
        exp_id = exp_c.get("experience_id") or "EXP_OVERLAPPING_ORDER_RESOLUTION_01"
        is_overlap = (exp_id == "EXP_OVERLAPPING_ORDER_RESOLUTION_01")

        if is_overlap:
            closure_path = "overlapping_order_resolution"
            sig = f"T2-10|{len(events)}|1|I1:{app}/{srv}/1/{closure_path}/resolved|none"
            start_src, start_ref = "Experience", exp_id
            res_src, res_ref = "Memory", "MF_001"
            rtt_src, rtt_ref = "Memory", "MF_001"

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
                        "resolution": {"min_value": {"value": res, "source_type": res_src, "source_ref": res_ref}},
                        "rtt": {"max_value": {"value": rtt, "source_type": rtt_src, "source_ref": rtt_ref}},
                        "timestamp": {
                            "start_timestamp": {"value": start, "source_type": start_src, "source_ref": start_ref},
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
                                "resolution": {"min_value": {"value": res, "source_type": res_src, "source_ref": res_ref}},
                                "rtt": {"max_value": {"value": rtt, "source_type": rtt_src, "source_ref": rtt_ref}},
                                "timestamp": {
                                    "start_timestamp": {"value": start, "source_type": start_src, "source_ref": start_ref},
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

            branching_info = {
                "learning_source_session": learning_source_session,
                "experience_id": exp_id,
                "rule_title": exp_c.get("title") or "工单时序重叠仲裁与让路接管经验",
                "fast_path": {
                    "round_count": 2,
                    "closure_path": "fast_experience_closed_loop",
                    "trigger_condition": "自动时钟裁决：协调前单在交界点提前交割结单，新保障单准时无缝激活接管通道，2轮化解工单冲突",
                    "resolved_turn": 2,
                    "key_params_source": {"source_type": "Experience", "source_ref": exp_id}
                },
                "slow_path": {
                    "round_count": 4,
                    "closure_path": "clarification_after_correction",
                    "trigger_condition": "系统报错时段重叠冲突甩锅用户退单重申，经历取消、重算、改期4轮拉扯",
                    "resolved_turn": 4,
                    "redundant_rounds": 2,
                    "simulator_dialogue_tree": [
                        {
                            "turn": 1,
                            "agent_hypothesis": "Agent因与已有工单时间重叠而直接提示冲突报错",
                            "simulator_user_prompt": "新申请的保障和之前的单子撞车了，不能直接报错啊！你们应该让原工单提前结单，新保障准时接管才对！",
                            "expected_agent_correction": "抱歉！已应用时钟让路仲裁：原预约工单将在重叠交界点提前终止结单，新保障准时无缝激活，避免冲突与重复计费，确认按此处理吗？"
                        },
                        {
                            "turn": 2,
                            "agent_hypothesis": "Agent询问是否确认让路",
                            "simulator_user_prompt": "好的，这样时序接续就可以，确认开通。",
                            "expected_agent_correction": "好的，已为您完成时序仲裁办理，原工单提前结单让路，新保障准时接续生效！"
                        }
                    ]
                }
            }
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

            branching_info = {
                "learning_source_session": learning_source_session,
                "experience_id": exp_id,
                "rule_title": exp_c.get("title") or "工单时序重叠仲裁与让路接管经验",
                "fast_path": {
                    "round_count": 2,
                    "closure_path": "fast_experience_closed_loop",
                    "trigger_condition": "检测新旧工单时段撞车，应用时钟仲裁策略协调原工单在重叠点提前结单让路，新保障无缝接管",
                    "resolved_turn": 2,
                    "key_params_source": {"source_type": "Experience", "source_ref": exp_id}
                },
                "slow_path": {
                    "round_count": 4,
                    "closure_path": "clarification_after_correction",
                    "trigger_condition": "Agent缺乏仲裁经验直接报错时段冲突拒绝办理，用户指责后才改由原工单提前退单让路，交互多轮才解决",
                    "resolved_turn": 4,
                    "redundant_rounds": 2,
                    "simulator_dialogue_tree": [
                        {
                            "turn": 1,
                            "agent_hypothesis": "Agent因与已有工单时间重叠而直接提示冲突报错",
                            "simulator_user_prompt": "新申请的保障和之前的单子撞车了，不能直接报错啊！你们应该让原工单提前结单，新保障准时接管才对！",
                            "expected_agent_correction": "抱歉！已应用时钟让路仲裁：原预约工单将在重叠交界点提前终止结单，新保障准时无缝激活，避免冲突与重复计费，确认按此处理吗？"
                        },
                        {
                            "turn": 2,
                            "agent_hypothesis": "Agent询问是否确认让路",
                            "simulator_user_prompt": "好的，这样时序接续就可以，确认开通。",
                            "expected_agent_correction": "好的，已为您完成时序仲裁办理，原工单提前结单让路，新保障准时接续生效！"
                        }
                    ]
                }
            }

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
