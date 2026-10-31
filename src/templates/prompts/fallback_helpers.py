"""对话兜底台词公共辅助函数模块。"""

from __future__ import annotations

import re


def _sanitize_env(env: str, time_str: str = "") -> str:
    if not env:
        return "现场"
    # 优先匹配特定现场
    patterns = [
        ("奥林匹克", "奥体中心多功能馆"),
        ("奥体中心", "奥体中心多功能馆"),
        ("会展中心", "国际会展中心"),
        ("公益赛事", "公益赛事活动现场"),
        ("外业调查", "外业调查实验现场"),
        ("音乐节", "城市音乐节现场"),
        ("联合执法", "联合执法执勤现场"),
        ("金融展会", "跨境商贸展会现场"),
        ("社区宣传", "社区宣传走访现场"),
        ("设计展", "设计展提案现场"),
        ("道路巡逻", "道路巡逻现场"),
        ("巡逻线", "道路巡逻现场"),
        ("社区走访", "社区走访现场"),
        ("走访", "社区走访现场"),
        ("晚间户外", "晚间户外活动现场"),
        ("街区采访", "街区采访现场"),
        ("沿海", "沿海巡逻岸线"),
        ("高山", "高山露天训练场"),
        ("大巴", "大巴转场途中"),
        ("酒店", "驻地酒店商务中心"),
    ]
    for kw, loc in patterns:
        if kw in env:
            env = loc
            break

    # 时段防冲突检查：如果时间是 11:00 以后的午间/下午/晚上，严禁出现“早高峰/早间/晨间”
    if time_str:
        m = re.search(r'(\d{1,2})[时:]', time_str)
        if m:
            hour = int(m.group(1))
            if hour >= 11:
                env = env.replace("早高峰", "外勤").replace("早间", "日间").replace("晨间", "日间")
            if hour < 17:
                env = env.replace("晚间", "日间").replace("夜间", "日间")

    if len(env) > 14 or any(kw in env for kw in ["当", "进入", "触发", "身处", "。"]):
        return "外勤保障现场"
    return env.strip("，, 。. ")

def _paraphrase_env(env: str) -> str:
    if "大巴" in env or "转场" in env:
        return "坐大巴车转场的路上"
    if "驻地" in env or "酒店" in env:
        return "外勤驻地酒店这边商务中心"
    if "现场" in env:
        return env.replace("现场", "活动这边现场")
    return f"{env}这边"


def _paraphrase_period(period_type: str) -> str:
    if period_type == "daily":
        return "按咱们中午那个例行档期"
    if period_type == "monthly":
        return "按咱们每月那个固定例会档期"
    return "按咱们每周那个固定例行档期"


def _implicit_service_phrase(srv: str) -> str:
    if any(k in srv for k in ("开直播", "转播", "带货", "推流")):
        return "上麦开播推流"
    if "看直播" in srv:
        return "蹲直播间看直播"
    if any(k in srv for k in ("会议", "开会", "视讯")):
        return "搞个线上投屏远程碰头会"
    if any(k in srv for k in ("游戏", "排位", "手游", "开黑")):
        return "上号打把排位赛"
    if "通话" in srv:
        return "连线打个视频通话"
    if "短视频" in srv:
        return "刷会儿短视频"
    return f"开启{srv}"


def _dur_cn_labels(mins: int) -> tuple[str, str]:
    mapping = {
        30: ("半小时", "半小时"),
        60: ("1个小时", "1小时"),
        90: ("1个半小时", "1.5小时"),
        120: ("2个小时", "2小时"),
        150: ("2个半小时", "2.5小时"),
        180: ("3个小时", "3小时"),
    }
    return mapping.get(mins, (f"{mins}分钟", f"{mins}分钟"))


def _formal_and_temp_dur_info(tp: dict) -> dict:
    formal_dur = str(tp.get("duration") or "120min")
    m_dur = re.search(r"(\d+)", formal_dur)
    formal_min = int(m_dur.group(1)) if m_dur else 120
    temp_min = 30 if formal_min <= 60 else 60
    temp_dur = f"{temp_min}min"
    formal_spoken, formal_short = _dur_cn_labels(formal_min)
    temp_spoken, temp_short = _dur_cn_labels(temp_min)
    sh_t = str(tp.get("start_timestamp") or "").split("日")[-1] or "14时00分"
    m_hm = re.search(r"(\d{1,2})时(\d{1,2})分", sh_t)
    if m_hm:
        tot = (int(m_hm.group(1)) * 60 + int(m_hm.group(2)) + temp_min) % (24 * 60)
        temp_end_t = f"{tot // 60:02d}时{tot % 60:02d}分"
    else:
        temp_end_t = "15时00分"
    return {
        "formal_dur": formal_dur,
        "formal_spoken": formal_spoken,
        "formal_short": formal_short,
        "temp_dur": temp_dur,
        "temp_spoken": temp_spoken,
        "temp_short": temp_short,
        "temp_end_t": temp_end_t,
    }

