import json
import re
from src.config.settings import Config
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
        self.llm_circuit_breaker = not getattr(Config, "use_llm", True)

    def generate_sessions_batch(self, session_items: list[tuple], persona: dict, batch_size: int = 5) -> list[dict]:
        """
        批量生成会话台词，大幅降低 API 调用次数与 Token 消耗。
        session_items: 包含 (s_plan, snapshot_before, memory_events, gold_after) 的元组列表
        """
        rendered_sessions = []

        for i in range(0, len(session_items), batch_size):
            chunk = session_items[i : i + batch_size]
            batch_turns_map = {}
            if not self.llm_circuit_breaker:
                try:
                    # 批量调用 DeepSeek 渲染该组会话台词
                    batch_turns_map = self._render_batch_dialogue_turns(chunk, persona)
                except Exception as e:
                    print(f"    [Batch Warning] Batch LLM render failed for chunk {i}: {e}. Falling back for this chunk only.")
                    batch_turns_map = {}

            for s_plan, snap_before, mem_events, gold_after in chunk:
                sid = s_plan["session_id"]
                raw_turns = batch_turns_map.get(sid, [])
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
                snap_parts = []
                for k, v in snap_before.items():
                    if isinstance(v, dict) and "application_name" in v:
                        snap_parts.append(f"[{k}] {v.get('application_name')}-{v.get('service_name')}({v.get('resolution')},{v.get('rtt_max')},status={v.get('status')})")
                    elif k == "working_records" and isinstance(v, list):
                        snap_parts.append(f"[working_records: {len(v)} items]")
                    elif k == "experiences" and isinstance(v, list):
                        snap_parts.append(f"[experiences: {len(v)} items]")
                snap_str = "; ".join(snap_parts) or "无"
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
                    t1_rule = f"【隐式归纳首次证据：第1轮必须直述标准应用名({tp['application_name']})、业务名({tp['service_name']})和精确开始时刻({tp['start_timestamp']})；第2轮用户必须完整补充画质({tp['resolution']})、时延({tp['rtt']})以及持续时长({tp['duration']})，台词中必须显式提及持续时长（如‘持续{tp['duration']}’），三者缺一不可。严禁出现‘以后’‘记住’‘老规矩’或登记任何小记忆点，本轮结束后只能形成 provisional 历史记录。】"
                else:
                    t1_rule = f"【建立小记忆：证据模式={evidence_mode}。第1轮使用标准应用、业务和精确开始时刻。第2轮用户必须完整补充画质、时延与持续时长({tp['duration']})，台词中必须显式提及持续时长（如‘持续{tp['duration']}’）。explicit_declaration 使用声明话术：{small_memory_declaration}；co_occurrence 使用同轮共现话术：{small_memory_co_occurrence}；cross_turn_clarification 必须用三轮，由用户先说模糊表达、Agent追问其是否对应标准值、用户最后确认。只登记指定类型={small_memory.get('type')}，不得登记其他别名。】"
            elif is_implicit_reinf:
                t1_rule = f"【隐式归纳二次发生固化契机：第1轮用户必须提及业务名作为最小锚点（如‘今天在{env}，{tp['service_name']}这次按上次的来’），但不得主动说出应用名({tp['application_name']})、画质/时延参数与起止时间；第1轮客服完整复述历史候选（明确指出上次是{tp['application_name']}）并要求确认；第2轮确认固化，小记忆证据模式={evidence_mode}，本会话使用同轮共现话术：{small_memory_co_occurrence}，不要改写成‘X就是Y’的显式定义。业务默认应用只对当前主线场景生效。】"
            elif tid == "T2-5":
                base_dur = s_plan.get("base_dur") or "60min"
                t1_rule = (
                    f"【时长延长会话：第1轮用户必须满足最小表达，表达'今天在{env}，老规矩，用{tp['application_name']}做{tp['service_name']}，帮我把保障开上'（严禁在第1轮提及画质、时延与修改后的时长！）；"
                    f"第1轮客服调取原基线老规矩配置向用户确认（基线时长为{base_dur}，严禁在第1轮提前说出修改后的时长{tp['duration']}！）；"
                    f"第2轮用户确认老规矩不变，但说明因现场活动延长等原因提出将时长延长到{tp['duration']}（必须明确表述为精确时长数值，如‘{tp['duration']}’或对应小时/分钟，严禁使用‘半天’、‘大半天’、‘一上午’等有歧义口语！）；"
                    f"第2轮客服确认按老规矩开通并将时长延长至{tp['duration']}。】"
                )
            elif tid == "T2-3":
                t1_rule = (
                    f"【临时纠正覆盖会话：第1轮用户必须满足最小表达，表达'今天在{env}，老规矩，用{tp['application_name']}做{tp['service_name']}，帮我把保障开上'；"
                    f"第1轮客服反问确认老规矩；"
                    f"第2轮用户说明因现场特殊临时调整画质为{tp['resolution']}、时延为{tp['rtt']}；"
                    f"第2轮客服确认本次临时调整。】"
                )
            elif tid == "T2-6":
                wm_ptr = s_plan.get("working_memory_pointer", {})
                rec_id = wm_ptr.get("target_record_id", "历史意图保障单")
                delta_d = wm_ptr.get("inferred_delta_days", 7)
                sh_t = tp["start_timestamp"].split("日")[-1]
                eh_t = tp["end_timestamp"].split("日")[-1]
                if s_plan.get("is_disambiguation") or s_plan.get("round_count") == 3:
                    t1_rule = (
                        f"【工作记忆多单消歧会话（3轮）：第1轮用户明确给出今日保障起止时间（从{sh_t}到{eh_t}，持续{tp['duration']}）以及应用{tp['application_name']}、业务{tp['service_name']}，并表示想按之前在{env}办过的意图保障单规格来（省略画质和时延）；"
                        f"第1轮客服从工作记忆账本中查出存在多笔历史意图保障单候选，向用户反问确认按哪一笔规格办理；"
                        f"第2轮用户明确选定按最近那次开通的规格（{rec_id}）来；"
                        f"第2轮客服确认继承最近一笔的画质{tp['resolution']}、时延{tp['rtt']}并汇总时段（{sh_t}至{eh_t}），请用户最终确认；"
                        f"第3轮用户确认开通，客服收尾祝福。】"
                    )
                else:
                    t1_rule = (
                        f"【工作记忆跨期复用会话：第1轮用户表达'这次去{env}，还按上周在{env}办的那个意图保障单规格来'，"
                        f"指代历史意图保障单({rec_id}，距今约{delta_d}天)，省略画质和时延，但提出今日保障；"
                        f"第1轮客服从工作记忆意图保障单账本中检索定位该单据，向用户确认继承的体验参数（画质{tp['resolution']}、时延{tp['rtt']}），并询问今日保障的具体起止时间；"
                        f"第2轮用户补充说明今日的起止时间（{sh_t}至{eh_t}，持续{tp['duration']}）；"
                        f"第2轮客服确认开通并收尾祝福。】"
                    )
            elif tid == "T2-7":
                wm_ptr = s_plan.get("working_memory_pointer", {})
                rec_id = wm_ptr.get("target_record_id", "历史意图保障单")
                t1_rule = (
                    f"【工作记忆单据改期会话：第1轮用户提出把昨天预约的{tp['application_name']}{tp['service_name']}保障往后推迟一个小时；"
                    f"第1轮客服调取预约意图保障单({rec_id})，向用户反问确认推迟后的新时段（{tp['start_timestamp'].split('日')[-1]}至{tp['end_timestamp'].split('日')[-1]}）；"
                    f"第2轮用户简短确认（如'对，确认修改'）；"
                    f"第2轮客服确认意图保障单改期生效并收尾。】"
                )
            elif tid == "T2-8":
                t1_rule = (
                    f"【工作记忆对账核查会话（单轮）：第1轮用户询问历史保障统计（如'帮我查下这周总共开了几次保障，一共多长时间？'）；"
                    f"第1轮客服调取历史意图保障单流水账，明确回复已开通的总次数、累计保障时长与明细，礼貌闭环。】"
                )
            elif tid == "T2-9":
                exp = s_plan.get("experience_citation", {})
                exp_title = exp.get("title", "重大活动与大型场馆现场提前30分钟网络预热起保经验")
                nom_s = (s_plan.get("nominal_start") or tp["start_timestamp"]).split("日")[-1]
                nom_d = s_plan.get("nominal_dur") or s_plan.get("base_dur") or tp["duration"]
                t1_rule = (
                    f"【经验记忆主动提议会话：当前环境为高密/重大活动现场'{env}'。第1轮用户必须一次性把基础参数说清楚（应用{tp['application_name']}、业务{tp['service_name']}、原定活动时间{nom_s}至{tp['end_timestamp'].split('日')[-1]}、原定时长{nom_d}、画质{tp['resolution']}、时延{tp['rtt']}以内），不依赖此前事实记忆；"
                    f"第1轮客服依据ReasoningBank经验卡片【{exp_title}】，主动将起保时间提前30分钟推算为{tp['start_timestamp'].split('日')[-1]}至{tp['end_timestamp'].split('日')[-1]}（保障时长扩至{tp['duration']}），询问用户是否确认开通；"
                    f"第2轮用户确认采纳提前预热经验（如'好的，提前半小时试机预热太重要了，按这个开通意图保障单！'）；"
                    f"第2轮客服确认按提前30分钟预热方案开通并收尾。】"
                )
            elif tid == "T2-10":
                exp = s_plan.get("experience_citation", {})
                exp_title = exp.get("title", "新旧意图保障单时段撞车无缝让路与时序重叠仲裁经验")
                t1_rule = (
                    f"【经验记忆经验回溯/仲裁会话：第1轮用户一次性说清紧急意图保障单的原定参数（应用{tp['application_name']}、业务{tp['service_name']}、原定时间15时00分至{tp['end_timestamp'].split('日')[-1]}、原定时长120min、画质{tp['resolution']}、时延{tp['rtt']}以内），并提及与系统内上一笔15时30分结束的在保意图保障单重叠冲突；"
                    f"第1轮客服调取经验卡片【{exp_title}】，将新意图保障单调整为从交界点{tp['start_timestamp'].split('日')[-1]}无缝接续起保至{tp['end_timestamp'].split('日')[-1]}，总时长缩减重算为{tp['duration']}，反问确认；"
                    f"第2轮用户确认（如'太好了，就按15时30分无缝接续起保、时长重算为90min的仲裁方案开通意图保障单！'）；"
                    f"第2轮客服确认按时序重叠仲裁方案开通并收尾。】"
                )
            elif tid == "X-1":
                is_weekend = "周末" in env
                time_constraint = "用户可表述为‘周末午休’；" if is_weekend else "由于当前是工作日（周一至周五），用户台词严禁出现‘周末’字样！只能表述为‘午休’或‘今天中午午休’；"
                t1_rule = (
                    f"【混合诉求（一办一拒）：单轮干扰会话，无先验记忆。当前环境为'{env}'，{time_constraint}"
                    f"关键时间要求：用户必须在台词中明确说明具体的保障时段范围（必须包含明确的起止时间点，如‘12点30分到13点30分’或‘12:30至13:30’）以及持续时长（如‘持续60分钟’或‘开60分钟’），严禁只说‘午休’、‘中午’或‘刷会儿’等无法确定起止点的模糊词汇！"
                    f"用户首次提出业务需求，同时提出域外需求'{s_plan.get('ood_goal') or '手机话费充值与账单查询'}'；"
                    f"严禁使用未建立过的个性化表达或老规矩；Agent 正常受理域内业务，并明确礼貌拒绝办理域外需求。】"
                )
            else:
                t1_rule = f"【常规复用/强化会话：大记忆点已生效。应用＋业务是最小表达：若小记忆类型为service_default_app，可只说业务；若为application_alias，必须说应用别名＋业务；若为画质/时延/时长/个性化周期表达，必须说标准应用＋业务＋该个性化表达。指定小记忆点='{primary_alias}'。Agent 从记忆中补全其余画质{tp['resolution']}、时延{tp['rtt']}、开始时间{tp['start_timestamp']}、结束时间{tp['end_timestamp']}和时长{tp['duration']}；不得把未说出的槽位标成 Turn 来源。】"
                if s_plan.get("retrieval_challenge_type") == "paraphrased_alias_scene":
                    t1_rule += "【检索盲区变体要求(paraphrased_alias_scene)：第1轮用户需使用拆词/同义近似口语来表达周期或现场（如将‘午间例行’说成‘按咱们中午那个例行档期’，将‘大巴转场途中’说成‘坐大巴车转场的路上’）。】"
                elif s_plan.get("retrieval_challenge_type") == "implicit_service_collocation":
                    t1_rule += "【检索盲区变体要求(implicit_service_collocation)：第1轮用户使用隐含动宾短语表达业务（如用‘上麦开播推流’代替‘开直播’，用‘搞个线上投屏远程碰头会’代替‘视频会议’）。】"
                elif s_plan.get("retrieval_challenge_type") == "negation_contrast":
                    t1_rule += f"【检索盲区变体要求(negation_contrast)：第1轮用户先用否定从句排除主线业务（如‘今天不用{s_plan.get('contrast_negated_app', '抖音')}做{s_plan.get('contrast_negated_service', '开直播')}了’），再转折提出当前诉求。】"

            ref_turns = []
            for r_idx in range(1, rounds + 1):
                ref_turns.append({
                    "turn": r_idx,
                    "reference_user_utterance": get_fallback_user_utterance(s_plan, r_idx, role),
                    "reference_agent_utterance": get_fallback_agent_utterance(s_plan, r_idx, role, r_idx == rounds),
                })

            prompt_items.append({
                "session_id": sid,
                "rounds": rounds,
                "role": role,
                "blueprint_type": b_type,
                "template_id": s_plan.get("template_id", "T2-1"),
                "turn1_requirement": t1_rule,
                "reference_turns": ref_turns,
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
        res = self.llm.chat_json(messages, max_retries=2, enable_thinking=False)
        output_map = {}
        s_list = res.get("sessions", []) if isinstance(res, dict) else (res if isinstance(res, list) else [])
        if isinstance(s_list, list):
            for s_entry in s_list:
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

            rel_ids = ["I1", "I2"] if tid in ["X-1", "T2-4"] else ["I1"]
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
            if s_plan.get("retrieval_challenge_type") == "negation_contrast":
                neg_app = s_plan.get("contrast_negated_app") or ""
                if not (neg_app and neg_app in u_text and "不" in u_text):
                    u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
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

        # 经验记忆负反例边界：必须坚持原画质，严禁降画质
        if s_plan.get("is_counterexample"):
            if tp.get("resolution", "1080p") not in u_text:
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)

        # 证据会话首轮必须包含标准应用、业务与开始时间，且严禁泄漏画质/时延/时长。
        if turn_idx == 1 and role == "evidence_session":
            app_ok = tp.get("application_name", "") in u_text
            srv_ok = tp.get("service_name", "") in u_text
            start_hm = tp.get("start_timestamp", "").split("日")[-1]
            time_ok = start_hm in u_text or start_hm.replace("时", ":").replace("分", "") in u_text or start_hm.replace("时", "点") in u_text
            leaked = any(k and k in u_text for k in [tp.get("resolution", ""), tp.get("rtt", ""), tp.get("duration", ""), "俩小时", "两小时", "一个钟头", "一个半小时", "三个小时", "60分钟", "90分钟", "120分钟", "150分钟", "180分钟"])
            if not (app_ok and srv_ok and time_ok) or leaked:
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
        if turn_idx == 2 and role == "evidence_session" and tid == "T2-1":
            dur_aliases = s_plan.get("aliases", {}).get("duration_aliases", [])
            has_dur = tp.get("duration", "") in u_text or any(da in u_text for da in dur_aliases)
            if tp.get("resolution", "") not in u_text or tp.get("rtt", "") not in u_text or not has_dur:
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
        if turn_idx == 1 and role in ["reinforcement_session", "reuse_session"] and tid not in ["T2-3", "T2-5", "T2-6", "T2-7", "T2-8", "T2-9", "T2-10"]:
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
        if s_plan.get("is_counterexample"):
            if "降" in a_text or ("原画" not in a_text and "1080p" not in a_text):
                a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
        if s_plan.get("is_disambiguation"):
            if turn_idx == 1:
                sh_t = tp.get("start_timestamp", "").split("日")[-1]
                eh_t = tp.get("end_timestamp", "").split("日")[-1]
                if sh_t not in u_text or eh_t not in u_text or tp.get("resolution", "") in u_text or tp.get("rtt", "") in u_text:
                    u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
                if "哪" not in a_text and "意图保障单" not in a_text and "记录" not in a_text:
                    a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
            elif turn_idx == 2:
                if "最近" not in u_text and "上次" not in u_text:
                    u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
                if tp.get("resolution", "") not in a_text or tp.get("rtt", "") not in a_text:
                    a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
            elif turn_idx == 3:
                if any(kw in u_text for kw in ["画面", "画质", "透亮", "清晰", "流畅", "时延", "延迟"]):
                    u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
        elif tid == "T2-6" and not s_plan.get("experience_citation"):
            sh_t = tp.get("start_timestamp", "").split("日")[-1]
            eh_t = tp.get("end_timestamp", "").split("日")[-1]
            if turn_idx == 1:
                if tp.get("resolution", "") not in a_text or tp.get("rtt", "") not in a_text:
                    a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
            elif turn_idx == 2:
                if sh_t not in u_text or eh_t not in u_text or tp.get("duration", "") not in u_text:
                    u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
        elif tid == "T2-7":
            sh_t = tp.get("start_timestamp", "").split("日")[-1]
            eh_t = tp.get("end_timestamp", "").split("日")[-1]
            is_adv = s_plan.get("working_memory_pointer", {}).get("reschedule_direction") == "advance"
            if turn_idx == 1:
                if (is_adv and "提前" not in u_text) or (not is_adv and "推迟" not in u_text):
                    u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
                if sh_t not in a_text or eh_t not in a_text:
                    a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
        if turn_idx == 1 and role in ["reinforcement_session", "reuse_session"] and tid not in ["T2-3", "T2-5", "T2-6", "T2-7", "T2-8", "T2-9", "T2-10", "T2-4"] and not s_plan.get("experience_citation"):
            is_imp_s03 = (role == "reinforcement_session" and s_plan.get("declaration_mode") == "implicit_induction" and s_plan.get("session_id", "").endswith("-03"))
            challenge_type = s_plan.get("retrieval_challenge_type")
            if is_imp_s03:
                if tp.get("service_name", "") not in u_text or tp.get("application_name", "") in u_text:
                    u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
            elif challenge_type == "negation_contrast":
                neg_app = s_plan.get("contrast_negated_app") or ""
                if not (neg_app and neg_app in u_text and "不" in u_text and tp.get("application_name", "") in u_text):
                    u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
            elif challenge_type in ("paraphrased_alias_scene", "implicit_service_collocation"):
                u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
            else:
                sm_val = s_plan.get("small_memory", {}).get("value") or ""
                if sm_val and sm_val not in u_text and tp.get("application_name", "") not in u_text:
                    u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
            if tp.get("resolution", "") not in a_text or tp.get("rtt", "") not in a_text:
                a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)
            for bad_word in ["零卡顿", "秒开", "极速响应"]:
                if bad_word in u_text:
                    u_text = u_text.replace(bad_word, f"{tp.get('rtt', '')}以内")
            for bad_word in ["顶格清晰度", "顶格画质", "最高画质", "极限画质", "最高清晰度"]:
                if bad_word in u_text:
                    u_text = u_text.replace(bad_word, "1080p原画" if tp.get("resolution") == "1080p" else tp.get("resolution", ""))

        # 经验记忆全系场景（含学习铺垫轮与迁移测试轮）：严格采用高保真标准化 Fallback，确保 Turn 1 基础参数自包含且与双轨分支评测 Ground Truth 100% 严密对齐
        exp_id = s_plan.get("experience_id") or s_plan.get("experience_citation", {}).get("experience_id")
        if (
            tid in ["T2-4", "T2-9", "T2-10"]
            or s_plan.get("memory_tier") == "experiential_memory"
            or s_plan.get("blueprint_type") == "experience_learning"
            or bool(exp_id)
        ):
            u_text = get_fallback_user_utterance(s_plan, turn_idx, role)
            a_text = get_fallback_agent_utterance(s_plan, turn_idx, role, is_last)

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
