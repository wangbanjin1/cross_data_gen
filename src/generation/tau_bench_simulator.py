# -*- coding: utf-8 -*-
"""
Tau-Bench 风格逐轮双智能体对话仿真器 (TauBenchDualSimulator)
------------------------------------------------------------------
通过物理隔离的 User Simulator LLM 与 Agent Simulator LLM 交替生成多轮对话：
Stage 1: User Simulator (仅见 turn1_allowed_slots + u1_instruction) -> 生成 Turn 1 用户台词 U1
Stage 2: Agent Simulator (仅见 U1 + agent_observable_view + a1_instruction) -> 检索记忆/单据并生成 Turn 1 响应 A1
Stage 3: User Simulator (见 [U1, A1] + turn2_reveal_slots + u2_instruction) -> 生成 Turn 2/3 用户补充/消歧台词 U2(/U3)
Stage 4: Agent Simulator (见 [U1, A1, U2(/U3)] + agent_observable_view + a2_instruction) -> 生成 Turn 2/3 闭环响应 A2(/A3)
"""

from __future__ import annotations

import json
import logging

from src.generation.isolated_views import build_isolated_views
from src.generation.llm_client import LLMClient
from src.generation.turn_normalizer import normalize_dialogue_turn
from src.templates.prompts.dialogue_fallbacks import get_fallback_user_utterance
from src.templates.prompts.tau_bench_prompts import (
    TAU_AGENT_TURN1_SYSTEM_PROMPT,
    TAU_AGENT_TURN1_USER_TEMPLATE,
    TAU_AGENT_TURN2_SYSTEM_PROMPT,
    TAU_AGENT_TURN2_USER_TEMPLATE,
    TAU_USER_TURN1_SYSTEM_PROMPT,
    TAU_USER_TURN1_USER_TEMPLATE,
    TAU_USER_TURN2_SYSTEM_PROMPT,
    TAU_USER_TURN2_USER_TEMPLATE,
    build_session_interaction_brief,
)

logger = logging.getLogger(__name__)


class TauBenchDualSimulator:
    """Tau-Bench 风格双智能体逐轮受控博弈仿真引擎（无预制台词锚点注入，自然产生快速闭环与多轮澄清）"""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def _call_stage_llm(self, sys_prompt: str, user_prompt: str) -> dict[str, dict]:
        try:
            res = self.llm.chat_json(
                [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                enable_thinking=False,
            )
            items = res.get("sessions", []) if isinstance(res, dict) else []
            return {it["session_id"]: it for it in items if isinstance(it, dict) and "session_id" in it}
        except Exception as exc:
            logger.warning("[TauBenchDualSimulator] Stage LLM call fallback triggered: %s", exc)
            return {}

    def _simulate_turn1_user(
        self,
        batch_items: list[tuple],
        views_map: dict[str, dict],
        briefs_map: dict[str, dict],
        persona: dict,
    ) -> dict[str, dict]:
        static = persona["static_profile"]
        style = static.get("speech_style", {})
        specs = []
        for s_plan, _, _, _ in batch_items:
            sid = s_plan["session_id"]
            u_view = views_map[sid]["user_private_view"]
            brief = briefs_map[sid]
            specs.append(
                {
                    "session_id": sid,
                    "reference_time": s_plan["reference_time"],
                    "template_id": s_plan["template_id"],
                    "memory_role": s_plan["memory_role"],
                    "round_count": s_plan["round_count"],
                    "interaction_mode": brief["interaction_mode"],
                    "u1_instruction": brief["u1_instruction"],
                    "turn1_allowed_slots": u_view["turn1_allowed_slots"],
                    "turn1_forbidden_values": u_view["turn1_forbidden_values"],
                }
            )
        prompt = TAU_USER_TURN1_USER_TEMPLATE.format(
            identity=static.get("identity", "移动互联网用户"),
            tone=style.get("tone", "自然口语"),
            catchphrases=", ".join(style.get("catchphrases", [])),
            typical_habits=style.get("typical_habits", "简洁直接"),
            turn1_user_specs_json=json.dumps(specs, ensure_ascii=False, indent=2),
        )
        return self._call_stage_llm(TAU_USER_TURN1_SYSTEM_PROMPT, prompt)

    def _simulate_turn1_agent(
        self,
        batch_items: list[tuple],
        views_map: dict[str, dict],
        briefs_map: dict[str, dict],
        u1_map: dict[str, dict],
    ) -> dict[str, dict]:
        specs = []
        for s_plan, _, _, _ in batch_items:
            sid = s_plan["session_id"]
            a_view = views_map[sid]["agent_observable_view"]
            brief = briefs_map[sid]
            u1_raw = (u1_map.get(sid) or {}).get("user_utterance") or get_fallback_user_utterance(
                s_plan, 1, s_plan["memory_role"]
            )
            specs.append(
                {
                    "session_id": sid,
                    "reference_time": s_plan["reference_time"],
                    "template_id": s_plan["template_id"],
                    "memory_role": s_plan["memory_role"],
                    "round_count": s_plan["round_count"],
                    "agility_factor": s_plan.get("agility_factor"),
                    "interaction_mode": brief["interaction_mode"],
                    "a1_instruction": brief["a1_instruction"],
                    "u1_utterance": u1_raw,
                    "agent_observable_view": a_view,
                }
            )
        prompt = TAU_AGENT_TURN1_USER_TEMPLATE.format(
            turn1_agent_specs_json=json.dumps(specs, ensure_ascii=False, indent=2)
        )
        return self._call_stage_llm(TAU_AGENT_TURN1_SYSTEM_PROMPT, prompt)

    def _simulate_turn2_user(
        self,
        multi_items: list[tuple],
        views_map: dict[str, dict],
        briefs_map: dict[str, dict],
        t1_norm_map: dict[str, tuple],
        persona: dict,
    ) -> dict[str, dict]:
        if not multi_items:
            return {}
        static = persona["static_profile"]
        style = static.get("speech_style", {})
        specs = []
        for s_plan, _, _, _ in multi_items:
            sid = s_plan["session_id"]
            rc = s_plan["round_count"]
            role = s_plan["memory_role"]
            u_view = views_map[sid]["user_private_view"]
            brief = briefs_map[sid]
            u1_txt, _, a1_txt, _ = t1_norm_map[sid]
            specs.append(
                {
                    "session_id": sid,
                    "reference_time": s_plan["reference_time"],
                    "template_id": s_plan["template_id"],
                    "memory_role": role,
                    "round_count": rc,
                    "interaction_mode": brief["interaction_mode"],
                    "u1_utterance": u1_txt,
                    "a1_utterance": a1_txt,
                    "u2_instruction": brief.get("u2_instruction", "自然确认或补充参数"),
                    "turn2_reveal_slots": u_view["turn2_reveal_slots"],
                }
            )
        prompt = TAU_USER_TURN2_USER_TEMPLATE.format(
            identity=static.get("identity", "移动互联网用户"),
            tone=style.get("tone", "自然口语"),
            catchphrases=", ".join(style.get("catchphrases", [])),
            turn2_user_specs_json=json.dumps(specs, ensure_ascii=False, indent=2),
        )
        return self._call_stage_llm(TAU_USER_TURN2_SYSTEM_PROMPT, prompt)

    def _simulate_turn2_agent(
        self,
        multi_items: list[tuple],
        views_map: dict[str, dict],
        briefs_map: dict[str, dict],
        t1_norm_map: dict[str, tuple],
        u2_map: dict[str, dict],
    ) -> dict[str, dict]:
        if not multi_items:
            return {}
        specs = []
        for s_plan, _, _, _ in multi_items:
            sid = s_plan["session_id"]
            rc = s_plan["round_count"]
            role = s_plan["memory_role"]
            brief = briefs_map[sid]
            u1_txt, _, a1_txt, _ = t1_norm_map[sid]
            u2_res = u2_map.get(sid) or {}
            u2_raw = u2_res.get("u2_utterance") or get_fallback_user_utterance(s_plan, 2, role)
            item = {
                "session_id": sid,
                "reference_time": s_plan["reference_time"],
                "template_id": s_plan["template_id"],
                "memory_role": role,
                "round_count": rc,
                "interaction_mode": brief["interaction_mode"],
                "u1_utterance": u1_txt,
                "a1_utterance": a1_txt,
                "u2_utterance": u2_raw,
                "a2_instruction": brief.get("a2_instruction", "确认参数并闭环"),
                "agent_observable_view": views_map[sid]["agent_observable_view"],
            }
            if rc >= 3:
                item["u3_utterance"] = u2_res.get("u3_utterance") or get_fallback_user_utterance(s_plan, 3, role)
            specs.append(item)
        prompt = TAU_AGENT_TURN2_USER_TEMPLATE.format(
            turn2_agent_specs_json=json.dumps(specs, ensure_ascii=False, indent=2)
        )
        return self._call_stage_llm(TAU_AGENT_TURN2_SYSTEM_PROMPT, prompt)

    def simulate_batch(self, batch_items: list[tuple], persona: dict) -> dict[str, list[dict]]:
        """执行 4 阶段双智能体交替仿真并返回每个 session_id 的标准化轮次字典列表。"""
        views_map = {
            s_plan["session_id"]: build_isolated_views(s_plan, snap_before)
            for s_plan, snap_before, _, _ in batch_items
        }
        briefs_map = {
            s_plan["session_id"]: build_session_interaction_brief(s_plan)
            for s_plan, _, _, _ in batch_items
        }
        u1_map = self._simulate_turn1_user(batch_items, views_map, briefs_map, persona)
        a1_map = self._simulate_turn1_agent(batch_items, views_map, briefs_map, u1_map)

        t1_norm_map: dict[str, tuple] = {}
        for s_plan, _, _, _ in batch_items:
            sid = s_plan["session_id"]
            rc = s_plan["round_count"]
            role = s_plan["memory_role"]
            raw_t1 = {
                "turn": 1,
                "user_utterance": (u1_map.get(sid) or {}).get("user_utterance", ""),
                "user_action_types": (u1_map.get(sid) or {}).get("user_action_types", []),
                "agent_utterance": (a1_map.get(sid) or {}).get("agent_utterance", ""),
                "agent_action_types": (a1_map.get(sid) or {}).get("agent_action_types", []),
            }
            t1_norm_map[sid] = normalize_dialogue_turn(raw_t1, 1, role, rc == 1, s_plan)

        multi_items = [it for it in batch_items if it[0]["round_count"] >= 2]
        u2_map = self._simulate_turn2_user(multi_items, views_map, briefs_map, t1_norm_map, persona)
        a2_map = self._simulate_turn2_agent(multi_items, views_map, briefs_map, t1_norm_map, u2_map)

        out_turns: dict[str, list[dict]] = {}
        for s_plan, _, _, _ in batch_items:
            sid = s_plan["session_id"]
            rc = s_plan["round_count"]
            role = s_plan["memory_role"]
            u1_txt, u1_acts, a1_txt, a1_acts = t1_norm_map[sid]
            turns = [
                {
                    "turn": 1,
                    "user_utterance": u1_txt,
                    "user_action_types": u1_acts,
                    "agent_utterance": a1_txt,
                    "agent_action_types": a1_acts,
                }
            ]
            if rc >= 2:
                u2_item = u2_map.get(sid) or {}
                a2_item = a2_map.get(sid) or {}
                raw_t2 = {
                    "turn": 2,
                    "user_utterance": u2_item.get("u2_utterance", ""),
                    "user_action_types": u2_item.get("u2_action_types", []),
                    "agent_utterance": a2_item.get("a2_utterance", ""),
                    "agent_action_types": a2_item.get("a2_action_types", []),
                }
                u2_txt, u2_acts, a2_txt, a2_acts = normalize_dialogue_turn(raw_t2, 2, role, rc == 2, s_plan)
                turns.append(
                    {
                        "turn": 2,
                        "user_utterance": u2_txt,
                        "user_action_types": u2_acts,
                        "agent_utterance": a2_txt,
                        "agent_action_types": a2_acts,
                    }
                )
            if rc >= 3:
                u2_item = u2_map.get(sid) or {}
                a2_item = a2_map.get(sid) or {}
                raw_t3 = {
                    "turn": 3,
                    "user_utterance": u2_item.get("u3_utterance", ""),
                    "user_action_types": u2_item.get("u3_action_types", []),
                    "agent_utterance": a2_item.get("a3_utterance", ""),
                    "agent_action_types": a2_item.get("a3_action_types", []),
                }
                u3_txt, u3_acts, a3_txt, a3_acts = normalize_dialogue_turn(raw_t3, 3, role, True, s_plan)
                turns.append(
                    {
                        "turn": 3,
                        "user_utterance": u3_txt,
                        "user_action_types": u3_acts,
                        "agent_utterance": a3_txt,
                        "agent_action_types": a3_acts,
                    }
                )
            out_turns[sid] = turns
        return out_turns
