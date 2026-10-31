"""
动态会话生命周期时间线蓝图配置模块。
定义了包含 7 种核心模版（T2-1, T2-2, T1-2, T2-5, X-1, T2-3, T1-1）的完整会话序列结构。
支持 daily / weekly / monthly 等多粒度周期与自定义起止时段的动态时间线计算。
"""

from __future__ import annotations

from src.templates.blueprint_helpers import (
    _extract_clean_event_env,
    _generate_timeline_dates,
    _m_time,
    _parse_time_range,
    assign_blueprint_timestamps,
)
from src.templates.blueprint_specs import (
    build_raw_blueprint_specs,
    plan_experience_slot_pairs,
    resolve_blueprint_time_context,
)


def get_session_blueprints(
    main_mt: dict,
    sub_01: dict,
    sub_02: dict,
    dist_01: dict,
    dist_02: dict,
    evt_01: dict,
    decl_mode: str,
    storyline_trigger_type: str,
    main_env_desc: str,
    main_trigger_desc: str,
    target_count: int = 22,
    selected_exp_ids: list[str] | None = None,
) -> list[dict]:
    """
    根据目标数量（支持 16 ~ 22 轮深层认知演进）生成自然时间线蓝图配置。
    动态结合主线设定的时间区间 (time_range) 与周期粒度 (period_type, days) 输出排期。
    动态结合画像适配的 1~2 个经验记忆卡片 (selected_exp_ids) 规划对应经验插槽。
    """
    if selected_exp_ids is None:
        selected_exp_ids = ["EXP_PREWARM_BUFFER_01", "EXP_MULTI_INTENT_PARTITION_01"]

    period_type = main_mt.get("period_type", "weekly")
    days = main_mt.get("days", [])
    tc = resolve_blueprint_time_context(main_mt, sub_01, sub_02, dist_01, dist_02, main_env_desc)
    slot_learn_map, slot_test_map = plan_experience_slot_pairs(selected_exp_ids)

    ctx = {
        "main_mt": main_mt,
        "sub_01": sub_01,
        "sub_02": sub_02,
        "dist_01": dist_01,
        "dist_02": dist_02,
        "evt_01": evt_01,
        "decl_mode": decl_mode,
        "storyline_trigger_type": storyline_trigger_type,
        "main_env_desc": main_env_desc,
        "main_trigger_desc": main_trigger_desc,
        "tc": tc,
        "slot_learn_map": slot_learn_map,
        "slot_test_map": slot_test_map,
    }
    candidate_slots = build_raw_blueprint_specs(ctx)
    selected = [dict(slot) for slot in candidate_slots[:target_count]]
    dates = _generate_timeline_dates(storyline_trigger_type, period_type, days, count=len(selected))

    evt_corr_idx = next((i for i, s in enumerate(selected) if s["tag"] == "evt_correct"), 10)
    evt_reuse_idx = next((i for i, s in enumerate(selected) if s["tag"] == "evt_reuse"), evt_corr_idx + 1)
    if evt_corr_idx < len(dates):
        evt_01["start_time"] = f"{dates[evt_corr_idx]}00时00分"
    if evt_reuse_idx < len(dates):
        evt_01["end_time"] = f"{dates[evt_reuse_idx]}23时59分"

    return assign_blueprint_timestamps(
        selected=selected,
        dates=dates,
        ref_str=tc["ref_str"],
        sh_str=tc["sh_str"],
        eh_str=tc["eh_str"],
        ext_eh_str=tc["ext_eh_str"],
        base_dur=tc["base_dur"],
        pw_s_str=tc["pw_s_str"],
        pw_dur_str=tc["pw_dur_str"],
        sub1_ref=tc["sub1_ref"],
        sub1_s=tc["sub1_s"],
        sub1_e=tc["sub1_e"],
        sub2_ref=tc["sub2_ref"],
        sub2_s=tc["sub2_s"],
        sub2_e=tc["sub2_e"],
        ood_s=tc["ood_s"],
        ood_e=tc["ood_e"],
        dn_s=tc["dn_s"],
        dn_e=tc["dn_e"],
    )


# 兼容既有调用
get_15_session_blueprints = get_session_blueprints
__all__ = [
    "get_session_blueprints",
    "get_15_session_blueprints",
    "_extract_clean_event_env",
    "_generate_timeline_dates",
    "_m_time",
    "_parse_time_range",
    "assign_blueprint_timestamps",
]
