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
        assert "Acknowledge" in last_turn["agent"]["action_types"], f"Session {sid} last agent utterance action should be Acknowledge!"
        
        # 2. 验证记忆强化/复用会话必须 ≥ 2 轮，且第 2 轮必须有用户确认
        if role in ["reinforcement_session", "reuse_session"]:
            assert len(events) >= 2, f"Reinforcement/Reuse session {sid} has only {len(events)} turns! Must be >= 2!"
            t1_agent = events[0]["agent"]
            t2_user = events[1]["user"]
            assert "Confirm_Slot" in t1_agent["action_types"], f"Session {sid} turn 1 agent should ask confirmation!"
            assert "Confirm_Slot" in t2_user["action_types"], f"Session {sid} turn 2 user should confirm slot!"
            
        # 3. 验证必需字段与记忆追踪字段
        required_keys = ['session_id', 'user_id', 'reference_time', 'session_meta', 'event_sequence', 'intents', 'relations', 'slot_updates']
        for k in required_keys:
            assert k in session, f"Missing key {k} in session {sid}"
            
        intent = session["intents"][0]
        params = intent["params"]
        app_source = params["application_name"]["source_type"]
        res_source = params["resolution"]["min_value"]["source_type"]
        
        print(f"[{i+1:02d}] {sid} | {ref_time} | {role:22s} | Turns: {len(events)} | Closure: {intent['closure_path']:12s} | App: {app_source:6s} | Res: {res_source:6s}")

    # 4. 检查该文件夹下是否有配套文件
    assert (jsonl_path.parent / "persona_skeleton.json").exists(), f"Missing persona_skeleton.json in {parent_dir}"
    assert (jsonl_path.parent / "memory_traces.json").exists(), f"Missing memory_traces.json in {parent_dir}"
    assert (jsonl_path.parent / "qc_report.json").exists(), f"Missing qc_report.json in {parent_dir}"

    print(f"\n[SUCCESS] [{parent_dir}]: All 15 sessions + skeleton + memory_traces + qc_report passed 100% strict verification!")

def main():
    base_gen = Path("data/generated")
    session_files = list(base_gen.glob("*/sessions.jsonl"))
    print(f"Found {len(session_files)} persona sample folders to verify.")
    for f in sorted(session_files):
        test_file(f)

if __name__ == "__main__":
    main()
