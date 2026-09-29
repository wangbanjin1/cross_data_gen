import copy


def _small_memory_mapping(small: dict) -> dict:
    """将规划的小记忆写成可解释的结构；业务维度保存业务到默认应用的映射。"""
    if small.get("type") == "service_default_app":
        return {
            "service_default_apps": [{
                "service_name": small.get("value"),
                "application_name": small.get("normalized_value"),
                "scope_condition": small.get("scope_condition"),
            }]
        }
    if small.get("alias_key") and small.get("value"):
        return {small["alias_key"]: [small["value"]]}
    return {}

class MemoryTracker:
    """
    记忆状态演进追踪器 (MemoryTracker)
    负责精确追踪整个生命周期中跨会话记忆的状态演进。
    计算：
      1. memory_snapshot_before: 会话发生前已生效的记忆集合
      2. memory_events_after: 本次会话触发的记忆事件（新增、强化、纠正、过期恢复、无关）
      3. gold_memory_state_after: 会话发生后的最新真值记忆集合
    """

    def __init__(self):
        self.active_memories = {}

    def get_snapshot_before(self) -> dict:
        return copy.deepcopy(self.active_memories)

    def process_session(self, s_plan: dict) -> tuple[dict, list[dict], dict]:
        snapshot_before = self.get_snapshot_before()
        b_type = s_plan["blueprint_type"]
        role = s_plan["memory_role"]
        tp = s_plan["target_params"]
        ref_time = s_plan["reference_time"]
        memory_events = []

        decl_mode = s_plan.get("declaration_mode", "explicit_declaration")

        if b_type == "main":
            trig_type = s_plan.get("storyline_trigger_type", "time_periodic")
            trig_cond = s_plan.get("trigger_condition", "每周常规周期时段")
            scope_val = "weekly_cycle" if trig_type == "time_periodic" else ("task_mission" if trig_type == "task_activity" else "location_boundary")

            small = s_plan.get("small_memory", {})
            selected_alias_map = _small_memory_mapping(small)

            if role == "evidence_session":
                if decl_mode == "explicit_declaration":
                    # 主线记忆显式初建 (One-shot)
                    mem_item = {
                        "memory_id": "MF_001",
                        "category": "periodic_main_storyline",
                        "storyline_trigger_type": trig_type,
                        "trigger_condition": trig_cond,
                        "declaration_mode": "explicit_declaration",
                        "application_name": tp["application_name"],
                        "service_name": tp["service_name"],
                        "resolution": tp["resolution"],
                        "rtt_max": tp["rtt"],
                        "start_time": tp["start_timestamp"].split("日")[-1],
                        "end_time": tp["end_timestamp"].split("日")[-1],
                        "duration": tp["duration"],
                        "alias_mapping": selected_alias_map,
                        "scope": scope_val,
                        "status": "active",
                        "evidence_count": 1,
                        "first_declared_at": ref_time,
                        "last_reinforced_at": ref_time
                    }
                    self.active_memories["MF_001"] = mem_item
                    memory_events.append({
                        "event_type": "form_memory_explicit",
                        "memory_id": "MF_001",
                        "description": f"用户首次明确显式声明长期偏好（触发条件：{trig_cond}）：{tp['application_name']}{tp['service_name']}（{tp['resolution']}, {tp['rtt']}），设立老规矩指令，登记个性化别名小记忆点。",
                        "target_slots": ["application_name", "service_name", "resolution", "rtt_max"]
                    })
                else:
                    # 隐式归纳路径：首次仅作为任务历史日志 (provisional)，防止单次行为过拟合
                    mem_item = {
                        "memory_id": "MF_001",
                        "category": "periodic_main_storyline",
                        "storyline_trigger_type": trig_type,
                        "trigger_condition": trig_cond,
                        "declaration_mode": "implicit_induction",
                        "application_name": tp["application_name"],
                        "service_name": tp["service_name"],
                        "resolution": tp["resolution"],
                        "rtt_max": tp["rtt"],
                        "start_time": tp["start_timestamp"].split("日")[-1],
                        "end_time": tp["end_timestamp"].split("日")[-1],
                        "duration": tp["duration"],
                        "alias_mapping": {},
                        "scope": scope_val,
                        "status": "provisional",  # 候选/待归纳状态
                        "evidence_count": 1,
                        "first_declared_at": ref_time,
                        "last_reinforced_at": ref_time
                    }
                    self.active_memories["MF_001"] = mem_item
                    memory_events.append({
                        "event_type": "log_task_history",
                        "memory_id": "MF_001",
                        "description": f"用户在场景（{trig_cond}）发生单次保障行为：{tp['application_name']}{tp['service_name']}，未显式声明长期偏好，记录单次历史日志（防单次行为过拟合）。",
                        "target_slots": ["application_name", "service_name", "resolution", "rtt_max"]
                    })
            elif role in ["reinforcement_session", "reuse_session"]:
                # 主线记忆强化或复用
                if "MF_001" in self.active_memories:
                    prev_status = self.active_memories["MF_001"].get("status")
                    self.active_memories["MF_001"]["evidence_count"] += 1
                    self.active_memories["MF_001"]["last_reinforced_at"] = ref_time

                    if prev_status == "provisional":
                        # 隐式归纳满足证据阈值 (N>=2)，正式固化为 active 长期老规矩
                        self.active_memories["MF_001"]["status"] = "active"
                        small = s_plan.get("small_memory", {})
                        if small.get("alias_key") and small.get("value"):
                            self.active_memories["MF_001"]["alias_mapping"] = _small_memory_mapping(small)
                        memory_events.append({
                            "event_type": "crystallize_implicit_memory",
                            "memory_id": "MF_001",
                            "description": f"用户再次在相似场景（{trig_cond}）发起相同配置，满足隐式归纳证据阈值(N>=2)，经Agent反问确认，正式固化为长期老规矩。",
                            "retrieved_slots": ["application_name", "service_name", "resolution", "rtt_max"]
                        })
                    else:
                        memory_events.append({
                            "event_type": "reinforce_memory",
                            "memory_id": "MF_001",
                            "description": f"用户在（{trig_cond}）省略参数复用主线记忆，Agent 成功补全并经用户确认，证据强度增至 {self.active_memories['MF_001']['evidence_count']} 次。",
                            "retrieved_slots": ["application_name", "service_name", "resolution", "rtt_max"]
                        })

        elif b_type == "sub_01":
            p_aliases = s_plan.get("aliases", {})
            small = s_plan.get("small_memory", {})
            sub1_map = _small_memory_mapping(small)
            if role == "evidence_session":
                mem_item = {
                    "memory_id": "SUB_001",
                    "category": "sub_storyline_transit",
                    "application_name": tp["application_name"],
                    "service_name": tp["service_name"],
                    "resolution": tp["resolution"],
                    "rtt_max": tp["rtt"],
                    "start_time": tp["start_timestamp"].split("日")[-1],
                    "duration": tp["duration"],
                    "alias_mapping": sub1_map,
                    "scope": "transit_evening",
                    "status": "active",
                    "evidence_count": 1,
                    "first_declared_at": ref_time,
                    "last_reinforced_at": ref_time
                }
                self.active_memories["SUB_001"] = mem_item
                memory_events.append({
                    "event_type": "form_memory",
                    "memory_id": "SUB_001",
                    "description": f"建立支线1条件记忆：{tp['application_name']}{tp['service_name']}在转场大巴上采用（{tp['resolution']}, {tp['rtt']}），登记代称小记忆点。",
                    "target_slots": ["application_name", "service_name", "resolution", "rtt_max"]
                })
            elif role in ["reinforcement_session", "reuse_session"]:
                if "SUB_001" in self.active_memories:
                    self.active_memories["SUB_001"]["evidence_count"] += 1
                    self.active_memories["SUB_001"]["last_reinforced_at"] = ref_time
                    memory_events.append({
                        "event_type": "reinforce_memory",
                        "memory_id": "SUB_001",
                        "description": f"支线1转场视频调度记忆复用成功，证据次数达 {self.active_memories['SUB_001']['evidence_count']} 次。",
                        "retrieved_slots": ["application_name", "service_name", "resolution", "rtt_max"]
                    })

        elif b_type == "sub_02":
            p_aliases = s_plan.get("aliases", {})
            small = s_plan.get("small_memory", {})
            sub2_map = _small_memory_mapping(small)
            if role == "evidence_session":
                mem_item = {
                    "memory_id": "SUB_002",
                    "category": "sub_storyline_hotel",
                    "application_name": tp["application_name"],
                    "service_name": tp["service_name"],
                    "resolution": tp["resolution"],
                    "rtt_max": tp["rtt"],
                    "start_time": tp["start_timestamp"].split("日")[-1],
                    "duration": tp["duration"],
                    "alias_mapping": sub2_map,
                    "scope": "hotel_evening_review",
                    "status": "active",
                    "evidence_count": 1,
                    "first_declared_at": ref_time,
                    "last_reinforced_at": ref_time
                }
                self.active_memories["SUB_002"] = mem_item
                memory_events.append({
                    "event_type": "form_memory",
                    "memory_id": "SUB_002",
                    "description": f"建立支线2条件记忆：酒店休息复盘录像采用（{tp['resolution']}, {tp['rtt']}），登记代称小记忆点。",
                    "target_slots": ["application_name", "service_name", "resolution", "rtt_max"]
                })
            elif role in ["reinforcement_session", "reuse_session"]:
                if "SUB_002" in self.active_memories:
                    self.active_memories["SUB_002"]["evidence_count"] += 1
                    self.active_memories["SUB_002"]["last_reinforced_at"] = ref_time
                    memory_events.append({
                        "event_type": "reinforce_memory",
                        "memory_id": "SUB_002",
                        "description": f"支线2酒店复盘记忆复用成功，证据次数达 {self.active_memories['SUB_002']['evidence_count']} 次。",
                        "retrieved_slots": ["application_name", "service_name", "resolution", "rtt_max"]
                    })

        elif b_type == "event_override":
            # 场景化临时事件纠正覆盖：属于单次/当天纠正，不破坏全局长期记忆 MF_001
            memory_events.append({
                "event_type": "temporary_correction",
                "description": f"用户因现场特殊临时主动调整本次参数为（{tp['resolution']}, {tp['rtt']}），仅本次生效，原长期记忆保持有效。",
                "modified_slots": {"resolution": tp["resolution"], "rtt_max": tp["rtt"]}
            })

        elif b_type == "event_reuse":
            # 临时事件次日复用：已结束单次临时纠正，恢复按原长期主线记忆 MF_001 执行
            if "MF_001" in self.active_memories:
                self.active_memories["MF_001"]["evidence_count"] += 1
                self.active_memories["MF_001"]["last_reinforced_at"] = ref_time
                memory_events.append({
                    "event_type": "reinforce_memory",
                    "memory_id": "MF_001",
                    "description": f"单次纠正结束后，会话正常复用原长期主线记忆 MF_001（{self.active_memories['MF_001']['resolution']}, {self.active_memories['MF_001']['rtt_max']}）。",
                    "retrieved_slots": ["application_name", "service_name", "resolution", "rtt_max"]
                })

        elif b_type == "main_recovery":
            # 主线记忆常规复用
            if "MF_001" in self.active_memories:
                self.active_memories["MF_001"]["status"] = "active"
                self.active_memories["MF_001"]["evidence_count"] += 1
                self.active_memories["MF_001"]["last_reinforced_at"] = ref_time

            memory_events.append({
                "event_type": "reinforce_memory",
                "memory_id": "MF_001",
                "description": "成功复用原长期主线偏好配置。"
            })

        elif b_type in ["distractor", "distractor_ood", "distractor_mixed"]:
            memory_events.append({
                "event_type": "no_memory_change",
                "description": "单次任务业务或域外诉求，与长期偏好无关，不发生记忆变更。"
            })

        gold_after = copy.deepcopy(self.active_memories)
        return snapshot_before, memory_events, gold_after
