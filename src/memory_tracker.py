import copy

class MemoryTracker:
    """
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
            if role == "evidence_session":
                if decl_mode == "explicit_declaration":
                    # 主线记忆显式初建 (One-shot)
                    mem_item = {
                        "memory_id": "MF_001",
                        "category": "periodic_main_storyline",
                        "declaration_mode": "explicit_declaration",
                        "application_name": tp["application_name"],
                        "service_name": tp["service_name"],
                        "resolution": tp["resolution"],
                        "rtt_max": tp["rtt"],
                        "scope": "weekly_cycle",
                        "status": "active",
                        "evidence_count": 1,
                        "first_declared_at": ref_time,
                        "last_reinforced_at": ref_time
                    }
                    self.active_memories["MF_001"] = mem_item
                    memory_events.append({
                        "event_type": "form_memory_explicit",
                        "memory_id": "MF_001",
                        "description": f"用户首次明确显式声明长期偏好：{tp['application_name']}{tp['service_name']}（{tp['resolution']}, {tp['rtt']}），设立老规矩指令。",
                        "target_slots": ["application_name", "service_name", "resolution", "rtt_max"]
                    })
                else:
                    # 隐式归纳路径：首次仅作为任务历史日志 (provisional)，防止单次行为过拟合
                    mem_item = {
                        "memory_id": "MF_001",
                        "category": "periodic_main_storyline",
                        "declaration_mode": "implicit_induction",
                        "application_name": tp["application_name"],
                        "service_name": tp["service_name"],
                        "resolution": tp["resolution"],
                        "rtt_max": tp["rtt"],
                        "scope": "weekly_cycle",
                        "status": "provisional",  # 候选/待归纳状态
                        "evidence_count": 1,
                        "first_declared_at": ref_time,
                        "last_reinforced_at": ref_time
                    }
                    self.active_memories["MF_001"] = mem_item
                    memory_events.append({
                        "event_type": "log_task_history",
                        "memory_id": "MF_001",
                        "description": f"用户发生单次保障行为：{tp['application_name']}{tp['service_name']}，未显式声明长期偏好，记录单次历史日志（防单次行为过拟合）。",
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
                        memory_events.append({
                            "event_type": "crystallize_implicit_memory",
                            "memory_id": "MF_001",
                            "description": f"用户再次在相似周期场景发起相同配置，满足隐式归纳证据阈值(N>=2)，经Agent反问确认，正式固化为长期老规矩。",
                            "retrieved_slots": ["application_name", "service_name", "resolution", "rtt_max"]
                        })
                    else:
                        memory_events.append({
                            "event_type": "reinforce_memory",
                            "memory_id": "MF_001",
                            "description": f"用户省略参数复用主线记忆，Agent 成功补全并经用户确认，证据强度增至 {self.active_memories['MF_001']['evidence_count']} 次。",
                            "retrieved_slots": ["application_name", "service_name", "resolution", "rtt_max"]
                        })

        elif b_type == "sub_01":
            if role == "evidence_session":
                mem_item = {
                    "memory_id": "SUB_001",
                    "category": "sub_storyline_transit",
                    "application_name": tp["application_name"],
                    "service_name": tp["service_name"],
                    "resolution": tp["resolution"],
                    "rtt_max": tp["rtt"],
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
                    "description": f"建立支线1条件记忆：{tp['application_name']}{tp['service_name']}在转场大巴上采用（{tp['resolution']}, {tp['rtt']}）。",
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
            if role == "evidence_session":
                mem_item = {
                    "memory_id": "SUB_002",
                    "category": "sub_storyline_hotel",
                    "application_name": tp["application_name"],
                    "service_name": tp["service_name"],
                    "resolution": tp["resolution"],
                    "rtt_max": tp["rtt"],
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
                    "description": f"建立支线2条件记忆：酒店休息复盘录像采用（{tp['resolution']}, {tp['rtt']}）。",
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
            # 场景化临时事件纠正覆盖
            mem_item = {
                "memory_id": "MF_001_v2",
                "category": "scenario_event_temporary",
                "parent_memory_id": "MF_001",
                "application_name": tp["application_name"],
                "service_name": tp["service_name"],
                "resolution": tp["resolution"],
                "rtt_max": tp["rtt"],
                "scope": "temporary_event_window",
                "valid_until": "2026-11-15",
                "status": "active_override",
                "evidence_count": 1,
                "created_at": ref_time
            }
            self.active_memories["MF_001_v2"] = mem_item
            if "MF_001" in self.active_memories:
                self.active_memories["MF_001"]["status"] = "temporarily_overridden"

            memory_events.append({
                "event_type": "correct_override_memory",
                "memory_id": "MF_001_v2",
                "overrides_id": "MF_001",
                "description": f"用户因恶劣环境主动纠正主线参数为（{tp['resolution']}, {tp['rtt']}），设定临时有效期至2026-11-15。",
                "modified_slots": {"resolution": tp["resolution"], "rtt_max": tp["rtt"]}
            })

        elif b_type == "event_reuse":
            if "MF_001_v2" in self.active_memories:
                self.active_memories["MF_001_v2"]["evidence_count"] += 1
                memory_events.append({
                    "event_type": "reinforce_temporary_memory",
                    "memory_id": "MF_001_v2",
                    "description": "赛事期内成功复用临时纠正参数。",
                    "retrieved_slots": ["resolution", "rtt_max"]
                })

        elif b_type == "main_recovery":
            # 临时规则过期，恢复原主线规则
            if "MF_001_v2" in self.active_memories:
                self.active_memories["MF_001_v2"]["status"] = "expired"
            if "MF_001" in self.active_memories:
                self.active_memories["MF_001"]["status"] = "active"
                self.active_memories["MF_001"]["evidence_count"] += 1
                self.active_memories["MF_001"]["last_reinforced_at"] = ref_time

            memory_events.append({
                "event_type": "expire_and_recover_memory",
                "expired_memory_id": "MF_001_v2",
                "recovered_memory_id": "MF_001",
                "description": "临时赛事保障窗口已到期，Agent 提示恢复并成功激活原长期主线偏好（1080p, 50ms）。"
            })

        elif b_type == "distractor":
            memory_events.append({
                "event_type": "no_memory_change",
                "description": "单次任务业务，与长期偏好无关，不发生记忆变更。"
            })

        gold_after = copy.deepcopy(self.active_memories)
        return snapshot_before, memory_events, gold_after
