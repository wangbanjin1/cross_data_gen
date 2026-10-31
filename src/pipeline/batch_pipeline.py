from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging
from pathlib import Path
import threading
import time

from src.config.settings import Config
from src.core.experience_bank import ExperienceBank
from src.core.memory_tracker import MemoryTracker
from src.core.qc_validator import QCValidator
from src.core.timeline_planner import DynamicTimelinePlanner
from src.core.working_records_ledger import WorkingRecordsLedger
from src.generation.dialogue_generator import DialogueGenerator
from src.generation.llm_client import LLMClient
from src.generation.persona_generator import PersonaGenerator

logger = logging.getLogger(__name__)


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
        self.ckpt_lock = threading.Lock()
        self.checkpoint = self._load_checkpoint()
        self.model = model or Config.model
        self.base_url = base_url or Config.base_url
        self.llm = LLMClient(model=self.model, base_url=self.base_url)
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

    @staticmethod
    def _load_or_generate_skeleton(
        pid: str,
        raw_persona: dict,
        sample_dir: Path,
        force: bool,
        worker_persona_gen: PersonaGenerator,
    ) -> dict:
        persona_skeleton_path = sample_dir / "persona_skeleton.json"
        if persona_skeleton_path.exists() and not force:
            with open(persona_skeleton_path, "r", encoding="utf-8") as f:
                persona_skeleton = json.load(f)
            persona_skeleton = worker_persona_gen._enrich_skeleton(persona_skeleton)
            with open(persona_skeleton_path, "w", encoding="utf-8") as f:
                json.dump(persona_skeleton, f, ensure_ascii=False, indent=2)
            logger.info("    - [%s] Loaded & Enriched existing Persona Skeleton -> %s", pid, persona_skeleton_path.name)
            return persona_skeleton

        persona_skeleton = worker_persona_gen.generate_skeleton(raw_persona)
        with open(persona_skeleton_path, "w", encoding="utf-8") as f:
            json.dump(persona_skeleton, f, ensure_ascii=False, indent=2)
        logger.info("    - [%s] Generated Persona Skeleton via DeepSeek API -> %s", pid, persona_skeleton_path.name)
        return persona_skeleton

    @staticmethod
    def _persist_persona_outputs(
        sample_dir: Path,
        rendered_sessions: list[dict],
        working_ledger: WorkingRecordsLedger,
        experience_bank: ExperienceBank,
        memory_traces: list[dict],
    ) -> dict:
        out_sessions_path = sample_dir / "sessions.jsonl"
        with open(out_sessions_path, "w", encoding="utf-8") as f:
            for s in rendered_sessions:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")

        with open(sample_dir / "sessions.json", "w", encoding="utf-8") as f:
            json.dump(rendered_sessions, f, ensure_ascii=False, indent=2)

        working_ledger.save()
        with open(sample_dir / "working_records.json", "w", encoding="utf-8") as f:
            json.dump(working_ledger.get_all_records(), f, ensure_ascii=False, indent=2)
        logger.info(
            "    - Saved decoupled Working Records Ledger (%d records) -> working_records.jsonl",
            len(working_ledger.get_all_records()),
        )

        with open(sample_dir / "experience_bank.json", "w", encoding="utf-8") as f:
            json.dump(experience_bank.get_all_experiences(), f, ensure_ascii=False, indent=2)

        with open(sample_dir / "memory_traces.json", "w", encoding="utf-8") as f:
            json.dump(memory_traces, f, ensure_ascii=False, indent=2)

        qc_report = QCValidator.validate_sessions(rendered_sessions, memory_traces=memory_traces)
        with open(sample_dir / "qc_report.json", "w", encoding="utf-8") as f:
            json.dump(qc_report, f, ensure_ascii=False, indent=2)
        return qc_report

    def process_single_persona(self, raw_persona: dict, force: bool = False, llm: LLMClient = None) -> dict:
        pid = raw_persona.get("persona_id")
        worker_llm = llm or self.llm
        worker_persona_gen = PersonaGenerator(worker_llm) if llm else self.persona_gen
        worker_dialogue_gen = DialogueGenerator(worker_llm) if llm else self.dialogue_gen

        sample_dir = self.output_dir / pid
        sample_dir.mkdir(parents=True, exist_ok=True)
        if not force and pid in self.checkpoint["completed_personas"] and (sample_dir / "sessions.jsonl").exists():
            logger.info("[-] Persona %s already completed in %s, skipping.", pid, sample_dir)
            return {"calls": 0, "total_tokens": 0, "cost_rmb": 0.0}

        logger.info("[+] Processing Persona %s (%s) -> %s", pid, raw_persona.get("persona_summary"), sample_dir)
        t0 = time.time()
        worker_llm.reset_usage()
        persona_skeleton = self._load_or_generate_skeleton(pid, raw_persona, sample_dir, force, worker_persona_gen)

        ledger_path = sample_dir / "working_records.jsonl"
        if ledger_path.exists():
            ledger_path.unlink()
        working_ledger = WorkingRecordsLedger(user_id=pid, storage_path=ledger_path)
        experience_bank = ExperienceBank()
        active_llm = worker_llm if getattr(Config, "use_llm", True) else None
        timeline = DynamicTimelinePlanner.plan(
            persona_skeleton, llm=active_llm, working_ledger=working_ledger, experience_bank=experience_bank
        )
        logger.info("    - [%s] Planned %d sessions across timeline.", pid, len(timeline))

        memory_tracker = MemoryTracker()
        planned_items, memory_traces = [], []
        for s_plan in timeline:
            snap_before, mem_events, gold_after = memory_tracker.process_session(s_plan)
            planned_items.append((s_plan, snap_before, mem_events, gold_after))
            memory_traces.append(
                {
                    "session_id": s_plan["session_id"],
                    "reference_time": s_plan["reference_time"],
                    "memory_role": s_plan["memory_role"],
                    "blueprint_type": s_plan["blueprint_type"],
                    "snapshot_before": snap_before,
                    "memory_events": mem_events,
                    "gold_state_after": gold_after,
                }
            )

        logger.info("    - [%s] Batch rendering %d sessions with DeepSeek Flash...", pid, len(timeline))
        rendered_sessions = worker_dialogue_gen.generate_sessions_batch(
            planned_items, persona_skeleton, batch_size=self.batch_size
        )
        qc_report = self._persist_persona_outputs(
            sample_dir, rendered_sessions, working_ledger, experience_bank, memory_traces
        )
        usage = worker_llm.get_usage()
        logger.info(
            "    [%s Cost & QC] Calls: %d | Tokens: %d | Cost: RMB %.4f | Pass Rate: %s (%d/%d)",
            pid,
            usage["calls"],
            usage["total_tokens"],
            usage["cost_rmb"],
            qc_report["pass_rate"],
            qc_report["passed_sessions"],
            qc_report["total_sessions"],
        )
        if qc_report["issues"]:
            logger.warning("    [!] %s QC Warnings/Issues: %s", pid, qc_report["issues"])

        with self.ckpt_lock:
            if pid not in self.checkpoint["completed_personas"]:
                self.checkpoint["completed_personas"].append(pid)
                self.checkpoint["completed_personas"].sort()
            self._save_checkpoint()
        logger.info("    [SUCCESS] %s finished in %.1fs -> %s", pid, time.time() - t0, sample_dir)
        return usage

    def run_batch(self, start_idx: int = None, count: int = None, raw_persona_path: str = None, force: bool = False, workers: int = 1):
        start_idx = start_idx if start_idx is not None else Config.default_start_idx
        count = count if count is not None else Config.default_count
        raw_path = Path(raw_persona_path or self.raw_persona_path)

        if not raw_path.exists():
            raise FileNotFoundError(f"Raw persona file not found at: {raw_path}")

        with open(raw_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            personas = data.get("personas", [])

        target_personas = personas[start_idx : start_idx + count]
        logger.info("=======================================================")
        logger.info("[*] Starting Batch Pipeline")
        logger.info("    Total in Raw File: %d", len(personas))
        logger.info("    Target Range: [%d : %d] (%d personas)", start_idx, start_idx + count, len(target_personas))
        logger.info("    Model: %s | Base URL: %s", self.llm.model, self.llm.base_url)
        logger.info("    Batch Size: %d sessions/call | Workers: %d", self.batch_size, workers)
        logger.info("    Output Directory: %s", self.output_dir.resolve())
        logger.info("=======================================================")

        total_calls, total_tokens, total_cost = 0, 0, 0.0
        if workers > 1:
            def _worker(p_item):
                w_llm = LLMClient(model=self.model, base_url=self.base_url)
                return self.process_single_persona(p_item, force=force, llm=w_llm)

            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(_worker, p): p for p in target_personas}
                for fut in as_completed(futures):
                    p = futures[fut]
                    try:
                        u = fut.result()
                        total_calls += u.get("calls", 0)
                        total_tokens += u.get("total_tokens", 0)
                        total_cost += u.get("cost_rmb", 0.0)
                    except Exception:
                        logger.exception("[ERROR] Failed processing persona %s", p.get("persona_id"))
        else:
            for p in target_personas:
                try:
                    u = self.process_single_persona(p, force=force)
                    total_calls += u.get("calls", 0)
                    total_tokens += u.get("total_tokens", 0)
                    total_cost += u.get("cost_rmb", 0.0)
                except Exception:
                    logger.exception("[ERROR] Failed processing persona %s", p.get("persona_id"))

        logger.info("=======================================================")
        logger.info("=== Batch Finished! Processed %d personas ===", len(target_personas))
        logger.info(
            "=== Total API Calls: %d | Total Tokens: %d | Total Cost: RMB %.4f ===",
            total_calls,
            total_tokens,
            total_cost,
        )
        logger.info("=======================================================")
