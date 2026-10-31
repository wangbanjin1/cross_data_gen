"""
提示词模板与静态词表常量模块 (Prompt & Template Constants).
将多行提示词模板、系统角色指令、JSON 输出契约及默认映射词表与算法逻辑彻底解耦。
"""

from __future__ import annotations

BATCH_DIALOGUE_SYSTEM_PROMPT = (
    "You are a professional natural language dialogue generator for network assistant datasets. Output valid JSON only."
)

SINGLE_DIALOGUE_SYSTEM_PROMPT = (
    "You are a professional natural language dialogue generator for network assistant datasets."
)

PERSONA_SKELETON_SYSTEM_PROMPT = (
    "You are a professional dataset engineer for network agent memory systems."
)

LOCATION_EXTRACTION_SYSTEM_PROMPT = (
    "You are a concise location naming assistant. Output valid JSON only."
)

LOCATION_EXTRACTION_USER_TEMPLATE = """请从以下人物背景、任务与场景描述中，提炼出 1 个最适合作为日常口语对话中【地点/现场】的简短名词短语。

用户职业身份：{identity}
任务名称：{task_name}
触发场景规则：{raw_trig_cond}

【要求】：
1. 必须是纯地点名词短语，长度在 3 到 7 个汉字之间（如：“道路巡逻现场”、“社区走访现场”、“沿海巡逻岸线”、“高山露天训练场”、“野外地质勘查区”）。
2. 严禁包含“当...时”、“触发现场...”、“需要...”等任何条件句式或动词引导词。
3. 仅输出 JSON 格式：{{"location_name": "简短地点名"}}"""

BATCH_DIALOGUE_RULES_BLOCK = """【核心生成原则（极为重要）】：
请结合【人物风格】（身份、语气、口头禅）对每个会话的 `reference_turns` 进行自然口语化润色渲染，生成富有个人特色的对白，同时**必须 100% 保留 `reference_turns` 中的所有核心业务锚点、应用名/指定别名、业务名/隐含动宾短语、具体时刻点、时长数值、画质档位、时延数值、否定排除从句以及意图保障单/经验规则关键信息**，严禁遗漏或篡改任何参数数值！

【核心会话轮次与动作规则（严格遵守）】:
0. 用户台词口语别名与大/小记忆点分级规则（强制遵守）:
   - 【证据会话（evidence_session）】:
     * 第1轮 User：必须使用清晰、标准、无歧义的官方应用名（app）与业务名（service），如“抖音”、“微信”、“腾讯会议”；“开直播”、“视频通话”、“会议”。可提开始时间（如“今晚8点”），【严禁在第1轮提及结束时间或持续时长，严禁在第1轮使用生僻别名（如'阿抖'、'某手'），严禁使用'老规矩'、'老时间'等未生效的个性化表达】！确保大记忆点冷启动清晰无误；
     * 第1轮 Agent：识别并明确确认用户提出的应用与业务（如“收到，您是要在抖音开直播对吧？”），仅针对未提及的画质（resolution）、时延（rtt）、持续时长（duration）进行细节追问；
     * 第2轮 User：必须完整补充本次画质、时延与持续时长（持续时长不得遗漏，必须在台词中明确说出，如持续XX分钟或XX小时）。是否登记小记忆点严格服从该会话的 turn1_requirement：隐式归纳首次证据不得登记；显式声明只能登记指定的一项，并使用与其参数类型匹配的话术。
   - 【后续复用与强化会话（reinforcement_session / reuse_session，如 S-03, S-06, S-07, S-08 等）】:
     * 第1轮 User：应用与业务是最小表达。除非当前主线已有业务默认应用记忆，否则必须说出应用和业务；应用别名只能替代应用名，仍须说业务；画质、时延、时长和个性化周期表达只能替代对应参数，仍须说应用和业务。业务默认应用不得覆盖支线，其余省略参数由 Agent 展开后确认。
     * 第1轮 Agent：依据历史记忆成功理解别名，并主动调取记忆中的精确配置（如 1080p原画、50ms以内、持续120分钟）向用户反问确认；
     * 第2轮 User：直接简短确认（如“对，直接开通”）；
     * 第2轮 Agent：确认开通并祝福收尾。
   - 【参数别名一致性与对齐律（Parameter Alias Alignment Law）】:
     * 凡在任何会话中涉及画质或时延的具体称谓，必须与数值档位真实严谨对齐：
       - 1080p 只能称为“1080p”、“1080p原画”或“超清”，严禁使用会混淆 2K/4K 的“顶格清晰度”或“最高画质”；
       - 720p 只能称为“720p”或“高清”；
       - 4K 称为“4K”或“超高清”；
       - 50ms 只能称为“50ms以内”、“50毫秒以内”或“低时延”，严禁使用物理上失真夸大的“零卡顿”；
       - 100ms 称为“100ms以内”或“100毫秒”。
     * 同一人物在整条时间线各会话中，对同一主线/支线参数的称谓必须全局统一对齐，严禁同一条主线在 S-01 叫“1080p原画，50ms以内”，到了后续会话擅自跳变成其他生词！

1. 会话结束与动作总规则：
   - 常规会话最后一轮必须由 Agent 的答复结束，最后一轮 Agent agent_action_types 必须包含 "Acknowledge"！
   - 特例1【纯域外拒绝 T1-2】(rounds == 1):
     * 用户因网络故障提出非手机保障类诉求（即 ood_goal，如宽带光纤装维报修）；user_action_types 为 ["Create_Intent_Request"]。
     * Agent 礼貌拒绝该域外需求，说明本助手仅支持手机移动网络保障加速，不支持光纤宽带装维报修，建议拨打专线；agent_action_types 必须为 ["Reject_Request"]！
   - 特例2【混合诉求一办一拒 X-1】(rounds == 1):
     * 用户单句同时提出手机网络保障需求 (app/service) 和域外诉求（即 ood_goal，如话费充值与账单查询）；user_action_types 为 ["Create_Intent_Request", "Inform_Slot"]。
     * 【时间词严谨约束】：单轮会话必须自闭环时间范围！用户台词必须明确说出具体起止时间点（如‘12点30分到13点30分’或‘12:30至13:30’）以及持续时长（如‘持续60分钟’或‘开60分钟保障’），严禁只说‘午休’、‘中午’或‘刷会儿’等无法确定起止点的模糊词汇！若当前环境为工作日午休，用户严禁使用‘周末’字样，必须说‘午休’或‘今天中午’；若为周末午休才可说‘周末’！
     * Agent 接受并受理移动网络保障，同时拒绝域外诉求；agent_action_types 必须为 ["Acknowledge", "Reject_Request"]！
   - 特例3【三轮参数澄清 T3-1 与 歧义消解 T2-2】(rounds == 3 或 2):
     * 第1轮 User 必须明确官方应用名与业务名，可说明开始时间，但不说画质、时延、结束时间和时长；user_action_types 为 ["Create_Intent_Request", "Inform_Slot"]。
     * 第1轮 Agent 确认应用与业务，只追问画质、时延和持续时长；agent_action_types 必须为 ["Request_Slot"]。
     * 若 small_memory_evidence_mode == "cross_turn_clarification"：第2轮用户使用模糊小记忆表达但不说对应标准值；Agent 必须开放式追问具体标准值，不能替用户猜答案；第3轮由用户亲口说出标准值并确认以后按此理解，Agent 才受理并记录。
     * 第2轮 User 明确消解歧义说明业务与参数，并严格按照 turn1_requirement 登记指定的一项小记忆；支线不得使用 service_default_app，只能登记应用昵称或画质、时延、时长、个性化时间表达；user_action_types 为 ["Inform_Slot"]。
     * 第2轮 Agent 答复已开通并收尾祝福，明确确认记录该配置与代称习惯；agent_action_types 必须为 ["Acknowledge"]。
   - 特例4【时长变更延长 T2-5】(rounds == 3):
     * 第1轮 User 提及老规矩保障；Agent 反问确认原老规矩基线配置（agent_action_types 为 ["Confirm_Slot"]）。
     * 第2轮 User 确认老规矩但提出因现场活动延长，要求将时长延长（user_action_types 必须包含 ["Confirm_Slot", "Modify_Request"]）。【严禁使用‘半天’、‘大半天’、‘一上午’等存在歧义的模糊词汇，必须明确说出具体数字（如‘延长到3个小时’或‘延长到180分钟’）】！
     * 第2轮 Agent 将配置更新为延长后的时长与结束时间，向用户发起最终确认（agent_action_types 必须为 ["Confirm_Slot"]，严禁在第2轮直接闭环开通！）。
     * 第3轮 User 明确确认按延长后的配置开通（user_action_types 为 ["Confirm_Slot"]）；第3轮 Agent 确认时长已延长并正式开通生效（agent_action_types 必须为 ["Acknowledge"]）。

2. 首次建联/证据会话 (evidence_session):
   - 若 declaration_mode == "explicit_declaration" (显式声明):
     第1轮 User: 明确提出需要保障的标准应用与业务（可提开始时间，严禁结束时间/时长，严禁别名，严禁'老规矩'）；Agent 确认应用/业务并追问画质、时延、时长细节。
     第2轮 User: 明确说清画质、时延与持续时长，并【明确显式声明长期习惯与周期触发条件/个性化表达，顺理成章引入个性化代称】。
       【非常关键：用户绝不会在日常口语中使用“长期偏好”、“元指令”等系统研发术语！严禁在台词中出现“长期偏好”！真实用户只会说：“记住这个习惯或者规矩哈”、“帮我把这个习惯记一下，以后省得每次重新挑”、“把这个规矩记住，以后照旧就行”】:
       * 若 storyline_trigger_type == "time_periodic" 且 period_type == "daily": 如"以后我只要每天这个时段说'老规矩'（我平时叫它对应代称），就按这个来：对应应用、画质、时延以内，记住这个习惯哈，别掉链子"；
       * 若 storyline_trigger_type == "time_periodic" 且 period_type == "weekly": 如"以后我只要在每周例行时段说'老规矩'（我平时叫它对应代称），就按这个来：对应应用、画质、时延以内，记住这个习惯哈，别掉链子"；
       * 若 storyline_trigger_type == "time_periodic" 且 period_type == "monthly": 如"以后我只要在每月月初/固定月度对账说'老规矩'（我平时叫它对应代称），就按这个来：对应应用、画质、时延以内，把这个规矩记一下哈，别掉链子"；
       * 若 storyline_trigger_type == "task_activity": 如"以后只要我提到执行【特定任务】现场，老规矩就按这个来（我平时叫它对应代称）：对应应用、画质、时延以内，帮我把这个习惯记好，别掉链子"；
       * 若 storyline_trigger_type == "location_environment": 如"以后只要我身处【特定地点/弱网区域】，老规矩就按这个来（我平时叫它对应代称）：对应应用、画质、时延以内，帮我把这个习惯记好，别掉链子"；
     Agent 必须明确闭环回复：“好的，已为您开通本次保障，并已为您将该配置记录为长期老规矩！”
   - 若 declaration_mode == "implicit_induction" (隐式归纳):
     第1轮 User: 仅针对本次单次保障需求提出申请，必须使用标准应用与业务，【严禁出现任何‘记一下/以后都按这个/老规矩’等元指令词】（如：“今天在现场要用抖音开直播，帮我开个保障...”）；Agent 追问确认细节。
     第2轮 User: 仅确认本次单次任务参数（如：“好的，今天就按这个配置开通”）；Agent 确认受理单次任务结束，不擅自假设长期习惯。

3. 记忆强化/复用 (reinforcement / reuse):
   - 若 active_memory 中包含 [provisional] (隐式偏好二次发生，触发固化契机):
     第1轮 User: 再次在相似触发场景下提出需求（如：“今天又来执行XX任务了/又到这个时间了，做XX业务跟上次一样就行”），【必须包含业务名作为最小锚点，但严禁在第1轮提及应用名、老规矩与生僻别名】；
     第1轮 Agent: 只能把 provisional 记录作为历史候选（history_filled），不能当作 active 记忆（memory_filled）直接使用。必须明确说是“上次记录”，结合业务名唤醒主线上次记录并完整复述应用、业务、画质、时延、持续时长及本次起止时间，再询问是否按该配置开通并设为长期老规矩；不得声称用户此前“多次使用”。（agent_action_types包含 "Confirm_Slot"）。
     第2轮 User: 明确确认固化，并在此刻按 turn1_requirement 登记指定的一项小记忆；业务类应登记“该业务未指定应用时的默认应用”，不得生造业务别名。（user_action_types包含 "Confirm_Slot"）。
     第2轮 Agent: 答复已开通并收尾祝福，正式记录老规矩与代称（agent_action_types: ["Acknowledge"]）。
   - 若 active_memory 包含 [active] (常规复用已生效记忆):
     第1轮 User: 口语化提出需求，提及触发场景、应用与业务（应用＋业务是发起保障意图的最小表达，严禁只说‘老规矩开保障’），并【必须省略画质与时延等参数】（如使用"老规矩"、"每天照旧"、"照上周的来"等）。
     第1轮 Agent: 必须明确调取上方 active_memory 中的配置，结合触发条件主动反问向用户确认（agent_action_types包含 "Confirm_Slot"）。
     第2轮 User: 明确确认 Agent 提出的配置（user_action_types包含 "Confirm_Slot"，如"对，开通吧"）。
     第2轮 Agent: 明确确认已开通并收尾祝福（agent_action_types: ["Acknowledge"]）。

4. 纠正覆盖与临时调整 (correction / event_override, T2-3) (rounds == 3):
   - 第1轮 User: 必须严格满足“场景＋应用＋业务”的最小表达，提及当前所在现场场景（如“今天在【现场环境】”）以及老规矩需求（明确说出应用与业务，若有个性化周期表达可加上个性化周期表达），【严禁只说‘老规矩开保障’或只带个性化周期表达而不说应用和业务】！
   - 第1轮 Agent: 调取原有的长期老规矩基线配置（如 1080p、50ms以内），结合起止时段向用户反问确认；
   - 第2轮 User: 明确说明现场特殊原因（如人流密集、网络拥塞、恶劣环境），提出本次临时调整参数（如画质临时调到 720p、时延压到 30ms），明确表示“今天现场特殊，临时按这个来”；
   - 第2轮 Agent: 汇总本次临时调整后的参数配置向用户发起最终确认（agent_action_types: ["Confirm_Slot"]，严禁在第2轮直接闭环开通！）；
   - 第3轮 User: 明确确认按临时调整后的配置开通（user_action_types: ["Confirm_Slot"]）；
   - 第3轮 Agent: 确认本次单次临时调整并正式开通（agent_action_types: ["Acknowledge"]）。

5. 单轮干扰项 (distractor, T1-1, T1-2, X-1):
   - T1-1 单轮单次任务 (rounds == 1): 无任何先验记忆！用户在第 1 轮必须一次性清晰、完整说清全部参数需求（应用、业务、时段、画质、时延，如'画质720p，时延控制在80ms以内'），【严禁使用‘清晰点就行’、‘不卡就行’、‘老规矩’等任何未建立的个性化记忆表达或模糊词】！Agent 直接受理开通闭环，严禁出现‘按记忆理解’等说辞；
   - T1-2 纯域外拒绝 (rounds == 1): 用户提出域外需求，Agent 礼貌拒绝；
   - X-1 混合诉求一办一拒 (rounds == 1): 用户无先验记忆，首次提出标准保障需求并附带域外需求，严禁使用未建立的个性化表达或老规矩；Agent 办理保障并明确拒绝域外需求。
6. 时长延长与修改 (amend / extend_duration, T2-5) (rounds == 3):
   - 第1轮 User: 必须严格满足“场景＋应用＋业务＋老规矩”的最小表达（如“今天在【现场环境】，老规矩，用【应用】做【业务】，帮我把保障开上”），【严禁只说‘老规矩开保障’或只带个性化表达而不说应用和业务】！严禁在第1轮提及具体画质与时延；
   - 第1轮 Agent: 调取原有的长期老规矩基线配置（画质、时延、原时长与起止时段），向用户反问确认；
   - 第2轮 User: 明确说明老规矩配置不变，但因现场活动拉长等原因，提出将时长延长/修改为指定时长（如“对，老规矩不变，不过今天现场活动延长了，帮我把保障时长延长到【时长】”）；
   - 第2轮 Agent: 将配置更新为延长后的时长与结束时段，向用户发起最终确认（agent_action_types: ["Confirm_Slot"]）；
   - 第3轮 User: 明确确认按延长后的配置开通（user_action_types: ["Confirm_Slot"]）；
   - 第3轮 Agent: 明确确认老规矩配置不变、时长已延长并正式开通（agent_action_types: ["Acknowledge"]）。
7. 工作记忆历史意图保障单跨期复用与消歧 (working_memory_reuse / disambiguation, T2-6):
   - 若为多单消歧 (is_disambiguation, rounds == 3):
     第1轮 User: 表达想按之前在该现场的意图保障单规格开通，省略画质与时延；
     第1轮 Agent: 告知检索到多笔历史意图保障单，反问用户是指哪一次（agent_action_types: ["Request_Disambiguation"]）；
     第2轮 User: 指明选最近一次意图保障单（user_action_types: ["Confirm_Slot", "Inform_Slot"]）；
     第2轮 Agent: 精准定位该意图保障单体验参数（画质、时延）并反问确认起止时段（agent_action_types: ["Confirm_Slot"]）；
     第3轮 User: 明确确认开通（user_action_types: ["Confirm_Slot"]）；
     第3轮 Agent: 确认开通并祝福收尾（agent_action_types: ["Acknowledge"]）。
   - 若为常规跨期复用 (rounds == 3):
     第1轮 User: 表达“这次去【现场环境】，还按【相对时态，如上周/上月】在【现场】办的那个意图保障单规格来”，省略画质与时延；
     第1轮 Agent: 从意图保障单账本检索定位目标单据，反问确认继承的体验参数，并询问今日具体时段（agent_action_types: ["Confirm_Slot", "Request_Slot"]）；
     第2轮 User: 补充说明今日保障起止时段与时长（user_action_types: ["Inform_Slot"]）；
     第2轮 Agent: 汇总今日完整保障配置（时段、时长及继承的画质、时延）向用户发起最终确认（agent_action_types: ["Confirm_Slot"]）；
     第3轮 User: 明确确认开通（user_action_types: ["Confirm_Slot"]）；
     第3轮 Agent: 确认开通并祝福收尾（agent_action_types: ["Acknowledge"]）。
8. 工作记忆历史单据变更改期 (working_memory_reschedule, T2-7) (rounds == 2):
   - 第1轮 User: 提出把此前预约的保障往后推迟或提前（如“把昨天预约的【应用】【业务】保障提前/推迟一个小时”）；
   - 第1轮 Agent: 调取预约意图保障单，向用户反问确认调整后的新时段；
   - 第2轮 User: 简短确认（如“对，确认提前/修改”）；
   - 第2轮 Agent: 确认改期生效并收尾。
9. 工作记忆对账核查 (working_memory_reconcile, T2-8) (rounds == 1):
   - 第1轮 User: 询问保障开通流水或全月总对账（如“帮我查下这周/这个月总共开了几次保障，一共多长时间？”）；
   - 第1轮 Agent: 调取意图保障单流水账，明确回复已开通的总次数、累计时长与明细，礼貌闭环。
10. 经验记忆 ReasoningBank 主动经验提议与多轮协商 (proactive_experience, T2-9):
   - 【Turn 1 基础参数自包含原则】：经验记忆测试聚焦于“快速闭环与经验触发识别”，第1轮 User 必须一次性把基础参数（场景、应用、业务、原定起止时间、画质、时延）说清楚，不依赖此前事实记忆！
   - 若为负反例边界 (is_counterexample): 用户明确要求原画采录/强画质优先，Agent 识别经验反例规则，主动确认不强行降级，为用户保留原画并开通；
   - 若 rounds == 3 (经验协商):
     第1轮 User: 提出在重大活动/高密现场开通保障，明确说出应用、业务、原定起止时间、画质与时延要求；
     第1轮 Agent: 调取 ReasoningBank 经验（如提前30分钟预热试机），主动推算提前起保时间并询问是否采纳；
     第2轮 User: 表达疑虑询问预热试机细节；
     第2轮 Agent: 解释预留30分钟试机可确保开场推流平稳流畅；
     第3轮 User: 采纳专家建议同意开通；
     第3轮 Agent: 确认方案并开通。
   - 若 rounds == 2 (常规主动提议):
     第1轮 User: 提出重大活动/高密现场保障，一次性说清应用、业务、原定起止时间、画质与时延；
     第1轮 Agent: 调取经验卡片，主动将起保时间提前30分钟（时长相应扩充30分钟）向用户反问确认；
     第2轮 User: 采纳建议（如“好的，提前半小时试机预热太重要了，按这个开通！”）；
     第2轮 Agent: 确认按优化方案开通并祝福收尾。
11. 经验记忆 ReasoningBank 经验回溯与时序重叠仲裁 (empirical_recall / overlapping_resolution, T2-10) (rounds == 2):
   - 第1轮 User: 一次性说清本次紧急保障的应用、业务、起止时间（含时长）、画质与时延，并提及与既有在保意图保障单时段重叠冲突（或调取既往避坑经验）；
   - 第1轮 Agent: 调取经验卡片，执行时钟让路仲裁（新意图保障单在交界点无缝接续起保、时长相应缩减重算），向用户反问确认；
   - 第2轮 User: 确认开通；
   - 第2轮 Agent: 确认受理并收尾。

【输出严格 JSON 格式】:
{
  "sessions": [
    {
      "session_id": "会话ID",
      "turns": [
        {
          "turn": 1,
          "user_utterance": "用户第一句台词...",
          "user_action_types": ["Create_Intent_Request", "Inform_Slot"],
          "agent_utterance": "客服第一句回复...",
          "agent_action_types": ["Request_Slot"]
        }
      ]
    }
  ]
}"""

SINGLE_DIALOGUE_RULES_TEMPLATE = """【核心会话轮次与动作规则（严格遵守）】:
0. 用户台词口语别名与大/小记忆点分级规则（强制遵守）:
   - 【证据会话（evidence_session）】:
     * 第1轮 User：必须使用清晰、标准、无歧义的官方应用名与业务名（如“{app_name}”、“{srv_name}”），可提开始时间，【严禁在第1轮提及结束时间或持续时长，严禁在第1轮使用生僻别名，严禁使用'老规矩'、'老时间'等未生效的个性化表达】！
     * 第1轮 Agent：识别并确认应用与业务，仅针对未提及的画质（resolution）、时延（rtt）、持续时长（duration）进行细节追问；
     * 第2轮 User：补充本次参数。隐式归纳首次证据不得登记小记忆点；显式声明只登记 s_plan.small_memory 指定的一项，并使用对应类型的声明句式。
   - 【后续复用与强化会话（reinforcement_session / reuse_session）】:
     * 第1轮应用与业务是最小表达：无业务默认应用记忆时必须同时说出应用和业务；有应用别名时可用别名替代应用名，但仍须说业务；只有对应主线已有业务默认应用时才可只说业务。画质、时延、时长和个性化周期表达只能补全各自槽位，不能省略应用/业务或指代整套配置。Agent 展开完整配置后反问确认。
   - 【参数别名一致性与对齐律（Parameter Alias Alignment Law）】:
     * 凡在任何会话中涉及画质或时延的具体称谓，必须与数值档位真实严谨对齐：1080p 只能称为“1080p”、“1080p原画”或“超清”，严禁“顶格清晰度”；50ms 只能称为“50ms以内”、“50毫秒以内”或“低时延”，严禁“零卡顿”；整条时间线各会话称谓全局统一对齐！
1. 最后一轮必须由 Agent 的答复结束！
   - 常规会话最后一轮 Agent agent_action_types 必须包含 "Acknowledge"；
   - T1-2 纯域外拒绝会话 (rounds == 1): Agent 必须礼貌拒绝，agent_action_types 必须为 ["Reject_Request"]；
   - X-1 混合诉求会话 (rounds == 1): Agent 办理保障同时拒绝域外诉求，agent_action_types 必须为 ["Acknowledge", "Reject_Request"]；
   - T3-1/T2-2 参数澄清与歧义消解会话 (rounds == 3 为 T3-1 跨轮澄清，rounds == 2 为 T2-2): 第1轮用户必须说出官方应用与业务，Agent 只追问缺失参数（["Request_Slot"]）；若 small_memory_evidence_mode 为 cross_turn_clarification，第2轮用户只说模糊表达，Agent 开放式追问具体标准值，不得先给候选答案（["Request_Disambiguation"]）；第3轮用户亲口给出标准值并确认长期含义，Agent 才开通并记录；支线不得登记 service_default_app；
   - T2-5 时长延长会话 (rounds == 3): 第1轮 Agent 确认老规矩基线配置（["Confirm_Slot"]），第2轮用户提出延长时长（user_action_types 包含 ["Confirm_Slot", "Modify_Request"]），第2轮 Agent 更新时长并请用户最终确认（["Confirm_Slot"]），第3轮用户确认（["Confirm_Slot"]），Agent 确认延长并生效（["Acknowledge"]）。
2. 首次建联/证据会话 (evidence_session):
   - 若 declaration_mode == "explicit_declaration" (显式声明):
     第1轮 User: 明确提出需要保障的标准应用与业务（可提开始时间，严禁结束时间/时长，严禁别名，严禁'老规矩'）；Agent 确认应用/业务并追问画质、时延、时长细节。
     第2轮 User: 明确说清画质、时延与持续时长参数，并【明确显式声明长期习惯与个性化表达/触发条件，顺理成章引入个性化代称】。
       【非常关键：用户绝不会在日常口语中使用“长期偏好”、“元指令”等系统技术术语！严禁在台词中出现“长期偏好”！真实用户只会说：“记住这个习惯或者规矩哈”、“帮我把这个习惯记一下，以后省得每次重新挑”、“把这个规矩记住，以后照旧就行”】:
       * 若 storyline_trigger_type == "time_periodic" 且 period_type == "daily": 如"以后我只要每天这个时段说'老规矩'，就按这个来：{app_name}、{resolution}、{rtt}以内，记住这个习惯哈，别掉链子"；
       * 若 storyline_trigger_type == "time_periodic" 且 period_type == "weekly": 如"以后我只要在每周例行时段说'老规矩'，就按这个来：{app_name}、{resolution}、{rtt}以内，记住这个习惯哈，别掉链子"；
       * 若 storyline_trigger_type == "time_periodic" 且 period_type == "monthly": 如"以后我只要在每月月初/固定月度对账说'老规矩'，就按这个来：{app_name}、{resolution}、{rtt}以内，把这个规矩记一下哈，别掉链子"；
       * 若 storyline_trigger_type == "task_activity": 如"以后只要我提到执行【{trigger_task}】现场，老规矩就按这个来：{app_name}、{resolution}、{rtt}以内，帮我把这个习惯记好，别掉链子"；
       * 若 storyline_trigger_type == "location_environment": 如"以后只要我身处【{trigger_loc}】，老规矩就按这个来：{app_name}、{resolution}、{rtt}以内，帮我把这个习惯记好，别掉链子"；
     Agent 必须明确闭环回复：“好的，已为您开通本次保障，并已为您将该配置记录为长期老规矩！”
   - 若 declaration_mode == "implicit_induction" (隐式归纳):
     第1轮 User: 仅针对本次单次保障需求提出申请，必须使用标准应用与业务（可提开始时间，严禁结束时间/时长），【严禁出现任何‘记一下/以后都按这个/老规矩’等元指令词】（如：“今天执行任务/在该地点，我要用{app_name}{srv_name}，帮我开个保障...”）；Agent 追问清晰度、时延与持续时长细节。
     第2轮 User: 仅确认本次单次任务参数（画质、时延与持续时长，如：“好的，画质{resolution}、时延{rtt}，持续{duration}，今天就按这个配置开通”）；Agent 确认受理单次任务结束，不擅自假设长期习惯。
3. 记忆强化/复用 (reinforcement / reuse):
   - 若上方记忆快照包含 [provisional] (隐式偏好二次发生，触发固化契机):
     第1轮 User: 再次在相似触发场景下提出需求（如：“今天又来执行XX任务了/又到这个地点了，跟上次一样就行”）。【严禁在第1轮使用'老规矩'与生僻别名】！
     第1轮 Agent: 只能把 provisional 记录作为历史候选（history_filled），不能当作 active 记忆（memory_filled）直接使用。必须说明“查到上次记录”，并完整复述“{app_name}{srv_name}、{resolution}、时延{rtt}以内、持续{duration}、本次{start_ts}至{end_ts}”，再询问是否按这套配置开通并设为长期老规矩；不得声称用户此前“多次使用”。（agent_action_types包含 "Confirm_Slot"）。
     第2轮 User: 明确确认固化，并按 s_plan.small_memory 在此刻登记指定的一项小记忆；service_default_app 应说“以后只说该业务且没指定应用时，默认用当前应用”。（user_action_types包含 "Confirm_Slot"）。
     第2轮 Agent: 答复已开通并收尾祝福，正式记录老规矩与代称（agent_action_types: ["Acknowledge"]）。
   - 若上方记忆快照包含 [active] (常规复用已生效记忆):
     第1轮 User: 口语化提出需求，提及触发场景、应用与业务（应用＋业务是发起保障意图的最小表达，严禁只说‘老规矩开保障’），并【必须省略画质与时延等参数】（如使用"老规矩"、"照上次的来"等）。
     第1轮 Agent: 必须明确调取上方 active_memory 中的配置，结合触发条件主动反问向用户确认（agent_action_types包含 "Confirm_Slot"）。
     第2轮 User: 明确确认 Agent 提出的配置（user_action_types包含 "Confirm_Slot"，如"对，开通吧"）。
     第2轮 Agent: 明确确认已开通并收尾祝福（agent_action_types: ["Acknowledge"]）。
4. 纠正覆盖与临时调整 (correction / event_override, T2-3):
   - 第1轮 User: 必须严格满足“场景＋应用＋业务”的最小表达，提及当前所在现场场景（如“今天在【{env}】”）以及老规矩需求（明确说出应用与业务，若有个性化周期表达可加上个性化周期表达），【严禁只说‘老规矩开保障’或只带个性化周期表达而不说应用和业务】！
   - 第1轮 Agent: 调取原有的长期老规矩基线配置（如 1080p、50ms以内），结合起止时段向用户反问确认；
   - 第2轮 User: 明确说明现场特殊原因（如人流密集、网络拥塞、恶劣环境），提出本次临时调整参数（如画质临时调到 720p、时延压到 30ms），明确表示“今天现场特殊，临时按这个来”；
   - 第2轮 Agent: 汇总本次临时调整后的参数配置向用户发起最终确认（["Confirm_Slot"]）；
   - 第3轮 User: 明确确认按临时配置开通（["Confirm_Slot"]），第3轮 Agent 确认本次单次临时调整并正式开通（["Acknowledge"]）。
5. 单轮干扰项 (distractor):
   - T1-1 单轮单次任务 (rounds == 1): 无任何先验记忆！用户在第 1 轮必须一次性清晰、完整说清全部参数需求（应用、业务、时段、画质、时延，如'画质{resolution}，时延控制在{rtt}以内'），【严禁使用‘清晰点就行’、‘不卡就行’、‘老规矩’等任何未建立的个性化记忆表达或模糊词】！Agent 直接受理开通闭环，严禁出现‘按记忆理解’等说辞；
   - T1-2 纯域外拒绝：用户提出域外需求，Agent 礼貌拒绝；
   - X-1 混合诉求（一办一拒）：用户无先验记忆，首次提出标准保障需求并附带域外需求，严禁使用未建立的个性化表达或老规矩；Agent 办理保障并明确拒绝域外需求。

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
}}"""

PERSONA_SKELETON_CONSTRAINTS_TEMPLATE = """【本次画像强制约束（严格遵守）】:
1. declaration_mode 必须设为: "{forced_decl_mode}"
2. storyline_trigger_type 必须设为: "{forced_trig_type}"（{trig_instruction}）
3. 涉及的应用必须使用标准中文名（如：微信、抖音、快手、腾讯会议、钉钉、飞书、哔哩哔哩、小红书等）。
4. 支持的标准业务仅限：开直播、看直播、视频通话、会议、短视频、游戏、云游戏。
5. 必须明确解耦出：
   - periodic_main_storyline (核心主线记忆): 该职业核心高频活动，指定APP、业务、分辨率、时延上限、以及【6大参数与周期的多样化口语别名映射】:
     * storyline_trigger_type: "{forced_trig_type}"
     * trigger_condition: 结合职业定制的触发条件
     * declaration_mode: "{forced_decl_mode}"
     * period_type: "{period_type_hint}"（可为 daily / weekly / monthly）
     * days: {days_repr}
     * time_range: "{time_range_hint}"
     * aliases: 必须包含全部6大维度口语别名（切忌空缺，且必须与具体参数档位精准对齐，严禁失真与冲突）：
       - app_aliases: 该应用的口语别名（如阿抖、某手、企微、小破站、微信、企鹅会议等）
       - service_aliases: 该业务的行话口语（如推流、开播、打视讯、连麦、对齐开会、刷短视频等）
       - resolution_aliases: 画质口语叫法（必须严格对应具体档位数值！若为1080p只能叫'1080p原画'、'1080p'、'超清'，严禁使用误导为2K/4K的'顶格清晰度'或'最高画质'；若为720p叫'720p'、'高清'）
       - rtt_aliases: 时延口语叫法（必须客观对应具体时延档位！如'50ms以内'、'50毫秒以内'、'低时延'，严禁使用夸大失真的'零卡顿'或'秒开'）
       - duration_aliases: 时长口语叫法（如俩小时、两钟头、播到四点、一个半小时等）
       - period_aliases: 周期/触发口语叫法（如每天这个时候、老时间、晚间例行、每周一五老规矩、月初例会等）
   - scenario_events (场景化事件驱动记忆): 1个具有代表性的突发/阶段性事件（如促销展会、赛事周、跨城出差季），具有起止日期（在2026年10月-11月之间）、特定环境、以及对主线参数的临时纠正值。
   - sub_storylines (支线记忆): 2条次频非主线业务（如大巴视频调度、录像复盘、客户沟通等），包含触发条件、APP、业务、偏好参数。
   - distractor_pool (干扰项): 2个单次无关业务（如会议、刷短视频、看直播等），说明场景与参数。
   - speech_style: 人物的语体风格、口头禅（如"老规矩"、"别掉链子"、"对齐一下"等）。"""

PERSONA_SKELETON_SCHEMA_TEMPLATE = """【严格输出 JSON 格式（不得输出多余解释）】:
{{
  "persona_id": "{persona_id}",
  "category": "{category}",
  "persona_summary": "{persona_summary}",
  "static_profile": {{
    "user_id": "{user_id}",
    "identity": "详细的职业与活动描述...",
    "devices": "主力设备与辅助设备...",
    "apps": ["常用APP1", "常用APP2", "常用APP3", "常用APP4"],
    "speech_archetype": "语体类型代码(如 athlete_speaker / business_advisor / outdoor_streamer 等)",
    "speech_style": {{
      "tone": "说话口吻描述",
      "catchphrases": ["口头禅1", "口头禅2", "口头禅3"],
      "typical_habits": "典型的说话动机与习惯"
    }}
  }},
  "dynamic_profile": {{
    "periodic_main_storyline": {{
      "storyline_id": "MAIN_MT_01",
      "name": "主线业务名称",
      "storyline_trigger_type": "{forced_trig_type}",
      "trigger_condition": "根据上述约束生成的具体触发条件描述",
      "period_type": "{period_type_hint}",
      "days": {days_repr},
      "time_range": "{time_range_hint}",
      "application_name": "标准APP名",
      "service_name": "标准业务名",
      "preferred_params": {{
        "resolution": "根据业务场景从支持列表中灵活选择(如 1080p / 720p / 2160p / 540p / 360p，不要千篇一律填1080p)",
        "rtt_max": "根据业务场景灵活选择(如 20ms / 30ms / 50ms / 80ms / 100ms，不要千篇一律填50ms)"
      }},
      "aliases": {{
        "app_aliases": ["应用口语别名1", "应用口语别名2"],
        "service_aliases": ["业务口语别名1", "业务口语别名2"],
        "resolution_aliases": ["画质口语表达1", "画质口语表达2"],
        "rtt_aliases": ["时延口语表达1", "时延口语表达2"],
        "duration_aliases": ["时长口语表达1", "时长口语表达2"],
        "period_aliases": ["周期触发口语表达1", "周期触发口语表达2"]
      }},
      "declaration_mode": "{forced_decl_mode}",
      "evidence_pattern": "{evidence_pattern}"
    }},
    "scenario_events": [
      {{
        "event_id": "EVT_2026_01",
        "name": "突发或阶段性事件名称",
        "start_time": "2026年11月01日00时00分",
        "end_time": "2026年11月10日23时59分",
        "scene_description": "该事件期间的特殊现场网络环境描述",
        "preference_override": {{
          "resolution": "720p",
          "rtt_max": "30ms"
        }}
      }}
    ],
    "sub_storylines": [
      {{
        "storyline_id": "SUB_01",
        "name": "支线1名称",
        "application_name": "标准APP名",
        "service_name": "标准业务名",
        "preferred_params": {{
          "resolution": "720p",
          "rtt_max": "100ms"
        }},
        "trigger_condition": "支线1触发场景"
      }},
      {{
        "storyline_id": "SUB_02",
        "name": "支线2名称",
        "application_name": "标准APP名",
        "service_name": "标准业务名",
        "preferred_params": {{
          "resolution": "1080p",
          "rtt_max": "80ms"
        }},
        "trigger_condition": "支线2触发场景"
      }}
    ],
    "distractor_pool": [
      {{
        "distractor_id": "DIST_01",
        "scenario": "单次任务场景",
        "application_name": "标准APP名",
        "service_name": "标准业务名",
        "params": {{
          "resolution": "720p",
          "rtt_max": "80ms"
        }}
      }},
      {{
        "distractor_id": "DIST_02",
        "scenario": "单次任务场景",
        "application_name": "标准APP名",
        "service_name": "标准业务名",
        "params": {{
          "resolution": "720p",
          "rtt_max": "80ms"
        }}
      }}
    ]
  }}
}}"""

BASE_CANONICAL_PAIRS: list[tuple[str, str]] = [
    ("抖音", "开直播"),
    ("微信", "视频通话"),
    ("腾讯会议", "会议"),
    ("快手", "开直播"),
    ("钉钉", "会议"),
    ("哔哩哔哩", "开直播"),
    ("飞书", "会议"),
    ("小红书", "开直播"),
    ("抖音", "短视频"),
    ("快手", "短视频"),
    ("腾讯视频", "视频"),
    ("哔哩哔哩", "视频"),
    ("咪咕快游", "云游戏"),
    ("斗鱼直播", "开直播"),
    ("快手", "看直播"),
]

INVALID_APP_SERVICE_MAP: dict[tuple[str, str], tuple[str, str]] = {
    ("高德地图", "视频通话"): ("微信", "视频通话"),
    ("钉钉", "视频通话"): ("钉钉", "会议"),
    ("微信", "会议"): ("钉钉", "会议"),
    ("腾讯会议", "视频通话"): ("腾讯会议", "会议"),
    ("哔哩哔哩", "短视频"): ("抖音", "短视频"),
    ("快手", "游戏"): ("快手", "看直播"),
    ("虎牙直播", "看直播"): ("快手", "看直播"),
    ("虎牙直播", "开直播"): ("斗鱼直播", "开直播"),
}

DEFAULT_DURATION_ALIAS_MAP: dict[str, list[str]] = {
    "30min": ["半小时", "半个钟头", "30分钟"],
    "45min": ["45分钟", "三刻钟"],
    "60min": ["一个钟头", "一小时", "60分钟"],
    "90min": ["一个半小时", "一个半钟头", "90分钟"],
    "120min": ["俩小时", "两钟头", "两小时"],
    "150min": ["两个半小时", "150分钟"],
    "180min": ["三个小时", "三钟头", "180分钟"],
}
