class DialogueEngine:
    """
    负责将 15 会话的长链时间线渲染为符合画像口吻与场景的真实对话，
    严格保证：
      1. 每个 Session 均以 Agent 的明确答复结束 (Acknowledge)；
      2. 凡是 reinforcement / reuse 的记忆复用会话，一律 ≥2 轮：
         第 1 轮 Agent 结合记忆反问待确认配置，第 2 轮用户明确确认，Agent 最终受理关闭；
      3. 支线记忆与干扰项素材均从 Persona 骨架中提取绑定；
      4. source_type 精确映射 (Turn / Memory / Knowledge / Context)。
    """

    @classmethod
    def render_session(cls, session_plan: dict, persona: dict, memory_store: dict) -> dict:
        sid = session_plan["session_id"]
        index = int(sid.split("-")[-1])
        method_name = f"_render_s{index:02d}"
        if hasattr(cls, method_name):
            return getattr(cls, method_name)(session_plan, persona, memory_store)
        else:
            raise ValueError(f"No renderer implemented for {sid} ({method_name})")

    # ==================== S01: Evidence Main ====================
    @staticmethod
    def _render_s01(plan, persona, memory_store):
        memory_store["MF_001"] = {
            "application_name": "抖音",
            "service_name": "开直播",
            "resolution": "1080p",
            "rtt": "50ms",
            "alias": "巡讲推流",
            "scope": "weekly_wednesday_saturday_afternoon",
            "declared_at": plan["reference_time"]
        }
        return {
            "session_id": plan["session_id"],
            "user_id": plan["user_id"],
            "reference_time": plan["reference_time"],
            "session_meta": {
                "template_id": plan["template_id"],
                "round_count": 2,
                "intent_count": 1,
                "memory_role": plan["memory_role"],
                "skeleton_signature": "T2-4|2|1|I1:抖音/开直播/1/clarified/resolved|none|Turn,Turn,Knowledge,Turn,Turn,Turn,Turn|none",
                "scenario": {"environment": "露天体育场看台集结区", "persona_tone": "坚毅果断", "memory_action": "declare_long_term_rule"}
            },
            "event_sequence": [
                {
                    "turn": 1,
                    "user": {
                        "utterance": "你好！我刚进雪场集结区，看台这边人越聚越多信号明显被挤了。两点整我有一场巡讲推流，帮我做个网络保障，画质要高清，时延尽量低一点，千万别掉链子！",
                        "action_types": ["Create_Intent_Request", "Inform_Slot"]
                    },
                    "agent": {
                        "utterance": "您好！已为您定位现场保障通道。为了提供最佳保障效果，请确认：您使用的是抖音平台开直播吗？另外期望的具体分辨率和时延上限是多少？保障预计持续到几点？",
                        "action_types": ["Request_Slot"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": ["application_name", "resolution", "rtt", "timestamp.end_timestamp"]
                },
                {
                    "turn": 2,
                    "user": {
                        "utterance": "对，就是阿抖开直播！分辨率给我定死1080P，时延上限50毫秒以内，播到下午四点。记住了，以后只要周三或者周六我说巡讲推流，全部按这个老规矩来办！",
                        "action_types": ["Fill_Missing_Slot", "Confirm_Slot"]
                    },
                    "agent": {
                        "utterance": "明白！已为您开通抖音开直播网络保障：分辨率1080p，时延上限50毫秒，保障时间为今天14:00到16:00，共2小时。您的偏好规则已牢记，后续周三、周六的巡讲推流都会默认按此标准为您保驾护航！",
                        "action_types": ["Acknowledge"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                }
            ],
            "intents": [
                {
                    "intent_id": "I1",
                    "status": "resolved",
                    "closure_path": "clarified",
                    "expression_level": 1,
                    "intent": "抖音开直播保障",
                    "params": {
                        "application_name": {"value": "抖音", "source_type": "Turn", "source_ref": "U2"},
                        "service_name": {"value": "开直播", "source_type": "Turn", "source_ref": "U1"},
                        "resolution": {"min_value": {"value": "1080p", "source_type": "Turn", "source_ref": "U2"}},
                        "rtt": {"max_value": {"value": "50ms", "source_type": "Turn", "source_ref": "U2"}},
                        "timestamp": {
                            "start_timestamp": {"value": "2026年10月07日14时00分", "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": "2026年10月07日16时00分", "source_type": "Turn", "source_ref": "U2"},
                            "duration": {"value": "120min", "source_type": "Context", "source_ref": "U2"}
                        }
                    }
                }
            ],
            "relations": [],
            "slot_updates": [
                {
                    "intent_id": "I1",
                    "turn_updates": [
                        {
                            "turn": 1,
                            "params": {
                                "service_name": {"value": "开直播", "source_type": "Turn", "source_ref": "U1"},
                                "timestamp": {"start_timestamp": {"value": "2026年10月07日14时00分", "source_type": "Turn", "source_ref": "U1"}}
                            }
                        },
                        {
                            "turn": 2,
                            "params": {
                                "application_name": {"value": "抖音", "source_type": "Turn", "source_ref": "U2"},
                                "resolution": {"min_value": {"value": "1080p", "source_type": "Turn", "source_ref": "U2"}},
                                "rtt": {"max_value": {"value": "50ms", "source_type": "Turn", "source_ref": "U2"}},
                                "timestamp": {
                                    "end_timestamp": {"value": "2026年10月07日16时00分", "source_type": "Turn", "source_ref": "U2"},
                                    "duration": {"value": "120min", "source_type": "Context", "source_ref": "U2"}
                                }
                            }
                        }
                    ]
                }
            ]
        }

    # ==================== S02: Evidence Sub 1 ====================
    @staticmethod
    def _render_s02(plan, persona, memory_store):
        sub_01 = persona["dynamic_profile"]["sub_storylines"][0]
        memory_store["SUB_001"] = {
            "application_name": sub_01["application_name"],
            "service_name": sub_01["service_name"],
            "resolution": sub_01["preferred_params"]["resolution"],
            "rtt": sub_01["preferred_params"]["rtt_max"],
            "alias": sub_01["aliases"]["service_aliases"][0],
            "scope": "transit_evening",
            "declared_at": plan["reference_time"]
        }
        return {
            "session_id": plan["session_id"],
            "user_id": plan["user_id"],
            "reference_time": plan["reference_time"],
            "session_meta": {
                "template_id": plan["template_id"],
                "round_count": 2,
                "intent_count": 1,
                "memory_role": plan["memory_role"],
                "skeleton_signature": "T2-1|2|1|I1:微信/视频通话/1/clarified/resolved|none|Turn,Turn,Knowledge,Turn,Turn,Turn,Turn|none",
                "scenario": {"environment": "大巴跨城转场高速公路", "persona_tone": "干练紧凑", "memory_action": "establish_sub_storyline"}
            },
            "event_sequence": [
                {
                    "turn": 1,
                    "user": {
                        "utterance": "大巴还在跨城高速上颠簸，车速有点快网络飘。傍晚6点45到7点45，我要用微信跟领队视频碰头对流程，帮我保一下通话网络。",
                        "action_types": ["Create_Intent_Request", "Inform_Slot"]
                    },
                    "agent": {
                        "utterance": "收到，高速移动场景已为您准备链路切换保障。请问微信视频通话对画质和时延有什么具体要求呢？",
                        "action_types": ["Request_Slot"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": ["resolution", "rtt"]
                },
                {
                    "turn": 2,
                    "user": {
                        "utterance": "车上对讲看得清人脸就行，标清720P，延时大点没关系，100毫秒内能正常说话不中断就可以，抓紧办上！",
                        "action_types": ["Fill_Missing_Slot"]
                    },
                    "agent": {
                        "utterance": "好的，已为您受理微信视频通话保障：画质720p，时延上限100毫秒，保障时间为今天18:45到19:45，共1小时，祝您对会顺利！",
                        "action_types": ["Acknowledge"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                }
            ],
            "intents": [
                {
                    "intent_id": "I1",
                    "status": "resolved",
                    "closure_path": "clarified",
                    "expression_level": 1,
                    "intent": "微信视频通话保障",
                    "params": {
                        "application_name": {"value": "微信", "source_type": "Turn", "source_ref": "U1"},
                        "service_name": {"value": "视频通话", "source_type": "Turn", "source_ref": "U1"},
                        "resolution": {"min_value": {"value": "720p", "source_type": "Turn", "source_ref": "U2"}},
                        "rtt": {"max_value": {"value": "100ms", "source_type": "Turn", "source_ref": "U2"}},
                        "timestamp": {
                            "start_timestamp": {"value": "2026年10月11日18时45分", "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": "2026年10月11日19时45分", "source_type": "Turn", "source_ref": "U1"},
                            "duration": {"value": "60min", "source_type": "Context", "source_ref": "U1"}
                        }
                    }
                }
            ],
            "relations": [],
            "slot_updates": [
                {
                    "intent_id": "I1",
                    "turn_updates": [
                        {
                            "turn": 1,
                            "params": {
                                "application_name": {"value": "微信", "source_type": "Turn", "source_ref": "U1"},
                                "service_name": {"value": "视频通话", "source_type": "Turn", "source_ref": "U1"},
                                "timestamp": {
                                    "start_timestamp": {"value": "2026年10月11日18时45分", "source_type": "Turn", "source_ref": "U1"},
                                    "end_timestamp": {"value": "2026年10月11日19时45分", "source_type": "Turn", "source_ref": "U1"}
                                }
                            }
                        },
                        {
                            "turn": 2,
                            "params": {
                                "resolution": {"min_value": {"value": "720p", "source_type": "Turn", "source_ref": "U2"}},
                                "rtt": {"max_value": {"value": "100ms", "source_type": "Turn", "source_ref": "U2"}}
                            }
                        }
                    ]
                }
            ]
        }

    # ==================== S03: Reinforcement Main ====================
    @staticmethod
    def _render_s03(plan, persona, memory_store):
        return {
            "session_id": plan["session_id"],
            "user_id": plan["user_id"],
            "reference_time": plan["reference_time"],
            "session_meta": {
                "template_id": plan["template_id"],
                "round_count": 2,
                "intent_count": 1,
                "memory_role": plan["memory_role"],
                "skeleton_signature": "T2-1|2|1|I1:抖音/开直播/1/memory_filled/resolved|none|Memory,Memory,Knowledge,Memory,Turn,Turn,Turn|none",
                "scenario": {"environment": "转场大巴刚到市体育馆", "persona_tone": "坚毅利索", "memory_action": "reinforce_main_memory"}
            },
            "event_sequence": [
                {
                    "turn": 1,
                    "user": {
                        "utterance": "大巴刚到市体育馆，今天周三两点巡讲现场开播，直接按老规矩帮我保上，保两个小时！",
                        "action_types": ["Create_Intent_Request", "Inform_Slot"]
                    },
                    "agent": {
                        "utterance": "收到！已按您周三巡讲的常用偏好规划：抖音开直播，画质1080p，时延上限50毫秒，保障时间为今天14:00到16:00。请确认是否立即开通？",
                        "action_types": ["Confirm_Slot"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                },
                {
                    "turn": 2,
                    "user": {
                        "utterance": "对，就是这样，赶紧开通吧，马上要进场了。",
                        "action_types": ["Confirm_Slot"]
                    },
                    "agent": {
                        "utterance": "好的，已成功为您开启抖音开直播网络保障（1080p / 时延≤50ms），祝您今天的励志巡讲圆满顺利！",
                        "action_types": ["Acknowledge"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                }
            ],
            "intents": [
                {
                    "intent_id": "I1",
                    "status": "resolved",
                    "closure_path": "memory_filled",
                    "expression_level": 1,
                    "intent": "抖音开直播保障",
                    "params": {
                        "application_name": {"value": "抖音", "source_type": "Memory", "source_ref": "MF_001"},
                        "service_name": {"value": "开直播", "source_type": "Memory", "source_ref": "MF_001"},
                        "resolution": {"min_value": {"value": "1080p", "source_type": "Memory", "source_ref": "MF_001"}},
                        "rtt": {"max_value": {"value": "50ms", "source_type": "Memory", "source_ref": "MF_001"}},
                        "timestamp": {
                            "start_timestamp": {"value": "2026年10月14日14时00分", "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": "2026年10月14日16时00分", "source_type": "Turn", "source_ref": "U1"},
                            "duration": {"value": "120min", "source_type": "Context", "source_ref": "U1"}
                        }
                    }
                }
            ],
            "relations": [],
            "slot_updates": [
                {
                    "intent_id": "I1",
                    "turn_updates": [
                        {
                            "turn": 1,
                            "params": {
                                "application_name": {"value": "抖音", "source_type": "Memory", "source_ref": "MF_001"},
                                "service_name": {"value": "开直播", "source_type": "Memory", "source_ref": "MF_001"},
                                "resolution": {"min_value": {"value": "1080p", "source_type": "Memory", "source_ref": "MF_001"}},
                                "rtt": {"max_value": {"value": "50ms", "source_type": "Memory", "source_ref": "MF_001"}},
                                "timestamp": {
                                    "start_timestamp": {"value": "2026年10月14日14时00分", "source_type": "Turn", "source_ref": "U1"},
                                    "end_timestamp": {"value": "2026年10月14日16时00分", "source_type": "Turn", "source_ref": "U1"}
                                }
                            }
                        },
                        {"turn": 2, "params": {}}
                    ]
                }
            ]
        }

    # ==================== S04: Evidence Sub 2 ====================
    @staticmethod
    def _render_s04(plan, persona, memory_store):
        sub_02 = persona["dynamic_profile"]["sub_storylines"][1]
        memory_store["SUB_002"] = {
            "application_name": sub_02["application_name"],
            "service_name": sub_02["service_name"],
            "resolution": sub_02["preferred_params"]["resolution"],
            "rtt": sub_02["preferred_params"]["rtt_max"],
            "alias": sub_02["aliases"]["service_aliases"][0],
            "scope": "hotel_evening_review",
            "declared_at": plan["reference_time"]
        }
        return {
            "session_id": plan["session_id"],
            "user_id": plan["user_id"],
            "reference_time": plan["reference_time"],
            "session_meta": {
                "template_id": plan["template_id"],
                "round_count": 2,
                "intent_count": 1,
                "memory_role": plan["memory_role"],
                "skeleton_signature": "T2-1|2|1|I1:快手/看直播/1/clarified/resolved|none|Turn,Turn,Knowledge,Turn,Turn,Turn,Turn|none",
                "scenario": {"environment": "驻地酒店休息区", "persona_tone": "专注严谨", "memory_action": "establish_sub_storyline_2"}
            },
            "event_sequence": [
                {
                    "turn": 1,
                    "user": {
                        "utterance": "刚回酒店，今晚8点15到9点45，我要在快手看赛事录像复盘，给运动员分析滑雪过旗门动作，帮我保一下观赛网络。",
                        "action_types": ["Create_Intent_Request", "Inform_Slot"]
                    },
                    "agent": {
                        "utterance": "收到，已定位快手看直播保障。请问对画质清晰度和时延有什么具体要求呢？",
                        "action_types": ["Request_Slot"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": ["resolution", "rtt"]
                },
                {
                    "turn": 2,
                    "user": {
                        "utterance": "看动作细节画质必须超清1080P，时延80毫秒内别频繁缓冲就行，一个半小时抓紧开通。",
                        "action_types": ["Fill_Missing_Slot"]
                    },
                    "agent": {
                        "utterance": "好的，已为您受理快手看直播（录像复盘）网络保障：分辨率1080p，时延上限80毫秒，保障时间为今晚20:15到21:45，共1.5小时，祝您复盘顺利！",
                        "action_types": ["Acknowledge"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                }
            ],
            "intents": [
                {
                    "intent_id": "I1",
                    "status": "resolved",
                    "closure_path": "clarified",
                    "expression_level": 1,
                    "intent": "快手看直播保障",
                    "params": {
                        "application_name": {"value": "快手", "source_type": "Turn", "source_ref": "U1"},
                        "service_name": {"value": "看直播", "source_type": "Turn", "source_ref": "U1"},
                        "resolution": {"min_value": {"value": "1080p", "source_type": "Turn", "source_ref": "U2"}},
                        "rtt": {"max_value": {"value": "80ms", "source_type": "Turn", "source_ref": "U2"}},
                        "timestamp": {
                            "start_timestamp": {"value": "2026年10月15日20时15分", "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": "2026年10月15日21时45分", "source_type": "Turn", "source_ref": "U1"},
                            "duration": {"value": "90min", "source_type": "Context", "source_ref": "U1"}
                        }
                    }
                }
            ],
            "relations": [],
            "slot_updates": [
                {
                    "intent_id": "I1",
                    "turn_updates": [
                        {
                            "turn": 1,
                            "params": {
                                "application_name": {"value": "快手", "source_type": "Turn", "source_ref": "U1"},
                                "service_name": {"value": "看直播", "source_type": "Turn", "source_ref": "U1"},
                                "timestamp": {
                                    "start_timestamp": {"value": "2026年10月15日20时15分", "source_type": "Turn", "source_ref": "U1"},
                                    "end_timestamp": {"value": "2026年10月15日21时45分", "source_type": "Turn", "source_ref": "U1"}
                                }
                            }
                        },
                        {
                            "turn": 2,
                            "params": {
                                "resolution": {"min_value": {"value": "1080p", "source_type": "Turn", "source_ref": "U2"}},
                                "rtt": {"max_value": {"value": "80ms", "source_type": "Turn", "source_ref": "U2"}}
                            }
                        }
                    ]
                }
            ]
        }

    # ==================== S05: Distractor 1 ====================
    @staticmethod
    def _render_s05(plan, persona, memory_store):
        return {
            "session_id": plan["session_id"],
            "user_id": plan["user_id"],
            "reference_time": plan["reference_time"],
            "session_meta": {
                "template_id": plan["template_id"],
                "round_count": 1,
                "intent_count": 1,
                "memory_role": plan["memory_role"],
                "skeleton_signature": "T1-1|1|1|I1:腾讯会议/会议/1/direct/resolved|none|Turn,Turn,Knowledge,Turn,Turn,Turn,Turn|none",
                "scenario": {"environment": "酒店休息区", "persona_tone": "明确简短", "memory_action": "distractor_no_memory"}
            },
            "event_sequence": [
                {
                    "turn": 1,
                    "user": {
                        "utterance": "在酒店临时用腾讯会议听个半小时宣讲通气会，时间今天上午10点到10点半，画质标清720p，时延80毫秒内就行，直接办吧。",
                        "action_types": ["Create_Intent_Request", "Inform_Slot"]
                    },
                    "agent": {
                        "utterance": "好的，已为您受理腾讯会议网络保障：分辨率720p，时延上限80毫秒，保障时间从今天10:00到10:30，时长30分钟。",
                        "action_types": ["Acknowledge"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                }
            ],
            "intents": [
                {
                    "intent_id": "I1",
                    "status": "resolved",
                    "closure_path": "direct",
                    "expression_level": 1,
                    "intent": "腾讯会议保障",
                    "params": {
                        "application_name": {"value": "腾讯会议", "source_type": "Turn", "source_ref": "U1"},
                        "service_name": {"value": "会议", "source_type": "Turn", "source_ref": "U1"},
                        "resolution": {"min_value": {"value": "720p", "source_type": "Turn", "source_ref": "U1"}},
                        "rtt": {"max_value": {"value": "80ms", "source_type": "Turn", "source_ref": "U1"}},
                        "timestamp": {
                            "start_timestamp": {"value": "2026年10月18日10时00分", "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": "2026年10月18日10时30分", "source_type": "Turn", "source_ref": "U1"},
                            "duration": {"value": "30min", "source_type": "Context", "source_ref": "U1"}
                        }
                    }
                }
            ],
            "relations": [],
            "slot_updates": [
                {
                    "intent_id": "I1",
                    "turn_updates": [
                        {
                            "turn": 1,
                            "params": {
                                "application_name": {"value": "腾讯会议", "source_type": "Turn", "source_ref": "U1"},
                                "service_name": {"value": "会议", "source_type": "Turn", "source_ref": "U1"},
                                "resolution": {"min_value": {"value": "720p", "source_type": "Turn", "source_ref": "U1"}},
                                "rtt": {"max_value": {"value": "80ms", "source_type": "Turn", "source_ref": "U1"}},
                                "timestamp": {
                                    "start_timestamp": {"value": "2026年10月18日10时00分", "source_type": "Turn", "source_ref": "U1"},
                                    "end_timestamp": {"value": "2026年10月18日10时30分", "source_type": "Turn", "source_ref": "U1"}
                                }
                            }
                        }
                    ]
                }
            ]
        }

    # ==================== S06: Reinforcement Sub 1 ====================
    @staticmethod
    def _render_s06(plan, persona, memory_store):
        return {
            "session_id": plan["session_id"],
            "user_id": plan["user_id"],
            "reference_time": plan["reference_time"],
            "session_meta": {
                "template_id": plan["template_id"],
                "round_count": 2,
                "intent_count": 1,
                "memory_role": plan["memory_role"],
                "skeleton_signature": "T2-1|2|1|I1:微信/视频通话/1/memory_filled/resolved|none|Memory,Memory,Knowledge,Memory,Turn,Turn,Turn|none",
                "scenario": {"environment": "大巴转场途中", "persona_tone": "雷厉风行", "memory_action": "reinforce_sub_storyline_1"}
            },
            "event_sequence": [
                {
                    "turn": 1,
                    "user": {
                        "utterance": "大巴快进隧道了，今晚7点到8点我要跟领队视频碰头，直接保上一个小时！",
                        "action_types": ["Create_Intent_Request", "Inform_Slot"]
                    },
                    "agent": {
                        "utterance": "收到！已按您傍晚转场的常用偏好规划：微信视频通话，画质720p，时延上限100毫秒，时间为19:00到20:00。请确认是否按此开通？",
                        "action_types": ["Confirm_Slot"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                },
                {
                    "turn": 2,
                    "user": {
                        "utterance": "对，就是微信对讲，利索点给我保上！",
                        "action_types": ["Confirm_Slot"]
                    },
                    "agent": {
                        "utterance": "好的，已成功开启微信视频通话保障（720p / 时延≤100ms），保障将在19:00准时生效，祝您对会顺畅！",
                        "action_types": ["Acknowledge"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                }
            ],
            "intents": [
                {
                    "intent_id": "I1",
                    "status": "resolved",
                    "closure_path": "memory_filled",
                    "expression_level": 1,
                    "intent": "微信视频通话保障",
                    "params": {
                        "application_name": {"value": "微信", "source_type": "Memory", "source_ref": "SUB_001"},
                        "service_name": {"value": "视频通话", "source_type": "Memory", "source_ref": "SUB_001"},
                        "resolution": {"min_value": {"value": "720p", "source_type": "Memory", "source_ref": "SUB_001"}},
                        "rtt": {"max_value": {"value": "100ms", "source_type": "Memory", "source_ref": "SUB_001"}},
                        "timestamp": {
                            "start_timestamp": {"value": "2026年10月21日19时00分", "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": "2026年10月21日20时00分", "source_type": "Turn", "source_ref": "U1"},
                            "duration": {"value": "60min", "source_type": "Context", "source_ref": "U1"}
                        }
                    }
                }
            ],
            "relations": [],
            "slot_updates": [
                {
                    "intent_id": "I1",
                    "turn_updates": [
                        {
                            "turn": 1,
                            "params": {
                                "application_name": {"value": "微信", "source_type": "Memory", "source_ref": "SUB_001"},
                                "service_name": {"value": "视频通话", "source_type": "Memory", "source_ref": "SUB_001"},
                                "resolution": {"min_value": {"value": "720p", "source_type": "Memory", "source_ref": "SUB_001"}},
                                "rtt": {"max_value": {"value": "100ms", "source_type": "Memory", "source_ref": "SUB_001"}},
                                "timestamp": {
                                    "start_timestamp": {"value": "2026年10月21日19时00分", "source_type": "Turn", "source_ref": "U1"},
                                    "end_timestamp": {"value": "2026年10月21日20时00分", "source_type": "Turn", "source_ref": "U1"}
                                }
                            }
                        },
                        {"turn": 2, "params": {}}
                    ]
                }
            ]
        }

    # ==================== S07: Reuse Main ====================
    @staticmethod
    def _render_s07(plan, persona, memory_store):
        return {
            "session_id": plan["session_id"],
            "user_id": plan["user_id"],
            "reference_time": plan["reference_time"],
            "session_meta": {
                "template_id": plan["template_id"],
                "round_count": 2,
                "intent_count": 1,
                "memory_role": plan["memory_role"],
                "skeleton_signature": "T2-1|2|1|I1:抖音/开直播/1/memory_filled/resolved|none|Memory,Memory,Knowledge,Memory,Turn,Turn,Turn|none",
                "scenario": {"environment": "周六露天主赛道看台", "persona_tone": "干练果断", "memory_action": "reuse_main_memory"}
            },
            "event_sequence": [
                {
                    "turn": 1,
                    "user": {
                        "utterance": "周六赛道这边观众满了，两点巡讲推流，直接按老规矩保两小时！",
                        "action_types": ["Create_Intent_Request", "Inform_Slot"]
                    },
                    "agent": {
                        "utterance": "收到！已为您调取周六巡讲偏好：抖音开直播，1080p高清，时延50毫秒以内，时间14:00到16:00。请确认是否立即开启？",
                        "action_types": ["Confirm_Slot"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                },
                {
                    "turn": 2,
                    "user": {
                        "utterance": "确认，赶紧开通！",
                        "action_types": ["Confirm_Slot"]
                    },
                    "agent": {
                        "utterance": "好的，已成功开通抖音开直播网络保障（1080p / 时延≤50ms），祝巡讲成功！",
                        "action_types": ["Acknowledge"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                }
            ],
            "intents": [
                {
                    "intent_id": "I1",
                    "status": "resolved",
                    "closure_path": "memory_filled",
                    "expression_level": 1,
                    "intent": "抖音开直播保障",
                    "params": {
                        "application_name": {"value": "抖音", "source_type": "Memory", "source_ref": "MF_001"},
                        "service_name": {"value": "开直播", "source_type": "Memory", "source_ref": "MF_001"},
                        "resolution": {"min_value": {"value": "1080p", "source_type": "Memory", "source_ref": "MF_001"}},
                        "rtt": {"max_value": {"value": "50ms", "source_type": "Memory", "source_ref": "MF_001"}},
                        "timestamp": {
                            "start_timestamp": {"value": "2026年10月24日14时00分", "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": "2026年10月24日16时00分", "source_type": "Turn", "source_ref": "U1"},
                            "duration": {"value": "120min", "source_type": "Context", "source_ref": "U1"}
                        }
                    }
                }
            ],
            "relations": [],
            "slot_updates": [
                {
                    "intent_id": "I1",
                    "turn_updates": [
                        {
                            "turn": 1,
                            "params": {
                                "application_name": {"value": "抖音", "source_type": "Memory", "source_ref": "MF_001"},
                                "service_name": {"value": "开直播", "source_type": "Memory", "source_ref": "MF_001"},
                                "resolution": {"min_value": {"value": "1080p", "source_type": "Memory", "source_ref": "MF_001"}},
                                "rtt": {"max_value": {"value": "50ms", "source_type": "Memory", "source_ref": "MF_001"}},
                                "timestamp": {
                                    "start_timestamp": {"value": "2026年10月24日14时00分", "source_type": "Turn", "source_ref": "U1"},
                                    "end_timestamp": {"value": "2026年10月24日16时00分", "source_type": "Turn", "source_ref": "U1"}
                                }
                            }
                        },
                        {"turn": 2, "params": {}}
                    ]
                }
            ]
        }

    # ==================== S08: Reinforcement Main ====================
    @staticmethod
    def _render_s08(plan, persona, memory_store):
        return {
            "session_id": plan["session_id"],
            "user_id": plan["user_id"],
            "reference_time": plan["reference_time"],
            "session_meta": {
                "template_id": plan["template_id"],
                "round_count": 2,
                "intent_count": 1,
                "memory_role": plan["memory_role"],
                "skeleton_signature": "T2-1|2|1|I1:抖音/开直播/1/memory_filled/resolved|none|Memory,Memory,Knowledge,Memory,Turn,Turn,Turn|none",
                "scenario": {"environment": "周三转场途中", "persona_tone": "熟稔自然", "memory_action": "reinforce_main_memory"}
            },
            "event_sequence": [
                {
                    "turn": 1,
                    "user": {
                        "utterance": "周三下午两点现场开播，按老规矩保一下！",
                        "action_types": ["Create_Intent_Request", "Inform_Slot"]
                    },
                    "agent": {
                        "utterance": "收到！为您配置：抖音开直播，1080p高清，时延50毫秒以内，时间14:00到16:00。请确认是否开启？",
                        "action_types": ["Confirm_Slot"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                },
                {
                    "turn": 2,
                    "user": {
                        "utterance": "对，开通吧。",
                        "action_types": ["Confirm_Slot"]
                    },
                    "agent": {
                        "utterance": "好的，已成功开通保障，祝您巡讲顺利！",
                        "action_types": ["Acknowledge"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                }
            ],
            "intents": [
                {
                    "intent_id": "I1",
                    "status": "resolved",
                    "closure_path": "memory_filled",
                    "expression_level": 1,
                    "intent": "抖音开直播保障",
                    "params": {
                        "application_name": {"value": "抖音", "source_type": "Memory", "source_ref": "MF_001"},
                        "service_name": {"value": "开直播", "source_type": "Memory", "source_ref": "MF_001"},
                        "resolution": {"min_value": {"value": "1080p", "source_type": "Memory", "source_ref": "MF_001"}},
                        "rtt": {"max_value": {"value": "50ms", "source_type": "Memory", "source_ref": "MF_001"}},
                        "timestamp": {
                            "start_timestamp": {"value": "2026年10月28日14时00分", "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": "2026年10月28日16时00分", "source_type": "Turn", "source_ref": "U1"},
                            "duration": {"value": "120min", "source_type": "Context", "source_ref": "U1"}
                        }
                    }
                }
            ],
            "relations": [],
            "slot_updates": [
                {
                    "intent_id": "I1",
                    "turn_updates": [
                        {
                            "turn": 1,
                            "params": {
                                "application_name": {"value": "抖音", "source_type": "Memory", "source_ref": "MF_001"},
                                "service_name": {"value": "开直播", "source_type": "Memory", "source_ref": "MF_001"},
                                "resolution": {"min_value": {"value": "1080p", "source_type": "Memory", "source_ref": "MF_001"}},
                                "rtt": {"max_value": {"value": "50ms", "source_type": "Memory", "source_ref": "MF_001"}},
                                "timestamp": {
                                    "start_timestamp": {"value": "2026年10月28日14时00分", "source_type": "Turn", "source_ref": "U1"},
                                    "end_timestamp": {"value": "2026年10月28日16时00分", "source_type": "Turn", "source_ref": "U1"}
                                }
                            }
                        },
                        {"turn": 2, "params": {}}
                    ]
                }
            ]
        }

    # ==================== S09: Reinforcement Sub 2 ====================
    @staticmethod
    def _render_s09(plan, persona, memory_store):
        return {
            "session_id": plan["session_id"],
            "user_id": plan["user_id"],
            "reference_time": plan["reference_time"],
            "session_meta": {
                "template_id": plan["template_id"],
                "round_count": 2,
                "intent_count": 1,
                "memory_role": plan["memory_role"],
                "skeleton_signature": "T2-1|2|1|I1:快手/看直播/1/memory_filled/resolved|none|Memory,Memory,Knowledge,Memory,Turn,Turn,Turn|none",
                "scenario": {"environment": "酒店复盘赛事", "persona_tone": "严谨专注", "memory_action": "reinforce_sub_storyline_2"}
            },
            "event_sequence": [
                {
                    "turn": 1,
                    "user": {
                        "utterance": "今晚8点半到10点，我要在快手看录像复盘，按上次标准保一个半小时。",
                        "action_types": ["Create_Intent_Request", "Inform_Slot"]
                    },
                    "agent": {
                        "utterance": "收到！已按您晚间复盘偏好规划：快手看直播，画质1080p超清，时延80毫秒内，时间20:30到22:00。请确认是否开启？",
                        "action_types": ["Confirm_Slot"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                },
                {
                    "turn": 2,
                    "user": {
                        "utterance": "对，就是这个配置，保上吧。",
                        "action_types": ["Confirm_Slot"]
                    },
                    "agent": {
                        "utterance": "好的，快手看直播保障已就绪（1080p / 时延≤80ms），祝复盘顺利！",
                        "action_types": ["Acknowledge"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                }
            ],
            "intents": [
                {
                    "intent_id": "I1",
                    "status": "resolved",
                    "closure_path": "memory_filled",
                    "expression_level": 1,
                    "intent": "快手看直播保障",
                    "params": {
                        "application_name": {"value": "快手", "source_type": "Memory", "source_ref": "SUB_002"},
                        "service_name": {"value": "看直播", "source_type": "Memory", "source_ref": "SUB_002"},
                        "resolution": {"min_value": {"value": "1080p", "source_type": "Memory", "source_ref": "SUB_002"}},
                        "rtt": {"max_value": {"value": "80ms", "source_type": "Memory", "source_ref": "SUB_002"}},
                        "timestamp": {
                            "start_timestamp": {"value": "2026年10月29日20时30分", "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": "2026年10月29日22时00分", "source_type": "Turn", "source_ref": "U1"},
                            "duration": {"value": "90min", "source_type": "Context", "source_ref": "U1"}
                        }
                    }
                }
            ],
            "relations": [],
            "slot_updates": [
                {
                    "intent_id": "I1",
                    "turn_updates": [
                        {
                            "turn": 1,
                            "params": {
                                "application_name": {"value": "快手", "source_type": "Memory", "source_ref": "SUB_002"},
                                "service_name": {"value": "看直播", "source_type": "Memory", "source_ref": "SUB_002"},
                                "resolution": {"min_value": {"value": "1080p", "source_type": "Memory", "source_ref": "SUB_002"}},
                                "rtt": {"max_value": {"value": "80ms", "source_type": "Memory", "source_ref": "SUB_002"}},
                                "timestamp": {
                                    "start_timestamp": {"value": "2026年10月29日20时30分", "source_type": "Turn", "source_ref": "U1"},
                                    "end_timestamp": {"value": "2026年10月29日22时00分", "source_type": "Turn", "source_ref": "U1"}
                                }
                            }
                        },
                        {"turn": 2, "params": {}}
                    ]
                }
            ]
        }

    # ==================== S10: Distractor 2 ====================
    @staticmethod
    def _render_s10(plan, persona, memory_store):
        return {
            "session_id": plan["session_id"],
            "user_id": plan["user_id"],
            "reference_time": plan["reference_time"],
            "session_meta": {
                "template_id": plan["template_id"],
                "round_count": 1,
                "intent_count": 1,
                "memory_role": plan["memory_role"],
                "skeleton_signature": "T1-1|1|1|I1:微信/短视频/1/direct/resolved|none|Turn,Turn,Knowledge,Turn,Turn,Turn,Turn|none",
                "scenario": {"environment": "午休刷短视频", "persona_tone": "随性明确", "memory_action": "distractor_no_memory"}
            },
            "event_sequence": [
                {
                    "turn": 1,
                    "user": {
                        "utterance": "中午休息用微信刷一个小时短视频，从12点半到1点半，画质720p，时延80毫秒就行，直接办上。",
                        "action_types": ["Create_Intent_Request", "Inform_Slot"]
                    },
                    "agent": {
                        "utterance": "好的，已为您受理微信短视频保障：清晰度720p，时延上限80毫秒，保障时间为今天12:30到13:30，时长1小时。",
                        "action_types": ["Acknowledge"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                }
            ],
            "intents": [
                {
                    "intent_id": "I1",
                    "status": "resolved",
                    "closure_path": "direct",
                    "expression_level": 1,
                    "intent": "微信短视频保障",
                    "params": {
                        "application_name": {"value": "微信", "source_type": "Turn", "source_ref": "U1"},
                        "service_name": {"value": "短视频", "source_type": "Turn", "source_ref": "U1"},
                        "resolution": {"min_value": {"value": "720p", "source_type": "Turn", "source_ref": "U1"}},
                        "rtt": {"max_value": {"value": "80ms", "source_type": "Turn", "source_ref": "U1"}},
                        "timestamp": {
                            "start_timestamp": {"value": "2026年11月01日12时30分", "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": "2026年11月01日13时30分", "source_type": "Turn", "source_ref": "U1"},
                            "duration": {"value": "60min", "source_type": "Context", "source_ref": "U1"}
                        }
                    }
                }
            ],
            "relations": [],
            "slot_updates": [
                {
                    "intent_id": "I1",
                    "turn_updates": [
                        {
                            "turn": 1,
                            "params": {
                                "application_name": {"value": "微信", "source_type": "Turn", "source_ref": "U1"},
                                "service_name": {"value": "短视频", "source_type": "Turn", "source_ref": "U1"},
                                "resolution": {"min_value": {"value": "720p", "source_type": "Turn", "source_ref": "U1"}},
                                "rtt": {"max_value": {"value": "80ms", "source_type": "Turn", "source_ref": "U1"}},
                                "timestamp": {
                                    "start_timestamp": {"value": "2026年11月01日12时30分", "source_type": "Turn", "source_ref": "U1"},
                                    "end_timestamp": {"value": "2026年11月01日13时30分", "source_type": "Turn", "source_ref": "U1"}
                                }
                            }
                        }
                    ]
                }
            ]
        }

    # ==================== S11: Correction ====================
    @staticmethod
    def _render_s11(plan, persona, memory_store):
        memory_store["MF_001_v2"] = {
            "application_name": "抖音",
            "service_name": "开直播",
            "resolution": "720p",
            "rtt": "30ms",
            "alias": "巡讲推流",
            "scope": "winter_games_temporary",
            "valid_from": "2026-11-01",
            "valid_to": "2026-11-15",
            "updated_at": plan["reference_time"]
        }
        return {
            "session_id": plan["session_id"],
            "user_id": plan["user_id"],
            "reference_time": plan["reference_time"],
            "session_meta": {
                "template_id": plan["template_id"],
                "round_count": 2,
                "intent_count": 1,
                "memory_role": plan["memory_role"],
                "skeleton_signature": "T2-3|2|1|I1:抖音/开直播/1/corrected/resolved|none|Memory,Memory,Knowledge,Turn,Turn,Turn,Turn|none",
                "scenario": {"environment": "雪场户外严寒与风雪", "persona_tone": "严肃果断", "memory_action": "override_temporary_preference"}
            },
            "event_sequence": [
                {
                    "turn": 1,
                    "user": {
                        "utterance": "雪场山顶风大得吓人，气温低手都僵了。下午两点巡讲现场开播保两个小时，按老规矩保上！",
                        "action_types": ["Create_Intent_Request", "Inform_Slot"]
                    },
                    "agent": {
                        "utterance": "收到，正为您按常用偏好配置：抖音开直播，1080p高清，时延50毫秒以内，保障时间14:00至16:00，请问确认开通吗？",
                        "action_types": ["Confirm_Slot"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                },
                {
                    "turn": 2,
                    "user": {
                        "utterance": "等等，不行！山顶风雪太大信号忽强忽弱，1080P扛不住会卡死。这次残运巡回选拔赛期间（15号前），巡讲推流全部改成720P标清，但时延必须压在30毫秒以内防抖抗抖，抓紧改过来！",
                        "action_types": ["Modify_Slot", "Confirm_Slot"]
                    },
                    "agent": {
                        "utterance": "明白！已为您紧急切换为赛事防抖保障模式：画质调整为720p，时延收紧至30毫秒以内，时间14:00至16:00。该临时规则在11月15日赛事结束前持续生效！",
                        "action_types": ["Acknowledge"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                }
            ],
            "intents": [
                {
                    "intent_id": "I1",
                    "status": "resolved",
                    "closure_path": "corrected",
                    "expression_level": 1,
                    "intent": "抖音开直播保障",
                    "params": {
                        "application_name": {"value": "抖音", "source_type": "Memory", "source_ref": "MF_001"},
                        "service_name": {"value": "开直播", "source_type": "Memory", "source_ref": "MF_001"},
                        "resolution": {"min_value": {"value": "720p", "source_type": "Turn", "source_ref": "U2"}},
                        "rtt": {"max_value": {"value": "30ms", "source_type": "Turn", "source_ref": "U2"}},
                        "timestamp": {
                            "start_timestamp": {"value": "2026年11月04日14时00分", "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": "2026年11月04日16时00分", "source_type": "Turn", "source_ref": "U1"},
                            "duration": {"value": "120min", "source_type": "Context", "source_ref": "U1"}
                        }
                    }
                }
            ],
            "relations": [],
            "slot_updates": [
                {
                    "intent_id": "I1",
                    "turn_updates": [
                        {
                            "turn": 1,
                            "params": {
                                "application_name": {"value": "抖音", "source_type": "Memory", "source_ref": "MF_001"},
                                "service_name": {"value": "开直播", "source_type": "Memory", "source_ref": "MF_001"},
                                "resolution": {"min_value": {"value": "1080p", "source_type": "Memory", "source_ref": "MF_001"}},
                                "rtt": {"max_value": {"value": "50ms", "source_type": "Memory", "source_ref": "MF_001"}},
                                "timestamp": {
                                    "start_timestamp": {"value": "2026年11月04日14时00分", "source_type": "Turn", "source_ref": "U1"},
                                    "end_timestamp": {"value": "2026年11月04日16时00分", "source_type": "Turn", "source_ref": "U1"}
                                }
                            }
                        },
                        {
                            "turn": 2,
                            "params": {
                                "resolution": {"min_value": {"value": "720p", "source_type": "Turn", "source_ref": "U2"}},
                                "rtt": {"max_value": {"value": "30ms", "source_type": "Turn", "source_ref": "U2"}}
                            }
                        }
                    ]
                }
            ]
        }

    # ==================== S12: Reuse Main (Temporary Event) ====================
    @staticmethod
    def _render_s12(plan, persona, memory_store):
        return {
            "session_id": plan["session_id"],
            "user_id": plan["user_id"],
            "reference_time": plan["reference_time"],
            "session_meta": {
                "template_id": plan["template_id"],
                "round_count": 2,
                "intent_count": 1,
                "memory_role": plan["memory_role"],
                "skeleton_signature": "T2-1|2|1|I1:抖音/开直播/1/memory_filled/resolved|none|Memory,Memory,Knowledge,Memory,Turn,Turn,Turn|none",
                "scenario": {"environment": "雪场终点赛事集结区", "persona_tone": "干练果断", "memory_action": "reuse_temporary_preference"}
            },
            "event_sequence": [
                {
                    "turn": 1,
                    "user": {
                        "utterance": "马上到雪场终点集结区了，今天周六两点巡讲现场开播，直接按赛事保障模式保两个小时！",
                        "action_types": ["Create_Intent_Request", "Inform_Slot"]
                    },
                    "agent": {
                        "utterance": "收到！结合残运赛事临时保障规则，已为您调取配置：抖音开直播，画质720p，时延压制在30毫秒内，保障时间为今天14:00到16:00。请确认是否立即开启？",
                        "action_types": ["Confirm_Slot"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                },
                {
                    "turn": 2,
                    "user": {
                        "utterance": "对，就按这个赛事模式来，利索点给我保上！",
                        "action_types": ["Confirm_Slot"]
                    },
                    "agent": {
                        "utterance": "好的，已成功开启抖音赛事超低时延直播保障（720p / 时延≤30ms），全力护航您的现场巡讲！",
                        "action_types": ["Acknowledge"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                }
            ],
            "intents": [
                {
                    "intent_id": "I1",
                    "status": "resolved",
                    "closure_path": "memory_filled",
                    "expression_level": 1,
                    "intent": "抖音开直播保障",
                    "params": {
                        "application_name": {"value": "抖音", "source_type": "Memory", "source_ref": "MF_001_v2"},
                        "service_name": {"value": "开直播", "source_type": "Memory", "source_ref": "MF_001_v2"},
                        "resolution": {"min_value": {"value": "720p", "source_type": "Memory", "source_ref": "MF_001_v2"}},
                        "rtt": {"max_value": {"value": "30ms", "source_type": "Memory", "source_ref": "MF_001_v2"}},
                        "timestamp": {
                            "start_timestamp": {"value": "2026年11月07日14时00分", "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": "2026年11月07日16时00分", "source_type": "Turn", "source_ref": "U1"},
                            "duration": {"value": "120min", "source_type": "Context", "source_ref": "U1"}
                        }
                    }
                }
            ],
            "relations": [],
            "slot_updates": [
                {
                    "intent_id": "I1",
                    "turn_updates": [
                        {
                            "turn": 1,
                            "params": {
                                "application_name": {"value": "抖音", "source_type": "Memory", "source_ref": "MF_001_v2"},
                                "service_name": {"value": "开直播", "source_type": "Memory", "source_ref": "MF_001_v2"},
                                "resolution": {"min_value": {"value": "720p", "source_type": "Memory", "source_ref": "MF_001_v2"}},
                                "rtt": {"max_value": {"value": "30ms", "source_type": "Memory", "source_ref": "MF_001_v2"}},
                                "timestamp": {
                                    "start_timestamp": {"value": "2026年11月07日14时00分", "source_type": "Turn", "source_ref": "U1"},
                                    "end_timestamp": {"value": "2026年11月07日16时00分", "source_type": "Turn", "source_ref": "U1"}
                                }
                            }
                        },
                        {"turn": 2, "params": {}}
                    ]
                }
            ]
        }

    # ==================== S13: Reuse Sub 1 ====================
    @staticmethod
    def _render_s13(plan, persona, memory_store):
        return {
            "session_id": plan["session_id"],
            "user_id": plan["user_id"],
            "reference_time": plan["reference_time"],
            "session_meta": {
                "template_id": plan["template_id"],
                "round_count": 2,
                "intent_count": 1,
                "memory_role": plan["memory_role"],
                "skeleton_signature": "T2-1|2|1|I1:微信/视频通话/1/memory_filled/resolved|none|Memory,Memory,Knowledge,Memory,Turn,Turn,Turn|none",
                "scenario": {"environment": "赛事转场大巴", "persona_tone": "干练利索", "memory_action": "sub_memory_unaffected"}
            },
            "event_sequence": [
                {
                    "turn": 1,
                    "user": {
                        "utterance": "转场大巴快开了，今晚7点到8点跟领队视频碰头，按老规矩保上！",
                        "action_types": ["Create_Intent_Request", "Inform_Slot"]
                    },
                    "agent": {
                        "utterance": "收到！已为您调取视频调度常用偏好：微信视频通话，画质720p，时延上限100毫秒，时间为19:00到20:00。请确认是否开启？",
                        "action_types": ["Confirm_Slot"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                },
                {
                    "turn": 2,
                    "user": {
                        "utterance": "对，就是微信对讲，直接开通吧。",
                        "action_types": ["Confirm_Slot"]
                    },
                    "agent": {
                        "utterance": "好的，已成功开通微信视频通话保障，祝您沟通顺畅！",
                        "action_types": ["Acknowledge"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                }
            ],
            "intents": [
                {
                    "intent_id": "I1",
                    "status": "resolved",
                    "closure_path": "memory_filled",
                    "expression_level": 1,
                    "intent": "微信视频通话保障",
                    "params": {
                        "application_name": {"value": "微信", "source_type": "Memory", "source_ref": "SUB_001"},
                        "service_name": {"value": "视频通话", "source_type": "Memory", "source_ref": "SUB_001"},
                        "resolution": {"min_value": {"value": "720p", "source_type": "Memory", "source_ref": "SUB_001"}},
                        "rtt": {"max_value": {"value": "100ms", "source_type": "Memory", "source_ref": "SUB_001"}},
                        "timestamp": {
                            "start_timestamp": {"value": "2026年11月11日19时00分", "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": "2026年11月11日20时00分", "source_type": "Turn", "source_ref": "U1"},
                            "duration": {"value": "60min", "source_type": "Context", "source_ref": "U1"}
                        }
                    }
                }
            ],
            "relations": [],
            "slot_updates": [
                {
                    "intent_id": "I1",
                    "turn_updates": [
                        {
                            "turn": 1,
                            "params": {
                                "application_name": {"value": "微信", "source_type": "Memory", "source_ref": "SUB_001"},
                                "service_name": {"value": "视频通话", "source_type": "Memory", "source_ref": "SUB_001"},
                                "resolution": {"min_value": {"value": "720p", "source_type": "Memory", "source_ref": "SUB_001"}},
                                "rtt": {"max_value": {"value": "100ms", "source_type": "Memory", "source_ref": "SUB_001"}},
                                "timestamp": {
                                    "start_timestamp": {"value": "2026年11月11日19时00分", "source_type": "Turn", "source_ref": "U1"},
                                    "end_timestamp": {"value": "2026年11月11日20时00分", "source_type": "Turn", "source_ref": "U1"}
                                }
                            }
                        },
                        {"turn": 2, "params": {}}
                    ]
                }
            ]
        }

    # ==================== S14: Distractor 1 ====================
    @staticmethod
    def _render_s14(plan, persona, memory_store):
        return {
            "session_id": plan["session_id"],
            "user_id": plan["user_id"],
            "reference_time": plan["reference_time"],
            "session_meta": {
                "template_id": plan["template_id"],
                "round_count": 1,
                "intent_count": 1,
                "memory_role": plan["memory_role"],
                "skeleton_signature": "T1-1|1|1|I1:腾讯会议/会议/1/direct/resolved|none|Turn,Turn,Knowledge,Turn,Turn,Turn,Turn|none",
                "scenario": {"environment": "赛事闭幕总结会", "persona_tone": "明确简短", "memory_action": "distractor_no_memory"}
            },
            "event_sequence": [
                {
                    "turn": 1,
                    "user": {
                        "utterance": "今天残运赛事闭幕，在酒店用腾讯会议听半小时总结会，10点到10点半，画质720p，时延80毫秒内，直接开通。",
                        "action_types": ["Create_Intent_Request", "Inform_Slot"]
                    },
                    "agent": {
                        "utterance": "好的，已为您受理腾讯会议网络保障：分辨率720p，时延上限80毫秒，保障时间为今天10:00到10:30，时长30分钟。",
                        "action_types": ["Acknowledge"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                }
            ],
            "intents": [
                {
                    "intent_id": "I1",
                    "status": "resolved",
                    "closure_path": "direct",
                    "expression_level": 1,
                    "intent": "腾讯会议保障",
                    "params": {
                        "application_name": {"value": "腾讯会议", "source_type": "Turn", "source_ref": "U1"},
                        "service_name": {"value": "会议", "source_type": "Turn", "source_ref": "U1"},
                        "resolution": {"min_value": {"value": "720p", "source_type": "Turn", "source_ref": "U1"}},
                        "rtt": {"max_value": {"value": "80ms", "source_type": "Turn", "source_ref": "U1"}},
                        "timestamp": {
                            "start_timestamp": {"value": "2026年11月15日10时00分", "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": "2026年11月15日10时30分", "source_type": "Turn", "source_ref": "U1"},
                            "duration": {"value": "30min", "source_type": "Context", "source_ref": "U1"}
                        }
                    }
                }
            ],
            "relations": [],
            "slot_updates": [
                {
                    "intent_id": "I1",
                    "turn_updates": [
                        {
                            "turn": 1,
                            "params": {
                                "application_name": {"value": "腾讯会议", "source_type": "Turn", "source_ref": "U1"},
                                "service_name": {"value": "会议", "source_type": "Turn", "source_ref": "U1"},
                                "resolution": {"min_value": {"value": "720p", "source_type": "Turn", "source_ref": "U1"}},
                                "rtt": {"max_value": {"value": "80ms", "source_type": "Turn", "source_ref": "U1"}},
                                "timestamp": {
                                    "start_timestamp": {"value": "2026年11月15日10时00分", "source_type": "Turn", "source_ref": "U1"},
                                    "end_timestamp": {"value": "2026年11月15日10时30分", "source_type": "Turn", "source_ref": "U1"}
                                }
                            }
                        }
                    ]
                }
            ]
        }

    # ==================== S15: Reuse Main Recovery ====================
    @staticmethod
    def _render_s15(plan, persona, memory_store):
        # 赛事临时规则已过期，Agent 智能识别并提示恢复原长期偏好 1080p + 50ms
        return {
            "session_id": plan["session_id"],
            "user_id": plan["user_id"],
            "reference_time": plan["reference_time"],
            "session_meta": {
                "template_id": plan["template_id"],
                "round_count": 2,
                "intent_count": 1,
                "memory_role": plan["memory_role"],
                "skeleton_signature": "T2-1|2|1|I1:抖音/开直播/1/memory_filled/resolved|none|Memory,Memory,Knowledge,Memory,Turn,Turn,Turn|none",
                "scenario": {"environment": "赛事结束恢复日常看台", "persona_tone": "豪爽果断", "memory_action": "recover_long_term_rule"}
            },
            "event_sequence": [
                {
                    "turn": 1,
                    "user": {
                        "utterance": "赛事全部圆满结束了！今天周三下午两点常规巡讲现场开播，按老规矩保两个小时！",
                        "action_types": ["Create_Intent_Request", "Inform_Slot"]
                    },
                    "agent": {
                        "utterance": "恭喜赛事圆满收官！检测到残运临时赛事保障已于15号到期，为您恢复常规周三巡讲偏好：抖音开直播，画质1080p全高清，时延50毫秒以内，时间14:00到16:00。请确认是否按此恢复开启？",
                        "action_types": ["Confirm_Slot"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                },
                {
                    "turn": 2,
                    "user": {
                        "utterance": "对，太对了！恢复常规高清标准，赶紧开通吧！",
                        "action_types": ["Confirm_Slot"]
                    },
                    "agent": {
                        "utterance": "好的，已成功恢复并开启抖音开直播常规高清保障（1080p / 时延≤50ms），祝巡回演讲继续精彩！",
                        "action_types": ["Acknowledge"]
                    },
                    "related_intent_ids": ["I1"],
                    "requested_params": []
                }
            ],
            "intents": [
                {
                    "intent_id": "I1",
                    "status": "resolved",
                    "closure_path": "memory_filled",
                    "expression_level": 1,
                    "intent": "抖音开直播保障",
                    "params": {
                        "application_name": {"value": "抖音", "source_type": "Memory", "source_ref": "MF_001"},
                        "service_name": {"value": "开直播", "source_type": "Memory", "source_ref": "MF_001"},
                        "resolution": {"min_value": {"value": "1080p", "source_type": "Memory", "source_ref": "MF_001"}},
                        "rtt": {"max_value": {"value": "50ms", "source_type": "Memory", "source_ref": "MF_001"}},
                        "timestamp": {
                            "start_timestamp": {"value": "2026年11月18日14时00分", "source_type": "Turn", "source_ref": "U1"},
                            "end_timestamp": {"value": "2026年11月18日16时00分", "source_type": "Turn", "source_ref": "U1"},
                            "duration": {"value": "120min", "source_type": "Context", "source_ref": "U1"}
                        }
                    }
                }
            ],
            "relations": [],
            "slot_updates": [
                {
                    "intent_id": "I1",
                    "turn_updates": [
                        {
                            "turn": 1,
                            "params": {
                                "application_name": {"value": "抖音", "source_type": "Memory", "source_ref": "MF_001"},
                                "service_name": {"value": "开直播", "source_type": "Memory", "source_ref": "MF_001"},
                                "resolution": {"min_value": {"value": "1080p", "source_type": "Memory", "source_ref": "MF_001"}},
                                "rtt": {"max_value": {"value": "50ms", "source_type": "Memory", "source_ref": "MF_001"}},
                                "timestamp": {
                                    "start_timestamp": {"value": "2026年11月18日14时00分", "source_type": "Turn", "source_ref": "U1"},
                                    "end_timestamp": {"value": "2026年11月18日16时00分", "source_type": "Turn", "source_ref": "U1"}
                                }
                            }
                        },
                        {"turn": 2, "params": {}}
                    ]
                }
            ]
        }
