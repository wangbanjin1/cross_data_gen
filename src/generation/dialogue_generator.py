import json
from src.generation.llm_client import LLMClient
from src.generation.session_assembler import SessionAssembler
from src.templates.prompts import (
    build_batch_dialogue_prompt,
    build_single_dialogue_prompt,
    get_fallback_user_utterance,
    get_fallback_agent_utterance,
    get_normalized_action_types,
)

class DialogueGenerator:
    """
    对话台词渲染与会话装配器 (DialogueGenerator)
    负责调用 DeepSeek API 将会话蓝图批量渲染为真实、口语化的网络保障交互对话，
    并将生成的台词送入 SessionAssembler 装配为符合 8 大模版规范的标准数据对象。
    """

    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm_client or LLMClient()

    def generate_sessions_batch(self, session_items: list[tuple], persona: dict, batch_size: int = 5) -> list[dict]:
        """
        批量生成会话台词，大幅降低 API 调用次数与 Token 消耗。
        session_items: 包含 (s_plan, snapshot_before, memory_events, gold_after) 的元组列表
        """
        rendered_sessions = []

        for i in range(0, len(session_items), batch_size):
            chunk = session_items[i : i + batch_size]
            try:
                # 批量调用 DeepSeek 渲染该组会话台词
                batch_turns_map = self._render_batch_dialogue_turns(chunk, persona)
            except Exception as e:
                print(f"    [Warning] Batch LLM render failed: {e}. Falling back to single session rendering.")
                batch_turns_map = {}

            for s_plan, snap_before, mem_events, gold_after in chunk:
                sid = s_plan["session_id"]
                raw_turns = batch_turns_map.get(sid)
                if not raw_turns:
                    # 单会话兜底
                    raw_turns = self._render_dialogue_turns(s_plan, persona, snap_before)
                session_obj = self._assemble_session(s_plan, persona, snap_before, mem_events, gold_after, raw_turns)
                rendered_sessions.append(session_obj)

        return rendered_sessions

    def generate_session(self, s_plan: dict, persona: dict, snapshot_before: dict, memory_events: list[dict], gold_after: dict) -> dict:
        """单会话生成接口（保留兼容性）"""
        raw_turns = self._render_dialogue_turns(s_plan, persona, snapshot_before)
        return self._assemble_session(s_plan, persona, snapshot_before, memory_events, gold_after, raw_turns)

    def _render_batch_dialogue_turns(self, chunk: list[tuple], persona: dict) -> dict[str, list[dict]]:
        speech = persona["static_profile"]["speech_style"]
        identity = persona["static_profile"]["identity"]

        prompt_items = []
        for s_plan, snap_before, _, _ in chunk:
            sid = s_plan["session_id"]
            role = s_plan["memory_role"]
            b_type = s_plan["blueprint_type"]
            tp = s_plan["target_params"]
            env = s_plan["scenario_env"]
            rounds = s_plan["round_count"]

            if snap_before:
                snap_str = "; ".join([f"[{k}] {v['application_name']}-{v['service_name']}({v['resolution']},{v['rtt_max']})" for k, v in snap_before.items()])
            else:
                snap_str = "无"

            p_aliases = s_plan.get("aliases", {})
            aliases_info = {
                "app_aliases": p_aliases.get("app_aliases", []),
                "service_aliases": p_aliases.get("service_aliases", []),
                "resolution_aliases": p_aliases.get("resolution_aliases", []),
                "rtt_aliases": p_aliases.get("rtt_aliases", []),
                "duration_aliases": p_aliases.get("duration_aliases", []),
                "period_aliases": p_aliases.get("period_aliases", []),
            }

            t1_rule = "【大记忆点首次建立：第1轮严禁使用'老规矩'/'老时间'与别名，必须直述标准应用名与业务名】" if role == "evidence_session" else "【后续复用/强化：鼓励自然使用已沉淀的别名与老规矩】"
            prompt_items.append({
                "session_id": sid,
                "rounds": rounds,
                "role": role,
                "blueprint_type": b_type,
                "template_id": s_plan.get("template_id", "T2-1"),
                "turn1_requirement": t1_rule,
                "ood_goal": s_plan.get("ood_goal", ""),
                "declaration_mode": s_plan.get("declaration_mode", "explicit_declaration"),
                "storyline_trigger_type": s_plan.get("storyline_trigger_type", "time_periodic"),
                "period_type": s_plan.get("period_type", "weekly"),
                "trigger_condition": s_plan.get("trigger_condition", ""),
                "time": s_plan["reference_time"],
                "env": env,
                "active_memory": snap_str,
                "app": tp["application_name"],
                "service": tp["service_name"],
                "resolution": tp["resolution"],
                "rtt": tp["rtt"],
                "duration": tp["duration"],
                "time_range": f"{tp['start_timestamp']} 至 {tp['end_timestamp']}",
                "aliases": aliases_info
            })

        prompt = build_batch_dialogue_prompt(prompt_items, identity, speech)
        messages = [
            {"role": "system", "content": "You are a professional natural language dialogue generator for network assistant datasets. Output valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        res = self.llm.chat_json(messages, enable_thinking=False)
        output_map = {}
        if isinstance(res, dict) and "sessions" in res and isinstance(res["sessions"], list):
            for s_entry in res["sessions"]:
                if isinstance(s_entry, dict) and "session_id" in s_entry:
                    output_map[s_entry["session_id"]] = s_entry.get("turns", [])
        return output_map

    def _render_dialogue_turns(self, s_plan: dict, persona: dict, snapshot_before: dict) -> list[dict]:
        prompt = build_single_dialogue_prompt(s_plan, persona, snapshot_before)
        messages = [
            {"role": "system", "content": "You are a professional natural language dialogue generator for network assistant datasets."},
            {"role": "user", "content": prompt}
        ]
        res = self.llm.chat_json(messages, enable_thinking=False)
        if isinstance(res, list):
            return res
        if isinstance(res, dict):
            return res.get("turns") or res.get("conversation") or res.get("dialogue") or []
        return []

    def _assemble_session(self, s_plan: dict, persona: dict, snapshot_before: dict, memory_events: list[dict], gold_after: dict, raw_turns: list[dict]) -> dict:
        role = s_plan["memory_role"]
        target_rounds = s_plan["round_count"]
        tid = s_plan["template_id"]

        event_sequence = []
        for turn_idx in range(1, target_rounds + 1):
            t_data = raw_turns[turn_idx - 1] if turn_idx <= len(raw_turns) else {}
            is_last = (turn_idx == target_rounds)
            u_text, u_acts, a_text, a_acts = self._normalize_turn(t_data, turn_idx, role, is_last, s_plan)

            req_params = []
            if turn_idx == 1 and role == "evidence_session" and tid != "T2-2":
                req_params = ["resolution", "rtt", "duration"]
            elif turn_idx == 1 and tid == "T2-2":
                req_params = ["service_name", "resolution", "rtt", "duration"]

            rel_ids = ["I1", "I2"] if tid == "X-1" else ["I1"]
            ev_item = {
                "turn": turn_idx,
                "user": {
                    "utterance": u_text,
                    "action_types": u_acts
                },
                "agent": {
                    "utterance": a_text,
                    "action_types": a_acts
                },
                "related_intent_ids": rel_ids,
                "requested_params": req_params
            }
            event_sequence.append(ev_item)

        return SessionAssembler.assemble(
            s_plan=s_plan,
            snapshot_before=snapshot_before,
            memory_events=memory_events,
            gold_after=gold_after,
            event_sequence=event_sequence,
        )

    def _normalize_turn(self, t_data: dict, turn_idx: int, role: str, is_last: bool, s_plan: dict):
        u_text = ""
        if isinstance(t_data, dict):
            u_text = (
                t_data.get("user_utterance")
                or t_data.get("user_query")
                or t_data.get("user_input")
                or (t_data.get("user", {}).get("utterance") if isinstance(t_data.get("user"), dict) else t_data.get("user"))
                or ""
            )
        if not u_text:
            u_text = get_fallback_user_utterance(s_plan, turn_idx, role)

        if turn_idx == 1 and role == "evidence_session":
            for kw in ["老规矩，", "老规矩、", "老规矩 ", "老规矩", "老时间，", "老时间、", "老时间 ", "老时间", "老样子，", "老样子、", "老样子 "]:
                u_text = u_text.replace(kw, "")
            u_text = u_text.strip("，, ")

        a_text = ""
        if isinstance(t_data, dict):
            a_text = (
                t_data.get("agent_utterance")
                or t_data.get("agent_response")
                or t_data.get("agent_reply")
                or t_data.get("assistant_utterance")
                or t_data.get("response")
                or (t_data.get("agent", {}).get("utterance") if isinstance(t_data.get("agent"), dict) else t_data.get("agent"))
                or ""
            )
        if not a_text:
            a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)

        raw_u_acts = t_data.get("user_action_types") if isinstance(t_data, dict) else None
        raw_a_acts = t_data.get("agent_action_types") if isinstance(t_data, dict) else None
        u_acts, a_acts = get_normalized_action_types(s_plan, turn_idx, role, is_last, raw_u_acts, raw_a_acts)

        return u_text, u_acts, a_text, a_acts
