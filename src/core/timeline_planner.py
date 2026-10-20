import hashlib
import re
from src.templates.timeline_blueprints import get_session_blueprints, get_15_session_blueprints
from src.core.small_memory_selector import build_small_memory_candidates
from src.core.working_records_ledger import WorkingRecordsLedger
from src.core.experience_bank import ExperienceBank
from src.core.temporal_engine import TemporalEngine

class DynamicTimelinePlanner:
    """
    时间线规划器 (DynamicTimelinePlanner)
    负责根据 Persona Skeleton 动态规划 15 会话时间线，
    并绑定记忆触发类型、声明模式与业务参数。
    """

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
            # 支线1为跨轮澄清消歧会话(T3-1)，契约严格消歧画质，必须使用画质别名(resolution_alias)
            res_candidates = [c for c in candidates if c["type"] == "resolution_alias"]
            if res_candidates:
                candidates = res_candidates
        digest = hashlib.sha256(f"{user_id}:{blueprint_type}".encode("utf-8")).digest()
        return candidates[int.from_bytes(digest[:4], "big") % len(candidates)]

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
    def _determine_concrete_venue(cls, persona: dict, main_mt: dict, storyline_trigger_type: str, llm=None) -> str:
        """从用户画像职业、类别及任务中提炼具象化真实场所（严禁出现'常规周期保障现场'等抽象研发用语）。"""
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
        """从 trigger_condition 中提炼简短自然的地点环境名称（4-8字），避免规则长句混入台词。"""
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
        """
        利用大模型从复杂场景长句中提炼出适合日常口语对话的地点/现场名称（3-7个汉字）。
        带有格式约束与规则兜底机制。
        """
        if not llm:
            return cls._extract_clean_location(raw_trig_cond, task_name)

        prompt = (
            f"请从以下人物背景、任务与场景描述中，提炼出 1 个最适合作为日常口语对话中【地点/现场】的简短名词短语。\n\n"
            f"用户职业身份：{identity}\n"
            f"任务名称：{task_name}\n"
            f"触发场景规则：{raw_trig_cond}\n\n"
            f"【要求】：\n"
            f"1. 必须是纯地点名词短语，长度在 3 到 7 个汉字之间（如：“道路巡逻现场”、“社区走访现场”、“沿海巡逻岸线”、“高山露天训练场”、“野外地质勘查区”）。\n"
            f"2. 严禁包含“当...时”、“触发现场...”、“需要...”等任何条件句式或动词引导词。\n"
            f"3. 仅输出 JSON 格式：{{\"location_name\": \"简短地点名\"}}"
        )
        messages = [
            {"role": "system", "content": "You are a concise location naming assistant. Output valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        try:
            res = llm.chat_json(messages, enable_thinking=False)
            if isinstance(res, dict) and res.get("location_name"):
                loc = str(res["location_name"]).strip()
                loc = re.sub(r'[，,。、\s]', '', loc)
                if 2 <= len(loc) <= 10 and not any(k in loc for k in ["当", "进入", "触发", "需要", "时段", "办事"]):
                    return loc
        except Exception:
            pass
        return cls._extract_clean_location(raw_trig_cond, task_name)

    @classmethod
    def plan(cls, persona: dict, llm=None, working_ledger=None, experience_bank=None) -> list[dict]:
        user_id = persona["static_profile"]["user_id"]
        if working_ledger is None:
            working_ledger = WorkingRecordsLedger(user_id=user_id)
        if experience_bank is None:
            experience_bank = ExperienceBank()
        main_mt = persona["dynamic_profile"]["periodic_main_storyline"]
        scenario_events = persona["dynamic_profile"].get("scenario_events", [])
        sub_list = persona["dynamic_profile"].get("sub_storylines", [])
        dist_list = persona["dynamic_profile"].get("distractor_pool", [])

        sub_01 = sub_list[0] if len(sub_list) > 0 else main_mt
        sub_02 = sub_list[1] if len(sub_list) > 1 else sub_01
        dist_01 = dist_list[0] if len(dist_list) > 0 else sub_01
        dist_02 = dist_list[1] if len(dist_list) > 1 else dist_01
        evt_01 = scenario_events[0] if len(scenario_events) > 0 else {
            "preference_override": {"resolution": "720p", "rtt_max": "30ms"},
            "event_name": "临时特殊场景保障",
            "scene_description": "现场人流拥塞临时防抖保障"
        }

        # 判定长期记忆声明模式：严格按人物ID进行50/50奇偶分流，保障显式声明与隐式归纳均匀分布
        num_match = re.search(r'\d+', user_id)
        uid_num = int(num_match.group()) if num_match else 1
        decl_mode = "explicit_declaration" if (uid_num % 2 == 1) else "implicit_induction"

        # 判定主线记忆触发类型：三大核心主线类型（周期时间型、任务/现场型、特定地点型）均匀分布
        explicit_trig_type = main_mt.get("storyline_trigger_type")
        if explicit_trig_type in ["time_periodic", "task_activity", "location_environment"]:
            storyline_trigger_type = explicit_trig_type
        else:
            trig_mod = uid_num % 3
            if trig_mod == 1:
                storyline_trigger_type = "time_periodic"
            elif trig_mod == 2:
                storyline_trigger_type = "task_activity"
            else:
                storyline_trigger_type = "location_environment"

        task_name = main_mt.get("name", "业务现场任务")
        raw_trig_cond = main_mt.get("trigger_condition")
        main_env_desc = cls._determine_concrete_venue(persona, main_mt, storyline_trigger_type, llm=llm)
        main_trigger_desc = raw_trig_cond if raw_trig_cond else f"在【{main_env_desc}】例行开展业务"

        # 会话数量支持根据画像与业务情境自然排期（16 ~ 20 轮深度认知演化）
        target_count = 16 + (uid_num % 5)

        # 动态筛选最适配当前画像的 1~2 个经验记忆场景（其余经验插槽自然降级为常规事实/工作记忆）
        selected_exp_ids = experience_bank.select_persona_experiences(persona, target_count=2)

        blueprint_configs = get_session_blueprints(
            main_mt=main_mt,
            sub_01=sub_01,
            sub_02=sub_02,
            dist_01=dist_01,
            dist_02=dist_02,
            evt_01=evt_01,
            decl_mode=decl_mode,
            storyline_trigger_type=storyline_trigger_type,
            main_env_desc=main_env_desc,
            main_trigger_desc=main_trigger_desc,
            target_count=target_count,
            selected_exp_ids=selected_exp_ids,
        )

        tag_to_sid = {cfg["tag"]: f"S-{user_id}-{cfg['idx']:02d}" for cfg in blueprint_configs}

        sessions = []
        for cfg in blueprint_configs:
            learning_source_session = tag_to_sid.get(cfg.get("learning_source_session_tag"))
            src = cfg["source"]
            is_override = "override" in cfg and cfg["type"] == "event_override"
            res = cfg["override"].get("resolution", "720p") if is_override else (
                src.get("preferred_params", {}).get("resolution") or src.get("params", {}).get("resolution", "1080p")
            )
            rtt = cfg["override"].get("rtt_max", "30ms") if is_override else (
                src.get("preferred_params", {}).get("rtt_max") or src.get("params", {}).get("rtt_max", "50ms")
            )

            if cfg["type"].startswith("distractor"):
                aliases = {}
                small_memory = {}
            else:
                aliases = src.get("aliases", {})
                small_memory = cls._select_small_memory(user_id, cfg["type"], src, {
                    "resolution": res,
                    "rtt": rtt,
                    "duration": cfg["dur"],
                })
            evidence_mode = {
                "main": "co_occurrence",
                "sub_01": "cross_turn_clarification",
                "sub_02": "explicit_declaration",
            }.get(cfg["type"], "explicit_declaration") if small_memory else "none"

            if cfg.get("round_count"):
                round_count = cfg["round_count"]
            else:
                round_count = 1 if (cfg["template_id"].startswith("T1") or cfg["template_id"].startswith("X-1") or cfg["template_id"] == "T2-8") else 2

            template_id = cfg["template_id"]
            if cfg["role"] == "evidence_session" and evidence_mode == "cross_turn_clarification":
                round_count = 3
                template_id = "T3-1"

            working_memory_pointer = {}
            working_memory_query = {}
            experience_citation = {}
            is_counterexample = cfg.get("is_counterexample", False)
            is_disambig = (cfg.get("tag") == "wm_disambig")

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
                    "validity": exp.get("validity") or str(exp.get("applicable_boundaries", ""))
                }
                if exp_id == "EXP_PREWARM_BUFFER_01":
                    res = src.get("preferred_params", {}).get("resolution") or "1080p"
                    rtt = src.get("preferred_params", {}).get("rtt_max") or "50ms"
                elif exp_id == "EXP_ORDER_QUALITY_DISAMBIGUATION_01":
                    prior_recs = working_ledger.query_prior_records(cfg["ref_time"])
                    target_rec = next((r for r in prior_recs if r.get("notes") != "network_jitter"), prior_recs[0] if prior_recs else None)
                    if target_rec:
                        working_memory_pointer = working_ledger.generate_session_pointer(target_rec, cfg["ref_time"])
                        working_memory_pointer["quality_filtered"] = True
                        working_memory_pointer["selected_order_quality"] = "flawless_zero_packet_loss"
                    else:
                        working_memory_pointer = {
                            "target_record_id": f"REC_{user_id}_20261010_01",
                            "candidate_record_ids": [f"REC_{user_id}_20261010_01", f"REC_{user_id}_20261013_02"],
                            "inferred_delta_days": 7,
                            "matched_application": src["application_name"],
                            "matched_service": src["service_name"],
                            "inherited_slots": {"resolution": res, "rtt_max": rtt, "duration": cfg["dur"]},
                            "quality_filtered": True,
                            "selected_order_quality": "flawless_zero_packet_loss"
                        }
                elif exp_id == "EXP_OVERLAPPING_ORDER_RESOLUTION_01":
                    prior_recs = working_ledger.query_prior_records(cfg["ref_time"])
                    if prior_recs:
                        target_rec = prior_recs[-1]
                        working_memory_pointer = {
                            "target_record_id": target_rec["record_id"],
                            "arbitration_type": "handover_early_termination",
                            "handover_timestamp": cfg["start"],
                            "original_scheduled_end": target_rec.get("end_timestamp"),
                            "conflict_resolved": True
                        }
                    else:
                        working_memory_pointer = {
                            "target_record_id": f"REC_{user_id}_PRIOR",
                            "arbitration_type": "handover_early_termination",
                            "handover_timestamp": cfg["start"],
                            "conflict_resolved": True
                        }
            elif template_id == "T2-6":
                is_long_reuse = (cfg.get("tag") == "wm_long_reuse")
                prior_recs = working_ledger.query_prior_records(cfg["ref_time"])
                if is_long_reuse and prior_recs:
                    target_rec = prior_recs[0]
                elif prior_recs:
                    target_rec = next((r for r in prior_recs if r.get("application_name") == src["application_name"]), prior_recs[-1])
                else:
                    target_rec = None

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
                        "is_disambiguation": is_disambig
                    }
            elif template_id == "T2-7":
                is_advance = (cfg.get("tag") == "wm_reschedule_2")
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
                        "reschedule_direction": "advance" if is_advance else "delay"
                    }
                else:
                    working_memory_pointer = {
                        "target_record_id": f"REC_{user_id}_PRIOR",
                        "inferred_delta_days": 1,
                        "matched_application": src["application_name"],
                        "matched_service": src["service_name"],
                        "modified_slots": {"start_timestamp": cfg["start"], "end_timestamp": cfg["end"]},
                        "reschedule_direction": "advance" if is_advance else "delay"
                    }
            elif template_id == "T2-8":
                all_recs = working_ledger.get_all_records()
                is_month_end = (cfg.get("tag") == "wm_reconcile_month")
                subset_recs = all_recs if is_month_end else all_recs[:min(7, len(all_recs))]
                working_memory_query = {
                    "reconciled_record_ids": [r["record_id"] for r in subset_recs],
                    "total_orders": len(subset_recs) if subset_recs else 3,
                    "total_duration_minutes": sum(int(re.search(r'\d+', r.get("duration", "60")).group()) for r in subset_recs if re.search(r'\d+', r.get("duration", ""))) or 360,
                    "reconcile_scope": "全月总对账" if is_month_end else "半月阶段对账"
                }
            elif template_id == "T2-9":
                exp = experience_bank.find_by_id("EXP_PREWARM_BUFFER_01") or experience_bank.match_proactive_experience(cfg["env"], task_name) or experience_bank.find_by_id("EXP_STADIUM_CONGESTION_01")
                if is_counterexample:
                    experience_citation = {
                        "experience_id": exp["experience_id"],
                        "title": exp["title"],
                        "strategy_type": "negative_counterexample",
                        "negative_counterexamples": exp.get("negative_counterexamples", ""),
                        "counterexample_applied": True
                    }
                    res = "1080p"
                    rtt = "50ms"
                else:
                    experience_citation = {
                        "experience_id": exp["experience_id"],
                        "title": exp["title"],
                        "strategy_type": exp["strategy_type"],
                        "suggested_adjustments": exp.get("recommended_adjustments", {}),
                        "condition": exp.get("condition") or "识别重大活动或大型直播现场，需提前预热试机",
                        "action": exp.get("action") or "起保时间提前30分钟，保障时长扩充30分钟",
                        "validity": exp.get("validity") or exp.get("applicable_boundaries", ""),
                        "negotiation_required": (round_count == 3)
                    }
                    res = exp.get("recommended_adjustments", {}).get("resolution", "1080p")
                    rtt = exp.get("recommended_adjustments", {}).get("rtt_max", "50ms")
            elif template_id == "T2-10":
                exp = experience_bank.find_by_id("EXP_OVERLAPPING_ORDER_RESOLUTION_01") or experience_bank.find_by_id("EXP_SEVERE_WEATHER_01")
                experience_citation = {
                    "experience_id": exp["experience_id"],
                    "title": exp["title"],
                    "strategy_type": exp["strategy_type"],
                    "suggested_adjustments": exp.get("recommended_adjustments", {}),
                    "condition": exp.get("condition") or "新申请保障与既有工单发生时段重叠冲突",
                    "action": exp.get("action") or "时钟让路仲裁：原工单提前结单，新保障准时激活",
                    "validity": exp.get("validity") or exp.get("applicable_boundaries", "")
                }

            s_obj = {
                "session_id": f"S-{user_id}-{cfg['idx']:02d}",
                "user_id": user_id,
                "reference_time": cfg["ref_time"],
                "template_id": template_id,
                "memory_role": cfg["role"],
                "round_count": round_count,
                "blueprint_type": cfg["type"],
                "scenario_env": cfg["env"],
                "memory_action": cfg["action"],
                "memory_tier": cfg.get("memory_tier", "factual_memory"),
                "cold_hot_type": cfg.get("cold_hot_type") if "cold_hot_type" in cfg else ("hot_start" if cfg["role"] in ["reinforcement_session", "reuse_session"] and cfg.get("memory_tier", "factual_memory") == "factual_memory" else ("cold_start" if cfg.get("memory_tier", "factual_memory") == "factual_memory" else None)),
                "agility_factor": cfg.get("agility_factor") if "agility_factor" in cfg else (0.5 if cfg["role"] in ["reinforcement_session", "reuse_session"] and cfg.get("memory_tier", "factual_memory") == "factual_memory" else (0.0 if cfg.get("memory_tier", "factual_memory") == "factual_memory" else None)),
                "declaration_mode": cfg.get("declaration_mode", decl_mode),
                "storyline_trigger_type": cfg.get("storyline_trigger_type", storyline_trigger_type if cfg["type"].startswith("main") else "time_periodic"),
                "trigger_condition": cfg.get("trigger_condition", main_trigger_desc if cfg["type"].startswith("main") else ""),
                "ood_goal": cfg.get("ood_goal", ""),
                "target_params": {
                    "application_name": src["application_name"],
                    "service_name": src["service_name"],
                    "resolution": res,
                    "rtt": rtt,
                    "start_timestamp": cfg["start"],
                    "end_timestamp": cfg["end"],
                    "duration": cfg["dur"]
                },
                "period_type": main_mt.get("period_type", "weekly"),
                "base_duration": cfg.get("base_dur", cfg["dur"]),
                "base_end_timestamp": cfg.get("base_end", cfg["end"]),
                "base_end": cfg.get("base_end"),
                "base_dur": cfg.get("base_dur"),
                "start2": cfg.get("start2"),
                "end2": cfg.get("end2"),
                "dur2": cfg.get("dur2"),
                "aliases": aliases,
                "small_memory": small_memory,
                "small_memory_evidence_mode": evidence_mode,
                "working_memory_pointer": working_memory_pointer,
                "working_memory_query": working_memory_query,
                "experience_citation": experience_citation,
                "is_counterexample": is_counterexample,
                "is_disambiguation": is_disambig,
                "second_source": cfg.get("second_source"),
                "nominal_start": cfg.get("nominal_start"),
                "nominal_dur": cfg.get("nominal_dur"),
                "holiday_defer_date": cfg.get("holiday_defer_date"),
                "learning_source_session": learning_source_session,
                "experience_id": cfg.get("experience_id"),
            }

            # 若为真实开通的保障业务（非纯域外拒绝与对账），将单据记入工单账本
            if template_id not in ["T1-2", "T2-8"]:
                new_rec = working_ledger.create_record_from_session(s_obj)
                working_ledger.append_record(new_rec)

            sessions.append(s_obj)

        return sessions
