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
    def _dispatch_specialized_template(cls, tid: str, base_args: tuple, tp_args: tuple, tail_args: tuple, s_plan: dict) -> dict | None:
        ood_goal = s_plan.get("ood_goal", "")
        if tid == "T1-2":
            return cls._assemble_t1_2(*base_args, ood_goal, *tail_args)
        if tid == "X-1":
            return cls._assemble_x_1(*base_args, ood_goal, *tp_args, *tail_args)
        if tid in ["T2-2", "T3-1"]:
            return cls._assemble_t2_2(
                *base_args, *tp_args, *tail_args,
                evidence_mode=s_plan.get("small_memory_evidence_mode", "explicit_declaration"),
            )
        if tid == "T2-5":
            return cls._assemble_t2_5(
                *base_args, *tp_args, *tail_args,
                base_end_ts=s_plan.get("base_end_timestamp"),
                base_dur=s_plan.get("base_duration"),
            )
        if tid == "T2-3":
            return cls._assemble_t2_3(*base_args, *tp_args, *tail_args)
        if tid == "T2-4":
            return cls._assemble_t2_4(
                *base_args, *tp_args, *tail_args,
                experience_citation=s_plan.get("experience_citation", {}),
                second_source=s_plan.get("second_source"),
                learning_source_session=s_plan.get("learning_source_session"),
                base_end=s_plan.get("base_end") or s_plan.get("base_end_timestamp"),
                base_dur=s_plan.get("base_dur") or s_plan.get("base_duration"),
                start2=s_plan.get("start2"),
                end2=s_plan.get("end2"),
                dur2=s_plan.get("dur2"),
            )
        if tid == "T2-6":
            return cls._assemble_t2_6(
                *base_args, *tp_args, *tail_args,
                working_memory_pointer=s_plan.get("working_memory_pointer", {}),
                experience_citation=s_plan.get("experience_citation", {}),
                learning_source_session=s_plan.get("learning_source_session"),
            )
        if tid == "T2-7":
            return cls._assemble_t2_7(
                *base_args, *tp_args, *tail_args,
                working_memory_pointer=s_plan.get("working_memory_pointer", {}),
            )
        if tid == "T2-8":
            return cls._assemble_t2_8(
                *base_args, *tail_args,
                working_memory_query=s_plan.get("working_memory_query", {}),
            )
        if tid == "T2-9":
            return cls._assemble_t2_9(
                *base_args, *tp_args, *tail_args,
                experience_citation=s_plan.get("experience_citation", {}),
                learning_source_session=s_plan.get("learning_source_session"),
            )
        if tid == "T2-10":
            return cls._assemble_t2_10(
                *base_args, *tp_args, *tail_args,
                experience_citation=s_plan.get("experience_citation", {}),
                learning_source_session=s_plan.get("learning_source_session"),
            )
        return None

    @classmethod
    def assemble(
        cls,
        s_plan: dict,
        snapshot_before: dict,
        memory_events: list[dict],
        gold_after: dict,
        event_sequence: list[dict],
    ) -> dict:
        tp = s_plan["target_params"]
        base_args = (
            s_plan["session_id"],
            s_plan["user_id"],
            s_plan["reference_time"],
            s_plan["template_id"],
            s_plan["memory_role"],
            s_plan["blueprint_type"],
            s_plan["scenario_env"],
            s_plan["memory_action"],
        )
        tp_args = (
            tp["application_name"],
            tp["service_name"],
            tp["resolution"],
            tp["rtt"],
            tp["start_timestamp"],
            tp["end_timestamp"],
            tp["duration"],
        )
        tail_args = (event_sequence, snapshot_before, memory_events, gold_after)
        res = cls._dispatch_specialized_template(s_plan["template_id"], base_args, tp_args, tail_args, s_plan)
        if res is None:
            res = cls._assemble_standard(
                *base_args,
                *tp_args,
                *tail_args,
                round_count=s_plan["round_count"],
                small_memory_type=(s_plan.get("small_memory") or {}).get("type"),
                experience_citation=s_plan.get("experience_citation", {}),
                learning_source_session=s_plan.get("learning_source_session"),
                nominal_start=s_plan.get("nominal_start_timestamp"),
                nominal_end=s_plan.get("nominal_end_timestamp"),
                nominal_dur=s_plan.get("nominal_duration"),
            )
        if isinstance(res, dict) and "session_meta" in res:
            res["session_meta"]["memory_tier"] = s_plan.get("memory_tier", "factual_memory")
            res["session_meta"]["cold_hot_type"] = s_plan.get("cold_hot_type")
            res["session_meta"]["agility_factor"] = s_plan.get("agility_factor")
            if s_plan.get("retrieval_challenge_type"):
                res["session_meta"]["retrieval_challenge_type"] = s_plan.get("retrieval_challenge_type")
        return res
