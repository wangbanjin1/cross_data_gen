import re
from src.config.settings import Config
from src.generation.llm_client import LLMClient
from src.templates.prompts.persona_prompts import build_persona_skeleton_prompt

class PersonaGenerator:
    """
    画像骨架生成器 (PersonaGenerator)
    负责调用 DeepSeek API 将粗粒度原始画像扩充为标准的解耦画像骨架 (Persona Skeleton)。
    """

    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm_client or LLMClient()
        self.valid_apps = list(getattr(Config, "app_map", {}).keys())
        self.support_matrix = getattr(Config, "support_matrix", {})

    def generate_skeleton(self, raw_persona: dict) -> dict:
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

        prompt = build_persona_skeleton_prompt(
            raw_persona=raw_persona,
            forced_decl_mode=forced_decl_mode,
            forced_trig_type=forced_trig_type,
            trig_instruction=trig_instruction
        )

        messages = [
            {"role": "system", "content": "You are a professional dataset engineer for network agent memory systems."},
            {"role": "user", "content": prompt}
        ]
        return self.llm.chat_json(messages)
