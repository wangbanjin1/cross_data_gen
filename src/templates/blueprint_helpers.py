"""时间线蓝图时间解析、场景名提炼与时间槽位分配辅助模块。"""

from __future__ import annotations

import re
from datetime import datetime


def _parse_time_range(time_range_str: str, ext_add_minutes: int = 60) -> tuple[str, str, str, str, str, str]:
    """
    解析 time_range 字符串（如 '20:00-22:00', '08:30-10:00'），
    返回 (start_time_str, end_time_str, ref_time_str, base_dur_str, ext_end_time_str, ext_dur_str)。
    """
    m = re.search(r'(\d{1,2}:\d{2})\s*[-~至到]\s*(\d{1,2}:\d{2})', time_range_str or "")
    if m:
        s_part = m.group(1).zfill(5)
        e_part = m.group(2).zfill(5)
    else:
        s_part = "14:00"
        e_part = "15:30"

    sh, sm = map(int, s_part.split(":"))
    eh, em = map(int, e_part.split(":"))

    base_minutes = (eh * 60 + em) - (sh * 60 + sm)
    if base_minutes <= 0:
        base_minutes = 90
        eh_tot = (sh * 60 + sm + base_minutes) % (24 * 60)
        e_part = f"{eh_tot // 60:02d}:{eh_tot % 60:02d}"

    base_dur_str = f"{base_minutes}min"

    # ref_time 提前 15 分钟
    ref_tot = (sh * 60 + sm) - 15
    if ref_tot < 0:
        ref_tot += 24 * 60
    ref_time_str = f"{ref_tot // 60:02d}:{ref_tot % 60:02d}"

    # T2-5 灵活延长 ext_add_minutes 分钟（支持 30 / 60 / 90 分钟，且严格控制在当日 23:30 前结束，防止跨零点日期错位）
    while ext_add_minutes > 30 and (sh * 60 + sm + base_minutes + ext_add_minutes) > 23 * 60 + 30:
        ext_add_minutes -= 30
    if (sh * 60 + sm + base_minutes + ext_add_minutes) >= 24 * 60:
        ext_add_minutes = max(15, (23 * 60 + 30) - (sh * 60 + sm + base_minutes))
    ext_minutes = base_minutes + ext_add_minutes
    ext_dur_str = f"{ext_minutes}min"
    ext_end_tot = (sh * 60 + sm) + ext_minutes
    ext_end_time_str = f"{(ext_end_tot // 60) % 24:02d}:{ext_end_tot % 60:02d}"

    return s_part, e_part, ref_time_str, base_dur_str, ext_end_time_str, ext_dur_str


def _extract_clean_event_env(evt: dict, time_range: str = "") -> str:
    """结合事件名称与描述提炼 4~8 字短现场名，并严格进行时段一致性校验（防止早晚时段打架）。"""
    name = evt.get("name", "") if isinstance(evt, dict) else ""
    desc = evt.get("scene_description", "") if isinstance(evt, dict) else ""
    text = f"{name} {desc}"

    patterns = [
        (r'公益赛事|赛事集结|赛事周', "公益赛事活动现场"),
        (r'棒球|球场|客场赛事', "棒球赛事活动现场"),
        (r'外业调查|实验现场|数据回传', "外业调查实验现场"),
        (r'音乐节|演出周|舞台', "城市音乐节现场"),
        (r'联合执法|巡逻线|检查点', "联合执法执勤现场"),
        (r'金融展会|展会外摆|商贸展', "跨境商贸展会现场"),
        (r'社区宣传|社区走访', "社区宣传走访现场"),
        (r'设计展|现场提案', "设计展提案现场"),
        (r'街区突发|转场直播|街巷', "城市街区采访现场"),
        (r'应急集结|夜间事故|处置点', "应急处置现场"),
        (r'联合实践|实践地|教学现场', "校际实践教学现场"),
        (r'搜救游泳|海岸线|码头', "搜救选拔赛事现场"),
        (r'模型交流|展览现场', "模型交流展会现场"),
        (r'儿童阅读|巡展现场', "儿童阅读巡展现场"),
        (r'喀斯喀特|登山口|集结区', "山脉赛事集结区"),
        (r'敬拜现场|录制周', "敬拜现场录制区"),
        (r'立法调研|草案冲刺', "立法调研办公现场"),
        (r'地质勘查|地质考察|科考营地', "野外地质勘查区"),
        (r'露天训练|高山露天', "高山露天训练场"),
        (r'道路巡逻|移动执勤', "道路巡逻执勤现场"),
    ]
    extracted = None
    for pat, loc in patterns:
        if re.search(pat, text):
            extracted = loc
            break

    if not extracted:
        clean_name = re.sub(r'(?:周|跨城|跨区域|跨校|联合|现场|冲刺|保障|外业)', '', name)
        clean_name = re.sub(r'[^\u4e00-\u9fa5]', '', clean_name)
        extracted = f"{clean_name[:4]}活动现场" if clean_name else "外勤保障现场"

    start_hour = None
    if time_range and "-" in time_range:
        try:
            start_hour = int(time_range.split("-")[0].split(":")[0])
        except (ValueError, IndexError):
            start_hour = None

    if start_hour is not None:
        if start_hour >= 11 and any(kw in extracted for kw in ["早间", "早高峰", "晨间"]):
            extracted = extracted.replace("早间", "日间").replace("早高峰", "日常").replace("晨间", "日间")
        if start_hour < 17 and any(kw in extracted for kw in ["晚间", "夜间"]):
            extracted = extracted.replace("晚间", "日间").replace("夜间", "日间")

    return extracted


def _generate_timeline_dates(storyline_trigger_type: str, period_type: str, days: list, count: int = 22) -> list[str]:
    """
    根据触发类型、周期粒度与设定日子生成严格单调递增的时间线日期列表（支持 30 个节点）。
    """
    days_str = " ".join(days or []).lower()

    # 严格单调递增日期序列：S06 必须严格锚定在 2026年09月28日（周一），
    # 确保从 S06 出发时“下周一”为 2026年10月05日（国庆长假中），节后顺延首个工作日为 2026年10月08日（周四），S07 在节后 10月09日（周五）开始
    dates = [
        "2026年09月14日", "2026年09月16日", "2026年09月18日", "2026年09月21日",
        "2026年09月25日", "2026年09月28日", "2026年10月09日", "2026年10月12日",
        "2026年10月14日", "2026年10月16日", "2026年10月19日", "2026年10月21日",
        "2026年10月23日", "2026年10月26日", "2026年10月28日", "2026年10月30日",
        "2026年11月02日", "2026年11月04日", "2026年11月06日", "2026年11月09日",
        "2026年11月11日", "2026年11月13日", "2026年11月16日", "2026年11月18日",
        "2026年11月20日", "2026年11月23日", "2026年11月25日", "2026年11月27日",
        "2026年11月30日", "2026年12月02日", "2026年12月04日", "2026年12月07日"
    ]

    return dates[:count]



def _m_time(d_str: str, t_str: str) -> str:
    parts = t_str.split(":")
    return f"{d_str}{parts[0]}时{parts[1]}分"


def assign_blueprint_timestamps(
    selected: list[dict],
    dates: list[str],
    ref_str: str,
    sh_str: str,
    eh_str: str,
    ext_eh_str: str,
    base_dur: str,
    pw_s_str: str,
    pw_dur_str: str,
    sub1_ref: str,
    sub1_s: str,
    sub1_e: str,
    sub2_ref: str,
    sub2_s: str,
    sub2_e: str,
    ood_s: str,
    ood_e: str,
    dn_s: str,
    dn_e: str,
) -> list[dict]:
    """填充每个蓝图槽位的具体起止时间与流水编号。"""
    final_blueprints = []
    for i, s in enumerate(selected):
        d_str = dates[i]
        t_kind = s["time_kind"]
        item = dict(s)
        item["idx"] = i + 1

        if t_kind == "main":
            item["ref_time"] = _m_time(d_str, ref_str)
            item["start"] = _m_time(d_str, sh_str)
            item["end"] = _m_time(d_str, eh_str)
        elif t_kind == "main_amend":
            item["ref_time"] = _m_time(d_str, ref_str)
            item["start"] = _m_time(d_str, sh_str)
            item["end"] = _m_time(d_str, ext_eh_str)
            item["base_end"] = _m_time(d_str, eh_str)
        elif t_kind == "prewarm":
            item["ref_time"] = _m_time(d_str, ref_str)
            item["start"] = _m_time(d_str, pw_s_str)
            item["end"] = _m_time(d_str, eh_str)
            item["dur"] = pw_dur_str
            item["nominal_start"] = _m_time(d_str, sh_str)
            item["nominal_dur"] = base_dur
        elif t_kind == "holiday":
            # 顺延至国庆长假后首个工作日办理 (2026年10月08日)，名义预定日为 2026年10月05日（下周一）
            defer_date = "2026年10月08日"
            nominal_date = "2026年10月05日"
            item["ref_time"] = _m_time(d_str, ref_str)
            item["start"] = _m_time(defer_date, sh_str)
            item["end"] = _m_time(defer_date, eh_str)
            item["nominal_start"] = _m_time(nominal_date, sh_str)
            item["nominal_end"] = _m_time(nominal_date, eh_str)
            item["holiday_defer_date"] = defer_date
        elif t_kind == "multi_intent":
            item["ref_time"] = _m_time(d_str, ref_str)
            item["start"] = _m_time(d_str, sh_str)
            item["base_end"] = _m_time(d_str, eh_str)
            item["base_dur"] = base_dur
            item["end"] = _m_time(d_str, eh_str)
            item["dur"] = base_dur
            item["start2"] = _m_time(d_str, sh_str)
            item["end2"] = _m_time(d_str, eh_str)
            item["dur2"] = base_dur
        elif t_kind == "overlap":
            item["ref_time"] = _m_time(d_str, ref_str)
            item["nominal_start"] = _m_time(d_str, sh_str)
            item["nominal_end"] = _m_time(d_str, eh_str)
            item["nominal_dur"] = base_dur
            item["start"] = _m_time(d_str, sh_str)
            item["end"] = _m_time(d_str, eh_str)
            item["dur"] = base_dur
        elif t_kind == "sub1":
            item["ref_time"] = _m_time(d_str, sub1_ref)
            item["start"] = _m_time(d_str, sub1_s)
            item["end"] = _m_time(d_str, sub1_e)
        elif t_kind == "sub2":
            item["ref_time"] = _m_time(d_str, sub2_ref)
            item["start"] = _m_time(d_str, sub2_s)
            item["end"] = _m_time(d_str, sub2_e)
        elif t_kind == "dist_ood":
            item["ref_time"] = _m_time(d_str, ood_s)
            item["start"] = _m_time(d_str, ood_s)
            item["end"] = _m_time(d_str, ood_e)
        elif t_kind == "dist_mixed":
            item["ref_time"] = f"{d_str}12时30分"
            item["start"] = f"{d_str}12时30分"
            item["end"] = f"{d_str}13时30分"
            m_date = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', d_str)
            if m_date:
                dt = datetime(int(m_date.group(1)), int(m_date.group(2)), int(m_date.group(3)))
                if dt.weekday() in [5, 6]:
                    item["env"] = "周末午休个人时间"
                else:
                    item["env"] = "工作日午休个人时间"
            else:
                item["env"] = "午休个人时间"
        elif t_kind == "dist_normal":
            item["ref_time"] = _m_time(d_str, dn_s)
            item["start"] = _m_time(d_str, dn_s)
            item["end"] = _m_time(d_str, dn_e)

        final_blueprints.append(item)

    return final_blueprints
