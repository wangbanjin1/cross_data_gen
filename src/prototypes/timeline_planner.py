class TimelinePlanner:
    """
    负责将 Persona Skeleton 中解耦的素材（主线、支线、场景事件、干扰项）
    规划为 10~20 轮、贴合周期粒度与完整生命周期的长链会话序列。
    """

    @staticmethod
    def plan_timeline(persona: dict) -> list[dict]:
        user_id = persona["static_profile"]["user_id"]
        main_mt = persona["dynamic_profile"]["periodic_main_storyline"]
        scenario_events = persona["dynamic_profile"]["scenario_events"]
        sub_mt_01 = persona["dynamic_profile"]["sub_storylines"][0]
        sub_mt_02 = persona["dynamic_profile"]["sub_storylines"][1]
        dist_01 = persona["dynamic_profile"]["distractor_pool"][0]
        dist_02 = persona["dynamic_profile"]["distractor_pool"][1]
        event_01 = scenario_events[0]

        timeline = [
            # S01: Evidence Main - 首次建联，现场看台背景，明确长期规则
            {
                "session_id": f"S-{user_id}-01",
                "user_id": user_id,
                "reference_time": "2026年10月07日13时45分",
                "template_id": "T2-4",
                "memory_role": "evidence_session",
                "round_count": 2,
                "scenario_hook": "crowded_stadium",
                "storyline_ref": "MAIN_MT_01",
                "intent_plan": {
                    "application_name": main_mt["application_name"],
                    "service_name": main_mt["service_name"],
                    "resolution": main_mt["preferred_params"]["resolution"],
                    "rtt": main_mt["preferred_params"]["rtt_max"],
                    "start_timestamp": "2026年10月07日14时00分",
                    "end_timestamp": "2026年10月07日16时00分",
                    "duration": "120min"
                }
            },
            # S02: Evidence Sub 1 - 支线1初建：大巴转场微信视频调度
            {
                "session_id": f"S-{user_id}-02",
                "user_id": user_id,
                "reference_time": "2026年10月11日18时30分",
                "template_id": "T2-1",
                "memory_role": "evidence_session",
                "round_count": 2,
                "scenario_hook": "transit_bus",
                "storyline_ref": "SUB_MT_01",
                "intent_plan": {
                    "application_name": sub_mt_01["application_name"],
                    "service_name": sub_mt_01["service_name"],
                    "resolution": sub_mt_01["preferred_params"]["resolution"],
                    "rtt": sub_mt_01["preferred_params"]["rtt_max"],
                    "start_timestamp": "2026年10月11日18时45分",
                    "end_timestamp": "2026年10月11日19时45分",
                    "duration": "60min"
                }
            },
            # S03: Reinforcement Main - 隔周周三主线复用，省略参数，Agent 反问确认
            {
                "session_id": f"S-{user_id}-03",
                "user_id": user_id,
                "reference_time": "2026年10月14日13时50分",
                "template_id": "T2-1",
                "memory_role": "reinforcement_session",
                "round_count": 2,
                "scenario_hook": "transit_bus",
                "storyline_ref": "MAIN_MT_01",
                "intent_plan": {
                    "application_name": main_mt["application_name"],
                    "service_name": main_mt["service_name"],
                    "resolution": main_mt["preferred_params"]["resolution"],
                    "rtt": main_mt["preferred_params"]["rtt_max"],
                    "start_timestamp": "2026年10月14日14时00分",
                    "end_timestamp": "2026年10月14日16时00分",
                    "duration": "120min"
                }
            },
            # S04: Evidence Sub 2 - 支线2初建：驻地酒店快手赛事录像复盘
            {
                "session_id": f"S-{user_id}-04",
                "user_id": user_id,
                "reference_time": "2026年10月15日20时00分",
                "template_id": "T2-1",
                "memory_role": "evidence_session",
                "round_count": 2,
                "scenario_hook": "rest_stop_hotel",
                "storyline_ref": "SUB_MT_02",
                "intent_plan": {
                    "application_name": sub_mt_02["application_name"],
                    "service_name": sub_mt_02["service_name"],
                    "resolution": sub_mt_02["preferred_params"]["resolution"],
                    "rtt": sub_mt_02["preferred_params"]["rtt_max"],
                    "start_timestamp": "2026年10月15日20时15分",
                    "end_timestamp": "2026年10月15日21时45分",
                    "duration": "90min"
                }
            },
            # S05: Distractor 1 - 酒店单轮腾讯会议，单次说清，不形成记忆
            {
                "session_id": f"S-{user_id}-05",
                "user_id": user_id,
                "reference_time": "2026年10月18日10时00分",
                "template_id": "T1-1",
                "memory_role": "distractor_session",
                "round_count": 1,
                "scenario_hook": "rest_stop_hotel",
                "storyline_ref": "DIST_01",
                "intent_plan": {
                    "application_name": dist_01["application_name"],
                    "service_name": dist_01["service_name"],
                    "resolution": dist_01["params"]["resolution"],
                    "rtt": dist_01["params"]["rtt_max"],
                    "start_timestamp": "2026年10月18日10时00分",
                    "end_timestamp": "2026年10月18日10时30分",
                    "duration": "30min"
                }
            },
            # S06: Reinforcement Sub 1 - 转场大巴再次视频调度，复用支线1记忆
            {
                "session_id": f"S-{user_id}-06",
                "user_id": user_id,
                "reference_time": "2026年10月21日18时40分",
                "template_id": "T2-1",
                "memory_role": "reinforcement_session",
                "round_count": 2,
                "scenario_hook": "transit_bus",
                "storyline_ref": "SUB_MT_01",
                "intent_plan": {
                    "application_name": sub_mt_01["application_name"],
                    "service_name": sub_mt_01["service_name"],
                    "resolution": sub_mt_01["preferred_params"]["resolution"],
                    "rtt": sub_mt_01["preferred_params"]["rtt_max"],
                    "start_timestamp": "2026年10月21日19时00分",
                    "end_timestamp": "2026年10月21日20时00分",
                    "duration": "60min"
                }
            },
            # S07: Reuse Main - 周六巡讲主线跨周期稳定复用
            {
                "session_id": f"S-{user_id}-07",
                "user_id": user_id,
                "reference_time": "2026年10月24日13时45分",
                "template_id": "T2-1",
                "memory_role": "reuse_session",
                "round_count": 2,
                "scenario_hook": "crowded_stadium",
                "storyline_ref": "MAIN_MT_01",
                "intent_plan": {
                    "application_name": main_mt["application_name"],
                    "service_name": main_mt["service_name"],
                    "resolution": main_mt["preferred_params"]["resolution"],
                    "rtt": main_mt["preferred_params"]["rtt_max"],
                    "start_timestamp": "2026年10月24日14时00分",
                    "end_timestamp": "2026年10月24日16时00分",
                    "duration": "120min"
                }
            },
            # S08: Reinforcement Main - 周三巡讲主线持续强化
            {
                "session_id": f"S-{user_id}-08",
                "user_id": user_id,
                "reference_time": "2026年10月28日13时50分",
                "template_id": "T2-1",
                "memory_role": "reinforcement_session",
                "round_count": 2,
                "scenario_hook": "transit_bus",
                "storyline_ref": "MAIN_MT_01",
                "intent_plan": {
                    "application_name": main_mt["application_name"],
                    "service_name": main_mt["service_name"],
                    "resolution": main_mt["preferred_params"]["resolution"],
                    "rtt": main_mt["preferred_params"]["rtt_max"],
                    "start_timestamp": "2026年10月28日14时00分",
                    "end_timestamp": "2026年10月28日16时00分",
                    "duration": "120min"
                }
            },
            # S09: Reinforcement Sub 2 - 酒店再次复盘赛事，复用支线2
            {
                "session_id": f"S-{user_id}-09",
                "user_id": user_id,
                "reference_time": "2026年10月29日20时10分",
                "template_id": "T2-1",
                "memory_role": "reinforcement_session",
                "round_count": 2,
                "scenario_hook": "rest_stop_hotel",
                "storyline_ref": "SUB_MT_02",
                "intent_plan": {
                    "application_name": sub_mt_02["application_name"],
                    "service_name": sub_mt_02["service_name"],
                    "resolution": sub_mt_02["preferred_params"]["resolution"],
                    "rtt": sub_mt_02["preferred_params"]["rtt_max"],
                    "start_timestamp": "2026年10月29日20时30分",
                    "end_timestamp": "2026年10月29日22时00分",
                    "duration": "90min"
                }
            },
            # S10: Distractor 2 - 周末休息刷微信短视频，单轮全说清
            {
                "session_id": f"S-{user_id}-10",
                "user_id": user_id,
                "reference_time": "2026年11月01日12时30分",
                "template_id": "T1-1",
                "memory_role": "distractor_session",
                "round_count": 1,
                "scenario_hook": "rest_stop_hotel",
                "storyline_ref": "DIST_02",
                "intent_plan": {
                    "application_name": dist_02["application_name"],
                    "service_name": dist_02["service_name"],
                    "resolution": dist_02["params"]["resolution"],
                    "rtt": dist_02["params"]["rtt_max"],
                    "start_timestamp": "2026年11月01日12时30分",
                    "end_timestamp": "2026年11月01日13时30分",
                    "duration": "60min"
                }
            },
            # S11: Correction - 场景事件：进入高山残运赛事期(11-01~11-15)，恶劣风雪，主动纠正为主线 720p+30ms
            {
                "session_id": f"S-{user_id}-11",
                "user_id": user_id,
                "reference_time": "2026年11月04日13时40分",
                "template_id": "T2-3",
                "memory_role": "correction_session",
                "round_count": 2,
                "scenario_hook": "cold_outdoors",
                "storyline_ref": "EVT_WINTER_GAMES",
                "intent_plan": {
                    "application_name": main_mt["application_name"],
                    "service_name": main_mt["service_name"],
                    "resolution": event_01["preference_override"]["resolution"],
                    "rtt": event_01["preference_override"]["rtt_max"],
                    "start_timestamp": "2026年11月04日14时00分",
                    "end_timestamp": "2026年11月04日16时00分",
                    "duration": "120min"
                }
            },
            # S12: Reuse Main - 赛事期内周六开播，复用临时纠正新记忆 (720p + 30ms)
            {
                "session_id": f"S-{user_id}-12",
                "user_id": user_id,
                "reference_time": "2026年11月07日13时45分",
                "template_id": "T2-1",
                "memory_role": "reuse_session",
                "round_count": 2,
                "scenario_hook": "crowded_stadium",
                "storyline_ref": "EVT_WINTER_GAMES",
                "intent_plan": {
                    "application_name": main_mt["application_name"],
                    "service_name": main_mt["service_name"],
                    "resolution": event_01["preference_override"]["resolution"],
                    "rtt": event_01["preference_override"]["rtt_max"],
                    "start_timestamp": "2026年11月07日14时00分",
                    "end_timestamp": "2026年11月07日16时00分",
                    "duration": "120min"
                }
            },
            # S13: Reuse Sub 1 - 赛事转场期微信视频碰头，支线不受主线临时纠正干扰，准确复用 720p+100ms
            {
                "session_id": f"S-{user_id}-13",
                "user_id": user_id,
                "reference_time": "2026年11月11日18时35分",
                "template_id": "T2-1",
                "memory_role": "reuse_session",
                "round_count": 2,
                "scenario_hook": "transit_bus",
                "storyline_ref": "SUB_MT_01",
                "intent_plan": {
                    "application_name": sub_mt_01["application_name"],
                    "service_name": sub_mt_01["service_name"],
                    "resolution": sub_mt_01["preferred_params"]["resolution"],
                    "rtt": sub_mt_01["preferred_params"]["rtt_max"],
                    "start_timestamp": "2026年11月11日19时00分",
                    "end_timestamp": "2026年11月11日20时00分",
                    "duration": "60min"
                }
            },
            # S14: Distractor 1 - 赛事闭幕通气会，腾讯会议单轮
            {
                "session_id": f"S-{user_id}-14",
                "user_id": user_id,
                "reference_time": "2026年11月15日10时00分",
                "template_id": "T1-1",
                "memory_role": "distractor_session",
                "round_count": 1,
                "scenario_hook": "rest_stop_hotel",
                "storyline_ref": "DIST_01",
                "intent_plan": {
                    "application_name": dist_01["application_name"],
                    "service_name": dist_01["service_name"],
                    "resolution": dist_01["params"]["resolution"],
                    "rtt": dist_01["params"]["rtt_max"],
                    "start_timestamp": "2026年11月15日10时00分",
                    "end_timestamp": "2026年11月15日10时30分",
                    "duration": "30min"
                }
            },
            # S15: Reuse Main Recovery - 赛事期结束(>11-15)，主线恢复原 1080p+50ms 规则，Agent 确认恢复
            {
                "session_id": f"S-{user_id}-15",
                "user_id": user_id,
                "reference_time": "2026年11月18日13时45分",
                "template_id": "T2-1",
                "memory_role": "reuse_session",
                "round_count": 2,
                "scenario_hook": "crowded_stadium",
                "storyline_ref": "MAIN_MT_01",
                "intent_plan": {
                    "application_name": main_mt["application_name"],
                    "service_name": main_mt["service_name"],
                    "resolution": main_mt["preferred_params"]["resolution"],
                    "rtt": main_mt["preferred_params"]["rtt_max"],
                    "start_timestamp": "2026年11月18日14时00分",
                    "end_timestamp": "2026年11月18日16时00分",
                    "duration": "120min"
                }
            }
        ]
        return timeline
