import os
import sys
import json
import time
import argparse
from pathlib import Path

from src.config import Config
from src.llm_client import LLMClient
from src.persona_generator import PersonaGenerator
from src.dynamic_timeline_planner import DynamicTimelinePlanner
from src.dialogue_generator import DialogueGenerator
from src.memory_tracker import MemoryTracker
from src.qc_validator import QCValidator

class BatchPipeline:
    def __init__(self, output_dir: str = "data/generated"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.ckpt_path = self.output_dir / "checkpoint.json"
        self.checkpoint = self._load_checkpoint()
        self.llm = LLMClient()
        self.persona_gen = PersonaGenerator(self.llm)
        self.dialogue_gen = DialogueGenerator(self.llm)

    def _load_checkpoint(self) -> dict:
        if self.ckpt_path.exists():
            with open(self.ckpt_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"completed_personas": []}

    def _save_checkpoint(self):
        with open(self.ckpt_path, "w", encoding="utf-8") as f:
            json.dump(self.checkpoint, f, ensure_ascii=False, indent=2)

    def process_single_persona(self, raw_persona: dict) -> bool:
        pid = raw_persona.get("persona_id")
        
        # 每个样本独立文件夹
        sample_dir = self.output_dir / pid
        sample_dir.mkdir(parents=True, exist_ok=True)

        if pid in self.checkpoint["completed_personas"] and (sample_dir / "sessions.jsonl").exists():
            print(f"[-] Persona {pid} already completed in {sample_dir}, skipping.")
            return True

        print(f"\n=======================================================")
        print(f"[+] Processing Persona {pid} ({raw_persona.get('persona_summary')})...")
        print(f"    Output Folder -> {sample_dir}")
        t0 = time.time()
        self.llm.reset_usage()
        
        # 1. 扩充详细画像骨架 (DeepSeek API, thinking disabled)
        persona_skeleton_path = sample_dir / "persona_skeleton.json"
        if persona_skeleton_path.exists():
            with open(persona_skeleton_path, "r", encoding="utf-8") as f:
                persona_skeleton = json.load(f)
            print(f"    - Loaded existing Persona Skeleton -> {persona_skeleton_path.name}")
        else:
            persona_skeleton = self.persona_gen.generate_skeleton(raw_persona)
            with open(persona_skeleton_path, "w", encoding="utf-8") as f:
                json.dump(persona_skeleton, f, ensure_ascii=False, indent=2)
            print(f"    - Generated Persona Skeleton -> {persona_skeleton_path.name}")

        # 2. 动态规划 15 会话时间线
        timeline = DynamicTimelinePlanner.plan(persona_skeleton)
        print(f"    - Planned {len(timeline)} sessions across timeline.")

        # 3. 计算记忆状态演进与批次渲染
        memory_tracker = MemoryTracker()
        planned_items = []
        memory_traces = []

        for s_plan in timeline:
            snap_before, mem_events, gold_after = memory_tracker.process_session(s_plan)
            planned_items.append((s_plan, snap_before, mem_events, gold_after))
            memory_traces.append({
                "session_id": s_plan["session_id"],
                "reference_time": s_plan["reference_time"],
                "memory_role": s_plan["memory_role"],
                "blueprint_type": s_plan["blueprint_type"],
                "snapshot_before": snap_before,
                "memory_events": mem_events,
                "gold_state_after": gold_after
            })

        print(f"    - Batch rendering 15 sessions with DeepSeek Flash (thinking disabled)...")
        rendered_sessions = self.dialogue_gen.generate_sessions_batch(planned_items, persona_skeleton, batch_size=5)

        # 4. 保存标准对话 sessions.jsonl
        out_sessions_path = sample_dir / "sessions.jsonl"
        with open(out_sessions_path, "w", encoding="utf-8") as f:
            for s in rendered_sessions:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")

        # 5. 保存评测记忆萃取能力的 memory_traces.json
        out_traces_path = sample_dir / "memory_traces.json"
        with open(out_traces_path, "w", encoding="utf-8") as f:
            json.dump({
                "persona_id": pid,
                "user_id": persona_skeleton["static_profile"]["user_id"],
                "session_traces": memory_traces
            }, f, ensure_ascii=False, indent=2)

        # 6. 运行自动化质检并保存 qc_report.json
        qc_result = QCValidator.validate_sessions(rendered_sessions)
        qc_report_path = sample_dir / "qc_report.json"
        with open(qc_report_path, "w", encoding="utf-8") as f:
            json.dump(qc_result, f, ensure_ascii=False, indent=2)

        elapsed = time.time() - t0
        usage = self.llm.get_usage()
        print(f"    [Cost & Tokens] Calls: {usage['calls']} | Tokens: {usage['total_tokens']} (In: {usage['total_prompt_tokens']}, Out: {usage['completion_tokens']}) | Cost: ￥{usage['cost_rmb']:.4f} 元")
        print(f"    [QC Report] Pass Rate: {qc_result['pass_rate']} ({qc_result['passed_sessions']}/{qc_result['total_sessions']})")
        print(f"    [SUCCESS] {pid} finished in {elapsed:.1f}s -> {sample_dir}")

        # 7. 更新 Checkpoint
        if pid not in self.checkpoint["completed_personas"]:
            self.checkpoint["completed_personas"].append(pid)
            self._save_checkpoint()

        return True

    def run_batch(self, start_idx: int = 0, count: int = 1):
        with open("data/original/mobile_network_personas_500.json", "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        personas_to_run = raw_data["personas"][start_idx : start_idx + count]
        print(f"=== Starting Batch Pipeline: {len(personas_to_run)} personas (index {start_idx} to {start_idx + count - 1}) ===")

        total_cost = 0.0
        total_tokens = 0

        for raw_p in personas_to_run:
            try:
                self.process_single_persona(raw_p)
                u = self.llm.get_usage()
                total_cost += u["cost_rmb"]
                total_tokens += u["total_tokens"]
            except Exception as e:
                print(f"[!] Error processing {raw_p.get('persona_id')}: {e}")

        print(f"\n=======================================================")
        print(f"=== Batch Finished! Processed {len(personas_to_run)} personas ===")
        print(f"=== Total Tokens: {total_tokens} | Total Cost: ￥{total_cost:.4f} 元 ===")
        print(f"=======================================================\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch pipeline for cross-session memory dataset generation")
    parser.add_argument("--start", type=int, default=0, help="Start persona index (0-based)")
    parser.add_argument("--count", type=int, default=1, help="Number of personas to process")
    args = parser.parse_args()

    pipeline = BatchPipeline()
    pipeline.run_batch(start_idx=args.start, count=args.count)
