# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

def inspect_persona(persona_dir: str, start: int = 1, end: int = 25):
    with open(f"{persona_dir}/persona_skeleton.json", "r", encoding="utf-8") as f:
        skeleton = json.load(f)
    
    with open(f"{persona_dir}/sessions.jsonl", "r", encoding="utf-8") as f:
        sessions = [json.loads(l) for l in f]

    print("=" * 60)
    print(f"画像概览: {skeleton['persona_id']} - {skeleton['category']}")
    print(f"职业身份: {skeleton['static_profile']['identity']}")
    print(f"说话风格: {skeleton['static_profile']['speech_style']['tone']}")
    print(f"口头禅: {', '.join(skeleton['static_profile']['speech_style']['catchphrases'])}")
    print(f"总会话数: {len(sessions)}")
    print("=" * 60)

    for i, s in enumerate(sessions):
        if not (start <= i + 1 <= end):
            continue
        meta = s["session_meta"]
        closure = s["intents"][0]["closure_path"] if s.get("intents") else "None"
        env = meta["scenario"].get("environment", "")
        print(f"\n--- [Session {i+1:02d}] {s['session_id']} ({s['reference_time']}) ---")
        print(f"模板: {meta['template_id']} | 角色: {meta['memory_role']} | 闭环: {closure} | 物理地点: {env} | 轮数: {meta['round_count']}")
        for ev in s["event_sequence"]:
            print(f"  [Turn {ev['turn']}]")
            print(f"    User : {ev['user']['utterance']}  (action: {ev['user']['action_types']})")
            print(f"    Agent: {ev['agent']['utterance']} (action: {ev['agent']['action_types']})")
            if ev.get("requested_params"):
                print(f"    -> requested_params: {ev['requested_params']}")

if __name__ == "__main__":
    p_dir = sys.argv[1] if len(sys.argv) > 1 else "data/cognitive_samples/mobile_persona_001"
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    end = int(sys.argv[3]) if len(sys.argv) > 3 else 25
    inspect_persona(p_dir, start, end)
