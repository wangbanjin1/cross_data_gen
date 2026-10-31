from __future__ import annotations


class MultiIntentAndOODAssemblerMixin:
    """Assembler methods for out-of-domain rejection (T1-2), mixed intent (X-1), sub-storyline (T2-2/T3-1), and rehearsal override (T2-4)."""

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
        i1_params = {
            "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
            "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
            "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}},
            "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}},
            "timestamp": {
                "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"},
            },
        }
        intents = [
            {
                "intent_id": "I1",
                "status": "resolved",
                "closure_path": "direct",
                "expression_level": 1,
                "intent": f"{app}{srv}保障",
                "params": i1_params,
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
        slot_updates = [{"intent_id": "I1", "turn_updates": [{"turn": 1, "params": i1_params}]}]
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

    @staticmethod
    def _populate_t2_2_events(events: list[dict], cross_turn: bool, app: str, srv: str, rtt: str, start: str, end: str, dur: str, intents: list[dict]) -> None:
        if not events or len(events) < 2:
            return
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
                    "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"}},
                },
            }
        ]
        if cross_turn and len(events) >= 3:
            events[1]["requested_params"] = ["resolution"]
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
                            "timestamp": {"start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"}},
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
            slot_updates[0]["turn_updates"].append({"turn": 3, "params": {"resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U3"}}}})
        cls._populate_t2_2_events(events, cross_turn, app, srv, rtt, start, end, dur, intents)
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
    def _assemble_t2_4(cls, sid, uid, ref_time, tid, role, b_type, env, act, app, srv, res, rtt, start, end, dur, events, snap, mems, gold, second_source=None, experience_citation=None, base_end=None, base_dur=None, start2=None, end2=None, dur2=None, learning_source_session=None):
        """T2-4: 经验记忆开播前私下对词试机位应用选择会话 (2 轮 / 1 意图: 微信-视频通话)"""
        exp_c = experience_citation or {}
        exp_id = exp_c.get("experience_id") or "EXP_MULTI_INTENT_PARTITION_01"
        app, srv = "微信", "视频通话"
        sig = f"T2-4|{len(events)}|1|I1:{app}/{srv}/1/multi_intent_experience/resolved|none"
        params = {
            "application_name": {"value": app, "source_type": "Experience", "source_ref": exp_id},
            "service_name": {"value": srv, "source_type": "Experience", "source_ref": exp_id},
            "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}},
            "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}},
            "timestamp": {
                "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"},
            },
        }
        intents = [{"intent_id": "I1", "status": "resolved", "closure_path": "multi_intent_experience", "expression_level": 1, "intent": f"{app}{srv}保障", "params": params}]
        slot_updates = [{"intent_id": "I1", "turn_updates": [{"turn": 1, "params": params}, {"turn": 2, "params": {}}]}]
        if events and len(events) >= 2:
            events[0]["requested_params"] = []
            events[0]["turn_intents"] = [{**intents[0], "status": "in_progress"}]
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
            ctx={"app": app, "srv": srv, "res": res, "rtt": rtt, "start": start, "end": end, "dur": dur},
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
