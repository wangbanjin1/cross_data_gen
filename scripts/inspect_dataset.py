import json
from pathlib import Path

def main():
    base = Path("data/generated")
    skeletons = sorted(base.glob("mobile_persona_*/persona_skeleton.json"))
    print(f"Total skeletons found: {len(skeletons)}")
    
    mode_counts = {}
    trig_counts = {}

    for s_path in skeletons:
        with open(s_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        pid = data.get("persona_id")
        main_story = data["dynamic_profile"]["periodic_main_storyline"]
        mode = main_story.get("declaration_mode")
        trig = main_story.get("storyline_trigger_type")
        cond = main_story.get("trigger_condition")

        mode_counts[mode] = mode_counts.get(mode, 0) + 1
        trig_counts[trig] = trig_counts.get(trig, 0) + 1

        print(f"[{pid}] Mode: {mode:20s} | Trigger: {trig:20s} | Cond: {cond}")

    print("\n--- Summary ---")
    print("Declaration Modes:", mode_counts)
    print("Storyline Triggers:", trig_counts)

if __name__ == "__main__":
    main()
