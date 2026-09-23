import json
from pathlib import Path
from src.config import Config
from src.persona_builder import PersonaBuilder
from src.timeline_planner import TimelinePlanner
from src.dialogue_engine import DialogueEngine

class CrossSessionPipeline:
    def __init__(self):
        self.output_dir = Path("data/generated")
        self.personas_dir = self.output_dir / "personas"
        self.sessions_dir = self.output_dir / "sessions"
        self.personas_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def run_single_persona(self, persona_index: int = 0):
        # 1. 读取原始画像
        with open("data/original/mobile_network_personas_500.json", "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        raw_persona = raw_data["personas"][persona_index]
        print(f"[*] Loaded raw persona: {raw_persona.get('persona_id')} ({raw_persona.get('persona_summary')})")

        # 2. 生成解耦的详细画像骨架 (包含主线、支线、场景化事件、语体)
        persona_skeleton = PersonaBuilder.build_persona_001(raw_persona)
        persona_path = self.personas_dir / f"{persona_skeleton['persona_id']}.json"
        with open(persona_path, "w", encoding="utf-8") as f:
            json.dump(persona_skeleton, f, ensure_ascii=False, indent=2)
        print(f"[+] Saved structured persona skeleton -> {persona_path}")

        # 3. 规划时间线会话序列 (Session Sequence)
        timeline = TimelinePlanner.plan_timeline(persona_skeleton)
        print(f"[+] Planned {len(timeline)} sessions across timeline:")
        for s in timeline:
            print(f"    - {s['session_id']} | {s['reference_time']} | {s['memory_role']} | {s['template_id']} | {s['scenario_hook']}")

        # 4. 逐会话渲染对话并管理记忆状态
        memory_store = {}
        rendered_sessions = []
        for s_plan in timeline:
            rendered = DialogueEngine.render_session(s_plan, persona_skeleton, memory_store)
            rendered_sessions.append(rendered)

        # 5. 输出为标准 ref_template 格式的 JSONL
        out_sessions_path = self.sessions_dir / f"{persona_skeleton['persona_id']}_sessions.jsonl"
        with open(out_sessions_path, "w", encoding="utf-8") as f:
            for s in rendered_sessions:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        print(f"[+] Successfully wrote {len(rendered_sessions)} sessions to {out_sessions_path}")

        return persona_skeleton, rendered_sessions

if __name__ == "__main__":
    pipeline = CrossSessionPipeline()
    persona, sessions = pipeline.run_single_persona(0)
