import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

import json
import glob
import os
import re
from datetime import datetime
import sys
sys.path.insert(0, ".")
from src.core.qc_validator import QCValidator

def parse_date_from_ref(ref_time_str):
    m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', ref_time_str or "")
    if m:
        y, month, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        dt = datetime(y, month, d)
        return dt, dt.weekday()
    return None, None

def fix_all_generated_data():
    persona_dirs = sorted(glob.glob("data/generated/mobile_persona_*"))
    logger.info(f"Total persona dirs found: {len(persona_dirs)}")

    stats = {
        "x1_fixed": 0,
        "t21_s03_fixed": 0,
        "t25_half_day_fixed": 0,
        "u2_missing_dur_fixed": 0,
        "qc_passed_personas": 0,
    }

    for p_dir in persona_dirs:
        p_id = os.path.basename(p_dir)
        sess_file = os.path.join(p_dir, "sessions.json")
        sessl_file = os.path.join(p_dir, "sessions.jsonl")
        trace_file = os.path.join(p_dir, "memory_traces.json")
        qc_file = os.path.join(p_dir, "qc_report.json")

        if not os.path.exists(sess_file):
            continue

        with open(sess_file, "r", encoding="utf-8") as f:
            sessions = json.load(f)

        modified = False

        for s_idx, s in enumerate(sessions):
            meta = s.get("session_meta", {})
            tid = meta.get("template_id")
            role = meta.get("memory_role")
            ref_time = s.get("reference_time", "")
            dt, weekday = parse_date_from_ref(ref_time)
            evs = s.get("event_sequence", [])

            # 1. 修复 X-1 工作日说"周末"
            if tid == "X-1" and weekday is not None and weekday < 5:
                # 检查并替换环境
                scenario = meta.get("scenario", {})
                if scenario.get("environment") == "周末午休个人时间":
                    scenario["environment"] = "工作日午休个人时间"
                    modified = True

                for ev in evs:
                    u = ev.get("user", {})
                    a = ev.get("agent", {})
                    u_utt = u.get("utterance", "")
                    a_utt = a.get("utterance", "")

                    if "周末" in u_utt:
                        # 替换周末午休 -> 今天午休，或 周末 -> 今天中午
                        new_u = u_utt.replace("周末午休", "今天午休").replace("周末", "今天中午")
                        u["utterance"] = new_u
                        modified = True
                        stats["x1_fixed"] += 1

                    if "周末" in a_utt:
                        new_a = a_utt.replace("周末午休", "今天午休").replace("周末", "今天中午")
                        a["utterance"] = new_a
                        modified = True

            # 2. 修复 S-03 隐式强化缺失业务名锚点
            if s_idx == 2 and role == "reinforcement_session":
                intents = s.get("intents", []) or s.get("event_sequence", [{}])[-1].get("turn_intents", [])
                srv_name = ""
                if intents:
                    srv_name = intents[0].get("params", {}).get("service_name", {}).get("value", "")
                
                if srv_name and evs:
                    ev0 = evs[0]
                    u = ev0.get("user", {})
                    u_utt = u.get("utterance", "")
                    if ("按上次" in u_utt or "跟上次" in u_utt) and (srv_name not in u_utt):
                        # 在"这次"后面或开头加上业务名
                        if "这次" in u_utt:
                            new_u = u_utt.replace("这次", f"这次{srv_name}")
                        elif "，" in u_utt:
                            parts = u_utt.split("，", 1)
                            new_u = f"{parts[0]}，{srv_name}{parts[1]}"
                        else:
                            new_u = f"{srv_name}{u_utt}"
                        u["utterance"] = new_u
                        modified = True
                        stats["t21_s03_fixed"] += 1

            # 3. 修复 T2-5 "一整个半天" -> "3个小时"
            if tid == "T2-5":
                for ev in evs:
                    u = ev.get("user", {})
                    u_utt = u.get("utterance", "")
                    if "一整个半天" in u_utt or "半天" in u_utt:
                        new_u = u_utt.replace("一整个半天", "3个小时").replace("半天", "3个小时")
                        u["utterance"] = new_u
                        modified = True
                        stats["t25_half_day_fixed"] += 1

            # 4. 修复 U2 漏说 duration (GT 标了 source_ref: U2)
            if len(evs) >= 2 and evs[1].get("turn") == 2:
                ev2 = evs[1]
                u2 = ev2.get("user", {})
                u2_utt = u2.get("utterance", "")
                t_intents = ev2.get("turn_intents", [])
                for tint in t_intents:
                    ts = tint.get("params", {}).get("timestamp", {})
                    dur_obj = ts.get("duration", {}) if isinstance(ts, dict) else {}
                    if dur_obj.get("source_ref") == "U2":
                        dur_val = dur_obj.get("value", "")
                        has_time_kw = bool(re.search(r'(\d+|两|俩|半)(分钟|min|小时|分)|持续|到\s*\d+|至\s*\d+', u2_utt))
                        if not has_time_kw and dur_val:
                            # 补入持续时长描述，例如 "，持续60分钟"
                            m_num = re.search(r'(\d+)', dur_val)
                            dur_text = f"持续{m_num.group(1)}分钟" if m_num else f"持续{dur_val}"
                            # 插入到句中
                            if "。" in u2_utt:
                                parts = u2_utt.split("。", 1)
                                new_u2 = f"{parts[0]}，{dur_text}。{parts[1]}"
                            elif "，" in u2_utt:
                                parts = u2_utt.split("，", 1)
                                new_u2 = f"{parts[0]}，{dur_text}，{parts[1]}"
                            else:
                                new_u2 = f"{u2_utt}，{dur_text}"
                            u2["utterance"] = new_u2
                            modified = True
                            stats["u2_missing_dur_fixed"] += 1

        # 保存写回
        if modified:
            with open(sess_file, "w", encoding="utf-8") as f:
                json.dump(sessions, f, ensure_ascii=False, indent=2)

            with open(sessl_file, "w", encoding="utf-8") as f:
                for s in sessions:
                    f.write(json.dumps(s, ensure_ascii=False) + "\n")

            # 运行质检并更新 qc_report
            mem_traces = None
            if os.path.exists(trace_file):
                with open(trace_file, "r", encoding="utf-8") as f:
                    mem_traces = json.load(f)
            qc_rep = QCValidator.validate_sessions(sessions, memory_traces=mem_traces)
            with open(qc_file, "w", encoding="utf-8") as f:
                json.dump(qc_rep, f, ensure_ascii=False, indent=2)
            if qc_rep.get("failed_sessions", 0) == 0:
                stats["qc_passed_personas"] += 1
        else:
            stats["qc_passed_personas"] += 1

    logger.info("\n================== 修复完成统计 ==================")
    logger.info(f"X-1 '工作日说周末' 修复数量: {stats['x1_fixed']}")
    logger.info(f"S-03 隐式偏好业务锚点补充数量: {stats['t21_s03_fixed']}")
    logger.info(f"T2-5 '半天' 歧义口语修复数量: {stats['t25_half_day_fixed']}")
    logger.info(f"U2 漏说时长补全数量: {stats['u2_missing_dur_fixed']}")
    logger.info(f"质检全通过 Persona 数量: {stats['qc_passed_personas']}/{len(persona_dirs)}")

if __name__ == "__main__":
    fix_all_generated_data()
