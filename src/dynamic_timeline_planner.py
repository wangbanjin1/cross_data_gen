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

        # 15个会话的蓝图定义
        blueprint_configs = [
            # 01: Main Evidence
            {
                "idx": 1, "ref_time": "2026年10月07日13时45分", "template_id": "T2-4", "role": "evidence_session",
                "source": main_mt, "type": "main", "start": "2026年10月07日14时00分", "end": "2026年10月07日16时00分", "dur": "120min",
                "env": "露天现场集结区", "action": "declare_long_term_rule"
            },
            # 02: Sub 1 Evidence
            {
                "idx": 2, "ref_time": "2026年10月11日18时30分", "template_id": "T2-1", "role": "evidence_session",
                "source": sub_01, "type": "sub_01", "start": "2026年10月11日18时45分", "end": "2026年10月11日19时45分", "dur": "60min",
                "env": "大巴跨城转场高速公路", "action": "establish_sub_storyline_1"
            },
            # 03: Main Reinforcement
            {
                "idx": 3, "ref_time": "2026年10月14日13时50分", "template_id": "T2-1", "role": "reinforcement_session",
                "source": main_mt, "type": "main", "start": "2026年10月14日14时00分", "end": "2026年10月14日16时00分", "dur": "120min",
                "env": "转场大巴刚到现场", "action": "reinforce_main_memory"
            },
            # 04: Sub 2 Evidence
            {
                "idx": 4, "ref_time": "2026年10月15日20时00分", "template_id": "T2-1", "role": "evidence_session",
                "source": sub_02, "type": "sub_02", "start": "2026年10月15日20时15分", "end": "2026年10月15日21时45分", "dur": "90min",
                "env": "驻地酒店休息区", "action": "establish_sub_storyline_2"
            },
            # 05: Distractor 1
            {
                "idx": 5, "ref_time": "2026年10月18日10时00分", "template_id": "T1-1", "role": "distractor_session",
                "source": dist_01, "type": "distractor", "start": "2026年10月18日10时00分", "end": "2026年10月18日10时30分", "dur": "30min",
                "env": "酒店临时办公区", "action": "distractor_no_memory"
            },
            # 06: Sub 1 Reinforcement
            {
                "idx": 6, "ref_time": "2026年10月21日18时40分", "template_id": "T2-1", "role": "reinforcement_session",
                "source": sub_01, "type": "sub_01", "start": "2026年10月21日19时00分", "end": "2026年10月21日20时00分", "dur": "60min",
                "env": "大巴转场途中", "action": "reinforce_sub_storyline_1"
            },
            # 07: Main Reuse
            {
                "idx": 7, "ref_time": "2026年10月24日13时45分", "template_id": "T2-1", "role": "reuse_session",
                "source": main_mt, "type": "main", "start": "2026年10月24日14时00分", "end": "2026年10月24日16时00分", "dur": "120min",
                "env": "周六现场看台", "action": "reuse_main_memory"
            },
            # 08: Main Reinforcement
            {
                "idx": 8, "ref_time": "2026年10月28日13时50分", "template_id": "T2-1", "role": "reinforcement_session",
                "source": main_mt, "type": "main", "start": "2026年10月28日14时00分", "end": "2026年10月28日16时00分", "dur": "120min",
                "env": "常规工作转场途中", "action": "reinforce_main_memory"
            },
            # 09: Sub 2 Reinforcement
            {
                "idx": 9, "ref_time": "2026年10月29日20时10分", "template_id": "T2-1", "role": "reinforcement_session",
                "source": sub_02, "type": "sub_02", "start": "2026年10月29日20时30分", "end": "2026年10月29日22时00分", "dur": "90min",
                "env": "驻地复盘业务", "action": "reinforce_sub_storyline_2"
            },
            # 10: Distractor 2
            {
                "idx": 10, "ref_time": "2026年11月01日12时30分", "template_id": "T1-1", "role": "distractor_session",
                "source": dist_02, "type": "distractor", "start": "2026年11月01日12时30分", "end": "2026年11月01日13时30分", "dur": "60min",
                "env": "周末午休个人时间", "action": "distractor_no_memory"
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
                "env": "恢复日常常规现场", "action": "recover_long_term_rule"
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
                "round_count": 1 if cfg["template_id"].startswith("T1") else 2,
                "blueprint_type": cfg["type"],
                "scenario_env": cfg["env"],
                "memory_action": cfg["action"],
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
