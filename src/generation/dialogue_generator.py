import json
import re
from src.generation.llm_client import LLMClient
from src.generation.session_assembler import SessionAssembler
from src.templates.prompts.small_memory_prompt import co_occurrence_example, declaration_example
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
            # 在常规复用/强化会话中，大记忆点已生效，用户只需使用应用/业务代称与个性化表达，必须省略画质/时延/时长参数
            if role in ["reinforcement_session", "reuse_session"] and s_plan.get("template_id") not in ["T2-3", "T2-5"]:
                aliases_info = {
                    "app_aliases": p_aliases.get("app_aliases", []),
                    "service_aliases": p_aliases.get("service_aliases", []),
                    "period_aliases": p_aliases.get("period_aliases", []),
                }
            else:
                aliases_info = {
                    "app_aliases": p_aliases.get("app_aliases", []),
                    "service_aliases": p_aliases.get("service_aliases", []),
                    "resolution_aliases": [r for r in p_aliases.get("resolution_aliases", []) if not any(b in r for b in ["顶格", "最高", "极限"])],
                    "rtt_aliases": [r for r in p_aliases.get("rtt_aliases", []) if not any(b in r for b in ["零卡顿", "秒开", "极速"])],
                    "duration_aliases": p_aliases.get("duration_aliases", []),
                    "period_aliases": p_aliases.get("period_aliases", []),
                }

            small_memory = s_plan.get("small_memory", {})
            primary_alias = small_memory.get("value") or tp["application_name"]
            small_memory_declaration = declaration_example(small_memory)
            evidence_mode = s_plan.get("small_memory_evidence_mode", "explicit_declaration")
            small_memory_co_occurrence = co_occurrence_example(small_memory)

            decl_mode = s_plan.get("declaration_mode", "explicit_declaration")
            is_implicit_reinf = (role == "reinforcement_session" and decl_mode == "implicit_induction" and sid.endswith("-03"))
            tid = s_plan.get("template_id", "T2-1")

            if tid == "T1-2":
                t1_rule = f"【纯域外拒绝：用户必须明确提出'{s_plan.get('ood_goal') or '宽带光纤装维报修'}'，不得提出任何应用网络保障或老规矩请求；Agent 必须明确说明不支持并拒绝办理。】"
            elif role == "evidence_session":
                if b_type == "main" and decl_mode == "implicit_induction":
                    t1_rule = f"【隐式归纳首次证据：第1轮必须直述标准应用名({tp['application_name']})、业务名({tp['service_name']})和精确开始时刻({tp['start_timestamp']})；第2轮只补充本次参数。严禁出现‘以后’‘记住’‘老规矩’或登记任何小记忆点，本轮结束后只能形成 provisional 历史记录。】"
                else:
                    t1_rule = f"【建立小记忆：证据模式={evidence_mode}。第1轮使用标准应用、业务和精确开始时刻。explicit_declaration 使用声明话术：{small_memory_declaration}；co_occurrence 使用同轮共现话术：{small_memory_co_occurrence}；cross_turn_clarification 必须用三轮，由用户先说模糊表达、Agent追问其是否对应标准值、用户最后确认。只登记指定类型={small_memory.get('type')}，不得登记其他别名。】"
            elif is_implicit_reinf:
                t1_rule = f"【隐式归纳二次发生固化契机：第1轮用户只表达‘这次按上次的来’，不得主动说出应用、业务、参数、起止时间；第1轮客服完整复述历史候选并要求确认；第2轮确认固化，小记忆证据模式={evidence_mode}，本会话使用同轮共现话术：{small_memory_co_occurrence}，不要改写成‘X就是Y’的显式定义。业务默认应用只对当前主线场景生效。】"
            elif tid == "T2-5":
                base_dur = s_plan.get("base_dur") or "60min"
                t1_rule = (
                    f"【时长延长会话：第1轮用户必须满足最小表达，表达'今天在{env}，老规矩，用{tp['application_name']}做{tp['service_name']}，帮我把保障开上'（严禁在第1轮提及画质、时延与修改后的时长！）；"
                    f"第1轮客服调取原基线老规矩配置向用户确认（基线时长为{base_dur}，严禁在第1轮提前说出修改后的时长{tp['duration']}！）；"
                    f"第2轮用户确认老规矩不变，但说明因现场活动延长等原因提出将时长延长到{tp['duration']}；"
                    f"第2轮客服确认按老规矩开通并将时长延长至{tp['duration']}。】"
                )
            elif tid == "T2-3":
                t1_rule = (
                    f"【临时纠正覆盖会话：第1轮用户必须满足最小表达，表达'今天在{env}，老规矩，用{tp['application_name']}做{tp['service_name']}，帮我把保障开上'；"
                    f"第1轮客服反问确认老规矩；"
                    f"第2轮用户说明因现场特殊临时调整画质为{tp['resolution']}、时延为{tp['rtt']}；"
                    f"第2轮客服确认本次临时调整。】"
                )
            elif tid == "X-1":
                t1_rule = f"【混合诉求（一办一拒）：单轮干扰会话，无先验记忆。用户首次提出业务需求，同时提出域外需求'{s_plan.get('ood_goal') or '手机话费充值与账单查询'}'；严禁使用未建立过的个性化表达或老规矩；Agent 正常受理域内业务，并明确礼貌拒绝办理域外需求。】"
            else:
                t1_rule = f"【常规复用/强化会话：大记忆点已生效。应用＋业务是最小表达：若小记忆类型为service_default_app，可只说业务；若为application_alias，必须说应用别名＋业务；若为画质/时延/时长/个性化周期表达，必须说标准应用＋业务＋该个性化表达。指定小记忆点='{primary_alias}'。Agent 从记忆中补全其余画质{tp['resolution']}、时延{tp['rtt']}、开始时间{tp['start_timestamp']}、结束时间{tp['end_timestamp']}和时长{tp['duration']}；不得把未说出的槽位标成 Turn 来源。】"

            prompt_items.append({
                "session_id": sid,
                "rounds": rounds,
                "role": role,
                "blueprint_type": b_type,
                "template_id": s_plan.get("template_id", "T2-1"),
                "turn1_requirement": t1_rule,
                "primary_alias": primary_alias,
                "small_memory": small_memory,
                "small_memory_declaration": small_memory_declaration,
                "small_memory_evidence_mode": evidence_mode,
                "small_memory_co_occurrence": small_memory_co_occurrence,
                "ood_goal": s_plan.get("ood_goal", ""),
                "declaration_mode": decl_mode,
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
            if turn_idx == 1 and role == "evidence_session":
                req_params = ["resolution", "rtt", "duration"]
            elif turn_idx == 2 and tid == "T3-1":
                req_params = ["resolution"]

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

        tp = s_plan.get("target_params", {})
        tid = s_plan.get("template_id", "T2-1")

        # 纯域外拒绝不能接受 LLM 渲染出的域内“老规矩”对话。
        if tid == "T1-2":
            u_text = get_fallback_user_utterance(s_plan, turn_idx, role)

        # 单轮干扰任务：必须清晰说全参数，严禁携带任何个性化表达/模糊词
        if tid == "T1-1" or s_plan.get("blueprint_type") == "distractor":
            bad_dist_kws = ["清晰点就行", "不卡就行", "一会儿", "老规矩", "老时间", "照旧", "按习惯"]
            if any(kw in u_text for kw in bad_dist_kws) or tp.get("resolution", "") not in u_text or tp.get("rtt", "") not in u_text:
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)

        # 临时纠正覆盖：第1轮必须满足场景+应用+业务的最小表达，第2轮必须包含特殊现场与调整参数
        if tid == "T2-3" or s_plan.get("blueprint_type") == "event_override":
            app = tp.get("application_name", "")
            srv = tp.get("service_name", "")
            env = s_plan.get("scenario_env", "")
            if turn_idx == 1:
                has_app = app in u_text or any(a in u_text for a in s_plan.get("aliases", {}).get("app_aliases", []))
                has_srv = srv in u_text or any(a in u_text for a in s_plan.get("aliases", {}).get("service_aliases", []))
                has_env = env in u_text or "现场" in u_text
                if not (has_app and has_srv and has_env):
                    u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
            elif turn_idx == 2:
                if tp.get("resolution", "") not in u_text or tp.get("rtt", "") not in u_text or "特殊" not in u_text:
                    u_text = get_fallback_user_utterance(s_plan, turn_idx, role)

        # 时长延长会话(T2-5)：第1轮必须满足场景+应用+业务的最小表达，第2轮必须包含时长延长
        if tid == "T2-5":
            app = tp.get("application_name", "")
            srv = tp.get("service_name", "")
            env = s_plan.get("scenario_env", "")
            if turn_idx == 1:
                has_app = app in u_text or any(a in u_text for a in s_plan.get("aliases", {}).get("app_aliases", []))
                has_srv = srv in u_text or any(a in u_text for a in s_plan.get("aliases", {}).get("service_aliases", []))
                has_env = env in u_text or any(k in u_text for k in ["现场", "营地", "训练场", "岸线", "途中", "休息区", "研讨会"])
                if not (has_app and has_srv and has_env):
                    u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
            elif turn_idx == 2:
                if tp.get("duration", "") not in u_text and "延长" not in u_text and "时长" not in u_text:
                    u_text = get_fallback_user_utterance(s_plan, turn_idx, role)

        # 证据会话首轮必须与规划的精确开始时间一致，避免模糊改写造成 turn-level 泄漏。
        if turn_idx == 1 and role == "evidence_session":
            u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
        if tid in ["T2-2", "T3-1"] and s_plan.get("small_memory_evidence_mode") == "cross_turn_clarification":
            u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
        if turn_idx == 2 and role == "reinforcement_session" and s_plan.get("small_memory_evidence_mode") == "co_occurrence" and s_plan.get("session_id", "").endswith("-03"):
            u_text = get_fallback_user_utterance(s_plan, turn_idx, role)

        # 规范化画质别名（严禁使用与数值冲突的'顶格清晰度'等词）
        for bad_word in ["顶格清晰度", "顶格画质", "最高画质", "极限画质", "最高清晰度"]:
            if bad_word in u_text:
                u_text = u_text.replace(bad_word, "1080p原画" if tp.get("resolution") == "1080p" else tp.get("resolution", ""))

        # 规范化时延别名（严禁使用失真夸大的'零卡顿'等词）
        for bad_word in ["零卡顿", "秒开", "极速响应"]:
            if bad_word in u_text:
                u_text = u_text.replace(bad_word, f"{tp.get('rtt', '')}以内")

        # 常规复用/强化会话第 1 轮：大记忆点已生效，用户提及老规矩/代称时，若仍堆砌了已沉淀的画质/时延/时长，予以自然精简
        if turn_idx == 1 and role in ["reinforcement_session", "reuse_session"] and tid not in ["T2-3", "T2-5"]:
            has_shorthand = any(k in u_text for k in ["老规矩", "老时间", "老样子", "照旧", "按习惯", "跟上次一样"])
            if has_shorthand:
                patterns_to_strip = [
                    r'，?(?:顶格清晰度|1080p原画|1080p|720p|超清|高清)[、，]?(?:零卡顿|\d+ms以内|\d+毫秒以内)[、，]?(?:俩小时|两小时|\d+分钟|\d+min)?',
                    r'[、，]?(?:顶格清晰度|1080p原画|1080p|720p|超清|高清)',
                    r'[、，]?(?:零卡顿|\d+ms以内|\d+毫秒以内)',
                ]
                for pat in patterns_to_strip:
                    u_text = re.sub(pat, '', u_text)
                u_text = re.sub(r'，\s*，', '，', u_text).strip("，, ")

        # 拦截清理误将后台规划长句拼入台词的异常
        if any(bad_kw in u_text for bad_kw in ["当上午", "进入道路", "触发现场", "办事了，", "弱网空间时", "固定外勤时段"]):
            u_text = get_fallback_user_utterance(s_plan, turn_idx, role)

        # 清除任何残留的后台规则词（如“触发用”、“触发”）
        u_text = u_text.replace("触发用", "用").replace("触发", "")

        # 检查并清除未经声明的幻觉别名
        sm_val = s_plan.get("small_memory", {}).get("value")
        def _clean_hallucinated_alias(match):
            alias_word = match.group(1)
            if alias_word in ["每天这个时候", "老规矩", "月初老规矩", "大半个下午"]:
                return match.group(0)
            if sm_val and alias_word == sm_val:
                return match.group(0)
            return ""

        u_text = re.sub(r'[，、]?(?:画质|时延|时长)?按[‘“\'\"]([^’度”\'\"]+)[’度”\'\"](?:来|开|算|处理)?', _clean_hallucinated_alias, u_text)
        u_text = re.sub(r'，\s*，', '，', u_text).strip("，, ")

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
        if tid == "T1-2":
            a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
        if tid == "T1-1" or s_plan.get("blueprint_type") == "distractor":
            if any(kw in a_text for kw in ["记忆理解", "理解为", "按‘", "按\""]):
                a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
        if tid in ["T2-2", "T3-1"] and s_plan.get("small_memory_evidence_mode") == "cross_turn_clarification":
            a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
        if tid == "T2-5" and turn_idx == 1:
            dur_str = tp.get("duration", "")
            dur_m = re.search(r'(\d+)\s*(?:min|分钟)', dur_str)
            if dur_m:
                num = dur_m.group(1)
                if f"{num}min" in a_text or f"{num}分钟" in a_text:
                    a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
        if turn_idx == 2 and role == "reinforcement_session" and s_plan.get("small_memory_evidence_mode") == "co_occurrence" and s_plan.get("session_id", "").endswith("-03"):
            a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
        if turn_idx == 1 and role in ["reinforcement_session", "reuse_session"] and tid not in ["T2-3", "T2-5"]:
            u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
            # 执行前必须把记忆补全出的时间与参数完整回显，不能让结构化时间凭空出现。
            a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
            for bad_word in ["零卡顿", "秒开", "极速响应"]:
                if bad_word in u_text:
                    u_text = u_text.replace(bad_word, f"{tp.get('rtt', '')}以内")
            for bad_word in ["顶格清晰度", "顶格画质", "最高画质", "极限画质", "最高清晰度"]:
                if bad_word in u_text:
                    u_text = u_text.replace(bad_word, "1080p原画" if tp.get("resolution") == "1080p" else tp.get("resolution", ""))

        # 同样规范化客服台词中的画质与时延
        for bad_word in ["顶格清晰度", "顶格画质", "最高画质", "极限画质", "最高清晰度"]:
            if bad_word in a_text:
                a_text = a_text.replace(bad_word, "1080p原画" if tp.get("resolution") == "1080p" else tp.get("resolution", ""))
        for bad_word in ["零卡顿", "秒开", "极速响应"]:
            if bad_word in a_text:
                a_text = a_text.replace(bad_word, f"{tp.get('rtt', '')}以内")

        # 拦截当天生效会话中错误出现的“明天/后天”口语词，防止与真实标注日期产生矛盾
        ref_day = s_plan.get("reference_time", "").split("日")[0]
        start_day = tp.get("start_timestamp", "").split("日")[0]
        if ref_day and start_day and ref_day == start_day:
            for w in ["明天", "后天"]:
                if w in u_text:
                    u_text = u_text.replace(w, "今天")
                if w in a_text:
                    a_text = a_text.replace(w, "今天")

        raw_u_acts = t_data.get("user_action_types") if isinstance(t_data, dict) else None
        raw_a_acts = t_data.get("agent_action_types") if isinstance(t_data, dict) else None
        u_acts, a_acts = get_normalized_action_types(s_plan, turn_idx, role, is_last, raw_u_acts, raw_a_acts)

        return u_text, u_acts, a_text, a_acts
