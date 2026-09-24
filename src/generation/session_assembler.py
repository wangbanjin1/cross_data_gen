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
            return cls._assemble_t1_2(
                sid, uid, ref_time, tid, role, b_type, env, act, ood_goal,
                event_sequence, snapshot_before, memory_events, gold_after
            )
        elif tid == "X-1":
            return cls._assemble_x_1(
                sid, uid, ref_time, tid, role, b_type, env, act, ood_goal,
                app_name, srv_name, res_val, rtt_val, start_ts, end_ts, dur_val,
                event_sequence, snapshot_before, memory_events, gold_after
            )
        elif tid == "T2-2":
            return cls._assemble_t2_2(
                sid, uid, ref_time, tid, role, b_type, env, act,
                app_name, srv_name, res_val, rtt_val, start_ts, end_ts, dur_val,
                event_sequence, snapshot_before, memory_events, gold_after
            )
        elif tid == "T2-5":
            return cls._assemble_t2_5(
                sid, uid, ref_time, tid, role, b_type, env, act,
                app_name, srv_name, res_val, rtt_val, start_ts, end_ts, dur_val,
                event_sequence, snapshot_before, memory_events, gold_after,
                base_end_ts=s_plan.get("base_end_timestamp"),
                base_dur=s_plan.get("base_duration")
            )
        elif tid == "T2-3":
            return cls._assemble_t2_3(
                sid, uid, ref_time, tid, role, b_type, env, act,
                app_name, srv_name, res_val, rtt_val, start_ts, end_ts, dur_val,
                event_sequence, snapshot_before, memory_events, gold_after
            )
        else:
            return cls._assemble_standard(
                sid, uid, ref_time, tid, role, b_type, env, act,
                app_name, srv_name, res_val, rtt_val, start_ts, end_ts, dur_val,
                event_sequence, snapshot_before, memory_events, gold_after,
                round_count=s_plan["round_count"]
            )

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
                        "duration": {"value": dur, "source_type": "Context", "source_ref": "U1"},
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
                                "duration": {"value": dur, "source_type": "Context", "source_ref": "U1"},
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
    def _assemble_t2_2(cls, sid, uid, ref_time, tid, role, b_type, env, act, app, srv, res, rtt, start, end, dur, events, snap, mems, gold):
        sig = f"T2-2|2|1|I1:{app}/{srv}/3/clarify/resolved|none"
        intents = [
            {
                "intent_id": "I1",
                "status": "resolved",
                "closure_path": "clarify",
                "expression_level": 3,
                "intent": f"{app}{srv}保障",
                "params": {
                    "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
                    "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U2"},
                    "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U2"}},
                    "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U2"}},
                    "timestamp": {
                        "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U2"},
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
                        },
                    },
                    {
                        "turn": 2,
                        "params": {
                            "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U2"},
                            "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U2"}},
                            "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U2"}},
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
            events[0]["requested_params"] = ["service_name", "resolution", "rtt", "duration"]
            events[0]["turn_intents"] = [
                {
                    "intent_id": "I1",
                    "status": "in_progress",
                    "closure_path": "clarify",
                    "expression_level": 3,
                    "intent": f"{app}保障",
                    "params": {
                        "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
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
    def _assemble_standard(cls, sid, uid, ref_time, tid, role, b_type, env, act, app, srv, res, rtt, start, end, dur, events, snap, mems, gold, round_count):
        closure_path = "direct"
        app_src, app_ref = "Turn", "U1"
        srv_src, srv_ref = "Turn", "U1"
        res_src, res_ref = "Turn", "U1"
        rtt_src, rtt_ref = "Turn", "U1"

        if b_type == "main":
            if role == "evidence_session":
                closure_path = "clarified"
                app_src, app_ref = "Turn", "U1"
                srv_src, srv_ref = "Turn", "U1"
                res_src, res_ref = "Turn", "U2"
                rtt_src, rtt_ref = "Turn", "U2"
            elif role in ["reinforcement_session", "reuse_session"]:
                closure_path = "memory_filled"
                app_src, app_ref = "Memory", "MF_001"
                srv_src, srv_ref = "Memory", "MF_001"
                res_src, res_ref = "Memory", "MF_001"
                rtt_src, rtt_ref = "Memory", "MF_001"

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

        elif b_type == "event_reuse":
            closure_path = "memory_filled"
            app_src, app_ref = "Memory", "MF_001_v2"
            srv_src, srv_ref = "Memory", "MF_001_v2"
            res_src, res_ref = "Memory", "MF_001_v2"
            rtt_src, rtt_ref = "Memory", "MF_001_v2"

        elif b_type == "main_recovery":
            closure_path = "memory_filled"
            app_src, app_ref = "Memory", "MF_001"
            srv_src, srv_ref = "Memory", "MF_001"
            res_src, res_ref = "Memory", "MF_001"
            rtt_src, rtt_ref = "Memory", "MF_001"

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
                        "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                        "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
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

        sig = f"{tid}|{len(events)}|1|I1:{app}/{srv}/1/{closure_path}/resolved|none"
        end_src, end_ref = ("Turn", "U2") if role == "evidence_session" else ("Turn", "U1")
        dur_src, dur_ref = ("Turn", "U2") if role == "evidence_session" else ("Context", "U1")
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
                        "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
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
            "slot_updates": [{"intent_id": "I1", "turn_updates": slot_updates_turn}],
        }
