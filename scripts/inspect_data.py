import sys
import json
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

def inspect_session(filepath):
    print(f"=== Inspecting {filepath} ===")
    with open(filepath, 'r', encoding='utf-8') as f:
        line = f.readline()
        if not line:
            print("Empty file")
            return
        data = json.loads(line)
        print("Session ID:", data.get("session_id"))
        print("User ID:", data.get("user_id"))
        print("Reference Time:", data.get("reference_time"))
        print("Meta:", data.get("session_meta"))
        print("Conversation:")
        for ev in data.get("event_sequence", []):
            turn = ev.get("turn")
            u = ev.get("user", {}).get("utterance")
            a = ev.get("agent", {}).get("utterance")
            u_act = ev.get("user", {}).get("action_types")
            a_act = ev.get("agent", {}).get("action_types")
            print(f"  [Turn {turn}]")
            print(f"    User ({u_act}): {u}")
            print(f"    Agent ({a_act}): {a}")

inspect_session('data/ref_template/pilot100_0813/rendered/sessions.T2-1.jsonl')
inspect_session('data/ref_template/pilot100_0813/rendered/sessions.T2-4.jsonl')
inspect_session('data/ref_template/pilot100_0813/rendered/sessions.X-1.jsonl')
