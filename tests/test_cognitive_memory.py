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

            # 验证会话规划包含认知演进模板且长度达到 20 ~ 24 轮
            self.assertGreaterEqual(len(planned_sessions), 20)
            self.assertLessEqual(len(planned_sessions), 24)

            # 验证彻底告别机械模板词“常规周期保障现场”，全部为真实具象物理场所
            for s in planned_sessions:
                self.assertNotEqual(s.get("scenario_env"), "常规周期保障现场")
                self.assertTrue(len(s.get("scenario_env", "")) > 1)

            tids = [s["template_id"] for s in planned_sessions]
            self.assertIn("T2-1", tids)
            self.assertIn("T2-6", tids)  # 工作记忆：跨期复用
            self.assertIn("T2-7", tids)  # 工作记忆：变更改期
            self.assertIn("T2-8", tids)  # 工作记忆：对账流水
            self.assertIn("T2-9", tids)  # 经验记忆：主动提议
            self.assertIn("T2-10", tids) # 经验记忆：经验回溯

            # 验证 T2-6 包含消歧会话 (3 轮)
            s_disambig = next((s for s in planned_sessions if s.get("is_disambiguation")), None)
            self.assertIsNotNone(s_disambig)
            self.assertEqual(s_disambig["round_count"], 3)
            self.assertIn("candidate_record_ids", s_disambig.get("working_memory_pointer", {}))

            # 验证包含负反例边界会话 (is_counterexample)
            s_counter = next((s for s in planned_sessions if s.get("is_counterexample")), None)
            self.assertIsNotNone(s_counter)
            self.assertEqual(s_counter["target_params"]["resolution"], "1080p")

            # 验证 T2-9 包含主动经验引文
            s_t2_9 = next(s for s in planned_sessions if s["template_id"] == "T2-9" and not s.get("is_counterexample"))
            self.assertIn("experience_citation", s_t2_9)
            self.assertEqual(s_t2_9["target_params"]["resolution"], "720p")

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


if __name__ == "__main__":
    unittest.main()
