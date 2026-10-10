"""小记忆语义规则及声明句渲染；候选和话术统一来自 expression_vault.json。"""

from src.config.settings import Config

_SEMANTIC_GUIDE = """【小记忆点语义规则】
小记忆点必须是脱离该用户就无法唯一确定含义的个性化表达。候选表达统一取自 expression_vault.json；普通同义词、数字换一种说法，只做语言归一化，不写入记忆。
1. 应用：只记用户明确声明的个人昵称；官方名、拼音和英文缩写只归一化。
2. 业务：仅主线可记住“在该主线场景中，用户未指定应用时，该业务默认使用的应用”。例如在日常开播主线中只说“开直播”时默认使用抖音；该默认值不得跨到支线，不把“打视频”“开会”等普通同义词登记成业务别名。
3. 画质：只记用户定义的模糊个人档位；“1080p原画”“720p高清”等确定表达只归一化。
4. 时延：只记用户定义的个性化体验表达；“50ms以内”“50毫秒以内”等确定表达只归一化。
5. 时长：只记“一会儿”“一下午”等无法直接换算的模糊表达；“俩小时”“一个半小时”“半小时”只归一化。
6. 周期：只记“老时间”等用户个性化时间表达；明确日期、星期和时刻只归一化。
只能使用规划结果指定的一项小记忆；应用与业务是发起保障意图的最小表达，除非已有“业务默认应用”记忆，否则用户必须表达应用和业务。画质、时延、时长、个性化周期表达只能省略对应参数，不能省略应用或业务，也不得指代整套配置；未显式声明时不得写入 alias_mapping。"""


def _templates() -> dict:
    return getattr(Config, "expression_vault", {}).get("small_memory_declaration_templates", {})


def _build_guide() -> str:
    examples = []
    for memory_type, templates in _templates().items():
        examples.append(f"- {memory_type}: " + " / ".join(templates))
    return _SEMANTIC_GUIDE + "\n【可参考声明话术（按实际 value/normalized 替换）】\n" + "\n".join(examples)


def declaration_example(item: dict) -> str:
    templates = _templates().get(item.get("type"), [])
    template = templates[0] if templates else None
    return template.format(
        value=item.get("value", ""),
        normalized=item.get("normalized_value", ""),
        scope=item.get("scope_condition", "主线"),
    ) if template else ""


def co_occurrence_example(item: dict) -> str:
    value = item.get("value", "")
    normalized = item.get("normalized_value", "")
    scope = item.get("scope_condition", "这类任务")
    templates = {
        "application_alias": f"这次用{normalized}，我平时顺口叫它‘{value}’，以后也这么说。",
        "service_default_app": f"这次{value}还是用{normalized}，以后在{scope}也照这个搭配来。",
        "resolution_alias": f"画质{value}就行，按{normalized}开，以后也照这个标准理解。",
        "rtt_alias": f"时延要{value}，上限按{normalized}控制，以后也照这个标准理解。",
        "duration_alias": f"这次开{value}，也就是{normalized}，以后照这个时长理解。",
        "period_alias": f"这次按{value}安排，也就是{normalized}，以后也照这个时间理解。",
    }
    return templates.get(item.get("type"), "")


def ambiguous_requirement(item: dict) -> str:
    value = item.get("value", "")
    h = abs(hash(value))
    m_type = item.get("type")

    if m_type == "resolution_alias":
        variants = [
            f"画质按‘{value}’来",
            f"画质只要‘{value}’",
            f"清晰度按‘{value}’开",
            f"画质标准按‘{value}’",
        ]
        return variants[h % len(variants)]
    elif m_type == "rtt_alias":
        variants = [
            f"时延按‘{value}’来",
            f"时延控制在‘{value}’",
            f"延迟按‘{value}’把控",
        ]
        return variants[h % len(variants)]
    elif m_type == "duration_alias":
        variants = [
            f"时长就‘{value}’",
            f"预计持续‘{value}’",
            f"时间开‘{value}’",
        ]
        return variants[h % len(variants)]
    elif m_type == "application_alias":
        variants = [
            f"应用就用‘{value}’",
            f"用‘{value}’开",
            f"指定用‘{value}’",
        ]
        return variants[h % len(variants)]
    elif m_type == "period_alias":
        variants = [
            f"时间按‘{value}’安排",
            f"时段照‘{value}’来",
        ]
        return variants[h % len(variants)]
    return f"就按‘{value}’来"


def clarification_question(item: dict) -> str:
    value = item.get("value", "")
    h = abs(hash(value))
    labels = {
        "application_alias": "应用",
        "resolution_alias": "画质档位",
        "rtt_alias": "时延上限",
        "duration_alias": "时长",
        "period_alias": "时间",
    }
    label = labels.get(item.get("type"), "这个说法")
    templates = [
        f"确认一下，您说的‘{value}’具体指哪个{label}？以后也按这个理解吗？",
        f"请教一下，您提到的‘{value}’具体对应哪档{label}？以后也帮您按这个记吗？",
        f"问一下，您说的‘{value}’具体是指哪种{label}？往后也按这套标准来吗？",
    ]
    return templates[h % len(templates)]


def clarification_answer(item: dict) -> str:
    normalized = item.get("normalized_value", "")
    h = abs(hash(normalized))
    labels = {
        "application_alias": "应用",
        "resolution_alias": "画质档位",
        "rtt_alias": "时延上限",
        "duration_alias": "时长",
        "period_alias": "时间",
    }
    label = labels.get(item.get("type"), "标准值")
    templates = [
        f"就是{label}{normalized}，以后就按这个理解，直接开通吧。",
        f"对，就是{label}{normalized}，往后都照这个标准记，开通吧。",
        f"指的就是{label}{normalized}，以后默认按这个来，直接保上吧。",
    ]
    return templates[h % len(templates)]


SMALL_MEMORY_GUIDE = _build_guide()
