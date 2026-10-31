from __future__ import annotations


class FactualAssemblerMixin:
    """Assembler methods for standard factual/learning sessions, duration extension (T2-5), and temporary override (T2-3)."""

    @classmethod
    def _assemble_t2_5(cls, sid, uid, ref_time, tid, role, b_type, env, act, app, srv, res, rtt, start, end, dur, events, snap, mems, gold, base_end_ts=None, base_dur=None):
        sig = f"T2-5|{len(events)}|1|I1:{app}/{srv}/1/amend/resolved|none"
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
        turn_updates = [
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
        ]
        if events and len(events) >= 3:
            turn_updates.append({"turn": 3, "params": {}})
        slot_updates = [{"intent_id": "I1", "turn_updates": turn_updates}]
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
            if len(events) >= 3:
                events[1]["requested_params"] = []
                events[1]["turn_intents"] = [
                    {
                        "intent_id": "I1",
                        "status": "in_progress",
                        "closure_path": "amend",
                        "expression_level": 1,
                        "intent": f"{app}{srv}保障",
                        "params": intents[0]["params"],
                    }
                ]
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
    def _assemble_t2_3(cls, sid, uid, ref_time, tid, role, b_type, env, act, app, srv, res, rtt, start, end, dur, events, snap, mems, gold):
        sig = f"T2-3|{len(events)}|1|I1:{app}/{srv}/4/correct/resolved|none"
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
        turn_updates = [
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
        ]
        if events and len(events) >= 3:
            turn_updates.append({"turn": 3, "params": {}})
        slot_updates = [{"intent_id": "I1", "turn_updates": turn_updates}]
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
            if len(events) >= 3:
                events[1]["requested_params"] = []
                events[1]["turn_intents"] = [
                    {
                        "intent_id": "I1",
                        "status": "in_progress",
                        "closure_path": "correct",
                        "expression_level": 4,
                        "intent": f"{app}{srv}保障",
                        "params": intents[0]["params"],
                    }
                ]
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
    def _assemble_standard(cls, sid, uid, ref_time, tid, role, b_type, env, act, app, srv, res, rtt, start, end, dur, events, snap, mems, gold, round_count, small_memory_type=None, experience_citation=None, learning_source_session=None, nominal_start=None, nominal_end=None, nominal_dur=None):
        closure_path = "direct"
        app_src, app_ref = "Turn", "U1"
        srv_src, srv_ref = "Turn", "U1"
        res_src, res_ref = "Turn", "U1"
        rtt_src, rtt_ref = "Turn", "U1"
        start_src, start_ref = "Turn", "U1"
        end_src, end_ref = "Turn", "U1"
        dur_src, dur_ref = "Context", "U1"

        exp_c = experience_citation or {}
        exp_id = exp_c.get("experience_id")
        if exp_id == "EXP_CALENDAR_HOLIDAY_EXCEPTION_01" and b_type != "experience_learning":
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
            if exp_id == "EXP_PREWARM_BUFFER_01":
                res_src, res_ref = "Turn", "U1"
                rtt_src, rtt_ref = "Turn", "U1"
                start_src, start_ref = "Turn", "U2"
                end_src, end_ref = "Turn", "U1"
                dur_src, dur_ref = "Turn", "U2"
            else:
                res_src, res_ref = "Turn", "U2"
                rtt_src, rtt_ref = "Turn", "U2"
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

        t1_start = (nominal_start or start) if (b_type == "experience_learning" and exp_id == "EXP_PREWARM_BUFFER_01") else start
        t1_end = (nominal_end or end) if (b_type == "experience_learning" and exp_id == "EXP_PREWARM_BUFFER_01") else end
        t1_dur = (nominal_dur or dur) if (b_type == "experience_learning" and exp_id == "EXP_PREWARM_BUFFER_01") else dur
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
                elif b_type == "experience_learning" and exp_id == "EXP_PREWARM_BUFFER_01":
                    t_params["timestamp"] = {
                        "start_timestamp": {"value": t1_start, "source_type": "Turn", "source_ref": "U1"},
                        "end_timestamp": {"value": t1_end, "source_type": "Turn", "source_ref": "U1"},
                        "duration": {"value": t1_dur, "source_type": "Turn", "source_ref": "U1"},
                    }
                    t_params["resolution"] = {"min_value": {"value": res, "source_type": res_src, "source_ref": res_ref}}
                    t_params["rtt"] = {"max_value": {"value": rtt, "source_type": rtt_src, "source_ref": rtt_ref}}
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
                    if b_type == "experience_learning" and exp_id == "EXP_PREWARM_BUFFER_01":
                        t_params = {
                            "timestamp": {
                                "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U2"},
                                "duration": {"value": dur, "source_type": "Turn", "source_ref": "U2"},
                            }
                        }
                    else:
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
                            "resolution": {"min_value": {"value": "1080p" if (b_type == "experience_learning" and exp_id != "EXP_PREWARM_BUFFER_01") else res, "source_type": "Turn" if b_type == "experience_learning" else res_src, "source_ref": "U1" if b_type == "experience_learning" else res_ref}},
                            "rtt": {"max_value": {"value": "50ms" if (b_type == "experience_learning" and exp_id != "EXP_PREWARM_BUFFER_01") else rtt, "source_type": "Turn" if b_type == "experience_learning" else rtt_src, "source_ref": "U1" if b_type == "experience_learning" else rtt_ref}},
                            "timestamp": {
                                "start_timestamp": {"value": t1_start, "source_type": "Turn" if b_type == "experience_learning" else start_src, "source_ref": "U1" if b_type == "experience_learning" else start_ref},
                                "end_timestamp": {"value": t1_end, "source_type": "Turn" if b_type == "experience_learning" else end_src, "source_ref": "U1" if b_type == "experience_learning" else end_ref},
                                "duration": {"value": t1_dur, "source_type": "Turn" if b_type == "experience_learning" else dur_src, "source_ref": "U1" if b_type == "experience_learning" else dur_ref},
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

