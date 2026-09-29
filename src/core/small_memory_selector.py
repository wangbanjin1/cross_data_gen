"""从既有 expression_vault 素材中筛选可形成个性化记忆的表达。"""

import re
from src.config.settings import Config

ALIAS_KEYS = {"application_alias": "app_aliases", "service_default_app": "service_default_apps", "resolution_alias": "resolution_aliases", "rtt_alias": "rtt_aliases", "duration_alias": "duration_aliases", "period_alias": "period_aliases"}


def build_small_memory_candidates(source: dict, target_params: dict, allow_service_default: bool = False) -> list[dict]:
    """选取含义依赖用户定义的表达；确定数值和通用同义词只做归一化。"""
    vault = getattr(Config, "expression_vault", {}).get("slot_synonyms", {})
    aliases = source.get("aliases", {})
    candidates = []
    app = source.get("application_name")
    app_alias = next((v for v in aliases.get("app_aliases", []) if _is_personal_app_alias(v, app)), None)
    if app_alias:
        candidates.append(_candidate("application_alias", app_alias, app))
    service = source.get("service_name")
    if allow_service_default and service and app:
        # 业务默认应用只允许用于主线，并绑定主线触发场景，避免覆盖支线中的同业务应用。
        candidates.append(_candidate(
            "service_default_app",
            service,
            app,
            scope_condition=source.get("name") or source.get("trigger_condition") or "主线场景",
        ))
    resolution = target_params.get("resolution")
    resolution_phrases = vault.get("resolution", {}).get(resolution, {}).get("good_expressions", [])
    for v in resolution_phrases:
        if _is_fuzzy_parameter(v):
            candidates.append(_candidate("resolution_alias", v, resolution))
    # 同时也补充骨架自身别名
    for v in aliases.get("resolution_aliases", []):
        if _is_fuzzy_parameter(v) and not any(c["value"] == v for c in candidates):
            candidates.append(_candidate("resolution_alias", v, resolution))

    rtt = target_params.get("rtt")
    rtt_phrases = vault.get("rtt", {}).get(rtt, {}).get("good_expressions", [])
    for v in rtt_phrases:
        if _is_fuzzy_parameter(v):
            candidates.append(_candidate("rtt_alias", v, rtt))
    for v in aliases.get("rtt_aliases", []):
        if _is_fuzzy_parameter(v) and not any(c["value"] == v for c in candidates):
            candidates.append(_candidate("rtt_alias", v, rtt))

    duration = target_params.get("duration")
    duration_phrases = vault.get("duration", {}).get(duration, [])
    for v in duration_phrases:
        if _is_fuzzy_duration(v):
            candidates.append(_candidate("duration_alias", v, duration))
    for v in aliases.get("duration_aliases", []):
        if _is_fuzzy_duration(v) and not any(c["value"] == v for c in candidates):
            candidates.append(_candidate("duration_alias", v, duration))

    if source.get("period_type") in {"daily", "weekly", "monthly"}:
        period = source.get("time_range") or "当前周期"
        for v in aliases.get("period_aliases", []):
            if _is_fuzzy_period(v) and not any(c["value"] == v for c in candidates):
                candidates.append(_candidate("period_alias", v, period))
    return candidates


def _candidate(memory_type: str, value: str, normalized_value: str, **extra) -> dict:
    return {"type": memory_type, "alias_key": ALIAS_KEYS[memory_type], "value": value, "normalized_value": normalized_value, **extra}


def _is_personal_app_alias(value: str, canonical: str) -> bool:
    return bool(value and value != canonical and re.search(r"[\u4e00-\u9fff]", value))


def _is_fuzzy_parameter(value: str) -> bool:
    normalized_terms = {
        "全高清", "超清画质", "高清推流", "蓝光", "高清晰度", "顶格画质",
        "高清", "普通高清", "标清偏上", "正常画质", "标清", "流畅画质",
        "画质拉满", "低延迟", "时延极低", "毫秒级响应",
        "顶格清晰度", "顶格画质", "最高画质", "极限画质", "最高清晰度",
        "零卡顿", "秒开", "极速响应", "元指令", "意图槽位", "长期偏好",
    }
    return bool(value) and value not in normalized_terms and not re.search(r"\d+\s*(?:p|P|k|K|毫秒|ms)", value)


def _is_fuzzy_duration(value: str) -> bool:
    deterministic = r"\d|半小时|[一二两三四五六七八九十俩]+个?小时|分钟|钟头|小时整"
    return bool(value) and not re.search(deterministic, value)


def _is_fuzzy_period(value: str) -> bool:
    return bool(value) and not re.search(r"\d|周[一二三四五六日天]|星期[一二三四五六日天]", value)
