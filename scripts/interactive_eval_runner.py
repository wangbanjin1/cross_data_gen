# -*- coding: utf-8 -*-
"""
动态多分支交互式模拟评测引擎 (Interactive Evaluation Runner)
面向通信保障意图提参场景，基于数据侧的声明式交互契约 (Interactive Eval Contract)
驱动“联接”Agent 与用户模拟器 (User Simulator) 的目标差距 (Delta) 动态澄清与快速闭环与多轮澄清路径评测。
"""
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class InteractiveEvalEngine:
    """
    声明式交互评测契约解释执行器
    根据 Agent 提参实际输出与标准答案的 Delta 差距，动态驱动用户模拟器反馈
    """

    def __init__(self, contract: Dict[str, Any], session_id: str = "SESSION_EVAL_01"):
        self.contract = contract
        self.session_id = session_id
        self.version = contract.get("version", "1.0")
        self.scenario_type = contract.get("scenario_type", "generic")
        self.ground_truth = contract.get("target_ground_truth", {})
        self.term_conds = contract.get("termination_conditions", {})
        self.max_turns = self.term_conds.get("max_turns", 6)
        self.reaction_matrix = contract.get("delta_reaction_matrix", {})

        # 运行态状态机
        self.current_turn = 0
        self.status = "in_progress"
        self.accumulated_slots: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []

    def get_initial_user_prompt(self, fallback_prompt: str = "") -> str:
        """获取首轮用户发起保障诉求"""
        return fallback_prompt or "帮我办理网络保障业务。"

    def step(
        self,
        agent_utterance: str,
        agent_action_types: List[str],
        agent_slots: Dict[str, Any]
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        """
        接收“联接”Agent 当轮提参输出，比对目标真值差分并执行状态转移
        返回: (user_simulator_reply, user_action_types, delta_report)
        """
        self.current_turn += 1
        self._merge_slots(agent_slots)

        delta_report = self._compute_slot_delta(agent_action_types)
        triggered_key = delta_report["triggered_reaction"]

        reaction = self.reaction_matrix.get(triggered_key, {})
        simulator_reply = reaction.get("simulator_reply", "收到，请继续确认。")
        user_actions = reaction.get("user_action_types", ["Inform_Slot"])

        if triggered_key == "on_goal_matched" or "Acknowledge" in agent_action_types:
            self.status = "resolved"
        elif self.current_turn >= self.max_turns:
            self.status = "terminated_max_turns"

        step_record = {
            "turn": self.current_turn,
            "agent_utterance": agent_utterance,
            "agent_action_types": agent_action_types,
            "agent_slots": agent_slots,
            "delta_report": delta_report,
            "triggered_reaction": triggered_key,
            "simulator_reply": simulator_reply,
            "user_action_types": user_actions,
            "eval_status": self.status
        }
        self.history.append(step_record)

        return simulator_reply, user_actions, delta_report

    def _merge_slots(self, new_slots: Dict[str, Any]):
        """合并 Agent 当轮抽取的槽位"""
        for k, v in new_slots.items():
            if isinstance(v, dict) and k in self.accumulated_slots and isinstance(self.accumulated_slots[k], dict):
                self.accumulated_slots[k].update(v)
            else:
                self.accumulated_slots[k] = v

    def _compute_slot_delta(self, agent_action_types: List[str]) -> Dict[str, Any]:
        """核心差分仲裁逻辑"""
        has_error = False
        error_details = []
        missing_details = []

        # 检查意图与槽位匹配
        for intent_id, gt_intent in self.ground_truth.items():
            gt_slots = gt_intent.get("slots", {})
            for slot_key, gt_val in gt_slots.items():
                if isinstance(gt_val, dict):
                    # 嵌套槽位如 timestamp (start, end, duration)
                    for sub_key, sub_gt_val in gt_val.items():
                        full_key = f"{intent_id}.{slot_key}.{sub_key}" if len(self.ground_truth) > 1 else f"{slot_key}.{sub_key}"
                        agent_val = self._lookup_slot_val(full_key, slot_key, sub_key, intent_id)
                        agent_norm = self._normalize_val(agent_val)
                        gt_norm = self._normalize_val(sub_gt_val)
                        if agent_norm is not None and str(agent_norm).strip() != str(gt_norm).strip():
                            has_error = True
                            error_details.append(f"{full_key}: expected '{gt_norm}', got '{agent_norm}'")
                        elif agent_norm is None:
                            missing_details.append(full_key)
                else:
                    full_key = f"{intent_id}.{slot_key}" if len(self.ground_truth) > 1 else slot_key
                    agent_val = self._lookup_slot_val(full_key, slot_key, None, intent_id)
                    agent_norm = self._normalize_val(agent_val)
                    gt_norm = self._normalize_val(gt_val)
                    if agent_norm is not None and str(agent_norm).strip() != str(gt_norm).strip():
                        has_error = True
                        error_details.append(f"{full_key}: expected '{gt_norm}', got '{agent_norm}'")
                    elif agent_norm is None:
                        missing_details.append(full_key)

        # 检查 Agent 动作异常（例如拒绝受理）
        if "Reject_Request" in agent_action_types:
            has_error = True
            error_details.append("agent_action_type: Reject_Request")

        # 判定触发哪种反馈
        if has_error:
            triggered = "on_slot_error"
        elif "Request_Slot" in agent_action_types:
            triggered = "on_agent_inquiry"
        elif missing_details:
            triggered = "on_slot_missing"
        else:
            triggered = "on_goal_matched"

        return {
            "has_error": has_error,
            "error_details": error_details,
            "missing_details": missing_details,
            "triggered_reaction": triggered,
            "is_goal_matched": (triggered == "on_goal_matched")
        }

    @staticmethod
    def _normalize_val(val: Any) -> Any:
        """递归提取包装字典中的真实业务值"""
        if isinstance(val, dict):
            if "value" in val:
                return InteractiveEvalEngine._normalize_val(val["value"])
            if "min_value" in val:
                return InteractiveEvalEngine._normalize_val(val["min_value"])
            if "max_value" in val:
                return InteractiveEvalEngine._normalize_val(val["max_value"])
        return val

    def _lookup_slot_val(self, full_key: str, key: str, sub_key: Optional[str], intent_id: str) -> Any:
        """多层级槽位检索"""
        # 1. 尝试直接以 full_key 索引
        if full_key in self.accumulated_slots:
            return self.accumulated_slots[full_key]
        # 2. 尝试从 intent_id 下层索引
        if intent_id in self.accumulated_slots and isinstance(self.accumulated_slots[intent_id], dict):
            i_slots = self.accumulated_slots[intent_id]
            if sub_key and key in i_slots and isinstance(i_slots[key], dict):
                return i_slots[key].get(sub_key)
            return i_slots.get(key)
        # 3. 尝试直接顶层
        if sub_key and key in self.accumulated_slots and isinstance(self.accumulated_slots[key], dict):
            return self.accumulated_slots[key].get(sub_key)
        return self.accumulated_slots.get(key)


def run_contract_benchmark(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """对单条经验测试会话运行基准多分支契约评测"""
    eb = session_data.get("experience_branching") or session_data.get("session_meta", {}).get("experience_branching")
    if not eb or "interactive_eval_contract" not in eb:
        return {"status": "skipped", "reason": "no_contract"}

    contract = eb["interactive_eval_contract"]
    engine = InteractiveEvalEngine(contract, session_id=session_data.get("session_id", "S-TEST"))

    # 从 slow_path 的 simulator_dialogue_tree 中模拟基准 Agent 对抗流
    slow_tree = eb.get("slow_path", {}).get("simulator_dialogue_tree", [])
    if not slow_tree:
        return {"status": "skipped", "reason": "no_slow_tree"}

    turn_results = []
    # 模拟 Agent 在 Slow 路径下拉扯修正的全过程
    for node in slow_tree:
        agent_utterance = node.get("expected_agent_correction") or node.get("baseline_agent_flawed_response", "")
        agent_actions = node.get("agent_action_types", ["Confirm_Slot"])

        # 构造当轮 Agent 提取的 slots（从 full_slow_event_sequence 对应轮次抽样）
        t_idx = node["turn"] - 1
        full_seq = eb.get("slow_path", {}).get("full_slow_event_sequence", [])
        turn_slots = {}
        if t_idx < len(full_seq):
            t_intents = full_seq[t_idx].get("turn_intents", [])
            for tint in t_intents:
                iid = tint["intent_id"]
                turn_slots[iid] = {}
                for pk, pv in tint.get("params", {}).items():
                    if isinstance(pv, dict) and "value" in pv:
                        turn_slots[iid][pk] = pv["value"]
                    elif isinstance(pv, dict):
                        turn_slots[iid][pk] = {sub_k: sub_v.get("value") for sub_k, sub_v in pv.items() if isinstance(sub_v, dict)}

        reply, user_actions, delta = engine.step(agent_utterance, agent_actions, turn_slots)
        turn_results.append({
            "turn": node["turn"],
            "triggered": delta["triggered_reaction"],
            "status": engine.status
        })

    fast_rounds = eb.get("fast_path", {}).get("round_count", 2)
    slow_rounds = engine.current_turn
    tcg = round((slow_rounds - fast_rounds) / slow_rounds * 100.0, 2) if slow_rounds > 0 else 0.0

    return {
        "status": "success",
        "session_id": session_data.get("session_id"),
        "scenario_type": contract.get("scenario_type"),
        "fast_rounds": fast_rounds,
        "slow_rounds": slow_rounds,
        "tcg_percentage": tcg,
        "final_status": engine.status,
        "turns": turn_results
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="运行动态多分支模拟评测引擎 (Interactive Evaluation Runner)")
    parser.add_argument("--data", type=str, default="data/cognitive_samples", help="样本目录")
    args = parser.parse_args()

    data_dir = Path(args.data)
    if not data_dir.exists():
        logger.info(f"[ERROR] 目录不存在: {data_dir}")
        sys.exit(1)

    logger.info("=" * 70)
    logger.info("  '联接'Agent 动态多分支交互式模拟评测 (Interactive Benchmark)")
    logger.info("=" * 70)

    total_sessions = 0
    success_count = 0
    sum_tcg = 0.0

    for p_dir in sorted(data_dir.glob("mobile_persona_*")):
        s_jsonl = p_dir / "sessions.jsonl"
        if not s_jsonl.exists():
            continue

        with open(s_jsonl, "r", encoding="utf-8") as f:
            sessions = [json.loads(line) for line in f if line.strip()]

        for s in sessions:
            eb = s.get("experience_branching") or s.get("session_meta", {}).get("experience_branching")
            if not eb or "interactive_eval_contract" not in eb:
                continue

            res = run_contract_benchmark(s)
            if res.get("status") == "success":
                total_sessions += 1
                if res["final_status"] == "resolved":
                    success_count += 1
                sum_tcg += res["tcg_percentage"]
                logger.info(f"[PASS] {p_dir.name} | {res['session_id']} | 场景: {res['scenario_type']:<26} | Fast={res['fast_rounds']} Slow={res['slow_rounds']} | TCG={res['tcg_percentage']}% | 终态={res['final_status']}")

    logger.info("-" * 70)
    if total_sessions > 0:
        avg_tcg = round(sum_tcg / total_sessions, 2)
        sr = round(success_count / total_sessions * 100.0, 1)
        logger.info(f"[SUMMARY] 评测会话数: {total_sessions} | 闭环成功率: {sr}% | 平均交互轮数压缩率 (TCG): {avg_tcg}%")
    else:
        logger.info("[INFO] 当前暂无已嵌入交互评测契约的经验测试会话，生成后即可跑分。")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
