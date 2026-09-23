# Persona 模板生成规范

## 1 概述

生成面向核心网 Agent 的用户画像（Persona）模板，用于跨 Session 记忆数据集生成。画像模板是 `corenet_personas.jsonl` 中的单条记录，描述一个真实用户画像。

画像模板可以通过两种方式获得：

| **方式说明适用场景** |                        |                                          |
| ------------ | ---------------------- | ---------------------------------------- |
| **人工设计**     | 按本规范手动编写 JSON          | 已有画像（如 `corenet_personas.jsonl` 中的 19 个） |
| **LLM 生成**   | 提供简短的人类角色描述，LLM 补全完整字段 | 需要批量生成新画像                                |

---

## 2 LLM 生成流程

独立脚本：`persona_generate.py`（命令行脚本，解耦于 pipeline）

```
persona_generate.py [--prompt "描述"] [--count N] [--mode generate|regenerate]
  │
  ├─ 读取 dataset_prepare/ 下的 3 个 JSON（app_config.json, app_map.json, support_matrix.json）
  ├─ LLM 接收系统 prompt（字段规范 + 可用 APP 列表）+ 可选基础描述
  ├─ LLM 输出完整 persona JSON (static_profile + dynamic_profile)
  ├─ 校验: 模板设计检查清单（apps数量/time_based覆盖/evidence类型等）
  ├─ 失败则重试（最多3次）
  └─ 写入 corenet_personas.jsonl (JSON 数组格式)
```

**Pipeline 调用**：`run.py` 只负责从 `corenet_personas.jsonl` 加载画像模板，不生成 personas。

**LLM 生成 vs 人工设计的区别**：

- LLM 生成时，apps 列表可能是通用名（如"视频APP"），后续 `persona_ground_truth.py` 的 `_resolve_app_name` 会 fallback 到 LLM 做映射
- 人工设计时，apps 直接用中文标准名，匹配更准确
- 两种方式的后续 pipeline 完全相同

### 2.1 使用示例

**方式1：自由生成**

```
python persona_generate.py --count 3
```

**方式2：带基础描述**

```
python persona_generate.py --count 3 \
  --prompt "一个经常出差的商务人士，主要用视频通话和导航" \
  --prompt "一个喜欢追剧的高中生，主要用短视频和追剧APP" \
  --prompt "一个退休老人，主要用微信视频和听书"
```

**方式3：覆盖全部**

```
python persona_generate.py --mode regenerate --count 10 --prompt "一个外卖骑手，主要用导航和外卖APP"
```

**方式4：指定资源目录和输出路径**

```
python persona_generate.py --resource-dir /path/to/dataset_prepare --output /path/to/output.jsonl
```

**输出**：生成完成后，LLM 调用的日志会显示 validation warnings（如果有），最终的 persona 文件会被写入 `output` 指定的路径（默认 `../PersonaMem-v2/data/corenet_personas.jsonl`）。

**使用 dataset_prepare/ 资源**：`persona_generate.py` 会自动读取 `dataset_prepare/` 下的 3 个 JSON：

- `app_config.json`：所有可用的 APP 名称和业务类型
- `app_map.json`：APP 中文名/英文名/别名
- `support_matrix.json`：APP × 业务 × 分辨率枚举

这些信息会被注入到 LLM prompt 中，让 LLM 知道能选哪些 APP，避免编造不存在的 APP。

---

## 3 模板结构

画像模板是 `corenet_personas.jsonl` 中的单条记录，包含两个顶层字段：

| **字段类型说明**        |        |                   |
| ----------------- | ------ | ----------------- |
| `static_profile`  | `dict` | 稳定画像（不变或极少变化）     |
| `dynamic_profile` | `dict` | 动态画像（随时间/场景/事件变化） |

---

## 4 `static_profile` 字段规范

| **字段类型必填说明**   |             |   |                                           |
| -------------- | ----------- | - | ----------------------------------------- |
| `identity`     | `str`       | 是 | 用户身份描述。需包含：职业/角色、核心活动特征、频率/时长、考核/目标       |
| `devices`      | `str`       | 是 | 使用的设备列表。需区分主力设备与备用设备                      |
| `apps`         | `list[str]` | 是 | 常用 APP 名称列表（中文）。建议 4-10 个，覆盖用户的核心使用场景     |
| `user_id`      | `str`       | 否 | 用户标识，格式 `USER_XXXX`                       |
| `subscription` | `dict`      | 否 | 套餐信息，包含 `plan_name`, `status`, `services` |

### 4.1 identity 写作规则

```
格式：身份 + 核心活动 + 频率/时长 + 考核/目标
示例：
  ✅ "抖音签约的全职户外主播，主要进行城市探店、夜市和商场直播，每周直播5-6场，每场2-4小时，有平台直播时长和活动场次考核"
  ❌ "全职户外主播，喜欢直播"
```

### 4.2 apps 选择规则

- 覆盖直播/视频类（主力）、沟通类、导航类、支付类等
- 与身份场景强相关，不要堆砌无关 APP
- APP 名用中文，需匹配 `app_config.json` 中的标准名

---

## 5 `dynamic_profile` 字段规范

### 5.1 `time_based`

| **字段类型说明** |       |                                |
| ---------- | ----- | ------------------------------ |
| key        | `str` | 时间段描述，格式如 "工作日下午（14:00-17:00）" |
| value      | `str` | 该时间段的典型活动和网络关注点                |

**设计原则**：

- 覆盖 3 个典型时段（下午/晚间/周末）
- 每个时段的活动 + 对应的网络需求要能映射到具体的 APP+业务
- 时间范围用括号标注具体时段

```
示例：
  "工作日晚间（18:00-22:00）": "在夜市、商业街或餐饮门店进行户外直播"
  "周末下午至晚间（14:00-21:00）": "在商场、景区或大型活动现场进行户外直播"
```

### 5.2 `scene_switch`

| **字段类型说明** |       |                   |
| ---------- | ----- | ----------------- |
| key        | `str` | 场景描述              |
| value      | `str` | 该场景下的行为模式 + 网络关注点 |

**设计原则**：

- 覆盖 3-4 个典型场景（不同环境/状态）
- 每个场景需说明：设备使用方式、主要关注的网络问题
- 至少包含一个"异常/应急"场景（主链路异常等）

```
示例：
  "夜市/商业街": "使用主力5G手机边走边播，主要关注人流密集区域的上行拥塞、小区切换和直播连续性"
  "主链路异常": "切换到备用5G手机或备用号码，关注直播恢复速度以及原有保障策略是否覆盖备用链路"
```

### 5.3 `role_change`

| **字段类型说明** |       |              |
| ---------- | ----- | ------------ |
| `from`     | `str` | 角色变化前的状态     |
| `to`       | `str` | 角色变化后的状态     |
| `trigger`  | `str` | 触发角色变化的原因/事件 |

**设计原则**：

- 记录 1 个有代表性的角色变化（业余 → 专业、换岗等）
- trigger 需说明为什么网络需求会改变
- 用于生成 Layer 3 changeable_gt（可变化事实）

```
示例：
  from: "业余探店博主，主要拍摄短视频后再上传"
  to: "抖音签约的全职户外主播，需要在不同地点完成实时直播"
  trigger: "签约后，内容形式从录制后上传为主转变为实时户外直播"
```

### 5.4 `event_driven`

| **字段类型说明** |       |               |
| ---------- | ----- | ------------- |
| `event`    | `str` | 事件描述          |
| `impact`   | `str` | 事件对网络/业务的具体影响 |

**设计原则**：

- 记录 1-2 个有代表性的事件（促销季、设备更换、活动赛事等）
- impact 需说明：网络需求的变化、对业务的影响、需要采取的保障动作
- 用于生成 Layer 3 changeable_gt（可变化事实），设置 valid_from/valid_to

```
示例：
  event: "双11商场促销活动期间进行品牌专场直播，并开启高清推流、嘉宾连麦和商品展示"
  impact: "高清推流和实时连麦使上行稳定性要求高于日常探店直播..."
```

### 5.5 `aliases`

| **字段类型说明**        |                        |              |
| ----------------- | ---------------------- | ------------ |
| `app_aliases`     | `dict[str, list[str]]` | APP 名 → 别名列表 |
| `service_aliases` | `dict[str, list[str]]` | 业务名 → 别名列表   |

**设计原则**：

- 每个常用 APP 提供 1-3 个自然别名
- 别名要真实：用户口语中实际会说的说法（如"抖"、"阿抖"）
- 排除子串别名（"抖"是"抖音"的子串，应选更长的"阿抖"）
- 至少包含 2 个 APP 别名 + 1 个业务别名

```
示例：
  "抖音": ["抖音", "抖", "阿抖"]
  "直播推流": ["直播", "推流", "开播"]
```

### 5.6 `time_expressions`

| **字段类型说明** |        |            |
| ---------- | ------ | ---------- |
| key        | `str`  | 模糊时间表达     |
| value      | `dict` | 解析后的具体时间信息 |

**设计原则**：

- 提供 2-3 个用户口语中的时间表达
- 覆盖 duration（时长）、relative（相对）、period（时段）等类型
- value 需包含具体的时间解析结果

```
示例：
  "一会儿": { "duration_minutes": 30, "type": "duration" }
  "下班前": { "relative_time": "before_work_end", "approximate": "18:00" }
```

### 5.7 `param_mappings`

| **字段类型说明** |        |               |
| ---------- | ------ | ------------- |
| key        | `str`  | 模糊质量表达（如"高清"） |
| value      | `dict` | 映射后的具体参数      |

**设计原则**：

- 提供 2-3 个用户口语中的画质/速度表达
- 每个表达映射到具体的 resolution 或时延值
- 这些映射将被生成 Layer 4 personalization_gt 中的 `expression_mappings`（quality_expression 类型）

```
示例：
  "高清": { "resolution": "1080p" }
  "流畅": { "resolution": "360p", "bitrate_kbps": 800 }
  "标清": { "resolution": "720p" }
```

### 5.8 `experience_preferences`

| **字段类型说明**              |                 |                                          |
| ----------------------- | --------------- | ---------------------------------------- |
| `app`                   | `str`           | APP 标准名（英文）                              |
| `service`               | `str`           | 业务标准名（英文）                                |
| `preferred`             | `dict`          | 首选体验参数组合                                 |
| `fallback`              | `dict`          | 备选体验参数组合                                 |
| `rejected`              | `dict` 或 `null` | 排斥的参数值                                   |
| `evidence`              | `str`           | 证据强度："explicit" / "behavioral"           |
| `support_count`         | `int`           | 证据数量（behavioral 时）                       |
| `scope`                 | `str`           | 偏好范围："long_term" / "temporary" / "scene" |
| `applicable_conditions` | `str`           | 适用条件描述                                   |

**设计原则**：

- 每个偏好覆盖一个 app+service 组合
- preferred/fallback/rejected 是"多参数组合"（resolution + 时延/上行），不是单参数
- evidence="explicit"表示用户明确说过，"behavioral"表示推断得出
- 必须包含 1 个 explicit + 1 个 behavioral，测试不同证据强度的记忆形成
- 用多参数组合偏好生成 Layer 4 `experience_param_preferences`，被反推为 MT（如 `multi_param_bundle`）

```
示例：
  {
    "app": "Douyin",
    "service": "live",
    "preferred": { "resolution": "1080p", "latency_ms": 60 },
    "fallback": { "resolution": "720p", "latency_ms": 120 },
    "rejected": { "resolution": "360p", "latency_ms": 200 },
    "evidence": "explicit",
    "scope": "long_term",
    "applicable_conditions": "户外直播场景"
  }
```

### 5.9 `app_service_preferences`

| **字段类型说明**                              |             |                                                    |
| --------------------------------------- | ----------- | -------------------------------------------------- |
| `type`                                  | `str`       | 偏好类型："service_to_app" / "app_to_service" / "combo" |
| `service` 或 `app`                       | `str`       | 已知的业务名或 APP 名（英文）                                  |
| `preferred_apps` 或 `preferred_services` | `list[str]` | 候选列表                                               |
| `excluded_apps`                         | `list[str]` | 排除列表                                               |
| `evidence`                              | `str`       | "explicit" / "behavioral"                          |

**设计原则**：

- 至少提供 1 个 `service_to_app`（只说业务→Agent 推断 APP）和 1 个 `app_to_service`（只说 APP→Agent 推断业务）
- preferred 列表中建议有 2-3 个候选，测试 Agent 是否能正确排序
- 生成 Layer 4 `app_business_preferences`，被反推为 MT（如 `service_to_app`、`app_to_service`、`app_service_combo`）

```
示例：
  {
    "type": "service_to_app",
    "service": "live",
    "preferred_apps": ["Douyin", "Kuaishou"],
    "excluded_apps": ["Weishi"],
    "evidence": "behavioral",
    "support_count": 8
  }
```

### 5.10 `conditional_preferences`

| **字段类型说明**      |        |                                       |
| --------------- | ------ | ------------------------------------- |
| `conditions`    | `dict` | 触发条件（location/event/time_period 等）    |
| `preference`    | `dict` | 条件满足时的偏好参数                            |
| `scope`         | `str`  | 条件范围："scene" / "temporary" / "global" |
| `evidence`      | `str`  | "explicit" / "behavioral"             |
| `support_count` | `int`  | 证据数量                                  |
| `valid_until`   | `str`  | 有效期（仅限 temporary 场景）                  |

**设计原则**：

- 覆盖 2-3 个不同条件场景（不同 location/event）
- 条件需具体、可验证（如"商场室内晚高峰"、"双11商场促销"）
- scope="temporary" 时必须有 valid_until
- 生成 Layer 2 `conditional_gt`（条件化真值），被反推为 MT（如 `temporary_preference`）

```
示例：
  {
    "conditions": { "event": "双11", "location": "商场" },
    "preference": { "resolution_preference": "1080p", "uplink_mbps": 15 },
    "scope": "temporary",
    "evidence": "explicit",
    "valid_until": "2026-11-12"
  }
```

---

## 6 模板设计检查清单

生成一个新画像模板时，按以下清单逐项核对：

| **#检查项验证方法** |                                                                              |                           |
| ------------ | ---------------------------------------------------------------------------- | ------------------------- |
| 1            | `static_profile.apps` 中至少 3 个 APP 能匹配 `app_config.json`                      | 运行生成器后 `frequent_apps` 非空 |
| 2            | `static_profile.identity` 包含角色+活动+频率                                         | 正则检查                      |
| 3            | `dynamic_profile.time_based` 覆盖至少 3 个时段                                      | 检查 key 数量                 |
| 4            | `dynamic_profile.scene_switch` 包含至少 1 个异常场景                                  | 检查 key 是否含"异常"/"备用"       |
| 5            | `dynamic_profile.aliases.app_aliases` 至少 2 个 APP 有别名                         | 检查嵌套 dict 长度              |
| 6            | `dynamic_profile.param_mappings` 至少 2 个画质表达                                  | 检查嵌套 dict 长度              |
| 7            | `dynamic_profile.experience_preferences` 至少 2 条，且含 explicit+behavioral       | 检查 evidence 字段            |
| 8            | `dynamic_profile.app_service_preferences` 包含 service_to_app + app_to_service | 检查 type 字段                |
| 9            | `dynamic_profile.conditional_preferences` 至少 1 条，含 temporary 类型              | 检查 scope 字段               |
| 10           | 整体一致性：apps + time_based + scene_switch 描述的活动与 identity 匹配                    | 人工审查                      |