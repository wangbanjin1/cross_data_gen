from __future__ import annotations


class ExperienceAssemblerMixin:
    """Assembler methods for proactive experience rules (T2-9) and empirical overlap/cohost resolution (T2-10)."""

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
