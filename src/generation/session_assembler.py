"""
会话组装器 (SessionAssembler)
负责根据模版规范（T2-4, T2-2, T2-1, T1-2, T2-5, X-1, T2-3, T1-1, T2-6~T2-10）
装配最终标准的 Session JSON 对象，包括 intents、slot_updates、skeleton_signature 与 scenario 元数据。
"""

from __future__ import annotations

from src.generation.assemblers import (
    ExperienceAssemblerMixin,
    ExperienceBranchingBuilderMixin,
    FactualAssemblerMixin,
    MultiIntentAndOODAssemblerMixin,
    WorkingMemoryAssemblerMixin,
)


class SessionAssembler(
    MultiIntentAndOODAssemblerMixin,
    FactualAssemblerMixin,
    WorkingMemoryAssemblerMixin,
    ExperienceAssemblerMixin,
    ExperienceBranchingBuilderMixin,
):
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
                learning_source_session=s_plan.get("learning_source_session"),
                nominal_start=s_plan.get("nominal_start_timestamp"),
                nominal_end=s_plan.get("nominal_end_timestamp"),
                nominal_dur=s_plan.get("nominal_duration")
            )

        if isinstance(res, dict) and "session_meta" in res:
            res["session_meta"]["memory_tier"] = s_plan.get("memory_tier", "factual_memory")
            res["session_meta"]["cold_hot_type"] = s_plan.get("cold_hot_type")
            res["session_meta"]["agility_factor"] = s_plan.get("agility_factor")
            if s_plan.get("retrieval_challenge_type"):
                res["session_meta"]["retrieval_challenge_type"] = s_plan.get("retrieval_challenge_type")
        return res

