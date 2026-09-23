import json
from src.config import Config
from src.llm_client import LLMClient

class PersonaGenerator:
    """
    调用 DeepSeek API 将任意原始画像自动扩充为标准的【解耦画像骨架】。
    """
    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm_client or LLMClient()
        self.valid_apps = list(Config.app_map.keys())
        self.support_matrix = Config.support_matrix

    def generate_skeleton(self, raw_persona: dict) -> dict:
        import re
        num_match = re.search(r'\d+', raw_persona.get("persona_id", ""))
        uid_num = int(num_match.group()) if num_match else 1
        forced_decl_mode = "explicit_declaration" if (uid_num % 2 == 1) else "implicit_induction"
        trig_mod = uid_num % 3
        if trig_mod == 1:
            forced_trig_type = "time_periodic"
            trig_instruction = "周期时间驱动：设定每周固定周期频次（如每周三周六下午），trigger_condition 必须为明确的周期时间描述（如'每周三周六下午常规业务'）"
        elif trig_mod == 2:
            forced_trig_type = "task_activity"
            trig_instruction = "任务现场驱动：因特定专业活动/现场任务触发（如'客户现场审计'、'婚庆跟拍'、'电力设备巡检'），trigger_condition 必须为执行该特定任务（如'执行客户现场合规审计任务'）"
        else:
            forced_trig_type = "location_environment"
            trig_instruction = "特定地点驱动：因特定物理空间/环境触发（如'利兹露天集结区'、'地下配电室'、'跨城物流中转站'），trigger_condition 必须为身处该特定空间（如'身处露天集结区弱网区域'）"

        prompt = f"""你是一个核心网通信与长程记忆专家。请将以下粗粒度的人物网络画像，扩充为结构化的【解耦画像骨架】。

【输入原始画像】:
{json.dumps(raw_persona, ensure_ascii=False, indent=2)}

【本次画像强制约束（严格遵守）】:
1. declaration_mode 必须设为: "{forced_decl_mode}"
2. storyline_trigger_type 必须设为: "{forced_trig_type}"（{trig_instruction}）
3. 涉及的应用必须使用标准中文名（如：微信、抖音、快手、腾讯会议、钉钉、飞书、哔哩哔哩、小红书等）。
4. 支持的标准业务仅限：开直播、看直播、视频通话、会议、短视频、游戏、云游戏。
5. 必须明确解耦出：
   - periodic_main_storyline (核心主线记忆): 该职业核心高频活动，指定APP、业务、分辨率、时延上限、口语别名及模糊词映射，以及：
     * storyline_trigger_type: "{forced_trig_type}"
     * trigger_condition: 结合职业定制的触发条件
     * declaration_mode: "{forced_decl_mode}"
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
      "period_type": "weekly",
      "days": ["Wednesday", "Saturday"],
      "time_range": "14:00-17:00",
      "application_name": "标准APP名",
      "service_name": "标准业务名",
      "preferred_params": {{
        "resolution": "1080p",
        "rtt_max": "50ms"
      }},
      "aliases": {{
        "app_aliases": ["别名1", "别名2"],
        "service_aliases": ["业务口语1", "业务口语2"]
      }},
      "param_mappings": {{
        "resolution": {{"高清": "1080p", "清晰点": "1080p"}},
        "rtt": {{"低时延": "50ms", "别卡": "50ms"}}
      }},
      "declaration_mode": "{forced_decl_mode}",
      "evidence_level": "explicit_long_term_declaration"
    }},
    "scenario_events": [
      {{
        "event_id": "EVT_01",
        "event_name": "事件名称",
        "valid_from": "2026-11-01",
        "valid_to": "2026-11-15",
        "impact_scope": "temporary",
        "scene_description": "特定场景网络环境...",
        "preference_override": {{
          "resolution": "720p",
          "rtt_max": "30ms"
        }},
        "trigger_reason": "为什么改变参数..."
      }}
    ],
    "sub_storylines": [
      {{
        "sub_id": "SUB_MT_01",
        "name": "支线1名称",
        "period_type": "weekly_evening",
        "days": ["Sunday", "Wednesday"],
        "trigger_condition": "触发条件描述",
        "application_name": "标准APP名",
        "service_name": "标准业务名",
        "preferred_params": {{
          "resolution": "720p",
          "rtt_max": "100ms"
        }},
        "aliases": {{
          "app_aliases": ["别名"],
          "service_aliases": ["业务代称"]
        }},
        "param_mappings": {{
          "resolution": {{"标清": "720p"}},
          "rtt": {{"能听清就行": "100ms"}}
        }}
      }},
      {{
        "sub_id": "SUB_MT_02",
        "name": "支线2名称",
        "period_type": "sporadic_evening",
        "trigger_condition": "触发条件描述",
        "application_name": "标准APP名",
        "service_name": "标准业务名",
        "preferred_params": {{
          "resolution": "1080p",
          "rtt_max": "80ms"
        }},
        "aliases": {{
          "app_aliases": ["别名"],
          "service_aliases": ["业务代称"]
        }},
        "param_mappings": {{
          "resolution": {{"超清": "1080p"}},
          "rtt": {{"不卡": "80ms"}}
        }}
      }}
    ],
    "distractor_pool": [
      {{
        "distractor_id": "DIST_01",
        "name": "干扰项1",
        "application_name": "标准APP名",
        "service_name": "标准业务名",
        "scenario_description": "场景说明",
        "params": {{
          "resolution": "720p",
          "rtt_max": "80ms"
        }}
      }},
      {{
        "distractor_id": "DIST_02",
        "name": "干扰项2",
        "application_name": "标准APP名",
        "service_name": "标准业务名",
        "scenario_description": "场景说明",
        "params": {{
          "resolution": "720p",
          "rtt_max": "80ms"
        }}
      }}
    ]
  }}
}}
"""
        messages = [
            {"role": "system", "content": "You are a professional dataset engineer for network agent memory systems."},
            {"role": "user", "content": prompt}
        ]
        return self.llm.chat_json(messages)
