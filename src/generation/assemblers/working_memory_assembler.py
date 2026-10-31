from __future__ import annotations


class WorkingMemoryAssemblerMixin:
    """Assembler methods for working memory cross-period reuse (T2-6), reschedule (T2-7), and ledger audit (T2-8)."""

    @staticmethod
    def _build_t2_6_exp_turns(app, srv, res, rtt, start, end, dur, exp_id, exp_c, wm_ptr, closure_path, intents, events):
        slot_updates = [
            {
                "intent_id": "I1",
                "turn_updates": [
                    {"turn": 1, "params": intents[0]["params"]},
                    {"turn": 2, "params": {}},
                ],
            }
        ]
        if events and len(events) >= 2:
            events[0]["requested_params"] = []
            events[0]["turn_intents"] = [{**intents[0], "status": "in_progress"}]
            events[0]["working_memory_pointer"] = wm_ptr
            events[0]["experience_citation"] = exp_c
            events[1]["requested_params"] = []
            events[1]["turn_intents"] = intents
        elif events and len(events) == 1:
            events[0]["requested_params"] = []
            events[0]["turn_intents"] = intents
            events[0]["working_memory_pointer"] = wm_ptr
            events[0]["experience_citation"] = exp_c
        return slot_updates

    @staticmethod
    def _build_t2_6_disambig_turns(app, srv, res, rtt, start, end, dur, rec_id, wm_ptr, closure_path, intents, events):
        t1_params = {
            "application_name": {"value": app, "source_type": "Turn", "source_ref": "U1"},
            "service_name": {"value": srv, "source_type": "Turn", "source_ref": "U1"},
            "timestamp": {
                "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                "duration": {"value": dur, "source_type": "Turn", "source_ref": "U1"},
            },
        }
        t2_params = {
            "application_name": {"value": app, "source_type": "WorkingRecord", "source_ref": rec_id},
            "service_name": {"value": srv, "source_type": "WorkingRecord", "source_ref": rec_id},
            "resolution": {"min_value": {"value": res, "source_type": "WorkingRecord", "source_ref": rec_id}},
            "rtt": {"max_value": {"value": rtt, "source_type": "WorkingRecord", "source_ref": rec_id}},
        }
        slot_updates = [{"intent_id": "I1", "turn_updates": [{"turn": 1, "params": t1_params}, {"turn": 2, "params": t2_params}, {"turn": 3, "params": {}}]}]
        events[0]["requested_params"] = ["target_record_id"]
        events[0]["turn_intents"] = [
            {
                "intent_id": "I1",
                "status": "in_progress",
                "closure_path": "working_record_disambig",
                "expression_level": 1,
                "intent": f"{app}{srv}保障",
                "params": t1_params,
            }
        ]
        events[0]["working_memory_pointer"] = wm_ptr
        events[1]["requested_params"] = []
        events[1]["turn_intents"] = [{**intents[0], "status": "in_progress", "closure_path": closure_path}]
        events[2]["requested_params"] = []
        events[2]["turn_intents"] = intents
        return slot_updates

    @staticmethod
    def _build_t2_6_standard_reuse_turns(app, srv, res, rtt, start, end, dur, rec_id, wm_ptr, intents, events):
        t1_params = {
            "application_name": {"value": app, "source_type": "WorkingRecord", "source_ref": rec_id},
            "service_name": {"value": srv, "source_type": "WorkingRecord", "source_ref": rec_id},
            "resolution": {"min_value": {"value": res, "source_type": "WorkingRecord", "source_ref": rec_id}},
            "rtt": {"max_value": {"value": rtt, "source_type": "WorkingRecord", "source_ref": rec_id}},
        }
        turn_updates = [
            {"turn": 1, "params": t1_params},
            {
                "turn": 2,
                "params": {
                    "timestamp": {
                        "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U2"},
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
            events[0]["requested_params"] = ["timestamp"]
            events[0]["turn_intents"] = [
                {
                    "intent_id": "I1",
                    "status": "in_progress",
                    "closure_path": "working_record_reuse",
                    "expression_level": 1,
                    "intent": f"{app}{srv}保障",
                    "params": t1_params,
                }
            ]
            events[0]["working_memory_pointer"] = wm_ptr
            if len(events) >= 3:
                events[1]["requested_params"] = []
                events[1]["turn_intents"] = [{**intents[0], "status": "in_progress"}]
                events[2]["requested_params"] = []
                events[2]["turn_intents"] = intents
            else:
                events[1]["requested_params"] = []
                events[1]["turn_intents"] = intents
        elif events and len(events) == 1:
            events[0]["requested_params"] = []
            events[0]["turn_intents"] = intents
            events[0]["working_memory_pointer"] = wm_ptr
        return slot_updates

    @classmethod
    def _assemble_t2_6(cls, sid, uid, ref_time, tid, role, b_type, env, act, app, srv, res, rtt, start, end, dur, events, snap, mems, gold, working_memory_pointer=None, experience_citation=None, learning_source_session=None):
        """T2-6: 工作记忆历史意图保障单跨期复用 (2 轮 / 3 轮消歧 / 经验记忆质量特征消歧)"""
        exp_c = experience_citation or {}
        exp_id = exp_c.get("experience_id")
        is_exp = bool(exp_c and exp_id == "EXP_ORDER_QUALITY_DISAMBIGUATION_01")
        wm_ptr = working_memory_pointer or {}
        rec_id = wm_ptr.get("target_record_id") or "REC_PRIOR"
        is_disambig = bool(wm_ptr.get("is_disambiguation", False))

        if is_exp:
            closure_path = "quality_disambiguated_reuse"
            app_src, app_ref = "Turn", "U1"
            srv_src, srv_ref = "Turn", "U1"
            res_src, res_ref = "Turn", "U1"
            rtt_src, rtt_ref = "Turn", "U1"
            ts_ref, end_src, end_ref, dur_src, dur_ref = "U1", "Experience", exp_id, "Experience", exp_id
        else:
            closure_path = "working_record_reuse"
            app_src, app_ref = "WorkingRecord", rec_id
            srv_src, srv_ref = "WorkingRecord", rec_id
            res_src, res_ref = "WorkingRecord", rec_id
            rtt_src, rtt_ref = "WorkingRecord", rec_id
            ts_ref = "U1" if is_disambig else "U2"
            end_src, end_ref, dur_src, dur_ref = "Turn", ts_ref, "Turn", ts_ref

        sig = f"T2-6|{len(events)}|1|I1:{app}/{srv}/1/{closure_path}/resolved|none"
        params = {
            "application_name": {"value": app, "source_type": app_src, "source_ref": app_ref},
            "service_name": {"value": srv, "source_type": srv_src, "source_ref": srv_ref},
            "resolution": {"min_value": {"value": res, "source_type": res_src, "source_ref": res_ref}},
            "rtt": {"max_value": {"value": rtt, "source_type": rtt_src, "source_ref": rtt_ref}},
            "timestamp": {
                "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": ts_ref},
                "end_timestamp": {"value": end, "source_type": end_src, "source_ref": end_ref},
                "duration": {"value": dur, "source_type": dur_src, "source_ref": dur_ref},
            },
        }
        intents = [{"intent_id": "I1", "status": "resolved", "closure_path": closure_path, "expression_level": 1, "intent": f"{app}{srv}保障", "params": params}]
        if is_exp:
            slot_updates = cls._build_t2_6_exp_turns(app, srv, res, rtt, start, end, dur, exp_id, exp_c, wm_ptr, closure_path, intents, events)
        elif is_disambig and len(events) >= 3:
            slot_updates = cls._build_t2_6_disambig_turns(app, srv, res, rtt, start, end, dur, rec_id, wm_ptr, closure_path, intents, events)
        else:
            slot_updates = cls._build_t2_6_standard_reuse_turns(app, srv, res, rtt, start, end, dur, rec_id, wm_ptr, intents, events)

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
                ctx={"app": app, "srv": srv, "res": res, "rtt": rtt, "start": start, "end": end, "dur": dur},
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
        params = {
            "application_name": {"value": app, "source_type": "WorkingRecord", "source_ref": rec_id},
            "service_name": {"value": srv, "source_type": "WorkingRecord", "source_ref": rec_id},
            "resolution": {"min_value": {"value": res, "source_type": "WorkingRecord", "source_ref": rec_id}},
            "rtt": {"max_value": {"value": rtt, "source_type": "WorkingRecord", "source_ref": rec_id}},
            "timestamp": {
                "start_timestamp": {"value": start, "source_type": "Turn", "source_ref": "U1"},
                "end_timestamp": {"value": end, "source_type": "Turn", "source_ref": "U1"},
                "duration": {"value": dur, "source_type": "WorkingRecord", "source_ref": rec_id},
            },
        }
        intents = [{"intent_id": "I1", "status": "resolved", "closure_path": "working_record_reschedule", "expression_level": 1, "intent": f"{app}{srv}保障", "params": params}]
        slot_updates = [{"intent_id": "I1", "turn_updates": [{"turn": 1, "params": params}, {"turn": 2, "params": {}}]}]
        if events and len(events) >= 2:
            events[0]["requested_params"] = []
            events[0]["turn_intents"] = [{**intents[0], "status": "in_progress"}]
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
