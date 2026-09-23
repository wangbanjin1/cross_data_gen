import json
from src.llm_client import LLMClient

class DialogueGenerator:
    """
    负责调用 DeepSeek API 将会话蓝图渲染为符合人物口吻、现场动机且严格遵守记忆规则的对话，
    支持高效低成本的批量生成 (Batch Generation) 并彻底关闭思考模式 (Thinking Disabled)，
    并将前置记忆快照注入 Prompt，保证 Agent 准确调用记忆反问确认；
    组装包含 memory_snapshot_before, memory_events_after, gold_memory_state_after 的标准对象。
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

            prompt_items.append({
                "session_id": sid,
                "rounds": rounds,
                "role": role,
                "blueprint_type": b_type,
                "declaration_mode": s_plan.get("declaration_mode", "explicit_declaration"),
                "time": s_plan["reference_time"],
                "env": env,
                "active_memory": snap_str,
                "app": tp["application_name"],
                "service": tp["service_name"],
                "resolution": tp["resolution"],
                "rtt": tp["rtt"],
                "duration": tp["duration"],
                "time_range": f"{tp['start_timestamp']} 至 {tp['end_timestamp']}"
            })

        prompt = f"""请根据以下人物画像背景与这组会话要求，为每个会话渲染真实、口语化的网络保障交互对话。

【人物风格】:
- 身份描述: {identity}
- 语气风格: {speech.get('tone')}
- 口头禅/表达习惯: {speech.get('catchphrases')} | {speech.get('typical_habits')}

【待生成会话列表】:
{json.dumps(prompt_items, ensure_ascii=False, indent=2)}

【核心会话轮次与动作规则（严格遵守）】:
1. 每个会话最后一轮必须由 Agent 的答复结束！最后一轮 Agent agent_action_types 必须包含 "Acknowledge"。
2. 首次建联/证据会话 (evidence_session):
   - 若 declaration_mode == "explicit_declaration" (显式声明):
     第1轮 User: 结合现场环境提出模糊需求；Agent 追问确认细节。
     第2轮 User: 明确说清参数，并【明确显式声明长期偏好与暗号】（如：“以后我在XX只要说‘下午大直播，老规矩’，就按这个来：抖音直播、1080p、50ms以内，先保连通再保清晰。记一下长期偏好，别掉链子”）；Agent 必须明确闭环回复：“好的，已为您开通本次保障，并已为您将该配置记录为长期老规矩！”
   - 若 declaration_mode == "implicit_induction" (隐式归纳):
     第1轮 User: 仅提出本次单次保障需求，【严禁出现任何‘记一下/以后都按这个/老规矩’等元指令词】（如：“今天下午有个网络保障，帮我开个抖音直播，1080p、50ms”）；Agent 追问确认细节。
     第2轮 User: 仅确认本次单次任务参数（如：“好的，今天就按这个配置开通”）；Agent 确认受理单次任务结束，不擅自假设长期偏好。
3. 记忆强化/复用 (reinforcement / reuse):
   - 若 active_memory 中包含 [provisional] (隐式偏好二次发生，触发固化契机):
     第1轮 User: 再次提出需求（如：“今天还是老时间开直播，跟上次一样就行”）。
     第1轮 Agent: 必须根据历史行为主动反问向用户建议固化：“检测到您周三下午多次使用该配置，是否按上次标准（1080p/50ms）为您开通并设为长期老规矩？”（agent_action_types包含 "Confirm_Slot"）。
     第2轮 User: 明确确认固化（如：“对，以后周三就按这个来”）（user_action_types包含 "Confirm_Slot"）。
     第2轮 Agent: 答复已开通并收尾祝福，正式记录老规矩（agent_action_types: ["Acknowledge"]）。
   - 若 active_memory 包含 [active] (常规复用已生效记忆):
     第1轮 User: 口语化提出需求，【必须省略应用或画质时延等参数】（如使用"老规矩"、"照上次的来"等）。
     第1轮 Agent: 必须明确调取上方 active_memory 中的配置，主动反问向用户确认（agent_action_types包含 "Confirm_Slot"）。
     第2轮 User: 明确确认 Agent 提出的配置（user_action_types包含 "Confirm_Slot"，如"对，开通吧"）。
     第2轮 Agent: 明确确认已开通并收尾祝福（agent_action_types: ["Acknowledge"]）。
4. 纠正覆盖 (correction / event_override):
   - 用户明确因当前特定事件/临时环境纠正旧参数，切换为新标准。
5. 单轮干扰项 (distractor):
   - 单轮内用户全部说清，Agent 正常受理直接结束。

【输出严格 JSON 格式】:
{{
  "sessions": [
    {{
      "session_id": "会话ID",
      "turns": [
        {{
          "turn": 1,
          "user_utterance": "用户第一句台词...",
          "user_action_types": ["Create_Intent_Request", "Inform_Slot"],
          "agent_utterance": "客服第一句回复...",
          "agent_action_types": ["Request_Slot"]
        }}
      ]
    }}
  ]
}}
"""
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

    def _assemble_session(self, s_plan: dict, persona: dict, snapshot_before: dict, memory_events: list[dict], gold_after: dict, raw_turns: list[dict]) -> dict:
        sid = s_plan["session_id"]
        uid = s_plan["user_id"]
        ref_time = s_plan["reference_time"]
        tid = s_plan["template_id"]
        role = s_plan["memory_role"]
        b_type = s_plan["blueprint_type"]
        tp = s_plan["target_params"]
        env = s_plan["scenario_env"]
        act = s_plan["memory_action"]

        app_name = tp["application_name"]
        srv_name = tp["service_name"]
        res_val = tp["resolution"]
        rtt_val = tp["rtt"]
        start_ts = tp["start_timestamp"]
        end_ts = tp["end_timestamp"]
        dur_val = tp["duration"]

        closure_path = "direct"
        app_src, app_ref = "Turn", "U1"
        srv_src, srv_ref = "Turn", "U1"
        res_src, res_ref = "Turn", "U1"
        rtt_src, rtt_ref = "Turn", "U1"

        if b_type == "main":
            if role == "evidence_session":
                closure_path = "clarified"
                app_src, app_ref = "Turn", "U2"
                res_src, res_ref = "Turn", "U2"
                rtt_src, rtt_ref = "Turn", "U2"
            elif role in ["reinforcement_session", "reuse_session"]:
                closure_path = "memory_filled"
                app_src, app_ref = "Memory", "MF_001"
                srv_src, srv_ref = "Memory", "MF_001"
                res_src, res_ref = "Memory", "MF_001"
                rtt_src, rtt_ref = "Memory", "MF_001"

        elif b_type == "sub_01":
            if role == "evidence_session":
                closure_path = "clarified"
                res_src, res_ref = "Turn", "U2"
                rtt_src, rtt_ref = "Turn", "U2"
            elif role in ["reinforcement_session", "reuse_session"]:
                closure_path = "memory_filled"
                app_src, app_ref = "Memory", "SUB_001"
                srv_src, srv_ref = "Memory", "SUB_001"
                res_src, res_ref = "Memory", "SUB_001"
                rtt_src, rtt_ref = "Memory", "SUB_001"

        elif b_type == "sub_02":
            if role == "evidence_session":
                closure_path = "clarified"
                res_src, res_ref = "Turn", "U2"
                rtt_src, rtt_ref = "Turn", "U2"
            elif role in ["reinforcement_session", "reuse_session"]:
                closure_path = "memory_filled"
                app_src, app_ref = "Memory", "SUB_002"
                srv_src, srv_ref = "Memory", "SUB_002"
                res_src, res_ref = "Memory", "SUB_002"
                rtt_src, rtt_ref = "Memory", "SUB_002"

        elif b_type == "event_override":
            closure_path = "corrected"
            app_src, app_ref = "Memory", "MF_001"
            srv_src, srv_ref = "Memory", "MF_001"
            res_src, res_ref = "Turn", "U2"
            rtt_src, rtt_ref = "Turn", "U2"

        elif b_type == "event_reuse":
            closure_path = "memory_filled"
            app_src, app_ref = "Memory", "MF_001_v2"
            srv_src, srv_ref = "Memory", "MF_001_v2"
            res_src, res_ref = "Memory", "MF_001_v2"
            rtt_src, rtt_ref = "Memory", "MF_001_v2"

        elif b_type == "main_recovery":
            closure_path = "memory_filled"
            app_src, app_ref = "Memory", "MF_001"
            srv_src, srv_ref = "Memory", "MF_001"
            res_src, res_ref = "Memory", "MF_001"
            rtt_src, rtt_ref = "Memory", "MF_001"

        target_rounds = s_plan["round_count"]
        event_sequence = []
        slot_updates_turn = []

        for turn_idx in range(1, target_rounds + 1):
            t_data = raw_turns[turn_idx - 1] if turn_idx <= len(raw_turns) else {}
            is_last = (turn_idx == target_rounds)
            u_text, u_acts, a_text, a_acts = self._normalize_turn(t_data, turn_idx, role, is_last, s_plan)

            req_params = []
            if turn_idx == 1 and role == "evidence_session":
                req_params = ["application_name", "resolution", "rtt"]

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
                "related_intent_ids": ["I1"],
                "requested_params": req_params
            }
            event_sequence.append(ev_item)

            if turn_idx == 1:
                t_params = {
                    "service_name": {"value": srv_name, "source_type": srv_src, "source_ref": srv_ref},
                    "timestamp": {
                        "start_timestamp": {"value": start_ts, "source_type": "Turn", "source_ref": "U1"},
                        "end_timestamp": {"value": end_ts, "source_type": "Turn", "source_ref": "U1"}
                    }
                }
                if role not in ["evidence_session", "correction_session"]:
                    t_params["application_name"] = {"value": app_name, "source_type": app_src, "source_ref": app_ref}
                    t_params["resolution"] = {"min_value": {"value": res_val, "source_type": res_src, "source_ref": res_ref}}
                    t_params["rtt"] = {"max_value": {"value": rtt_val, "source_type": rtt_src, "source_ref": rtt_ref}}
                slot_updates_turn.append({"turn": 1, "params": t_params})
            elif turn_idx == 2:
                t_params = {}
                if role in ["evidence_session", "correction_session"]:
                    t_params = {
                        "application_name": {"value": app_name, "source_type": app_src, "source_ref": app_ref},
                        "resolution": {"min_value": {"value": res_val, "source_type": res_src, "source_ref": res_ref}},
                        "rtt": {"max_value": {"value": rtt_val, "source_type": rtt_src, "source_ref": rtt_ref}}
                    }
                slot_updates_turn.append({"turn": 2, "params": t_params})

        session_obj = {
            "session_id": sid,
            "user_id": uid,
            "reference_time": ref_time,
            "session_meta": {
                "template_id": tid,
                "round_count": len(event_sequence),
                "intent_count": 1,
                "memory_role": role,
                "skeleton_signature": f"{tid}|{len(event_sequence)}|1|I1:{app_name}/{srv_name}/1/{closure_path}/resolved|none",
                "scenario": {
                    "environment": env,
                    "blueprint_type": b_type,
                    "memory_action": act
                }
            },
            "event_sequence": event_sequence,
            "intents": [
                {
                    "intent_id": "I1",
                    "status": "resolved",
                    "closure_path": closure_path,
                    "expression_level": 1,
                    "intent": f"{app_name}{srv_name}保障",
                    "params": {
                        "application_name": {"value": app_name, "source_type": app_src, "source_ref": app_ref},
                        "service_name": {"value": srv_name, "source_type": srv_src, "source_ref": srv_ref},
                        "resolution": {"min_value": {"value": res_val, "source_type": res_src, "source_ref": res_ref}},
                        "rtt": {"max_value": {"value": rtt_val, "source_type": rtt_src, "source_ref": rtt_ref}},
                        "timestamp": {
                            "start_timestamp": {"value": start_ts, "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": end_ts, "source_type": "Turn", "source_ref": "U1"},
                            "duration": {"value": dur_val, "source_type": "Context", "source_ref": "U1"}
                        }
                    }
                }
            ],
            "relations": [],
            "slot_updates": [{"intent_id": "I1", "turn_updates": slot_updates_turn}],
            "memory_snapshot_before": snapshot_before,
            "memory_events_after": memory_events,
            "gold_memory_state_after": gold_after
        }
        return session_obj

    def _normalize_turn(self, t_data: dict, turn_idx: int, role: str, is_last: bool, s_plan: dict):
        tp = s_plan["target_params"]
        app = tp["application_name"]
        srv = tp["service_name"]
        res = tp["resolution"]
        rtt = tp["rtt"]

        u_text = ""
        if isinstance(t_data, dict):
            u_text = (
                t_data.get("user_utterance")
                or t_data.get("user_query")
                or t_data.get("user_input")
                or (t_data.get("user", {}).get("utterance") if isinstance(t_data.get("user"), dict) else t_data.get("user"))
                or ""
            )
        decl_mode = s_plan.get("declaration_mode", "explicit_declaration")
        if not u_text:
            if turn_idx == 1:
                u_text = f"你好，需要给{app}{srv}做一个网络保障，时间是今天{tp['start_timestamp'].split('日')[-1]}开始，持续{tp['duration']}。"
            else:
                if role == "evidence_session" and decl_mode == "explicit_declaration":
                    u_text = f"好的，确认按这个配置直接开通。以后我在{env}只要说'下午大直播，老规矩'，就按这个来：{app}{srv}、{res}、{rtt}以内，记一下长期偏好，别掉链子。"
                elif role == "evidence_session" and decl_mode == "implicit_induction":
                    u_text = "好的，今天就按这个配置开通吧。"
                else:
                    u_text = "好的，确认按这个配置直接开通。"

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
            if is_last:
                if role == "evidence_session" and decl_mode == "explicit_declaration":
                    a_text = f"好的，已为您成功受理本次保障，并已为您将该配置记录为长期老规矩，祝您使用愉快！"
                else:
                    a_text = f"好的，已为您成功受理{app}{srv}网络保障（{res} / 时延≤{rtt}），祝您使用愉快！"
            else:
                if role == "reinforcement_session" and decl_mode == "implicit_induction" and s_plan.get("session_id", "").endswith("-03"):
                    a_text = f"检测到您周三下午多次使用{app}{srv}保障，请问是否按上次标准（{res} / 时延≤{rtt}）为您开通并设为默认老规矩？"
                else:
                    a_text = f"收到，请问{app}{srv}是否按分辨率{res}、时延上限{rtt}的标准来为您开通？"

        u_acts = t_data.get("user_action_types") if isinstance(t_data, dict) else None
        if turn_idx == 1:
            if not u_acts:
                u_acts = ["Create_Intent_Request", "Inform_Slot"]
            elif isinstance(u_acts, str):
                u_acts = [u_acts]
        else:
            if role in ["reinforcement_session", "reuse_session"]:
                u_acts = ["Confirm_Slot"]
            elif not u_acts:
                u_acts = ["Confirm_Slot"]
            elif isinstance(u_acts, str):
                u_acts = [u_acts]

        a_acts = t_data.get("agent_action_types") if isinstance(t_data, dict) else None
        if is_last:
            a_acts = ["Acknowledge"]
        elif role in ["reinforcement_session", "reuse_session"]:
            a_acts = ["Confirm_Slot"]
        elif not a_acts:
            a_acts = ["Request_Slot"] if role == "evidence_session" else ["Confirm_Slot"]
        elif isinstance(a_acts, str):
            a_acts = [a_acts]

        return u_text, u_acts, a_text, a_acts

    def _render_dialogue_turns(self, s_plan: dict, persona: dict, snapshot_before: dict) -> list[dict]:
        role = s_plan["memory_role"]
        b_type = s_plan["blueprint_type"]
        tp = s_plan["target_params"]
        env = s_plan["scenario_env"]
        speech = persona["static_profile"]["speech_style"]
        identity = persona["static_profile"]["identity"]
        round_count = s_plan["round_count"]

        if snapshot_before:
            memory_context_str = "当前已建立的记忆快照 (Memory Snapshot Before):\n"
            for mid, mval in snapshot_before.items():
                memory_context_str += f"  - [{mid}] 应用: {mval['application_name']}, 业务: {mval['service_name']}, 画质: {mval['resolution']}, 时延: {mval['rtt_max']}, 状态: {mval.get('status')}\n"
        else:
            memory_context_str = "当前记忆快照为空（首次建联会话，尚无已形成的长期记忆）。\n"

        prompt = f"""请根据以下人物背景、场景环境和记忆规则，渲染一段极其真实、口语化的多轮人机交互对话。

【人物画像】:
- 身份描述: {identity}
- 语气风格: {speech.get('tone')}
- 口头禅/表达习惯: {speech.get('catchphrases')} | {speech.get('typical_habits')}

【当前生效的历史记忆 (Memory Snapshot)】:
{memory_context_str}

【当前场景与网络动机】:
- 发生时间: {s_plan['reference_time']}
- 现场环境: {env}
- 会话角色: {role} (类型: {b_type})
- 偏好模式: {s_plan.get('declaration_mode', 'explicit_declaration')}
- 目标保障业务: 应用={tp['application_name']}, 业务={tp['service_name']}, 分辨率={tp['resolution']}, 时延上限={tp['rtt']}, 时段={tp['start_timestamp']} 至 {tp['end_timestamp']} (时长{tp['duration']})

【核心会话轮次与动作规则（严格遵守）】:
1. 最后一轮必须由 Agent 的答复结束！最后一轮 Agent agent_action_types 必须包含 "Acknowledge"。
2. 首次建联/证据会话 (evidence_session):
   - 若 declaration_mode == "explicit_declaration" (显式声明):
     第1轮 User: 结合现场环境提出模糊需求；Agent 追问确认细节。
     第2轮 User: 明确说清参数，并【明确显式声明长期偏好与暗号】（如：“以后我在XX只要说‘下午大直播，老规矩’，就按这个来：抖音直播、1080p、50ms以内，先保连通再保清晰。记一下长期偏好，别掉链子”）；Agent 必须明确闭环回复：“好的，已为您开通本次保障，并已为您将该配置记录为长期老规矩！”
   - 若 declaration_mode == "implicit_induction" (隐式归纳):
     第1轮 User: 仅提出本次单次保障需求，【严禁出现任何‘记一下/以后都按这个/老规矩’等元指令词】（如：“今天下午有个网络保障，帮我开个抖音直播，1080p、50ms”）；Agent 追问确认细节。
     第2轮 User: 仅确认本次单次任务参数（如：“好的，今天就按这个配置开通”）；Agent 确认受理单次任务结束，不擅自假设长期偏好。
3. 记忆强化/复用 (reinforcement / reuse):
   - 若上方记忆快照包含 [provisional] (隐式偏好二次发生，触发固化契机):
     第1轮 User: 再次提出需求（如：“今天还是老时间开直播，跟上次一样就行”）。
     第1轮 Agent: 必须根据历史行为主动反问向用户建议固化：“检测到您周三下午多次使用该配置，是否按上次标准（1080p/50ms）为您开通并设为长期老规矩？”（agent_action_types包含 "Confirm_Slot"）。
     第2轮 User: 明确确认固化（如：“对，以后周三就按这个来”）（user_action_types包含 "Confirm_Slot"）。
     第2轮 Agent: 答复已开通并收尾祝福，正式记录老规矩（agent_action_types: ["Acknowledge"]）。
   - 若上方记忆快照包含 [active] (常规复用已生效记忆):
     第1轮 User: 口语化提出需求，【必须省略应用或画质时延等参数】（如使用"老规矩"、"照上次的来"等）。
     第1轮 Agent: 必须明确调取上方 active_memory 中的配置，主动反问向用户确认（agent_action_types包含 "Confirm_Slot"）。
     第2轮 User: 明确确认 Agent 提出的配置（user_action_types包含 "Confirm_Slot"，如"对，开通吧"）。
     第2轮 Agent: 明确确认已开通并收尾祝福（agent_action_types: ["Acknowledge"]）。
4. 纠正覆盖 (correction / event_override):
   - 用户明确因当前特定事件/临时环境纠正旧参数，切换为新标准。
5. 单轮干扰项 (distractor):
   - 单轮内用户全部说清，Agent 正常受理直接结束。

【输出 JSON 格式（必须包含 {round_count} 轮）】:
{{
  "turns": [
    {{
      "turn": 1,
      "user_utterance": "用户第一句台词...",
      "user_action_types": ["Create_Intent_Request", "Inform_Slot"],
      "agent_utterance": "客服第一句回复...",
      "agent_action_types": ["Request_Slot"]
    }}
  ]
}}
"""
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
