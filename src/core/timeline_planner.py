import re
from src.templates.timeline_blueprints import get_15_session_blueprints

class DynamicTimelinePlanner:
    """
    时间线规划器 (DynamicTimelinePlanner)
    负责根据 Persona Skeleton 动态规划 15 会话时间线，
    并绑定记忆触发类型、声明模式与业务参数。
    """

    @classmethod
    def plan(cls, persona: dict) -> list[dict]:
        user_id = persona["static_profile"]["user_id"]
        main_mt = persona["dynamic_profile"]["periodic_main_storyline"]
        scenario_events = persona["dynamic_profile"].get("scenario_events", [])
        sub_list = persona["dynamic_profile"].get("sub_storylines", [])
        dist_list = persona["dynamic_profile"].get("distractor_pool", [])

        sub_01 = sub_list[0] if len(sub_list) > 0 else main_mt
        sub_02 = sub_list[1] if len(sub_list) > 1 else sub_01
        dist_01 = dist_list[0] if len(dist_list) > 0 else sub_01
        dist_02 = dist_list[1] if len(dist_list) > 1 else dist_01
        evt_01 = scenario_events[0] if len(scenario_events) > 0 else {
            "preference_override": {"resolution": "720p", "rtt_max": "30ms"},
            "event_name": "临时特殊场景保障",
            "scene_description": "现场人流拥塞临时防抖保障"
        }

        # 判定长期记忆声明模式：严格按人物ID进行50/50奇偶分流，保障显式声明与隐式归纳均匀分布
        num_match = re.search(r'\d+', user_id)
        uid_num = int(num_match.group()) if num_match else 1
        decl_mode = "explicit_declaration" if (uid_num % 2 == 1) else "implicit_induction"

        # 判定主线记忆触发类型：三大核心主线类型（周期时间型、任务/现场型、特定地点型）均匀分布
        explicit_trig_type = main_mt.get("storyline_trigger_type")
        if explicit_trig_type in ["time_periodic", "task_activity", "location_environment"]:
            storyline_trigger_type = explicit_trig_type
        else:
            trig_mod = uid_num % 3
            if trig_mod == 1:
                storyline_trigger_type = "time_periodic"
            elif trig_mod == 2:
                storyline_trigger_type = "task_activity"
            else:
                storyline_trigger_type = "location_environment"

        task_name = main_mt.get("name", "业务现场任务")
        raw_trig_cond = main_mt.get("trigger_condition")
        if storyline_trigger_type == "task_activity":
            main_env_desc = f"{task_name}现场"
            main_trigger_desc = raw_trig_cond if raw_trig_cond else f"执行【{task_name}】任务"
        elif storyline_trigger_type == "location_environment":
            main_env_desc = raw_trig_cond if raw_trig_cond else "利兹露天集结区"
            main_trigger_desc = raw_trig_cond if raw_trig_cond else "处于【利兹露天集结区/特定弱网区域】"
        else:
            main_env_desc = "常规周期保障现场"
            main_trigger_desc = raw_trig_cond if raw_trig_cond else "每周常规周期时段"

        blueprint_configs = get_15_session_blueprints(
            main_mt=main_mt,
            sub_01=sub_01,
            sub_02=sub_02,
            dist_01=dist_01,
            dist_02=dist_02,
            evt_01=evt_01,
            decl_mode=decl_mode,
            storyline_trigger_type=storyline_trigger_type,
            main_env_desc=main_env_desc,
            main_trigger_desc=main_trigger_desc,
        )

        sessions = []
        for cfg in blueprint_configs:
            src = cfg["source"]
            is_override = "override" in cfg
            res = cfg["override"].get("resolution", "720p") if is_override else (
                src.get("preferred_params", {}).get("resolution") or src.get("params", {}).get("resolution", "1080p")
            )
            rtt = cfg["override"].get("rtt_max", "30ms") if is_override else (
                src.get("preferred_params", {}).get("rtt_max") or src.get("params", {}).get("rtt_max", "50ms")
            )

            s_obj = {
                "session_id": f"S-{user_id}-{cfg['idx']:02d}",
                "user_id": user_id,
                "reference_time": cfg["ref_time"],
                "template_id": cfg["template_id"],
                "memory_role": cfg["role"],
                "round_count": 1 if (cfg["template_id"].startswith("T1") or cfg["template_id"].startswith("X-1")) else 2,
                "blueprint_type": cfg["type"],
                "scenario_env": cfg["env"],
                "memory_action": cfg["action"],
                "declaration_mode": cfg.get("declaration_mode", decl_mode),
                "storyline_trigger_type": cfg.get("storyline_trigger_type", storyline_trigger_type if cfg["type"].startswith("main") else "time_periodic"),
                "trigger_condition": cfg.get("trigger_condition", main_trigger_desc if cfg["type"].startswith("main") else ""),
                "ood_goal": cfg.get("ood_goal", ""),
                "target_params": {
                    "application_name": src["application_name"],
                    "service_name": src["service_name"],
                    "resolution": res,
                    "rtt": rtt,
                    "start_timestamp": cfg["start"],
                    "end_timestamp": cfg["end"],
                    "duration": cfg["dur"]
                },
                "period_type": main_mt.get("period_type", "weekly"),
                "base_duration": cfg.get("base_dur", cfg["dur"]),
                "base_end_timestamp": cfg.get("base_end", cfg["end"]),
                "aliases": src.get("aliases", {})
            }
            sessions.append(s_obj)

        return sessions
