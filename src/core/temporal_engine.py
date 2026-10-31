# -*- coding: utf-8 -*-
"""
时态推断与相对指代计算引擎 (TemporalEngine)
---------------------------------------------------------------
职责：
1. 精准解析多格式中文/标准日期时间字符串（如“2026年10月24日 14:00”、“2026-10-17 14:00”）；
2. 计算当前会话参考时点与历史意图保障单流水的时间差 Δt（天数差与时差）；
3. 实现时态相对代指的双向映射：
   - 正向：给定 Δt，生成自然口语表达（“昨天”、“前天”、“上周”、“上次”）；
   - 反向：给定用户口语输入与历史意图保障单库，精准检索目标意图保障单，并在多候选冲突时识别歧义（触发消歧判定）。
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


class TemporalEngine:
    """时态相对推断引擎"""

    @staticmethod
    def parse_datetime(dt_str: str) -> datetime:
        """鲁棒解析各类中文与标准日期时间字符串。"""
        if not dt_str or not isinstance(dt_str, str):
            raise ValueError(f"Invalid datetime input: {dt_str}")
        s = dt_str.strip()
        m_full = re.search(
            r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})[日号]?\s*(?:(\d{1,2})[时:点](\d{1,2})?(?:分|:(\d{1,2}))?)?',
            s,
        )
        if m_full:
            return datetime(
                int(m_full.group(1)),
                int(m_full.group(2)),
                int(m_full.group(3)),
                int(m_full.group(4)) if m_full.group(4) else 0,
                int(m_full.group(5)) if m_full.group(5) else 0,
                int(m_full.group(6)) if m_full.group(6) else 0,
            )
        m_no_year = re.search(
            r'(\d{1,2})[月\-/](\d{1,2})[日号]?\s*(?:(\d{1,2})[时:点](\d{1,2})?(?:分|:(\d{1,2}))?)?',
            s,
        )
        if m_no_year:
            return datetime(
                2026,
                int(m_no_year.group(1)),
                int(m_no_year.group(2)),
                int(m_no_year.group(3)) if m_no_year.group(3) else 0,
                int(m_no_year.group(4)) if m_no_year.group(4) else 0,
                0,
            )
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            pass
        raise ValueError(f"Unable to parse datetime string: {dt_str}")

    @staticmethod
    def format_cn_datetime(dt: datetime, include_minute: bool = True) -> str:
        """格式化为标准中文日期：'2026年10月24日 14:00'"""
        if include_minute:
            return dt.strftime("%Y年%m月%d日 %H:%M")
        return dt.strftime("%Y年%m月%d日")

    @classmethod
    def calculate_delta_days(cls, ref_time_str: str, target_time_str: str) -> int:
        """计算参考时间相对目标时间的日历日天数差 (ref - target)"""
        dt_ref = cls.parse_datetime(ref_time_str)
        dt_target = cls.parse_datetime(target_time_str)
        return (dt_ref.date() - dt_target.date()).days

    @classmethod
    def get_relative_temporal_term(cls, delta_days: int) -> str:
        """根据天数差获取最自然的口语指称词"""
        if delta_days == 0:
            return "今天"
        if delta_days == 1:
            return "昨天"
        if delta_days == 2:
            return "前天"
        if delta_days == 3:
            return "大前天"
        if 3 < delta_days <= 7:
            return "上周"
        if 7 < delta_days <= 14:
            return "两周前"
        if 14 < delta_days <= 35:
            return "上个月"
        if delta_days > 35:
            return f"{delta_days // 30}个月前"
        return "未来时段"

    @classmethod
    def generate_record_temporal_aliases(cls, current_ref_time: str, record: dict) -> Dict[str, str]:
        """为历史意图保障单生成基于当前时间点的所有自然时态别名引用。"""
        record_created_at = record.get("created_at") or record.get("start_timestamp")
        if not record_created_at:
            return {}
        delta_days = cls.calculate_delta_days(current_ref_time, record_created_at)
        loc = record.get("location") or "外勤现场"
        app = record.get("application_name") or ""
        srv = record.get("service_name") or "保障"
        rel_term = cls.get_relative_temporal_term(delta_days)
        aliases = {
            f"offset_{delta_days}d": f"{rel_term}开的{srv}",
            "temporal_label": rel_term,
        }
        if delta_days == 1:
            aliases["day_offset_1"] = f"昨天在{loc}办的{srv}"
            aliases["spoken_compact"] = f"昨天的{srv}"
        elif delta_days == 2:
            aliases["day_offset_2"] = f"前天在{loc}的{srv}"
        elif 3 <= delta_days <= 7:
            aliases["day_offset_7"] = f"上周在{loc}办的{srv}"
            aliases["spoken_compact"] = f"上周开的{srv}"
            aliases["spoken_weekday"] = "上周同期的保障"
        if loc:
            aliases["location_ref"] = f"上次在{loc}开的那个"
        aliases["last_similar"] = f"上次办的{app}{srv}"
        return aliases

    @staticmethod
    def _match_temporal_window(query_text: str) -> Tuple[Optional[Tuple[int, int]], Optional[str]]:
        temporal_rules = [
            (r'昨天|昨儿|昨日', 1, 1),
            (r'前天', 2, 2),
            (r'大前天', 3, 3),
            (r'上周|上个礼拜|上星期', 3, 7),
            (r'两周前|半个月前', 8, 16),
            (r'上个月|上月', 20, 35),
            (r'上次|上回|之前办的', 0, 90),
        ]
        for pat, min_d, max_d in temporal_rules:
            m = re.search(pat, query_text)
            if m:
                return (min_d, max_d), m.group()
        return None, None

    @staticmethod
    def _score_record_content(query_text: str, rec: Dict[str, Any]) -> int:
        app = rec.get("application_name", "")
        srv = rec.get("service_name", "")
        loc = rec.get("location", "")
        score = 0
        if app and (app in query_text or (len(app) >= 2 and app[:2] in query_text)):
            score += 3
        if srv and (srv in query_text or any(p in query_text for p in [srv.replace("赛事", ""), srv.replace("业务", ""), srv[:2]] if len(p) >= 2)):
            score += 3
        if loc and (
            loc in query_text
            or any(
                clean_loc in query_text
                for clean_loc in [loc.replace("看台", ""), loc.replace("现场", ""), loc.replace("中心", ""), loc[:4], loc[:2]]
                if len(clean_loc) >= 2
            )
        ):
            score += 2
        if "会议" in query_text and "会议" in srv:
            score += 2
        if "直播" in query_text and "直播" in srv:
            score += 2
        return score

    @classmethod
    def _collect_valid_candidates(
        cls,
        query_text: str,
        current_time: str,
        candidate_records: List[Dict[str, Any]],
        matched_window: Optional[Tuple[int, int]],
    ) -> List[Dict[str, Any]]:
        valid_candidates = []
        for rec in candidate_records:
            rec_created = rec.get("created_at") or rec.get("start_timestamp")
            if not rec_created:
                continue
            try:
                delta = cls.calculate_delta_days(current_time, rec_created)
            except (ValueError, TypeError):
                continue
            score = cls._score_record_content(query_text, rec)
            if matched_window:
                min_d, max_d = matched_window
                if min_d <= delta <= max_d:
                    valid_candidates.append({"record": rec, "delta_days": delta, "content_score": score})
            else:
                valid_candidates.append({"record": rec, "delta_days": delta, "content_score": score})
        return valid_candidates

    @classmethod
    def resolve_temporal_query(
        cls,
        query_text: str,
        current_time: str,
        candidate_records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """给定用户的自然语言输入与历史意图保障单候选集，解析时态意图与目标意图保障单。"""
        if not candidate_records:
            return {
                "status": "not_found",
                "target_record": None,
                "reason": "历史意图保障单账本为空，无法执行跨期复用",
            }
        matched_window, matched_term = cls._match_temporal_window(query_text)
        valid_candidates = cls._collect_valid_candidates(query_text, current_time, candidate_records, matched_window)
        if not valid_candidates:
            return {
                "status": "not_found",
                "matched_term": matched_term,
                "target_record": None,
                "reason": f"未在{matched_term or '指定'}时间范围内检索到符合条件的履约意图保障单",
            }

        def _rank_key(c: Dict[str, Any]) -> Tuple[int, int]:
            center = 7 if matched_window == (3, 7) else (1 if matched_window == (1, 1) else 0)
            proximity = -abs(c["delta_days"] - center) if center > 0 else -c["delta_days"]
            return (c["content_score"], proximity)

        valid_candidates.sort(key=_rank_key, reverse=True)
        top_cand = valid_candidates[0]
        max_score = top_cand["content_score"]
        tied_candidates = [
            c for c in valid_candidates if c["content_score"] == max_score and c["delta_days"] == top_cand["delta_days"]
        ]
        if len(tied_candidates) > 1 and max_score <= 1:
            return {
                "status": "ambiguous",
                "matched_term": matched_term,
                "need_disambiguation": True,
                "candidates": [c["record"] for c in tied_candidates],
                "reason": f"在{matched_term}时间段内定位到 {len(tied_candidates)} 条不同保障单据，无法独立推断，需向用户确认具体业务。",
            }
        target_rec = top_cand["record"]
        return {
            "status": "matched",
            "matched_term": matched_term,
            "target_record": target_rec,
            "inferred_delta_days": top_cand["delta_days"],
            "inherited_slots": {
                "resolution": target_rec.get("resolution"),
                "rtt_max": target_rec.get("rtt_max"),
                "duration": target_rec.get("duration"),
                "application_name": target_rec.get("application_name"),
                "service_name": target_rec.get("service_name"),
            },
            "need_disambiguation": False,
        }
