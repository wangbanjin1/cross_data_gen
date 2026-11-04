"""
多轮对话批量渲染与组装引擎 (DialogueGenerator).
负责按批次将规划好的会话结构 (s_plan) 与记忆状态快照 (snapshot_before) 通过 Tau-Bench 风格逐轮双智能体仿真渲染为自然语言对话，
并调用 SessionAssembler 组装最终的 JSON 输出。
"""

from __future__ import annotations

import logging

from src.config.settings import Config
from src.generation.isolated_views import build_isolated_views
from src.generation.llm_client import LLMClient
from src.generation.session_assembler import SessionAssembler
from src.generation.tau_bench_simulator import TauBenchDualSimulator
from src.generation.turn_normalizer import normalize_dialogue_turn
from src.templates.prompts.dialogue_fallbacks import (
    get_fallback_agent_utterance,
    get_fallback_user_utterance,
    get_normalized_action_types,
)

logger = logging.getLogger(__name__)


class DialogueGenerator:
    """多轮对话批量渲染器 (支持 Tau-Bench 双智能体逐轮受控博弈仿真)."""

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()
        self.dual_simulator = TauBenchDualSimulator(self.llm)

    @staticmethod
    def _get_fallback_user_utterance(s_plan: dict, turn: int, role: str) -> str:
        return get_fallback_user_utterance(s_plan, turn, role)

    @staticmethod
    def _get_fallback_agent_utterance(s_plan: dict, turn: int, role: str, is_last: bool) -> str:
        return get_fallback_agent_utterance(s_plan, turn, role, is_last)

    @staticmethod
    def _get_normalized_action_types(
        s_plan: dict, turn: int, role: str, is_last: bool, raw_u_acts: list, raw_a_acts: list
    ) -> tuple[list[str], list[str]]:
        return get_normalized_action_types(s_plan, turn, role, is_last, raw_u_acts, raw_a_acts)

    @staticmethod
    def build_isolated_views(s_plan: dict, snapshot_before: dict) -> dict:
        return build_isolated_views(s_plan, snapshot_before)

    def _normalize_turn(self, raw_turn: dict, t_idx: int, role: str, is_last: bool, s_plan: dict) -> tuple[str, list[str], str, list[str]]:
        return normalize_dialogue_turn(raw_turn, t_idx, role, is_last, s_plan)

    def _render_batch_dialogue_turns(self, batch_items: list[tuple], persona: dict) -> dict[str, list[dict]]:
        """
        调用 TauBenchDualSimulator 执行 4 阶段双智能体逐轮交替仿真 (User Simulator <-> Agent Simulator)。
        """
        return self.dual_simulator.simulate_batch(batch_items, persona)

    def generate_sessions_batch(
        self,
        planned_items: list[tuple],
        persona: dict,
        batch_size: int | None = None,
    ) -> list[dict]:
        """按批次渲染并组装所有 Session."""
        bs = batch_size or Config.batch_size
        all_sessions: list[dict] = []

        for i in range(0, len(planned_items), bs):
            batch = planned_items[i : i + bs]
            sids = [item[0]["session_id"] for item in batch]
            logger.info("      -> Tau-Bench Dual-Agent Simulating batch [%d:%d]: %s", i, i + len(batch), ", ".join(sids))
            rendered_map = self._render_batch_dialogue_turns(batch, persona) if getattr(Config, "use_llm", True) else {}

            for s_plan, snap_before, mem_events, gold_after in batch:
                sid = s_plan["session_id"]
                rc = s_plan["round_count"]
                role = s_plan["memory_role"]
                raw_turns = rendered_map.get(sid, [])

                event_sequence = []
                for t_idx in range(1, rc + 1):
                    is_last = t_idx == rc
                    t_raw = raw_turns[t_idx - 1] if t_idx - 1 < len(raw_turns) else {}
                    u_utt, u_acts, a_utt, a_acts = self._normalize_turn(t_raw, t_idx, role, is_last, s_plan)
                    event_sequence.append(
                        {
                            "turn": t_idx,
                            "user": {"utterance": u_utt, "action_types": u_acts},
                            "agent": {"utterance": a_utt, "action_types": a_acts},
                        }
                    )

                session_obj = SessionAssembler.assemble(s_plan, snap_before, mem_events, gold_after, event_sequence)
                if "session_meta" in session_obj:
                    session_obj["session_meta"]["simulation_mode"] = "tau_bench_turn_by_turn_dual_agent"
                all_sessions.append(session_obj)

        return all_sessions


__all__ = ["DialogueGenerator"]
