import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

import sys
import json
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

def inspect_session(filepath):
    logger.info(f"=== Inspecting {filepath} ===")
    with open(filepath, 'r', encoding='utf-8') as f:
        line = f.readline()
        if not line:
            logger.info("Empty file")
            return
        data = json.loads(line)
        logger.info("Session ID:", data.get("session_id"))
        logger.info("User ID:", data.get("user_id"))
        logger.info("Reference Time:", data.get("reference_time"))
        logger.info("Meta:", data.get("session_meta"))
        logger.info("Conversation:")
        for ev in data.get("event_sequence", []):
            turn = ev.get("turn")
            u = ev.get("user", {}).get("utterance")
            a = ev.get("agent", {}).get("utterance")
            u_act = ev.get("user", {}).get("action_types")
            a_act = ev.get("agent", {}).get("action_types")
            logger.info(f"  [Turn {turn}]")
            logger.info(f"    User ({u_act}): {u}")
            logger.info(f"    Agent ({a_act}): {a}")

inspect_session('data/ref_template/pilot100_0813/rendered/sessions.T2-1.jsonl')
inspect_session('data/ref_template/pilot100_0813/rendered/sessions.T2-4.jsonl')
inspect_session('data/ref_template/pilot100_0813/rendered/sessions.X-1.jsonl')
