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

    @staticmethod
    def _build_intent_params(app: str, srv: str, res: str, rtt: str, start: str, end: str, dur: str, app_src: str = "Turn", app_ref: str = "U1", srv_src: str = "Turn", srv_ref: str = "U1") -> dict:
        return {
            "application_name": {"value": app, "source_type": app_src, "source_ref": app_ref},
            "service_name": {"value": srv, "source_type": srv_src, "source_ref": srv_ref},
            "resolution": {"min_value": {"value": res, "source_type": "Turn", "source_ref": "U1"}},
            "rtt": {"max_value": {"value": rtt, "source_type": "Turn", "source_ref": "U1"}},
            "timestamp": {
                "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"},
            },
        }

    @staticmethod
    def _resolve_second_intent_tuple(app: str, srv: str, res: str, rtt: str, start: str, end: str, dur: str, second_target_params: dict | None, second_source: dict | None, mode: str, start2: str | None, end2: str | None, dur2: str | None) -> tuple[str, str, str, str, str, str, str]:
        if isinstance(second_target_params, dict) and second_target_params.get("application_name"):
            return (
                second_target_params["application_name"],
                second_target_params["service_name"],
                second_target_params.get("resolution", res),
                second_target_params.get("rtt", rtt),
                second_target_params.get("start_timestamp") or start2 or start,
                second_target_params.get("end_timestamp") or end2 or end,
                second_target_params.get("duration") or dur2 or dur,
            )
        if mode == "homogeneous":
            peer_map = {"抖音": "快手", "快手": "抖音", "哔哩哔哩": "抖音", "腾讯会议": "钉钉", "钉钉": "腾讯会议", "飞书": "腾讯会议", "微信": "钉钉"}
            app2 = peer_map.get(app, "快手" if "直播" in srv else "钉钉")
            return app2, srv, res, rtt, start2 or start, end2 or end, dur2 or dur
        sec = second_source or {}
        app2 = sec.get("application_name") or ("抖音" if app == "微信" else "微信")
        srv2 = sec.get("service_name") or ("开直播" if srv == "视频通话" else "视频通话")
        if srv2 == srv:
            srv2 = "视频通话" if srv != "视频通话" else "开直播"
            app2 = "微信" if srv2 == "视频通话" else "抖音"
        sec_p = sec.get("preferred_params") or sec.get("params") or {}
        return app2, srv2, sec_p.get("resolution", res), sec_p.get("rtt_max", rtt), start2 or start, end2 or end, dur2 or dur

    @classmethod
    def _assemble_t1_3(cls, sid, uid, ref_time, tid, role, b_type, env, act, app, srv, res, rtt, start, end, dur, events, snap, mems, gold, second_target_params=None, second_source=None, multi_intent_mode="homogeneous", start2=None, end2=None, dur2=None):
        """T1-3: 单轮双正常意图并发闭环 (支持同类同构 homogeneous 与非同类异构 heterogeneous)"""
        app2, srv2, res2, rtt2, s2, e2, d2 = cls._resolve_second_intent_tuple(
            app, srv, res, rtt, start, end, dur, second_target_params, second_source, multi_intent_mode, start2, end2, dur2
        )
        rel_type = "parallel_homogeneous" if multi_intent_mode == "homogeneous" else "parallel_heterogeneous"
        sig = f"T1-3|{len(events)}|2|I1:{app}/{srv}/1/direct/resolved;I2:{app2}/{srv2}/1/direct/resolved|{rel_type}"
        p1 = cls._build_intent_params(app, srv, res, rtt, start, end, dur)
        p2 = cls._build_intent_params(app2, srv2, res2, rtt2, s2, e2, d2)
        intents = [
            {"intent_id": "I1", "status": "resolved", "closure_path": "direct", "expression_level": 1, "intent": f"{app}{srv}保障", "params": p1},
            {"intent_id": "I2", "status": "resolved", "closure_path": "direct", "expression_level": 1, "intent": f"{app2}{srv2}保障", "params": p2},
        ]
        slot_updates = [
            {"intent_id": "I1", "turn_updates": [{"turn": 1, "params": p1}]},
            {"intent_id": "I2", "turn_updates": [{"turn": 1, "params": p2}]},
        ]
        relations = [{"relation_id": "R1", "type": rel_type, "source_intent_id": "I1", "target_intent_id": "I2"}]
        if events and len(events) >= 1:
            events[0]["requested_params"] = []
            events[0]["related_intent_ids"] = ["I1", "I2"]
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
                "scenario": {"environment": env, "blueprint_type": b_type, "memory_action": act, "multi_intent_mode": multi_intent_mode},
            },
            "event_sequence": events,
            "intents": intents,
            "relations": relations,
            "slot_updates": slot_updates,
        }

    @classmethod
    def _assemble_t2_4(cls, sid, uid, ref_time, tid, role, b_type, env, act, app, srv, res, rtt, start, end, dur, events, snap, mems, gold, second_source=None, second_target_params=None, multi_intent_mode="heterogeneous", experience_citation=None, base_end=None, base_dur=None, start2=None, end2=None, dur2=None, learning_source_session=None):
        """T2-4: 多轮双正常意图会话 (2 轮 / 2 正常意图: I1 resolved + I2 resolved)"""
        exp_c = experience_citation or {}
        has_exp = bool(exp_c.get("experience_id")) or b_type == "multi_intent_experience"
        exp_id = exp_c.get("experience_id") or "EXP_MULTI_INTENT_PARTITION_01"
        if has_exp:
            app, srv = "微信", "视频通话"
        app2, srv2, res2, rtt2, s2, e2, d2 = cls._resolve_second_intent_tuple(
            app, srv, res, rtt, start, end, dur, second_target_params, second_source, multi_intent_mode, start2, end2, dur2
        )
        i1_closure = "multi_intent_experience" if has_exp else "direct"
        i2_closure = "direct" if has_exp else "add"
        p1 = cls._build_intent_params(app, srv, res, rtt, start, end, dur, app_src="Experience" if has_exp else "Turn", app_ref=exp_id if has_exp else "U1", srv_src="Experience" if has_exp else "Turn", srv_ref=exp_id if has_exp else "U1")
        p2 = cls._build_intent_params(app2, srv2, res2, rtt2, s2, e2, d2)
        sig = f"T2-4|{len(events)}|2|I1:{app}/{srv}/1/{i1_closure}/resolved;I2:{app2}/{srv2}/1/{i2_closure}/resolved|none"
        intents = [
            {"intent_id": "I1", "status": "resolved", "closure_path": i1_closure, "expression_level": 1, "intent": f"{app}{srv}保障", "params": p1},
            {"intent_id": "I2", "status": "resolved", "closure_path": i2_closure, "expression_level": 1, "intent": f"{app2}{srv2}保障", "params": p2},
        ]
        slot_updates = [
            {"intent_id": "I1", "turn_updates": [{"turn": 1, "params": p1}, {"turn": 2, "params": {}}]},
            {"intent_id": "I2", "turn_updates": [{"turn": 1, "params": p2}, {"turn": 2, "params": {}}]},
        ]
        rel_type = "sequential_heterogeneous" if multi_intent_mode == "heterogeneous" else "parallel_homogeneous"
        relations = [{"relation_id": "R1", "type": rel_type, "source_intent_id": "I1", "target_intent_id": "I2"}]
        if events and len(events) >= 2:
            events[0]["requested_params"] = []
            events[0]["related_intent_ids"] = ["I1", "I2"]
            events[0]["turn_intents"] = [{**intents[0], "status": "in_progress"}, {**intents[1], "status": "in_progress"}]
            if has_exp:
                events[0]["experience_citation"] = exp_c
            events[1]["requested_params"] = []
            events[1]["related_intent_ids"] = ["I1", "I2"]
            events[1]["turn_intents"] = intents
        u_prompt = events[0]["user"]["utterance"] if events and "user" in events[0] else ""
        branching_info = cls._build_experience_branching(
            scenario_type="multi_intent_partition",
            exp_id=exp_id,
            rule_title=exp_c.get("title") or "直播前私下跟搭档对词与看镜头机位（使用微信视频通话而非抖音开直播）经验",
            learning_source_session=learning_source_session,
            user_prompt=u_prompt,
            ctx={"app": app, "srv": srv, "res": res, "rtt": rtt, "start": start, "end": end, "dur": dur, "app2": app2, "srv2": srv2, "res2": res2, "rtt2": rtt2, "start2": s2, "end2": e2, "dur2": d2},
        ) if has_exp else None
        meta = {
            "template_id": tid,
            "round_count": len(events),
            "intent_count": 2,
            "memory_role": role,
            "memory_tier": "experiential_memory" if has_exp else "factual_memory",
            "skeleton_signature": sig,
            "scenario": {"environment": env, "blueprint_type": b_type, "memory_action": act, "multi_intent_mode": multi_intent_mode},
        }
        if has_exp:
            meta["experience_citation"] = exp_c
            meta["experience_branching"] = branching_info
        return {
            "session_id": sid,
            "user_id": uid,
            "reference_time": ref_time,
            "session_meta": meta,
            **({"experience_citation": exp_c, "experience_branching": branching_info} if has_exp else {}),
            "event_sequence": events,
            "intents": intents,
            "relations": relations,
            "slot_updates": slot_updates,
        }
