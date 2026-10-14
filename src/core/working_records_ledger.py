# -*- coding: utf-8 -*-
"""
工作记忆独立工单账本管理器 (WorkingRecordsLedger)
---------------------------------------------------------------
职责：
1. 彻底落实架构解耦：将历史保障工单独立存储于 working_records.jsonl，
   绝不将冗余的工单全量嵌入每轮对话的 sessions.jsonl 中；
2. 负责每个用户生命周期内保障工单的生成、追加、持久化与结构化检索；
3. 为 sessions.jsonl 提供轻量化索引指针（working_memory_pointer），
   确保 Prompt 上下文精简高效，杜绝长文本剧烈膨胀。
"""

import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from src.core.temporal_engine import TemporalEngine


class WorkingRecordsLedger:
    """工作记忆工单流水账管理器"""

    def __init__(self, user_id: str, storage_path: Optional[Path] = None):
        self.user_id = user_id
        self.storage_path = Path(storage_path) if storage_path else None
        self.records: List[Dict[str, Any]] = []

        if self.storage_path and self.storage_path.exists():
            self.load()

    def load(self) -> None:
        """从独立 working_records.jsonl 中加载所有历史工单"""
        if not self.storage_path or not self.storage_path.exists():
            return
        self.records = []
        with open(self.storage_path, "r", encoding="utf-8") as f:
            for line in f:
                line_s = line.strip()
                if line_s:
                    try:
                        self.records.append(json.loads(line_s))
                    except Exception:
                        pass

    def save(self) -> None:
        """持久化保存至 working_records.jsonl"""
        if not self.storage_path:
            return
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as f:
            for rec in self.records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def create_record_from_session(
        self,
        s_plan: Dict[str, Any],
        status: str = "completed",
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        根据会话规划和已完成的会话参数，生成一条标准的独立工作工单记录。
        """
        sid = s_plan["session_id"]
        ref_time = s_plan["reference_time"]
        tp = s_plan["target_params"]
        env = s_plan.get("scenario_env", "常规作业现场")

        # 生成工单流水号：REC_{USER}_{YYYYMMDD}_{seq:02d}
        try:
            dt = TemporalEngine.parse_datetime(ref_time)
            date_str = dt.strftime("%Y%m%d")
        except Exception:
            date_str = "20261024"

        seq_num = len(self.records) + 1
        record_id = f"REC_{self.user_id}_{date_str}_{seq_num:02d}"

        record = {
            "record_id": record_id,
            "source_session_id": sid,
            "user_id": self.user_id,
            "created_at": ref_time,
            "application_name": tp["application_name"],
            "service_name": tp["service_name"],
            "start_timestamp": tp["start_timestamp"],
            "end_timestamp": tp["end_timestamp"],
            "duration": tp["duration"],
            "resolution": tp["resolution"],
            "rtt_max": tp["rtt"],
            "location": env,
            "execution_status": status,
            "notes": notes,
            "temporal_reference_aliases": TemporalEngine.generate_record_temporal_aliases(ref_time, {
                "created_at": ref_time,
                "location": env,
                "application_name": tp["application_name"],
                "service_name": tp["service_name"]
            })
        }
        return record

    def append_record(self, record: Dict[str, Any]) -> None:
        """追加工单并自动更新"""
        self.records.append(record)
        if self.storage_path:
            self.save()

    def get_all_records(self) -> List[Dict[str, Any]]:
        """获取当前用户所有历史工单"""
        return list(self.records)

    def find_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """按单据 ID 快速索引"""
        for r in self.records:
            if r.get("record_id") == record_id:
                return r
        return None

    def query_prior_records(self, before_time_str: str) -> List[Dict[str, Any]]:
        """检索指定时间点之前的所有历史有效工单（严禁未来单据倒灌）"""
        dt_before = TemporalEngine.parse_datetime(before_time_str)
        priors = []
        for r in self.records:
            t_str = r.get("created_at") or r.get("start_timestamp")
            if not t_str:
                continue
            try:
                dt_r = TemporalEngine.parse_datetime(t_str)
                if dt_r < dt_before:
                    priors.append(r)
            except Exception:
                pass
        return priors

    @classmethod
    def generate_session_pointer(
        cls,
        target_record: Dict[str, Any],
        current_time: str
    ) -> Dict[str, Any]:
        """
        为 sessions.jsonl 构造轻量化指针（Lightweight Pointer）。
        sessions 仅保存该指针，不冗余包含大段工单属性。
        """
        rec_time = target_record.get("created_at") or target_record.get("start_timestamp")
        delta_days = TemporalEngine.calculate_delta_days(current_time, rec_time)

        return {
            "target_record_id": target_record.get("record_id"),
            "inferred_delta_days": delta_days,
            "matched_application": target_record.get("application_name"),
            "matched_service": target_record.get("service_name"),
            "inherited_slots": {
                "resolution": target_record.get("resolution"),
                "rtt_max": target_record.get("rtt_max"),
                "duration": target_record.get("duration")
            }
        }
