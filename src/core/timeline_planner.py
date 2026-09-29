import hashlib
import re
from src.templates.timeline_blueprints import get_15_session_blueprints
from src.core.small_memory_selector import build_small_memory_candidates

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

    @staticmethod
    def _extract_clean_location(raw_cond: str, task_name: str) -> str:
        """从 trigger_condition 中提炼简短自然的地点环境名称（4-8字），避免规则长句混入台词。"""
        if not raw_cond:
            return "执勤活动现场"
        
        patterns = [
            (r'道路巡逻|巡逻线|事故现场|移动执勤', "道路巡逻现场"),
            (r'社区走访|走访点|临时会议', "社区走访现场"),
            (r'户外现场|晚间户外|临时停留点|等候区', "晚间户外活动现场"),
            (r'街区采访|拍摄地|遮挡区域', "街区采访现场"),
            (r'沿海公路|巡逻岸线|集结区', "沿海巡逻岸线"),
            (r'高山|登山口|露天训练|偏远山区', "高山露天训练场"),
        ]
        for pat, loc in patterns:
            if re.search(pat, raw_cond):
                return loc

        m = re.search(r'(?:身处|在|进入)([^，,。、\s]{2,8}(?:走访点|现场|岸线|训练场|营区|路线|区域|停留点))', raw_cond)
        if m:
            clean = m.group(1).replace("等", "")
            return clean if len(clean) <= 8 else f"{clean[:6]}现场"

        clean_task = re.sub(r'(?:任务|保障|协同|即时调度|回传|上传|与|及)', '', task_name or '')
        if clean_task and 2 <= len(clean_task) <= 8:
            return f"{clean_task}现场"

        return "外勤保障现场"

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
    def plan(cls, persona: dict, llm=None) -> list[dict]:
        user_id = persona["static_profile"]["user_id"]
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
        if storyline_trigger_type == "task_activity":
            clean_task = re.sub(r'(?:任务|保障|协同|即时调度|回传|上传)', '', task_name or '')
            main_env_desc = f"{clean_task}现场" if clean_task else f"{task_name}现场"
            main_trigger_desc = raw_trig_cond if raw_trig_cond else f"执行【{task_name}】任务"
        elif storyline_trigger_type == "location_environment":
            identity_desc = persona.get("static_profile", {}).get("identity", "")
            if llm:
                main_env_desc = cls._extract_location_with_llm(llm, raw_trig_cond, task_name, identity_desc)
            else:
                main_env_desc = cls._extract_clean_location(raw_trig_cond, task_name)
            main_trigger_desc = f"处于【{main_env_desc}】"
        else:
            main_env_desc = "常规周期保障现场"
            main_trigger_desc = raw_trig_cond if raw_trig_cond else "每周常规周期时段"

        # 会话数量支持根据画像与业务情境自然浮动（12 ~ 16 轮）
        # 彻底破除强制 15 轮限制
        target_count = 12 + (uid_num % 5)

        blueprint_configs = get_15_session_blueprints(
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
        )

        sessions = []
        for cfg in blueprint_configs:
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
            round_count = 1 if (cfg["template_id"].startswith("T1") or cfg["template_id"].startswith("X-1")) else 2
            template_id = cfg["template_id"]
            if cfg["role"] == "evidence_session" and evidence_mode == "cross_turn_clarification":
                round_count = 3
                template_id = "T3-1"
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
                "aliases": aliases,
                "small_memory": small_memory,
                "small_memory_evidence_mode": evidence_mode,
            }
            sessions.append(s_obj)

        return sessions
