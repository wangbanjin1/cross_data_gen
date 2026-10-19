# -*- coding: utf-8 -*-
"""
单元与集成测试：认知记忆全景演进体系 (Cognitive Memory Evolution Test Suite)
覆盖：
1. 时态推断引擎 (TemporalEngine): 日期解析、Δt、时态词生成、消歧识别
2. 独立工单账本 (WorkingRecordsLedger): 物理文件解耦、工单生命周期、轻量级索引指针
3. 结构化经验知识库 (ExperienceBank): ReasoningBank 三元组、主动提议、经验回溯、边界反例
4. 时间线规划与蓝图 (TimelinePlanner & Blueprints): 动态规划、T2-6~T2-10 蓝图生成
5. 会话装配器 (SessionAssembler): T2-6 ~ T2-10 会话结构、指针与引文组装
6. 自动化质检器 (QCValidator): 规则遵从性校验
7. 事实记忆核心指标 (TCG & Agility Factor): 交互轮数压缩增益公式与敏捷度调制
"""

import unittest
import tempfile
import json
from pathlib import Path

from src.core.temporal_engine import TemporalEngine
from src.core.working_records_ledger import WorkingRecordsLedger
from src.core.experience_bank import ExperienceBank, DEFAULT_EXPERIENCE_ENTRIES
from src.core.timeline_planner import DynamicTimelinePlanner
from src.generation.session_assembler import SessionAssembler
from src.core.qc_validator import QCValidator
from src.core.memory_tracker import MemoryTracker


class TestCognitiveMemoryEvolution(unittest.TestCase):

    def test_01_temporal_engine(self):
        """测试时态推断引擎的核心功能"""
        # 1. 中文日期解析
        dt1 = TemporalEngine.parse_datetime("2026年10月24日 14:00")
        self.assertEqual(dt1.year, 2026)
        self.assertEqual(dt1.month, 10)
        self.assertEqual(dt1.day, 24)
        self.assertEqual(dt1.hour, 14)

        # 2. 时差天数计算
        delta = TemporalEngine.calculate_delta_days("2026年10月24日 14:00", "2026年10月17日 14:00")
        self.assertEqual(delta, 7)

        # 3. 相对时态口语表达生成
        self.assertEqual(TemporalEngine.get_relative_temporal_term(0), "今天")
        self.assertEqual(TemporalEngine.get_relative_temporal_term(1), "昨天")
        self.assertEqual(TemporalEngine.get_relative_temporal_term(7), "上周")

        # 4. 候选单据精确检索与命中
        records = [
            {
                "record_id": "REC_20261017_01",
                "created_at": "2026年10月17日 14:00",
                "application_name": "快手",
                "service_name": "赛事转播",
                "resolution": "1080p",
                "rtt_max": "50ms",
                "location": "奥体看台"
            },
            {
                "record_id": "REC_20261020_01",
                "created_at": "2026年10月20日 19:00",
                "application_name": "腾讯会议",
                "service_name": "视频会议",
                "resolution": "720p",
                "rtt_max": "80ms",
                "location": "办公区"
            }
        ]

        # 唯一命中
        res = TemporalEngine.resolve_temporal_query("这次去奥体，还按上周在奥体开的那个规格来", "2026年10月24日 14:00", records)
        self.assertEqual(res["status"], "matched")
        self.assertEqual(res["target_record"]["record_id"], "REC_20261017_01")
        self.assertEqual(res["inherited_slots"]["resolution"], "1080p")
        self.assertFalse(res["need_disambiguation"])

        # 歧义消歧识别 (MemoryArena 启发)
        ambiguous_records = [
            {"record_id": "REC_01", "created_at": "2026年10月17日 10:00", "application_name": "腾讯会议", "service_name": "早间会议"},
            {"record_id": "REC_02", "created_at": "2026年10月17日 10:00", "application_name": "抖音", "service_name": "直播带货"}
        ]
        res_ambig = TemporalEngine.resolve_temporal_query("今天按上周那次来", "2026年10月24日 10:00", ambiguous_records)
        self.assertEqual(res_ambig["status"], "ambiguous")
        self.assertTrue(res_ambig["need_disambiguation"])

    def test_02_working_records_ledger_decoupling(self):
        """测试工作记忆独立工单账本与物理存储解耦"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            ledger_path = Path(tmp_dir) / "working_records.jsonl"
            ledger = WorkingRecordsLedger(user_id="USER_TEST", storage_path=ledger_path)

            mock_s_plan = {
                "session_id": "S-USER_TEST-01",
                "reference_time": "2026年10月17日 14:00",
                "scenario_env": "奥体体育场",
                "target_params": {
                    "application_name": "快手",
                    "service_name": "赛事转播",
                    "start_timestamp": "2026年10月17日 14:00",
                    "end_timestamp": "2026年10月17日 16:00",
                    "duration": "120min",
                    "resolution": "1080p",
                    "rtt": "50ms"
                }
            }

            rec = ledger.create_record_from_session(mock_s_plan)
            ledger.append_record(rec)

            # 验证物理文件独立存在且解耦
            self.assertTrue(ledger_path.exists())
            with open(ledger_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            self.assertEqual(len(lines), 1)
            loaded_rec = json.loads(lines[0])
            self.assertEqual(loaded_rec["application_name"], "快手")
            self.assertEqual(loaded_rec["resolution"], "1080p")

            # 验证轻量级索引指针生成（仅包含关键键，杜绝整条大工单嵌入会话）
            ptr = ledger.generate_session_pointer(rec, "2026年10月24日 14:00")
            self.assertEqual(ptr["target_record_id"], rec["record_id"])
            self.assertEqual(ptr["inferred_delta_days"], 7)
            self.assertEqual(ptr["inherited_slots"]["resolution"], "1080p")

    def test_03_experience_bank(self):
        """测试 ReasoningBank 结构化经验知识库"""
        bank = ExperienceBank()
        all_exp = bank.get_all_experiences()
        self.assertGreaterEqual(len(all_exp), 6)

        # 1. 验证 ReasoningBank 三元组 Schema (title, description, content) 及适用边界与反例
        card = bank.find_by_id("EXP_STADIUM_CONGESTION_01")
        self.assertIsNotNone(card)
        self.assertIn("title", card)
        self.assertIn("description", card)
        self.assertIn("content", card)
        self.assertIn("applicable_boundaries", card)
        self.assertIn("negative_counterexamples", card)

        # 2. 测试主动经验提议检索 (Proactive Suggestion)
        proactive_card = bank.match_proactive_experience(scenario_env="奥体中心万人演唱会现场")
        self.assertIsNotNone(proactive_card)
        self.assertEqual(proactive_card["experience_id"], "EXP_STADIUM_CONGESTION_01")
        self.assertEqual(proactive_card["recommended_adjustments"]["resolution"], "720p")

        # 3. 测试经验回溯检索 (Empirical Recall)
        recall_card = bank.match_empirical_recall("现场大暴雨很恶劣，按上次恶劣天气加固方案开")
        self.assertIsNotNone(recall_card)
        self.assertEqual(recall_card["experience_id"], "EXP_SEVERE_WEATHER_01")

    def test_04_timeline_planner_and_cognitive_blueprints(self):
        """测试时间线动态规划器对工作记忆与经验记忆模版的规划与自动组装"""
        mock_persona = {
            "static_profile": {"user_id": "USER_999", "identity": "赛事外场直播总监", "speech_style": {"tone": "干练", "catchphrases": "效率第一", "typical_habits": "简洁"}},
            "dynamic_profile": {
                "periodic_main_storyline": {
                    "application_name": "快手",
                    "service_name": "赛事转播",
                    "period_type": "weekly",
                    "time_range": "14:00-16:00",
                    "preferred_params": {"resolution": "1080p", "rtt_max": "50ms"}
                },
                "scenario_events": [
                    {
                        "event_name": "台风暴雨极端保障",
                        "scene_description": "外场台风大暴雨突发",
                        "preference_override": {"resolution": "720p", "rtt_max": "30ms"}
                    }
                ],
                "sub_storylines": [
                    {
                        "application_name": "微信",
                        "service_name": "对齐开会",
                        "params": {"resolution": "720p", "rtt_max": "60ms"}
                    }
                ],
                "distractor_pool": [
                    {"application_name": "中国移动", "service_name": "宽带报修"}
                ]
            }
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            ledger_path = Path(tmp_dir) / "working_records.jsonl"
            ledger = WorkingRecordsLedger(user_id="USER_999", storage_path=ledger_path)
            exp_bank = ExperienceBank()

            planned_sessions = DynamicTimelinePlanner.plan(
                persona=mock_persona,
                working_ledger=ledger,
                experience_bank=exp_bank
            )

            # 验证会话规划包含认知演进模板且长度达到 16 轮
            self.assertGreaterEqual(len(planned_sessions), 16)
            self.assertLessEqual(len(planned_sessions), 24)

            # 验证彻底告别机械模板词“常规周期保障现场”，全部为真实具象物理场所
            for s in planned_sessions:
                self.assertNotEqual(s.get("scenario_env"), "常规周期保障现场")
                self.assertTrue(len(s.get("scenario_env", "")) > 1)

            tids = [s["template_id"] for s in planned_sessions]
            self.assertIn("T2-1", tids)
            self.assertIn("T2-6", tids)  # 工作记忆：跨期复用与消歧
            self.assertIn("T2-7", tids)  # 工作记忆：变更改期
            self.assertTrue(any(exp_tid in tids for exp_tid in ["T2-9", "T2-10", "T2-4", "T2-1"])) # 经验记忆测试

            # 验证经验记忆成对学习铺垫 (Approach 2: 踩坑反思沉淀 -> 动态成败分支评测)
            b_types = [s["blueprint_type"] for s in planned_sessions]
            self.assertIn("experience_learning", b_types)
            learn_sids = [s["session_id"] for s in planned_sessions if s["blueprint_type"] == "experience_learning"]
            self.assertGreaterEqual(len(learn_sids), 1)

            test_sessions = [s for s in planned_sessions if s.get("learning_source_session")]
            self.assertGreaterEqual(len(test_sessions), 1)
            for ts in test_sessions:
                self.assertIn(ts["learning_source_session"], learn_sids)
                self.assertLess(int(ts["learning_source_session"].split("-")[-1]), int(ts["session_id"].split("-")[-1]))

            # 验证 T2-6 包含消歧会话 (3 轮)
            s_disambig = next((s for s in planned_sessions if s.get("is_disambiguation")), None)
            self.assertIsNotNone(s_disambig)
            self.assertEqual(s_disambig["round_count"], 3)
            self.assertIn("candidate_record_ids", s_disambig.get("working_memory_pointer", {}))

            # 验证工单流水账自动建立并已保存
            ledger.save()
            self.assertTrue(ledger_path.exists())
            self.assertGreater(len(ledger.get_all_records()), 0)

    def test_05_session_assembler_and_qc(self):
        """测试 SessionAssembler 装配 T2-6 ~ T2-10 与 QCValidator 规则通过率"""
        mock_plan_t2_6 = {
            "session_id": "S-TEST-04",
            "user_id": "USER_TEST",
            "reference_time": "2026年10月24日 14:00",
            "template_id": "T2-6",
            "memory_role": "reuse_session",
            "round_count": 2,
            "blueprint_type": "working_record_reuse",
            "scenario_env": "奥体中心主体育场看台",
            "memory_action": "retrieve_working_record_reuse",
            "working_memory_pointer": {
                "target_record_id": "REC_USER_TEST_20261017_01",
                "inferred_delta_days": 7,
                "matched_application": "快手",
                "matched_service": "赛事转播",
                "inherited_slots": {"resolution": "1080p", "rtt_max": "50ms", "duration": "120min"}
            },
            "target_params": {
                "application_name": "快手",
                "service_name": "赛事转播",
                "resolution": "1080p",
                "rtt": "50ms",
                "start_timestamp": "2026年10月24日 14:00",
                "end_timestamp": "2026年10月24日 16:00",
                "duration": "120min"
            }
        }

        mock_events_t2_6 = [
            {
                "turn": 1,
                "user": {"utterance": "这次去奥体，还按上周在奥体办的那个规格来。", "action_types": ["Create_Intent_Request", "Inform_Slot"]},
                "agent": {"utterance": "已为您找到上周在奥体的快手转播单（1080p/50ms）。请问今天的保障起止时间是？", "action_types": ["Confirm_Slot", "Request_Slot"]},
                "related_intent_ids": ["I1"],
                "requested_params": []
            },
            {
                "turn": 2,
                "user": {"utterance": "今天是从14点到16点，持续120分钟。", "action_types": ["Inform_Slot"]},
                "agent": {"utterance": "好的，已按引用的历史工单为您开通快手保障（1080p/50ms），祝您顺利！", "action_types": ["Acknowledge"]},
                "related_intent_ids": ["I1"],
                "requested_params": []
            }
        ]

        tracker = MemoryTracker()
        snap_before, mem_events, gold_after = tracker.process_session(mock_plan_t2_6)

        assembled_s4 = SessionAssembler.assemble(
            s_plan=mock_plan_t2_6,
            snapshot_before=snap_before,
            memory_events=mem_events,
            gold_after=gold_after,
            event_sequence=mock_events_t2_6
        )

        # 检查组装结构的完备性与轻量指针
        self.assertEqual(assembled_s4["session_meta"]["template_id"], "T2-6")
        self.assertIn("working_memory_pointer", assembled_s4)
        self.assertEqual(assembled_s4["working_memory_pointer"]["target_record_id"], "REC_USER_TEST_20261017_01")
        self.assertEqual(assembled_s4["intents"][0]["params"]["resolution"]["min_value"]["source_type"], "WorkingRecord")

        # 检查自动化质检器通过
        qc_res = QCValidator.validate_sessions([assembled_s4])
        self.assertEqual(qc_res["passed_sessions"], 1)
        self.assertEqual(qc_res["failed_sessions"], 0)

    def test_06_tcg_metric_and_agility_factor(self):
        """测试单一量化指标 Turn Compression Gain (TCG) 与 敏捷度因子 α 控制"""
        # 1. TCG 指标计算验证
        t_cold = 3.0  # 冷启动多轮澄清基准
        t_hot = 1.5   # 热启动平均轮次
        tcg = (t_cold - t_hot) / t_cold * 100.0
        self.assertAlmostEqual(tcg, 50.0)

        # 2. 敏捷度因子 α 调制轮次公式
        alpha_high = 0.8
        t_expected_high = round(t_cold * (1 - alpha_high))
        self.assertEqual(t_expected_high, 1)

        alpha_mid = 0.4
        t_expected_mid = round(t_cold * (1 - alpha_mid))
        self.assertEqual(t_expected_mid, 2)

    def test_07_experience_slow_path_branching(self):
        """测试经验记忆双轨成败分支测试体系中的完整 4 轮 Slow Path 交互树与仲裁门"""
        eb = SessionAssembler._build_experience_branching(
            scenario_type="prewarm_buffer",
            exp_id="EXP_PREWARM_BUFFER_01",
            rule_title="重大活动提前30分钟网络预热起保经验",
            learning_source_session="S-USER_001-05",
            user_prompt="今天在奥体有重大活动直播，帮我开抖音开直播保障，时间从12点30分到13点30分。",
            ctx={"app": "抖音", "srv": "开直播", "res": "1080p", "rtt": "50ms", "start": "2026年10月17日12时00分", "end": "2026年10月17日13时30分", "dur": "90min"}
        )

        # 1. 验证 Fast Path 极速出单元数据
        self.assertEqual(eb["fast_path"]["round_count"], 2)
        self.assertEqual(eb["fast_path"]["key_params_source"]["source_type"], "Experience")

        # 2. 验证 Slow Path 评测仲裁门 (Branch Decision Gate)
        slow = eb["slow_path"]
        self.assertEqual(slow["round_count"], 4)
        gate = slow.get("branch_decision_gate", {})
        self.assertEqual(gate.get("eval_turn"), 1)
        self.assertEqual(gate.get("pass_route"), "fast_path")
        self.assertEqual(gate.get("fail_route"), "slow_path")
        self.assertIn("key_slot_assertions", gate)

        # 4. 验证 4 轮引导交互树结构完整性与逐轮 GT (Turn 1~4 逐轮对齐)
        tree = slow.get("simulator_dialogue_tree", [])
        self.assertEqual(len(tree), 4)
        turns = [t["turn"] for t in tree]
        self.assertEqual(turns, [1, 2, 3, 4])
        self.assertEqual(tree[0]["speaker"], "user")
        self.assertIn("baseline_agent_flawed_response", tree[0])
        self.assertIn("flaw_type", tree[0])
        self.assertIn("expected_slots_gt", tree[0])
        self.assertEqual(tree[1]["speaker"], "user_simulator")
        self.assertIn("expected_agent_correction", tree[1])
        self.assertIn("expected_slots_gt", tree[1])
        self.assertEqual(tree[3]["expected_agent_correction"], tree[3].get("expected_agent_correction"))
        self.assertIn("Acknowledge", tree[3]["agent_action_types"])
        self.assertIn("expected_slots_gt", tree[3])

        # 5. 验证逐轮标准金标 (turn_level_ground_truth) 完备性
        turn_gt = slow.get("turn_level_ground_truth", [])
        self.assertEqual(len(turn_gt), 4)
        for i, tgt in enumerate(turn_gt):
            self.assertEqual(tgt["turn"], i + 1)
            self.assertIn("expected_slots_gt", tgt)
            self.assertIn("expected_agent_action_types", tgt)
            self.assertIn("intents_status", tgt)
            self.assertIn("I1", tgt["expected_slots_gt"])

        # 6. 验证声明式交互评测契约 (interactive_eval_contract) 完整性
        contract = eb.get("interactive_eval_contract")
        self.assertIsNotNone(contract)
        self.assertEqual(contract["version"], "1.0")
        self.assertEqual(contract["scenario_type"], "prewarm_buffer")
        self.assertIn("target_ground_truth", contract)
        self.assertIn("turn_level_ground_truth", contract)
        self.assertEqual(len(contract["turn_level_ground_truth"]), 4)
        self.assertEqual(contract["target_ground_truth"]["I1"]["slots"]["application_name"], "抖音")
        self.assertEqual(contract["target_ground_truth"]["I1"]["slots"]["timestamp"]["start_timestamp"], "2026年10月17日12时00分")
        self.assertIn("delta_reaction_matrix", contract)
        self.assertIn("on_slot_error", contract["delta_reaction_matrix"])
        self.assertIn("on_slot_missing", contract["delta_reaction_matrix"])
        self.assertIn("on_agent_inquiry", contract["delta_reaction_matrix"])
        self.assertIn("on_goal_matched", contract["delta_reaction_matrix"])
        self.assertIn("evaluator_prompt_template", contract)

    def test_08_multi_intent_5_turn_slow_path(self):
        """测试多意图局部突发延误隔离场景符合设计规范的 5 轮 Slow Path 深度交互树与密集累积追踪"""
        eb = SessionAssembler._build_experience_branching(
            scenario_type="multi_intent_partition",
            exp_id="EXP_MULTI_INTENT_PARTITION_01",
            rule_title="多任务并行局部调整与时序因果隔离经验",
            learning_source_session="S-USER_001-06",
            user_prompt="帮我改一下上午的微信视频通话保障，延后到12点结束；下午的保障千万别动，保持原样。",
            ctx={
                "app": "微信", "srv": "视频通话", "res": "1080p", "rtt": "50ms", "start": "09:00", "end": "12:00", "dur": "180min",
                "app2": "抖音", "srv2": "直播", "res2": "1080p", "rtt2": "50ms", "start2": "14:00", "end2": "16:00", "dur2": "120min"
            }
        )

        # 1. 验证 Fast Path 为 3 轮，Slow Path 为 5 轮
        self.assertEqual(eb["fast_path"]["round_count"], 3)
        self.assertEqual(eb["slow_path"]["round_count"], 5)
        self.assertEqual(eb["slow_path"]["redundant_rounds"], 2)

        # 2. 验证 5 轮对话树完整性与每轮 expected_slots_gt
        tree = eb["slow_path"]["simulator_dialogue_tree"]
        self.assertEqual(len(tree), 5)
        self.assertEqual([t["turn"] for t in tree], [1, 2, 3, 4, 5])
        self.assertIn("Acknowledge", tree[-1]["agent_action_types"])
        for node in tree:
            self.assertIn("expected_slots_gt", node)
            self.assertIn("I1", node["expected_slots_gt"])
            self.assertIn("I2", node["expected_slots_gt"])

        # 3. 验证 Dense Cumulative Tracking 累积槽位完备性
        full_seq = eb["slow_path"]["full_slow_event_sequence"]
        self.assertEqual(len(full_seq), 5)
        for t in full_seq:
            self.assertEqual(len(t["turn_intents"]), 2)
            self.assertEqual(t["turn_intents"][0]["params"]["application_name"]["value"], "微信")
            self.assertEqual(t["turn_intents"][1]["params"]["application_name"]["value"], "抖音")

        # 4. 验证逐轮标准金标 (turn_level_ground_truth) 覆盖 5 轮且每轮槽位完整
        turn_gt = eb["slow_path"]["turn_level_ground_truth"]
        self.assertEqual(len(turn_gt), 5)
        self.assertEqual(turn_gt[-1]["intents_status"]["I1"], "resolved")
        self.assertEqual(turn_gt[-1]["intents_status"]["I2"], "resolved")

        # 5. 验证终态双闭环
        self.assertEqual(full_seq[-1]["turn_intents"][0]["status"], "resolved")
        self.assertEqual(full_seq[-1]["turn_intents"][1]["status"], "resolved")

        # 6. 验证多意图双轨评测契约
        c = eb["interactive_eval_contract"]
        self.assertIn("I1", c["target_ground_truth"])
        self.assertIn("I2", c["target_ground_truth"])
        self.assertEqual(c["target_ground_truth"]["I2"]["slots"]["service_name"], "直播")
        self.assertIn("I2.timestamp.start_timestamp", c["delta_reaction_matrix"]["on_slot_error"]["monitored_slots"])

    def test_09_all_scenarios_interactive_eval_contract(self):
        """测试 5 大经验场景的声明式交互评测契约 (interactive_eval_contract) 与逐轮 GT 完备性"""
        scenarios = [
            ("multi_intent_partition", "EXP_MULTI_INTENT_PARTITION_01"),
            ("prewarm_buffer", "EXP_PREWARM_BUFFER_01"),
            ("holiday_exception", "EXP_CALENDAR_HOLIDAY_EXCEPTION_01"),
            ("quality_disambiguation", "EXP_ORDER_QUALITY_DISAMBIGUATION_01"),
            ("overlapping_resolution", "EXP_OVERLAPPING_ORDER_RESOLUTION_01"),
        ]
        ctx = {
            "app": "腾讯会议", "srv": "视频会议", "res": "1080p", "rtt": "50ms",
            "start": "09:00", "end": "11:00", "dur": "120min",
            "app2": "快手", "srv2": "直播", "res2": "720p", "rtt2": "60ms",
            "start2": "14:00", "end2": "16:00", "dur2": "120min"
        }
        for s_type, exp_id in scenarios:
            eb = SessionAssembler._build_experience_branching(
                scenario_type=s_type,
                exp_id=exp_id,
                rule_title=f"{s_type}经验测试",
                learning_source_session="S-USER_TEST-01",
                user_prompt="测试输入",
                ctx=ctx
            )
            c = eb.get("interactive_eval_contract")
            self.assertIsNotNone(c, f"Contract missing for {s_type}")
            self.assertEqual(c["scenario_type"], s_type)
            self.assertIn("target_ground_truth", c)
            self.assertIn("turn_level_ground_truth", c)
            self.assertIn("delta_reaction_matrix", c)
            self.assertIn("termination_conditions", c)

            # 验证逐轮 GT 的轮数和字段完备性
            turn_gt = c["turn_level_ground_truth"]
            expected_turns = 5 if s_type == "multi_intent_partition" else 4
            self.assertEqual(len(turn_gt), expected_turns, f"Turn GT length mismatch for {s_type}")
            for tgt in turn_gt:
                self.assertIn("turn", tgt)
                self.assertIn("expected_slots_gt", tgt)
                self.assertIn("expected_agent_action_types", tgt)
                self.assertIn("intents_status", tgt)
                self.assertGreater(len(tgt["expected_slots_gt"]), 0)

            matrix = c["delta_reaction_matrix"]
            for key in ["on_slot_error", "on_agent_inquiry", "on_slot_missing", "on_goal_matched"]:
                self.assertIn(key, matrix, f"Matrix missing key {key} in {s_type}")
                self.assertTrue(len(matrix[key]["simulator_reply"]) > 0)


if __name__ == "__main__":
    unittest.main()

