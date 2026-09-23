# -*- coding: utf-8 -*-
import sys
import json
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

def test_file(jsonl_path: Path):
    with open(jsonl_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    total = len(lines)
    parent_dir = jsonl_path.parent.name
    print(f"\n=======================================================")
    print(f"=== Verifying {total} sessions in [{parent_dir}] ===")
    print(f"=======================================================")
    assert 10 <= total <= 20, f"Timeline length must be between 10 and 20, got {total}"
    
    for i, line in enumerate(lines):
        session = json.loads(line)
        sid = session["session_id"]
        role = session["session_meta"]["memory_role"]
        ref_time = session["reference_time"]
        events = session["event_sequence"]
        
        # 1. 验证必须以 Agent 答复结束
        last_turn = events[-1]
        assert "agent" in last_turn and last_turn["agent"]["utterance"], f"Session {sid} does not end with Agent utterance!"
        assert any(act in last_turn["agent"]["action_types"] for act in ["Acknowledge", "Reject_Request"]), f"Session {sid} last agent utterance action should be Acknowledge or Reject_Request!"
        
        # 2. 验证记忆强化/复用会话必须 ≥ 2 轮，且第 2 轮必须有用户确认
        if role in ["reinforcement_session", "reuse_session"]:
            assert len(events) >= 2, f"Reinforcement/Reuse session {sid} has only {len(events)} turns! Must be >= 2!"
            t1_agent = events[0]["agent"]
            t2_user = events[1]["user"]
            assert any(act in t1_agent["action_types"] for act in ["Confirm_Slot", "Request_Slot", "Request_Disambiguation"]), f"Session {sid} turn 1 agent should ask confirmation or disambiguation!"
            assert "Confirm_Slot" in t2_user["action_types"], f"Session {sid} turn 2 user should confirm slot!"
            
        # 3. 验证必需字段与记忆追踪字段
        required_keys = ['session_id', 'user_id', 'reference_time', 'session_meta', 'event_sequence', 'intents', 'relations', 'slot_updates']
        for k in required_keys:
            assert k in session, f"Missing key {k} in session {sid}"

        # 4. 验证 Turn 级意图隔离性与无泄露
        for ev_idx, ev in enumerate(events):
            assert "turn_intents" in ev, f"Session {sid} turn {ev_idx+1} missing turn_intents!"
            assert "requested_params" in ev, f"Session {sid} turn {ev_idx+1} missing requested_params!"

        if role == "evidence_session" and len(events) >= 2:
            t1_params = events[0]["turn_intents"][0].get("params", {})
            assert "resolution" not in t1_params, f"Session {sid} Turn 1 intent answers leaked resolution!"
            assert "rtt" not in t1_params, f"Session {sid} Turn 1 intent answers leaked rtt!"
            t1_u_utt = events[0]["user"]["utterance"]
            assert not any(kw in t1_u_utt for kw in ["老规矩", "老时间", "老样子"]), f"Evidence session {sid} Turn 1 user utterance has premature rule codewords: {t1_u_utt}"
            for su in session.get("slot_updates", []):
                for tu in su.get("turn_updates", []):
                    if tu.get("turn") == 1:
                        p = tu.get("params", {})
                        assert "resolution" not in p and "rtt" not in p, f"Session {sid} Turn 1 slot_updates leaked resolution/rtt!"
            
        intent = session["intents"][0]
        if intent.get("status") == "rejected":
            app_source, res_source = "None", "None"
        else:
            params = intent["params"]
            app_source = params["application_name"]["source_type"]
            res_source = params["resolution"]["min_value"]["source_type"]
        
        print(f"[{i+1:02d}] {sid} | {ref_time} | {role:22s} | Turns: {len(events)} | Closure: {intent['closure_path']:12s} | App: {app_source:6s} | Res: {res_source:6s}")

    # 4. 检查该文件夹下是否有配套文件
    assert (jsonl_path.parent / "persona_skeleton.json").exists(), f"Missing persona_skeleton.json in {parent_dir}"
    assert (jsonl_path.parent / "memory_traces.json").exists(), f"Missing memory_traces.json in {parent_dir}"
    assert (jsonl_path.parent / "qc_report.json").exists(), f"Missing qc_report.json in {parent_dir}"

    print(f"\n[SUCCESS] [{parent_dir}]: All {total} sessions + skeleton + memory_traces + qc_report passed 100% strict verification!")

def main(output_dir: str = None):
    base_gen = Path(output_dir or "data/generated")
    session_files = list(base_gen.glob("*/sessions.jsonl"))
    print(f"Found {len(session_files)} persona sample folders in '{base_gen}' to verify.")
    for f in sorted(session_files):
        test_file(f)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Verify generated datasets")
    parser.add_argument("--output", "-o", type=str, default="data/generated", help="Output directory to verify")
    args = parser.parse_args()
    main(output_dir=args.output)
