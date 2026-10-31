from __future__ import annotations

import logging

from src.config.settings import Config
from src.generation.isolated_views import build_isolated_views as _build_isolated_views
from src.generation.llm_client import LLMClient
from src.generation.session_assembler import SessionAssembler
from src.generation.turn_normalizer import normalize_dialogue_turn
from src.templates.prompts import (
    BATCH_DIALOGUE_SYSTEM_PROMPT,
    SINGLE_DIALOGUE_SYSTEM_PROMPT,
    build_batch_dialogue_prompt,
    build_single_dialogue_prompt,
    get_fallback_agent_utterance,
    get_fallback_user_utterance,
)
from src.templates.prompts.small_memory_prompt import co_occurrence_example, declaration_example

logger = logging.getLogger(__name__)


class DialogueGenerator:
    """
    对话台词渲染与会话装配器 (DialogueGenerator)
    负责调用 DeepSeek API 将会话蓝图批量渲染为真实、口语化的网络保障交互对话，
    并将生成的台词送入 SessionAssembler 装配为符合 8 大模版规范的标准数据对象。
    """

    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm_client or LLMClient()
        self.llm_circuit_breaker = not getattr(Config, "use_llm", True)

    @staticmethod
    def build_isolated_views(s_plan: dict, snapshot_before: dict) -> dict:
        """构建信息隔离的双向渲染视图 (Information-Isolated Dual Views)."""
        return _build_isolated_views(s_plan, snapshot_before)

    def generate_sessions_batch(self, session_items: list[tuple], persona: dict, batch_size: int = 5) -> list[dict]:
        """批量生成会话台词，大幅降低 API 调用次数与 Token 消耗。"""
        rendered_sessions = []
        for i in range(0, len(session_items), batch_size):
            chunk = session_items[i : i + batch_size]
            batch_turns_map = {}
            if not self.llm_circuit_breaker:
                try:
                    batch_turns_map = self._render_batch_dialogue_turns(chunk, persona)
                except Exception as e:
                    logger.warning(
                        "[Batch Warning] Batch LLM render failed for chunk %s: %s. Falling back for this chunk only.",
                        i,
                        e,
                    )
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

    @staticmethod
    def _format_batch_snapshot(snap_before: dict) -> str:
        if not snap_before:
            return "无"
        snap_parts = []
        for k, v in snap_before.items():
            if isinstance(v, dict) and "application_name" in v:
                snap_parts.append(
                    f"[{k}] {v.get('application_name')}-{v.get('service_name')}({v.get('resolution')},{v.get('rtt_max')},status={v.get('status')})"
                )
            elif k == "working_records" and isinstance(v, list):
                snap_parts.append(f"[working_records: {len(v)} items]")
            elif k == "experiences" and isinstance(v, list):
                snap_parts.append(f"[experiences: {len(v)} items]")
        return "; ".join(snap_parts) or "无"

    @staticmethod
    def _build_turn1_specialized_rule(s_plan: dict, tid: str, env: str, tp: dict) -> str | None:
        if tid == "T2-5":
            base_dur = s_plan.get("base_dur") or "60min"
            return (
                f"【时长延长会话（3轮修改再确认闭环）：第1轮用户必须满足最小表达，表达'今天在{env}，老规矩，用{tp['application_name']}做{tp['service_name']}，帮我把保障开上'（严禁在第1轮提及画质、时延与修改后的时长！）；"
                f"第1轮客服调取原基线老规矩配置向用户确认（基线时长为{base_dur}，严禁在第1轮提前说出修改后的时长{tp['duration']}！）；"
                f"第2轮用户确认老规矩不变，但说明因现场活动延长等原因提出将时长延长到{tp['duration']}（必须明确表述为精确时长数值，如‘{tp['duration']}’或对应小时/分钟，严禁使用‘半天’、‘大半天’、‘一上午’等有歧义口语！）；"
                f"第2轮客服将配置更新为延长后的时长{tp['duration']}（时段{tp['start_timestamp'].split('日')[-1]}至{tp['end_timestamp'].split('日')[-1]}，画质{tp['resolution']}、时延{tp['rtt']}以内），并向用户发起最终确认（严禁在第2轮直接闭环开通！）；"
                f"第3轮用户明确确认按延长后的配置开通，第3轮客服正式确认开通并收尾祝福。】"
            )
        if tid == "T2-3":
            return (
                f"【临时纠正覆盖会话（3轮纠偏再确认闭环）：第1轮用户必须满足最小表达，表达'今天在{env}，老规矩，用{tp['application_name']}做{tp['service_name']}，帮我把保障开上'；"
                f"第1轮客服反问确认原老规矩基线配置；"
                f"第2轮用户说明因现场特殊临时调整画质为{tp['resolution']}、时延为{tp['rtt']}；"
                f"第2轮客服汇总本次临时调整后的参数配置（画质{tp['resolution']}、时延{tp['rtt']}以内）并向用户发起最终确认（严禁在第2轮直接闭环开通！）；"
                f"第3轮用户明确确认按临时配置开通，第3轮客服正式确认开通并收尾祝福。】"
            )
        if tid == "T2-6":
            wm_ptr = s_plan.get("working_memory_pointer", {})
            rec_id = wm_ptr.get("target_record_id", "历史意图保障单")
            delta_d = wm_ptr.get("inferred_delta_days", 7)
            sh_t, eh_t = tp["start_timestamp"].split("日")[-1], tp["end_timestamp"].split("日")[-1]
            if s_plan.get("is_disambiguation"):
                return (
                    f"【工作记忆多单消歧会话（3轮）：第1轮用户明确给出今日保障起止时间（从{sh_t}到{eh_t}，持续{tp['duration']}）以及应用{tp['application_name']}、业务{tp['service_name']}，并表示想按之前在{env}办过的意图保障单规格来（省略画质和时延）；"
                    f"第1轮客服从工作记忆账本中查出存在多笔历史意图保障单候选，向用户反问确认按哪一笔规格办理；"
                    f"第2轮用户明确选定按最近那次开通的规格（{rec_id}）来；"
                    f"第2轮客服确认继承最近一笔的画质{tp['resolution']}、时延{tp['rtt']}并汇总时段（{sh_t}至{eh_t}），请用户最终确认；"
                    f"第3轮用户确认开通，客服收尾祝福。】"
                )
            return (
                f"【工作记忆跨期复用会话（3轮补全再确认闭环）：第1轮用户表达'这次去{env}，还按上周在{env}办的那个意图保障单规格来'，"
                f"指代历史意图保障单({rec_id}，距今约{delta_d}天)，省略画质和时延，但提出今日保障；"
                f"第1轮客服从工作记忆意图保障单账本中检索定位该单据，向用户确认继承的体验参数（画质{tp['resolution']}、时延{tp['rtt']}），并询问今日保障的具体起止时间；"
                f"第2轮用户补充说明今日的起止时间（{sh_t}至{eh_t}，持续{tp['duration']}）；"
                f"第2轮客服汇总今日完整保障配置（{sh_t}至{eh_t}，持续{tp['duration']}，画质{tp['resolution']}、时延{tp['rtt']}以内）向用户发起最终确认；"
                f"第3轮用户明确确认开通，第3轮客服正式确认开通并收尾祝福。】"
            )
        if tid == "T2-7":
            rec_id = s_plan.get("working_memory_pointer", {}).get("target_record_id", "历史意图保障单")
            return (
                f"【工作记忆单据改期会话：第1轮用户提出把昨天预约的{tp['application_name']}{tp['service_name']}保障往后推迟一个小时；"
                f"第1轮客服调取预约意图保障单({rec_id})，向用户反问确认推迟后的新时段（{tp['start_timestamp'].split('日')[-1]}至{tp['end_timestamp'].split('日')[-1]}）；"
                f"第2轮用户简短确认（如'对，确认修改'）；第2轮客服确认意图保障单改期生效并收尾。】"
            )
        if tid == "T2-8":
            return "【工作记忆对账核查会话（单轮）：第1轮用户询问历史保障统计（如'帮我查下这周总共开了几次保障，一共多长时间？'）；第1轮客服调取历史意图保障单流水账，明确回复已开通的总次数、累计保障时长与明细，礼貌闭环。】"
        if tid == "T2-9":
            exp_title = s_plan.get("experience_citation", {}).get("title", "重大活动与大型场馆现场提前30分钟网络预热起保经验")
            nom_s = (s_plan.get("nominal_start") or tp["start_timestamp"]).split("日")[-1]
            nom_d = s_plan.get("nominal_dur") or s_plan.get("base_dur") or tp["duration"]
            return (
                f"【经验记忆主动提议会话：当前环境为高密/重大活动现场'{env}'。第1轮用户必须一次性把基础参数说清楚（应用{tp['application_name']}、业务{tp['service_name']}、原定活动时间{nom_s}至{tp['end_timestamp'].split('日')[-1]}、原定时长{nom_d}、画质{tp['resolution']}、时延{tp['rtt']}以内），不依赖此前事实记忆；"
                f"第1轮客服依据ReasoningBank经验卡片【{exp_title}】，主动将起保时间提前30分钟推算为{tp['start_timestamp'].split('日')[-1]}至{tp['end_timestamp'].split('日')[-1]}（保障时长扩至{tp['duration']}），询问用户是否确认开通；"
                f"第2轮用户确认采纳提前预热经验（如'好的，提前半小时试机预热太重要了，按这个开通意图保障单！'）；第2轮客服确认按提前30分钟预热方案开通并收尾。】"
            )
        if tid == "T2-10":
            exp_title = s_plan.get("experience_citation", {}).get("title", "新旧意图保障单时段撞车无缝让路与时序重叠仲裁经验")
            return (
                f"【经验记忆经验回溯/仲裁会话：第1轮用户一次性说清紧急意图保障单的原定参数（应用{tp['application_name']}、业务{tp['service_name']}、原定时间15时00分至{tp['end_timestamp'].split('日')[-1]}、原定时长120min、画质{tp['resolution']}、时延{tp['rtt']}以内），并提及与系统内上一笔15时30分结束的在保意图保障单重叠冲突；"
                f"第1轮客服调取经验卡片【{exp_title}】，将新意图保障单调整为从交界点{tp['start_timestamp'].split('日')[-1]}无缝接续起保至{tp['end_timestamp'].split('日')[-1]}，总时长缩减重算为{tp['duration']}，反问确认；"
                f"第2轮用户确认；第2轮客服确认按时序重叠仲裁方案开通并收尾。】"
            )
        return None

    @classmethod
    def _build_turn1_requirement_rule(cls, s_plan: dict, primary_alias: str, small_memory_declaration: str, small_memory_co_occurrence: str) -> str:
        sid = s_plan["session_id"]
        role = s_plan["memory_role"]
        b_type = s_plan["blueprint_type"]
        tp = s_plan["target_params"]
        env = s_plan["scenario_env"]
        small_memory = s_plan.get("small_memory", {})
        evidence_mode = s_plan.get("small_memory_evidence_mode", "explicit_declaration")
        decl_mode = s_plan.get("declaration_mode", "explicit_declaration")
        is_implicit_reinf = role == "reinforcement_session" and decl_mode == "implicit_induction" and sid.endswith("-03")
        tid = s_plan.get("template_id", "T2-1")

        if tid == "T1-2":
            return f"【纯域外拒绝：用户必须明确提出'{s_plan.get('ood_goal') or '宽带光纤装维报修'}'，不得提出任何应用网络保障或老规矩请求；Agent 必须明确说明不支持并拒绝办理。】"
        if role == "evidence_session":
            if b_type == "main" and decl_mode == "implicit_induction":
                return f"【隐式归纳首次证据：第1轮必须直述标准应用名({tp['application_name']})、业务名({tp['service_name']})和精确开始时刻({tp['start_timestamp']})；第2轮用户必须完整补充画质({tp['resolution']})、时延({tp['rtt']})以及持续时长({tp['duration']})，台词中必须显式提及持续时长（如‘持续{tp['duration']}’），三者缺一不可。严禁出现‘以后’‘记住’‘老规矩’或登记任何小记忆点，本轮结束后只能形成 provisional 历史记录。】"
            return f"【建立小记忆：证据模式={evidence_mode}。第1轮使用标准应用、业务和精确开始时刻。第2轮用户必须完整补充画质、时延与持续时长({tp['duration']})，台词中必须显式提及持续时长（如‘持续{tp['duration']}’）。explicit_declaration 使用声明话术：{small_memory_declaration}；co_occurrence 使用同轮共现话术：{small_memory_co_occurrence}；cross_turn_clarification 必须用三轮，由用户先说模糊表达、Agent追问其是否对应标准值、用户最后确认。只登记指定类型={small_memory.get('type')}，不得登记其他别名。】"
        if is_implicit_reinf:
            return f"【隐式归纳二次发生固化契机：第1轮用户必须提及业务名作为最小锚点（如‘今天在{env}，{tp['service_name']}这次按上次的来’），但不得主动说出应用名({tp['application_name']})、画质/时延参数与起止时间；第1轮客服完整复述历史候选（明确指出上次是{tp['application_name']}）并要求确认；第2轮确认固化，小记忆证据模式={evidence_mode}，本会话使用同轮共现话术：{small_memory_co_occurrence}，不要改写成‘X就是Y’的显式定义。业务默认应用只对当前主线场景生效。】"
        spec = cls._build_turn1_specialized_rule(s_plan, tid, env, tp)
        if spec is not None:
            return spec
        if tid == "X-1":
            is_weekend = "周末" in env
            time_constraint = "用户可表述为‘周末午休’；" if is_weekend else "由于当前是工作日（周一至周五），用户台词严禁出现‘周末’字样！只能表述为‘午休’或‘今天中午午休’；"
            sh_t, eh_t = tp["start_timestamp"].split("日")[-1], tp["end_timestamp"].split("日")[-1]
            return (
                f"【混合诉求（一办一拒）：单轮干扰会话，无先验记忆。当前环境为'{env}'，{time_constraint}"
                f"关键参数与时间要求：用户必须在台词中完整说出应用名({tp['application_name']})、业务名({tp['service_name']})、精确起止时间点（从{sh_t}到{eh_t}）、持续时长（持续{tp['duration']}）、画质({tp['resolution']})以及时延({tp['rtt']}以内)，缺一不可！"
                f"用户同时提出域外需求'{s_plan.get('ood_goal') or '手机话费充值与账单查询'}'；"
                f"严禁使用未建立过的个性化表达或老规矩；Agent 正常受理域内业务，并明确礼貌拒绝办理域外需求。】"
            )
        t1_rule = f"【常规复用/强化会话：大记忆点已生效。应用＋业务是最小表达：若小记忆类型为service_default_app，可只说业务；若为application_alias，必须说应用别名＋业务；若为画质/时延/时长/个性化周期表达，必须说标准应用＋业务＋该个性化表达。指定小记忆点='{primary_alias}'。Agent 从记忆中补全其余画质{tp['resolution']}、时延{tp['rtt']}、开始时间{tp['start_timestamp']}、结束时间{tp['end_timestamp']}和时长{tp['duration']}；不得把未说出的槽位标成 Turn 来源。】"
        if s_plan.get("retrieval_challenge_type") == "paraphrased_alias_scene":
            t1_rule += "【检索盲区变体要求(paraphrased_alias_scene)：第1轮用户需使用拆词/同义近似口语来表达周期或现场（如将‘午间例行’说成‘按咱们中午那个例行档期’，将‘大巴转场途中’说成‘坐大巴车转场的路上’）。】"
        elif s_plan.get("retrieval_challenge_type") == "implicit_service_collocation":
            t1_rule += "【检索盲区变体要求(implicit_service_collocation)：第1轮用户使用隐含动宾短语表达业务（如用‘上麦开播推流’代替‘开直播’，用‘搞个线上投屏远程碰头会’代替‘视频会议’）。】"
        elif s_plan.get("retrieval_challenge_type") == "negation_contrast":
            t1_rule += f"【检索盲区变体要求(negation_contrast)：第1轮用户先用否定从句排除主线业务（如‘今天不用{s_plan.get('contrast_negated_app', '抖音')}做{s_plan.get('contrast_negated_service', '开直播')}了’），再转折提出当前诉求。】"
        return t1_rule

    def _build_batch_prompt_item(self, s_plan: dict, snap_before: dict) -> dict:
        sid = s_plan["session_id"]
        role = s_plan["memory_role"]
        b_type = s_plan["blueprint_type"]
        tp = s_plan["target_params"]
        env = s_plan["scenario_env"]
        rounds = s_plan["round_count"]
        snap_str = self._format_batch_snapshot(snap_before)

        p_aliases = s_plan.get("aliases", {})
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
        t1_rule = self._build_turn1_requirement_rule(s_plan, primary_alias, small_memory_declaration, small_memory_co_occurrence)

        ref_turns = [
            {
                "turn": r_idx,
                "reference_user_utterance": get_fallback_user_utterance(s_plan, r_idx, role),
                "reference_agent_utterance": get_fallback_agent_utterance(s_plan, r_idx, role, r_idx == rounds),
            }
            for r_idx in range(1, rounds + 1)
        ]
        isolated_views = self.build_isolated_views(s_plan, snap_before)
        return {
            "session_id": sid,
            "rounds": rounds,
            "role": role,
            "blueprint_type": b_type,
            "template_id": s_plan.get("template_id", "T2-1"),
            "turn1_requirement": t1_rule,
            "isolated_views": isolated_views,
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
            "app": isolated_views["user_private_view"]["turn1_allowed_slots"].get("application_name") or tp["application_name"],
            "service": tp["service_name"],
            "turn1_allowed_slots": isolated_views["user_private_view"]["turn1_allowed_slots"],
            "turn2_reveal_slots": isolated_views["user_private_view"]["turn2_reveal_slots"],
            "aliases": aliases_info,
        }

    def _render_batch_dialogue_turns(self, chunk: list[tuple], persona: dict) -> dict[str, list[dict]]:
        speech = persona["static_profile"]["speech_style"]
        identity = persona["static_profile"]["identity"]
        prompt_items = [self._build_batch_prompt_item(s_plan, snap_before) for s_plan, snap_before, _, _ in chunk]
        prompt = build_batch_dialogue_prompt(prompt_items, identity, speech)
        messages = [
            {"role": "system", "content": BATCH_DIALOGUE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
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
            {"role": "system", "content": SINGLE_DIALOGUE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
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
            is_last = turn_idx == target_rounds
            u_text, u_acts, a_text, a_acts = self._normalize_turn(t_data, turn_idx, role, is_last, s_plan)

            req_params = []
            if turn_idx == 1 and role == "evidence_session":
                req_params = ["resolution", "rtt", "duration"]
            elif turn_idx == 2 and tid == "T3-1":
                req_params = ["resolution"]

            rel_ids = ["I1", "I2"] if tid in ["X-1", "T1-3", "T2-4"] else ["I1"]
            event_sequence.append(
                {
                    "turn": turn_idx,
                    "user": {"utterance": u_text, "action_types": u_acts},
                    "agent": {"utterance": a_text, "action_types": a_acts},
                    "related_intent_ids": rel_ids,
                    "requested_params": req_params,
                }
            )
        return SessionAssembler.assemble(
            s_plan=s_plan,
            snapshot_before=snapshot_before,
            memory_events=memory_events,
            gold_after=gold_after,
            event_sequence=event_sequence,
        )

    def _normalize_turn(self, t_data: dict, turn_idx: int, role: str, is_last: bool, s_plan: dict):
        """规范化单轮 User 与 Agent 台词及动作标注。"""
        return normalize_dialogue_turn(t_data, turn_idx, role, is_last, s_plan)
