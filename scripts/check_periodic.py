import sys
import json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

for p_dir in sorted(Path("data/generated").glob("mobile_persona_*")):
    sk_path = p_dir / "persona_skeleton.json"
    if not sk_path.exists():
        continue
    with open(sk_path, "r", encoding="utf-8") as f:
        sk = json.load(f)
    main = sk["dynamic_profile"]["periodic_main_storyline"]
    trig_type = main.get("storyline_trigger_type")
    if trig_type == "time_periodic":
        print(f"[{sk['persona_id']}] {sk.get('persona_summary')}")
        print(f"  period_type: {main.get('period_type')}")
        print(f"  days: {main.get('days')}")
        print(f"  time_range: {main.get('time_range')}")
        print(f"  trigger_condition: {main.get('trigger_condition')}")
        print(f"  declaration_mode: {main.get('declaration_mode')}")
        
        # 查看 Session 01 和 Session 03 的台词
        sess_path = p_dir / "sessions.jsonl"
        with open(sess_path, "r", encoding="utf-8") as sf:
            s_lines = [json.loads(line) for line in sf]
            s01 = s_lines[0]
            s03 = s_lines[2]
            print(f"  S01 (T2-4) Turn 2 User: {s01['event_sequence'][1]['user']['utterance']}")
            print(f"  S03 (T2-1) Turn 1 Agent: {s03['event_sequence'][0]['agent']['utterance']}")
        print()
