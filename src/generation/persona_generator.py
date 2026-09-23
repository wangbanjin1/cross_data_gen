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
            grain_idx = (uid_num // 3) % 3
            if grain_idx == 0:
                # 日级周期 (daily)
                daily_slots = [
                    ("08:30-10:00", "每天早高峰通勤与晨间例行业务"),
                    ("12:30-13:30", "每天午间休息与午间复盘业务"),
                    ("20:00-22:00", "每天晚间黄金档高频业务"),
                    ("19:00-21:00", "每天傍晚黄金档例行业务"),
                    ("23:00-00:30", "每天深夜巡检与连线业务")
                ]
                time_range_hint, trig_desc_example = daily_slots[uid_num % len(daily_slots)]
                period_type_hint = "daily"
                days_hint = ["daily"]
                trig_instruction = f"周期时间驱动【daily日级周期】：设定每天固定时段的高频业务（如{time_range_hint}，{trig_desc_example}），period_type必须为'daily'，days设为['daily']，time_range设为'{time_range_hint}'，trigger_condition设为明确的日周期描述（如'{trig_desc_example}'）"
            elif grain_idx == 1:
                # 周级周期 (weekly 多样化组合，坚决破除单一周三周六)
                weekly_combos = [
                    (["Monday", "Friday"], "09:30-11:30", "每周一与周五例会与业务对齐"),
                    (["Tuesday", "Thursday"], "14:00-16:00", "每周二与周四常规专业培训/研讨"),
                    (["Saturday", "Sunday"], "15:00-17:00", "每周六与周日周末赛事专场/排位"),
                    (["Wednesday", "Friday"], "19:00-21:00", "每周三与周五晚间对账与复盘"),
                    (["Tuesday", "Saturday"], "20:00-22:00", "每周二与周六晚间行业直播"),
                    (["Monday", "Wednesday", "Friday"], "10:00-12:00", "工作日一三五常规业务例会")
                ]
                days_hint, time_range_hint, trig_desc_example = weekly_combos[uid_num % len(weekly_combos)]
                period_type_hint = "weekly"
                trig_instruction = f"周期时间驱动【weekly周级周期】：设定每周固定周几频次的高频业务，必须多样化，严禁单一重复（已指定周组合：{days_hint}，时段：{time_range_hint}），period_type必须为'weekly'，days设为{days_hint}，time_range设为'{time_range_hint}'，trigger_condition设为明确的周周期描述（如'{trig_desc_example}'）"
            else:
                # 月级周期 (monthly)
                monthly_combos = [
                    (["1st", "2nd"], "09:00-11:00", "每月月初1-2号例行开门红与月度动员会"),
                    (["15th", "16th"], "14:00-16:00", "每月月中15-16号例行综合对账与业务巡检"),
                    (["28th", "29th"], "20:00-22:00", "每月月末28-29号例行封账冲刺与月度大复盘")
                ]
                days_hint, time_range_hint, trig_desc_example = monthly_combos[uid_num % len(monthly_combos)]
                period_type_hint = "monthly"
                trig_instruction = f"周期时间驱动【monthly月级周期】：设定每月特定日期的月度高频业务（已指定月度日期：{days_hint}，时段：{time_range_hint}），period_type必须为'monthly'，days设为{days_hint}，time_range设为'{time_range_hint}'，trigger_condition设为明确的月周期描述（如'{trig_desc_example}'）"
        elif trig_mod == 2:
            forced_trig_type = "task_activity"
            period_type_hint = "task_driven"
            days_hint = ["task_specific"]
            time_range_hint = "14:00-16:00"
            trig_instruction = "任务现场驱动：因特定专业活动/现场任务触发（如'客户现场审计'、'婚庆跟拍'、'电力设备巡检'、'医疗会诊'等），trigger_condition 必须为执行该特定任务（如'执行客户现场合规审计任务'）"
        else:
            forced_trig_type = "location_environment"
            period_type_hint = "location_driven"
            days_hint = ["location_specific"]
            time_range_hint = "15:00-17:00"
            trig_instruction = "特定地点驱动：因特定物理空间/环境触发（如'利兹露天集结区'、'地下配电室'、'跨城物流中转站'、'高铁沿线弱网区'），trigger_condition 必须为身处该特定空间（如'身处露天集结区弱网区域'）"

        prompt = build_persona_skeleton_prompt(
            raw_persona=raw_persona,
            forced_decl_mode=forced_decl_mode,
            forced_trig_type=forced_trig_type,
            trig_instruction=trig_instruction,
            period_type_hint=period_type_hint,
            days_hint=days_hint,
            time_range_hint=time_range_hint
        )

        messages = [
            {"role": "system", "content": "You are a professional dataset engineer for network agent memory systems."},
            {"role": "user", "content": prompt}
        ]
        res = self.llm.chat_json(messages)
        return self._enrich_skeleton(res)

    def _enrich_skeleton(self, sk: dict) -> dict:
        """
        后置校验并补齐 6 大维度口语别名，确保每一个画像骨架都具备高质量行话库。
        """
        if not isinstance(sk, dict) or "dynamic_profile" not in sk:
            return sk

        expr_vault = getattr(Config, "expression_vault", {})
        synonyms = expr_vault.get("slot_synonyms", {})
        app_map = getattr(Config, "app_map", {})

        main_mt = sk["dynamic_profile"].get("periodic_main_storyline", {})
        app = main_mt.get("application_name", "抖音")
        srv = main_mt.get("service_name", "开直播")
        res = main_mt.get("preferred_params", {}).get("resolution", "1080p")
        rtt = main_mt.get("preferred_params", {}).get("rtt_max", "50ms")
        p_type = main_mt.get("period_type", "weekly")

        aliases = main_mt.get("aliases", {})
        if not isinstance(aliases, dict):
            aliases = {}

        # 1. 补齐 app_aliases (优先选择地道中文叫法)
        if not aliases.get("app_aliases"):
            app_aliases_found = []
            for k, val_list in app_map.items():
                if app in val_list:
                    cn_aliases = [a for a in val_list if a != app and re.search(r'[\u4e00-\u9fa5]', a)]
                    other_aliases = [a for a in val_list if a != app and a not in cn_aliases]
                    app_aliases_found = cn_aliases + other_aliases
                    break
            aliases["app_aliases"] = app_aliases_found[:3] if app_aliases_found else [app]

        # 2. 补齐 service_aliases
        if not aliases.get("service_aliases"):
            srv_syns = synonyms.get("services", {}).get(srv, {}).get("general_aliases", [])
            aliases["service_aliases"] = [s for s in srv_syns if s != srv][:3] if srv_syns else [srv]

        # 3. 补齐 resolution_aliases
        if not aliases.get("resolution_aliases"):
            res_syns = synonyms.get("resolution", {}).get(res, {}).get("good_expressions", [])
            aliases["resolution_aliases"] = res_syns[:3] if res_syns else ["高清", "原画", "顶格画质"]

        # 4. 补齐 rtt_aliases
        if not aliases.get("rtt_aliases"):
            rtt_syns = synonyms.get("rtt", {}).get(rtt, {}).get("good_expressions", [])
            aliases["rtt_aliases"] = rtt_syns[:3] if rtt_syns else ["别掉链子", "零卡顿", "极速响应"]

        # 5. 补齐 duration_aliases
        if not aliases.get("duration_aliases"):
            dur_syns = synonyms.get("duration", {}).get("120min", [])
            aliases["duration_aliases"] = (dur_syns + ["俩小时", "两钟头"])[:4] if dur_syns else ["俩小时", "两钟头", "两小时"]

        # 6. 补齐 period_aliases
        if not aliases.get("period_aliases"):
            if p_type == "daily":
                aliases["period_aliases"] = ["每天这个时候", "老时间", "日常例行", "每天照旧", "每天这个点"]
            elif p_type == "weekly":
                aliases["period_aliases"] = ["每周老时间", "周例行时段", "照上周的来", "每周固定这个时候"]
            elif p_type == "monthly":
                aliases["period_aliases"] = ["月初例行", "每月老时间", "月度固定配置", "照旧按月度标准"]
            else:
                aliases["period_aliases"] = ["老规矩", "老时间", "按习惯来", "照旧"]

        main_mt["aliases"] = aliases
        sk["dynamic_profile"]["periodic_main_storyline"] = main_mt

        # 同样补齐 sub_storylines
        for sub in sk["dynamic_profile"].get("sub_storylines", []):
            s_app = sub.get("application_name", "")
            s_srv = sub.get("service_name", "")
            s_aliases = sub.get("aliases", {})
            if not isinstance(s_aliases, dict):
                s_aliases = {}
            if not s_aliases.get("app_aliases"):
                s_app_syns = []
                for k, vlist in app_map.items():
                    if s_app in vlist:
                        s_app_syns = [a for a in vlist if a != s_app]
                        break
                s_aliases["app_aliases"] = s_app_syns[:2] if s_app_syns else [s_app]
            if not s_aliases.get("service_aliases"):
                s_srv_syns = synonyms.get("services", {}).get(s_srv, {}).get("general_aliases", [])
                s_aliases["service_aliases"] = [s for s in s_srv_syns if s != s_srv][:2] if s_srv_syns else [s_srv]
            sub["aliases"] = s_aliases

        return sk
