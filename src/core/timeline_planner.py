"""
动态时间线规划器模块 (DynamicTimelinePlanner).
负责根据 Persona Skeleton 动态规划多会话认知演进时间线，并绑定记忆触发类型、声明模式与业务参数。
"""

from __future__ import annotations

import hashlib
import re
from src.core.experience_bank import ExperienceBank
from src.core.small_memory_selector import build_small_memory_candidates
from src.core.temporal_engine import TemporalEngine
from src.core.working_records_ledger import WorkingRecordsLedger
from src.templates.prompts import (
    LOCATION_EXTRACTION_SYSTEM_PROMPT,
    LOCATION_EXTRACTION_USER_TEMPLATE,
)
from src.templates.timeline_blueprints import get_15_session_blueprints, get_session_blueprints


class DynamicTimelinePlanner:
    """时间线规划器 (DynamicTimelinePlanner)."""

    CATEGORY_VENUE_MAP = {
        "体育训练与赛事保障": ["露天高山滑雪训练基地", "体育公园综合集训场", "奥体中心多功能馆"],
        "交通运输与移动出行": ["智慧交通综合调度中心", "公路客运中转服务区", "高铁物流综合集散站"],
        "公共事务与外勤协作": ["高新区政企服务示范中心", "政务便民综合服务大厅", "行政审批服务综合大厅"],
        "公共安全与移动执勤": ["沿海治安综合巡逻站", "城市综合执勤前沿站点", "应急联动调度指挥站"],
        "医疗健康与移动服务": ["社区巡回流动诊疗大厅", "公共卫生移动保障中心", "康复医疗巡诊服务站"],
        "技术研发与现场支持": ["软件产业园创新中心", "智能制造现场工程指挥部", "高新试验测试基地"],
        "文化创作与移动演出": ["文创园数字演播中心", "大剧院户外彩排中心", "影视传媒数字创作基地"],
        "科研调查与移动协作": ["野外生态科考大本营", "地质勘查巡回工作站", "综合科学实验工作站"],
        "移动学习与教育协作": ["智慧教育研修示范中心", "青年公益活动交流中心", "高校实训教学研讨厅"],
        "移动生活与现场协作": ["社区综合文化活动中心", "青年创客交流示范基地", "市民文化生活多功能厅"],
        "移动经营与客户服务": ["金融街财富管理中心", "国际会展商务交流中心", "商贸中心数字展销大厅"],
        "移动采编与内容生产": ["全媒体新闻采编演播中心", "新媒体户外直播工作站", "融媒体外景采编演播厅"],
        "野外科研与农业作业": ["现代农业试验示范园区", "生态农业科研实验区", "林业生态野外观测站"],
    }

    @classmethod
    def _select_small_memory(cls, user_id: str, blueprint_type: str, source: dict, target_params: dict) -> dict:
        """从可用别名维度中做稳定随机选择，确保重跑可复现且后续复用一致。"""
        candidates = build_small_memory_candidates(
            source,
            target_params,
            allow_service_default=(blueprint_type == "main"),
        )
        if not candidates:
            return {}
        if blueprint_type == "sub_01":
            res_candidates = [c for c in candidates if c["type"] == "resolution_alias"]
            if res_candidates:
                candidates = res_candidates
        digest = hashlib.sha256(f"{user_id}:{blueprint_type}".encode("utf-8")).digest()
        return candidates[int.from_bytes(digest[:4], "big") % len(candidates)]

    @classmethod
    def _determine_concrete_venue(cls, persona: dict, main_mt: dict, storyline_trigger_type: str, llm=None) -> str:
        """从用户画像职业、类别及任务中提炼具象化真实场所。"""
        task_name = main_mt.get("name", "")
        raw_trig_cond = main_mt.get("trigger_condition", "")
        identity = persona.get("static_profile", {}).get("identity", "")
        category = persona.get("category", "")
        user_id = persona.get("static_profile", {}).get("user_id", "")
        num_match = re.search(r'\d+', user_id)
        uid_num = int(num_match.group()) if num_match else 1

        patterns = [
            (r'滑雪|雪道|赛道|高山', "露天高山滑雪训练基地"),
            (r'体育馆|球场|田径|训练场', "体育公园综合集训场"),
            (r'金融|顾问|理财|路演', "金融街财富管理中心"),
            (r'文创|新媒体|短视频|演播', "文创园数字演播中心"),
            (r'影视|剧组|拍摄|采风', "影视传媒数字创作基地"),
            (r'公益|志愿|社区|社群', "市青年公益服务中心"),
            (r'申报|政务|行政|园区', "高新技术产业园示范中心"),
            (r'巡逻|执勤|治安|港口', "沿海治安综合巡逻站"),
            (r'医疗|急救|诊疗|康复', "社区巡回医疗健康中心"),
            (r'农田|科研|地质|勘查', "生态农业科研示范园区"),
            (r'物流|交通|枢纽|调度', "智慧交通综合调度中心"),
        ]
        combined_text = f"{identity} {raw_trig_cond} {task_name}"
        for pat, loc in patterns:
            if re.search(pat, combined_text):
                return loc

        venue_options = cls.CATEGORY_VENUE_MAP.get(category)
        if venue_options:
            return venue_options[uid_num % len(venue_options)]
        return "企业总部多功能路演大厅"

    @staticmethod
    def _extract_clean_location(raw_cond: str, task_name: str) -> str:
        """从 trigger_condition 中提炼简短自然的地点环境名称（4-8字）。"""
        if not raw_cond:
            return "企业总部多功能路演大厅"
        patterns = [
            (r'道路巡逻|巡逻线|事故现场|移动执勤', "道路综合执勤现场"),
            (r'社区走访|走访点|临时会议', "社区综合走访现场"),
            (r'户外现场|晚间户外|临时停留点|等候区', "户外巡查工作现场"),
            (r'街区采访|拍摄地|遮挡区域', "街区新闻采访现场"),
            (r'沿海公路|巡逻岸线|集结区', "沿海综合巡逻岸线"),
            (r'高山|登山口|露天训练|偏远山区', "高山露天训练基地"),
        ]
        for pat, loc in patterns:
            if re.search(pat, raw_cond):
                return loc

        m = re.search(r'(?:身处|在|进入)([^，,。、\s]{2,8}(?:走访点|现场|岸线|训练场|营区|路线|区域|停留点|大厅|中心|基地))', raw_cond)
        if m:
            clean = m.group(1).replace("等", "")
            return clean if len(clean) <= 8 else f"{clean[:6]}现场"

        clean_task = re.sub(r'(?:任务|保障|协同|即时调度|回传|上传|与|及)', '', task_name or '')
        if clean_task and 2 <= len(clean_task) <= 8:
            return f"{clean_task}现场"
        return "企业总部多功能路演大厅"

    @classmethod
    def _extract_location_with_llm(cls, llm, raw_trig_cond: str, task_name: str, identity: str = "") -> str:
        """利用大模型从复杂场景长句中提炼出适合日常口语对话的地点/现场名称（3-7个汉字）。"""
        if not llm:
            return cls._extract_clean_location(raw_trig_cond, task_name)

        prompt = LOCATION_EXTRACTION_USER_TEMPLATE.format(
            identity=identity,
            task_name=task_name,
            raw_trig_cond=raw_trig_cond,
        )
        messages = [
            {"role": "system", "content": LOCATION_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        try:
            res = llm.chat_json(messages, enable_thinking=False)
            if isinstance(res, dict) and res.get("location_name"):
                loc = re.sub(r'[，,。、\s]', '', str(res["location_name"]).strip())
                if 2 <= len(loc) <= 10 and not any(k in loc for k in ["当", "进入", "触发", "需要", "时段", "办事"]):
                    return loc
        except (ValueError, TypeError, KeyError, RuntimeError):
            pass
        return cls._extract_clean_location(raw_trig_cond, task_name)

    @classmethod
    def _extract_storyline_context(cls, persona: dict, llm, experience_bank: ExperienceBank) -> dict:
        """从画像骨架提取主线、支线、干扰项与触发控制上下文。"""
        user_id = persona["static_profile"]["user_id"]
        dyn = persona["dynamic_profile"]
        main_mt = dyn["periodic_main_storyline"]
        scenario_events = dyn.get("scenario_events", [])
        sub_list = dyn.get("sub_storylines", [])
        dist_list = dyn.get("distractor_pool", [])

        sub_01 = sub_list[0] if len(sub_list) > 0 else main_mt
        sub_02 = sub_list[1] if len(sub_list) > 1 else sub_01
        dist_01 = dist_list[0] if len(dist_list) > 0 else sub_01
        dist_02 = dist_list[1] if len(dist_list) > 1 else dist_01
        evt_01 = scenario_events[0] if len(scenario_events) > 0 else {
            "preference_override": {"resolution": "720p", "rtt_max": "30ms"},
            "event_name": "临时特殊场景保障",
            "scene_description": "现场人流拥塞临时防抖保障",
        }

        num_match = re.search(r'\d+', user_id)
        uid_num = int(num_match.group()) if num_match else 1
        decl_mode = "explicit_declaration" if (uid_num % 2 == 1) else "implicit_induction"

        explicit_trig_type = main_mt.get("storyline_trigger_type")
        if explicit_trig_type in ["time_periodic", "task_activity", "location_environment"]:
            storyline_trigger_type = explicit_trig_type
        else:
            trig_mod = uid_num % 3
            storyline_trigger_type = "time_periodic" if trig_mod == 1 else ("task_activity" if trig_mod == 2 else "location_environment")

        task_name = main_mt.get("name", "业务现场任务")
        raw_trig_cond = main_mt.get("trigger_condition")
        main_env_desc = cls._determine_concrete_venue(persona, main_mt, storyline_trigger_type, llm=llm)
        main_trigger_desc = raw_trig_cond if raw_trig_cond else f"在【{main_env_desc}】例行开展业务"
        target_count = 16 + (uid_num % 5)
        selected_exp_ids = experience_bank.select_persona_experiences(persona, target_count=2)

        return {
            "user_id": user_id,
            "main_mt": main_mt,
            "sub_01": sub_01,
            "sub_02": sub_02,
            "dist_01": dist_01,
            "dist_02": dist_02,
            "evt_01": evt_01,
            "decl_mode": decl_mode,
            "storyline_trigger_type": storyline_trigger_type,
            "task_name": task_name,
            "main_env_desc": main_env_desc,
            "main_trigger_desc": main_trigger_desc,
            "target_count": target_count,
            "selected_exp_ids": selected_exp_ids,
        }

    @classmethod
    def _plan_working_memory_for_blueprint(
        cls, cfg: dict, template_id: str, user_id: str, src: dict, res: str, rtt: str, working_ledger: WorkingRecordsLedger
    ) -> tuple[dict, dict]:
        """规划工作记忆指针 (T2-6/T2-7) 与工作记忆流水查询 (T2-8)。"""
        working_memory_pointer: dict = {}
        working_memory_query: dict = {}
        is_disambig = cfg.get("tag") == "wm_disambig"

        if template_id == "T2-6":
            is_long_reuse = cfg.get("tag") == "wm_long_reuse"
            prior_recs = working_ledger.query_prior_records(cfg["ref_time"])
            target_rec = (
                prior_recs[0]
                if (is_long_reuse and prior_recs)
                else (next((r for r in prior_recs if r.get("application_name") == src["application_name"]), prior_recs[-1]) if prior_recs else None)
            )
            cand_ids = [r["record_id"] for r in prior_recs[:2]] if len(prior_recs) >= 2 else (
                [target_rec["record_id"]] if target_rec else [f"REC_{user_id}_20261010_01", f"REC_{user_id}_20261013_02"]
            )
            if target_rec:
                working_memory_pointer = working_ledger.generate_session_pointer(target_rec, cfg["ref_time"])
                if is_disambig:
                    working_memory_pointer["candidate_record_ids"] = cand_ids
                    working_memory_pointer["is_disambiguation"] = True
            else:
                working_memory_pointer = {
                    "target_record_id": f"REC_{user_id}_20261005_01",
                    "candidate_record_ids": cand_ids if is_disambig else [],
                    "inferred_delta_days": 30 if is_long_reuse else 7,
                    "matched_application": src["application_name"],
                    "matched_service": src["service_name"],
                    "inherited_slots": {"resolution": res, "rtt_max": rtt, "duration": cfg["dur"]},
                    "is_disambiguation": is_disambig,
                }
        elif template_id == "T2-7":
            is_advance = cfg.get("tag") == "wm_reschedule_2"
            prior_recs = working_ledger.query_prior_records(cfg["ref_time"])
            target_rec = prior_recs[-1] if prior_recs else None
            if target_rec:
                d_days = TemporalEngine.calculate_delta_days(cfg["ref_time"], target_rec.get("created_at") or target_rec.get("start_timestamp"))
                working_memory_pointer = {
                    "target_record_id": target_rec["record_id"],
                    "inferred_delta_days": d_days,
                    "matched_application": target_rec.get("application_name"),
                    "matched_service": target_rec.get("service_name"),
                    "modified_slots": {"start_timestamp": cfg["start"], "end_timestamp": cfg["end"]},
                    "reschedule_direction": "advance" if is_advance else "delay",
                }
            else:
                working_memory_pointer = {
                    "target_record_id": f"REC_{user_id}_PRIOR",
                    "inferred_delta_days": 1,
                    "matched_application": src["application_name"],
                    "matched_service": src["service_name"],
                    "modified_slots": {"start_timestamp": cfg["start"], "end_timestamp": cfg["end"]},
                    "reschedule_direction": "advance" if is_advance else "delay",
                }
        elif template_id == "T2-8":
            all_recs = working_ledger.get_all_records()
            is_month_end = cfg.get("tag") == "wm_reconcile_month"
            subset_recs = all_recs if is_month_end else all_recs[: min(7, len(all_recs))]
            working_memory_query = {
                "reconciled_record_ids": [r["record_id"] for r in subset_recs],
                "total_orders": len(subset_recs) if subset_recs else 3,
                "total_duration_minutes": sum(int(re.search(r'\d+', r.get("duration", "60")).group()) for r in subset_recs if re.search(r'\d+', r.get("duration", ""))) or 360,
                "reconcile_scope": "全月总对账" if is_month_end else "半月阶段对账",
            }
        return working_memory_pointer, working_memory_query

    @staticmethod
    def _resolve_order_quality_pointer(cfg: dict, user_id: str, src: dict, working_ledger: WorkingRecordsLedger) -> dict:
        prior_recs = working_ledger.query_prior_records(cfg["ref_time"])
        target_rec = next(
            (r for r in prior_recs if r.get("duration") == cfg["dur"] and r.get("application_name") == src["application_name"]),
            next((r for r in prior_recs if r.get("duration") == cfg["dur"]), prior_recs[0] if prior_recs else None),
        )
        if target_rec:
            ptr = working_ledger.generate_session_pointer(target_rec, cfg["ref_time"])
            ptr["duration_filtered"] = True
            ptr["selected_order_duration"] = f"formal_roadshow_{cfg['dur']}"
            return ptr
        return {
            "target_record_id": f"REC_{user_id}_20261010_01",
            "candidate_record_ids": [f"REC_{user_id}_20261010_01", f"REC_{user_id}_20261013_02"],
            "inferred_delta_days": 7,
            "matched_application": src["application_name"],
            "matched_service": src["service_name"],
            "inherited_slots": {"duration": cfg["dur"]},
            "duration_filtered": True,
            "selected_order_duration": f"formal_roadshow_{cfg['dur']}",
        }

    @classmethod
    def _plan_experience_for_blueprint(
        cls,
        cfg: dict,
        template_id: str,
        user_id: str,
        task_name: str,
        src: dict,
        base_res: str,
        base_rtt: str,
        res: str,
        rtt: str,
        round_count: int,
        working_ledger: WorkingRecordsLedger,
        experience_bank: ExperienceBank,
    ) -> tuple[dict, dict, str, str]:
        """规划经验记忆引用卡片 (experience_citation) 及关联的工作记忆指针。"""
        experience_citation: dict = {}
        working_memory_pointer: dict = {}
        is_counterexample = cfg.get("is_counterexample", False)

        if cfg.get("experience_id"):
            exp_id = cfg["experience_id"]
            exp = experience_bank.find_by_id(exp_id) or {}
            experience_citation = {
                "experience_id": exp.get("experience_id", exp_id),
                "title": exp.get("title", "ReasoningBank经验策略"),
                "strategy_type": exp.get("strategy_type", "proactive_suggestion"),
                "suggested_adjustments": exp.get("recommended_adjustments", {}),
                "condition": exp.get("condition") or str(exp.get("trigger_conditions", {})),
                "action": exp.get("action") or str(exp.get("recommended_adjustments", {})),
                "validity": exp.get("validity") or str(exp.get("applicable_boundaries", "")),
            }
            if exp_id in ("EXP_PREWARM_BUFFER_01", "EXP_MULTI_INTENT_PARTITION_01", "EXP_OVERLAPPING_ORDER_RESOLUTION_01"):
                res, rtt = base_res, base_rtt
            elif exp_id == "EXP_ORDER_QUALITY_DISAMBIGUATION_01":
                working_memory_pointer = cls._resolve_order_quality_pointer(cfg, user_id, src, working_ledger)
        elif template_id == "T2-9":
            exp = experience_bank.find_by_id("EXP_PREWARM_BUFFER_01") or experience_bank.match_proactive_experience(cfg["env"], task_name) or experience_bank.find_by_id("EXP_STADIUM_CONGESTION_01")
            if is_counterexample:
                experience_citation = {
                    "experience_id": exp["experience_id"],
                    "title": exp["title"],
                    "strategy_type": "negative_counterexample",
                    "negative_counterexamples": exp.get("negative_counterexamples", ""),
                    "counterexample_applied": True,
                }
                res, rtt = base_res, base_rtt
            else:
                experience_citation = {
                    "experience_id": exp["experience_id"],
                    "title": exp["title"],
                    "strategy_type": exp["strategy_type"],
                    "suggested_adjustments": exp.get("recommended_adjustments", {}),
                    "condition": exp.get("condition") or "识别重大活动或大型直播现场，需提前预热试机",
                    "action": exp.get("action") or "起保时间提前30分钟，保障时长扩充30分钟",
                    "validity": exp.get("validity") or exp.get("applicable_boundaries", ""),
                    "negotiation_required": round_count == 3,
                }
                res = exp.get("recommended_adjustments", {}).get("resolution") or base_res
                rtt = exp.get("recommended_adjustments", {}).get("rtt_max") or base_rtt
        elif template_id == "T2-10":
            exp = experience_bank.find_by_id("EXP_OVERLAPPING_ORDER_RESOLUTION_01") or experience_bank.find_by_id("EXP_SEVERE_WEATHER_01")
            experience_citation = {
                "experience_id": exp["experience_id"],
                "title": exp["title"],
                "strategy_type": exp["strategy_type"],
                "suggested_adjustments": exp.get("recommended_adjustments", {}),
                "condition": exp.get("condition") or "户外公园、营地或广场活动意图保障单，收尾撤场存在边走边播移动转场与跨基站切换断流风险",
                "action": exp.get("action") or "保持 start_timestamp 不变，将意图保障单 end_timestamp 向后顺延30分钟，duration 增加30分钟",
                "validity": exp.get("validity") or exp.get("applicable_boundaries", ""),
            }
        return experience_citation, working_memory_pointer, res, rtt

    @classmethod
    def _resolve_base_and_override_params(cls, cfg: dict, src: dict) -> tuple[str, str, str, str]:
        base_res = src.get("preferred_params", {}).get("resolution") or src.get("params", {}).get("resolution", "1080p")
        base_rtt = src.get("preferred_params", {}).get("rtt_max") or src.get("params", {}).get("rtt_max", "50ms")
        if "override" in cfg and cfg["type"] == "event_override":
            ov_res = cfg["override"].get("resolution") or ("720p" if base_res != "720p" else "1080p")
            if ov_res == base_res:
                ov_res = "720p" if base_res != "720p" else "1080p"
            ov_rtt = cfg["override"].get("rtt_max") or ("30ms" if base_rtt != "30ms" else "50ms")
            if ov_rtt == base_rtt:
                ov_rtt = "30ms" if base_rtt != "30ms" else ("80ms" if base_rtt != "80ms" else "50ms")
            return base_res, base_rtt, ov_res, ov_rtt
        return base_res, base_rtt, base_res, base_rtt

    @staticmethod
    def _resolve_retrieval_challenge(cfg: dict, tag: str | None, main_mt: dict, sub_01: dict) -> tuple[str | None, str | None, str | None]:
        challenge_type = cfg.get("retrieval_challenge_type") or (
            "negation_contrast" if tag in ("evt_correct", "dist_normal", "sub1_reuse_10") else (
                "paraphrased_alias_scene" if tag == "evt_reuse" else (
                    "implicit_service_collocation" if tag in ("main_amend", "sub2_reuse", "main_final") else None
                )
            )
        )
        neg_app = sub_01.get("application_name", "钉钉") if tag == "evt_correct" else (main_mt.get("application_name", "抖音") if tag in ("dist_normal", "sub1_reuse_10") else None)
        neg_srv = sub_01.get("service_name", "视频会议") if tag == "evt_correct" else (main_mt.get("service_name", "开直播") if tag in ("dist_normal", "sub1_reuse_10") else None)
        return challenge_type, neg_app, neg_srv

    @staticmethod
    def _resolve_second_target_params(cfg: dict, src: dict, main_mt: dict, base_res: str, base_rtt: str) -> dict | None:
        """为多意图模版 (T1-3 / T2-4) 动态解析第 2 个正常意图 (I2) 的完整参数字典。"""
        if cfg.get("template_id") not in ("T1-3", "T2-4"):
            return None
        mode = cfg.get("multi_intent_mode", "heterogeneous")
        start2 = cfg.get("start2") or cfg.get("start", "")
        end2 = cfg.get("end2") or cfg.get("end", "")
        dur2 = cfg.get("dur2") or cfg.get("base_dur") or cfg.get("dur", "60min")
        idx_seed = int(cfg.get("idx", 1)) * 31 + sum(ord(c) for c in str(src.get("application_name", "")))
        res_choices = ["1080p", "720p"]
        rtt_choices = ["30ms", "50ms", "80ms"]

        if mode == "homogeneous":
            srv2 = src["service_name"]
            if "直播" in srv2:
                pool = ["抖音", "快手", "哔哩哔哩", "小红书", "虎牙", "斗鱼"]
            elif "会议" in srv2:
                pool = ["腾讯会议", "钉钉", "飞书", "云视讯"]
            elif "通话" in srv2:
                pool = ["微信", "钉钉", "QQ"]
            elif "游戏" in srv2:
                pool = ["王者荣耀", "和平精英", "原神", "三角洲"]
            else:
                pool = ["抖音", "快手", "腾讯会议", "钉钉"]
            candidates = [a for a in pool if a != src["application_name"]] or ["快手"]
            app2 = candidates[idx_seed % len(candidates)]
            res2 = base_res if (idx_seed % 2 == 0) else res_choices[(idx_seed // 2) % len(res_choices)]
            rtt2 = base_rtt if (idx_seed % 2 == 0) else rtt_choices[(idx_seed // 3) % len(rtt_choices)]
            return {
                "application_name": app2, "service_name": srv2,
                "resolution": res2, "rtt": rtt2,
                "start_timestamp": start2, "end_timestamp": end2, "duration": dur2,
            }
        if cfg.get("experience_id") == "EXP_MULTI_INTENT_PARTITION_01":
            app2, srv2 = main_mt.get("application_name", "抖音"), main_mt.get("service_name", "开直播")
            if app2 == "微信" and srv2 == "视频通话":
                app2, srv2 = "抖音", "开直播"
            return {
                "application_name": app2, "service_name": srv2,
                "resolution": base_res, "rtt": base_rtt,
                "start_timestamp": start2, "end_timestamp": end2, "duration": dur2,
            }
        sec = cfg.get("second_source") or main_mt
        app2 = sec.get("application_name", "抖音")
        srv2 = sec.get("service_name", "开直播")
        if srv2 == src["service_name"] or app2 == src["application_name"]:
            het_options = [("微信", "视频通话"), ("腾讯会议", "视频会议"), ("钉钉", "视频会议"), ("抖音", "开直播"), ("快手", "开直播")]
            valid_het = [(a, s) for a, s in het_options if a != src["application_name"] and s != src["service_name"]]
            app2, srv2 = valid_het[idx_seed % len(valid_het)]
        sec_p = sec.get("preferred_params") or sec.get("params") or {}
        res2 = sec_p.get("resolution") or res_choices[idx_seed % len(res_choices)]
        rtt2 = sec_p.get("rtt_max") or rtt_choices[(idx_seed // 2) % len(rtt_choices)]
        return {
            "application_name": app2, "service_name": srv2,
            "resolution": res2, "rtt": rtt2,
            "start_timestamp": start2, "end_timestamp": end2, "duration": dur2,
        }

    @classmethod
    def _build_planned_session_item(
        cls,
        cfg: dict,
        s_ctx: dict,
        tag_to_sid: dict[str, str],
        working_ledger: WorkingRecordsLedger,
        experience_bank: ExperienceBank,
    ) -> dict:
        """将单个蓝图配置槽位转化为完整的规划会话字典 (s_obj)。"""
        user_id, main_mt, sub_01 = s_ctx["user_id"], s_ctx["main_mt"], s_ctx["sub_01"]
        learning_source_session = tag_to_sid.get(cfg.get("learning_source_session_tag"))
        src = cfg["source"]
        base_res, base_rtt, res, rtt = cls._resolve_base_and_override_params(cfg, src)

        if cfg["type"].startswith("distractor"):
            aliases, small_memory = {}, {}
        else:
            aliases = src.get("aliases", {})
            small_memory = cls._select_small_memory(user_id, cfg["type"], src, {"resolution": res, "rtt": rtt, "duration": cfg["dur"]})

        evidence_mode = {"main": "co_occurrence", "sub_01": "cross_turn_clarification", "sub_02": "explicit_declaration"}.get(cfg["type"], "explicit_declaration") if small_memory else "none"
        round_count = cfg.get("round_count") or (1 if (cfg["template_id"].startswith("T1") or cfg["template_id"].startswith("X-1") or cfg["template_id"] == "T2-8") else 2)
        template_id = cfg["template_id"]
        if cfg["role"] == "evidence_session" and evidence_mode == "cross_turn_clarification":
            round_count, template_id = 3, "T3-1"

        if cfg.get("experience_id") or template_id in ("T2-9", "T2-10"):
            experience_citation, working_memory_pointer, res, rtt = cls._plan_experience_for_blueprint(
                cfg, template_id, user_id, s_ctx["task_name"], src, base_res, base_rtt, res, rtt, round_count, working_ledger, experience_bank
            )
            working_memory_query = {}
        else:
            experience_citation = {}
            working_memory_pointer, working_memory_query = cls._plan_working_memory_for_blueprint(
                cfg, template_id, user_id, src, res, rtt, working_ledger
            )

        tag, mem_tier = cfg.get("tag"), cfg.get("memory_tier", "factual_memory")
        is_hot_factual = cfg["role"] in ["reinforcement_session", "reuse_session"] and mem_tier == "factual_memory"
        challenge_type, neg_app, neg_srv = cls._resolve_retrieval_challenge(cfg, tag, main_mt, sub_01)
        second_tp = cls._resolve_second_target_params(cfg, src, main_mt, base_res, base_rtt)

        return {
            "session_id": f"S-{user_id}-{cfg['idx']:02d}", "user_id": user_id, "reference_time": cfg["ref_time"],
            "template_id": template_id, "memory_role": cfg["role"], "round_count": round_count,
            "blueprint_type": cfg["type"], "scenario_env": cfg["env"], "memory_action": cfg["action"], "memory_tier": mem_tier,
            "cold_hot_type": cfg.get("cold_hot_type") if "cold_hot_type" in cfg else ("hot_start" if is_hot_factual else ("cold_start" if mem_tier == "factual_memory" else None)),
            "agility_factor": cfg.get("agility_factor") if "agility_factor" in cfg else (0.5 if is_hot_factual else (0.0 if mem_tier == "factual_memory" else None)),
            "declaration_mode": cfg.get("declaration_mode", s_ctx["decl_mode"]),
            "storyline_trigger_type": cfg.get("storyline_trigger_type", s_ctx["storyline_trigger_type"] if cfg["type"].startswith("main") else "time_periodic"),
            "trigger_condition": cfg.get("trigger_condition", s_ctx["main_trigger_desc"] if cfg["type"].startswith("main") else ""),
            "ood_goal": cfg.get("ood_goal", ""),
            "target_params": {
                "application_name": "微信" if cfg.get("experience_id") == "EXP_MULTI_INTENT_PARTITION_01" else ("抖音" if cfg.get("experience_id") == "EXP_OVERLAPPING_ORDER_RESOLUTION_01" else src["application_name"]),
                "service_name": "视频通话" if cfg.get("experience_id") == "EXP_MULTI_INTENT_PARTITION_01" else ("开直播" if cfg.get("experience_id") == "EXP_OVERLAPPING_ORDER_RESOLUTION_01" else src["service_name"]),
                "resolution": res, "rtt": rtt, "start_timestamp": cfg["start"], "end_timestamp": cfg["end"], "duration": cfg["dur"],
            },
            "second_target_params": second_tp,
            "multi_intent_mode": cfg.get("multi_intent_mode"),
            "period_type": main_mt.get("period_type", "weekly"),
            "base_resolution": base_res, "base_rtt": base_rtt,
            "base_duration": cfg.get("base_dur", cfg["dur"]), "base_end_timestamp": cfg.get("base_end", cfg["end"]),
            "base_end": cfg.get("base_end"), "base_dur": cfg.get("base_dur"),
            "start2": cfg.get("start2"), "end2": cfg.get("end2"), "dur2": cfg.get("dur2"),
            "aliases": aliases, "small_memory": small_memory, "small_memory_evidence_mode": evidence_mode,
            "working_memory_pointer": working_memory_pointer, "working_memory_query": working_memory_query,
            "experience_citation": experience_citation, "is_counterexample": cfg.get("is_counterexample", False),
            "is_disambiguation": tag == "wm_disambig", "second_source": cfg.get("second_source"),
            "nominal_start": cfg.get("nominal_start"), "nominal_dur": cfg.get("nominal_dur"),
            "holiday_defer_date": cfg.get("holiday_defer_date"), "learning_source_session": learning_source_session,
            "experience_id": cfg.get("experience_id"), "retrieval_challenge_type": challenge_type,
            "contrast_negated_app": neg_app, "contrast_negated_service": neg_srv,
        }

    @classmethod
    def plan(cls, persona: dict, llm=None, working_ledger=None, experience_bank=None) -> list[dict]:
        user_id = persona["static_profile"]["user_id"]
        if working_ledger is None:
            working_ledger = WorkingRecordsLedger(user_id=user_id)
        if experience_bank is None:
            experience_bank = ExperienceBank()

        s_ctx = cls._extract_storyline_context(persona, llm, experience_bank)
        blueprint_configs = get_session_blueprints(
            main_mt=s_ctx["main_mt"],
            sub_01=s_ctx["sub_01"],
            sub_02=s_ctx["sub_02"],
            dist_01=s_ctx["dist_01"],
            dist_02=s_ctx["dist_02"],
            evt_01=s_ctx["evt_01"],
            decl_mode=s_ctx["decl_mode"],
            storyline_trigger_type=s_ctx["storyline_trigger_type"],
            main_env_desc=s_ctx["main_env_desc"],
            main_trigger_desc=s_ctx["main_trigger_desc"],
            target_count=s_ctx["target_count"],
            selected_exp_ids=s_ctx["selected_exp_ids"],
        )
        tag_to_sid = {cfg["tag"]: f"S-{user_id}-{cfg['idx']:02d}" for cfg in blueprint_configs}

        sessions = []
        for cfg in blueprint_configs:
            s_obj = cls._build_planned_session_item(cfg, s_ctx, tag_to_sid, working_ledger, experience_bank)
            if s_obj["template_id"] not in ["T1-2", "T2-8"]:
                new_rec = working_ledger.create_record_from_session(s_obj)
                working_ledger.append_record(new_rec)
            sessions.append(s_obj)

        return sessions


__all__ = ["DynamicTimelinePlanner", "get_session_blueprints", "get_15_session_blueprints"]
