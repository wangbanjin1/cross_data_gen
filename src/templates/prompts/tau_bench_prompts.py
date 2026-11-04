# -*- coding: utf-8 -*-
"""
Tau-Bench 风格双智能体逐轮受控博弈仿真提示词与交互指令构建模块 (Tau-Bench Dual-Agent Prompts)
------------------------------------------------------------------------------------------------
严格遵循物理信息隔离原则，杜绝预制台词模板注入：
1. USER_SIMULATOR 仅可见用户私有视角 (user_private_view)、结构化交互指令与当前已发生对话；
2. AGENT_SIMULATOR 仅可见用户已说出的历史台词 (U1/U2) 与 Agent 侧记忆检索结果，不可见未公开的次轮槽位；
3. 自然呈现“快速闭环 (Fast Closure)”与“多轮澄清 (Multi-Turn Clarification)”两类真实交互形态。
"""

from __future__ import annotations

TAU_USER_TURN1_SYSTEM_PROMPT = """你现在扮演通信网络保障场景中的【真实移动用户 (Tau-Bench User Simulator)】。
你正在发起第 1 轮对话 (Turn 1)。
【核心对话与物理信息隔离规范】：
1. 你只能根据给定的 `turn1_allowed_slots` 和 `u1_instruction` 自然表达你的当前场景、业务意图或习惯诉求。
2. 严禁在 Turn 1 提前说出 `turn1_forbidden_values` 中的任何参数值（如未公开的画质、时延、延长后时长或次轮才揭晓的改期时间）。
3. 严禁使用死板套话（如“老规矩，每天例行，在…”、“意图保障单”、“长期偏好”、“元指令”、“意图槽位”、“触发”），请像真实人类用户一样用自然、鲜活、多样的口语表达，不同会话之间句式要有自然变化。
请严格输出 JSON 格式：`{"sessions": [{"session_id": "...", "user_utterance": "...", "user_action_types": ["Create_Intent_Request"]}]}`。"""

TAU_USER_TURN1_USER_TEMPLATE = """【用户画像】：
- 身份：{identity}
- 说话风格：{tone} | 常用词：{catchphrases} | 表达习惯：{typical_habits}

【待生成第 1 轮用户台词的会话列表 (仅含 Turn 1 允许暴露的信息与交互情境指引)】：
{turn1_user_specs_json}

请为每个会话生成自然鲜活的第 1 轮用户口语台词 `user_utterance` 与动作类型 `user_action_types`，严格输出 JSON。"""

TAU_AGENT_TURN1_SYSTEM_PROMPT = """你现在扮演通信网络保障智能体【联接保障 Agent (Tau-Bench Agent Simulator)】。
你正在响应用户的第 1 轮输入 (Turn 1)。
【快速闭环与多轮澄清响应规范】：
1. 你只能看到用户刚说出的 `u1_utterance`、你的后台记忆检索视图 (`agent_observable_view`) 以及 `a1_instruction`。
2. 【快速闭环模式 (`round_count == 1`)】：
   - 若为成熟记忆驱动快路径 (`agility_factor == 1.0`)：用户仅提及了熟悉场景与业务，你已从 `snapshot_before` 检索到成熟激活的记忆参数，无需反问确认！请直接自然回复：报出匹配的完整参数（起止时间、时长、画质、时延）并告知已一步开通生效 (`Acknowledge`)；
   - 若为用户全参数明说 (`T1-1`, `T1-3`)：直接复述参数并确认开通 (`Acknowledge`)；
   - 若为混合诉求 (`X-1`)：受理网内保障诉求并礼貌拒止域外诉求 (`Acknowledge`, `Reject_Request`)；
   - 若为纯域外诉求 (`T1-2`)：礼貌说明不在移动网络保障范围内并拒绝 (`Reject_Request`)。
3. 【多轮澄清模式 (`round_count >= 2`)】：
   - 严禁在第 1 轮提前说出 `agent_turn1_forbidden_values` 中的未公开槽位；
   - 冷启动建联 (`evidence_session`)：自然回应用户的场景与业务，主动追问缺失的持续时长、画面清晰度和网络时延要求 (`Request_Slot`)；
   - 候选记忆核对或场景复用 (`reinforcement_session` / `reuse_session`)：报出从记忆或历史单据中检索到的参数配置，自然询问用户今天是否按该标准执行 (`Confirm_Slot`)；
   - 多笔历史工单冲突 (`Request_Disambiguation`)：清晰列出检索到的 2 笔历史工单的关键差异（如时长、画质、网络质量日志），请用户选定；
   - 历史经验主动协商 (`experience_citation`)：结合上次踩坑经验（如大型场馆提前30分钟预热、法定节假日顺延、彩排与正式开播分段保障、重叠单据切换），主动给出贴心的参数调整建议并征求用户同意 (`Confirm_Slot`)。
4. 严禁出现“触发”、“意图保障单”等生硬机器词，语气自然专业。
请严格输出 JSON 格式：`{"sessions": [{"session_id": "...", "agent_utterance": "...", "agent_action_types": ["..."]}]}`。"""

TAU_AGENT_TURN1_USER_TEMPLATE = """【用户第 1 轮真实输入及 Agent 记忆检索观察视图】：
{turn1_agent_specs_json}

请根据用户的 `u1_utterance`、记忆检索状态与 `a1_instruction`，生成自然得体的第 1 轮 Agent 回复 `agent_utterance` 与 `agent_action_types`，严格输出 JSON。"""

TAU_USER_TURN2_SYSTEM_PROMPT = """你现在扮演通信网络保障场景中的【真实移动用户 (Tau-Bench User Simulator)】。
你正在进行多轮澄清的第 2 轮（及第 3 轮确认）交互。
【多轮澄清演进规范】：
1. 你已看到第 1 轮你自己的发言 `u1_utterance` 和 Agent 的追问/提议 `a1_utterance`。
2. 请结合 `turn2_reveal_slots` 与 `u2_instruction`，像真实人类对话一样自然承接 `a1_utterance` 的问题或提议，生成第 2 轮回复 `u2_utterance`（补充缺失参数、选定历史单据、说明现场突发天气/网络状况临时改参、延长时长，或采纳 Agent 的经验提议）。
3. 若 `round_count == 3`，表示你在第 2 轮提出了新的参数补充或变更，Agent 会在第 2 轮向你做最终核对，请同时生成第 3 轮简短自然的最终确认台词 `u3_utterance`（如“对，没问题，就按这个办”、“好的，直接开吧”）。
4. 严禁出现“触发”、“长期偏好”、“元指令”、“意图槽位”等违规词，当天会话严禁说“明天/后天”。
请严格输出 JSON 格式：`{"sessions": [{"session_id": "...", "u2_utterance": "...", "u2_action_types": ["..."], "u3_utterance": "...", "u3_action_types": ["Confirm_Slot"]}]}`。"""

TAU_USER_TURN2_USER_TEMPLATE = """【用户画像】：
- 身份：{identity}
- 说话风格：{tone} | 常用词：{catchphrases}

【第 1 轮交互历史与第 2 轮待披露/确认的意图槽位及指引】：
{turn2_user_specs_json}

请为每个多轮会话生成自然口语化的 `u2_utterance`（以及 `round_count == 3` 时的 `u3_utterance`），严格输出 JSON。"""

TAU_AGENT_TURN2_SYSTEM_PROMPT = """你现在扮演通信网络保障智能体【联接保障 Agent (Tau-Bench Agent Simulator)】。
你正在根据多轮对话上下文完成第 2 轮（及第 3 轮）闭环响应。
【闭环响应规范】：
1. 若 `round_count == 2`：用户在 `u2_utterance` 中已完成确认、单据选择或改期说明，请生成自然简明的最终闭环答复 `a2_utterance`（动作必须包含 `Acknowledge`），准确交代最终生效的业务参数并告知已开通保障。
2. 若 `round_count == 3`：用户在 `u2_utterance` 中补充了新参数或提出了临时修改，请在第 2 轮 `a2_utterance` 中清晰汇总更新后的完整参数并向用户做最后核对（动作必须为 `Confirm_Slot`，严禁提前 `Acknowledge`）；并在第 3 轮 `a3_utterance` 中对用户的 `u3_utterance` 做出最终生效闭环（动作必须包含 `Acknowledge`）。
3. 严禁在台词中出现“触发”二字。
请严格输出 JSON 格式：`{"sessions": [{"session_id": "...", "a2_utterance": "...", "a2_action_types": ["..."], "a3_utterance": "...", "a3_action_types": ["Acknowledge"]}]}`。"""

TAU_AGENT_TURN2_USER_TEMPLATE = """【多轮对话上下文及 Agent 可见状态】：
{turn2_agent_specs_json}

请为每个多轮会话生成自然专业的 `a2_utterance`（以及 `round_count == 3` 时的 `a3_utterance`），严格输出 JSON。"""


def build_session_interaction_brief(s_plan: dict) -> dict[str, str]:
    """根据会话蓝图构建结构化自然交互指引（不含任何预制模板台词，确保 LLM 对话自然多样且语义完备）。"""
    tid = s_plan.get("template_id", "T2-1")
    role = s_plan.get("memory_role", "")
    b_type = s_plan.get("blueprint_type", "")
    rc = int(s_plan.get("round_count", 2) or 2)
    agility = s_plan.get("agility_factor")
    tp = s_plan.get("target_params") or {}
    env = s_plan.get("scenario_env", "")
    app, srv = tp.get("application_name", ""), tp.get("service_name", "")
    res, rtt = tp.get("resolution", ""), tp.get("rtt", "")
    start, end, dur = tp.get("start_timestamp", ""), tp.get("end_timestamp", ""), tp.get("duration", "")
    exp_id = s_plan.get("experience_id") or (s_plan.get("experience_citation") or {}).get("experience_id")
    wm_ptr = s_plan.get("working_memory_pointer") or {}

    if tid == "T1-2":
        ood_goal = s_plan.get("ood_goal", "宽带光纤装维报修")
        return {
            "interaction_mode": "1轮域外诉求直接拒止 (Fast Rejection)",
            "u1_instruction": f"用自然口语提出『{ood_goal}』诉求，不要提任何移动App或画质时延参数。",
            "a1_instruction": f"礼貌说明系统仅支持移动网络业务加速与保障，暂不支持办理『{ood_goal}』，建议联系对应专线客服 (Reject_Request)。",
        }
    if tid == "X-1":
        ood_goal = s_plan.get("ood_goal", "宽带报修")
        return {
            "interaction_mode": "1轮网内快路径闭环+域外诉求剥离 (Mixed Fast Closure)",
            "u1_instruction": f"在一句话里自然提出两件事：①在{env}用{app}做{srv}保障（必须完整说出起止时刻 {start}至{end}、时长{dur}、画质{res}、时延{rtt}，工作日切勿说成周末）；②顺便问能不能办『{ood_goal}』。",
            "a1_instruction": f"1轮内明确回复：已为您开通 {start}至{end}（{dur}）的{app}{srv}保障（{res}、{rtt}），同时礼貌说明『{ood_goal}』不在服务范围内无法办理 (Acknowledge, Reject_Request)。",
        }
    if tid == "T1-3":
        sec = s_plan.get("second_target_params") or {}
        return {
            "interaction_mode": "1轮双业务并行快路径闭环 (Dual-Intent Fast Closure)",
            "u1_instruction": f"在1轮内自然提出两项并行保障需求：①{start}至{end}（{dur}）在{env}用{app}{srv}（{res}、{rtt}）；②{sec.get('start_timestamp', start)}至{sec.get('end_timestamp', end)}（{sec.get('duration', dur)}）用{sec.get('application_name', '')}{sec.get('service_name', '')}（{sec.get('resolution', '')}、{sec.get('rtt', '')}）。",
            "a1_instruction": "1轮内同时确认这两笔并行保障的参数并直接开通生效 (Acknowledge)。",
        }
    if rc == 1 and agility == 1.0:
        return {
            "interaction_mode": "1轮成熟记忆驱动快速闭环 (Memory-Driven Fast Closure)",
            "u1_instruction": f"你和系统已经很熟了，简短自然地打个招呼：说明自己到了『{env}』，准备用『{app}』做『{srv}』，让助手按平时的配置直接把网络保上。严禁说出{res}、{rtt}或{dur}！",
            "a1_instruction": f"检测到用户的长期记忆已成熟激活(agility_factor=1.0)，无需反问确认！直接在第1轮热情回复：已按您在『{env}』的『{app}{srv}』常用配置（{start}至{end}，时长{dur}，画质{res}，时延{rtt}）一步开启保障 (Acknowledge)。",
        }
    if rc == 1:
        return {
            "interaction_mode": "1轮全参数直达快速闭环 (Explicit Fast Closure)",
            "u1_instruction": f"偶发临时需求，一次性自然说清：在『{env}』用『{app}』做『{srv}』，时间{start}至{end}（时长{dur}），要求画质{res}、时延{rtt}。切勿使用‘老规矩/照旧/清晰点就行’等习惯词。",
            "a1_instruction": f"直接确认按用户指定的参数（{app}{srv}，{start}至{end}，{dur}，{res}，{rtt}）立即开通保障 (Acknowledge)。",
        }
    if role == "evidence_session":
        sm = s_plan.get("small_memory") or {}
        u2_extra = f"，并顺带用口语提一句自己平时习惯叫『{sm.get('value')}』" if sm.get("value") else "，并自然提一句以后在这个场景/时间段基本都按这个标准来"
        return {
            "interaction_mode": "3轮冷启动缺参追问澄清 (Cold-Start Multi-Turn Clarification)",
            "u1_instruction": f"首次在『{env}』发起需求，只自然说出所在地点『{env}』、开始时间『{start}』以及想用『{app}』做『{srv}』。严禁在首轮说出画质({res})、时延({rtt})和时长({dur})！",
            "a1_instruction": f"背景无先验记忆，请礼貌回应『{env}』的『{app}{srv}』需求，主动追问本次大概持续多久、对画面清晰度和网络时延有什么要求 (Request_Slot)，严禁提前说出{res}/{rtt}/{dur}。",
            "u2_instruction": f"自然回答客服的追问：说明持续时长『{dur}』（到{end}结束），画质要求『{res}』，时延要求『{rtt}』{u2_extra}。",
            "a2_instruction": f"汇总刚才补齐的完整参数（{app}{srv}，{start}至{end}，时长{dur}，画质{res}，时延{rtt}），请用户做最后确认 (Confirm_Slot)。",
        }
    if tid == "T2-3" or b_type == "event_override":
        return {
            "interaction_mode": "3轮现场突发状况临时改参澄清 (On-Site Anomaly Override Clarification)",
            "u1_instruction": f"自然说出自己今天在『{env}』，准备『{start}』开始用『{app}』做『{srv}』，让助手先按平时的老规矩看下排期。首轮严禁提前说出临时调整后的{res}和{rtt}！",
            "a1_instruction": "调取用户平时的长期记忆参数（如1080p等默认配置），询问今天是否照常按平时标准执行 (Confirm_Slot)。",
            "u2_instruction": f"自然说明今天『{env}』现场遇到突发天气/人流拥塞导致网络信号不稳，怕平时的高配撑不住，今天这单临时改成画质『{res}』、时延『{rtt}』（时长仍按{dur}，到{end}结束），平时习惯不用改。",
            "a2_instruction": f"表示理解现场特殊网络状况，确认仅将今日这笔『{app}{srv}』临时调整为 {res}、{rtt}（{start}至{end}，{dur}），不影响日常偏好，请用户最终确认 (Confirm_Slot)。",
        }
    if tid == "T2-4":
        sec = s_plan.get("second_target_params") or {}
        app2, srv2 = sec.get("application_name", "抖音"), sec.get("service_name", "开直播")
        res2, rtt2 = sec.get("resolution", res), sec.get("rtt", rtt)
        s2 = s_plan.get("start2") or sec.get("start_timestamp", end)
        e2 = s_plan.get("end2") or sec.get("end_timestamp", end)
        d2 = s_plan.get("dur2") or sec.get("duration", dur)
        if b_type == "multi_intent_experience" or exp_id == "EXP_MULTI_INTENT_PARTITION_01":
            return {
                "interaction_mode": "2轮彩排与正式开播双意图经验切分 (Experience-Driven Dual-Intent Partition)",
                "u1_instruction": (
                    f"自然说出今天在『{env}』有两段安排：①先在『{start}』至『{end}』（时长{dur}，画质{res}，时延{rtt}）"
                    f"跟搭档私下对一下抖音直播的词和看镜头机位；②接着在『{s2}』至『{e2}』（时长{d2}，画质{res2}，时延{rtt2}）正式用『{app2}』做『{srv2}』。"
                ),
                "a1_instruction": (
                    f"引用历史经验（EXP_MULTI_INTENT_PARTITION_01：私下对词看机位实际用微信视频通话），主动为用户切分为两笔保障单："
                    f"第1笔『{start}至{end}（{dur}，{res}，{rtt}）』设为『微信-视频通话』，第2笔『{s2}至{e2}（{d2}，{res2}，{rtt2}）』设为『{app2}-{srv2}』，请用户确认 (Confirm_Slot)。"
                ),
                "u2_instruction": f"欣然确认：第一段私下对词看机位就按微信视频通话（{start}至{end}，{dur}，{res}，{rtt}），第二段正式开播按{app2}{srv2}（{s2}至{e2}，{d2}，{res2}，{rtt2}）执行。",
                "a2_instruction": f"确认已为您同时开通『微信视频通话（{start}至{end}，{dur}，{res}，{rtt}）』与『{app2}{srv2}（{s2}至{e2}，{d2}，{res2}，{rtt2}）』两笔保障 (Acknowledge)。",
            }
        return {
            "interaction_mode": "2轮双异构业务并行办理与参数补齐 (Heterogeneous Dual-Intent Clarification)",
            "u1_instruction": (
                f"自然说出今天在『{env}』有两项安排：①『{start}』至『{end}』（时长{dur}）用『{app}』做『{srv}』（注意：第一项严禁在首轮说出画质{res}和时延{rtt}，也不要说老规矩）；"
                f"②『{s2}』至『{e2}』（时长{d2}）用『{app2}』做『{srv2}』，第二项明确要求画质『{res2}』、时延『{rtt2}』。"
            ),
            "a1_instruction": (
                f"确认已记录第2项『{app2}{srv2}（{s2}至{e2}，{d2}，{res2}，{rtt2}）』，同时针对第1项『{app}{srv}（{start}至{end}，{dur}）』"
                f"询问或建议是否按画质『{res}』、时延『{rtt}』配置 (Confirm_Slot)。"
            ),
            "u2_instruction": f"明确回复：第一项『{app}{srv}（{start}至{end}，{dur}）』就按画质『{res}』、时延『{rtt}』来办，第二项『{app2}{srv2}（{s2}至{e2}，{d2}，{res2}，{rtt2}）』保持不变，两单一起开。",
            "a2_instruction": f"确认已为您同时开通『{app}{srv}（{start}至{end}，{dur}，{res}，{rtt}）』与『{app2}{srv2}（{s2}至{e2}，{d2}，{res2}，{rtt2}）』两笔保障 (Acknowledge)。",
        }
    if tid == "T2-5":
        base_dur = s_plan.get("base_duration", "120min")
        base_end = s_plan.get("base_end_timestamp", "")
        return {
            "interaction_mode": "3轮保障时长临时延长澄清 (Duration Extension Clarification)",
            "u1_instruction": f"自然说出自己在『{env}』，准备『{start}』开始用『{app}』做『{srv}』，让助手先按平时的老规矩看下排期。首轮严禁提前说出延长后的时长{dur}！",
            "a1_instruction": f"调取日常记忆参数（画质{res}、时延{rtt}、原定时长{base_dur}至{base_end}），询问今天是否按这套原定时长执行 (Confirm_Slot)，严禁提前说出{dur}！",
            "u2_instruction": f"回答说画质{res}和时延{rtt}照旧，但今天活动内容较多，原定的{base_dur}不够用，需要把保障时长延长到『{dur}』（一直保到{end}结束）。",
            "a2_instruction": f"确认已将今日保障时长延长为 {dur}（{start}至{end}，{res}，{rtt}），请用户做最后确认 (Confirm_Slot)。",
        }
    if tid in ("T2-6", "T2-7"):
        if wm_ptr.get("is_disambiguation") or exp_id == "EXP_ORDER_QUALITY_DISAMBIGUATION_01":
            return {
                "interaction_mode": "多轮历史工单多候选冲突消歧 (Working Memory Multi-Ticket Disambiguation)",
                "u1_instruction": f"自然提出今天在『{env}』想照着之前办过的『{app}{srv}』历史工单再开一单，从『{start}』开始。",
                "a1_instruction": "说明在历史记录中查到 2 笔同场景的『{app}{srv}』工单（列举两笔工单在时长/画质或历史网络质量日志上的差异），请用户澄清具体复用哪一笔 (Request_Disambiguation)。",
                "u2_instruction": f"明确拍板选择目标工单（时长{dur}、画质{res}、时延{rtt}、体验稳定无卡顿的那笔），时间从{start}到{end}。",
                "a2_instruction": f"若为2轮则直接确认开通({app}{srv}，{start}至{end}，{dur}，{res}，{rtt})；若为3轮则先复述核对 (Confirm_Slot)。",
            }
        if tid == "T2-7":
            return {
                "interaction_mode": "2轮历史工单改期澄清 (Working Memory Ticket Reschedule)",
                "u1_instruction": f"自然提出之前在『{env}』预约的『{app}{srv}』工单需要临时改期调整时间。",
                "a1_instruction": f"定位到该笔历史工单（{app}{srv}，{res}，{rtt}，时长{dur}），询问用户需要改期到今天哪个具体时间段 (Request_Slot)。",
                "u2_instruction": f"明确告知改期后的新时间段为『{start}』至『{end}』（保持时长{dur}、{res}、{rtt}不变）。",
                "a2_instruction": f"确认已将工单改期至 {start}至{end}（{dur}，{res}，{rtt}）并生效 (Acknowledge)。",
            }
        return {
            "interaction_mode": "3轮历史工单参数复用澄清 (Working Memory Ticket Reuse)",
            "u1_instruction": f"自然提出今天在『{env}』想直接复用上次那笔『{app}{srv}』历史工单的配置，省得重新设参数。",
            "a1_instruction": f"报出查到的历史工单配置（{app}{srv}，画质{res}，时延{rtt}，时长{dur}），询问今天打算从几点开始执行 (Confirm_Slot)。",
            "u2_instruction": f"告知今天从『{start}』开始，到『{end}』结束（共{dur}），参数就按那笔历史单子来。",
            "a2_instruction": f"复述完整配置（{start}至{end}，{dur}，{res}，{rtt}）请用户做最终确认 (Confirm_Slot)。",
        }
    if role == "learning_session" or b_type == "experience_learning":
        nom_s = s_plan.get("nominal_start") or start
        nom_d = s_plan.get("nominal_dur") or dur
        if exp_id == "EXP_PREWARM_BUFFER_01":
            u2_inst = f"突然想到在『{env}』这种大型场馆开播前现场调试经常来不及调试、手忙脚乱，主动要求把今天开始时间提前30分钟改从『{start}』开始预热（保到{end}结束），总时长扩充为『{dur}』，并明确要求画质『{res}』、时延『{rtt}』，叮嘱助手以后凡是去大型场馆都记得提前半小时预热。"
        elif exp_id == "EXP_CALENDAR_HOLIDAY_EXCEPTION_01":
            u2_inst = f"经提醒意识到原定的『{nom_s}』正逢国庆法定假期不出工，主动要求将排期顺延到节后首个工作日『{start}』至『{end}』（时长{dur}），并明确要求画质『{res}』、时延『{rtt}』，叮嘱助手把这个节假日顺延经验记下来。"
        elif exp_id == "EXP_MULTI_INTENT_PARTITION_01":
            u2_inst = f"补充说明：像这种开播前私下跟搭档对一下直播词和看镜头机位，我们平时都是用微信视频通话（不直接开公开直播），本次采用画质『{res}』、时延『{rtt}』（时间{start}至{end}，时长{dur}），并叮嘱助手把这个经验记下来。"
        else:
            u2_inst = f"结合现场实际踩坑情况，说明需要采用画质『{res}』、时延『{rtt}』（时间{start}至{end}，时长{dur}），并叮嘱助手把这个经验教训记下来以后遇到同类情况主动提醒。"
        return {
            "interaction_mode": "3轮现场踩坑与经验归纳对话 (Experience Learning Multi-Turn)",
            "u1_instruction": f"自然提出在『{env}』从『{nom_s}』开始用『{app}』做『{srv}』（原计划时长{nom_d}，首轮严禁说出画质{res}和时延{rtt}，也不要用‘别掉链子/稳住节奏/老规矩’等词）。",
            "a1_instruction": f"核对用户的『{app}{srv}』诉求并询问具体保障参数或确认排期 (Confirm_Slot)。",
            "u2_instruction": u2_inst,
            "a2_instruction": f"汇总更新后的参数（{app}{srv}，{start}至{end}，时长{dur}，画质{res}，时延{rtt}），表示已将该条经验规则沉淀记下，请用户最终确认本次执行 (Confirm_Slot)。",
        }
    if exp_id:
        nom_s = s_plan.get("nominal_start") or start
        nom_d = s_plan.get("nominal_dur") or dur
        u1_inst = (
            f"自然提出在『{env}』预约从『{nom_s}』（必须明确说出该具体日期与时刻，严禁说成‘今天’！）开始、计划时长『{nom_d}』用『{app}』做『{srv}』，要求画质『{res}』、时延『{rtt}』。"
            if exp_id == "EXP_CALENDAR_HOLIDAY_EXCEPTION_01"
            else f"自然说出在『{env}』准备从『{nom_s}』开始（计划时长『{nom_d}』）用『{app}』做『{srv}』，要求画质『{res}』、时延『{rtt}』。"
        )
        return {
            "interaction_mode": "2轮历史经验主动提醒与协商 (Experience-Driven Proactive Negotiation)",
            "u1_instruction": u1_inst,
            "a1_instruction": f"主动引用之前沉淀的经验卡片（{exp_id}），贴心向用户建议调整后的方案：时间『{start}』至『{end}』（时长{dur}），画质『{res}』、时延『{rtt}』，询问用户是否采纳该经验方案 (Confirm_Slot)。",
            "u2_instruction": f"欣然采纳助手的经验提议，确认按调整后的 {start}至{end}（{dur}，{res}，{rtt}）执行。",
            "a2_instruction": f"确认已按经验优化方案（{start}至{end}，{dur}，{res}，{rtt}）为您开通保障 (Acknowledge)。",
        }
    return {
        "interaction_mode": "2轮候选记忆参数核对澄清 (Memory Confirmation Multi-Turn)",
        "u1_instruction": f"自然说出自己到了『{env}』，准备从『{start}』开始用『{app}』做『{srv}』，请助手帮忙安排网络保障。注意：首轮严禁说出画质({res})、时延({rtt})、时长({dur})，也不要说‘按上次/平时的配置/老规矩’！",
        "a1_instruction": f"从记忆中调取到『{app}{srv}』的候选配置（{start}至{end}，时长{dur}，画质{res}，时延{rtt}），自然询问用户今天是否按这套参数开通 (Confirm_Slot)。",
        "u2_instruction": f"明确确认采纳助手提议的配置：按时长『{dur}』（到{end}结束）、画质『{res}』、时延『{rtt}』执行。",
        "a2_instruction": f"确认已按 {app}{srv}（{start}至{end}，{dur}，{res}，{rtt}）正式开通保障，并将该习惯巩固生效 (Acknowledge)。",
    }


__all__ = [
    "TAU_USER_TURN1_SYSTEM_PROMPT",
    "TAU_USER_TURN1_USER_TEMPLATE",
    "TAU_AGENT_TURN1_SYSTEM_PROMPT",
    "TAU_AGENT_TURN1_USER_TEMPLATE",
    "TAU_USER_TURN2_SYSTEM_PROMPT",
    "TAU_USER_TURN2_USER_TEMPLATE",
    "TAU_AGENT_TURN2_SYSTEM_PROMPT",
    "TAU_AGENT_TURN2_USER_TEMPLATE",
    "build_session_interaction_brief",
]
