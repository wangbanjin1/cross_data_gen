import json

def build_persona_skeleton_prompt(
    raw_persona: dict,
    forced_decl_mode: str,
    forced_trig_type: str,
    trig_instruction: str,
    period_type_hint: str = "weekly",
    days_hint: list = None,
    time_range_hint: str = "14:00-16:00"
) -> str:
    """
    构建用于将原始画像扩充为解耦画像骨架的 Prompt。
    支持日级/周级/月级多粒度周期与6大核心参数口语别名配置。
    """
    days_repr = json.dumps(days_hint or ["Monday", "Friday"], ensure_ascii=False)
    return f"""你是一个核心网通信与长程记忆专家。请将以下粗粒度的人物网络画像，扩充为结构化的【解耦画像骨架】。

【输入原始画像】:
{json.dumps(raw_persona, ensure_ascii=False, indent=2)}

【本次画像强制约束（严格遵守）】:
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
     * aliases: 必须包含全部6大维度口语别名（切忌空缺）：
       - app_aliases: 该应用的口语别名（如阿抖、某手、企微、小破站、微信、企鹅会议等）
       - service_aliases: 该业务的行话口语（如推流、开播、打视讯、连麦、对齐开会、刷短视频等）
       - resolution_aliases: 画质口语叫法（如原画、顶格清晰度、千万别糊、超清、蓝光、凑合能看等）
       - rtt_aliases: 时延口语叫法（如别掉链子、零卡顿、极速响应、秒开、毫秒级、别转圈等）
       - duration_aliases: 时长口语叫法（如俩小时、两钟头、播到四点、一个半小时、大半个下午等）
       - period_aliases: 周期/触发口语叫法（如每天这个时候、老时间、晚间例行、每周一五老规矩、月初例会等）
   - scenario_events (场景化事件驱动记忆): 1个具有代表性的突发/阶段性事件（如促销展会、赛事周、跨城出差季），具有起止日期（在2026年10月-11月之间）、特定环境、以及对主线参数的临时纠正值。
   - sub_storylines (支线记忆): 2条次频非主线业务（如大巴视频调度、录像复盘、客户沟通等），包含触发条件、APP、业务、偏好参数。
   - distractor_pool (干扰项): 2个单次无关业务（如会议、刷短视频、看直播等），说明场景与参数。
   - speech_style: 人物的语体风格、口头禅（如"老规矩"、"别掉链子"、"对齐一下"等）。

【严格输出 JSON 格式（不得输出多余解释）】:
{{
  "persona_id": "{raw_persona.get('persona_id')}",
  "category": "{raw_persona.get('category')}",
  "persona_summary": "{raw_persona.get('persona_summary')}",
  "static_profile": {{
    "user_id": "USER_{raw_persona.get('persona_id').split('_')[-1]}",
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
        "resolution": "1080p",
        "rtt_max": "50ms"
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
      "evidence_pattern": "显式口述固定偏好" if forced_decl_mode == "explicit_declaration" else "隐式单次保障并随后固化"
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
}}
"""
