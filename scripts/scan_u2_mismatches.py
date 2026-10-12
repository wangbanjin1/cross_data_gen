import json
import glob
import os
import re

def scan_u2_timestamp_mismatch():
    persona_dirs = sorted(glob.glob("data/generated/mobile_persona_*"))
    mismatches = []
    for p_dir in persona_dirs:
        p_id = os.path.basename(p_dir)
        sess_file = os.path.join(p_dir, "sessions.json")
        if not os.path.exists(sess_file):
            continue
        with open(sess_file, "r", encoding="utf-8") as f:
            sessions = json.load(f)

        for s_idx, s in enumerate(sessions):
            evs = s.get("event_sequence", [])
            for ev in evs:
                if ev.get("turn") == 2:
                    u_utt = ev.get("user", {}).get("utterance", "")
                    intents = ev.get("turn_intents", [])
                    for tint in intents:
                        params = tint.get("params", {})
                        ts = params.get("timestamp", {})
                        if isinstance(ts, dict):
                            dur = ts.get("duration", {})
                            end_ts = ts.get("end_timestamp", {})
                            if dur.get("source_ref") == "U2" or end_ts.get("source_ref") == "U2":
                                # 检查 u_utt 是否有任何时长或时间词汇
                                # 常见时长词: 分钟, min, 小时, 点, 结束, 持续, 俩小时, 半小时
                                has_time_kw = bool(re.search(r'(\d+|两|俩|半)(分钟|min|小时|分)|持续|到\s*\d+|至\s*\d+', u_utt))
                                if not has_time_kw:
                                    mismatches.append({
                                        "persona": p_id,
                                        "session_id": s.get("session_id"),
                                        "turn": 2,
                                        "dur_val": dur.get("value"),
                                        "end_val": end_ts.get("value"),
                                        "u_utt": u_utt
                                    })
    print(f"Total U2 timestamp mismatches: {len(mismatches)}")
    for m in mismatches[:10]:
        print(f"  {m['persona']} {m['session_id']}: dur={m['dur_val']}, end={m['end_val']}")
        print(f"     U2: {m['u_utt']}")

if __name__ == "__main__":
    scan_u2_timestamp_mismatch()
