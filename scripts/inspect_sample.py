import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

def inspect_persona(persona_dir: str, start: int = 1, end: int = 25):
    with open(f"{persona_dir}/persona_skeleton.json", "r", encoding="utf-8") as f:
        skeleton = json.load(f)
    
    with open(f"{persona_dir}/sessions.jsonl", "r", encoding="utf-8") as f:
        sessions = [json.loads(l) for l in f]

    logger.info("=" * 60)
    logger.info(f"画像概览: {skeleton['persona_id']} - {skeleton['category']}")
    logger.info(f"职业身份: {skeleton['static_profile']['identity']}")
    logger.info(f"说话风格: {skeleton['static_profile']['speech_style']['tone']}")
    logger.info(f"口头禅: {', '.join(skeleton['static_profile']['speech_style']['catchphrases'])}")
    logger.info(f"总会话数: {len(sessions)}")
    logger.info("=" * 60)

    for i, s in enumerate(sessions):
        if not (start <= i + 1 <= end):
            continue
        meta = s["session_meta"]
        closure = s["intents"][0]["closure_path"] if s.get("intents") else "None"
        env = meta["scenario"].get("environment", "")
        logger.info(f"\n--- [Session {i+1:02d}] {s['session_id']} ({s['reference_time']}) ---")
        logger.info(f"模板: {meta['template_id']} | 角色: {meta['memory_role']} | 闭环: {closure} | 物理地点: {env} | 轮数: {meta['round_count']}")
        for ev in s["event_sequence"]:
            logger.info(f"  [Turn {ev['turn']}]")
            logger.info(f"    User : {ev['user']['utterance']}  (action: {ev['user']['action_types']})")
            logger.info(f"    Agent: {ev['agent']['utterance']} (action: {ev['agent']['action_types']})")
            if ev.get("requested_params"):
                logger.info(f"    -> requested_params: {ev['requested_params']}")

if __name__ == "__main__":
    p_dir = sys.argv[1] if len(sys.argv) > 1 else "data/cognitive_samples/mobile_persona_001"
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    end = int(sys.argv[3]) if len(sys.argv) > 3 else 25
    inspect_persona(p_dir, start, end)
