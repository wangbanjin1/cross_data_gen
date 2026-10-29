import re
from src.config.settings import Config
from src.generation.llm_client import LLMClient
from src.templates.prompts.persona_prompts import build_persona_skeleton_prompt
from src.templates.trigger_presets import TriggerPresetManager

class PersonaGenerator:
    """
    画像骨架生成器 (PersonaGenerator)
    负责调用 DeepSeek API 将粗粒度原始画像扩充为标准的解耦画像骨架 (Persona Skeleton)。
    """

    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm_client or LLMClient()
        self.valid_apps = list(getattr(Config, "app_map", {}).keys())
        self.support_matrix = getattr(Config, "support_matrix", {})

    def generate_skeleton(self, raw_persona: dict) -> dict:
        num_match = re.search(r'\d+', raw_persona.get("persona_id", ""))
        uid_num = int(num_match.group()) if num_match else 1
        forced_decl_mode, forced_trig_type, period_type_hint, days_hint, time_range_hint, trig_instruction = (
            TriggerPresetManager.resolve_trigger_plan(uid_num, raw_persona)
        )

        prompt = build_persona_skeleton_prompt(
            raw_persona=raw_persona,
            forced_decl_mode=forced_decl_mode,
            forced_trig_type=forced_trig_type,
            trig_instruction=trig_instruction,
            period_type_hint=period_type_hint,
            days_hint=days_hint,
            time_range_hint=time_range_hint
        )

        messages = [
            {"role": "system", "content": "You are a professional dataset engineer for network agent memory systems."},
            {"role": "user", "content": prompt}
        ]
        res = self.llm.chat_json(messages)
        return self._enrich_skeleton(res)

    def _enrich_skeleton(self, sk: dict) -> dict:
        """
        后置校验并补齐 6 大维度口语别名，确保每一个画像骨架都具备高质量行话库。
        """
        if not isinstance(sk, dict) or "dynamic_profile" not in sk:
            return sk

        expr_vault = getattr(Config, "expression_vault", {})
        synonyms = expr_vault.get("slot_synonyms", {})
        app_map = getattr(Config, "app_map", {})
        support_matrix = getattr(Config, "support_matrix", {})

        # 标准多品类合规 (应用, 业务) 候选池，支持按人物 ID 轮转采样以保障全数据集应用与业务多样性
        base_canonical_pairs = [
            ("抖音", "开直播"),
            ("微信", "视频通话"),
            ("腾讯会议", "会议"),
            ("快手", "开直播"),
            ("钉钉", "会议"),
            ("哔哩哔哩", "开直播"),
            ("飞书", "会议"),
            ("小红书", "开直播"),
            ("抖音", "短视频"),
            ("快手", "短视频"),
            ("腾讯视频", "视频"),
            ("哔哩哔哩", "视频"),
            ("咪咕快游", "云游戏"),
            ("斗鱼直播", "开直播"),
            ("虎牙直播", "看直播"),
        ]
        pid_m = re.search(r"(\d+)", str(sk.get("persona_id") or ""))
        pid_offset = int(pid_m.group(1)) if pid_m else 0
        canonical_pairs = base_canonical_pairs[pid_offset % len(base_canonical_pairs):] + base_canonical_pairs[:pid_offset % len(base_canonical_pairs)]

        def _fix_pair(app_val: str, srv_val: str, used_apps: set, used_srvs: set = None) -> tuple[str, str, bool]:
            changed = False
            # 专项映射常见越界组合
            invalid_map = {
                ("高德地图", "视频通话"): ("微信", "视频通话"),
                ("钉钉", "视频通话"): ("钉钉", "会议"),
                ("微信", "会议"): ("钉钉", "会议"),
                ("腾讯会议", "视频通话"): ("腾讯会议", "会议"),
                ("哔哩哔哩", "短视频"): ("抖音", "短视频"),
                ("快手", "游戏"): ("快手", "看直播"),
            }
            if (app_val, srv_val) in invalid_map:
                app_val, srv_val = invalid_map[(app_val, srv_val)]
                changed = True
            elif app_val not in support_matrix or srv_val not in support_matrix.get(app_val, {}):
                for c_app, c_srv in canonical_pairs:
                    if c_app not in used_apps and (used_srvs is None or c_srv not in used_srvs):
                        app_val, srv_val = c_app, c_srv
                        changed = True
                        break
            if app_val in used_apps or (used_srvs is not None and srv_val in used_srvs):
                for c_app, c_srv in canonical_pairs:
                    if c_app not in used_apps and (used_srvs is None or c_srv not in used_srvs):
                        app_val, srv_val = c_app, c_srv
                        changed = True
                        break
            return app_val, srv_val, changed

        main_mt = sk["dynamic_profile"].get("periodic_main_storyline", {})
        app = main_mt.get("application_name", "抖音")
        srv = main_mt.get("service_name", "开直播")
        used_apps = set()
        used_srvs = set()
        app, srv, main_changed = _fix_pair(app, srv, used_apps, used_srvs)
        main_mt["application_name"] = app
        main_mt["service_name"] = srv
        used_apps.add(app)
        used_srvs.add(srv)
        res = main_mt.get("preferred_params", {}).get("resolution", "1080p")
        rtt = main_mt.get("preferred_params", {}).get("rtt_max", "50ms")
        p_type = main_mt.get("period_type", "weekly")

        aliases = main_mt.get("aliases", {})
        if not isinstance(aliases, dict):
            aliases = {}
        if main_changed:
            aliases["app_aliases"] = []
            aliases["service_aliases"] = []

        # 1. 补齐 app_aliases (优先选择地道中文叫法)
        if not aliases.get("app_aliases"):
            app_aliases_found = []
            for k, val_list in app_map.items():
                if app in val_list:
                    cn_aliases = [a for a in val_list if a != app and re.search(r'[\u4e00-\u9fa5]', a)]
                    other_aliases = [a for a in val_list if a != app and a not in cn_aliases]
                    app_aliases_found = cn_aliases + other_aliases
                    break
            aliases["app_aliases"] = app_aliases_found[:3] if app_aliases_found else [app]

        # 2. 补齐 service_aliases
        if not aliases.get("service_aliases"):
            srv_syns = synonyms.get("services", {}).get(srv, {}).get("general_aliases", [])
            aliases["service_aliases"] = [s for s in srv_syns if s != srv][:3] if srv_syns else [srv]

        # 3. 补齐 resolution_aliases（严格对应数值档位，严禁使用混淆 2K/4K 的'顶格清晰度'）
        if not aliases.get("resolution_aliases"):
            if res == "1080p":
                aliases["resolution_aliases"] = ["1080p原画", "1080p", "超清"]
            elif res == "720p":
                aliases["resolution_aliases"] = ["720p", "高清"]
            elif res == "4K":
                aliases["resolution_aliases"] = ["4K", "4K超高清"]
            else:
                aliases["resolution_aliases"] = [res, f"{res}清晰"]
        else:
            cleaned_res = [r for r in aliases["resolution_aliases"] if not any(b in r for b in ["顶格", "最高", "极限", "极致", "蓝光"])]
            if res == "1080p" and not cleaned_res:
                cleaned_res = ["1080p原画", "1080p", "超清"]
            aliases["resolution_aliases"] = cleaned_res or [res]

        # 4. 补齐 rtt_aliases（严格对应时延数值档位，严禁使用夸大失真的'零卡顿'）
        if not aliases.get("rtt_aliases"):
            if rtt == "50ms":
                aliases["rtt_aliases"] = ["50ms以内", "50毫秒以内", "低时延"]
            elif rtt == "30ms":
                aliases["rtt_aliases"] = ["30ms以内", "30毫秒以内", "超低时延"]
            elif rtt == "100ms":
                aliases["rtt_aliases"] = ["100ms以内", "100毫秒以内"]
            else:
                aliases["rtt_aliases"] = [f"{rtt}以内", rtt]
        else:
            cleaned_rtt = [r for r in aliases["rtt_aliases"] if not any(b in r for b in ["零卡顿", "秒开", "极速"])]
            if rtt == "50ms" and not cleaned_rtt:
                cleaned_rtt = ["50ms以内", "50毫秒以内", "低时延"]
            aliases["rtt_aliases"] = cleaned_rtt or [f"{rtt}以内"]

        # 5. 补齐 duration_aliases（根据主线 time_range 的真实时长动态匹配口语别名，禁止写死 120min）
        tr_str = str(main_mt.get("time_range") or "14:00-16:00")
        m_tr = re.search(r"(\d{1,2}):(\d{2})\s*[-~至到]\s*(\d{1,2}):(\d{2})", tr_str)
        if m_tr:
            tr_mins = (int(m_tr.group(3)) * 60 + int(m_tr.group(4))) - (int(m_tr.group(1)) * 60 + int(m_tr.group(2)))
            if tr_mins <= 0:
                tr_mins += 24 * 60
        else:
            tr_mins = 120
        dur_key = f"{tr_mins}min"
        default_dur_map = {
            "30min": ["半小时", "半个钟头", "30分钟"],
            "45min": ["45分钟", "三刻钟"],
            "60min": ["一个钟头", "一小时", "60分钟"],
            "90min": ["一个半小时", "一个半钟头", "90分钟"],
            "120min": ["俩小时", "两钟头", "两小时"],
            "150min": ["两个半小时", "150分钟"],
            "180min": ["三个小时", "三钟头", "180分钟"],
        }
        if not aliases.get("duration_aliases"):
            dur_syns = synonyms.get("duration", {}).get(dur_key, [])
            fallbacks = default_dur_map.get(dur_key, [f"{tr_mins}分钟"])
            aliases["duration_aliases"] = (dur_syns + fallbacks)[:4]

        # 6. 补齐 period_aliases
        if not aliases.get("period_aliases"):
            if p_type == "daily":
                aliases["period_aliases"] = ["每天这个时候", "老时间", "日常例行", "每天照旧", "每天这个点"]
            elif p_type == "weekly":
                aliases["period_aliases"] = ["每周老时间", "周例行时段", "照上周的来", "每周固定这个时候"]
            elif p_type == "monthly":
                aliases["period_aliases"] = ["月初例行", "每月老时间", "月度固定配置", "照旧按月度标准"]
            else:
                aliases["period_aliases"] = ["老规矩", "老时间", "按习惯来", "照旧"]

        main_mt["aliases"] = aliases
        sk["dynamic_profile"]["periodic_main_storyline"] = main_mt

        # 同样补齐并规范化 sub_storylines
        for sub in sk["dynamic_profile"].get("sub_storylines", []):
            s_app = sub.get("application_name", "")
            s_srv = sub.get("service_name", "")
            s_app, s_srv, sub_changed = _fix_pair(s_app, s_srv, used_apps, used_srvs)
            sub["application_name"] = s_app
            sub["service_name"] = s_srv
            used_apps.add(s_app)
            used_srvs.add(s_srv)
            s_res = sub.get("preferred_params", {}).get("resolution", "720p")
            s_rtt = sub.get("preferred_params", {}).get("rtt_max", "100ms")
            s_aliases = sub.get("aliases", {})
            if not isinstance(s_aliases, dict):
                s_aliases = {}
            if sub_changed:
                s_aliases["app_aliases"] = []
                s_aliases["service_aliases"] = []
            if not s_aliases.get("app_aliases"):
                s_app_syns = []
                for k, vlist in app_map.items():
                    if s_app in vlist:
                        s_app_syns = [a for a in vlist if a != s_app]
                        break
                s_aliases["app_aliases"] = s_app_syns[:2] if s_app_syns else [s_app]
            if not s_aliases.get("service_aliases"):
                s_srv_syns = synonyms.get("services", {}).get(s_srv, {}).get("general_aliases", [])
                s_aliases["service_aliases"] = [s for s in s_srv_syns if s != s_srv][:2] if s_srv_syns else [s_srv]
            if not s_aliases.get("resolution_aliases"):
                s_aliases["resolution_aliases"] = ["1080p原画", "1080p"] if s_res == "1080p" else [s_res, "高清" if s_res == "720p" else s_res]
            if not s_aliases.get("rtt_aliases"):
                s_aliases["rtt_aliases"] = [f"{s_rtt}以内", f"{s_rtt.replace('ms', '毫秒')}以内"]
            sub["aliases"] = s_aliases

        # 规范化 distractor_pool
        dist_used_apps = {app}
        for dist in sk["dynamic_profile"].get("distractor_pool", []):
            d_app = dist.get("application_name", "钉钉")
            d_srv = dist.get("service_name", "会议")
            d_app, d_srv, _ = _fix_pair(d_app, d_srv, dist_used_apps, None)
            dist["application_name"] = d_app
            dist["service_name"] = d_srv
            dist_used_apps.add(d_app)

        return sk
