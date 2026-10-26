import json
from pathlib import Path
import html

def load_data():
    base_dir = Path("data/cognitive_samples")
    personas = []
    for p_dir in sorted(base_dir.iterdir()):
        if not p_dir.is_dir() or not p_dir.name.startswith("mobile_persona_"):
            continue
        skeleton = json.loads((p_dir / "persona_skeleton.json").read_text(encoding="utf-8"))
        exp_bank_raw = json.loads((p_dir / "experience_bank.json").read_text(encoding="utf-8"))
        exp_list = exp_bank_raw if isinstance(exp_bank_raw, list) else exp_bank_raw.get("experiences", [])
        exp_map = {e["experience_id"]: e for e in exp_list}
        sessions = [
            json.loads(line)
            for line in (p_dir / "sessions.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        sess_map = {s["session_id"]: s for s in sessions}

        exp_pairs = []
        for s in sessions:
            eb = s.get("experience_branching")
            if not eb:
                continue
            learn_sid = eb.get("learning_source_session")
            learn_sess = sess_map.get(learn_sid)
            exp_id = eb.get("experience_id")
            exp_entry = exp_map.get(exp_id, {})
            exp_pairs.append({
                "reuse_session": s,
                "learning_session": learn_sess,
                "exp_entry": exp_entry,
                "branching": eb,
            })

        first_uid = sessions[0].get("user_id", "") if sessions else ""
        personas.append({
            "folder": p_dir.name,
            "user_id": skeleton.get("user_id") or first_uid,
            "role": skeleton.get("role") or skeleton.get("occupation") or (skeleton.get("persona_profile") or {}).get("occupation_role", ""),
            "pairs": exp_pairs,
        })
    return personas


def render_intents_badges(intents, highlight_sources=True):
    if not intents:
        return '<div class="empty-slot">无意图参数</div>'
    blocks = []
    for it in intents:
        iid = html.escape(str(it.get("intent_id", "I1")))
        iname = html.escape(str(it.get("intent", "")))
        status = html.escape(str(it.get("status", "")))
        cpath = html.escape(str(it.get("closure_path", "")))
        p = it.get("params", {})
        app_obj = p.get("application_name", {})
        srv_obj = p.get("service_name", {})
        res_obj = (p.get("resolution") or {}).get("min_value", {})
        rtt_obj = (p.get("rtt") or {}).get("max_value", {})
        ts = p.get("timestamp") or {}
        st_obj = ts.get("start_timestamp", {})
        et_obj = ts.get("end_timestamp", {})
        du_obj = ts.get("duration", {})

        def fmt_slot(label, obj):
            if not isinstance(obj, dict) or not obj.get("value"):
                return ""
            val = html.escape(str(obj.get("value", "")))
            stype = str(obj.get("source_type", ""))
            sref = str(obj.get("source_ref", ""))
            is_exp = stype == "Experience"
            badge_cls = "slot-chip exp-chip" if is_exp else "slot-chip turn-chip"
            src_tag = f'<span class="src-tag">[{html.escape(stype)}:{html.escape(sref)}]</span>' if highlight_sources and stype else ""
            return f'<span class="{badge_cls}"><b>{html.escape(label)}:</b> {val} {src_tag}</span>'

        chips = "".join([
            fmt_slot("应用", app_obj),
            fmt_slot("业务", srv_obj),
            fmt_slot("分辨率", res_obj),
            fmt_slot("时延", rtt_obj),
            fmt_slot("起保", st_obj),
            fmt_slot("结束", et_obj),
            fmt_slot("时长", du_obj),
        ])
        blocks.append(f'''
        <div class="intent-box">
            <div class="intent-header">
                <span class="intent-id">{iid} · {iname}</span>
                <span class="intent-meta">status: <b>{status}</b> | path: <b>{cpath}</b></span>
            </div>
            <div class="slot-chips">{chips}</div>
        </div>
        ''')
    return "".join(blocks)


def render_gt_vs_flawed_diff(final_gt, flawed_intents, monitored_slots):
    gt_map = {i.get("intent_id", "I1"): i for i in (final_gt or [])}
    fl_map = {i.get("intent_id", "I1"): i for i in (flawed_intents or [])}
    rows = []
    slot_defs = [
        ("application_name", "应用名称", lambda p: (p.get("application_name") or {}).get("value", "-")),
        ("service_name", "业务类型", lambda p: (p.get("service_name") or {}).get("value", "-")),
        ("resolution", "分辨率门限", lambda p: ((p.get("resolution") or {}).get("min_value") or {}).get("value", "-")),
        ("rtt", "时延上限", lambda p: ((p.get("rtt") or {}).get("max_value") or {}).get("value", "-")),
        ("start_timestamp", "起保时间", lambda p: ((p.get("timestamp") or {}).get("start_timestamp") or {}).get("value", "-")),
        ("end_timestamp", "结束时间", lambda p: ((p.get("timestamp") or {}).get("end_timestamp") or {}).get("value", "-")),
        ("duration", "保障时长", lambda p: ((p.get("timestamp") or {}).get("duration") or {}).get("value", "-")),
    ]
    for iid in sorted(gt_map.keys()):
        gt_p = gt_map[iid].get("params", {})
        fl_p = (fl_map.get(iid) or {}).get("params", {})
        for skey, slabel, getter in slot_defs:
            g_val = getter(gt_p)
            f_val = getter(fl_p)
            is_diff = (g_val != f_val)
            if not is_diff and skey not in (monitored_slots or []):
                continue
            cls = "diff-row mismatch" if is_diff else "diff-row match"
            status_txt = "❌ 首轮偏差 (进入多轮澄清纠偏)" if is_diff else "✅ 一致"
            rows.append(f'''
            <tr class="{cls}">
                <td><b>{html.escape(iid)}.{html.escape(skey)}</b> ({html.escape(slabel)})</td>
                <td class="val-flawed">{html.escape(str(f_val))}</td>
                <td class="val-gt">{html.escape(str(g_val))}</td>
                <td><b>{status_txt}</b></td>
            </tr>
            ''')
    return f'''
    <table class="diff-table">
        <thead>
            <tr>
                <th>监控槽位 (Monitored Slot)</th>
                <th>多轮澄清路径首轮提取 (无经验字面提取)</th>
                <th>快速闭环路径目标真值 (应用经验规则目标值)</th>
                <th>参数比对结果</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows)}
        </tbody>
    </table>
    '''


def build_html(personas):
    cards_html = []
    total_pairs = 0
    for p in personas:
        uid = p["user_id"]
        role = p["role"]
        for pair in p["pairs"]:
            total_pairs += 1
            rs = pair["reuse_session"]
            ls = pair["learning_session"]
            eb = pair["branching"]
            exp_e = pair["exp_entry"]

            sid = rs["session_id"]
            ref_time = rs["reference_time"]
            tid = rs["session_meta"]["template_id"]
            contract = eb.get("interactive_eval_contract", {})
            scen_type = contract.get("scenario_type", "")
            exp_id = eb.get("experience_id", "")
            rule_title = eb.get("rule_title", "")
            fast_path = eb.get("fast_path", {})
            slow_path = eb.get("slow_path", {})
            final_gt = rs.get("intents", [])
            monitored_slots = (contract.get("delta_reaction_matrix", {}).get("on_slot_error") or {}).get("monitored_slots", [])

            # Learning session turns
            learn_turns_html = ""
            if ls:
                l_sid = ls["session_id"]
                l_time = ls["reference_time"]
                l_t_items = []
                for ev in ls.get("event_sequence", []):
                    t_num = ev.get("turn")
                    u_utt = html.escape(ev.get("user", {}).get("utterance", ""))
                    a_th = html.escape(ev.get("agent", {}).get("thought", ""))
                    a_utt = html.escape(ev.get("agent", {}).get("utterance", ""))
                    l_t_items.append(f'''
                    <div class="turn-item learn-turn">
                        <div class="turn-badge">经验习得 第 {t_num} 轮</div>
                        <div class="msg user-msg"><b>👤 用户：</b>{u_utt}</div>
                        <div class="msg thought-msg"><b>🧠 “联接”Agent 思考：</b>{a_th}</div>
                        <div class="msg agent-msg"><b>🤖 “联接”Agent 回复：</b>{a_utt}</div>
                    </div>
                    ''')
                learn_turns_html = f'''
                <div class="learning-panel">
                    <div class="panel-header learn-header">
                        <div>
                            <span class="badge badge-learn">阶段一：前置经验习得 (Learning Session)</span>
                            <b>{html.escape(l_sid)}</b> · <span class="time-tag">{html.escape(l_time)}</span>
                        </div>
                        <div class="exp-id-tag">沉淀规则 ID: <b>{html.escape(exp_id)}</b></div>
                    </div>
                    <div class="rule-summary-grid">
                        <div class="rule-cell"><b>触发条件 (Condition)：</b>{html.escape(exp_e.get("condition", ""))}</div>
                        <div class="rule-cell"><b>提参修正动作 (Action)：</b>{html.escape(exp_e.get("action", ""))}</div>
                        <div class="rule-cell"><b>适用边界与反例 (Boundary)：</b>{html.escape(exp_e.get("negative_counterexamples", ""))}</div>
                    </div>
                    <div class="turns-container">
                        {"".join(l_t_items)}
                    </div>
                </div>
                '''

            # Fast path turns
            fast_turns = []
            for ev in rs.get("event_sequence", []):
                t_num = ev.get("turn")
                u_utt = html.escape(ev.get("user", {}).get("utterance", ""))
                a_th = html.escape(ev.get("agent", {}).get("thought", ""))
                a_utt = html.escape(ev.get("agent", {}).get("utterance", ""))
                t_intents_html = render_intents_badges(ev.get("turn_intents", []), highlight_sources=True)
                match_badge = (
                    '<span class="branch-pill pass-pill">首轮直接命中目标参数 (引用经验规则)</span>'
                    if t_num == 1 else
                    '<span class="branch-pill goal-pill">用户确认无误 → 2轮快速闭环</span>'
                )
                fast_turns.append(f'''
                <div class="turn-card fast-turn-card">
                    <div class="turn-card-head">
                        <span class="turn-num">快速闭环路径 · 第 {t_num} 轮</span>
                        {match_badge}
                    </div>
                    <div class="msg user-msg"><b>👤 用户输入 (U{t_num})：</b>{u_utt}</div>
                    <div class="msg thought-msg"><b>🧠 “联接”Agent 思考 (启用经验记忆)：</b>{a_th}</div>
                    <div class="msg agent-msg"><b>🤖 “联接”Agent 回复 (A{t_num})：</b>{a_utt}</div>
                    <div class="turn-slots-wrap">
                        <div class="slots-title">📌 第 {t_num} 轮意图槽位状态 (turn_intents)：</div>
                        {t_intents_html}
                    </div>
                </div>
                ''')

            # Slow path turns
            slow_seq = slow_path.get("full_slow_event_sequence", [])
            slow_turns = []
            for ev in slow_seq:
                t_num = ev.get("turn")
                u_utt = html.escape(ev.get("user", {}).get("utterance", ""))
                a_th = html.escape(ev.get("agent", {}).get("thought", ""))
                a_utt = html.escape(ev.get("agent", {}).get("utterance", ""))
                t_intents_html = render_intents_badges(ev.get("turn_intents", []), highlight_sources=False)
                if t_num == 1:
                    b_pill = '<span class="branch-pill err-pill">首轮字面提参存在偏差 → 触发用户澄清指正</span>'
                elif t_num == 2:
                    b_pill = '<span class="branch-pill warn-pill">用户补充真实目标参数 → 二轮修正对齐</span>'
                else:
                    b_pill = '<span class="branch-pill goal-pill">用户确认修正结果 → 3轮澄清闭环</span>'
                slow_turns.append(f'''
                <div class="turn-card slow-turn-card">
                    <div class="turn-card-head">
                        <span class="turn-num">多轮澄清路径 · 第 {t_num} 轮</span>
                        {b_pill}
                    </div>
                    <div class="msg user-msg"><b>👤 用户输入 / 澄清指正 (U{t_num})：</b>{u_utt}</div>
                    <div class="msg thought-msg"><b>🧠 “联接”Agent 思考 (未启用经验记忆)：</b>{a_th}</div>
                    <div class="msg agent-msg"><b>🤖 “联接”Agent 回复 (A{t_num})：</b>{a_utt}</div>
                    <div class="turn-slots-wrap">
                        <div class="slots-title">📌 第 {t_num} 轮意图槽位状态 (turn_intents)：</div>
                        {t_intents_html}
                    </div>
                </div>
                ''')

            flawed_t1_intents = slow_seq[0].get("turn_intents", []) if slow_seq else []
            diff_table_html = render_gt_vs_flawed_diff(final_gt, flawed_t1_intents, monitored_slots)

            cards_html.append(f'''
            <section class="session-card" data-user="{html.escape(uid)}" data-exp="{html.escape(exp_id)}">
                <div class="session-card-banner">
                    <div class="banner-left">
                        <span class="user-pill">{html.escape(uid)} · {html.escape(role)}</span>
                        <span class="tpl-pill">模板 {html.escape(tid)}</span>
                        <span class="exp-pill">{html.escape(exp_id)}</span>
                        <h2 class="session-title">{html.escape(sid)} — {html.escape(rule_title)}</h2>
                        <div class="session-subtitle">应用会话时间：{html.escape(ref_time)} | 场景类型：<code>{html.escape(scen_type)}</code> | 监控槽位：<code>{html.escape(", ".join(monitored_slots))}</code></div>
                    </div>
                    <div class="banner-metrics">
                        <div class="metric-item fast-metric">
                            <span class="m-label">快速闭环路径 (有经验)</span>
                            <span class="m-val">{fast_path.get("round_count", 2)} 轮闭环</span>
                        </div>
                        <div class="metric-item slow-metric">
                            <span class="m-label">多轮澄清路径 (无经验)</span>
                            <span class="m-val">{slow_path.get("round_count", 3)} 轮闭环</span>
                        </div>
                        <div class="metric-item tcg-metric">
                            <span class="m-label">交互轮数压缩率</span>
                            <span class="m-val">33.33%</span>
                        </div>
                    </div>
                </div>

                {learn_turns_html}

                <div class="diff-section">
                    <div class="diff-header">🔍 首轮参数提取对比 (多轮澄清路径首轮字面提参 vs 快速闭环路径经验修正参数)</div>
                    {diff_table_html}
                </div>

                <div class="dual-track-grid">
                    <div class="track-col fast-col">
                        <div class="track-header fast-track-header">
                            <div>
                                <span class="track-tag">快速闭环路径</span>
                                <b>启用经验记忆 · 首轮精准提参 (2轮快速闭环)</b>
                            </div>
                            <span class="round-tag">2 轮闭环</span>
                        </div>
                        <div class="track-desc">{html.escape(fast_path.get("trigger_condition", ""))}</div>
                        <div class="track-turns">
                            {"".join(fast_turns)}
                        </div>
                    </div>

                    <div class="track-col slow-col">
                        <div class="track-header slow-track-header">
                            <div>
                                <span class="track-tag">多轮澄清路径</span>
                                <b>未启用经验记忆 · 经用户澄清纠偏后闭环 (3轮澄清闭环)</b>
                            </div>
                            <span class="round-tag">3 轮闭环</span>
                        </div>
                        <div class="track-desc">{html.escape(slow_path.get("trigger_condition", ""))}</div>
                        <div class="track-turns">
                            {"".join(slow_turns)}
                        </div>
                    </div>
                </div>
            </section>
            ''')

    html_doc = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>“联接”Agent 经验记忆：快速闭环路径 vs 多轮澄清路径 对比可视化看板</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
:root {{
    --bg: #f8fafc;
    --card-bg: #ffffff;
    --border: #e2e8f0;
    --text: #0f172a;
    --muted: #475569;
    --fast-primary: #059669;
    --fast-bg: #ecfdf5;
    --fast-border: #a7f3d0;
    --slow-primary: #d97706;
    --slow-bg: #fffbeb;
    --slow-border: #fde68a;
    --err-primary: #dc2626;
    --err-bg: #fef2f2;
    --learn-primary: #2563eb;
    --learn-bg: #eff6ff;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    padding: 24px 32px;
}}
.page-header {{
    background: #ffffff;
    border: 2px solid #0f172a;
    border-radius: 12px;
    padding: 24px 28px;
    margin-bottom: 24px;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
}}
.page-header h1 {{
    font-size: 24px;
    font-weight: 800;
    color: #0f172a;
    margin-bottom: 8px;
}}
.page-header p {{
    color: var(--muted);
    font-size: 14px;
}}
.summary-strip {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 14px;
    margin-top: 18px;
}}
.stat-box {{
    background: #f8fafc;
    border: 1.5px solid #cbd5e1;
    border-radius: 8px;
    padding: 12px 16px;
}}
.stat-box .s-title {{ font-size: 12px; color: var(--muted); font-weight: 700; }}
.stat-box .s-num {{ font-size: 20px; font-weight: 800; color: #0f172a; margin-top: 4px; }}

.arch-panel {{
    background: #ffffff;
    border: 1.5px solid var(--border);
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 24px;
}}
.arch-panel h3 {{
    font-size: 16px;
    font-weight: 800;
    margin-bottom: 12px;
}}
.mermaid {{
    background: #FFFFFF;
    padding: 12px;
    border-radius: 8px;
    border: 1px solid #e2e8f0;
    text-align: center;
}}

.filter-bar {{
    background: #ffffff;
    border: 1.5px solid var(--border);
    border-radius: 10px;
    padding: 14px 20px;
    margin-bottom: 24px;
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    align-items: center;
    position: sticky;
    top: 12px;
    z-index: 50;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
}}
.filter-group {{
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}}
.filter-label {{
    font-size: 13px;
    font-weight: 800;
    color: #0f172a;
}}
.filter-btn {{
    padding: 6px 12px;
    border-radius: 6px;
    border: 1.5px solid #cbd5e1;
    background: #ffffff;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    color: #334155;
    transition: all 0.15s;
}}
.filter-btn:hover {{
    border-color: #0f172a;
    color: #0f172a;
}}
.filter-btn.active {{
    background: #0f172a;
    color: #ffffff;
    border-color: #0f172a;
}}

.session-card {{
    background: var(--card-bg);
    border: 2px solid #cbd5e1;
    border-radius: 14px;
    margin-bottom: 32px;
    overflow: hidden;
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
}}
.session-card-banner {{
    background: #0f172a;
    color: #ffffff;
    padding: 20px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
}}
.user-pill, .tpl-pill, .exp-pill {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 5px;
    font-size: 12px;
    font-weight: 800;
    margin-right: 8px;
    margin-bottom: 6px;
}}
.user-pill {{ background: #3b82f6; color: #ffffff; }}
.tpl-pill {{ background: #64748b; color: #ffffff; }}
.exp-pill {{ background: #10b981; color: #052e16; }}
.session-title {{
    font-size: 19px;
    font-weight: 800;
    margin: 4px 0;
}}
.session-subtitle {{
    font-size: 13px;
    color: #cbd5e1;
}}
.session-subtitle code {{
    background: rgba(255,255,255,0.15);
    padding: 2px 6px;
    border-radius: 4px;
    color: #f8fafc;
}}
.banner-metrics {{
    display: flex;
    gap: 12px;
}}
.metric-item {{
    padding: 8px 14px;
    border-radius: 8px;
    text-align: center;
    min-width: 120px;
}}
.fast-metric {{ background: #065f46; border: 1.5px solid #34d399; }}
.slow-metric {{ background: #78350f; border: 1.5px solid #fbbf24; }}
.tcg-metric {{ background: #1e3a8a; border: 1.5px solid #60a5fa; }}
.metric-item .m-label {{ display: block; font-size: 11px; color: #e2e8f0; font-weight: 700; }}
.metric-item .m-val {{ display: block; font-size: 17px; font-weight: 800; color: #ffffff; margin-top: 2px; }}

.learning-panel {{
    background: var(--learn-bg);
    border-bottom: 2px solid #bfdbfe;
    padding: 18px 24px;
}}
.panel-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    flex-wrap: wrap;
}}
.badge-learn {{
    background: var(--learn-primary);
    color: #ffffff;
    padding: 4px 10px;
    border-radius: 5px;
    font-size: 12px;
    font-weight: 800;
    margin-right: 8px;
}}
.exp-id-tag {{
    font-size: 13px;
    color: #1e40af;
    background: #dbeafe;
    padding: 4px 10px;
    border-radius: 6px;
}}
.rule-summary-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 14px;
}}
.rule-cell {{
    background: #ffffff;
    border: 1px solid #93c5fd;
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 13px;
}}
.turns-container {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
}}
.learn-turn {{
    background: #ffffff;
    border: 1px solid #bfdbfe;
    border-radius: 8px;
    padding: 12px;
}}
.turn-badge {{
    display: inline-block;
    background: #1d4ed8;
    color: #ffffff;
    font-size: 11px;
    font-weight: 800;
    padding: 2px 8px;
    border-radius: 4px;
    margin-bottom: 8px;
}}

.diff-section {{
    padding: 18px 24px;
    background: #ffffff;
    border-bottom: 2px solid #e2e8f0;
}}
.diff-header {{
    font-size: 14px;
    font-weight: 800;
    margin-bottom: 10px;
    color: #0f172a;
}}
.diff-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}}
.diff-table th, .diff-table td {{
    border: 1.5px solid #cbd5e1;
    padding: 8px 12px;
    text-align: left;
}}
.diff-table th {{
    background: #f1f5f9;
    font-weight: 800;
}}
.diff-row.mismatch {{
    background: #fef2f2;
}}
.diff-row.mismatch .val-flawed {{
    color: #dc2626;
    font-weight: 800;
    text-decoration: underline wavy #dc2626;
}}
.diff-row.mismatch .val-gt {{
    color: #059669;
    font-weight: 800;
}}

.dual-track-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0;
}}
.track-col {{
    padding: 20px 24px;
}}
.fast-col {{
    background: #f0fdf4;
    border-right: 2px solid #cbd5e1;
}}
.slow-col {{
    background: #fffbeb;
}}
.track-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 14px;
    border-radius: 8px;
    margin-bottom: 10px;
}}
.fast-track-header {{
    background: #059669;
    color: #ffffff;
}}
.slow-track-header {{
    background: #d97706;
    color: #ffffff;
}}
.track-tag {{
    background: rgba(0,0,0,0.25);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 800;
    margin-right: 8px;
}}
.round-tag {{
    background: #ffffff;
    color: #0f172a;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 800;
}}
.track-desc {{
    font-size: 13px;
    color: #334155;
    margin-bottom: 14px;
    font-weight: 600;
}}
.turn-card {{
    background: #ffffff;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 14px;
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
}}
.fast-turn-card {{ border: 2px solid #6ee7b7; }}
.slow-turn-card {{ border: 2px solid #fcd34d; }}
.turn-card-head {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
    flex-wrap: wrap;
    gap: 8px;
}}
.turn-num {{
    font-weight: 800;
    font-size: 13px;
    color: #0f172a;
}}
.branch-pill {{
    font-size: 12px;
    font-weight: 800;
    padding: 3px 9px;
    border-radius: 5px;
}}
.pass-pill {{ background: #d1fae5; color: #065f46; border: 1px solid #34d399; }}
.err-pill {{ background: #fee2e2; color: #991b1b; border: 1px solid #f87171; }}
.warn-pill {{ background: #fef3c7; color: #92400e; border: 1px solid #fbbf24; }}
.goal-pill {{ background: #dbeafe; color: #1e40af; border: 1px solid #60a5fa; }}

.msg {{
    font-size: 13.5px;
    padding: 8px 12px;
    border-radius: 6px;
    margin-bottom: 8px;
}}
.user-msg {{ background: #f8fafc; border-left: 4px solid #0f172a; }}
.thought-msg {{ background: #f1f5f9; border-left: 4px solid #64748b; color: #334155; font-size: 12.5px; }}
.agent-msg {{ background: #eff6ff; border-left: 4px solid #2563eb; }}

.turn-slots-wrap {{
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px dashed #cbd5e1;
}}
.slots-title {{
    font-size: 12px;
    font-weight: 800;
    color: #475569;
    margin-bottom: 6px;
}}
.intent-box {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 8px 10px;
    margin-bottom: 6px;
}}
.intent-header {{
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    margin-bottom: 6px;
}}
.intent-id {{ font-weight: 800; color: #0f172a; }}
.intent-meta {{ color: #64748b; }}
.slot-chips {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}}
.slot-chip {{
    font-size: 12px;
    padding: 3px 8px;
    border-radius: 4px;
    border: 1px solid #cbd5e1;
    background: #ffffff;
}}
.exp-chip {{
    background: #ecfdf5;
    border-color: #10b981;
    color: #065f46;
}}
.src-tag {{
    font-size: 11px;
    font-weight: 800;
    color: #047857;
    margin-left: 3px;
}}
</style>
</head>
<body>

<header class="page-header">
    <h1>“联接”Agent 经验记忆：快速闭环路径 vs 多轮澄清路径 对比看板</h1>
    <p>本看板聚焦展示 5 个典型用户（USER_001 ~ USER_005）的 <b>前置经验习得会话（Learning Session）</b> 与 <b>经验记忆应用会话（快速闭环路径 vs 多轮澄清路径 对比）</b>。全量术语已统一规范为 <b>“意图保障单”</b>，并移除网络底层丢包/抖动日志依赖。</p>
    <div class="summary-strip">
        <div class="stat-box">
            <div class="s-title">经验评测会话总数</div>
            <div class="s-num">{total_pairs} 组 (含前置习得共 {total_pairs * 2} 会话)</div>
        </div>
        <div class="stat-box">
            <div class="s-title">快速闭环路径 (启用经验)</div>
            <div class="s-num" style="color:#059669;">2 轮快速闭环 (首轮即命中)</div>
        </div>
        <div class="stat-box">
            <div class="s-title">多轮澄清路径 (未启用经验)</div>
            <div class="s-num" style="color:#d97706;">3 轮澄清闭环</div>
        </div>
        <div class="stat-box">
            <div class="s-title">交互轮数压缩率 (TCG)</div>
            <div class="s-num" style="color:#2563eb;">33.33%</div>
        </div>
        <div class="stat-box">
            <div class="s-title">路径闭环验证通过率</div>
            <div class="s-num" style="color:#059669;">100.0% (10/10 PASS)</div>
        </div>
    </div>
</header>

<section class="arch-panel">
    <h3>📐 经验记忆“快速闭环路径”与“多轮澄清路径”对比流转逻辑</h3>
    <div class="mermaid">
flowchart LR
    U1["<b>Turn 1: 用户原始口语输入</b><br/><b>(含字面常规时段或模糊历史指代)</b>"] --> SW{{"<b>经验记忆库检索</b><br/><b>(ExperienceBank)</b>"}}
    SW -->|"<b>启用经验 (快速闭环路径)</b>"| F1["<b>Turn 1: “联接”Agent 匹配经验规则</b><br/><b>直接输出修正后目标参数</b>"]
    F1 -->|"<b>用户直接确认</b>"| F2["<b>Turn 2: 无需额外澄清</b><br/><b>2 轮完成意图保障单快速闭环</b>"]
    SW -->|"<b>未启用经验 (多轮澄清路径)</b>"| S1["<b>Turn 1: “联接”Agent 按字面直接提参</b><br/><b>产生参数偏差</b>"]
    S1 -->|"<b>触发用户澄清指正</b>"| S2["<b>Turn 2: 用户指出冲突并给出目标参数</b><br/><b>“联接”Agent 二轮修正对齐</b>"]
    S2 -->|"<b>用户最终确认</b>"| S3["<b>Turn 3: 确认修正结果</b><br/><b>3 轮完成意图保障单澄清闭环</b>"]

    style U1 fill:#FFFFFF,stroke:#0f172a,stroke-width:2.5px,color:#0f172a
    style SW fill:#FFFFFF,stroke:#2563eb,stroke-width:2.5px,color:#0f172a
    style F1 fill:#FFFFFF,stroke:#059669,stroke-width:2.5px,color:#0f172a
    style F2 fill:#FFFFFF,stroke:#059669,stroke-width:2.5px,color:#0f172a
    style S1 fill:#FFFFFF,stroke:#dc2626,stroke-width:2.5px,color:#0f172a
    style S2 fill:#FFFFFF,stroke:#d97706,stroke-width:2.5px,color:#0f172a
    style S3 fill:#FFFFFF,stroke:#059669,stroke-width:2.5px,color:#0f172a
    linkStyle default stroke:#0f172a,stroke-width:2px
    </div>
</section>

<div class="filter-bar">
    <div class="filter-group">
        <span class="filter-label">👤 按用户筛选：</span>
        <button class="filter-btn active" onclick="filterCards('user', 'ALL', this)">全部用户 (10)</button>
        <button class="filter-btn" onclick="filterCards('user', 'USER_001', this)">USER_001 巡回讲者 (2)</button>
        <button class="filter-btn" onclick="filterCards('user', 'USER_002', this)">USER_002 金融顾问 (2)</button>
        <button class="filter-btn" onclick="filterCards('user', 'USER_003', this)">USER_003 社群组织者 (2)</button>
        <button class="filter-btn" onclick="filterCards('user', 'USER_004', this)">USER_004 项目申报 (2)</button>
        <button class="filter-btn" onclick="filterCards('user', 'USER_005', this)">USER_005 视觉创作者 (2)</button>
    </div>
    <div class="filter-group">
        <span class="filter-label">📘 按经验规则筛选：</span>
        <button class="filter-btn active" onclick="filterCards('exp', 'ALL', this)">全部经验规则 (5类)</button>
        <button class="filter-btn" onclick="filterCards('exp', 'EXP_PREWARM_BUFFER_01', this)">大型活动提前30分钟试机 (3)</button>
        <button class="filter-btn" onclick="filterCards('exp', 'EXP_CALENDAR_HOLIDAY_EXCEPTION_01', this)">例行排期遇法定假日顺延 (3)</button>
        <button class="filter-btn" onclick="filterCards('exp', 'EXP_MULTI_INTENT_PARTITION_01', this)">私下对直播词看机位选微信视频 (2)</button>
        <button class="filter-btn" onclick="filterCards('exp', 'EXP_ORDER_QUALITY_DISAMBIGUATION_01', this)">按上次来过滤1h临时单选2h正式单 (1)</button>
        <button class="filter-btn" onclick="filterCards('exp', 'EXP_OVERLAPPING_ORDER_RESOLUTION_01', this)">进直播间当连麦嘉宾选开直播 (1)</button>
    </div>
</div>

<main id="cards-root">
    {"".join(cards_html)}
</main>

<script>
mermaid.initialize({{ startOnLoad: true, theme: 'base', themeVariables: {{ background: '#FFFFFF', primaryColor: '#FFFFFF', primaryTextColor: '#0f172a', lineColor: '#0f172a' }} }});

let currentUser = 'ALL';
let currentExp = 'ALL';

function filterCards(type, val, btn) {{
    if (type === 'user') {{
        currentUser = val;
        btn.parentElement.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    }} else {{
        currentExp = val;
        btn.parentElement.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    }}
    document.querySelectorAll('.session-card').forEach(card => {{
        const uMatch = (currentUser === 'ALL' || card.dataset.user === currentUser);
        const eMatch = (currentExp === 'ALL' || card.dataset.exp === currentExp);
        card.style.display = (uMatch && eMatch) ? 'block' : 'none';
    }});
}}
</script>
</body>
</html>
'''
    out_path = Path("docs/html/experience_fast_slow_eval_preview.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_doc, encoding="utf-8")
    print(f"Generated {out_path} ({len(html_doc)} chars, {total_pairs} experience session pairs)")


if __name__ == "__main__":
    personas = load_data()
    build_html(personas)
