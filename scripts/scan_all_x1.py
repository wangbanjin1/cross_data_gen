import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

import json
import glob
import os
import re

def scan_all_x1():
    dirs = sorted(glob.glob("data/generated/mobile_persona_*"))
    logger.info(f"Total personas: {len(dirs)}")

    results = []
    no_time_point = [] # 用户没说具体点点分分
    no_duration = []   # 用户没说具体时长数值

    for p_dir in dirs:
        pid = os.path.basename(p_dir)
        path = os.path.join(p_dir, "sessions.json")
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            sessions = json.load(f)

        for s_idx, s in enumerate(sessions):
            if s.get("session_meta", {}).get("template_id") == "X-1":
                ev = s["event_sequence"][0]
                u_utt = ev["user"]["utterance"]
                a_utt = ev["agent"]["utterance"]
                ts_params = ev["turn_intents"][0]["params"].get("timestamp", {})

                has_time_point = bool(re.search(r'(\d{1,2}[:：点时]\d{0,2})', u_utt))
                has_dur_val = bool(re.search(r'(\d+|两|俩|半)(分钟|min|小时|分)', u_utt))

                results.append({
                    "pid": pid,
                    "session_id": s["session_id"],
                    "session_idx": s_idx + 1,
                    "ref_time": s["reference_time"],
                    "u_utt": u_utt,
                    "has_time_point": has_time_point,
                    "has_dur_val": has_dur_val,
                    "start_ts": ts_params.get("start_timestamp", {}).get("value"),
                    "end_ts": ts_params.get("end_timestamp", {}).get("value"),
                    "dur": ts_params.get("duration", {}).get("value"),
                })
                if not has_time_point:
                    no_time_point.append(pid)
                if not has_dur_val:
                    no_duration.append(pid)

    logger.info(f"Total X-1 sessions: {len(results)}")
    logger.info(f"X-1 sessions where user didn't mention specific time point (e.g. 12:30): {len(no_time_point)} / {len(results)}")
    logger.info(f"X-1 sessions where user didn't mention duration: {len(no_duration)} / {len(results)}")

    with open("scripts/x1_scan_report.txt", "w", encoding="utf-8") as out:
        for r in results:
            out.write(f"{r['pid']} {r['session_id']} (time_point={r['has_time_point']}, dur={r['has_dur_val']})\n")
            out.write(f"  User: {r['u_utt']}\n")
            out.write(f"  GT: start={r['start_ts']}, end={r['end_ts']}, dur={r['dur']}\n")

if __name__ == '__main__':
    scan_all_x1()
