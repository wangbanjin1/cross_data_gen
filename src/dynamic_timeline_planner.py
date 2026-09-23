class DynamicTimelinePlanner:
    """
    通用时间链规划器：能够将任意结构化 Persona Skeleton 动态规划为 15 会话的长链时间序列。
    完全根据画像中定义的 Main Storyline, Sub Storylines, Scenario Events 和 Distractors 进行装配。
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
        import re
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

        # 15个会话的蓝图定义
        blueprint_configs = [
            # 01: Main Evidence
            {
                "idx": 1, "ref_time": "2026年10月07日13时45分", "template_id": "T2-4", "role": "evidence_session",
                "source": main_mt, "type": "main", "start": "2026年10月07日14时00分", "end": "2026年10月07日16时00分", "dur": "120min",
                "env": main_env_desc, 
                "action": "declare_explicit_rule" if decl_mode == "explicit_declaration" else "single_task_implicit_behavior",
                "declaration_mode": decl_mode,
                "storyline_trigger_type": storyline_trigger_type,
                "trigger_condition": main_trigger_desc
            },
            # 02: Sub 1 Evidence (T2-2 歧义消解)
            {
                "idx": 2, "ref_time": "2026年10月11日18时30分", "template_id": "T2-2", "role": "evidence_session",
                "source": sub_01, "type": "sub_01", "start": "2026年10月11日18时45分", "end": "2026年10月11日19时45分", "dur": "60min",
                "env": "大巴跨城转场高速公路", "action": "disambiguate_sub_storyline_1",
                "declaration_mode": "implicit_induction",
                "storyline_trigger_type": "location_environment",
                "trigger_condition": "大巴转场弱网环境"
            },
            # 03: Main Reinforcement
            {
                "idx": 3, "ref_time": "2026年10月14日13时50分", "template_id": "T2-1", "role": "reinforcement_session",
                "source": main_mt, "type": "main", "start": "2026年10月14日14时00分", "end": "2026年10月14日16时00分", "dur": "120min",
                "env": main_env_desc, 
                "action": "reinforce_explicit_memory" if decl_mode == "explicit_declaration" else "crystallize_implicit_memory",
                "declaration_mode": decl_mode,
                "storyline_trigger_type": storyline_trigger_type,
                "trigger_condition": main_trigger_desc
            },
            # 04: Sub 2 Evidence
            {
                "idx": 4, "ref_time": "2026年10月15日20时00分", "template_id": "T2-1", "role": "evidence_session",
                "source": sub_02, "type": "sub_02", "start": "2026年10月15日20时15分", "end": "2026年10月15日21时45分", "dur": "90min",
                "env": "驻地酒店休息区", "action": "establish_sub_storyline_2",
                "declaration_mode": "implicit_induction",
                "storyline_trigger_type": "location_environment",
                "trigger_condition": "驻地酒店休息区"
            },
            # 05: Distractor 1 (T1-2 纯域外拒绝，如宽带光纤报修)
            {
                "idx": 5, "ref_time": "2026年10月18日10时00分", "template_id": "T1-2", "role": "distractor_session",
                "source": dist_01, "type": "distractor_ood", "start": "2026年10月18日10时00分", "end": "2026年10月18日10时30分", "dur": "30min",
                "env": "酒店临时办公区网络故障", "action": "reject_out_of_domain",
                "ood_goal": "宽带光纤装维报修"
            },
            # 06: Sub 1 Reinforcement
            {
                "idx": 6, "ref_time": "2026年10月21日18时40分", "template_id": "T2-1", "role": "reinforcement_session",
                "source": sub_01, "type": "sub_01", "start": "2026年10月21日19时00分", "end": "2026年10月21日20时00分", "dur": "60min",
                "env": "大巴转场途中", "action": "reinforce_sub_storyline_1"
            },
            # 07: Main Reuse (T2-5 延长保障时长至 180min)
            {
                "idx": 7, "ref_time": "2026年10月24日13时45分", "template_id": "T2-5", "role": "reuse_session",
                "source": main_mt, "type": "main", "start": "2026年10月24日14时00分", "end": "2026年10月24日17时00分", "dur": "180min",
                "env": main_env_desc, "action": "extend_duration_amend",
                "storyline_trigger_type": storyline_trigger_type,
                "trigger_condition": main_trigger_desc
            },
            # 08: Main Reinforcement
            {
                "idx": 8, "ref_time": "2026年10月28日13时50分", "template_id": "T2-1", "role": "reinforcement_session",
                "source": main_mt, "type": "main", "start": "2026年10月28日14时00分", "end": "2026年10月28日16时00分", "dur": "120min",
                "env": main_env_desc, "action": "reinforce_main_memory",
                "storyline_trigger_type": storyline_trigger_type,
                "trigger_condition": main_trigger_desc
            },
            # 09: Sub 2 Reinforcement
            {
                "idx": 9, "ref_time": "2026年10月29日20时10分", "template_id": "T2-1", "role": "reinforcement_session",
                "source": sub_02, "type": "sub_02", "start": "2026年10月29日20时30分", "end": "2026年10月29日22时00分", "dur": "90min",
                "env": "驻地复盘业务", "action": "reinforce_sub_storyline_2"
            },
            # 10: Distractor 2 (X-1 混合诉求一办一拒)
            {
                "idx": 10, "ref_time": "2026年11月01日12时30分", "template_id": "X-1", "role": "distractor_session",
                "source": dist_02, "type": "distractor_mixed", "start": "2026年11月01日12时30分", "end": "2026年11月01日13时30分", "dur": "60min",
                "env": "周末午休个人时间", "action": "mixed_in_out_domain",
                "ood_goal": "手机话费充值与账单查询"
            },
            # 11: Event Correction
            {
                "idx": 11, "ref_time": "2026年11月04日13时40分", "template_id": "T2-3", "role": "correction_session",
                "source": main_mt, "type": "event_override", "start": "2026年11月04日14时00分", "end": "2026年11月04日16时00分", "dur": "120min",
                "env": evt_01.get("scene_description", "恶劣环境临时保障"), "action": "override_temporary_preference",
                "override": evt_01.get("preference_override", {})
            },
            # 12: Event Reuse
            {
                "idx": 12, "ref_time": "2026年11月07日13时45分", "template_id": "T2-1", "role": "reuse_session",
                "source": main_mt, "type": "event_reuse", "start": "2026年11月07日14时00分", "end": "2026年11月07日16时00分", "dur": "120min",
                "env": "特殊事件集结区", "action": "reuse_temporary_preference",
                "override": evt_01.get("preference_override", {})
            },
            # 13: Sub 1 Reuse
            {
                "idx": 13, "ref_time": "2026年11月11日18时35分", "template_id": "T2-1", "role": "reuse_session",
                "source": sub_01, "type": "sub_01", "start": "2026年11月11日19时00分", "end": "2026年11月11日20时00分", "dur": "60min",
                "env": "转场大巴途中", "action": "sub_memory_unaffected"
            },
            # 14: Distractor 1
            {
                "idx": 14, "ref_time": "2026年11月15日10时00分", "template_id": "T1-1", "role": "distractor_session",
                "source": dist_01, "type": "distractor", "start": "2026年11月15日10时00分", "end": "2026年11月15日10时30分", "dur": "30min",
                "env": "阶段工作总结会", "action": "distractor_no_memory"
            },
            # 15: Event Expiry & Main Recovery
            {
                "idx": 15, "ref_time": "2026年11月18日13时45分", "template_id": "T2-1", "role": "reuse_session",
                "source": main_mt, "type": "main_recovery", "start": "2026年11月18日14时00分", "end": "2026年11月18日16时00分", "dur": "120min",
                "env": main_env_desc, "action": "recover_long_term_rule",
                "storyline_trigger_type": storyline_trigger_type,
                "trigger_condition": main_trigger_desc
            }
        ]

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
                "aliases": src.get("aliases", {})
            }
            sessions.append(s_obj)

        return sessions
