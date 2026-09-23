"""
触发规则与周期偏好预设管理模块 (TriggerPresetManager)
从外部配置文件 data/whitelist/trigger_presets.json 动态加载周期槽位 (daily)、周组合 (weekly)、
月度节点 (monthly)、现场任务预设 (task_activity) 与物理地点预设 (location_environment)，
实现配置与代码的完全解耦，用户可随时向 JSON 文件直接增添自定义规则。
"""

import json
from pathlib import Path
from src.config.settings import Config

class TriggerPresetManager:
    """
    触发预设管理器
    负责解析与分发各维度的长程记忆触发类型、周期排期与提示词约束。
    """
    _cached_presets = None

    @classmethod
    def get_presets(cls) -> dict:
        if cls._cached_presets is not None:
            return cls._cached_presets

        # 优先从 Config 获取
        presets = getattr(Config, "trigger_presets", None)
        if not presets:
            whitelist_path = Path(__file__).resolve().parent.parent.parent / "data" / "whitelist" / "trigger_presets.json"
            if whitelist_path.exists():
                with open(whitelist_path, "r", encoding="utf-8") as f:
                    presets = json.load(f)
            else:
                presets = {}

        cls._cached_presets = presets
        return cls._cached_presets

    @classmethod
    def reload(cls):
        cls._cached_presets = None
        return cls.get_presets()

    @classmethod
    def resolve_trigger_plan(cls, uid_num: int) -> tuple[str, str, str, list, str, str]:
        """
        根据用户序号 (uid_num) 均匀映射并解析触发偏好配置。
        返回: (forced_decl_mode, forced_trig_type, period_type_hint, days_hint, time_range_hint, trig_instruction)
        """
        presets = cls.get_presets()
        forced_decl_mode = "explicit_declaration" if (uid_num % 2 == 1) else "implicit_induction"

        trig_mod = uid_num % 3
        if trig_mod == 1:
            forced_trig_type = "time_periodic"
            grain_idx = (uid_num // 3) % 3
            tp_cfg = presets.get("time_periodic", {})

            if grain_idx == 0:
                # 1. 日级周期 (daily)
                daily_cfg = tp_cfg.get("daily", {})
                slots = daily_cfg.get("slots", [
                    {"time_range": "08:30-10:00", "desc": "每天早高峰通勤与晨间例行业务"},
                    {"time_range": "12:30-13:30", "desc": "每天午间休息与午间复盘业务"},
                    {"time_range": "20:00-22:00", "desc": "每天晚间黄金档高频业务"}
                ])
                chosen = slots[uid_num % len(slots)]
                time_range_hint = chosen.get("time_range", "08:30-10:00")
                desc = chosen.get("desc", "每天例行业务")
                period_type_hint = "daily"
                days_hint = ["daily"]

                tpl = daily_cfg.get(
                    "instruction_template",
                    "周期时间驱动【daily日级周期】：设定每天固定时段的高频业务（如{time_range}，{desc}），period_type必须为'daily'，days设为['daily']，time_range设为'{time_range}'，trigger_condition设为明确的日周期描述（如'{desc}'）"
                )
                trig_instruction = tpl.format(time_range=time_range_hint, desc=desc)

            elif grain_idx == 1:
                # 2. 周级周期 (weekly 多样化组合)
                weekly_cfg = tp_cfg.get("weekly", {})
                combos = weekly_cfg.get("combos", [
                    {"days": ["Monday", "Friday"], "time_range": "09:30-11:30", "desc": "每周一与周五例会与业务对齐"},
                    {"days": ["Tuesday", "Thursday"], "time_range": "14:00-16:00", "desc": "每周二与周四常规专业培训/研讨"},
                    {"days": ["Saturday", "Sunday"], "time_range": "15:00-17:00", "desc": "每周六与周日周末赛事专场/排位"}
                ])
                chosen = combos[uid_num % len(combos)]
                days_hint = chosen.get("days", ["Monday", "Friday"])
                time_range_hint = chosen.get("time_range", "14:00-16:00")
                desc = chosen.get("desc", "周度例行业务")
                period_type_hint = "weekly"

                tpl = weekly_cfg.get(
                    "instruction_template",
                    "周期时间驱动【weekly周级周期】：设定每周固定周几频次的高频业务，必须多样化，严禁单一重复（已指定周组合：{days}，时段：{time_range}），period_type必须为'weekly'，days设为{days}，time_range设为'{time_range}'，trigger_condition设为明确的周周期描述（如'{desc}'）"
                )
                trig_instruction = tpl.format(days=days_hint, time_range=time_range_hint, desc=desc)

            else:
                # 3. 月级周期 (monthly)
                monthly_cfg = tp_cfg.get("monthly", {})
                combos = monthly_cfg.get("combos", [
                    {"days": ["1st", "2nd"], "time_range": "09:00-11:00", "desc": "每月月初1-2号例行开门红与月度动员会"},
                    {"days": ["15th", "16th"], "time_range": "14:00-16:00", "desc": "每月月中15-16号例行综合对账与业务巡检"},
                    {"days": ["28th", "29th"], "time_range": "20:00-22:00", "desc": "每月月末28-29号例行封账冲刺与月度大复盘"}
                ])
                chosen = combos[uid_num % len(combos)]
                days_hint = chosen.get("days", ["1st", "2nd"])
                time_range_hint = chosen.get("time_range", "14:00-16:00")
                desc = chosen.get("desc", "月度例行业务")
                period_type_hint = "monthly"

                tpl = monthly_cfg.get(
                    "instruction_template",
                    "周期时间驱动【monthly月级周期】：设定每月特定日期的月度高频业务（已指定月度日期：{days}，时段：{time_range}），period_type必须为'monthly'，days设为{days}，time_range设为'{time_range}'，trigger_condition设为明确的月周期描述（如'{desc}'）"
                )
                trig_instruction = tpl.format(days=days_hint, time_range=time_range_hint, desc=desc)

        elif trig_mod == 2:
            # 4. 任务现场驱动 (task_activity)
            forced_trig_type = "task_activity"
            period_type_hint = "task_driven"
            days_hint = ["task_specific"]

            task_cfg = presets.get("task_activity", {})
            presets_list = task_cfg.get("presets", [
                {"task_name": "客户现场合规审计", "time_range": "14:00-16:00", "trigger_condition": "执行客户现场合规审计任务"},
                {"task_name": "婚庆跟拍与现场推流", "time_range": "10:00-12:00", "trigger_condition": "执行婚庆跟拍与现场推流任务"},
                {"task_name": "高压变电站设备现场巡检", "time_range": "15:00-17:00", "trigger_condition": "执行高压变电站设备现场巡检任务"}
            ])
            chosen = presets_list[uid_num % len(presets_list)]
            task_name = chosen.get("task_name", "特定专业任务")
            time_range_hint = chosen.get("time_range", "14:00-16:00")

            tpl = task_cfg.get(
                "instruction_template",
                "任务现场驱动：因特定专业活动/现场任务触发（如'客户现场审计'、'婚庆跟拍'、'电力设备巡检'、'医疗会诊'等），trigger_condition 必须为执行该特定任务（如'执行{task_name}任务'）"
            )
            trig_instruction = tpl.format(task_name=task_name)

        else:
            # 5. 特定地点驱动 (location_environment)
            forced_trig_type = "location_environment"
            period_type_hint = "location_driven"
            days_hint = ["location_specific"]

            loc_cfg = presets.get("location_environment", {})
            presets_list = loc_cfg.get("presets", [
                {"location_name": "利兹露天集结区", "time_range": "15:00-17:00", "trigger_condition": "身处露天集结区弱网区域"},
                {"location_name": "地下封闭配电室", "time_range": "10:00-12:00", "trigger_condition": "身处地下封闭配电室深处弱网环境"},
                {"location_name": "跨城物流中转站", "time_range": "20:00-22:00", "trigger_condition": "身处跨城物流中转站露天堆场弱网区"}
            ])
            chosen = presets_list[uid_num % len(presets_list)]
            location_name = chosen.get("location_name", "特定弱网物理空间")
            time_range_hint = chosen.get("time_range", "15:00-17:00")

            tpl = loc_cfg.get(
                "instruction_template",
                "特定地点驱动：因特定物理空间/环境触发（如'利兹露天集结区'、'地下配电室'、'跨城物流中转站'、'高铁沿线弱网区'），trigger_condition 必须为身处该特定空间（如'身处{location_name}弱网区域'）"
            )
            trig_instruction = tpl.format(location_name=location_name)

        return forced_decl_mode, forced_trig_type, period_type_hint, days_hint, time_range_hint, trig_instruction
