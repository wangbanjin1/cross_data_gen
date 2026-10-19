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
    def _build_experience_branching(
        cls,
        scenario_type: str,
        exp_id: str,
        rule_title: str,
        learning_source_session: str,
        user_prompt: str,
        ctx: dict
    ) -> dict:
        """构建具备完整 4 轮可执行交互树与自动化仲裁门 (Branch Decision Gate) 的双轨评测元数据"""
        app = ctx.get("app", "保障应用")
        srv = ctx.get("srv", "保障业务")
        res = ctx.get("res", "1080p")
        rtt = ctx.get("rtt", "50ms")
        start = ctx.get("start", "14:00")
        end = ctx.get("end", "16:00")
        dur = ctx.get("dur", "120min")

        if scenario_type == "multi_intent_partition":
            app2 = ctx.get("app2", "微信")
            srv2 = ctx.get("srv2", "视频通话")
            res2 = ctx.get("res2", "1080p")
            rtt2 = ctx.get("rtt2", "50ms")
            start2 = ctx.get("start2", "14:00")
            end2 = ctx.get("end2", "16:00")
            dur2 = ctx.get("dur2", "120min")

            fast_cond = "Agent应用多意图隔离经验，锁定I1局部调整，I2完全冻结保护，避免交叉污染"
            slow_cond = "Agent缺乏隔离经验，错误将I1延误扩散至I2，导致下午保障被意外篡改，经多轮纠偏澄清才收尾"
            
            gate = {
                "eval_turn": 1,
                "decision_type": "experience_isolation_check",
                "pass_condition": "Agent在I1顺延时，严格锁定并冻结I2的时序与配置不变 (EXP_MULTI_INTENT_PARTITION_01)",
                "fail_condition": "Agent发生跨意图污染，将I1的时钟延误扩散至I2，或推倒重来全盘追问I2",
                "key_slot_assertions": {
                    "target_intent_id": "I2",
                    "isolated_slots": ["timestamp.start_timestamp", "timestamp.end_timestamp"],
                    "expected_action": "isolate_and_freeze"
                },
                "pass_route": "fast_path",
                "fail_route": "slow_path"
            }

            tree = [
                {
                    "turn": 1,
                    "speaker": "user",
                    "simulator_user_prompt": user_prompt,
                    "agent_hypothesis": f"Agent缺乏时序因果隔离经验，误将{app}{srv}的延期连带应用到{app2}{srv2}，统一往后推迟",
                    "baseline_agent_flawed_response": f"收到，已为您将上午{app}{srv}顺延至{end}，同时为您将下午{app2}{srv2}一并顺延后移，确认按此统一调整吗？",
                    "expected_agent_correction": f"收到，已为您将上午{app}{srv}顺延至{end}，同时为您将下午{app2}{srv2}一并顺延后移，确认按此统一调整吗？",
                    "flaw_type": "cross_intent_delay_leakage",
                    "flaw_description": "将I1的任务延期错误扩散至I2，污染非目标意图时段",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}},
                        "I2": {"application_name": app2, "service_name": srv2, "resolution": res2, "rtt": rtt2, "timestamp": {"start_timestamp": start2, "end_timestamp": end2, "duration": dur2}}
                    },
                    "baseline_flawed_slots": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}},
                        "I2": {"application_name": app2, "service_name": srv2, "resolution": res2, "rtt": rtt2, "timestamp": {"start_timestamp": end, "end_timestamp": end2, "duration": dur2}}
                    },
                    "delta_from_gt": {
                        "has_error": True,
                        "error_details": [f"I2.timestamp.start_timestamp: expected '{start2}', got '{end}'"],
                        "triggered_reaction": "on_slot_error"
                    }
                },
                {
                    "turn": 2,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": f"不对啊！我只让你把上午的{srv}延长，怎么把下午的{srv2}也往后推迟了？下午的时间绝对不能动！",
                    "agent_hypothesis": "Agent意识到跨任务污染错误，紧急冻结锁定下午时段，但遗漏了上午时长的重新核算，泛泛反问",
                    "expected_agent_correction": f"非常抱歉！已纠正错误，上午{app}{srv}已顺延，下午{app2}{srv2}已严格锁定恢复原时段（{start2}至{end2}）不变，请问上午按此直接开通吗？",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}},
                        "I2": {"application_name": app2, "service_name": srv2, "resolution": res2, "rtt": rtt2, "timestamp": {"start_timestamp": start2, "end_timestamp": end2, "duration": dur2}}
                    },
                    "baseline_flawed_slots": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end}},
                        "I2": {"application_name": app2, "service_name": srv2, "resolution": res2, "rtt": rtt2, "timestamp": {"start_timestamp": start2, "end_timestamp": end2, "duration": dur2}}
                    },
                    "delta_from_gt": {
                        "has_error": False,
                        "missing_details": ["I1.timestamp.duration"],
                        "triggered_reaction": "on_slot_missing"
                    }
                },
                {
                    "turn": 3,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": f"下午别动是对的，但我上午延后之后，总保障时长到底是按多久算的？你们系统到底算准了没有？",
                    "agent_hypothesis": "Agent对上午任务重算时长，并向用户明确两任务独立生效且时长核准",
                    "expected_agent_correction": f"非常抱歉疏忽！已为您核对重算：上午{app}{srv}总时长已精确更新为{dur}，下午维持原有时序（{dur2}），请您核对确认！",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}},
                        "I2": {"application_name": app2, "service_name": srv2, "resolution": res2, "rtt": rtt2, "timestamp": {"start_timestamp": start2, "end_timestamp": end2, "duration": dur2}}
                    }
                },
                {
                    "turn": 4,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": f"行，时长算清楚了。那改期后上午和下午的网络规格（清晰度和时延）没被改乱吧？",
                    "agent_hypothesis": "Agent核验两笔保障各自网络指标独立完整，向用户发起正式出单确认",
                    "expected_agent_correction": f"请您放心，上午全程继续执行{res}与时延≤{rtt}，下午严格保持{res2}与时延≤{rtt2}，两项保障互不干扰，确认现在为您正式受理吗？",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}},
                        "I2": {"application_name": app2, "service_name": srv2, "resolution": res2, "rtt": rtt2, "timestamp": {"start_timestamp": start2, "end_timestamp": end2, "duration": dur2}}
                    }
                },
                {
                    "turn": 5,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": "行，两边都对齐没问题了，确认开通。",
                    "agent_hypothesis": "Agent成功完成多任务因果隔离闭环出单",
                    "expected_agent_correction": f"好的，已完成多任务时序因果隔离确认，上午{app}延长办理、下午{app2}维持原有时段不变，两笔保障均已成功受理！",
                    "agent_action_types": ["Acknowledge"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}},
                        "I2": {"application_name": app2, "service_name": srv2, "resolution": res2, "rtt": rtt2, "timestamp": {"start_timestamp": start2, "end_timestamp": end2, "duration": dur2}}
                    }
                }
            ]

            full_slow_seq = [
                {
                    "turn": 1,
                    "user": {"utterance": tree[0]["simulator_user_prompt"], "action_types": ["Create_Intent_Request", "Inform_Slot"]},
                    "agent": {"utterance": tree[0]["baseline_agent_flawed_response"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1", "I2"],
                    "requested_params": [],
                    "turn_intents": [
                        {"intent_id": "I1", "status": "in_progress", "closure_path": "flawed_delay_leakage", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"}}}},
                        {"intent_id": "I2", "status": "in_progress", "closure_path": "flawed_delay_leakage", "expression_level": 1, "intent": f"{app2}{srv2}保障", "params": {"application_name": {"value": app2, "source_type": "Memory", "source_ref": "SUB_001"}, "service_name": {"value": srv2, "source_type": "Memory", "source_ref": "SUB_001"}, "resolution": {"min_value": {"value": res2, "source_type": "Memory", "source_ref": "SUB_001"}}, "rtt": {"max_value": {"value": rtt2, "source_type": "Memory", "source_ref": "SUB_001"}}, "timestamp": {"start_timestamp": {"value": end, "source_type": "Flawed_Inference", "source_ref": "Agent"}, "end_timestamp": {"value": end2, "source_type": "Memory", "source_ref": "SUB_001"}, "duration": {"value": dur2, "source_type": "Memory", "source_ref": "SUB_001"}}}}
                    ]
                },
                {
                    "turn": 2,
                    "user": {"utterance": tree[1]["simulator_user_prompt"], "action_types": ["Revise_Intent_Request", "Inform_Slot"]},
                    "agent": {"utterance": tree[1]["expected_agent_correction"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1", "I2"],
                    "requested_params": [],
                    "turn_intents": [
                        {"intent_id": "I1", "status": "in_progress", "closure_path": "correction_in_progress", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Correction", "source_ref": "Agent"}}}},
                        {"intent_id": "I2", "status": "in_progress", "closure_path": "isolated_locked", "expression_level": 1, "intent": f"{app2}{srv2}保障", "params": {"application_name": {"value": app2, "source_type": "Memory", "source_ref": "SUB_001"}, "service_name": {"value": srv2, "source_type": "Memory", "source_ref": "SUB_001"}, "resolution": {"min_value": {"value": res2, "source_type": "Memory", "source_ref": "SUB_001"}}, "rtt": {"max_value": {"value": rtt2, "source_type": "Memory", "source_ref": "SUB_001"}}, "timestamp": {"start_timestamp": {"value": start2, "source_type": "Memory", "source_ref": "SUB_001"}, "end_timestamp": {"value": end2, "source_type": "Memory", "source_ref": "SUB_001"}, "duration": {"value": dur2, "source_type": "Memory", "source_ref": "SUB_001"}}}}
                    ]
                },
                {
                    "turn": 3,
                    "user": {"utterance": tree[2]["simulator_user_prompt"], "action_types": ["Confirm_Slot"]},
                    "agent": {"utterance": tree[2]["expected_agent_correction"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1", "I2"],
                    "requested_params": [],
                    "turn_intents": [
                        {"intent_id": "I1", "status": "in_progress", "closure_path": "duration_recalculated", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Correction", "source_ref": "Agent"}}}},
                        {"intent_id": "I2", "status": "in_progress", "closure_path": "isolated_locked", "expression_level": 1, "intent": f"{app2}{srv2}保障", "params": {"application_name": {"value": app2, "source_type": "Memory", "source_ref": "SUB_001"}, "service_name": {"value": srv2, "source_type": "Memory", "source_ref": "SUB_001"}, "resolution": {"min_value": {"value": res2, "source_type": "Memory", "source_ref": "SUB_001"}}, "rtt": {"max_value": {"value": rtt2, "source_type": "Memory", "source_ref": "SUB_001"}}, "timestamp": {"start_timestamp": {"value": start2, "source_type": "Memory", "source_ref": "SUB_001"}, "end_timestamp": {"value": end2, "source_type": "Memory", "source_ref": "SUB_001"}, "duration": {"value": dur2, "source_type": "Memory", "source_ref": "SUB_001"}}}}
                    ]
                },
                {
                    "turn": 4,
                    "user": {"utterance": tree[3]["simulator_user_prompt"], "action_types": ["Confirm_Slot"]},
                    "agent": {"utterance": tree[3]["expected_agent_correction"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1", "I2"],
                    "requested_params": [],
                    "turn_intents": [
                        {"intent_id": "I1", "status": "in_progress", "closure_path": "specs_verified", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Correction", "source_ref": "Agent"}}}},
                        {"intent_id": "I2", "status": "in_progress", "closure_path": "isolated_locked", "expression_level": 1, "intent": f"{app2}{srv2}保障", "params": {"application_name": {"value": app2, "source_type": "Memory", "source_ref": "SUB_001"}, "service_name": {"value": srv2, "source_type": "Memory", "source_ref": "SUB_001"}, "resolution": {"min_value": {"value": res2, "source_type": "Memory", "source_ref": "SUB_001"}}, "rtt": {"max_value": {"value": rtt2, "source_type": "Memory", "source_ref": "SUB_001"}}, "timestamp": {"start_timestamp": {"value": start2, "source_type": "Memory", "source_ref": "SUB_001"}, "end_timestamp": {"value": end2, "source_type": "Memory", "source_ref": "SUB_001"}, "duration": {"value": dur2, "source_type": "Memory", "source_ref": "SUB_001"}}}}
                    ]
                },
                {
                    "turn": 5,
                    "user": {"utterance": tree[4]["simulator_user_prompt"], "action_types": ["Confirm_Slot"]},
                    "agent": {"utterance": tree[4]["expected_agent_correction"], "action_types": ["Acknowledge"]},
                    "related_intent_ids": ["I1", "I2"],
                    "requested_params": [],
                    "turn_intents": [
                        {"intent_id": "I1", "status": "resolved", "closure_path": "clarification_after_correction", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Correction", "source_ref": "Agent"}}}},
                        {"intent_id": "I2", "status": "resolved", "closure_path": "locked_intact", "expression_level": 1, "intent": f"{app2}{srv2}保障", "params": {"application_name": {"value": app2, "source_type": "Memory", "source_ref": "SUB_001"}, "service_name": {"value": srv2, "source_type": "Memory", "source_ref": "SUB_001"}, "resolution": {"min_value": {"value": res2, "source_type": "Memory", "source_ref": "SUB_001"}}, "rtt": {"max_value": {"value": rtt2, "source_type": "Memory", "source_ref": "SUB_001"}}, "timestamp": {"start_timestamp": {"value": start2, "source_type": "Memory", "source_ref": "SUB_001"}, "end_timestamp": {"value": end2, "source_type": "Memory", "source_ref": "SUB_001"}, "duration": {"value": dur2, "source_type": "Memory", "source_ref": "SUB_001"}}}}
                    ]
                }
            ]

        elif scenario_type == "prewarm_buffer":
            import re
            fast_cond = "自主识别重大活动并执行推流预热时间差推算（提前30分钟起保，总时长扩充），2轮确认极速闭环"
            slow_cond = "机械按活动时间开通，未预留调试时间导致用户纠偏改单，拉扯4轮才收尾"
            gate = {
                "eval_turn": 1,
                "decision_type": "prewarm_buffer_check",
                "pass_condition": "Agent识别重大活动并主动将 start_timestamp 提前 30 分钟预热，同时 duration 扩充 30 分钟 (EXP_PREWARM_BUFFER_01)",
                "fail_condition": "Agent机械按用户口语活动时间掐点预约，未预留调试与预热时间",
                "key_slot_assertions": {
                    "target_intent_id": "I1",
                    "checked_slot": "timestamp.start_timestamp",
                    "expected_adjustment": "-30min_prewarm_offset"
                },
                "pass_route": "fast_path",
                "fail_route": "slow_path"
            }

            # 计算口语/未预热的原始活动起止时间与时长 (顺延后退30分钟起保，时长缩减30分钟)
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
            nom_dur = f"{max(30, int(m_d.group(1)) - 30)}min" if m_d else "60min"

            tree = [
                {
                    "turn": 1,
                    "speaker": "user",
                    "simulator_user_prompt": user_prompt,
                    "agent_hypothesis": "Agent按活动开始时间掐点预约，未做提前30分钟预热试机推算",
                    "baseline_agent_flawed_response": f"收到，已按活动起止时间锁定{app}{srv}保障（{nom_start}至{end}，{res} / 时延≤{rtt}），确认直接为您开通吗？",
                    "expected_agent_correction": f"收到，已按活动起止时间锁定{app}{srv}保障（{nom_start}至{end}，{res} / 时延≤{rtt}），确认直接为您开通吗？",
                    "flaw_type": "missing_prewarm_buffer",
                    "flaw_description": "未对重大活动外场设备调试推流进行前置时间差推算",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {
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
                    },
                    "baseline_flawed_slots": {
                        "I1": {
                            "application_name": app,
                            "service_name": srv,
                            "resolution": res,
                            "rtt": rtt,
                            "timestamp": {
                                "start_timestamp": nom_start,
                                "end_timestamp": end,
                                "duration": nom_dur
                            }
                        }
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
                    "simulator_user_prompt": "等等，这是大型场馆活动，现场设备调试很多，掐着点开通根本来不及试机！必须提前半小时起保！",
                    "agent_hypothesis": "Agent收到纠偏后重新推算起保时间与总时长",
                    "expected_agent_correction": f"抱歉！已为您重新推算时间，将保障开始时间自动提前30分钟推算为{start}至{end}（总时长扩至{dur}），确认按此提前开通吗？",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    }
                },
                {
                    "turn": 3,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": "对，必须提前半小时试机才稳妥，那预热调试期间的网络指标还是保持高规格吧？",
                    "agent_hypothesis": "Agent核验预热阶段网络指标一致性并向用户确认",
                    "expected_agent_correction": f"是的，提前预热试机全程同样执行{res}与时延≤{rtt}的高规格保障，确认现在为您提交办理吗？",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    }
                },
                {
                    "turn": 4,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": "好的，这就稳妥了，确认开通。",
                    "agent_hypothesis": "Agent完成提前预热试机保障受理",
                    "expected_agent_correction": f"好的，已为您成功受理提前30分钟预热试机网络保障（起保时间：{start}），预祝大型活动圆满顺利！",
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
                    "agent": {"utterance": tree[0]["baseline_agent_flawed_response"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "in_progress", "closure_path": "flawed_baseline_attempt", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}}, "timestamp": {"start_timestamp": {"value": nom_start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": nom_dur, "source_type": "Turn", "source_ref": "U1"}}}}]
                },
                {
                    "turn": 2,
                    "user": {"utterance": tree[1]["simulator_user_prompt"], "action_types": ["Revise_Intent_Request", "Inform_Slot"]},
                    "agent": {"utterance": tree[1]["expected_agent_correction"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "in_progress", "closure_path": "prewarm_correction", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Correction", "source_ref": "Agent"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Correction", "source_ref": "Agent"}}}}]
                },
                {
                    "turn": 3,
                    "user": {"utterance": tree[2]["simulator_user_prompt"], "action_types": ["Confirm_Slot"]},
                    "agent": {"utterance": tree[2]["expected_agent_correction"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "in_progress", "closure_path": "prewarm_correction", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Correction", "source_ref": "Agent"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Correction", "source_ref": "Agent"}}}}]
                },
                {
                    "turn": 4,
                    "user": {"utterance": tree[3]["simulator_user_prompt"], "action_types": ["Confirm_Slot"]},
                    "agent": {"utterance": tree[3]["expected_agent_correction"], "action_types": ["Acknowledge"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "resolved", "closure_path": "clarification_after_correction", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Correction", "source_ref": "Agent"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Correction", "source_ref": "Agent"}}}}]
                }
            ]

        elif scenario_type == "holiday_exception":
            import re
            fast_cond = "日历引擎识别国庆假期冲突，主动在大白话回复中顺延至节后首个工作日，2轮优雅出单"
            slow_cond = "Agent缺乏节假日经验，机械按放假当天开通导致白白扣费，用户投诉退单，经历取消、重算、改期4轮拉扯"
            gate = {
                "eval_turn": 1,
                "decision_type": "holiday_conflict_deferral_check",
                "pass_condition": "Agent识别下周一为法定节假日（国庆长假），主动提醒避让并顺延至节后首个工作日 (EXP_CALENDAR_HOLIDAY_EXCEPTION_01)",
                "fail_condition": "Agent缺乏日历假期常识，直接在放假日当天预约，导致空跑浪费",
                "key_slot_assertions": {
                    "target_intent_id": "I1",
                    "checked_slot": "timestamp.start_timestamp",
                    "expected_deferral": "post_holiday_workday"
                },
                "pass_route": "fast_path",
                "fail_route": "slow_path"
            }

            holiday_start = re.sub(r'\d{4}年\d{1,2}月\d{1,2}日', '2026年10月01日', start)
            holiday_end = re.sub(r'\d{4}年\d{1,2}月\d{1,2}日', '2026年10月01日', end)
            holiday_dur = dur

            tree = [
                {
                    "turn": 1,
                    "speaker": "user",
                    "simulator_user_prompt": user_prompt,
                    "agent_hypothesis": "Agent未识别下周一为国庆节法定假期，直接在放假当天机械预约",
                    "baseline_agent_flawed_response": f"收到，已为您预约下周一（10月1日）的{app}{srv}保障（{holiday_start}至{holiday_end}），确认直接按此开通吗？",
                    "expected_agent_correction": f"收到，已为您预约下周一（10月1日）的{app}{srv}保障（{holiday_start}至{holiday_end}），确认直接按此开通吗？",
                    "flaw_type": "unaware_of_holiday_conflict",
                    "flaw_description": "未对法定节假日冲突避让进行推断，在办公室全员放假时机械预约",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {
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
                    },
                    "baseline_flawed_slots": {
                        "I1": {
                            "application_name": app,
                            "service_name": srv,
                            "resolution": res,
                            "rtt": rtt,
                            "timestamp": {
                                "start_timestamp": holiday_start,
                                "end_timestamp": holiday_end,
                                "duration": holiday_dur
                            }
                        }
                    },
                    "delta_from_gt": {
                        "has_error": True,
                        "error_details": [f"I1.timestamp.start_timestamp: expected '{start}', got '{holiday_start}'"],
                        "triggered_reaction": "on_slot_error"
                    }
                },
                {
                    "turn": 2,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": "等等，下周一不是国庆长假第一天全员放假吗？办公室都没人，怎么还给我排在10月1号？",
                    "agent_hypothesis": "Agent收到投诉纠偏后撤销放假当天预约，并反问改期",
                    "expected_agent_correction": "抱歉！识别到10月1日为国庆法定长假，全员放假。已为您撤销10月1日的预约，请问您打算改到哪天办理？",
                    "agent_action_types": ["Request_Slot"],
                    "expected_slots_gt": {
                        "I1": {
                            "application_name": app,
                            "service_name": srv,
                            "resolution": res,
                            "rtt": rtt,
                            "timestamp": {
                                "start_timestamp": None,
                                "end_timestamp": None,
                                "duration": dur
                            }
                        }
                    }
                },
                {
                    "turn": 3,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": "放假千万别空跑白扣费，按惯例自动顺延到节后上班第一天就行。",
                    "agent_hypothesis": "Agent推算节后首个工作日时段并发起确认",
                    "expected_agent_correction": f"明白！节后首个工作日为10月8日，已将例行保障顺延至10月8日同时段（{res} / 时延≤{rtt}），避免假期产生空跑费用，确认按此顺延生效吗？",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    }
                },
                {
                    "turn": 4,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": "对，放假千万别空跑，就顺延到10月8日开通吧。",
                    "agent_hypothesis": "Agent完成节后顺延办理并出单",
                    "expected_agent_correction": f"好的，已成功将保障顺延至10月8日办理（{res} / 时延≤{rtt}），祝您假期愉快！",
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
                    "agent": {"utterance": tree[0]["baseline_agent_flawed_response"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "in_progress", "closure_path": "flawed_baseline_attempt", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Memory", "source_ref": "MF_001"}, "service_name": {"value": srv, "source_type": "Memory", "source_ref": "MF_001"}, "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}}, "timestamp": {"start_timestamp": {"value": holiday_start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": holiday_end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": holiday_dur, "source_type": "Turn", "source_ref": "U1"}}}}]
                },
                {
                    "turn": 2,
                    "user": {"utterance": tree[1]["simulator_user_prompt"], "action_types": ["Revise_Intent_Request", "Inform_Slot"]},
                    "agent": {"utterance": tree[1]["expected_agent_correction"], "action_types": ["Request_Slot"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": ["start_timestamp"],
                    "turn_intents": [{"intent_id": "I1", "status": "in_progress", "closure_path": "holiday_cancellation", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Memory", "source_ref": "MF_001"}, "service_name": {"value": srv, "source_type": "Memory", "source_ref": "MF_001"}, "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}}, "timestamp": {"duration": {"value": dur, "source_type": "Memory", "source_ref": "MF_001"}}}}]
                },
                {
                    "turn": 3,
                    "user": {"utterance": tree[2]["simulator_user_prompt"], "action_types": ["Inform_Slot"]},
                    "agent": {"utterance": tree[2]["expected_agent_correction"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "in_progress", "closure_path": "holiday_deferral_confirm", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Memory", "source_ref": "MF_001"}, "service_name": {"value": srv, "source_type": "Memory", "source_ref": "MF_001"}, "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Correction", "source_ref": "Agent"}, "end_timestamp": {"value": end, "source_type": "Correction", "source_ref": "Agent"}, "duration": {"value": dur, "source_type": "Memory", "source_ref": "MF_001"}}}}]
                },
                {
                    "turn": 4,
                    "user": {"utterance": tree[3]["simulator_user_prompt"], "action_types": ["Confirm_Slot"]},
                    "agent": {"utterance": tree[3]["expected_agent_correction"], "action_types": ["Acknowledge"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "resolved", "closure_path": "clarification_after_correction", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Memory", "source_ref": "MF_001"}, "service_name": {"value": srv, "source_type": "Memory", "source_ref": "MF_001"}, "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Correction", "source_ref": "Agent"}, "end_timestamp": {"value": end, "source_type": "Correction", "source_ref": "Agent"}, "duration": {"value": dur, "source_type": "Memory", "source_ref": "MF_001"}}}}]
                }
            ]

        elif scenario_type == "quality_disambiguation":
            fast_cond = "调取工单质量运行日志，过滤掉网络波动单据，精准锁定历史无丢包优质工单并直接调取规格，2轮完成参数继承与闭环"
            slow_cond = "Agent缺乏经验按盲猜选错单据或向用户全盘追问报菜名，用户严厉纠偏，拉扯4轮才办妥"
            gate = {
                "eval_turn": 1,
                "decision_type": "quality_log_disambiguation_check",
                "pass_condition": "Agent调取历史工单质量日志，过滤掉存在抖动丢包的异常单，精准锁定零丢包优质工单并直接继承规格 (EXP_ORDER_QUALITY_DISAMBIGUATION_01)",
                "fail_condition": "Agent盲猜复用近期网络异常的工单，或全盘报菜名盘问用户",
                "key_slot_assertions": {
                    "target_intent_id": "I1",
                    "checked_source": "Experience",
                    "expected_quality_filter": "filter_packet_loss_records"
                },
                "pass_route": "fast_path",
                "fail_route": "slow_path"
            }
            tree = [
                {
                    "turn": 1,
                    "speaker": "user",
                    "simulator_user_prompt": user_prompt,
                    "agent_hypothesis": "Agent盲猜复用了上周发生抖动丢包的异常工单",
                    "baseline_agent_flawed_response": f"收到，已为您调取上周在现场的历史工单规格（720p / 时延80ms），今日{start}至{end}为您开通，确认吗？",
                    "expected_agent_correction": f"收到，已为您调取上周在现场的历史工单规格（720p / 时延80ms），今日{start}至{end}为您开通，确认吗？",
                    "flaw_type": "blind_reuse_flawed_record",
                    "flaw_description": "未检索运行质量日志，盲目就近复用了存在网络抖动或丢包的历史异常工单",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    },
                    "baseline_flawed_slots": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": "720p", "rtt": "80ms", "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    },
                    "delta_from_gt": {
                        "has_error": True,
                        "error_details": [
                            f"I1.resolution: expected '{res}', got '720p'",
                            f"I1.rtt: expected '{rtt}', got '80ms'"
                        ],
                        "triggered_reaction": "on_slot_error"
                    }
                },
                {
                    "turn": 2,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": "不对啊！你复用的这是哪天的工单？上周四那单网络有明显抖动丢包，千万别按那天的参数配，要按全程无丢包最好的那次配！",
                    "agent_hypothesis": "Agent重新排查质量日志，过滤异常单并匹配优质单",
                    "expected_agent_correction": f"非常抱歉！已重新调取质量日志，排查发现前序工单确有丢包记录；已为您过滤异常单，精准锁定全程零丢包的优质保障规格（{res} / 时延≤{rtt}），请问按此优质配置开通吗？",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    }
                },
                {
                    "turn": 3,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": "对，必须按无丢包那次最稳的来，那今天的起止时间没搞错吧？",
                    "agent_hypothesis": "Agent核对今日时间与优质工单参数",
                    "expected_agent_correction": f"已为您核对确认：本次保障时间为{start}至{end}（时长{dur}），严格继承优质无丢包规格（{res} / 时延≤{rtt}），确认现在为您开通吗？",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    }
                },
                {
                    "turn": 4,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": "没错，就按无丢包的那单开通。",
                    "agent_hypothesis": "Agent按优质工单成功出单",
                    "expected_agent_correction": f"好的，已按优质历史工单为您成功受理保障，祝您网络体验顺畅！",
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
                    "agent": {"utterance": tree[0]["baseline_agent_flawed_response"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "in_progress", "closure_path": "flawed_baseline_attempt", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": "720p", "source_type": "Flawed_Record", "source_ref": "REC_FLAWED"}}, "rtt": {"max_value": {"value": "80ms", "source_type": "Flawed_Record", "source_ref": "REC_FLAWED"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"}}}}]
                },
                {
                    "turn": 2,
                    "user": {"utterance": tree[1]["simulator_user_prompt"], "action_types": ["Revise_Intent_Request", "Inform_Slot"]},
                    "agent": {"utterance": tree[1]["expected_agent_correction"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "in_progress", "closure_path": "quality_filtering", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Correction", "source_ref": "Quality_Log"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Correction", "source_ref": "Quality_Log"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"}}}}]
                },
                {
                    "turn": 3,
                    "user": {"utterance": tree[2]["simulator_user_prompt"], "action_types": ["Confirm_Slot"]},
                    "agent": {"utterance": tree[2]["expected_agent_correction"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "in_progress", "closure_path": "quality_filtering", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Correction", "source_ref": "Quality_Log"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Correction", "source_ref": "Quality_Log"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"}}}}]
                },
                {
                    "turn": 4,
                    "user": {"utterance": tree[3]["simulator_user_prompt"], "action_types": ["Confirm_Slot"]},
                    "agent": {"utterance": tree[3]["expected_agent_correction"], "action_types": ["Acknowledge"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "resolved", "closure_path": "clarification_after_correction", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Correction", "source_ref": "Quality_Log"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Correction", "source_ref": "Quality_Log"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"}}}}]
                }
            ]

        elif scenario_type == "overlapping_resolution":
            fast_cond = "自动时钟裁决：协调前单在交界点提前交割结单，新保障单准时无缝激活接管通道，2轮化解工单冲突"
            slow_cond = "系统报错时段重叠冲突甩锅用户退单重申，经历取消、重算、改期4轮拉扯"
            gate = {
                "eval_turn": 1,
                "decision_type": "overlapping_arbitration_check",
                "pass_condition": "Agent识别新申请与既有工单时段重叠冲突，主动执行时钟让路仲裁：原工单提前结单，新保障准时无缝激活 (EXP_OVERLAPPING_ORDER_RESOLUTION_01)",
                "fail_condition": "Agent直接报错时序重叠冲突拒绝受理，或甩锅要求用户手动去退单",
                "key_slot_assertions": {
                    "target_intent_id": "I1",
                    "checked_strategy": "clock_arbitration_yield",
                    "expected_action": "terminate_prior_and_activate_new"
                },
                "pass_route": "fast_path",
                "fail_route": "slow_path"
            }
            tree = [
                {
                    "turn": 1,
                    "speaker": "user",
                    "simulator_user_prompt": user_prompt,
                    "agent_hypothesis": "Agent检测到底层已有工单时段撞车，直接提示冲突报错甩锅",
                    "baseline_agent_flawed_response": f"抱歉，系统检测到您已预约了一笔保障（生效至{start}后），与新申请时段存在重叠冲突，无法受理。请您先手动取消退单后再重新申请。",
                    "expected_agent_correction": f"抱歉，系统检测到您已预约了一笔保障（生效至{start}后），与新申请时段存在重叠冲突，无法受理。请您先手动取消退单后再重新申请。",
                    "flaw_type": "mechanical_conflict_rejection",
                    "flaw_description": "缺乏底层工单时序仲裁能力，将工单系统冲突转嫁给用户手动退单",
                    "agent_action_types": ["Reject_Request"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    },
                    "baseline_flawed_slots": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}, "action": "Reject_Request"}
                    },
                    "delta_from_gt": {
                        "has_error": True,
                        "error_details": ["I1: Agent triggered Reject_Request instead of clock arbitration yield"],
                        "triggered_reaction": "on_action_error"
                    }
                },
                {
                    "turn": 2,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": "新申请的保障和之前的单子撞车了，不能直接报错甩锅让我手动退单啊！你们系统应该协调原工单提前结单，新保障准时接管才对！",
                    "agent_hypothesis": "Agent收到指责后协调底层时钟仲裁策略",
                    "expected_agent_correction": f"非常抱歉！已协调时钟让路仲裁方案：可在{start}交界点提前终止结单原工单，新{app}{srv}保障准时在{start}无缝接管网络通道，避免冲突和重复扣费，您看可以这样处理吗？",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    }
                },
                {
                    "turn": 3,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": "这样接续才合理，那提前结单的原工单不会产生额外扣费吧？",
                    "agent_hypothesis": "Agent解答计费疑虑并再次核实生效范围",
                    "expected_agent_correction": f"请您放心，原工单仅按实际使用截至{start}计算费用，绝不会重复扣费；新保障将于{start}至{end}准时生效，确认现在直接开通吗？",
                    "agent_action_types": ["Confirm_Slot"],
                    "expected_slots_gt": {
                        "I1": {"application_name": app, "service_name": srv, "resolution": res, "rtt": rtt, "timestamp": {"start_timestamp": start, "end_timestamp": end, "duration": dur}}
                    }
                },
                {
                    "turn": 4,
                    "speaker": "user_simulator",
                    "simulator_user_prompt": "好的，这样时序接续就可以，确认开通。",
                    "agent_hypothesis": "Agent完成时序让路仲裁出单",
                    "expected_agent_correction": f"好的，已为您完成时钟让路仲裁办理，原工单提前结单让路，新{app}保障准时接续生效！",
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
                    "agent": {"utterance": tree[0]["baseline_agent_flawed_response"], "action_types": ["Reject_Request"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "rejected", "closure_path": "mechanical_conflict_rejection", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"}}}}]
                },
                {
                    "turn": 2,
                    "user": {"utterance": tree[1]["simulator_user_prompt"], "action_types": ["Revise_Intent_Request", "Inform_Slot"]},
                    "agent": {"utterance": tree[1]["expected_agent_correction"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "in_progress", "closure_path": "clock_arbitration_yield", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Correction", "source_ref": "Agent"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"}}}}]
                },
                {
                    "turn": 3,
                    "user": {"utterance": tree[2]["simulator_user_prompt"], "action_types": ["Confirm_Slot"]},
                    "agent": {"utterance": tree[2]["expected_agent_correction"], "action_types": ["Confirm_Slot"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "in_progress", "closure_path": "clock_arbitration_yield", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Correction", "source_ref": "Agent"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"}}}}]
                },
                {
                    "turn": 4,
                    "user": {"utterance": tree[3]["simulator_user_prompt"], "action_types": ["Confirm_Slot"]},
                    "agent": {"utterance": tree[3]["expected_agent_correction"], "action_types": ["Acknowledge"]},
                    "related_intent_ids": ["I1"],
                    "requested_params": [],
                    "turn_intents": [{"intent_id": "I1", "status": "resolved", "closure_path": "clarification_after_correction", "expression_level": 1, "intent": f"{app}{srv}保障", "params": {"application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"}, "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"}, "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}}, "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}}, "timestamp": {"start_timestamp": {"value": start, "source_type": "Correction", "source_ref": "Agent"}, "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"}, "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"}}}}]
                }
            ]
        else:
            fast_cond = "Agent应用经验策略达成高效闭环"
            slow_cond = "Agent缺乏经验导致交互拉扯"
            gate = {"eval_turn": 1, "pass_condition": "命中经验", "fail_condition": "未命中经验", "pass_route": "fast_path", "fail_route": "slow_path"}
            tree = []
            full_slow_seq = []

        slow_rounds = len(tree) if tree else 4
        fast_rounds = 3 if scenario_type == "multi_intent_partition" else 2

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
            target_gt["I2"] = {
                "intent": f"{app2}{srv2}保障",
                "slots": {
                    "application_name": app2,
                    "service_name": srv2,
                    "resolution": res2,
                    "rtt": rtt2,
                    "timestamp": {
                        "start_timestamp": start2,
                        "end_timestamp": end2,
                        "duration": dur2
                    }
                }
            }
            reaction_matrix = {
                "on_slot_error": {
                    "description": "Agent发生跨意图污染，误将I1延误扩散至受保护意图I2的时段",
                    "trigger_condition": "agent_slots.get('I2.timestamp.start_timestamp') != ground_truth['I2']['slots']['timestamp']['start_timestamp']",
                    "monitored_slots": ["I2.timestamp.start_timestamp", "I2.timestamp.end_timestamp"],
                    "user_action_types": ["Revise_Intent_Request", "Inform_Slot"],
                    "simulator_reply": f"不对啊！我只让你把上午的{srv}延长，怎么把下午的{srv2}也往后推迟了？下午的时间绝对不能动！"
                },
                "on_slot_missing": {
                    "description": "Agent虽冻结锁定I2，但遗漏了上午任务延后后的总保障时长核算",
                    "trigger_condition": "not agent_slots.get('I1.timestamp.duration')",
                    "monitored_slots": ["I1.timestamp.duration"],
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": f"下午别动是对的，但我上午延后之后，总保障时长到底是按多久算的？你们系统到底算准了没有？"
                },
                "on_agent_inquiry": {
                    "description": "Agent向用户核验两笔保障各自网络指标独立完整性",
                    "trigger_condition": "agent_action in ['Request_Slot', 'Confirm_Slot']",
                    "user_action_types": ["Confirm_Slot", "Inform_Slot"],
                    "simulator_reply": f"行，时长算清楚了。那改期后上午和下午的网络规格（清晰度和时延）没被改乱吧？"
                },
                "on_goal_matched": {
                    "description": "两笔保障参数与时序完全核准对齐，用户确认闭环出单",
                    "trigger_condition": "agent_slots_all_matched and agent_action in ['Confirm_Slot', 'Acknowledge']",
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": "行，两边都对齐没问题了，确认开通。"
                }
            }
        elif scenario_type == "prewarm_buffer":
            reaction_matrix = {
                "on_slot_error": {
                    "description": "Agent机械按活动时间掐点预约，未执行提前30分钟试机预热推算",
                    "trigger_condition": "agent_slots.get('timestamp.start_timestamp') != ground_truth['I1']['slots']['timestamp']['start_timestamp']",
                    "monitored_slots": ["I1.timestamp.start_timestamp"],
                    "user_action_types": ["Revise_Intent_Request", "Inform_Slot"],
                    "simulator_reply": "等等，这是大型场馆活动，现场设备调试很多，掐着点开通根本来不及试机！必须提前半小时起保！"
                },
                "on_slot_missing": {
                    "description": "Agent虽修正了提前起保时间，但未向用户主动确认预热期的网络指标规格",
                    "trigger_condition": "not agent_slots.get('resolution') or not agent_slots.get('rtt')",
                    "monitored_slots": ["I1.resolution", "I1.rtt"],
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": "对，必须提前半小时试机才稳妥，那预热调试期间的网络指标还是保持高规格吧？"
                },
                "on_agent_inquiry": {
                    "description": "Agent主动询问用户预热起止时段或规格要求",
                    "trigger_condition": "agent_action in ['Request_Slot']",
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": f"保障时间要从{start}开始算，提前30分钟起保，规格按{res}和时延≤{rtt}。"
                },
                "on_goal_matched": {
                    "description": "提前预热起保时序与网络指标完全核准对齐，用户确认办理",
                    "trigger_condition": "agent_slots_all_matched and agent_action in ['Confirm_Slot', 'Acknowledge']",
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": "好的，这就稳妥了，确认开通。"
                }
            }
        elif scenario_type == "holiday_exception":
            reaction_matrix = {
                "on_slot_error": {
                    "description": "Agent未识别国庆长假，机械在办公室全员放假当天预约",
                    "trigger_condition": "agent_slots.get('timestamp.start_timestamp') == '2026年10月01日08时30分'",
                    "monitored_slots": ["I1.timestamp.start_timestamp"],
                    "user_action_types": ["Revise_Intent_Request", "Inform_Slot"],
                    "simulator_reply": "等等，下周一不是国庆长假第一天全员放假吗？办公室都没人，怎么还给我排在10月1号？"
                },
                "on_agent_inquiry": {
                    "description": "Agent识别假期冲突并撤销放假当天预约后，反问改期意图",
                    "trigger_condition": "agent_action in ['Request_Slot']",
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": "放假千万别空跑白扣费，按惯例自动顺延到节后上班第一天就行。"
                },
                "on_slot_missing": {
                    "description": "Agent顺延了日期但遗漏明确节后规格或扣费说明",
                    "trigger_condition": "not agent_slots.get('timestamp.duration')",
                    "monitored_slots": ["I1.timestamp.duration", "I1.resolution"],
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": f"顺延到节后的话，时长还是{dur}，清晰度规格没变吧？"
                },
                "on_goal_matched": {
                    "description": "节后首个工作日顺延时序与规格核准，用户确认办理",
                    "trigger_condition": "agent_slots_all_matched and agent_action in ['Confirm_Slot', 'Acknowledge']",
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": "对，放假千万别空跑，就顺延到10月8日开通吧。"
                }
            }
        elif scenario_type == "quality_disambiguation":
            reaction_matrix = {
                "on_slot_error": {
                    "description": "Agent盲目复用了网络异常或丢包的历史工单参数",
                    "trigger_condition": "agent_slots.get('resolution') != ground_truth['I1']['slots']['resolution'] or agent_slots.get('rtt') != ground_truth['I1']['slots']['rtt']",
                    "monitored_slots": ["I1.resolution", "I1.rtt"],
                    "user_action_types": ["Revise_Intent_Request", "Inform_Slot"],
                    "simulator_reply": "不对啊！你复用的这是哪天的工单？上周四那单网络有明显抖动丢包，千万别按那天的参数配，要按全程无丢包最好的那次配！"
                },
                "on_slot_missing": {
                    "description": "Agent过滤了异常单后，遗漏核对今日保障具体时序",
                    "trigger_condition": "not agent_slots.get('timestamp.start_timestamp')",
                    "monitored_slots": ["I1.timestamp.start_timestamp", "I1.timestamp.end_timestamp"],
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": "对，必须按无丢包那次最稳的来，那今天的起止时间没搞错吧？"
                },
                "on_agent_inquiry": {
                    "description": "Agent询问历史单据偏好或具体保障规格",
                    "trigger_condition": "agent_action in ['Request_Slot']",
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": f"按历史零丢包优质单据执行，规格为{res}，时延≤{rtt}，今日时段{start}至{end}。"
                },
                "on_goal_matched": {
                    "description": "优质无丢包工单规格继承无误，用户确认受理",
                    "trigger_condition": "agent_slots_all_matched and agent_action in ['Confirm_Slot', 'Acknowledge']",
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": "没错，就按无丢包的那单开通。"
                }
            }
        elif scenario_type == "overlapping_resolution":
            reaction_matrix = {
                "on_slot_error": {
                    "description": "Agent检测到底层已有工单时段撞车，直接提示冲突报错甩锅给用户手动退单",
                    "trigger_condition": "agent_action in ['Reject_Request']",
                    "monitored_slots": ["agent_action"],
                    "user_action_types": ["Revise_Intent_Request", "Inform_Slot"],
                    "simulator_reply": "新申请的保障和之前的单子撞车了，不能直接报错甩锅让我手动退单啊！你们系统应该协调原工单提前结单，新保障准时接管才对！"
                },
                "on_slot_missing": {
                    "description": "Agent协调让路方案但未向用户澄清计费与提前结单无额外扣费",
                    "trigger_condition": "not agent_clarified_billing",
                    "monitored_slots": ["billing_clarification"],
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": "这样接续才合理，那提前结单的原工单不会产生额外扣费吧？"
                },
                "on_agent_inquiry": {
                    "description": "Agent询问时钟仲裁方案细节或起止时段",
                    "trigger_condition": "agent_action in ['Request_Slot']",
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": f"让原工单在{start}提前结单，新保障准时在{start}至{end}接管。"
                },
                "on_goal_matched": {
                    "description": "时钟让路接续仲裁完成且计费说明明确，用户确认办理",
                    "trigger_condition": "agent_slots_all_matched and agent_action in ['Confirm_Slot', 'Acknowledge']",
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": "好的，这样时序接续就可以，确认开通。"
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
                    "simulator_reply": "确认无误，直接办理吧。"
                }
            }

        turn_level_gt = []
        for i, node in enumerate(tree):
            item = {
                "turn": node["turn"],
                "speaker": node["speaker"],
                "simulator_user_prompt": node.get("simulator_user_prompt", ""),
                "expected_agent_correction": node.get("expected_agent_correction", ""),
                "expected_agent_action_types": node.get("agent_action_types", []),
                "expected_slots_gt": node.get("expected_slots_gt", {}),
                "intents_status": {
                    tint["intent_id"]: tint["status"]
                    for tint in (full_slow_seq[i].get("turn_intents", []) if i < len(full_slow_seq) else [])
                }
            }
            if "baseline_flawed_slots" in node:
                item["baseline_flawed_slots"] = node["baseline_flawed_slots"]
            if "delta_from_gt" in node:
                item["delta_from_gt"] = node["delta_from_gt"]
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
                "每轮接收'联接'Agent输出的提参结果与话术，对比 target_ground_truth 与 turn_level_ground_truth 计算参数差分（Delta）。"
                "若存在参数错误或越权修改，触发 on_slot_error 并发出纠偏提示；"
                "若'联接'Agent发起槽位追问，触发 on_agent_inquiry 提供真值槽位；"
                "若'联接'Agent遗漏关键校验项（如时长核算或服务规格），触发 on_slot_missing 提醒核验；"
                "若所有参数均已正确命中且 Agent 提请开通，触发 on_goal_matched 确认闭环并收尾。"
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
        res2 = second_source.get("resolution", "1080p") if second_source else "1080p"
        rtt2 = second_source.get("rtt", "50ms") if second_source else "50ms"

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
        u_prompt = events[0]["user"]["utterance"] if events and "user" in events[0] else ""
        branching_info = cls._build_experience_branching(
            scenario_type="multi_intent_partition",
            exp_id=exp_id,
            rule_title=exp_c.get("title") or "多任务并行局部调整与时序因果隔离经验",
            learning_source_session=learning_source_session,
            user_prompt=u_prompt,
            ctx={
                "app": app, "srv": srv, "res": res, "rtt": rtt, "start": start, "end": end, "dur": dur,
                "app2": app2, "srv2": srv2, "res2": res2, "rtt2": rtt2, "start2": start2, "end2": end2, "dur2": dur2
            }
        )

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
            u_prompt = events[0]["user"]["utterance"] if events and "user" in events[0] else ""
            branching_info = cls._build_experience_branching(
                scenario_type="quality_disambiguation",
                exp_id=exp_id,
                rule_title=exp_c.get("title") or "基于历史工单网络质量日志的智能消歧经验",
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

            u_prompt = events[0]["user"]["utterance"] if events and "user" in events[0] else ""
            branching_info = cls._build_experience_branching(
                scenario_type="overlapping_resolution",
                exp_id=exp_id,
                rule_title=exp_c.get("title") or "工单时序重叠仲裁与让路接管经验",
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
                rule_title=exp_c.get("title") or "工单时序重叠仲裁与让路接管经验",
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
