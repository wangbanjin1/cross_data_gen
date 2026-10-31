"""Agent 侧确定性兜底台词与动作类型规范化模块。"""

from __future__ import annotations

from src.templates.prompts.small_memory_prompt import clarification_question, declaration_example
from src.templates.prompts.fallback_helpers import (
    _formal_and_temp_dur_info,
    _sanitize_env,
)


def _fallback_agent_experience_learning(s_plan: dict, turn_idx: int, is_last: bool, tp: dict) -> str:
    app, srv, res, rtt = tp["application_name"], tp["service_name"], tp["resolution"], tp["rtt"]
    exp_id = s_plan.get("experience_id") or s_plan.get("experience_citation", {}).get("experience_id")
    if exp_id == "EXP_CALENDAR_HOLIDAY_EXCEPTION_01":
        sh_t = (s_plan.get("nominal_start") or tp.get("start_timestamp", "")).split("日")[-1] or "15时00分"
        eh_t = (s_plan.get("nominal_end") or tp.get("end_timestamp", "")).split("日")[-1] or "17时00分"
        if turn_idx == 1:
            return f"收到，已为您准备好下周一（10月5日）{sh_t}至{eh_t}的例行周会意图保障单（{res} / 时延≤{rtt}），确认按此时段预约吗？"
        if turn_idx == 2 and not is_last:
            return f"明白！10月5日确实处于国庆法定假期。已为您将例行周会意图保障单顺延调整至节后首个工作日（10月8日）{sh_t}至{eh_t}（{res} / 时延≤{rtt}），确认按此顺延方案预约吗？"
        return f"好的，已为您将本次例行周会意图保障单顺延调整至国庆节后首个工作日（10月8日）同时段办理（{res} / 时延≤{rtt}），并记下这条节假日避让顺延经验，祝您假期愉快！"
    if exp_id == "EXP_MULTI_INTENT_PARTITION_01":
        sh_t = tp.get("start_timestamp", "").split("日")[-1] or "12时30分"
        new_eh_t = tp.get("end_timestamp", "").split("日")[-1] or "14时30分"
        dur_val = tp.get("duration", "120min")
        if turn_idx == 1:
            return f"收到，已为您准备好{sh_t}至{new_eh_t}（持续{dur_val}）的【抖音-开直播】意图保障单（{res} / 时延≤{rtt}），确认直接为您开通吗？"
        if turn_idx == 2 and not is_last:
            return f"明白！原来私下跟搭档对直播词、看镜头机位平时都是用【微信-视频通话】沟通。已为您将意图保障单修正为【微信-视频通话】（{sh_t}至{new_eh_t}，持续{dur_val}，{res} / 时延≤{rtt}），确认按修改后的配置开通吗？"
        return f"好的，已为您成功开通【微信-视频通话】意图保障单（{sh_t}至{new_eh_t}，持续{dur_val}，{res} / 时延≤{rtt}），并记下这条日常对词试机位经验，祝您对词顺利！"
    if exp_id == "EXP_PREWARM_BUFFER_01":
        nom_sh_t = (s_plan.get("nominal_start") or tp.get("start_timestamp", "")).split("日")[-1]
        pw_sh_t, eh_t = tp["start_timestamp"].split("日")[-1], tp["end_timestamp"].split("日")[-1]
        if turn_idx == 1:
            return f"收到，已为您准备好{nom_sh_t}至{eh_t}的现场意图保障单配置（{res} / 时延≤{rtt}），确认直接开通吗？"
        if turn_idx == 2 and not is_last:
            return f"明白！大型场馆重大活动现场设备调试确实需要预留试机时间。已为您将意图保障单起保时间提前30分钟调整为{pw_sh_t}至{eh_t}（总时长扩充至{tp['duration']}，{res} / 时延≤{rtt}），确认按调整后的预热方案开通吗？"
        return f"好的，已按提前30分钟预热方案为您开通{app}{srv}意图保障单（{pw_sh_t}至{eh_t}，持续{tp['duration']}，{res} / 时延≤{rtt}），并记下这条大型活动提前预热试机的日常经验，祝现场活动顺利！"
    if exp_id == "EXP_ORDER_QUALITY_DISAMBIGUATION_01":
        sh_t, eh_t = tp["start_timestamp"].split("日")[-1], tp["end_timestamp"].split("日")[-1]
        d_info = _formal_and_temp_dur_info(tp)
        if turn_idx == 1:
            return f"收到，已按您最近一笔（前天）的记录，为您准备好{sh_t}至{d_info['temp_end_t']}（持续{d_info['temp_dur']}）的{app}{srv}意图保障单（{res} / 时延≤{rtt}），确认按此开通吗？"
        if turn_idx == 2 and not is_last:
            return f"明白！已为您过滤前天的{d_info['temp_short']}临时短单，改按上周正式客户路演单为您排满{d_info['formal_short']}（{sh_t}至{eh_t}，持续{d_info['formal_dur']}，{res} / 时延≤{rtt}），确认按此正式规格开通吗？"
        return f"好的，已按上周正式客户路演单规格为您排满{d_info['formal_short']}（{sh_t}至{eh_t}，持续{d_info['formal_dur']}，{res} / 时延≤{rtt}），并记下这条经验，祝您路演顺畅！"
    if exp_id == "EXP_OVERLAPPING_ORDER_RESOLUTION_01":
        sh_t = tp.get("start_timestamp", "").split("日")[-1] or "15时00分"
        eh_t = tp.get("end_timestamp", "").split("日")[-1] or "17时00分"
        dur_val = tp.get("duration", "120min")
        if turn_idx == 1:
            return f"收到，已为您准备好{sh_t}至{eh_t}（持续{dur_val}）的【抖音-看直播】意图保障单（{res} / 时延≤{rtt}），确认按此直接开通吗？"
        if turn_idx == 2 and not is_last:
            return f"明白！进他人直播间当连麦嘉宾需要上麦发言推流，确实应当按【开直播】保障上行。已为您修正为【抖音-开直播】意图保障单（{sh_t}至{eh_t}，持续{dur_val}，{res} / 时延≤{rtt}），确认按修改后的配置开通吗？"
        return f"好的，已为您成功开通【抖音-开直播】意图保障单（{sh_t}至{eh_t}，持续{dur_val}，{res} / 时延≤{rtt}），并记下这条日常经验，祝您连麦互动顺利！"
    if turn_idx == 1:
        return f"收到，已为您配置好意图保障单方案（{res} / 时延≤{rtt}），确认直接开通吗？"
    if turn_idx == 2 and not is_last:
        return f"明白，已按您的要求更新意图保障单配置（{res} / 时延≤{rtt}），确认按修改后的方案开通吗？"
    return f"好的，已为您成功受理本次意图保障单（{res} / 时延≤{rtt}），祝您工作顺利！"


def _fallback_agent_experience_reuse(s_plan: dict, turn_idx: int, env: str, tp: dict) -> str | None:
    app, srv, res, rtt = tp["application_name"], tp["service_name"], tp["resolution"], tp["rtt"]
    tid = s_plan.get("template_id", "")
    exp_id = s_plan.get("experience_citation", {}).get("experience_id")
    learn_sid = s_plan.get("learning_source_session")
    if exp_id == "EXP_CALENDAR_HOLIDAY_EXCEPTION_01":
        learn_prefix = f"参考此前在 {learn_sid} 的处理做法，" if learn_sid else "参考此前的处理经验，"
        return (
            f"收到，识别到下周一（10月5日）恰逢国庆节法定长假，办公区全员放假。{learn_prefix}已主动为您将例行周会意图保障单顺延至节后首个工作日（10月8日）同时段办理，避免放假期间在空办公室空跑产生费用，确认按此顺延办理吗？"
            if turn_idx == 1
            else f"好的，已为您将例行周会意图保障单顺延至10月8日办理（{res} / 时延≤{rtt}），祝您假期愉快！"
        )
    if tid == "T2-4" or exp_id == "EXP_MULTI_INTENT_PARTITION_01":
        learn_prefix = f"参考此前在 {learn_sid} 的日常对词试机位经验，" if learn_sid else "参考此前的日常对词试机位经验，"
        sh_t = tp.get("start_timestamp", "").split("日")[-1] or "12时00分"
        eh_t = tp.get("end_timestamp", "").split("日")[-1] or "12时30分"
        dur_val = tp.get("duration", "30min")
        tp2 = s_plan.get("second_target_params") or {}
        app2 = tp2.get("application_name") or (s_plan.get("second_source") or {}).get("application_name") or "抖音"
        srv2 = tp2.get("service_name") or (s_plan.get("second_source") or {}).get("service_name") or "开直播"
        res2, rtt2 = tp2.get("resolution", res), tp2.get("rtt", rtt)
        sh2_t = (tp2.get("start_timestamp") or s_plan.get("start2") or tp.get("start_timestamp", "")).split("日")[-1] or "12时30分"
        eh2_t = (tp2.get("end_timestamp") or s_plan.get("end2") or tp.get("end_timestamp", "")).split("日")[-1] or "14时00分"
        dur2_val = tp2.get("duration") or s_plan.get("dur2") or s_plan.get("base_dur") or "90min"
        if exp_id == "EXP_MULTI_INTENT_PARTITION_01" or s_plan.get("blueprint_type") == "multi_intent_experience":
            return (
                f"识别到您第一场（{sh_t}至{eh_t}）是在正式开播前先跟搭档私下对直播词和看镜头机位。{learn_prefix}第一笔已主动为您匹配【微信-视频通话】意图保障单（{sh_t}至{eh_t}，持续{dur_val}，{res} / 时延≤{rtt}）；第二笔正式业务为您准备好【{app2}-{srv2}】意图保障单（{sh2_t}至{eh2_t}，持续{dur2_val}，{res2} / 时延≤{rtt2}），确认按这两笔配置开通吗？"
                if turn_idx == 1
                else f"好的，已为您同时成功开通第一笔【微信-视频通话】（{sh_t}至{eh_t}，持续{dur_val}，{res} / 时延≤{rtt}）与第二笔【{app2}-{srv2}】（{sh2_t}至{eh2_t}，持续{dur2_val}，{res2} / 时延≤{rtt2}）两笔意图保障单，祝您对词试机位与正式活动一切顺利！"
            )
        return (
            f"收到，已为您准备好两笔异构业务保障方案：第一笔【{app}-{srv}】（{sh_t}至{eh_t}，持续{dur_val}，画质{res} / 时延≤{rtt}）；第二笔【{app2}-{srv2}】（{sh2_t}至{eh2_t}，持续{dur2_val}，画质{res2} / 时延≤{rtt2}），确认按这两笔配置开通吗？"
            if turn_idx == 1
            else f"好的，已为您成功受理并开通【{app}-{srv}】（{sh_t}至{eh_t}，{res} / 时延≤{rtt}）与【{app2}-{srv2}】（{sh2_t}至{eh2_t}，{res2} / 时延≤{rtt2}）两笔网络保障单，祝您使用愉快！"
        )
    if tid == "T2-9" or exp_id == "EXP_PREWARM_BUFFER_01":
        pw_start_t, end_t = tp["start_timestamp"].split("日")[-1], tp["end_timestamp"].split("日")[-1]
        learn_prefix = f"参考此前在 {learn_sid} 的处理做法，" if learn_sid else "参考此前的处理经验，"
        if s_plan.get("is_counterexample"):
            return (
                f"收到，{env}现场人比较多，一般建议优先保流畅；不过既然您明确需要原画采录，已按您的要求保持{res}画质、时延{rtt}以内，确认直接开通意图保障单吗？"
                if turn_idx == 1
                else f"好的，已按原画要求为您开通{app}{srv}意图保障单（{res} / 时延≤{rtt}），祝您录制顺利！"
            )
        if s_plan.get("round_count") == 3:
            if turn_idx == 1:
                return f"收到，{env}现场属于大型场馆重大活动，建议将意图保障单起保时间提前30分钟推算为{pw_start_t}至{end_t}进行试机预热。您看这样合适吗？"
            if turn_idx == 2:
                return f"预留30分钟试机能够确保开场推流平稳流畅，画质{res}、时延稳定在{rtt}。确认按这个开通意图保障单吗？"
            return f"好的，已为您开通{app}{srv}意图保障单（{pw_start_t}至{end_t}，{res} / 时延≤{rtt}），祝您现场活动顺利！"
        return (
            f"收到！大型场馆重大活动现场设备调试与连线建议提前预热试机。{learn_prefix}为您将意图保障单起保时间自动提前30分钟推算为{pw_start_t}至{end_t}（保障时长扩充至{tp['duration']}，{res} / 时延≤{rtt}），确认直接开通吗？"
            if turn_idx == 1
            else f"好的，已为您成功受理{app}{srv}意图保障单（{pw_start_t}至{end_t}，持续{tp['duration']}，{res} / 时延≤{rtt}），预留30分钟预热试机，祝现场顺利！"
        )
    if exp_id == "EXP_ORDER_QUALITY_DISAMBIGUATION_01":
        start_t, end_t = tp["start_timestamp"].split("日")[-1], tp["end_timestamp"].split("日")[-1]
        d_info = _formal_and_temp_dur_info(tp)
        learn_prefix = f"参考此前在 {learn_sid} 的历史单据时长优选经验，" if learn_sid else "参考此前的历史单据时长优选经验，"
        return (
            f"检索到您历史账本中有两笔记录（前天{d_info['temp_short']}临时短单{d_info['temp_dur']} vs 上周正式客户路演单{d_info['formal_dur']}）。{learn_prefix}识别到您今天是办正式客户远程路演，已自动为您过滤前天那笔{d_info['temp_short']}临时短单，按上周正式路演单为您排满{d_info['formal_short']}（{start_t}至{end_t}，持续{tp['duration']}，{res} / 时延≤{rtt}），确认直接开通吗？"
            if turn_idx == 1
            else f"好的，已按上周{d_info['formal_short']}正式路演单时长（{start_t}至{end_t}，持续{tp['duration']}，{res} / 时延≤{rtt}）为您成功受理{app}{srv}意图保障单，祝您路演顺畅！"
        )
    if tid == "T2-10" or exp_id == "EXP_OVERLAPPING_ORDER_RESOLUTION_01":
        start_t, end_t = tp["start_timestamp"].split("日")[-1], tp["end_timestamp"].split("日")[-1]
        learn_prefix = f"参考此前在 {learn_sid} 的连麦嘉宾业务选择经验，" if learn_sid else "参考此前的连麦嘉宾业务选择经验，"
        return (
            f"识别到您是受邀进主会场抖音直播间当连麦嘉宾互动，需要开摄像头上麦发言推流，不能按普通观众【看直播】受理。{learn_prefix}已主动为您匹配【抖音-开直播】意图保障单（{start_t}至{end_t}，持续{tp['duration']}，{res} / 时延≤{rtt}），确认按此开通吗？"
            if turn_idx == 1
            else f"好的，已为您成功开通【抖音-开直播】意图保障单（{start_t}至{end_t}，持续{tp['duration']}，{res} / 时延≤{rtt}），祝您连麦互动圆满顺利！"
        )
    return None


def _fallback_agent_working_and_override(s_plan: dict, turn_idx: int, is_last: bool, env: str, tp: dict) -> str | None:
    app, srv, res, rtt = tp["application_name"], tp["service_name"], tp["resolution"], tp["rtt"]
    tid = s_plan.get("template_id", "")
    b_type = s_plan.get("blueprint_type", "")
    start_t, end_t = tp["start_timestamp"].split("日")[-1], tp["end_timestamp"].split("日")[-1]
    if tid == "T2-5":
        if turn_idx == 1:
            return f"收到，我调取到之前登记的{app}{srv}配置：画质{res}、时延{rtt}以内，从{start_t}开始保障，确认按这套配置开通吗？"
        if turn_idx == 2 and not is_last:
            return f"收到，已为您将{app}{srv}保障时长延长至{tp['duration']}（时段更新为{start_t}至{end_t}，画质保持{res}、时延≤{rtt}），确认按延长后的配置开通吗？"
        return f"好的，已按老规矩为您开通{app}{srv}保障：画质保持{res}、时延上限{rtt}，时长已延长至{tp['duration']}（{start_t}至{end_t}）。祝您活动顺利！"
    if tid == "T2-6":
        if s_plan.get("is_disambiguation", False):
            cand_ids = s_plan.get("working_memory_pointer", {}).get("candidate_record_ids", [])
            cand_str = "、".join(cand_ids) if cand_ids else "意图保障单A和意图保障单B"
            if turn_idx == 1:
                return f"收到，查询到您此前在{env}有多次{app}{srv}历史意图保障单（包括 {cand_str}），配置规格略有差异。请问您今天是指按哪一次的规格来开通呢？"
            if turn_idx == 2:
                return f"明白，已精准锁定最近一次意图保障单规格（{res} / 时延≤{rtt}），时段为{start_t}至{end_t}，确认直接开通吗？"
            return f"好的，已按您确认的历史意图保障单规格成功开通今日{app}{srv}保障（{res} / 时延≤{rtt}，时段{start_t}至{end_t}）。祝您工作顺利！"
        is_month = s_plan.get("working_memory_pointer", {}).get("inferred_delta_days", 7) >= 25
        if turn_idx == 1:
            return (
                f"收到，已为您跨期调取到上个月在{env}的{app}{srv}历史意图保障单（画质{res}、时延≤{rtt}）。请问今天具体的保障时间是几点到几点呢？"
                if is_month
                else f"收到，已为您在历史意图保障单账本中找到上周在{env}的{app}{srv}意图保障单（画质{res}、时延≤{rtt}）。请问今天具体的保障时间是几点到几点呢？"
            )
        if turn_idx == 2 and not is_last:
            label = "上月" if is_month else "上周"
            return f"收到，已为您锁定今日{start_t}至{end_t}（持续{tp['duration']}）的{app}{srv}保障（继承{label}历史意图保障单规格：画质{res}、时延≤{rtt}），确认按此配置开通吗？"
        return (
            f"好的，已按一个月前历史意图保障单规格为您开通今日{app}{srv}保障（{res} / 时延≤{rtt}，时段{start_t}至{end_t}）。祝您工作顺利！"
            if is_month
            else f"好的，已按您引用的历史意图保障单规格为您成功开通今日{app}{srv}保障（{res} / 时延≤{rtt}，时段{start_t}至{end_t}）。祝您工作顺利！"
        )
    if tid == "T2-7":
        is_adv = s_plan.get("working_memory_pointer", {}).get("reschedule_direction") == "advance"
        if turn_idx == 1:
            return (
                f"收到，已找到您此前预约的{app}{srv}意图保障单。提前一小时后，新的保障时段为{start_t}至{end_t}，确认进行提前改期吗？"
                if is_adv
                else f"收到，已找到您此前预约的{app}{srv}意图保障单。往后推迟一小时后，新的保障时段为{start_t}至{end_t}，确认进行改期吗？"
            )
        return (
            f"好的，已为您成功办理意图保障单提前生效变更，保障时段已更新为{start_t}至{end_t}生效。祝您使用顺利！"
            if is_adv
            else f"好的，已为您成功办理意图保障单延期变更，保障时段已更新为{start_t}至{end_t}生效。祝您使用顺利！"
        )
    if tid == "T2-8":
        query_info = s_plan.get("working_memory_query", {})
        total_orders = query_info.get("total_orders", 3)
        total_mins = query_info.get("total_duration_minutes", 300)
        if "全月" in query_info.get("reconcile_scope", ""):
            return f"已为您生成全月历史意图保障单总对账报表：本月您累计成功办理了 {total_orders} 次移动网络保障，累计保障总时长达 {total_mins} 分钟，涵盖各类重点场景，所有意图保障单全部履约闭环。"
        return f"已为您查询到本周历史意图保障单流水账：本周您共成功办理了 {total_orders} 次移动网络保障，累计保障时长达 {total_mins} 分钟，涵盖{app}{srv}等场景，所有意图保障单均已按期履约。"
    if tid == "T2-3":
        base_res = s_plan.get("base_resolution") or "1080p"
        base_rtt = s_plan.get("base_rtt") or "50ms"
        if turn_idx == 1:
            return f"收到，我调取到之前登记的{app}{srv}配置：画质{base_res}、时延{base_rtt}以内，{start_t}至{end_t}（持续{tp['duration']}），确认按这套配置开通吗？"
        if turn_idx == 2 and not is_last:
            return f"明白，已针对今日现场特殊情况为您临时调整{app}{srv}保障参数：画质{res}、时延{rtt}以内，时段{start_t}至{end_t}（持续{tp['duration']}），确认按此临时配置开通吗？"
        return f"好的，已按现场特殊情况为您临时调整开通{app}{srv}保障：画质{res}、时延上限{rtt}，时段{start_t}至{end_t}。祝您现场顺利！"
    if tid == "T1-3":
        tp2 = s_plan.get("second_target_params") or {}
        app2 = tp2.get("application_name") or ("快手" if app == "抖音" else "钉钉")
        srv2 = tp2.get("service_name") or srv
        res2, rtt2 = tp2.get("resolution", res), tp2.get("rtt", rtt)
        sh2_t = (tp2.get("start_timestamp") or s_plan.get("start2") or tp["start_timestamp"]).split("日")[-1]
        eh2_t = (tp2.get("end_timestamp") or s_plan.get("end2") or tp["end_timestamp"]).split("日")[-1]
        dur2_val = tp2.get("duration") or s_plan.get("dur2") or tp["duration"]
        return (
            f"收到，已为您同时开通两笔同类{srv}网络保障：第一笔【{app}-{srv}】（画质{res}，时延上限{rtt}，保障时段{start_t}至{end_t}，持续{tp['duration']}）；"
            f"第二笔【{app2}-{srv2}】（画质{res2}，时延上限{rtt2}，保障时段{sh2_t}至{eh2_t}，持续{dur2_val}）。祝您两场业务都顺利！"
        )
    if tid == "T1-1" or b_type == "distractor":
        return f"收到，已为您开通{app}{srv}网络保障：画质{res}，时延上限{rtt}，保障时间{tp['start_timestamp']}至{tp['end_timestamp']}（共{tp['duration']}）。祝您使用顺利！"
    return None


def _fallback_agent_factual(s_plan: dict, turn_idx: int, role: str, is_last: bool, env: str, tp: dict) -> str:
    app, srv, res, rtt = tp["application_name"], tp["service_name"], tp["resolution"], tp["rtt"]
    decl_mode = s_plan.get("declaration_mode", "explicit_declaration")
    trig_type = s_plan.get("storyline_trigger_type", "time_periodic")
    period_type = s_plan.get("period_type", "weekly")
    start_t, end_t = tp["start_timestamp"].split("日")[-1], tp["end_timestamp"].split("日")[-1]
    if is_last:
        if s_plan.get("agility_factor") == 1.0 and role in ["reinforcement_session", "reuse_session"]:
            return f"好的，已按老规矩为您开通{app}{srv}网络保障（{res} / 时延≤{rtt}，时段{start_t}至{end_t}），祝您使用愉快！"
        if role == "evidence_session" and decl_mode == "explicit_declaration":
            return "好的，已为您成功受理本次保障，并已为您将该配置记录为长期老规矩，祝您使用愉快！"
        if role == "reinforcement_session" and decl_mode == "implicit_induction" and s_plan.get("session_id", "").endswith("-03"):
            return "好的，已按您刚才的表达记录这个使用习惯，并为您开通本次保障。祝您使用愉快！"
        return f"好的，已为您成功受理{app}{srv}网络保障（{res} / 时延≤{rtt}），祝您使用愉快！"
    if role == "evidence_session":
        if turn_idx == 1:
            return f"收到，已为您锁定{app}{srv}保障，时间从{start_t}开始。请问您需要保障的清晰度、时延上限和预计持续时长分别是多少呢？"
        return f"收到，已为您登记老规矩习惯。确认按{res}、{rtt}以内立即为您开通本次保障吗？"
    if role == "reinforcement_session" and decl_mode == "implicit_induction" and s_plan.get("session_id", "").endswith("-03"):
        loc_text = f"在{env}" if env and env != "现场" else "在上次场景"
        return f"我查到您上次{loc_text}使用的是{app}{srv}，配置为{res}、时延{rtt}以内、持续{tp['duration']}。本次计划{start_t}至{end_t}，是否按这套配置开通？如果确认，我也可以将它设为以后该场景的默认配置。"
    if role in ["reinforcement_session", "reuse_session"]:
        return f"收到，我调取到之前登记的{app}{srv}配置：{res}、时延{rtt}以内，{start_t}开始、{end_t}结束，持续{tp['duration']}。确认按这套配置开通吗？"
    if trig_type == "time_periodic":
        p_desc = "每天固定时段" if period_type == "daily" else ("每月固定时段" if period_type == "monthly" else "每周例行时段")
        return f"收到，检测到您在{p_desc}需要保障，请问{app}{srv}是否按老规矩标准（{res} / 时延≤{rtt}）为您开通？"
    return f"收到，请问{app}{srv}是否按分辨率{res}、时延上限{rtt}的标准来为您开通？"


def get_fallback_agent_utterance(s_plan: dict, turn_idx: int, role: str, is_last: bool) -> str:
    tp = s_plan["target_params"]
    app, srv, res, rtt = tp["application_name"], tp["service_name"], tp["resolution"], tp["rtt"]
    tid = s_plan.get("template_id", "")
    b_type = s_plan.get("blueprint_type", "")
    ood_goal = s_plan.get("ood_goal", "")
    env = _sanitize_env(s_plan.get("scenario_env", ""), tp.get("start_timestamp", ""))
    small_memory = s_plan.get("small_memory", {})
    small_declaration = declaration_example(small_memory)
    evidence_mode = s_plan.get("small_memory_evidence_mode", "explicit_declaration")

    if tid == "T1-2":
        return f"抱歉，本智能助手仅提供手机移动网络加速与保障服务，暂不支持办理{ood_goal or '宽带光纤装维报修'}业务，建议您联系宽带专线处理。"
    if tid == "X-1":
        start_t, end_t = tp["start_timestamp"].split("日")[-1], tp["end_timestamp"].split("日")[-1]
        return f"好的，已为您成功受理{start_t}至{end_t}（持续{tp['duration']}）的{app}{srv}网络保障（{res} / 时延≤{rtt}）；另外关于{ood_goal or '手机话费充值与账单查询'}，目前暂不支持在线代办，请前往掌上营业厅查看。"
    if tid in ["T2-2", "T3-1"]:
        if turn_idx == 1:
            return f"收到，已确认是{app}{srv}保障。请问画质、时延和持续时长有什么具体要求？"
        if evidence_mode == "cross_turn_clarification" and turn_idx == 2:
            return clarification_question(small_memory)
        if evidence_mode == "cross_turn_clarification" and turn_idx == 3:
            return f"好的，已按您刚确认的含义记录，并为您开通{app}{srv}保障（{res} / 时延≤{rtt}）。祝您使用愉快！"
        memory_ack = f"并已记录您的习惯：{small_declaration}" if small_declaration else ""
        return f"好的，已为您开通{app}{srv}网络保障（{res} / 时延≤{rtt}），{memory_ack}祝您使用愉快！"
    if b_type == "experience_learning":
        return _fallback_agent_experience_learning(s_plan, turn_idx, is_last, tp)
    exp_res = _fallback_agent_experience_reuse(s_plan, turn_idx, env, tp)
    if exp_res is not None:
        return exp_res
    wm_res = _fallback_agent_working_and_override(s_plan, turn_idx, is_last, env, tp)
    if wm_res is not None:
        return wm_res
    return _fallback_agent_factual(s_plan, turn_idx, role, is_last, env, tp)


def _get_specialized_action_types(s_plan: dict, tid: str, b_type: str, turn_idx: int, is_last: bool) -> tuple[list[str], list[str]] | None:
    if b_type == "experience_learning":
        if turn_idx == 1:
            return ["Create_Intent_Request", "Inform_Slot"], ["Confirm_Slot"]
        if turn_idx == 2 and not is_last:
            return ["Correct_Previous_Input", "Modify_Request"], ["Confirm_Slot"]
        return ["Confirm_Slot"], ["Acknowledge"]
    if tid == "T1-2":
        return ["Create_Intent_Request"], ["Reject_Request"]
    if tid == "T1-3":
        return ["Create_Intent_Request", "Inform_Slot"], ["Acknowledge"]
    if tid == "T2-4":
        return (["Create_Intent_Request", "Inform_Slot"], ["Confirm_Slot"]) if turn_idx == 1 else (["Confirm_Slot"], ["Acknowledge"])
    if tid == "X-1":
        return ["Create_Intent_Request", "Inform_Slot"], ["Acknowledge", "Reject_Request"]
    if tid in ["T2-2", "T3-1"]:
        if turn_idx == 1:
            return ["Create_Intent_Request", "Inform_Slot"], ["Request_Slot"]
        if s_plan.get("small_memory_evidence_mode") == "cross_turn_clarification" and not is_last:
            return ["Inform_Slot"], ["Request_Disambiguation"]
        return (["Confirm_Slot"], ["Acknowledge"]) if turn_idx > 2 else (["Inform_Slot"], ["Acknowledge"])
    if tid in ["T2-5", "T2-3"]:
        if turn_idx == 1:
            return ["Create_Intent_Request", "Inform_Slot"], ["Confirm_Slot"]
        if turn_idx == 2 and not is_last:
            u_act = ["Confirm_Slot", "Modify_Request"] if tid == "T2-5" else ["Correct_Previous_Input", "Inform_Slot"]
            return u_act, ["Confirm_Slot"]
        return ["Confirm_Slot"], ["Acknowledge"]
    if tid == "T2-6":
        if s_plan.get("is_disambiguation", False):
            if turn_idx == 1:
                return ["Create_Intent_Request", "Inform_Slot"], ["Request_Disambiguation"]
            return (["Confirm_Slot", "Inform_Slot"], ["Confirm_Slot"]) if turn_idx == 2 else (["Confirm_Slot"], ["Acknowledge"])
        if turn_idx == 1:
            return ["Create_Intent_Request", "Inform_Slot"], ["Confirm_Slot", "Request_Slot"]
        return (["Inform_Slot"], ["Confirm_Slot"]) if (turn_idx == 2 and not is_last) else (["Confirm_Slot"], ["Acknowledge"])
    if tid == "T2-7":
        return (["Modify_Request", "Inform_Slot"], ["Confirm_Slot"]) if turn_idx == 1 else (["Confirm_Slot"], ["Acknowledge"])
    if tid == "T2-8":
        return ["Create_Intent_Request"], ["Acknowledge"]
    if tid == "T2-9":
        if s_plan.get("round_count") == 3 and turn_idx == 2:
            return ["Inform_Slot"], ["Confirm_Slot"]
        return (["Create_Intent_Request", "Inform_Slot"], ["Confirm_Slot"]) if turn_idx == 1 else (["Confirm_Slot"], ["Acknowledge"])
    if tid == "T2-10":
        return (["Create_Intent_Request", "Inform_Slot"], ["Confirm_Slot"]) if turn_idx == 1 else (["Confirm_Slot"], ["Acknowledge"])
    return None


def get_normalized_action_types(s_plan: dict, turn_idx: int, role: str, is_last: bool, raw_u_acts, raw_a_acts) -> tuple[list[str], list[str]]:
    tid = s_plan.get("template_id", "")
    b_type = s_plan.get("blueprint_type", "")
    spec = _get_specialized_action_types(s_plan, tid, b_type, turn_idx, is_last)
    if spec is not None:
        return spec

    if role == "evidence_session" and s_plan.get("round_count") == 3:
        if turn_idx == 1:
            return ["Create_Intent_Request", "Inform_Slot"], ["Request_Slot"]
        return (["Inform_Slot"], ["Confirm_Slot"]) if turn_idx == 2 else (["Confirm_Slot"], ["Acknowledge"])
    if s_plan.get("agility_factor") == 1.0 and s_plan.get("round_count") == 1:
        return ["Create_Intent_Request", "Inform_Slot"], ["Acknowledge"]

    is_implicit_reinf = (
        role == "reinforcement_session"
        and s_plan.get("declaration_mode") == "implicit_induction"
        and s_plan.get("session_id", "").endswith("-03")
    )
    u_acts = raw_u_acts
    if turn_idx == 1:
        if is_implicit_reinf:
            u_acts = ["Create_Intent_Request"]
        elif not u_acts:
            u_acts = ["Create_Intent_Request", "Inform_Slot"]
        elif isinstance(u_acts, str):
            u_acts = [u_acts]
    else:
        if role in ["reinforcement_session", "reuse_session"] or not u_acts:
            u_acts = ["Confirm_Slot"]
        elif isinstance(u_acts, str):
            u_acts = [u_acts]

    a_acts = raw_a_acts
    if is_last:
        a_acts = ["Acknowledge"]
    elif role in ["reinforcement_session", "reuse_session"]:
        a_acts = ["Confirm_Slot"]
    elif not a_acts:
        a_acts = ["Request_Slot"] if role == "evidence_session" else ["Confirm_Slot"]
    elif isinstance(a_acts, str):
        a_acts = [a_acts]
    return u_acts, a_acts
