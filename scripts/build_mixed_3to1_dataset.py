"""Build a 3:1 mixed cognitive + colleague evaluation dataset.

Mixes each native persona timeline (~18 sessions) with 6 colleague sessions
from dataset_930 (2 Memory-dependent, 2 Record-dependent, 2 self-contained
multi-turn/multi-intent/correction/cancellation sessions) while guaranteeing:
  1. Strict application_name disjointness against native persona habits/records.
  2. Safe chronological gap insertion with exact day-offset timestamp rebasing.
  3. Stage-0 MemorySystem pre-seeding metadata (`preseed_memory.json`) for the
     sampled colleague Memory and Record sessions.
"""
from __future__ import annotations

import glob
import json
import logging
import random
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

NATIVE_DIR = Path(r"D:\coding\cross_memory_data\data\cognitive_samples")
OUT_DIR = Path(r"D:\coding\cross_memory_data\data\cognitive_samples_mixed_3to1")
COLLEAGUE_SESSIONS_PATH = Path(r"C:\Users\Administrator\Downloads\sessions\sessions.jsonl")
COLLEAGUE_USERS_PATH = Path(r"D:\coding\qwen_intent_rag\data\dataset_930\users_3000.jsonl")
NOISE_GLOB = r"D:\coding\qwen_intent_rag\data\*noise*.json"

ABS_DATE_RE = re.compile(r"\d+\s*月\s*\d+\s*[日号]|\d{4}\s*年")
TS_RE = re.compile(r"(\d{4})年(\d{2})月(\d{2})日(\d{2})(?::(\d{2})|时(\d{2})分)")


def _load_noise_ids() -> set[str]:
    noise: set[str] = set()
    for p in glob.glob(NOISE_GLOB):
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        noise.update(data.get("session_ids") or [])
    return noise


def _parse_ymd(ts_str: str) -> date:
    m = TS_RE.search(ts_str or "")
    if not m:
        raise ValueError(f"Invalid timestamp string: {ts_str!r}")
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _shift_ts_str(ts_str: str, delta_days: int) -> str:
    def _repl(m: re.Match[str]) -> str:
        mm = int(m.group(5)) if m.group(5) is not None else int(m.group(6))
        use_cn = m.group(6) is not None
        dt = datetime(
            int(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
            int(m.group(4)),
            mm,
        ) + timedelta(days=delta_days)
        if use_cn:
            return (
                f"{dt.year:04d}年{dt.month:02d}月{dt.day:02d}日"
                f"{dt.hour:02d}时{dt.minute:02d}分"
            )
        return (
            f"{dt.year:04d}年{dt.month:02d}月{dt.day:02d}日"
            f"{dt.hour:02d}:{dt.minute:02d}"
        )

    return TS_RE.sub(_repl, ts_str or "")


def _shift_json_timestamps(obj: Any, delta_days: int) -> Any:
    if isinstance(obj, str):
        return _shift_ts_str(obj, delta_days) if TS_RE.search(obj) else obj
    if isinstance(obj, list):
        return [_shift_json_timestamps(x, delta_days) for x in obj]
    if isinstance(obj, dict):
        return {k: _shift_json_timestamps(v, delta_days) for k, v in obj.items()}
    return obj


def _has_abs_date_in_user_turns(sess: dict[str, Any]) -> bool:
    for ev in sess.get("event_sequence") or []:
        utt = ((ev.get("user") or {}).get("utterance")) or ""
        if ABS_DATE_RE.search(utt):
            return True
    return False


def _collect_source_types(sess: dict[str, Any]) -> set[str]:
    stypes: set[str] = set()
    for it in sess.get("intents") or []:
        params = it.get("params") or {}
        for k, v in params.items():
            if isinstance(v, dict):
                if v.get("source_type"):
                    stypes.add(str(v["source_type"]))
                for sub_v in v.values():
                    if isinstance(sub_v, dict) and sub_v.get("source_type"):
                        stypes.add(str(sub_v["source_type"]))
    return stypes


def _extract_session_apps(sess: dict[str, Any]) -> list[str]:
    apps: list[str] = []
    for it in sess.get("intents") or []:
        app = (((it.get("params") or {}).get("application_name") or {}).get("value")) or ""
        if app and app not in apps:
            apps.append(str(app))
    return apps


def _all_intents_app_in_u1(sess: dict[str, Any]) -> bool:
    intents = sess.get("intents") or []
    if not intents:
        return False
    u1_utt = (((sess.get("event_sequence") or [{}])[0].get("user") or {}).get("utterance")) or ""
    for it in intents:
        app_obj = (it.get("params") or {}).get("application_name") or {}
        app_val = str(app_obj.get("value") or "")
        if not app_val:
            return False
        if app_obj.get("source_type") != "Turn" or app_obj.get("source_ref") != "U1":
            if app_val not in u1_utt:
                return False
    return True


def _load_colleague_pools() -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    noise_ids = _load_noise_ids()
    users_by_id: dict[str, dict[str, Any]] = {}
    for line in COLLEAGUE_USERS_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            u = json.loads(line)
            users_by_id[str(u["user_id"])] = u

    mem_pool: list[dict[str, Any]] = []
    rec_pool: list[dict[str, Any]] = []
    self_pool: list[dict[str, Any]] = []
    target_self_tpls = {
        "T1-3", "T2-1", "T2-2", "T2-3", "T2-4", "T2-5", "T2-6", "T3-1", "T3-2", "X-1", "X-2"
    }

    for line in COLLEAGUE_SESSIONS_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        s = json.loads(line)
        sid = str(s.get("session_id") or "")
        if sid in noise_ids or _has_abs_date_in_user_turns(s):
            continue
        tpl = str((s.get("session_meta") or {}).get("template_id") or "")
        stypes = _collect_source_types(s)
        uid = str(s.get("user_id") or "")
        u_obj = users_by_id.get(uid)
        if not u_obj:
            continue

        if "Memory" in stypes and "Record" not in stypes:
            if _all_intents_app_in_u1(s) and len(s.get("intents") or []) == 1:
                it = s["intents"][0]["params"]
                svc_obj = it.get("service_name") or {}
                res_obj = (it.get("resolution") or {}).get("min_value") or {}
                rtt_obj = (it.get("rtt") or {}).get("max_value") or {}
                prof_map = {p["key"]: p["value"] for p in (u_obj.get("profile") or [])}
                ok_mem = True
                if svc_obj.get("source_type") == "Memory":
                    p_svc = "视频" if prof_map.get("常用业务") == "短视频" else prof_map.get("常用业务")
                    if p_svc != svc_obj.get("value"):
                        ok_mem = False
                if res_obj.get("source_type") == "Memory" and prof_map.get("默认分辨率") != res_obj.get("value"):
                    ok_mem = False
                if rtt_obj.get("source_type") == "Memory" and prof_map.get("常用时延要求") != rtt_obj.get("value"):
                    ok_mem = False
                if ok_mem and (
                    prof_map.get("默认分辨率") or prof_map.get("常用时延要求") or prof_map.get("常用开始时段")
                ):
                    mem_pool.append(s)
        elif "Record" in stypes and "Memory" not in stypes:
            if _all_intents_app_in_u1(s) and len(s.get("intents") or []) == 1:
                it = s["intents"][0]["params"]
                app = (it.get("application_name") or {}).get("value")
                svc = (it.get("service_name") or {}).get("value")
                res_obj = (it.get("resolution") or {}).get("min_value") or {}
                rtt_obj = (it.get("rtt") or {}).get("max_value") or {}
                recs = [
                    r for r in (u_obj.get("records") or [])
                    if r.get("application_name") == app
                    and r.get("service_name") == svc
                    and (
                        res_obj.get("source_type") != "Record"
                        or (r.get("resolution") or {}).get("min_value") == res_obj.get("value")
                    )
                    and (
                        rtt_obj.get("source_type") != "Record"
                        or (r.get("rtt") or {}).get("max_value") == rtt_obj.get("value")
                    )
                ]
                if recs:
                    rec_pool.append(s)
        elif not (stypes & {"Memory", "Record"}) and tpl in target_self_tpls:
            if _extract_session_apps(s):
                self_pool.append(s)

    logger.info(
        "Loaded colleague pools: mem_pool=%d, rec_pool=%d, self_pool=%d",
        len(mem_pool), len(rec_pool), len(self_pool),
    )
    return mem_pool, rec_pool, self_pool, users_by_id


def _find_safe_gaps(sessions: list[dict[str, Any]], k: int = 6) -> list[tuple[int, date]]:
    """Select k chronological gaps (after index i) sorted by gap size descending."""
    candidates: list[tuple[int, int, date]] = []
    for i in range(len(sessions) - 1):
        s_cur = sessions[i]
        s_nxt = sessions[i + 1]
        d_cur = _parse_ymd(s_cur["reference_time"])
        d_nxt = _parse_ymd(s_nxt["reference_time"])
        gap_days = (d_nxt - d_cur).days
        if gap_days < 2:
            continue
        nxt_meta = s_nxt.get("session_meta") or {}
        nxt_tier = nxt_meta.get("memory_tier", "")
        nxt_action = (nxt_meta.get("scenario") or {}).get("memory_action", "")
        if nxt_tier == "working_memory":
            continue
        if "implicit_habit" in nxt_action:
            continue
        target_date = d_cur + timedelta(days=1)
        candidates.append((gap_days, i, target_date))

    candidates.sort(key=lambda x: (-x[0], x[1]))
    chosen = sorted(candidates[:k], key=lambda x: x[1])
    return [(idx, t_date) for _, idx, t_date in chosen]


def _build_preseed_profile_entry(
    sess: dict[str, Any], u_obj: dict[str, Any]
) -> dict[str, Any]:
    it = (sess.get("intents") or [])[0]["params"]
    app = str((it.get("application_name") or {}).get("value") or "")
    svc = str((it.get("service_name") or {}).get("value") or "")
    prof_map = {p["key"]: p["value"] for p in (u_obj.get("profile") or [])}
    res = str(prof_map.get("默认分辨率") or "")
    lat = str(prof_map.get("常用时延要求") or "")
    tw_val = str(prof_map.get("常用开始时段") or "")
    dur_val = str(prof_map.get("常用保障时长") or "")
    return {
        "application": app,
        "business": svc,
        "application_name": app,
        "service_name": svc,
        "resolution": res,
        "latency": lat,
        "rtt": lat,
        "time_window": tw_val,
        "duration": dur_val,
        "default_duration": dur_val,
    }


def _build_preseed_record_entry(
    sess: dict[str, Any],
    u_obj: dict[str, Any],
    delta_days: int,
    persona_uid: str,
    rec_seq: int,
) -> dict[str, Any]:
    it = (sess.get("intents") or [])[0]["params"]
    app = str((it.get("application_name") or {}).get("value") or "")
    svc = str((it.get("service_name") or {}).get("value") or "")
    res_obj = (it.get("resolution") or {}).get("min_value") or {}
    rtt_obj = (it.get("rtt") or {}).get("max_value") or {}
    recs = [
        r for r in (u_obj.get("records") or [])
        if r.get("application_name") == app
        and r.get("service_name") == svc
        and (
            res_obj.get("source_type") != "Record"
            or (r.get("resolution") or {}).get("min_value") == res_obj.get("value")
        )
        and (
            rtt_obj.get("source_type") != "Record"
            or (r.get("rtt") or {}).get("max_value") == rtt_obj.get("value")
        )
    ]
    recs.sort(key=lambda r: str(r.get("completed_at") or ""), reverse=True)
    raw_rec = recs[0]
    ts_block = raw_rec.get("timestamp") or {}
    st_shifted = _shift_ts_str(str(ts_block.get("start_timestamp") or ""), delta_days)
    et_shifted = _shift_ts_str(str(ts_block.get("end_timestamp") or ""), delta_days)
    comp_shifted = _shift_ts_str(str(raw_rec.get("completed_at") or ""), delta_days)
    return {
        "record_id": f"Z_PRESEED_{persona_uid}_{rec_seq:02d}",
        "session_id": f"PRESEED-{rec_seq:02d}",
        "created_at": comp_shifted,
        "completed_at": comp_shifted,
        "application_name": app,
        "service_name": svc,
        "resolution": (raw_rec.get("resolution") or {}).get("min_value") or "",
        "rtt": (raw_rec.get("rtt") or {}).get("max_value") or "",
        "start_timestamp": st_shifted,
        "end_timestamp": et_shifted,
        "duration": ts_block.get("duration") or "",
        "status": "completed",
        "validity": "long_term",
        "is_preseed_record": True,
    }


def _select_six_colleague_sessions(
    rng: random.Random,
    used_apps: set[str],
    mem_pool: list[dict[str, Any]],
    rec_pool: list[dict[str, Any]],
    self_pool: list[dict[str, Any]],
) -> list[tuple[str, dict[str, Any]]]:
    """Select 2 Memory, 2 Record, and 2 Self-contained colleague sessions with disjoint apps."""
    picked: list[tuple[str, dict[str, Any]]] = []
    mem_t14 = [s for s in mem_pool if s["session_meta"]["template_id"] == "T1-4"]
    mem_multi = [s for s in mem_pool if s["session_meta"]["template_id"] != "T1-4"]
    rng.shuffle(mem_t14)
    rng.shuffle(mem_multi)

    for subpool in (mem_t14, mem_multi):
        for s in subpool:
            apps = set(_extract_session_apps(s))
            if apps and not (apps & used_apps):
                used_apps.update(apps)
                picked.append(("colleague_memory_session", s))
                break

    rec_cands = list(rec_pool)
    rng.shuffle(rec_cands)
    for s in rec_cands:
        if len([x for x in picked if x[0] == "colleague_record_session"]) >= 2:
            break
        apps = set(_extract_session_apps(s))
        if apps and not (apps & used_apps):
            used_apps.update(apps)
            picked.append(("colleague_record_session", s))

    self_cands = list(self_pool)
    rng.shuffle(self_cands)
    used_tpls: set[str] = set()
    for s in self_cands:
        if len(picked) >= 6:
            break
        tpl = s["session_meta"]["template_id"]
        apps = set(_extract_session_apps(s))
        if apps and not (apps & used_apps) and tpl not in used_tpls:
            used_apps.update(apps)
            used_tpls.add(tpl)
            picked.append(("colleague_self_contained", s))

    rng.shuffle(picked)
    return picked


def build_mixed_dataset() -> None:
    mem_pool, rec_pool, self_pool, users_by_id = _load_colleague_pools()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    persona_dirs = sorted(
        [d for d in NATIVE_DIR.iterdir() if d.is_dir() and d.name.startswith("mobile_persona_")],
        key=lambda p: p.name,
    )
    total_native = 0
    total_ext = 0
    role_counts: dict[str, int] = {}
    manifest_personas: list[dict[str, Any]] = []

    for idx_p, p_dir in enumerate(persona_dirs, 1):
        rng = random.Random(20260409 + idx_p * 97)
        p_skel_file = p_dir / "persona_skeleton.json"
        persona_data = (
            json.loads(p_skel_file.read_text(encoding="utf-8"))
            if p_skel_file.exists()
            else {"persona_id": p_dir.name}
        )
        native_sessions = json.loads((p_dir / "sessions.json").read_text(encoding="utf-8"))
        persona_uid = str(native_sessions[0]["user_id"])

        native_apps: set[str] = set()
        for s in native_sessions:
            native_apps.update(_extract_session_apps(s))

        gaps = _find_safe_gaps(native_sessions, k=6)
        picked = _select_six_colleague_sessions(
            rng, set(native_apps), mem_pool, rec_pool, self_pool
        )
        assert len(gaps) == 6 and len(picked) == 6, f"{p_dir.name}: gaps={len(gaps)}, picked={len(picked)}"

        preseed_profiles: list[dict[str, Any]] = []
        preseed_records: list[dict[str, Any]] = []
        insert_By_after_idx: dict[int, dict[str, Any]] = {}

        for ext_i, ((after_idx, target_date), (role, raw_ext)) in enumerate(zip(gaps, picked), 1):
            role_counts[role] = role_counts.get(role, 0) + 1
            orig_uid = str(raw_ext["user_id"])
            u_obj = users_by_id[orig_uid]
            orig_date = _parse_ymd(raw_ext["reference_time"])
            delta_days = (target_date - orig_date).days

            rebased = _shift_json_timestamps(raw_ext, delta_days)
            orig_sid = str(raw_ext.get("session_id") or f"EXT{ext_i:02d}")
            tpl = str((raw_ext.get("session_meta") or {}).get("template_id") or "EXT")
            rebased["user_id"] = persona_uid
            rebased["session_id"] = f"{persona_uid}-EXT{ext_i:02d}-{orig_sid}"
            rebased["session_meta"] = {
                "template_id": tpl,
                "memory_tier": "external_distractor",
                "memory_role": role,
                "source_colleague_session_id": orig_sid,
                "source_colleague_user_id": orig_uid,
                "scenario": {
                    "blueprint_type": f"{role}:{tpl}",
                    "environment": "colleague_930_mix",
                    "memory_action": role,
                },
            }
            if role == "colleague_memory_session":
                preseed_profiles.append(_build_preseed_profile_entry(raw_ext, u_obj))
            elif role == "colleague_record_session":
                preseed_records.append(
                    _build_preseed_record_entry(
                        raw_ext, u_obj, delta_days, persona_uid, len(preseed_records) + 1
                    )
                )
            insert_By_after_idx[after_idx] = rebased

        mixed_sessions: list[dict[str, Any]] = []
        for i, ns_sess in enumerate(native_sessions):
            mixed_sessions.append(ns_sess)
            if i in insert_By_after_idx:
                mixed_sessions.append(insert_By_after_idx[i])

        out_p_dir = OUT_DIR / p_dir.name
        out_p_dir.mkdir(parents=True, exist_ok=True)
        (out_p_dir / "persona.json").write_text(
            json.dumps(persona_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (out_p_dir / "persona_skeleton.json").write_text(
            json.dumps(persona_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (out_p_dir / "sessions.json").write_text(
            json.dumps(mixed_sessions, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (out_p_dir / "sessions.jsonl").write_text(
            "\n".join(json.dumps(s, ensure_ascii=False) for s in mixed_sessions) + "\n",
            encoding="utf-8",
        )
        preseed_payload = {
            "user_id": persona_uid,
            "event_time": "2026-04-01T00:00:00+08:00",
            "profiles": preseed_profiles,
            "records": preseed_records,
        }
        (out_p_dir / "preseed_memory.json").write_text(
            json.dumps(preseed_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        total_native += len(native_sessions)
        total_ext += len(picked)
        manifest_personas.append(
            {
                "persona_dir": p_dir.name,
                "user_id": persona_uid,
                "native_sessions": len(native_sessions),
                "colleague_sessions": len(picked),
                "total_sessions": len(mixed_sessions),
                "preseed_profiles": len(preseed_profiles),
                "preseed_records": len(preseed_records),
            }
        )

    manifest = {
        "dataset_name": "cognitive_samples_mixed_3to1",
        "mix_ratio": "3:1 (approx. 18 native cognitive sessions : 6 colleague sessions per persona)",
        "persona_count": len(persona_dirs),
        "total_native_sessions": total_native,
        "total_colleague_sessions": total_ext,
        "total_sessions": total_native + total_ext,
        "colleague_role_breakdown": role_counts,
        "personas": manifest_personas,
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(
        "Completed 35-persona 3:1 dataset: %d total sessions (%d native + %d colleague) | roles=%s",
        total_native + total_ext,
        total_native,
        total_ext,
        role_counts,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    build_mixed_dataset()
