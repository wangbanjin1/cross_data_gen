import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

import json
import glob
import os
import re
from datetime import datetime

# 解析参考时间中的日期
def parse_date_from_ref(ref_time_str):
    # 示例: 2026年10月28日12时30分
    m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', ref_time_str or "")
    if m:
        y, month, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        dt = datetime(y, month, d)
        return dt, dt.weekday() # 0: Mon, ..., 5: Sat, 6: Sun
    return None, None

def scan_dataset():
    persona_dirs = sorted(glob.glob("data/generated/mobile_persona_*"))
    logger.info(f"Total persona dirs found: {len(persona_dirs)}")

    x1_weekday_with_weekend_word = []
    t21_s03_implicit = []
    t25_half_day = []
    dst_missing_duration = []

    for p_dir in persona_dirs:
        p_id = os.path.basename(p_dir)
        sess_file = os.path.join(p_dir, "sessions.json")
        if not os.path.exists(sess_file):
            continue
        with open(sess_file, "r", encoding="utf-8") as f:
            sessions = json.load(f)

        for s_idx, s in enumerate(sessions):
            meta = s.get("session_meta", {})
            tid = meta.get("template_id")
            role = meta.get("memory_role")
            ref_time = s.get("reference_time", "")
            dt, weekday = parse_date_from_ref(ref_time)
            evs = s.get("event_sequence", [])

            # Check 1: X-1 with "周末" on weekday
            if tid == "X-1":
                for ev in evs:
                    u_utt = ev.get("user", {}).get("utterance", "")
                    if "周末" in u_utt and weekday is not None and weekday < 5:
                        x1_weekday_with_weekend_word.append({
                            "persona": p_id,
                            "session_id": s.get("session_id"),
                            "session_idx": s_idx + 1,
                            "ref_time": ref_time,
                            "weekday": weekday, # 0=Mon..4=Fri
                            "user_utterance": u_utt
                        })

            # Check 2: T2-1 S-03 implicit "按上次的来" without app/service
            if s_idx == 2 and role == "reinforcement_session":
                for ev in evs:
                    if ev.get("turn") == 1:
                        u_utt = ev.get("user", {}).get("utterance", "")
                        if "按上次" in u_utt or "上次一样" in u_utt:
                            # 检查是否包含了 app 或 service
                            t21_s03_implicit.append({
                                "persona": p_id,
                                "session_id": s.get("session_id"),
                                "user_utterance": u_utt
                            })

            # Check 3: T2-5 with "半天"
            if tid == "T2-5":
                for ev in evs:
                    u_utt = ev.get("user", {}).get("utterance", "")
                    if "半天" in u_utt:
                        t25_half_day.append({
                            "persona": p_id,
                            "session_id": s.get("session_id"),
                            "user_utterance": u_utt
                        })

    logger.info(f"\n1. X-1 with '周末' on weekday: {len(x1_weekday_with_weekend_word)} occurrences")
    for item in x1_weekday_with_weekend_word[:10]:
        logger.info(f"   {item['persona']} {item['session_id']} (weekday={item['weekday']}, {item['ref_time']}): {item['user_utterance'][:50]}...")

    logger.info(f"\n2. S-03 T2-1 implicit '按上次的来': {len(t21_s03_implicit)} occurrences")
    for item in t21_s03_implicit[:10]:
        logger.info(f"   {item['persona']} {item['session_id']}: {item['user_utterance']}")

    logger.info(f"\n3. T2-5 with '半天': {len(t25_half_day)} occurrences")
    for item in t25_half_day:
        logger.info(f"   {item['persona']} {item['session_id']}: {item['user_utterance']}")

if __name__ == "__main__":
    scan_dataset()
