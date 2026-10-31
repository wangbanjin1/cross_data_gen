# Project Memory & Architecture Guide (`cross_memory_data`)

本文件为 `D:\coding\cross_memory_data`（远端仓库：`https://github.com/wangbanjin1/cross_data_gen.git`，主干基线分支：`main`，基线 Tag：`v2.0.0-three-tier-baseline`）的项目级记忆与开发准则。

---

## 1. 项目定位与环境配置

- **智能体正式称谓**：本项目面向通信网络保障“提参数”场景，核心智能体统一命名为 **“联接”Agent**。
- **核心职责**：自动化生成高拟真、跨会话、长周期的多轮认知记忆评测数据集（涵盖**事实记忆**、**工作记忆**与**经验记忆**三大维度，储存在 `data/cognitive_samples` 与 `data/generated`）。
- **关联全景架构文档**：[`D:\coding\memory_system\docs\COGNITIVE_MEMORY_ARCHITECTURE.md`](../memory_system/docs/COGNITIVE_MEMORY_ARCHITECTURE.md) — 跨会话合成数据四步流水线与下游三层记忆系统完整规范。
- **Python 解释器**：`C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe`
- **对话渲染模型**：必须真实调用 **`deepseek-v4.1-flash` (`deepseek-flash`)** 等百炼 API 进行自然语言对话渲染，**严禁跳过 API 直接使用本地静态模板伪造输出**。
- **Git 分支工作流**：`main` 分支已归档当前三层认知记忆稳定基线（`v2.0.0-three-tier-baseline`）；后续任何新特性开发（如 `TODO #01 信息隔离的双向渲染`）**必须先从 `main` 单独拉取 `feature/<topic>` 分支进行开发验证**，严禁直接在 `main` 上裸写实验代码。

---

## 2. 核心数据架构与质量红线 (`Rule + Why + How to apply`)

1. **全面动态化与零固定值硬编码（Flexible Multi-Dimension Slots）**：
   - 画像生成器（`persona_generator.py`）、时间线规划器（`timeline_planner.py` / `dynamic_timeline_planner.py`）与经验预设（`trigger_presets.py`）中的所有槽位维度——包括 `duration`（如 60/90/120/150/180min 等）、起止时间窗、主支线应用与业务组合（`openlive` 开直播、`live` 看直播、`meeting`、`game` 等）、画质（`720p`/`1080p`/`4K`）、时延（`20ms`~`100ms`）、地点场馆与干扰项——必须具备随机性与多分布覆盖，严禁写死固定值（如严禁全局硬编码 `120min`）。
   - **Why:** 固定时长或固定时间窗会让下游评测退化为死记硬背，无法检验记忆系统对多分布参数的真实提取与泛化能力。
   - **How to apply:** 在采样每个习惯和工单时从多分布池随机抽取，并在 `qc_validator.py` 中强制校验算术自洽性（`end - start == duration`，含跨夜、顺延、提前预热偏移计算）。

2. **会话设计与最小意图表达自洽性**：
   - 用户发起保障或改期请求时，必须至少交代业务或上下文铺垫（例如会说“开直播保障”，而不会在无铺垫情况下突兀只说“开保障”或直接冒出孤立参数）。
   - **Why:** 缺少最小业务语义锚点的残缺输入在真实对话中不成立，且会导致多轮状态跟踪无法区分是“隐式习惯复用”还是“指令缺失”。
   - **How to apply:**
     - **事实记忆会话**：覆盖周期时间关联、默认参数、特定场景覆写、个性化表述映射教学与复用。
     - **工作记忆会话 (`working_record_*`)**：覆盖单笔直通与多笔同条件工单的两阶段消歧闭环（`working_record_disambig`）。
     - **经验记忆会话 (`experience_*`)**：快路径（Fast Path）Turn 1 交代完整基础业务信息测试一步闭环；慢路径（Slow Path）构造多候选分支生成引导澄清轨迹。

3. **治本铁律（Fix Generator Code First）**：
   - 任何时候发现生成的 JSON 样本或标准记忆状态快照（GT）存在逻辑瑕疵，必须修改 `src/` 下的生成器代码与校验器（`qc_validator.py`），绝不允许只手动修补单个产物数据文件。
   - **Why:** 手动改 JSON 产物会导致下次批量重跑生成时历史 Bug 再次复现，且无法保证跨用户样本的一致性。
   - **How to apply:** 先定位并修复 `persona_generator.py` / `dynamic_timeline_planner.py` / `qc_validator.py` 源码，先跑 3~4 个代表性用户样本完成联调验证后，再执行全量数据生成。

---

## 3. 术语与制图规范

1. **正规评测术语**：架构图、时序图、文档与代码注释中**严禁出现“Galgame”字样**，统一使用**“动态多分支模拟评测”**、**“快速闭环与多轮澄清路径对比评测”**或**“树状交互评测”**。
2. **Mermaid 可视化标准**：纯白底色（`#FFFFFF`）、所有节点与连线文字**全量加粗（Bold）**、连接线与箭头加粗（`stroke-width: 2px ~ 2.5px`）。
