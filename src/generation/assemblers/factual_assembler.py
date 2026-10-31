from __future__ import annotations


class FactualAssemblerMixin:
    """Assembler methods for standard factual/learning sessions, duration extension (T2-5), and temporary override (T2-3)."""

    @staticmethod
    def _populate_two_or_three_turn_events(events: list[dict], turn1_intent: dict, final_intents: list[dict]) -> None:
        if not events or len(events) < 2:
            return
        events[0]["requested_params"] = []
        events[0]["turn_intents"] = [turn1_intent]
        if len(events) >= 3:
            events[1]["requested_params"] = []
            events[1]["turn_intents"] = [
                {
                    **turn1_intent,
                    "params": final_intents[0]["params"],
                }
            ]
            events[2]["requested_params"] = []
            events[2]["turn_intents"] = final_intents
        else:
            events[1]["requested_params"] = []
            events[1]["turn_intents"] = final_intents

    @classmethod
    def _assemble_t2_5(cls, sid, uid, ref_time, tid, role, b_type, env, act, app, srv, res, rtt, start, end, dur, events, snap, mems, gold, base_end_ts=None, base_dur=None):
        sig = f"T2-5|{len(events)}|1|I1:{app}/{srv}/1/amend/resolved|none"
        if not base_end_ts:
            base_end_ts = end.replace("17时00分", "16时00分") if "17时00分" in end else end
        base_dur = base_dur or "120min"
        base_params = {
            "application_name": {"value": app, "source_type": "Memory", "source_ref": "MF_001"},
            "service_name": {"value": srv, "source_type": "Memory", "source_ref": "MF_001"},
            "resolution": {"min_value": {"value": res, "source_type": "Memory", "source_ref": "MF_001"}},
            "rtt": {"max_value": {"value": rtt, "source_type": "Memory", "source_ref": "MF_001"}},
        }
        intents = [
            {
                "intent_id": "I1",
                "status": "resolved",
                "closure_path": "amend",
                "expression_level": 1,
                "intent": f"{app}{srv}保障",
                "params": {
                    **base_params,
                    "timestamp": {
                        "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                        "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U2"},
                        "duration": {"value": dur, "source_type": "Turn", "source_ref": "U2"},
                    },
                },
            }
        ]
        t1_params = {
            **base_params,
            "timestamp": {
                "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                "end_timestamp": {"value": base_end_ts, "source_type": "Turn", "source_ref": "U1"},
                "duration": {"value": base_dur, "source_type": "Context", "source_ref": "U1"},
            },
        }
        turn_updates = [
            {"turn": 1, "params": t1_params},
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
        turn1_intent = {
            "intent_id": "I1",
            "status": "in_progress",
            "closure_path": "amend",
            "expression_level": 1,
            "intent": f"{app}{srv}保障",
            "params": t1_params,
        }
        cls._populate_two_or_three_turn_events(events, turn1_intent, intents)
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
            "slot_updates": [{"intent_id": "I1", "turn_updates": turn_updates}],
        }

    @classmethod
    def _assemble_t2_3(cls, sid, uid, ref_time, tid, role, b_type, env, act, app, srv, res, rtt, start, end, dur, events, snap, mems, gold):
        sig = f"T2-3|{len(events)}|1|I1:{app}/{srv}/4/correct/resolved|none"
        ts_params = {
            "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
            "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
            "duration": {"value": dur, "source_type": "Context", "source_ref": "U1"},
        }
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
                    "timestamp": ts_params,
                },
            }
        ]
        mf_001 = snap.get("MF_001", {}) if snap else {}
        base_res = mf_001.get("resolution", "1080p")
        base_rtt = mf_001.get("rtt_max", "50ms")
        t1_params = {
            "application_name": {"value": app, "source_type": "Memory", "source_ref": "MF_001"},
            "service_name": {"value": srv, "source_type": "Memory", "source_ref": "MF_001"},
            "resolution": {"min_value": {"value": base_res, "source_type": "Memory", "source_ref": "MF_001"}},
            "rtt": {"max_value": {"value": base_rtt, "source_type": "Memory", "source_ref": "MF_001"}},
            "timestamp": ts_params,
        }
        turn_updates = [
            {"turn": 1, "params": t1_params},
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
        turn1_intent = {
            "intent_id": "I1",
            "status": "in_progress",
            "closure_path": "correct",
            "expression_level": 4,
            "intent": f"{app}{srv}保障",
            "params": t1_params,
        }
        cls._populate_two_or_three_turn_events(events, turn1_intent, intents)
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
            "slot_updates": [{"intent_id": "I1", "turn_updates": turn_updates}],
        }

    @staticmethod
    def _resolve_standard_sources(role: str, b_type: str, snap: dict, exp_id: str | None, small_memory_type: str | None) -> dict:
        src = {
            "closure_path": "direct",
            "app": ("Turn", "U1"),
            "srv": ("Turn", "U1"),
            "res": ("Turn", "U1"),
            "rtt": ("Turn", "U1"),
            "start": ("Turn", "U1"),
            "end": ("Turn", "U1"),
            "dur": ("Context", "U1"),
        }
        if exp_id == "EXP_CALENDAR_HOLIDAY_EXCEPTION_01" and b_type != "experience_learning":
            src.update({"start": ("Experience", exp_id), "end": ("Experience", exp_id), "dur": ("Turn", "U1"), "closure_path": "holiday_avoidance_deferral"})
        elif b_type == "experience_learning":
            src["closure_path"] = "experience_crystallized"
            if exp_id == "EXP_PREWARM_BUFFER_01":
                src.update({"start": ("Turn", "U2"), "dur": ("Turn", "U2")})
            else:
                src.update({"res": ("Turn", "U2"), "rtt": ("Turn", "U2"), "dur": ("Turn", "U1")})

        if b_type in ["main", "sub_01", "sub_02"] and role == "evidence_session":
            src.update({"closure_path": "clarified", "res": ("Turn", "U2"), "rtt": ("Turn", "U2")})
        elif b_type == "main" and role in ["reinforcement_session", "reuse_session"]:
            is_prov = (snap.get("MF_001") or {}).get("status") == "provisional"
            s_type = "History" if is_prov else "Memory"
            src["closure_path"] = "history_filled" if is_prov else "memory_filled"
            for k in ["app", "srv", "res", "rtt", "start", "end", "dur"]:
                src[k] = (s_type, "MF_001")
        elif b_type in ["sub_01", "sub_02"] and role in ["reinforcement_session", "reuse_session"]:
            ref = "SUB_001" if b_type == "sub_01" else "SUB_002"
            src["closure_path"] = "memory_filled"
            for k in ["app", "srv", "res", "rtt", "start", "dur"]:
                src[k] = ("Memory", ref)
            src["end"] = ("Context", ref)
        elif b_type in ["event_reuse", "main_recovery"]:
            src["closure_path"] = "memory_filled"
            for k in ["app", "srv", "res", "rtt", "start", "end", "dur"]:
                src[k] = ("Memory", "MF_001")

        if role in ["reinforcement_session", "reuse_session"] and b_type in ["main", "sub_01", "sub_02"]:
            is_prov_main = b_type == "main" and (snap.get("MF_001") or {}).get("status") == "provisional"
            if not is_prov_main:
                if small_memory_type not in ["service_default_app", "application_alias"]:
                    src["app"] = ("Turn", "U1")
                src["srv"] = ("Turn", "U1")
        return src

    @staticmethod
    def _build_standard_slot_updates(round_count: int, role: str, b_type: str, exp_id: str | None, src: dict, vals: dict) -> list[dict]:
        slot_updates_turn = []
        is_prewarm_learn = b_type == "experience_learning" and exp_id == "EXP_PREWARM_BUFFER_01"
        for t_idx in range(1, round_count + 1):
            if t_idx == 1:
                t_params = {
                    "application_name": {"value": vals["app"], "source_type": src["app"][0], "source_ref": src["app"][1]},
                    "service_name": {"value": vals["srv"], "source_type": src["srv"][0], "source_ref": src["srv"][1]},
                }
                if role == "evidence_session":
                    t_params["timestamp"] = {"start_timestamp": {"value": vals["start"], "source_type": "Turn", "source_ref": "U1"}}
                elif is_prewarm_learn:
                    t_params["timestamp"] = {
                        "start_timestamp": {"value": vals["t1_start"], "source_type": "Turn", "source_ref": "U1"},
                        "end_timestamp": {"value": vals["t1_end"], "source_type": "Turn", "source_ref": "U1"},
                        "duration": {"value": vals["t1_dur"], "source_type": "Turn", "source_ref": "U1"},
                    }
                    t_params["resolution"] = {"min_value": {"value": vals["res"], "source_type": src["res"][0], "source_ref": src["res"][1]}}
                    t_params["rtt"] = {"max_value": {"value": vals["rtt"], "source_type": src["rtt"][0], "source_ref": src["rtt"][1]}}
                else:
                    t_params["timestamp"] = {
                        "start_timestamp": {"value": vals["start"], "source_type": src["start"][0], "source_ref": src["start"][1]},
                        "end_timestamp": {"value": vals["end"], "source_type": src["end"][0], "source_ref": src["end"][1]},
                        "duration": {"value": vals["dur"], "source_type": src["dur"][0], "source_ref": src["dur"][1]},
                    }
                    if role not in ["evidence_session", "correction_session"]:
                        t_params["resolution"] = {"min_value": {"value": vals["res"], "source_type": src["res"][0], "source_ref": src["res"][1]}}
                        t_params["rtt"] = {"max_value": {"value": vals["rtt"], "source_type": src["rtt"][0], "source_ref": src["rtt"][1]}}
                slot_updates_turn.append({"turn": 1, "params": t_params})
            elif t_idx == 2:
                t_params = {}
                if role in ["evidence_session", "correction_session"]:
                    if is_prewarm_learn:
                        t_params = {
                            "timestamp": {
                                "start_timestamp": {"value": vals["start"], "source_type": "Turn", "source_ref": "U2"},
                                "duration": {"value": vals["dur"], "source_type": "Turn", "source_ref": "U2"},
                            }
                        }
                    else:
                        t_params = {
                            "resolution": {"min_value": {"value": vals["res"], "source_type": src["res"][0], "source_ref": src["res"][1]}},
                            "rtt": {"max_value": {"value": vals["rtt"], "source_type": src["rtt"][0], "source_ref": src["rtt"][1]}},
                        }
                        if role == "evidence_session":
                            t_params["timestamp"] = {
                                "end_timestamp": {"value": vals["end"], "source_type": "Turn", "source_ref": "U2"},
                                "duration": {"value": vals["dur"], "source_type": "Turn", "source_ref": "U2"},
                            }
                slot_updates_turn.append({"turn": 2, "params": t_params})
            else:
                slot_updates_turn.append({"turn": t_idx, "params": {}})
        return slot_updates_turn

    @staticmethod
    def _populate_standard_evidence_events(events: list[dict], vals: dict, intents: list[dict]) -> None:
        events[0]["requested_params"] = ["resolution", "rtt", "duration"]
        events[0]["turn_intents"] = [
            {
                "intent_id": "I1",
                "status": "in_progress",
                "closure_path": "clarify",
                "expression_level": 1,
                "intent": f"{vals['app']}{vals['srv']}保障",
                "params": {
                    "application_name": {"value": vals["app"], "source_type": "Turn", "source_ref": "U1"},
                    "service_name": {"value": vals["srv"], "source_type": "Turn", "source_ref": "U1"},
                    "timestamp": {"start_timestamp": {"value": vals["start"], "source_type": "Turn", "source_ref": "U1"}},
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
                    "intent": f"{vals['app']}{vals['srv']}保障",
                    "params": {
                        "application_name": {"value": vals["app"], "source_type": "Turn", "source_ref": "U1"},
                        "service_name": {"value": vals["srv"], "source_type": "Turn", "source_ref": "U1"},
                        "resolution": {"min_value": {"value": vals["res"], "source_type": "Turn", "source_ref": "U2"}},
                        "rtt": {"max_value": {"value": vals["rtt"], "source_type": "Turn", "source_ref": "U2"}},
                        "timestamp": {
                            "start_timestamp": {"value": vals["start"], "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": vals["end"], "source_type": "Turn", "source_ref": "U2"},
                            "duration": {"value": vals["dur"], "source_type": "Turn", "source_ref": "U2"},
                        },
                    },
                }
            ]
            events[2]["requested_params"] = []
            events[2]["turn_intents"] = intents
        else:
            events[1]["requested_params"] = []
            events[1]["turn_intents"] = intents

    @staticmethod
    def _populate_standard_non_evidence_events(events: list[dict], b_type: str, exp_id: str | None, exp_c: dict, src: dict, vals: dict, intents: list[dict]) -> None:
        is_exp_learn = b_type == "experience_learning"
        is_other_learn = is_exp_learn and exp_id != "EXP_PREWARM_BUFFER_01"
        events[0]["requested_params"] = []
        events[0]["turn_intents"] = [
            {
                "intent_id": "I1",
                "status": "in_progress",
                "closure_path": src["closure_path"],
                "expression_level": 1,
                "intent": f"{vals['app']}{vals['srv']}保障",
                "params": {
                    "application_name": {"value": vals["app"], "source_type": src["app"][0], "source_ref": src["app"][1]},
                    "service_name": {"value": vals["srv"], "source_type": src["srv"][0], "source_ref": src["srv"][1]},
                    "resolution": {"min_value": {"value": "1080p" if is_other_learn else vals["res"], "source_type": "Turn" if is_exp_learn else src["res"][0], "source_ref": "U1" if is_exp_learn else src["res"][1]}},
                    "rtt": {"max_value": {"value": "50ms" if is_other_learn else vals["rtt"], "source_type": "Turn" if is_exp_learn else src["rtt"][0], "source_ref": "U1" if is_exp_learn else src["rtt"][1]}},
                    "timestamp": {
                        "start_timestamp": {"value": vals["t1_start"], "source_type": "Turn" if is_exp_learn else src["start"][0], "source_ref": "U1" if is_exp_learn else src["start"][1]},
                        "end_timestamp": {"value": vals["t1_end"], "source_type": "Turn" if is_exp_learn else src["end"][0], "source_ref": "U1" if is_exp_learn else src["end"][1]},
                        "duration": {"value": vals["t1_dur"], "source_type": "Turn" if is_exp_learn else src["dur"][0], "source_ref": "U1" if is_exp_learn else src["dur"][1]},
                    },
                },
            }
        ]
        if exp_c:
            events[0]["experience_citation"] = exp_c
        if len(events) >= 3:
            events[1]["requested_params"] = []
            events[1]["turn_intents"] = [{**intents[0], "status": "in_progress"}]
            events[2]["requested_params"] = []
            events[2]["turn_intents"] = intents
        else:
            events[1]["requested_params"] = []
            events[1]["turn_intents"] = intents

    @classmethod
    def _assemble_standard(cls, sid, uid, ref_time, tid, role, b_type, env, act, app, srv, res, rtt, start, end, dur, events, snap, mems, gold, round_count, small_memory_type=None, experience_citation=None, learning_source_session=None, nominal_start=None, nominal_end=None, nominal_dur=None):
        exp_c = experience_citation or {}
        exp_id = exp_c.get("experience_id")
        src = cls._resolve_standard_sources(role, b_type, snap or {}, exp_id, small_memory_type)
        is_prewarm_learn = b_type == "experience_learning" and exp_id == "EXP_PREWARM_BUFFER_01"
        vals = {
            "app": app, "srv": srv, "res": res, "rtt": rtt,
            "start": start, "end": end, "dur": dur,
            "t1_start": (nominal_start or start) if is_prewarm_learn else start,
            "t1_end": (nominal_end or end) if is_prewarm_learn else end,
            "t1_dur": (nominal_dur or dur) if is_prewarm_learn else dur,
        }
        slot_updates_turn = cls._build_standard_slot_updates(round_count, role, b_type, exp_id, src, vals)
        sig = f"{tid}|{len(events)}|1|I1:{app}/{srv}/1/{src['closure_path']}/resolved|none"
        if role == "evidence_session":
            src["end"] = ("Turn", "U2")
            src["dur"] = ("Turn", "U2")
        intents = [
            {
                "intent_id": "I1",
                "status": "resolved",
                "closure_path": src["closure_path"],
                "expression_level": 1,
                "intent": f"{app}{srv}保障",
                "params": {
                    "application_name": {"value": app, "source_type": src["app"][0], "source_ref": src["app"][1]},
                    "service_name": {"value": srv, "source_type": src["srv"][0], "source_ref": src["srv"][1]},
                    "resolution": {"min_value": {"value": res, "source_type": src["res"][0], "source_ref": src["res"][1]}},
                    "rtt": {"max_value": {"value": rtt, "source_type": src["rtt"][0], "source_ref": src["rtt"][1]}},
                    "timestamp": {
                        "start_timestamp": {"value": start, "source_type": src["start"][0], "source_ref": src["start"][1]},
                        "end_timestamp": {"value": end, "source_type": src["end"][0], "source_ref": src["end"][1]},
                        "duration": {"value": dur, "source_type": src["dur"][0], "source_ref": src["dur"][1]},
                    },
                },
            }
        ]
        if events and len(events) == 1:
            events[0]["requested_params"] = []
            events[0]["turn_intents"] = intents
        elif events and len(events) >= 2:
            if role == "evidence_session":
                cls._populate_standard_evidence_events(events, vals, intents)
            else:
                cls._populate_standard_non_evidence_events(events, b_type, exp_id, exp_c, src, vals, intents)
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
                    ctx={"app": app, "srv": srv, "res": res, "rtt": rtt, "start": start, "end": end, "dur": dur},
                )
                ret["experience_branching"] = branching_info
                ret["session_meta"]["experience_branching"] = branching_info
        return ret
