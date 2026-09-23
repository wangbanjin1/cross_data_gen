# 跨会话长程记忆数据集生成引擎 - 命令行使用手册与架构指南

本文档汇总了当前数据集生成引擎的所有命令行工具、配置文件规范、自定义原始画像替换指南，以及数据核心字段 `skeleton_signature` 的深度作用解析。

---

## 一、 快速上手：常用命令行一览

| 目标任务 | 推荐执行命令 | 说明 |
| :--- | :--- | :--- |
| **一键批量生成** | `python run.py` | 读取 `config.json` 默认配置执行（默认生成 20 个人物画像） |
| **按数量生成** | `python run.py --start 0 --count 10` | 从第 0 个画像开始，生成 10 个人物（共 150 个会话） |
| **更换原始画像** | `python run.py --input data/original/custom.json --count 5` | 指定自定义原始画像池，不修改全局配置 |
| **更换输出目录** | `python run.py --output data/experiment_v2 --count 5` | 将生成样本保存至指定的新目录 |
| **全量自动化校验** | `python run.py --verify` | 自动化遍历校验当前输出目录下所有样本的格式与动作完整性 |
| **校验指定目录** | `python run.py --verify --output data/experiment_v2` | 针对自定义输出目录执行严格 100% 格式验收 |
| **查看分布统计** | `python scripts/inspect_dataset.py` | 扫描画像骨架，统计显/隐模式与三大触发范式的分布比例 |

---

## 二、 配置文件 `config.json` 说明

项目根目录下的 `config.json` 是全局默认运行参数的集中管理文件：

```json
{
  "raw_persona_path": "data/original/mobile_network_personas_500.json",
  "output_dir": "data/generated",
  "batch_size": 5,
  "default_start_idx": 0,
  "default_count": 20,
  "model": "deepseek-flash",
  "base_url": "https://api.deepseek.com",
  "enable_thinking": false
}
```

### 字段说明：
- `raw_persona_path`: 原始人物画像池文件路径。若要永久替换初始画像，修改此项即可。
- `output_dir`: 生成产物的默认保存目录。
- `batch_size`: 对话渲染并发批次大小（默认 5 个会话为一个批次请求，大幅节约 API 往返耗时）。
- `default_start_idx`: 默认起始画像下标（从 0 开始）。
- `default_count`: 默认生成的画像数量。
- `model`: 调用的模型名称（默认为超低成本极速模型 `deepseek-flash`）。
- `enable_thinking`: 是否开启深度思考（默认 `false`，生成结构化对话无需 CoT，成本节约 95%）。

> **优先级原则**：命令行参数（如 `--input`, `--output`, `--count`）> `config.json` 配置值 > 代码内部缺省值。

---

## 三、 如何替换为自定义原始画像？

### 1. 原始画像格式兼容说明
系统内部已实现了数据结构的自适应解析，你的新原始画像 JSON 支持以下任意格式：
- **格式 A（顶层字典带 personas 键）**：
  ```json
  {
    "personas": [
      { "persona_id": "custom_001", "persona_summary": "职业与习惯描述...", ... }
    ]
  }
  ```
- **格式 B（顶层直接为列表）**：
  ```json
  [
    { "persona_id": "custom_001", "persona_summary": "职业与习惯描述...", ... },
    { "persona_id": "custom_002", "persona_summary": "职业与习惯描述...", ... }
  ]
  ```

### 2. 执行方式（任选其一）
- **方式 1：命令行即插即用（无需改配置文件）**
  ```powershell
  python run.py --input "D:/data/my_new_personas.json" --output "data/my_output" --count 10
  ```
- **方式 2：修改 `config.json` 后直接运行**
  修改 `"raw_persona_path": "D:/data/my_new_personas.json"`，随后执行：
  ```powershell
  python run.py
  ```

---

## 四、 核心字段深度解析：`skeleton_signature` 的作用是啥？

在每个会话的 `session_meta` 中，都有一个类似如下的指纹字符串：
```json
"skeleton_signature": "T1-1|1|1|I1:快手/看直播/1/direct/resolved|none"
```
或对于两轮记忆复用会话：
```json
"skeleton_signature": "T2-1|2|1|I1:抖音/开直播/1/memory_filled/resolved|none"
```

### 1. 结构各段切片详解

该签名字段用 `|` 和 `/` 分隔，是一套严谨的**会话拓扑指纹（Topological Signature）**：

| 段落切片 | 示例中的值 | 含义解释 |
| :--- | :--- | :--- |
| **第 1 段** | `T1-1` 或 `T2-1` | **会话模板协议 ID**（`T1-1` 为 1 轮直达型；`T2-1` 为 2 轮反问确认/记忆引导型；`T2-4` 为 2 轮显式纠正型） |
| **第 2 段** | `1` 或 `2` | **交互总轮数（Round Count）** |
| **第 3 段** | `1` | **包含的意图数量（Intent Count）** |
| **第 4 段** | `I1:快手/看直播/1/direct/resolved` | **意图核心特征五元组**：<br>• `I1`: 意图编号<br>• `快手`: 目标应用 (`application_name`)<br>• `看直播`: 目标业务 (`service_name`)<br>• `1`: 用户表达层级（1 为简明直接，5 为复杂指代）<br>• `direct` / `memory_filled`: **闭环路径 (`closure_path`)**（`direct` 为单轮直接完整说清；`clarified` 为通过追问填补；`memory_filled` 为借助历史跨会话记忆自动补全；`corrected` 为临时纠正覆盖）<br>• `resolved`: 意图最终达成状态 |
| **第 5 段** | `none` | **意图依赖关系（Relations）**（单意图为 none，多意图时记录依赖或共现关系） |

### 2. 为什么需要它？它的核心作用是什么？

1. **毫秒级结构指纹检索与去重**：
   - 在数万条的大规模对话语料库中，算法无需反序列化数千行深层嵌套的 JSON 树，直接依靠该字符串即可瞬间对会话的交互拓扑进行唯一索引、统计与去重。
2. **下游评测分桶切片（Benchmark Evaluation Slicing）**：
   - 评测跨会话记忆模型时，评测框架通过正则提取 `memory_filled`，即可一键切分出所有“依赖长程记忆补全”的硬核测试集，单独计算其参数召回准确率。
   - 对比分析 `T1-1`（零记忆单轮）与 `T2-1`（跨会话双轮）的意图辨识能力差异。
3. **数据集覆盖度与多样性审计（Diversity Audit）**：
   - 监控训练集和测试集中各应用、业务、闭环路径的交叉组合比例，防止训练数据在某种路径（如全是 direct 闭环）上发生过拟合。
4. **电信运营商与标准协议对齐**：
   - 完全对齐标准评测模板 `pilot100_0813` 规范，下游模型可无缝接入现有的评估脚本与评测流水线。

---

## 五、 代码分级架构与模块职责说明

为避免 Prompt、模版定义与业务逻辑互相交织耦合，系统采用清晰的分层解耦架构：

```
cross_memory_data/
├── run.py                          # 顶层命令行统一入口
├── config.json                     # 全局可调参数集中配置文件
├── src/
│   ├── config/                     # 【配置层】
│   │   ├── settings.py             # 全局配置类与环境变量加载 (Config)
│   │   └── __init__.py
│   ├── core/                       # 【核心领域状态与质检层】
│   │   ├── timeline_planner.py     # 15会话动态时间线规划器 (DynamicTimelinePlanner)
│   │   ├── memory_tracker.py       # 跨会话记忆演进追踪器与状态机 (MemoryTracker)
│   │   ├── qc_validator.py         # 100% 规则验证器 (QCValidator)
│   │   └── __init__.py
│   ├── generation/                 # 【生成与装配引擎】
│   │   ├── llm_client.py           # DeepSeek 客户端、Token计费与重试机制 (LLMClient)
│   │   ├── persona_generator.py    # 画像骨架扩充生成器 (PersonaGenerator)
│   │   ├── dialogue_generator.py   # 对话批量渲染引擎 (DialogueGenerator)
│   │   ├── session_assembler.py    # 8 大模版数据装配器 (SessionAssembler)
│   │   └── __init__.py
│   ├── pipeline/                   # 【流水线调度层】
│   │   ├── batch_pipeline.py       # 自动化流水线调度与检查点控制 (BatchPipeline)
│   │   └── __init__.py
│   └── templates/                  # 【模版与 Prompt 独立层（解耦抽离）】
│       ├── timeline_blueprints.py  # 15 会话生命周期序列蓝图配置模版
│       └── prompts/                # 纯净 Prompt 与兜底台词库
│           ├── persona_prompts.py  # 画像骨架扩充 Prompt 模版
│           ├── dialogue_prompts.py # 批量与单会话台词渲染 Prompt 模版
│           ├── dialogue_fallbacks.py# 各模版确定性兜底台词与动作规范
│           └── __init__.py
```

### 核心解耦优势：
1. **Prompt 纯净维护**：所有向大模型发送的指令、规则和 JSON Schema 集中在 `src/templates/prompts/` 中，调优台词或微调语气无需改动任何生成逻辑。
2. **模版装配隔离**：8 大模版（`T2-4`, `T2-2`, `T2-1`, `T1-2`, `T2-5`, `X-1`, `T2-3`, `T1-1`）的标准 JSON 结构与槽位流转逻辑全部封装在 `SessionAssembler` 中，新增或变更模版不影响渲染器。
3. **100% 平滑向下兼容**：顶层 `src/` 提供了兼容性 Facade 引用，现有外部工具脚本无需修改即可直接使用。

