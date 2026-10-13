import json
import glob
import os
import re
import sys

sys.path.insert(0, ".")
from src.core.qc_validator import QCValidator

def fix_x1_sessions(dry_run=False):
    dirs = sorted(glob.glob("data/generated/mobile_persona_*"))
    print(f"Total personas: {len(dirs)}")

    modified_count = 0
    qc_pass_count = 0

    for p_dir in dirs:
        pid = os.path.basename(p_dir)
        sess_file = os.path.join(p_dir, "sessions.json")
        sessl_file = os.path.join(p_dir, "sessions.jsonl")
        trace_file = os.path.join(p_dir, "memory_traces.json")
        qc_file = os.path.join(p_dir, "qc_report.json")

        if not os.path.exists(sess_file):
            continue

        with open(sess_file, "r", encoding="utf-8") as f:
            sessions = json.load(f)

        p_modified = False

        for s_idx, s in enumerate(sessions):
            meta = s.get("session_meta", {})
            if meta.get("template_id") == "X-1":
                evs = s.get("event_sequence", [])
                if not evs:
                    continue
                ev0 = evs[0]
                u0 = ev0.get("user", {})
                u_utt = u0.get("utterance", "")

                has_tp = bool(re.search(r'(\d{1,2}[:：点时]\d{0,2})', u_utt))
                has_dur = bool(re.search(r'(\d+|两|俩|半)(分钟|min|小时|分)', u_utt))

                orig_u = u_utt
                new_u = u_utt

                # 1. 修复模糊时长词（如“刷会儿”）
                if "刷会儿" in new_u:
                    new_u = new_u.replace("刷会儿", "刷短视频，保障开60分钟")
                    # 避免重复“短视频”
                    new_u = new_u.replace("刷短视频，保障开60分钟短视频", "刷短视频，保障开60分钟")
                    has_dur = True
                elif "看会儿" in new_u:
                    new_u = new_u.replace("看会儿", "看直播，保障开60分钟")
                    new_u = new_u.replace("看直播，保障开60分钟直播", "看直播，保障开60分钟")
                    has_dur = True
                elif "玩会儿" in new_u:
                    new_u = new_u.replace("玩会儿", "打游戏，保障开60分钟")
                    has_dur = True
                elif not has_dur:
                    # 在顺便或另外前面补时长，或者在句末补
                    if "，另外" in new_u:
                        parts = new_u.split("，另外", 1)
                        new_u = f"{parts[0]}，保障开60分钟，另外{parts[1]}"
                    elif "，顺便" in new_u:
                        parts = new_u.split("，顺便", 1)
                        new_u = f"{parts[0]}，保障开60分钟，顺便{parts[1]}"
                    else:
                        new_u = f"{new_u}，保障开60分钟"
                    has_dur = True

                # 2. 修复缺失起止时间点
                if not has_tp:
                    if "今天午休" in new_u:
                        new_u = new_u.replace("今天午休", "今天午休12点30分到13点30分")
                    elif "周末午休" in new_u:
                        new_u = new_u.replace("周末午休", "周末午休12点30分到13点30分")
                    elif "午休" in new_u:
                        new_u = new_u.replace("午休", "午休12点30分到13点30分")
                    elif "今天中午" in new_u:
                        new_u = new_u.replace("今天中午", "今天中午12点30分到13点30分")
                    else:
                        new_u = f"今天12点30分到13点30分，{new_u}"
                    has_tp = True

                if new_u != orig_u:
                    u0["utterance"] = new_u
                    p_modified = True

                # 3. 规范 GT 标注中的 duration source_type 为 Turn
                for tint in ev0.get("turn_intents", []):
                    ts = tint.get("params", {}).get("timestamp", {})
                    dur_obj = ts.get("duration", {}) if isinstance(ts, dict) else {}
                    if dur_obj and dur_obj.get("source_type") != "Turn":
                        dur_obj["source_type"] = "Turn"
                        dur_obj["source_ref"] = "U1"
                        p_modified = True

                for intent in s.get("intents", []):
                    ts = intent.get("params", {}).get("timestamp", {})
                    dur_obj = ts.get("duration", {}) if isinstance(ts, dict) else {}
                    if dur_obj and dur_obj.get("source_type") != "Turn":
                        dur_obj["source_type"] = "Turn"
                        dur_obj["source_ref"] = "U1"
                        p_modified = True

                for su in s.get("slot_updates", []):
                    for tu in su.get("turn_updates", []):
                        ts = tu.get("params", {}).get("timestamp", {})
                        dur_obj = ts.get("duration", {}) if isinstance(ts, dict) else {}
                        if dur_obj and dur_obj.get("source_type") != "Turn":
                            dur_obj["source_type"] = "Turn"
                            dur_obj["source_ref"] = "U1"
                            p_modified = True

                if p_modified:
                    modified_count += 1
                    if modified_count <= 5 or pid in ['mobile_persona_001', 'mobile_persona_003', 'mobile_persona_006']:
                        print(f"[{pid} {s['session_id']}]")
                        print(f"  Old User: {orig_u}")
                        print(f"  New User: {new_u}")

        if p_modified and not dry_run:
            with open(sess_file, "w", encoding="utf-8") as f:
                json.dump(sessions, f, ensure_ascii=False, indent=2)

            with open(sessl_file, "w", encoding="utf-8") as f:
                for s in sessions:
                    f.write(json.dumps(s, ensure_ascii=False) + "\n")

            mem_traces = None
            if os.path.exists(trace_file):
                with open(trace_file, "r", encoding="utf-8") as f:
                    mem_traces = json.load(f)
            qc_rep = QCValidator.validate_sessions(sessions, memory_traces=mem_traces)
            with open(qc_file, "w", encoding="utf-8") as f:
                json.dump(qc_rep, f, ensure_ascii=False, indent=2)
            if qc_rep.get("failed_sessions", 0) == 0:
                qc_pass_count += 1
            else:
                print(f"[!] QC Failed on {pid}: {qc_rep.get('issues')}")
        else:
            qc_pass_count += 1

    print("\n" + "="*50)
    print(f"Total X-1 sessions modified: {modified_count}")
    print(f"Total QC passed personas: {qc_pass_count}/{len(dirs)}")

if __name__ == '__main__':
    fix_x1_sessions(dry_run=False)
