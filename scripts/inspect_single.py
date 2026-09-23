import json
from pathlib import Path

def inspect(sample_dir):
    sess_file = Path(sample_dir) / "sessions.jsonl"
    with open(sess_file, "r", encoding="utf-8") as f:
        sessions = [json.loads(line) for line in f]
    
    print(f"Total sessions: {len(sessions)}")
    for s in sessions:
        sid = s["session_id"]
        tid = s["session_meta"]["template_id"]
        role = s["session_meta"]["memory_role"]
        ref_time = s["reference_time"]
        tp = s["intents"][0].get("params", {}) if s["intents"] else {}
        app = tp.get("application_name", {}).get("value", "N/A")
        srv = tp.get("service_name", {}).get("value", "N/A")
        dur = tp.get("timestamp", {}).get("duration", {}).get("value", "N/A")
        print(f"\n[{sid}] ({tid}, {role}) @ {ref_time} | {app}-{srv} ({dur})")
        for ev in s["event_sequence"]:
            t = ev["turn"]
            u = ev["user"]["utterance"]
            u_acts = ev["user"]["action_types"]
            a = ev["agent"]["utterance"]
            a_acts = ev["agent"]["action_types"]
            print(f"  Turn {t}:")
            print(f"    User ({u_acts}): {u}")
            print(f"    Agent ({a_acts}): {a}")

if __name__ == "__main__":
    inspect("data/test_gen/mobile_persona_001")
