from __future__ import annotations

import copy
from src.core.qc_validator import PrematureDisclosureValidator, QCValidator
from src.generation.dialogue_generator import DialogueGenerator


def _make_sample_plan(role: str = "reinforcement_session", template_id: str = "T2-1") -> dict:
    return {
        "session_id": "U001-S-03",
        "user_id": "U001",
        "reference_time": "2026年09月10日 12时30分",
        "memory_role": role,
        "memory_tier": "factual_memory",
        "blueprint_type": "main",
        "template_id": template_id,
        "round_count": 2,
        "intent_count": 1,
        "scenario_env": "大巴转场途中",
        "declaration_mode": "explicit_declaration",
        "storyline_trigger_type": "time_periodic",
        "period_type": "daily",
        "trigger_condition": "12:30-13:30",
        "target_params": {
            "application_name": "抖音",
            "service_name": "开直播",
            "resolution": "1080p",
            "rtt": "50ms",
            "start_timestamp": "2026年09月10日 12时30分",
            "end_timestamp": "2026年09月10日 14时30分",
            "duration": "120min",
        },
        "small_memory": {
            "type": "period_expression",
            "value": "午间例行",
            "target": "12:30-13:30",
        },
        "aliases": {
            "app_aliases": ["阿抖"],
            "service_aliases": ["直播推流"],
            "resolution_aliases": ["1080p原画"],
            "rtt_aliases": ["50ms以内"],
            "duration_aliases": ["两个小时"],
            "period_aliases": ["午间例行"],
        },
    }


def test_build_isolated_views_separates_user_and_agent_contexts() -> None:
    # Case 1: Hot-start reinforcement_session (resolution & rtt are memory_filled -> forbidden in User Turn 1)
    plan_reinf = _make_sample_plan(role="reinforcement_session", template_id="T2-1")
    snap_before = {
        "M_MAIN": {
            "application_name": "抖音",
            "service_name": "开直播",
            "resolution": "1080p",
            "rtt_max": "50ms",
            "status": "active",
        }
    }
    views_reinf = DialogueGenerator.build_isolated_views(plan_reinf, snap_before)
    u_view = views_reinf["user_private_view"]
    a_view = views_reinf["agent_observable_view"]

    assert "resolution" not in u_view["turn1_allowed_slots"]
    assert "rtt" not in u_view["turn1_allowed_slots"]
    assert "1080p" in u_view["turn1_forbidden_values"]
    assert "50ms" in u_view["turn1_forbidden_values"]
    assert a_view["snapshot_before"] == snap_before
    assert a_view["turn1_forbidden_values"] == []

    # Case 2: Cold-start evidence_session (resolution, rtt, duration are Turn 2 reveal -> forbidden in Turn 1 for BOTH User & Agent)
    plan_ev = _make_sample_plan(role="evidence_session", template_id="T2-1")
    views_ev = DialogueGenerator.build_isolated_views(plan_ev, {})
    u_ev = views_ev["user_private_view"]
    a_ev = views_ev["agent_observable_view"]

    assert set(u_ev["turn1_allowed_slots"].keys()) == {
        "scenario_env",
        "application_name",
        "service_name",
        "start_timestamp",
    }
    assert u_ev["turn2_reveal_slots"]["resolution"] == "1080p"
    assert u_ev["turn2_reveal_slots"]["rtt"] == "50ms"
    assert u_ev["turn2_reveal_slots"]["duration"] == "120min"
    assert set(a_ev["turn1_forbidden_values"]) == {"1080p", "50ms", "120min"}


def test_normalize_turn_strips_leaked_memory_filled_slots_in_turn1() -> None:
    gen = DialogueGenerator()
    plan_reinf = _make_sample_plan(role="reinforcement_session", template_id="T2-1")
    # Simulate an LLM response that leaked 1080p and 50ms in Turn 1 despite not using the word '老规矩'
    leaked_turn1 = {
        "turn": 1,
        "user_utterance": "今天在大巴转场途中，按午间例行用抖音开直播，画质1080p、50ms以内",
        "agent_utterance": "收到，按您午间例行记忆配置：抖音开直播、1080p、50ms以内、12时30分至14时30分（120min），确认开通吗？",
    }
    u_text, _, a_text, _ = gen._normalize_turn(leaked_turn1, 1, "reinforcement_session", False, plan_reinf)
    assert "1080p" not in u_text
    assert "50ms" not in u_text
    assert "1080p" in a_text
    assert "50ms" in a_text


def test_premature_disclosure_validator_catches_user_and_agent_turn1_leaks() -> None:
    base_session = {
        "session_id": "U001-S-01",
        "user_id": "U001",
        "reference_time": "2026年09月01日 12时30分",
        "session_meta": {
            "memory_role": "evidence_session",
            "memory_tier": "factual_memory",
            "template_id": "T2-1",
            "round_count": 2,
            "intent_count": 1,
            "skeleton_signature": "T2-1|2|1|test",
            "scenario": {"blueprint_type": "main", "environment": "大巴转场途中"},
        },
        "event_sequence": [
            {
                "turn": 1,
                "user": {"utterance": "今天12时30分在大巴转场途中要用抖音开直播", "action_types": ["Create_Intent_Request"]},
                "agent": {"utterance": "收到，请问画质、时延和持续时长是多少？", "action_types": ["Request_Slot"]},
                "turn_intents": [{"params": {"application_name": {"value": "抖音"}, "service_name": {"value": "开直播"}, "timestamp": {"start_timestamp": {"value": "2026年09月01日 12时30分"}}}}],
                "requested_params": ["resolution", "rtt", "duration"],
            },
            {
                "turn": 2,
                "user": {"utterance": "画质1080p、时延50ms以内，持续120min，以后午间例行都按这个来", "action_types": ["Inform_Slot"]},
                "agent": {"utterance": "好的，已为您开通并记录。", "action_types": ["Acknowledge"]},
                "turn_intents": [],
                "requested_params": [],
            },
        ],
        "intents": [
            {
                "id": "I1",
                "status": "accepted",
                "params": {
                    "application_name": {"value": "抖音"},
                    "service_name": {"value": "开直播"},
                    "resolution": {"value": "1080p"},
                    "rtt": {"value": "50ms"},
                    "timestamp": {"duration": {"value": "120min"}},
                },
            }
        ],
        "relations": [],
        "slot_updates": [],
    }

    # Clean session passes PrematureDisclosureValidator
    assert PrematureDisclosureValidator.check_session(base_session) == []

    # Contaminate Agent Turn 1 in cold-start evidence_session with unrevealed '1080p'
    leaked_agent_session = copy.deepcopy(base_session)
    leaked_agent_session["event_sequence"][0]["agent"]["utterance"] = "收到，已为您按1080p准备抖音开直播，请问时长多久？"
    issues_a = PrematureDisclosureValidator.check_session(leaked_agent_session)
    assert any("Agent Turn 1 违反信息隔离" in msg for msg in issues_a)
    qc_report = QCValidator.validate_sessions([leaked_agent_session])
    assert qc_report["rule_checks"]["premature_disclosure_check"] is False

    # Contaminate User Turn 1 in hot-start reinforcement_session with memory_filled '1080p'
    leaked_user_reinf = copy.deepcopy(base_session)
    leaked_user_reinf["session_meta"]["memory_role"] = "reinforcement_session"
    leaked_user_reinf["event_sequence"][0]["user"]["utterance"] = "今天在大巴转场途中用抖音开直播，画质1080p"
    issues_u = PrematureDisclosureValidator.check_session(leaked_user_reinf)
    assert any("User Turn 1 违反信息隔离" in msg for msg in issues_u)


def test_three_round_confirmation_closure_for_turn2_modifications() -> None:
    import tempfile
    from pathlib import Path
    from src.core.timeline_planner import DynamicTimelinePlanner
    from src.core.working_records_ledger import WorkingRecordsLedger
    from src.core.experience_bank import ExperienceBank
    from src.generation.session_assembler import SessionAssembler
    from src.templates.prompts.dialogue_fallbacks import (
        get_fallback_user_utterance,
        get_fallback_agent_utterance,
        get_normalized_action_types,
    )

    mock_persona = {
        "static_profile": {"user_id": "USER_001", "identity": "户外直播达人", "speech_style": {"tone": "自然", "catchphrases": "老规矩", "typical_habits": "简洁"}},
        "dynamic_profile": {
            "periodic_main_storyline": {
                "application_name": "抖音",
                "service_name": "开直播",
                "period_type": "daily",
                "time_range": "12:30-13:30",
                "preferred_params": {"resolution": "1080p", "rtt_max": "50ms"},
            },
            "scenario_events": [
                {
                    "event_name": "高山强风极限直播",
                    "scene_description": "高山露天训练场强风加大人流拥塞",
                    "preference_override": {"resolution": "720p", "rtt_max": "100ms"},
                }
            ],
            "sub_storylines": [
                {
                    "application_name": "腾讯会议",
                    "service_name": "音视频会议",
                    "params": {"resolution": "720p", "rtt_max": "80ms"},
                }
            ],
            "distractor_pool": [
                {"application_name": "中国移动", "service_name": "宽带报修"}
            ],
        },
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        ledger = WorkingRecordsLedger(user_id="USER_001", storage_path=Path(tmp_dir) / "working_records.jsonl")
        exp_bank = ExperienceBank()
        plans = DynamicTimelinePlanner.plan(persona=mock_persona, working_ledger=ledger, experience_bank=exp_bank)

    # All sessions where user introduces new/modified/corrected parameters in Turn 2 must be 3 rounds
    mod_sessions = [
        p for p in plans
        if p["blueprint_type"] in ("working_record_reuse", "experience_learning", "event_override")
        or p["template_id"] in ("T2-3", "T2-5")
    ]
    assert len(mod_sessions) >= 4
    for p in mod_sessions:
        sid = p["session_id"]
        assert p["round_count"] == 3, f"{sid} ({p['blueprint_type']}/{p['template_id']}) expected round_count=3, got {p['round_count']}"

        events = []
        for t in range(1, 4):
            is_last = t == 3
            u_act, a_act = get_normalized_action_types(p, t, p["memory_role"], is_last, [], [])
            events.append({
                "turn": t,
                "user": {"utterance": get_fallback_user_utterance(p, t, p["memory_role"]), "action_types": u_act},
                "agent": {"utterance": get_fallback_agent_utterance(p, t, p["memory_role"], is_last), "action_types": a_act},
            })
        assembled = SessionAssembler.assemble(p, {}, [], {}, events)
        ev_seq = assembled["event_sequence"]
        assert len(ev_seq) == 3
        assert "Confirm_Slot" in ev_seq[1]["agent"]["action_types"]
        assert "Acknowledge" not in ev_seq[1]["agent"]["action_types"]
        assert ev_seq[1]["turn_intents"][0]["status"] == "in_progress"
        assert "Confirm_Slot" in ev_seq[2]["user"]["action_types"]
        assert "Acknowledge" in ev_seq[2]["agent"]["action_types"]
        assert ev_seq[2]["turn_intents"][0]["status"] == "resolved"

