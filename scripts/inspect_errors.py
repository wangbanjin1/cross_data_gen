import json
import os

def check_personas(persona_configs):
    with open("scripts/inspection_result.txt", "w", encoding="utf-8") as out:
        for p_id, sess_list in persona_configs:
            path = f"data/generated/{p_id}/sessions.json"
            if not os.path.exists(path):
                out.write(f"Not found: {path}\n")
                continue
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            out.write(f"\n=================== {p_id} ===================\n")
            for i, s in enumerate(data):
                if sess_list and (i+1) not in sess_list:
                    continue
                meta = s.get("session_meta", {})
                out.write(f"\n--- Session {i+1} ({s['session_id']}) ---\n")
                out.write(f"  Template: {meta.get('template_id')}, Role: {meta.get('memory_role')}, Ref: {s.get('reference_time')}\n")
                out.write(f"  Scenario: {json.dumps(meta.get('scenario'), ensure_ascii=False)}\n")
                for ev in s.get("event_sequence", []):
                    turn_no = ev.get("turn")
                    u = ev.get("user", {})
                    a = ev.get("agent", {})
                    out.write(f"  Turn {turn_no} [User]: {u.get('utterance')}\n")
                    out.write(f"         acts: {u.get('action_types')}\n")
                    out.write(f"  Turn {turn_no} [Agent]: {a.get('utterance')}\n")
                    out.write(f"         acts: {a.get('action_types')}\n")
                    intents = ev.get("turn_intents", [])
                    for tint in intents:
                        out.write(f"    Intent {tint.get('intent_id')}: {tint.get('intent')}, status: {tint.get('status')}\n")
                        params = tint.get("params", {})
                        param_strs = []
                        for pk, pv in params.items():
                            param_strs.append(f"{pk}={pv.get('value')}({pv.get('source_type')}:{pv.get('source_ref')})")
                        out.write(f"      Params: {', '.join(param_strs)}\n")

if __name__ == "__main__":
    check_personas([
        ("mobile_persona_004", [1, 2, 3]),
        ("mobile_persona_008", [1, 2, 3]),
        ("mobile_persona_005", [8]),
        ("mobile_persona_007", [7, 10]),
        ("mobile_persona_019", [1, 4]),
        ("mobile_persona_017", [1]),
    ])
    print("Done writing to scripts/inspection_result.txt")
