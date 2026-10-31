from __future__ import annotations

from src.generation.assemblers.experience_branching_scenarios import build_scenario_branch_nodes


class ExperienceBranchingBuilderMixin:
    """Builds interactive evaluation contracts and fast/slow path branching metadata."""

    @classmethod
    def _build_experience_branching(
        cls,
        scenario_type: str,
        exp_id: str,
        rule_title: str,
        learning_source_session: str,
        user_prompt: str,
        ctx: dict,
    ) -> dict:
        """构建具备完整 3 轮可执行交互树与自动化仲裁门 (Branch Decision Gate) 的快速闭环与多轮澄清路径评测元数据"""
        app = ctx.get("app", "保障应用")
        srv = ctx.get("srv", "保障业务")
        res = ctx.get("res", "1080p")
        rtt = ctx.get("rtt", "50ms")
        start = ctx.get("start", "14:00")
        end = ctx.get("end", "16:00")
        dur = ctx.get("dur", "120min")

        (
            fast_cond,
            slow_cond,
            gate,
            slot_err_reply,
            goal_match_reply,
            tree,
            full_slow_seq,
            app,
            srv,
        ) = build_scenario_branch_nodes(
            scenario_type=scenario_type,
            user_prompt=user_prompt,
            app=app,
            srv=srv,
            res=res,
            rtt=rtt,
            start=start,
            end=end,
            dur=dur,
        )
        slow_rounds = len(tree) if tree else 3
        fast_rounds = 2

        # 构建声明式交互评测契约 (Interactive Evaluation Contract)
        target_gt = {
            "I1": {
                "intent": f"{app}{srv}保障",
                "slots": {
                    "application_name": app,
                    "service_name": srv,
                    "resolution": res,
                    "rtt": rtt,
                    "timestamp": {
                        "start_timestamp": start,
                        "end_timestamp": end,
                        "duration": dur
                    }
                }
            }
        }

        if scenario_type == "multi_intent_partition":
            reaction_matrix = {
                "on_slot_error": {
                    "description": "Agent被字面‘抖音直播’误导，将私下对词试机位误提为【抖音-开直播】而非【微信-视频通话】",
                    "trigger_condition": "agent_slots.get('application_name') != ground_truth['I1']['slots']['application_name'] or agent_slots.get('service_name') != ground_truth['I1']['slots']['service_name']",
                    "monitored_slots": ["I1.application_name", "I1.service_name"],
                    "user_action_types": ["Revise_Intent_Request", "Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_slot_missing": {
                    "description": "Agent遗漏意图保障单的时长或时段槽位",
                    "trigger_condition": "not agent_slots.get('timestamp.duration')",
                    "monitored_slots": ["I1.timestamp.duration"],
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_agent_inquiry": {
                    "description": "Agent向用户询问对词试机位使用的具体应用软件",
                    "trigger_condition": "agent_action in ['Request_Slot']",
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_goal_matched": {
                    "description": "【微信-视频通话】应用、业务与时段完全核准对齐，用户确认闭环出单",
                    "trigger_condition": "agent_slots_all_matched and agent_action in ['Confirm_Slot', 'Inform_Slot', 'Acknowledge']",
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": goal_match_reply
                }
            }
        elif scenario_type == "prewarm_buffer":
            reaction_matrix = {
                "on_slot_error": {
                    "description": "Agent机械按活动原定时间掐点预约，未执行提前30分钟试机预热推算",
                    "trigger_condition": "agent_slots.get('timestamp.start_timestamp') != ground_truth['I1']['slots']['timestamp']['start_timestamp']",
                    "monitored_slots": ["I1.timestamp.start_timestamp", "I1.timestamp.duration"],
                    "user_action_types": ["Revise_Intent_Request", "Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_slot_missing": {
                    "description": "Agent遗漏起保时间或总时长槽位",
                    "trigger_condition": "not agent_slots.get('timestamp.duration')",
                    "monitored_slots": ["I1.timestamp.duration"],
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_agent_inquiry": {
                    "description": "Agent主动询问用户预热起止时段或规格要求",
                    "trigger_condition": "agent_action in ['Request_Slot']",
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_goal_matched": {
                    "description": "提前预热起保时序与网络指标完全核准对齐，用户确认办理",
                    "trigger_condition": "agent_slots_all_matched and agent_action in ['Confirm_Slot', 'Inform_Slot', 'Acknowledge']",
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": goal_match_reply
                }
            }
        elif scenario_type == "holiday_exception":
            reaction_matrix = {
                "on_slot_error": {
                    "description": "Agent未识别国庆长假，机械在10月5日放假当天预约意图保障单",
                    "trigger_condition": "agent_slots.get('timestamp.start_timestamp') != ground_truth['I1']['slots']['timestamp']['start_timestamp']",
                    "monitored_slots": ["I1.timestamp.start_timestamp", "I1.timestamp.end_timestamp"],
                    "user_action_types": ["Revise_Intent_Request", "Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_agent_inquiry": {
                    "description": "Agent识别假期冲突后反问改期时间",
                    "trigger_condition": "agent_action in ['Request_Slot']",
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_slot_missing": {
                    "description": "Agent顺延了日期但遗漏时长或清晰度槽位",
                    "trigger_condition": "not agent_slots.get('timestamp.duration')",
                    "monitored_slots": ["I1.timestamp.duration", "I1.resolution"],
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_goal_matched": {
                    "description": "节后首个工作日顺延时序与规格核准，用户确认办理",
                    "trigger_condition": "agent_slots_all_matched and agent_action in ['Confirm_Slot', 'Inform_Slot', 'Acknowledge']",
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": goal_match_reply
                }
            }
        elif scenario_type == "quality_disambiguation":
            reaction_matrix = {
                "on_slot_error": {
                    "description": "Agent因最近邻偏见机械复用了前天1小时(60min)临时短单时长",
                    "trigger_condition": "agent_slots.get('timestamp.end_timestamp') != ground_truth['I1']['slots']['timestamp']['end_timestamp'] or agent_slots.get('timestamp.duration') != ground_truth['I1']['slots']['timestamp']['duration']",
                    "monitored_slots": ["I1.timestamp.end_timestamp", "I1.timestamp.duration"],
                    "user_action_types": ["Revise_Intent_Request", "Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_slot_missing": {
                    "description": "Agent遗漏核对今日意图保障单起止时序或时长",
                    "trigger_condition": "not agent_slots.get('timestamp.duration')",
                    "monitored_slots": ["I1.timestamp.end_timestamp", "I1.timestamp.duration"],
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_agent_inquiry": {
                    "description": "Agent询问历史意图保障单选择或具体保障时长",
                    "trigger_condition": "agent_action in ['Request_Slot', 'Request_Disambiguation']",
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_goal_matched": {
                    "description": "上周2小时(120min)正式路演单时长继承无误，用户确认受理",
                    "trigger_condition": "agent_slots_all_matched and agent_action in ['Confirm_Slot', 'Inform_Slot', 'Acknowledge']",
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": goal_match_reply
                }
            }
        elif scenario_type == "overlapping_resolution":
            reaction_matrix = {
                "on_slot_error": {
                    "description": "Agent看到‘进主会场抖音直播间’字眼，将连麦嘉宾误提为【看直播】而非【开直播】",
                    "trigger_condition": "agent_slots.get('service_name') != ground_truth['I1']['slots']['service_name']",
                    "monitored_slots": ["I1.service_name"],
                    "user_action_types": ["Revise_Intent_Request", "Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_slot_missing": {
                    "description": "Agent遗漏业务类型或保障时长",
                    "trigger_condition": "not agent_slots.get('service_name')",
                    "monitored_slots": ["I1.service_name"],
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_agent_inquiry": {
                    "description": "Agent询问连麦嘉宾具体业务类型",
                    "trigger_condition": "agent_action in ['Request_Slot']",
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": slot_err_reply
                },
                "on_goal_matched": {
                    "description": "【抖音-开直播】业务类型与时段核准完成，用户确认办理",
                    "trigger_condition": "agent_slots_all_matched and agent_action in ['Confirm_Slot', 'Inform_Slot', 'Acknowledge']",
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": goal_match_reply
                }
            }
        else:
            reaction_matrix = {
                "on_slot_error": {
                    "description": "Agent提参错误，用户指正",
                    "trigger_condition": "agent_slots_mismatch",
                    "monitored_slots": [],
                    "user_action_types": ["Revise_Intent_Request"],
                    "simulator_reply": "参数不对，请重新核实。"
                },
                "on_agent_inquiry": {
                    "description": "Agent询问缺失参数，用户提供",
                    "trigger_condition": "agent_action == 'Request_Slot'",
                    "monitored_slots": [],
                    "user_action_types": ["Inform_Slot"],
                    "simulator_reply": f"按规格{res}和时延≤{rtt}办理。"
                },
                "on_slot_missing": {
                    "description": "Agent遗漏必要参数",
                    "trigger_condition": "agent_slot_missing",
                    "monitored_slots": [],
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": "请核对时长和完整保障指标。"
                },
                "on_goal_matched": {
                    "description": "参数对齐闭环",
                    "trigger_condition": "agent_slots_all_matched",
                    "monitored_slots": [],
                    "user_action_types": ["Confirm_Slot"],
                    "simulator_reply": "好的，规格时间都对了，确认按此开通。"
                }
            }

        turn_level_gt = []
        for i, node in enumerate(tree):
            item = {
                "turn": node["turn"],
                "speaker": node["speaker"],
                "simulator_user_prompt": node.get("simulator_user_prompt", ""),
                "expected_agent_response": node.get("expected_agent_response", node.get("expected_agent_correction", "")),
                "expected_agent_correction": node.get("expected_agent_correction", ""),
                "expected_agent_action_types": node.get("agent_action_types", []),
                "expected_slots_gt": node.get("expected_slots_gt", {}),
                "intents_status": {
                    tint["intent_id"]: tint["status"]
                    for tint in (full_slow_seq[i].get("turn_intents", []) if i < len(full_slow_seq) else [])
                }
            }
            if "baseline_agent_flawed_response" in node:
                item["baseline_agent_flawed_response"] = node["baseline_agent_flawed_response"]
            if "baseline_flawed_action_types" in node:
                item["baseline_flawed_action_types"] = node["baseline_flawed_action_types"]
            if "baseline_flawed_slots" in node:
                item["baseline_flawed_slots"] = node["baseline_flawed_slots"]
            if "delta_from_gt" in node:
                item["delta_from_gt"] = node["delta_from_gt"]
            item["is_terminal"] = (i == len(tree) - 1)
            turn_level_gt.append(item)

        contract = {
            "version": "1.0",
            "contract_name": "DynamicGoalDeltaReactionContract",
            "scenario_type": scenario_type,
            "target_ground_truth": target_gt,
            "turn_level_ground_truth": turn_level_gt,
            "termination_conditions": {
                "max_turns": slow_rounds + 1,
                "required_status": "resolved",
                "early_stop_on_match": True
            },
            "delta_reaction_matrix": reaction_matrix,
            "evaluator_prompt_template": (
                "你作为通信网络保障评测环境中的用户模拟器（User Simulator）。"
                "每轮接收'联接'Agent输出的意图保障单提参结果与话术，对比 target_ground_truth 与 turn_level_ground_truth 计算参数差分（Delta）。"
                "若存在参数错误或越权修改，触发 on_slot_error 并发出包含明确目标真值槽位的纠偏提示；"
                "若'联接'Agent发起槽位追问，触发 on_agent_inquiry 提供真值槽位；"
                "若'联接'Agent遗漏关键槽位，触发 on_slot_missing 提醒核验；"
                "若所有参数均已正确命中且 Agent 提请确认，触发 on_goal_matched 确认闭环并收尾。"
            )
        }

        return {
            "learning_source_session": learning_source_session,
            "experience_id": exp_id,
            "rule_title": rule_title,
            "interactive_eval_contract": contract,
            "fast_path": {
                "round_count": fast_rounds,
                "closure_path": "fast_experience_closed_loop",
                "trigger_condition": fast_cond,
                "resolved_turn": fast_rounds,
                "key_params_source": {"source_type": "Experience", "source_ref": exp_id}
            },
            "slow_path": {
                "round_count": slow_rounds,
                "closure_path": "clarification_after_correction",
                "trigger_condition": slow_cond,
                "resolved_turn": slow_rounds,
                "redundant_rounds": slow_rounds - fast_rounds,
                "branch_decision_gate": gate,
                "interactive_eval_contract": contract,
                "turn_level_ground_truth": turn_level_gt,
                "simulator_dialogue_tree": tree,
                "full_slow_event_sequence": full_slow_seq
            }
        }

