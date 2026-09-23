import os
import sys
import json
import time
import argparse
from pathlib import Path

from src.config.settings import Config
from src.generation.llm_client import LLMClient
from src.generation.persona_generator import PersonaGenerator
from src.generation.dialogue_generator import DialogueGenerator
from src.core.timeline_planner import DynamicTimelinePlanner
from src.core.memory_tracker import MemoryTracker
from src.core.qc_validator import QCValidator

class BatchPipeline:
    """
    批处理流水线调度器 (BatchPipeline)
    串联：原始画像读取 -> 画像骨架扩充 -> 时间线规划 -> 记忆演进追踪 -> 批次对话渲染 -> 结构组装 -> 自动化质检 -> Checkpoint 保存。
    """

    def __init__(self, output_dir: str = None, raw_persona_path: str = None, batch_size: int = None, model: str = None, base_url: str = None):
        self.output_dir = Path(output_dir or Config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.raw_persona_path = Path(raw_persona_path or Config.raw_persona_path)
        self.batch_size = batch_size or Config.batch_size
        self.ckpt_path = self.output_dir / "checkpoint.json"
        self.checkpoint = self._load_checkpoint()
        self.llm = LLMClient(model=model or Config.model, base_url=base_url or Config.base_url)
        self.persona_gen = PersonaGenerator(self.llm)
        self.dialogue_gen = DialogueGenerator(self.llm)

    def _load_checkpoint(self) -> dict:
        if self.ckpt_path.exists():
            with open(self.ckpt_path, "r", encoding="utf-8-sig") as f:
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
        rendered_sessions = self.dialogue_gen.generate_sessions_batch(planned_items, persona_skeleton, batch_size=self.batch_size)

        # 4. 保存标准对话 sessions.jsonl
        out_sessions_path = sample_dir / "sessions.jsonl"
        with open(out_sessions_path, "w", encoding="utf-8") as f:
            for s in rendered_sessions:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")

        # 5. 保存评测记忆萃取能力的 memory_traces.json
        out_traces_path = sample_dir / "memory_traces.json"
        with open(out_traces_path, "w", encoding="utf-8") as f:
            json.dump(memory_traces, f, ensure_ascii=False, indent=2)

        # 6. 执行自动化质检并保存报告
        qc_report = QCValidator.validate_sessions(rendered_sessions)
        out_qc_path = sample_dir / "qc_report.json"
        with open(out_qc_path, "w", encoding="utf-8") as f:
            json.dump(qc_report, f, ensure_ascii=False, indent=2)

        # 7. 统计耗时与调用花销
        usage = self.llm.get_usage()
        elapsed = time.time() - t0
        print(f"    [Cost & Tokens] Calls: {usage['calls']} | Tokens: {usage['total_tokens']} (In: {usage['total_prompt_tokens']}, Out: {usage['completion_tokens']}) | Cost: RMB {usage['cost_rmb']:.4f}")
        print(f"    [QC Report] Pass Rate: {qc_report['pass_rate']} ({qc_report['passed_sessions']}/{qc_report['total_sessions']})")
        if qc_report["issues"]:
            print(f"    [!] QC Warnings/Issues: {qc_report['issues']}")

        # 8. 记录检查点
        self.checkpoint["completed_personas"].append(pid)
        self._save_checkpoint()
        print(f"    [SUCCESS] {pid} finished in {elapsed:.1f}s -> {sample_dir}")
        return True

    def run_batch(self, start_idx: int = None, count: int = None, raw_persona_path: str = None):
        start_idx = start_idx if start_idx is not None else Config.default_start_idx
        count = count if count is not None else Config.default_count
        raw_path = Path(raw_persona_path or self.raw_persona_path)

        if not raw_path.exists():
            raise FileNotFoundError(f"Raw persona file not found at: {raw_path}")

        with open(raw_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            personas = data.get("personas", [])

        target_personas = personas[start_idx : start_idx + count]
        print(f"=======================================================")
        print(f"[*] Starting Batch Pipeline")
        print(f"    Total in Raw File: {len(personas)}")
        print(f"    Target Range: [{start_idx} : {start_idx + count}] ({len(target_personas)} personas)")
        print(f"    Model: {self.llm.model} | Base URL: {self.llm.base_url}")
        print(f"    Batch Size: {self.batch_size} sessions/call")
        print(f"    Output Directory: {self.output_dir.resolve()}")
        print(f"=======================================================")

        total_tokens = 0
        total_cost = 0.0

        for idx, p in enumerate(target_personas, start=start_idx + 1):
            try:
                self.process_single_persona(p)
                u = self.llm.get_usage()
                total_tokens += u["total_tokens"]
                total_cost += u["cost_rmb"]
            except Exception as e:
                print(f"[ERROR] Failed processing persona {p.get('persona_id')}: {e}")
                import traceback
                traceback.print_exc()

        print(f"\n=======================================================")
        print(f"=== Batch Finished! Processed {len(target_personas)} personas ===")
        print(f"=== Total Tokens: {total_tokens} | Total Cost: RMB {total_cost:.4f} ===")
        print(f"=======================================================\n")
