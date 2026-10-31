import hashlib
import re

from src.config.settings import Config
from src.generation.llm_client import LLMClient
from src.templates.prompts import (
    BASE_CANONICAL_PAIRS,
    DEFAULT_DURATION_ALIAS_MAP,
    INVALID_APP_SERVICE_MAP,
    PERSONA_SKELETON_SYSTEM_PROMPT,
    build_persona_skeleton_prompt,
)
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
        num_match = re.search(r"\d+", raw_persona.get("persona_id", ""))
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
            time_range_hint=time_range_hint,
        )
        messages = [
            {"role": "system", "content": PERSONA_SKELETON_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        res = self.llm.chat_json(messages)
        return self._enrich_skeleton(res)

    @staticmethod
    def _fix_app_service_pair(
        app_val: str,
        srv_val: str,
        used_apps: set,
        used_srvs: set | None,
        canonical_pairs: list[tuple[str, str]],
        support_matrix: dict,
    ) -> tuple[str, str, bool]:
        changed = False
        if (app_val, srv_val) in INVALID_APP_SERVICE_MAP:
            app_val, srv_val = INVALID_APP_SERVICE_MAP[(app_val, srv_val)]
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

    @staticmethod
    def _populate_main_aliases(aliases: dict, app: str, srv: str, res: str, rtt: str, p_type: str, time_range_str: str, app_map: dict, synonyms: dict) -> dict:
        if not aliases.get("app_aliases"):
            app_aliases_found = []
            for val_list in app_map.values():
                if app in val_list:
                    cn_aliases = [a for a in val_list if a != app and re.search(r"[\u4e00-\u9fa5]", a)]
                    other_aliases = [a for a in val_list if a != app and a not in cn_aliases]
                    app_aliases_found = cn_aliases + other_aliases
                    break
            aliases["app_aliases"] = app_aliases_found[:3] if app_aliases_found else [app]

        if not aliases.get("service_aliases"):
            srv_syns = synonyms.get("services", {}).get(srv, {}).get("general_aliases", [])
            aliases["service_aliases"] = [s for s in srv_syns if s != srv][:3] if srv_syns else [srv]

        res_alias_map = {
            "1080p": ["1080p原画", "1080p", "超清"],
            "720p": ["720p", "高清"],
            "4K": ["4K", "4K超高清"],
        }
        aliases["resolution_aliases"] = res_alias_map.get(res, [res, f"{res}清晰"])

        rtt_alias_map = {
            "50ms": ["50ms以内", "50毫秒以内", "低时延"],
            "30ms": ["30ms以内", "30毫秒以内", "超低时延"],
            "80ms": ["80ms以内", "80毫秒以内"],
            "100ms": ["100ms以内", "100毫秒以内"],
        }
        aliases["rtt_aliases"] = rtt_alias_map.get(rtt, [f"{rtt}以内", rtt])

        m_tr = re.search(r"(\d{1,2}):(\d{2})\s*[-~至到]\s*(\d{1,2}):(\d{2})", time_range_str)
        if m_tr:
            tr_mins = (int(m_tr.group(3)) * 60 + int(m_tr.group(4))) - (int(m_tr.group(1)) * 60 + int(m_tr.group(2)))
            if tr_mins <= 0:
                tr_mins += 24 * 60
        else:
            tr_mins = 90
        dur_key = f"{tr_mins}min"
        dur_syns = synonyms.get("duration", {}).get(dur_key, [])
        fallbacks = DEFAULT_DURATION_ALIAS_MAP.get(dur_key, [f"{tr_mins}分钟"])
        aliases["duration_aliases"] = list(dict.fromkeys(fallbacks + dur_syns))[:4]

        period_alias_map = {
            "daily": ["每天这个时候", "老时间", "日常例行", "每天照旧"],
            "weekly": ["每周老时间", "周例行时段", "照上周的来", "每周固定这个时候"],
            "monthly": ["月初例行", "每月老时间", "月度固定配置", "照旧按月度标准"],
        }
        aliases["period_aliases"] = period_alias_map.get(p_type, ["老规矩", "老时间", "按习惯来", "照旧"])
        return aliases

    @classmethod
    def _enrich_sub_and_distractors(
        cls,
        sk: dict,
        main_app: str,
        used_apps: set,
        used_srvs: set,
        canonical_pairs: list[tuple[str, str]],
        support_matrix: dict,
        app_map: dict,
        synonyms: dict,
    ) -> None:
        for sub in sk["dynamic_profile"].get("sub_storylines", []):
            s_app = sub.get("application_name", "")
            s_srv = sub.get("service_name", "")
            s_app, s_srv, sub_changed = cls._fix_app_service_pair(
                s_app, s_srv, used_apps, used_srvs, canonical_pairs, support_matrix
            )
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
                for vlist in app_map.values():
                    if s_app in vlist:
                        s_app_syns = [a for a in vlist if a != s_app]
                        break
                s_aliases["app_aliases"] = s_app_syns[:2] if s_app_syns else [s_app]
            if not s_aliases.get("service_aliases"):
                s_srv_syns = synonyms.get("services", {}).get(s_srv, {}).get("general_aliases", [])
                s_aliases["service_aliases"] = [s for s in s_srv_syns if s != s_srv][:2] if s_srv_syns else [s_srv]
            if not s_aliases.get("resolution_aliases"):
                s_aliases["resolution_aliases"] = (
                    ["1080p原画", "1080p"] if s_res == "1080p" else [s_res, "高清" if s_res == "720p" else s_res]
                )
            if not s_aliases.get("rtt_aliases"):
                s_aliases["rtt_aliases"] = [f"{s_rtt}以内", f"{s_rtt.replace('ms', '毫秒')}以内"]
            sub["aliases"] = s_aliases

        dist_used_apps = {main_app}
        for dist in sk["dynamic_profile"].get("distractor_pool", []):
            d_app = dist.get("application_name", "钉钉")
            d_srv = dist.get("service_name", "会议")
            d_app, d_srv, _ = cls._fix_app_service_pair(
                d_app, d_srv, dist_used_apps, None, canonical_pairs, support_matrix
            )
            dist["application_name"] = d_app
            dist["service_name"] = d_srv
            dist_used_apps.add(d_app)

    def _enrich_skeleton(self, sk: dict) -> dict:
        """后置校验并补齐 6 大维度口语别名，确保每一个画像骨架都具备高质量个性化表述映射库。"""
        if not isinstance(sk, dict) or "dynamic_profile" not in sk:
            return sk

        expr_vault = getattr(Config, "expression_vault", {})
        synonyms = expr_vault.get("slot_synonyms", {})
        app_map = getattr(Config, "app_map", {})
        support_matrix = getattr(Config, "support_matrix", {})

        pid_m = re.search(r"(\d+)", str(sk.get("persona_id") or ""))
        pid_offset = int(pid_m.group(1)) if pid_m else 0
        rot = pid_offset % len(BASE_CANONICAL_PAIRS)
        canonical_pairs = BASE_CANONICAL_PAIRS[rot:] + BASE_CANONICAL_PAIRS[:rot]

        main_mt = sk["dynamic_profile"].get("periodic_main_storyline", {})
        TriggerPresetManager.reload()
        _, _, _, _, preset_time_range, _ = TriggerPresetManager.resolve_trigger_plan(pid_offset or 1, sk)
        if preset_time_range:
            main_mt["time_range"] = preset_time_range

        used_apps, used_srvs = set(), set()
        app, srv, main_changed = self._fix_app_service_pair(
            main_mt.get("application_name", "抖音"),
            main_mt.get("service_name", "开直播"),
            used_apps,
            used_srvs,
            canonical_pairs,
            support_matrix,
        )
        main_mt["application_name"] = app
        main_mt["service_name"] = srv
        used_apps.add(app)
        used_srvs.add(srv)

        supp_res_list = support_matrix.get(app, {}).get(srv, {}).get("resolutions", ["720p", "1080p"])
        valid_res_choices = [r for r in ["720p", "1080p"] if r in supp_res_list] or ["1080p"]
        rtt_choices = ["30ms", "50ms", "80ms", "100ms"]
        pref_params = main_mt.get("preferred_params", {})
        if not isinstance(pref_params, dict):
            pref_params = {}
        h_bytes = hashlib.sha256(f"{sk.get('persona_id', '')}:{app}:{srv}".encode("utf-8")).digest()
        res = valid_res_choices[h_bytes[0] % len(valid_res_choices)]
        rtt = rtt_choices[h_bytes[1] % len(rtt_choices)]
        pref_params["resolution"] = res
        pref_params["rtt_max"] = rtt
        main_mt["preferred_params"] = pref_params

        aliases = main_mt.get("aliases", {})
        if not isinstance(aliases, dict):
            aliases = {}
        if main_changed:
            aliases["app_aliases"] = []
            aliases["service_aliases"] = []

        main_mt["aliases"] = self._populate_main_aliases(
            aliases,
            app,
            srv,
            res,
            rtt,
            main_mt.get("period_type", "weekly"),
            str(main_mt.get("time_range") or "14:00-15:30"),
            app_map,
            synonyms,
        )
        sk["dynamic_profile"]["periodic_main_storyline"] = main_mt
        self._enrich_sub_and_distractors(
            sk, app, used_apps, used_srvs, canonical_pairs, support_matrix, app_map, synonyms
        )
        return sk
