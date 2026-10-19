# -*- coding: utf-8 -*-
"""
批量刷新 cognitive_samples 中的 experience_branching (包含完整 4 轮 slow path 交互树与仲裁门)
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.generation.session_assembler import SessionAssembler

exp_map = {
    'EXP_MULTI_INTENT_PARTITION_01': 'multi_intent_partition',
    'EXP_PREWARM_BUFFER_01': 'prewarm_buffer',
    'EXP_CALENDAR_HOLIDAY_EXCEPTION_01': 'holiday_exception',
    'EXP_ORDER_QUALITY_DISAMBIGUATION_01': 'quality_disambiguation',
    'EXP_OVERLAPPING_ORDER_RESOLUTION_01': 'overlapping_resolution'
}

def refresh():
    base = Path('data/cognitive_samples')
    updated_count = 0
    for p_dir in sorted(base.glob('mobile_persona_*')):
        s_jsonl = p_dir / 'sessions.jsonl'
        s_json = p_dir / 'sessions.json'
        if not s_jsonl.exists():
            continue
        
        with open(s_jsonl, 'r', encoding='utf-8') as f:
            sessions = [json.loads(line) for line in f if line.strip()]
            
        for s in sessions:
            eb = s.get('experience_branching') or s.get('session_meta', {}).get('experience_branching')
            if not eb:
                continue
            
            exp_id = eb.get('experience_id')
            scenario_type = exp_map.get(exp_id)
            if not scenario_type:
                continue
            
            rule_title = eb.get('rule_title')
            learning_source_session = eb.get('learning_source_session')
            events = s.get('event_sequence', [])
            user_prompt = events[0]['user']['utterance'] if events and 'user' in events[0] else ''
            
            intents = s.get('intents', [])
            I1_params = intents[0].get('params', {}) if intents else {}
            ts1 = I1_params.get('timestamp', {})
            
            ctx = {
                'app': I1_params.get('application_name', {}).get('value', ''),
                'srv': I1_params.get('service_name', {}).get('value', ''),
                'res': I1_params.get('resolution', {}).get('min_value', {}).get('value', '1080p'),
                'rtt': I1_params.get('rtt', {}).get('max_value', {}).get('value', '50ms'),
                'start': ts1.get('start_timestamp', {}).get('value', ''),
                'end': ts1.get('end_timestamp', {}).get('value', ''),
                'dur': ts1.get('duration', {}).get('value', '')
            }
            if len(intents) >= 2:
                I2_params = intents[1].get('params', {})
                ts2 = I2_params.get('timestamp', {})
                ctx.update({
                    'app2': I2_params.get('application_name', {}).get('value', ''),
                    'srv2': I2_params.get('service_name', {}).get('value', ''),
                    'res2': I2_params.get('resolution', {}).get('min_value', {}).get('value', '1080p'),
                    'rtt2': I2_params.get('rtt', {}).get('max_value', {}).get('value', '50ms'),
                    'start2': ts2.get('start_timestamp', {}).get('value', ''),
                    'end2': ts2.get('end_timestamp', {}).get('value', ''),
                    'dur2': ts2.get('duration', {}).get('value', '')
                })
                
            new_eb = SessionAssembler._build_experience_branching(
                scenario_type=scenario_type,
                exp_id=exp_id,
                rule_title=rule_title,
                learning_source_session=learning_source_session,
                user_prompt=user_prompt,
                ctx=ctx
            )
            s['experience_branching'] = new_eb
            s['session_meta']['experience_branching'] = new_eb
            updated_count += 1
            print(f"Updated {p_dir.name} | {s['session_id']} | {exp_id} | tree_turns={len(new_eb['slow_path']['simulator_dialogue_tree'])}")

        # 保存更新后的 sessions.jsonl 与 sessions.json
        with open(s_jsonl, 'w', encoding='utf-8') as f:
            for s in sessions:
                f.write(json.dumps(s, ensure_ascii=False) + '\n')
        with open(s_json, 'w', encoding='utf-8') as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)

    print(f"\n[SUCCESS] Total updated experience test sessions: {updated_count}")

if __name__ == '__main__':
    refresh()
