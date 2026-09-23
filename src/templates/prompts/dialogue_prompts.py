import json

def build_batch_dialogue_prompt(prompt_items: list[dict], identity: str, speech: dict) -> str:
    """
    构建批量渲染多轮对话的完整 Prompt。
    包含 8 种会话模版（T2-4, T2-2, T2-1, T1-2, T2-5, X-1, T2-3, T1-1）的动作规范与生成要求。
    """
    return f"""请根据以下人物画像背景与这组会话要求，为每个会话渲染真实、口语化的网络保障交互对话。

【人物风格】:
- 身份描述: {identity}
- 语气风格: {speech.get('tone')}
- 口头禅/表达习惯: {speech.get('catchphrases')} | {speech.get('typical_habits')}

【待生成会话列表】:
{json.dumps(prompt_items, ensure_ascii=False, indent=2)}

【核心会话轮次与动作规则（严格遵守）】:
0. 用户台词口语别名多样化（强制遵守）:
   - 用户台词中严禁机械复述官方标准词（切勿总是生硬复述“抖音开直播1080p50ms”），必须多使用本次会话配置中的 `aliases` 口语化别名与行话：
     * 应用名：优先多用 `aliases.app_aliases`（如“阿抖”、“某手”、“企微”、“小破站”、“鹅厂会议”等）；
     * 业务名：优先多用 `aliases.service_aliases`（如“推流”、“开播”、“打视讯”、“连麦”、“对齐开会”、“刷短剧”等）；
     * 画质：优先多用 `aliases.resolution_aliases`（如“原画”、“顶格清晰度”、“千万别糊”、“蓝光”、“高清”等）；
     * 时延：优先多用 `aliases.rtt_aliases`（如“别掉链子”、“零卡顿”、“极速响应”、“秒级同步”、“别转圈”等）；
     * 时长：优先多用 `aliases.duration_aliases`（如“俩小时”、“两钟头”、“播到四点”、“一个半小时”等）；
     * 周期/触发表达：优先多用 `aliases.period_aliases`（如“每天这个时候”、“老时间”、“周一例会照旧”、“月初开门红”等）。

1. 会话结束与动作总规则：
   - 常规会话最后一轮必须由 Agent 的答复结束，最后一轮 Agent agent_action_types 必须包含 "Acknowledge"！
   - 特例1【纯域外拒绝 T1-2】(rounds == 1):
     * 用户因网络故障提出非手机保障类诉求（即 ood_goal，如宽带光纤装维报修）；user_action_types 为 ["Create_Intent_Request"]。
     * Agent 礼貌拒绝该域外需求，说明本助手仅支持手机移动网络保障加速，不支持光纤宽带装维报修，建议拨打专线；agent_action_types 必须为 ["Reject_Request"]！
   - 特例2【混合诉求一办一拒 X-1】(rounds == 1):
     * 用户单句同时提出手机网络保障需求 (app/service) 和域外诉求（即 ood_goal，如话费充值与账单查询）；user_action_types 为 ["Create_Intent_Request", "Inform_Slot"]。
     * Agent 接受并受理移动网络保障，同时拒绝域外诉求；agent_action_types 必须为 ["Acknowledge", "Reject_Request"]！
   - 特例3【歧义消解 T2-2】(rounds == 2):
     * 第1轮 User 提出模糊需求（如仅提app未说清具体service）；user_action_types 为 ["Create_Intent_Request", "Inform_Slot"]。
     * 第1轮 Agent 执行歧义追问确认（如询问进行哪个业务保障）；agent_action_types 必须为 ["Request_Disambiguation"]。
     * 第2轮 User 明确消解歧义并说明参数；user_action_types 为 ["Inform_Slot"]。
     * 第2轮 Agent 答复已开通并收尾；agent_action_types 必须为 ["Acknowledge"]。
   - 特例4【时长变更延长 T2-5】(rounds == 2):
     * 第1轮 User 提及老规矩保障；Agent 反问确认老规矩配置（agent_action_types 为 ["Confirm_Slot"]）。
     * 第2轮 User 确认老规矩但提出因现场活动延长，要求将时长延长（user_action_types 必须包含 ["Confirm_Slot", "Modify_Request"]）。
     * 第2轮 Agent 确认时长已延长并生效；agent_action_types 必须为 ["Acknowledge"]。

2. 首次建联/证据会话 (evidence_session):
   - 若 declaration_mode == "explicit_declaration" (显式声明):
     第1轮 User: 结合现场环境提出模糊需求；Agent 追问确认细节。
     第2轮 User: 明确说清参数，并【明确显式声明长期偏好与周期触发条件/暗号】:
       * 若 storyline_trigger_type == "time_periodic" 且 period_type == "daily": 如"以后我只要每天这个时段说'老规矩'，就按这个来：对应应用、画质、时延以内，记一下长期偏好，别掉链子"；
       * 若 storyline_trigger_type == "time_periodic" 且 period_type == "weekly": 如"以后我只要在每周例行时段说'老规矩'，就按这个来：对应应用、画质、时延以内，记一下长期偏好，别掉链子"；
       * 若 storyline_trigger_type == "time_periodic" 且 period_type == "monthly": 如"以后我只要在每月月初/固定月度对账说'老规矩'，就按这个来：对应应用、画质、时延以内，记一下长期偏好，别掉链子"；
       * 若 storyline_trigger_type == "task_activity": 如"以后只要我提到执行【特定任务】现场，老规矩就按这个来：对应应用、画质、时延以内，记一下长期偏好，别掉链子"；
       * 若 storyline_trigger_type == "location_environment": 如"以后只要我身处【特定地点/弱网区域】，老规矩就按这个来：对应应用、画质、时延以内，记一下长期偏好，别掉链子"；
     Agent 必须明确闭环回复：“好的，已为您开通本次保障，并已为您将该配置记录为长期老规矩！”
   - 若 declaration_mode == "implicit_induction" (隐式归纳):
     第1轮 User: 仅针对本次单次保障需求提出申请，【严禁出现任何‘记一下/以后都按这个/老规矩’等元指令词】（如：“今天执行任务/在该地点，帮我开个保障...”）；Agent 追问确认细节。
     第2轮 User: 仅确认本次单次任务参数（如：“好的，今天就按这个配置开通”）；Agent 确认受理单次任务结束，不擅自假设长期偏好。

3. 记忆强化/复用 (reinforcement / reuse):
   - 若 active_memory 中包含 [provisional] (隐式偏好二次发生，触发固化契机):
     第1轮 User: 再次在相似触发场景下提出需求（如：“今天又来执行XX任务了/又到这个时间了/又到这个地点了，跟上次一样就行”）。
     第1轮 Agent: 必须根据历史行为主动反问向用户建议固化：“检测到您在【触发条件】多次使用该配置，是否按上次标准为您开通并设为长期老规矩？”（agent_action_types包含 "Confirm_Slot"）。
     第2轮 User: 明确确认固化（如：“对，以后遇到这个场景就按这个来”）（user_action_types包含 "Confirm_Slot"）。
     第2轮 Agent: 答复已开通并收尾祝福，正式记录老规矩（agent_action_types: ["Acknowledge"]）。
   - 若 active_memory 包含 [active] (常规复用已生效记忆):
     第1轮 User: 口语化提出需求，提及触发场景并【必须省略应用或画质时延等参数】（如使用"老规矩"、"每天照旧"、"照上周的来"等）。
     第1轮 Agent: 必须明确调取上方 active_memory 中的配置，结合触发条件主动反问向用户确认（agent_action_types包含 "Confirm_Slot"）。
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

def build_single_dialogue_prompt(s_plan: dict, persona: dict, snapshot_before: dict) -> str:
    """
    单会话渲染兜底 Prompt。
    """
    role = s_plan["memory_role"]
    b_type = s_plan["blueprint_type"]
    tp = s_plan["target_params"]
    env = s_plan["scenario_env"]
    speech = persona["static_profile"]["speech_style"]
    identity = persona["static_profile"]["identity"]
    round_count = s_plan["round_count"]
    tid = s_plan.get("template_id", "T2-1")
    ood_goal = s_plan.get("ood_goal", "")

    if snapshot_before:
        memory_context_str = "当前已建立的记忆快照 (Memory Snapshot Before):\n"
        for mid, mval in snapshot_before.items():
            memory_context_str += f"  - [{mid}] 应用: {mval['application_name']}, 业务: {mval['service_name']}, 画质: {mval['resolution']}, 时延: {mval['rtt_max']}, 状态: {mval.get('status')}\n"
    else:
        memory_context_str = "当前记忆快照为空（首次建联会话，尚无已形成的长期记忆）。\n"

    return f"""请根据以下人物背景、场景环境和记忆规则，渲染一段极其真实、口语化的多轮人机交互对话。

【人物画像】:
- 身份描述: {identity}
- 语气风格: {speech.get('tone')}
- 口头禅/表达习惯: {speech.get('catchphrases')} | {speech.get('typical_habits')}

【当前生效的历史记忆 (Memory Snapshot)】:
{memory_context_str}

【当前场景与网络动机】:
- 会话模版: {tid} (角色: {role}, 类型: {b_type})
- 发生时间: {s_plan['reference_time']}
- 现场环境: {env}
- 偏好模式: {s_plan.get('declaration_mode', 'explicit_declaration')}
- 触发类型: {s_plan.get('storyline_trigger_type', 'time_periodic')} (触发条件: {s_plan.get('trigger_condition', env)})
- 目标保障业务: 应用={tp['application_name']}, 业务={tp['service_name']}, 分辨率={tp['resolution']}, 时延上限={tp['rtt']}, 时段={tp['start_timestamp']} 至 {tp['end_timestamp']} (时长{tp['duration']})
{"- 域外诉求目标: " + ood_goal if ood_goal else ""}

【核心会话轮次与动作规则（严格遵守）】:
0. 用户台词口语别名多样化（强制遵守）:
   - 用户台词中多使用行话与口语偏好词，避免机械复述；APP、业务、画质、时延、时长、周期尽量使用口语化表达（如“阿抖推流”、“原画”、“别掉链子”、“俩小时”、“每天这个时候”等）。
1. 最后一轮必须由 Agent 的答复结束！
   - 常规会话最后一轮 Agent agent_action_types 必须包含 "Acknowledge"；
   - T1-2 纯域外拒绝会话 (rounds == 1): Agent 必须礼貌拒绝，agent_action_types 必须为 ["Reject_Request"]；
   - X-1 混合诉求会话 (rounds == 1): Agent 办理保障同时拒绝域外诉求，agent_action_types 必须为 ["Acknowledge", "Reject_Request"]；
   - T2-2 歧义消解会话 (rounds == 2): 第1轮 Agent 反问消解歧义（["Request_Disambiguation"]），第2轮用户说明业务后 Agent 确认开通；
   - T2-5 时长延长会话 (rounds == 2): 第1轮 Agent 确认老规矩配置（["Confirm_Slot"]），第2轮用户提出延长时长（user_action_types 包含 ["Confirm_Slot", "Modify_Request"]），Agent 确认延长并生效。
2. 首次建联/证据会话 (evidence_session):
   - 若 declaration_mode == "explicit_declaration" (显式声明):
     第1轮 User: 结合现场环境提出模糊需求；Agent 追问确认细节。
     第2轮 User: 明确说清参数，并【明确显式声明长期偏好与暗号/触发条件】:
       * 若 storyline_trigger_type == "time_periodic" 且 period_type == "daily": 如"以后我只要每天这个时段说'老规矩'，就按这个来：{tp['application_name']}、{tp['resolution']}、{tp['rtt']}以内，记一下长期偏好，别掉链子"；
       * 若 storyline_trigger_type == "time_periodic" 且 period_type == "weekly": 如"以后我只要在每周例行时段说'老规矩'，就按这个来：{tp['application_name']}、{tp['resolution']}、{tp['rtt']}以内，记一下长期偏好，别掉链子"；
       * 若 storyline_trigger_type == "time_periodic" 且 period_type == "monthly": 如"以后我只要在每月月初/固定月度对账说'老规矩'，就按这个来：{tp['application_name']}、{tp['resolution']}、{tp['rtt']}以内，记一下长期偏好，别掉链子"；
       * 若 storyline_trigger_type == "task_activity": 如"以后只要我提到执行【{s_plan.get('trigger_condition', '该任务')}】现场，老规矩就按这个来：{tp['application_name']}、{tp['resolution']}、{tp['rtt']}以内，记一下长期偏好，别掉链子"；
       * 若 storyline_trigger_type == "location_environment": 如"以后只要我身处【{s_plan.get('trigger_condition', env)}】，老规矩就按这个来：{tp['application_name']}、{tp['resolution']}、{tp['rtt']}以内，记一下长期偏好，别掉链子"；
     Agent 必须明确闭环回复：“好的，已为您开通本次保障，并已为您将该配置记录为长期老规矩！”
   - 若 declaration_mode == "implicit_induction" (隐式归纳):
     第1轮 User: 仅针对本次单次保障需求提出申请，【严禁出现任何‘记一下/以后都按这个/老规矩’等元指令词】（如：“今天执行任务/在该地点，帮我开个保障...”）；Agent 追问确认细节。
     第2轮 User: 仅确认本次单次任务参数（如：“好的，今天就按这个配置开通”）；Agent 确认受理单次任务结束，不擅自假设长期偏好。
3. 记忆强化/复用 (reinforcement / reuse):
   - 若上方记忆快照包含 [provisional] (隐式偏好二次发生，触发固化契机):
     第1轮 User: 再次在相似触发场景下提出需求（如：“今天又来执行XX任务了/又到这个地点了，跟上次一样就行”）。
     第1轮 Agent: 必须根据历史行为主动反问向用户建议固化：“检测到您在【{s_plan.get('trigger_condition', env)}】多次使用该配置，是否按上次标准（{tp['resolution']}/{tp['rtt']}）为您开通并设为长期老规矩？”（agent_action_types包含 "Confirm_Slot"）。
     第2轮 User: 明确确认固化（如：“对，以后遇到这个场景就按这个来”）（user_action_types包含 "Confirm_Slot"）。
     第2轮 Agent: 答复已开通并收尾祝福，正式记录老规矩（agent_action_types: ["Acknowledge"]）。
   - 若上方记忆快照包含 [active] (常规复用已生效记忆):
     第1轮 User: 口语化提出需求，提及触发场景并【必须省略应用或画质时延等参数】（如使用"老规矩"、"照上次的来"等）。
     第1轮 Agent: 必须明确调取上方 active_memory 中的配置，结合触发条件主动反问向用户确认（agent_action_types包含 "Confirm_Slot"）。
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
