# -*- coding: utf-8 -*-
"""
ReasoningBank 结构化经验知识库 (ExperienceBank)
---------------------------------------------------------------
职责：
1. 落地 ReasoningBank 核心卡片规范，每条经验封装为标准三元组：
   (title, description, content) 以及适用边界（applicable_boundaries）与负向反例（negative_counterexamples）；
2. 维护通信保障场景下的专家避坑与元认知策略库；
3. 支持情境触发匹配（Trigger Context Matching），为智能体提供：
   - 通路 A：主动经验提议（Proactive Suggestion，如人流拥塞主动降画质保稳定）；
   - 通路 B：用户经验回溯（Empirical Recall，如恶劣天气经验方案调取）；
   - 通用策略迁移：指导跨期单据消歧、作用域隔离、多意图修正。
"""

import json
import re
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any


DEFAULT_EXPERIENCE_ENTRIES = [
    {
        "experience_id": "EXP_PREWARM_BUFFER_01",
        "title": "重大活动与大型现场提前30分钟网络预热起保经验",
        "description": "大型体育赛事、关键峰会直播或重要现场活动，设备连线与信道加固需要提前试机，直接按活动开始时间起保容易导致开场准备期卡顿掉流。",
        "content": "识别到大型赛事直播、重要现场活动等时，主动应用前置预热经验，将起保时间提前30分钟（例如14:00活动提前至13:30起保），保障时长相应延长30分钟，实现1轮极速闭环。",
        "trigger_conditions": {
            "keywords": ["赛事直播", "重大活动", "开幕式", "主旨演讲", "奥体中心", "峰会", "大型活动"],
            "risk_factors": ["开场网络拥堵", "设备准备期试机断流"]
        },
        "recommended_adjustments": {
            "start_offset_minutes": -30,
            "duration_add_minutes": 30,
            "strategy": "前置预热加固"
        },
        "applicable_boundaries": "适用于大型外场直播、开幕式、峰会论坛等重大活动现场；普通单人日常视频通话不适用此预热规则。",
        "negative_counterexamples": "若用户明确声明“必须精准从14:00开始开通，千万不要提前开”，则遵从用户指令。",
        "strategy_type": "prewarm_buffer"
    },
    {
        "experience_id": "EXP_MULTI_INTENT_PARTITION_01",
        "title": "多任务并行局部调整与时序因果隔离经验",
        "description": "一通对话中同时办理两笔保障任务时，若用户调整其中一个任务的时段或参数，容易错误波及另一个任务发生参数污染。",
        "content": "先锁定被修改的目标任务单元；局部更新仅作用于目标任务，另一关键任务严格保持原有配置冻结不变，防止多任务间参数相互污染。",
        "trigger_conditions": {
            "keywords": ["改一下", "调整", "不变", "另一个", "第二笔", "第一笔"],
            "risk_factors": ["多任务交叉污染", "修改扩散导致正常任务被篡改"]
        },
        "recommended_adjustments": {
            "rule": "严格按任务单元进行局部更新与隔离"
        },
        "applicable_boundaries": "适用于单次会话内包含 2 个及以上业务任务（如上午会议 + 晚上直播）的复合场景。",
        "negative_counterexamples": "若用户明确表示“两个任务全都改成同样的时间和规格”，则按用户指示统一更新。",
        "strategy_type": "multi_intent_partition"
    },
    {
        "experience_id": "EXP_CALENDAR_HOLIDAY_EXCEPTION_01",
        "title": "周期例行排期遇法定节假日自动顺延经验",
        "description": "每周或每月例行安排的保障如果恰逢国家法定节假日，公司通常无人办公，机械执行会导致空跑扣费。",
        "content": "识别到例行时段撞上法定节假日时，主动提醒避让，并将保障计划顺延至假期后的首个工作日办理，避免空跑浪费。",
        "trigger_conditions": {
            "keywords": ["国庆节", "中秋节", "元旦", "春节", "法定假日", "放假", "例行周会"],
            "risk_factors": ["放假期间无人办公空跑扣费"]
        },
        "recommended_adjustments": {
            "action": "顺延至节后首个工作日",
            "strategy": "节假日排期避让"
        },
        "applicable_boundaries": "适用于工作日固定周期例会类保障；节假日照常举办的文体演出或商业活动不适用避让规则。",
        "negative_counterexamples": "若用户明确说明“国庆期间虽然放假但有突发值班，必须照常开通保障”，则遵从指令按原排期办理。",
        "strategy_type": "holiday_avoidance"
    },
    {
        "experience_id": "EXP_ORDER_QUALITY_DISAMBIGUATION_01",
        "title": "基于历史工单网络质量日志的智能消歧经验",
        "description": "用户模糊提及'按上周办得好的那次规格来'，历史存在多个相似工单，机械反问工单流水号会增加用户查询负担。",
        "content": "调取历史工单的网络质量评估日志，主动剔除发生过卡顿或时延波动的异常单据，直接锁定全程零卡顿的高质量工单继承参数，快速闭环。",
        "trigger_conditions": {
            "keywords": ["上次好的", "不卡的那次", "体验好的", "上周顺畅的", "效果好的那次"],
            "risk_factors": ["误继承卡顿故障工单参数", "报工单号反问增加交互成本"]
        },
        "recommended_adjustments": {
            "rule": "基于质量日志过滤异常工单并锁定优质工单"
        },
        "applicable_boundaries": "适用于历史存在同类应用多次保障记录且网络质量存在差异的情境；若历史工单质量均一致，则需按时间就近原则办理。",
        "negative_counterexamples": "若用户直接报出确切工单编号（如“按单号REC-01来”），则直接按指定工单执行，无需比对质量日志。",
        "strategy_type": "quality_disambiguation"
    },
    {
        "experience_id": "EXP_OVERLAPPING_ORDER_RESOLUTION_01",
        "title": "新旧工单时段撞车无缝让路与时序重叠仲裁经验",
        "description": "新提交的保障与正在生效或已预约的旧单据在时间上有重叠冲突，直接报错拒绝受理会导致业务断档。",
        "content": "检测到新旧保障时段冲突时，自动在重叠交界点将前一工单提前结单让路，由新工单无缝接续保障，确保网络不中断且不重复计费。",
        "trigger_conditions": {
            "keywords": ["时间撞了", "提前接上", "时段冲突", "临时加单", "重叠", "接着开"],
            "risk_factors": ["单据冲突报错拒单", "重叠时段重复计费"]
        },
        "recommended_adjustments": {
            "action": "冲突交界点提前结单旧工单并无缝接续新工单",
            "strategy": "时序重叠仲裁"
        },
        "applicable_boundaries": "适用于同设备或同账号下新旧工单时段交叠的场景；不同独立设备的工单并行运行不受此仲裁约束。",
        "negative_counterexamples": "若用户明确要求“两笔单子同时并行开通，各走各的”，则不进行提前结单。",
        "strategy_type": "overlapping_resolution"
    },
    {
        "experience_id": "EXP_STADIUM_CONGESTION_01",
        "title": "极值与高密环境主动保流畅抗丢包经验",
        "description": "大型体育场馆、漫展或演唱会万人集聚场景下，现场人多容易发生网络拥挤，盲目开高画质易引发频繁卡顿转圈。",
        "content": "识别到体育场、会展中心等高密人流场景时，主动提议将画质调整为 720p、时延锁定在 30ms 以内，以保流畅优先策略确保网络推流零卡顿。",
        "trigger_conditions": {
            "keywords": ["体育场", "漫展", "演唱会", "会展中心", "奥体", "工体", "万人"],
            "crowd_density": "极度密集",
            "risk_factors": ["现场人多网络争抢", "突发丢包卡顿"]
        },
        "recommended_adjustments": {
            "resolution": "720p",
            "rtt_max": "30ms",
            "strategy": "保流畅优先"
        },
        "applicable_boundaries": "仅适用于公众聚集、现场人流过密的外场保障；私有专网独立保障的 VIP 场景不适用此降质规则。",
        "negative_counterexamples": "用户明确声明“无论多卡都必须保留 1080p 原画录制”时，智能体不得强行覆盖，应提示风险后遵从用户指令。",
        "strategy_type": "proactive_suggestion"
    },
    {
        "experience_id": "EXP_SEVERE_WEATHER_01",
        "title": "恶劣天气高衰减环境增强抗丢包加固经验",
        "description": "野外高山、海岛或偏远林区遇暴雨、强台风等恶劣天气时，无线信号衰落严重，数据传输易发生抖动与卡顿。",
        "content": "识别到大暴雨、强台风或高山极端天气时，调取抗恶劣天气加固方案，采用 720p 高清压缩与 30ms 时延收紧门限，优先保障音画不中断。",
        "trigger_conditions": {
            "keywords": ["大暴雨", "恶劣天气", "暴雨", "台风", "深山", "海上", "狂风"],
            "environment": "户外极端气候",
            "risk_factors": ["暴雨衰落", "信号抖动"]
        },
        "recommended_adjustments": {
            "resolution": "720p",
            "rtt_max": "30ms",
            "strategy": "抗衰落连续性优先"
        },
        "applicable_boundaries": "仅适用于外场直面恶劣天气的作业；室内封闭机房或有线接入环境不适用。",
        "negative_counterexamples": "若用户已处于室内固定有线网络，无需调用无线恶劣天气加固经验。",
        "strategy_type": "empirical_recall"
    }
]


class ExperienceBank:
    """ReasoningBank 结构化经验知识库管理器"""

    def __init__(self, custom_path: Optional[Path] = None, user_id: Optional[str] = None, **kwargs):
        self.user_id = user_id
        self.custom_path = Path(custom_path) if custom_path else None
        self.entries: List[Dict[str, Any]] = []

        if self.custom_path and self.custom_path.exists():
            self.load()
        else:
            self.entries = list(DEFAULT_EXPERIENCE_ENTRIES)

    def load(self) -> None:
        """加载自定义经验库"""
        if not self.custom_path or not self.custom_path.exists():
            return
        with open(self.custom_path, "r", encoding="utf-8") as f:
            self.entries = json.load(f)

    def save(self) -> None:
        """持久化保存经验知识库"""
        if not self.custom_path:
            return
        self.custom_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.custom_path, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, ensure_ascii=False, indent=2)

    def get_all_experiences(self) -> List[Dict[str, Any]]:
        """获取所有可用经验卡片"""
        return list(self.entries)

    def match_proactive_experience(self, scenario_env: str, task_name: str = "") -> Optional[Dict[str, Any]]:
        """
        根据作业现场与任务特征，检索是否触发【智能体主动提议（Proactive Suggestion）】卡片。
        例如：大型场馆、万人漫展 -> EXP_STADIUM_CONGESTION_01
        """
        combined_text = f"{scenario_env} {task_name}"
        for exp in self.entries:
            if exp.get("strategy_type") != "proactive_suggestion":
                continue
            kws = exp.get("trigger_conditions", {}).get("keywords", [])
            if any(k in combined_text for k in kws):
                return exp
        return None

    def match_empirical_recall(self, query_text: str) -> Optional[Dict[str, Any]]:
        """
        根据用户台词特征，检索是否触发【用户经验回溯（Empirical Recall）】卡片。
        例如：“按上次恶劣天气那套方案配” -> EXP_SEVERE_WEATHER_01
        """
        for exp in self.entries:
            if exp.get("strategy_type") != "empirical_recall":
                continue
            kws = exp.get("trigger_conditions", {}).get("keywords", [])
            if any(k in query_text for k in kws):
                return exp
        return None

    def find_by_id(self, experience_id: str) -> Optional[Dict[str, Any]]:
        """按 ID 检索经验卡片"""
        for exp in self.entries:
            if exp.get("experience_id") == experience_id:
                return exp
        return None

    @classmethod
    def select_persona_experiences(cls, persona: dict, target_count: int = 2) -> List[str]:
        """
        根据用户画像属性（职业身份、主线业务、触发场景等）动态筛选最适配的 1~2 个经验记忆卡片 ID。
        确保每个样本精准对应其业务特征，而非机械全量灌入所有经验。
        """
        user_id = persona.get("static_profile", {}).get("user_id", "")
        identity = persona.get("static_profile", {}).get("identity", "")
        summary = persona.get("persona_summary", "")
        category = persona.get("category", "")
        main_storyline = persona.get("dynamic_profile", {}).get("periodic_main_storyline", {})
        task_name = main_storyline.get("name", "")
        trig_cond = main_storyline.get("trigger_condition", "")
        combined_text = f"{category} {summary} {identity} {task_name} {trig_cond}"

        # 5类核心经验卡片的画像特征契合度关键词库
        EXPERIENCE_AFFINITY_KEYWORDS = {
            "EXP_PREWARM_BUFFER_01": [
                "讲者", "赛事", "直播", "演播", "开幕式", "主旨演讲", "体育", "露天", 
                "训练", "奥体", "峰会", "重大活动", "大本营", "巡回", "推流"
            ],
            "EXP_MULTI_INTENT_PARTITION_01": [
                "多任务", "调度", "回传", "转场", "双任务", "协调", "并行", "因果", 
                "交通", "物流", "巡逻", "执法", "多场景", "分段"
            ],
            "EXP_CALENDAR_HOLIDAY_EXCEPTION_01": [
                "例行", "周期", "周会", "顾问", "金融", "理财", "外访", "客户拜访", 
                "办公", "政务", "行政", "申报", "商贸", "工作日", "固定"
            ],
            "EXP_ORDER_QUALITY_DISAMBIGUATION_01": [
                "质量", "资金", "签署", "核验", "医疗", "研发", "工程", "勘查", 
                "试验", "测试", "影视", "设计", "高要求", "零卡顿", "电子签署"
            ],
            "EXP_OVERLAPPING_ORDER_RESOLUTION_01": [
                "社区", "社群", "公益", "组织者", "走访", "应急", "志愿者", 
                "临时加单", "紧凑", "群众", "突发", "协调会议", "连续"
            ],
        }

        scores = {}
        for exp_id, kws in EXPERIENCE_AFFINITY_KEYWORDS.items():
            score = sum(1 for kw in kws if kw in combined_text)
            scores[exp_id] = score

        # 稳定哈希兜底：若得分相同，根据 (score, md5(user_id:exp_id)) 稳定排序
        def sort_key(item):
            exp_id, score = item
            h = int(hashlib.md5(f"{user_id}:{exp_id}".encode()).hexdigest()[:4], 16)
            return (score, h)

        ranked = sorted(scores.items(), key=sort_key, reverse=True)
        selected = [item[0] for item in ranked[:target_count]]
        return selected

