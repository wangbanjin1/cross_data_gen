# 跨会话认知记忆数据集与引擎开发文档中心

> 本文档中心为**“联接”Agent**（面向通信网络保障**意图参数提取（提参数）**与闭环受理的核心智能体）跨会话认知记忆数据集与评测引擎的统一文档索引。

---

## 一、 文档分类导航与目录索引

```text
docs/
├── README.md                              # [本文件] 文档中心导航总览与索引
│
├── 记忆建模与数据集生成要求.md              # 【需求标准】第一层：事实记忆建模、正负样本生成要求与追问决策准则
├── 跨 Session 记忆数据集生成器思路.md        # 【系统设计】第二层：跨 Session 数据集生成器总体架构、流水线设计、GT建模与校验
│
├── specs/                                 # 【核心技术规范】
│   ├── cognitive_memory_dev_spec.md       # 【核心规范】第二层：“联接”Agent 三层认知记忆与双轨评测技术规范 (16~20轮)
│   └── persona_spec.md                    # 【基础规范】第三层：Persona 画像、主/支线与干扰项建模生成规范
│
├── guides/                                # 【研发与运行指南】
│   └── cli_usage.md                       # 第三层：命令行工具手册、批处理流水线与数据质检操作指南
│
└── archive/                               # 【历史沉淀与排查记录】
    ├── memory_evolution_proposal.md       # 第四层：认知架构立项方案 (RFC)：ReasoningBank 理论调研、α 因子推导与演进路线
    └── defect_triage_log.md               # 第四层：001~150 早期批次数据治理实录：21 项典型生成缺陷、排查根因与修复措施
```

---

## 二、 基础系统设计与需求准则

### 1. [记忆建模与数据集生成要求](记忆建模与数据集生成要求.md)
* **核心定位**：记忆建模规范与正负样本评测基准要求。
* **涵盖模块**：
  * **用户事实记忆边界**：静态事实（套餐/权益）与动态事实（个性化表达、选择偏好、时间规律、体验参数）；
  * **追问决策准则**：证据不足、多候选接近、冲突场景下的必须追问条件；
  * **四层 Ground Truth** 映射矩阵。

### 2. [跨 Session 记忆数据集生成器思路](跨%20Session%20记忆数据集生成器思路.md)
* **核心定位**：全流水线顶层设计文档。
* **涵盖模块**：
  * **流水线架构**：GT 构建 $\to$ Memory Targets 规划 $\to$ 时间线编排 $\to$ 逐 Session 渲染 $\to$ 评测与一致性校验；
  * **Session 角色 × 模板 × 轮数硬约束**；
  * **双层校验防御**：结构校验 R1~R8（纯规则）与内容校验 C1~C5（语义断言）；
  * **输入输出契约**：画像骨架（`skeleton.json`）与对话记录（`sessions.jsonl`）。

---

## 三、 核心技术规范 (Specs)

### 1. [“联接”Agent 三层认知记忆与双轨评测技术规范](specs/cognitive_memory_dev_spec.md) `[核心规范]`
- **业务定位**：面向“联接”Agent 通信保障场景下的**意图参数提取（提参数）**与闭环受理。
- **三层认知记忆架构**：
  - **事实记忆 (Factual Memory)**：用户长期配置画像（偏好、别名映射、长期默认参数）。
  - **工作记忆 (Working Memory)**：跨会话历史工单记录（单据复用、时间变更、多候选消歧）。
  - **经验记忆 (Experiential Memory)**：跨会话排障与提参策略库（`experiences.jsonl` 结构化卡片）。
- **五类经验记忆场景**：
  1. `EXP_MULTI_INTENT_PARTITION_01`：多任务并行分段隔离与局部调整。
  2. `EXP_PREWARM_BUFFER_01`：重大活动提前预热时间推算。
  3. `EXP_CALENDAR_HOLIDAY_EXCEPTION_01`：周期例行排期遇法定节假日顺延。
  4. `EXP_ORDER_QUALITY_DISAMBIGUATION_01`：基于历史工单运行质量的同日多单消歧。
  5. `EXP_OVERLAPPING_ORDER_RESOLUTION_01`：新旧工单时段重叠冲突裁决。
- **会话规模与拓扑**：单生命周期支持 **16 ~ 20 轮动态会话**演进（S01 ~ S20 动态 DAG 拓扑）。
- **双轨成败分支测试（Fast/Slow Branch Evaluation）**：
  - 经验应用测试会话首轮（Turn 1）基础参数自包含，重点评测模型能否识别场景特征并主动应用经验；
  - 对比 Fast Path（命中经验记忆：2~3 轮快速闭环）与 Slow Path（缺失经验记忆：4~5 轮澄清与纠偏）；
  - 交互轮数压缩增益：$$\text{TCG} = \frac{T_{\text{Slow}} - T_{\text{Fast}}}{T_{\text{Slow}}} \times 100\% \ge 50\%$$。

### 2. [Persona 画像与主/支线建模规范](specs/persona_spec.md) `[基础规范]`
- 规范 Persona 静态画像（职业、语言风格、身份背景）与动态画像（主线业务、支线保障、突发事件、干扰项池）。
- 保证生成画像的多样性、真实性与参数合理性。

---

## 四、 研发与运行指南 (Guides)

### 1. [命令行使用手册与流水线指南](guides/cli_usage.md)
- **端到端生成与质检**：`python run.py --input data/personas --output data/cognitive_samples --start 0 --count 5 --verify`
- **离线确定性生成**：`python run.py --input data/personas --output data/cognitive_samples --start 0 --count 5 --offline --verify`
- **单独执行质检**：`python run.py --output data/cognitive_samples --verify-only`

---

## 五、 历史沉淀与排查记录 (Archive)

- **[认知记忆演进提案规划 (memory_evolution_proposal.md)](archive/memory_evolution_proposal.md)**：三层认知记忆架构设计草案（RFC），包含 MemoryArena / ReasoningBank 理论参考、敏捷度因子 $\alpha$ 推导及 Phase 1~4 演进路线。
- **[早期生成排查与数据治理实录 (defect_triage_log.md)](archive/defect_triage_log.md)**：归档 001~150 批次生成中关于跨轮泄漏、时间倒灌、T1-1/T2-5 边界、口语自然度等 21 项典型缺陷的根因分析与修复方案。

---

## 六、 文档维护与更新准则

1. **唯一真值原则**：
   - 系统整体思路与需求基准以顶层设计文档为准；三层认知记忆实现以 `specs/cognitive_memory_dev_spec.md` 为准；`archive/` 保留历史排查与立项背景。
2. **命名规范**：
   - 新增文档采用英文小写加下划线命名，历史顶层文档保留原名以保障兼容。
3. **评测术语规范**：
   - 所有技术文档统一使用**“双轨成败分支测试（Fast/Slow Branch Evaluation）”**或**“动态多分支模拟评测”**。
4. **语言风格**：
   - 文档表述保持严谨、简洁；业务对话示例采用自然口语表达，避免生僻底层网管专业术语（如“空口切片”、“相控阵天线”）。
5. **Mermaid 制图规范**：
   - 纯白底色 (`#FFFFFF`)、粗体文字、加粗线条（`stroke-width: 2px`）。
