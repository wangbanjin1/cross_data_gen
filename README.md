# 跨会话多轮长程记忆数据集生成引擎 (Cross-Session Memory Data Generator)

本项目面向通信与智能助理的长程记忆演进、记忆抽取、记忆评测与意图保障场景，基于 500 个粗粒度人物画像自动化构建符合标准化 Schema 的跨会话多轮对话数据集。

---

## 🌟 核心特性与架构设计

1. **严格契合业务与通信标准 Schema**:
   - 会话结构完全对齐 `pilot100_0813` 规范：`session_id`, `user_id`, `reference_time`, `session_meta`, `event_sequence`, `intents`, `relations`, `slot_updates`。
   - 核心通信参数约束：`application_name`, `service_name`, `start_timestamp`, `end_timestamp`/`duration`, `resolution`, `rtt`。
2. **长程生命周期时间线规划 (15 会话 / 跨度 43 天)**:
   - 包含主线证据建立 (`evidence`)、主线强化复用 (`reinforcement`/`reuse`)、支线记忆 (`sub_01`, `sub_02`)、场景化事件纠正覆盖 (`event_override` 临时规则)、主线到期恢复 (`main_recovery`) 以及单次干扰项 (`distractor`)。
3. **记忆演进全链路追踪与评测基准支撑**:
   - 每个会话内嵌三元组字段：`memory_snapshot_before`（会话前生效记忆）、`memory_events_after`（记忆变更事件）、`gold_memory_state_after`（会话后真值快照）。
   - 伴生输出 `{persona_id}_memory_traces.json`，直接服务于下游模型**记忆萃取能力（Memory Distillation）的离线评测**。
4. **硬性会话闭环与行为约束 (Invariants)**:
   - 所有会话严格以 Agent 的最终答复收尾（包含 `Acknowledge`）。
   - 凡记忆强化与复用会话，严格要求 $\ge 2$ 轮交互：Agent 必须根据生效记忆向用户反问确认（`Confirm_Slot`），用户确认后 Agent 受理结束。
5. **极简低成本优化 (Batch Render & Thinking Disabled)**:
   - 针对 DeepSeek Flash 模型彻底关闭深度思考模式 (`thinking: disabled`)，消除数万冗余推理 token。
   - 采用 5-会话分批渲染 (`batch rendering`)，将单个人物（15 会话）的 API 调用次数从 16 次压缩至 4 次。
   - **单人物全量生成成本从 0.25 元 骤降至 0.016 元（成本降低 93%~97%）**，500 个人物全量生成仅需约 8 元人民币。
6. **自动化 5 重质检规则 (Automated QC)**:
   - 自动化检测时间单调性、参数白名单合法性、收尾完整性、强化轮次与确认行为、记忆快照逻辑一致性，自动输出 `qc_report.json`。

---

## 📂 项目结构

```text
cross_memory_data/
├── data/
│   ├── original/              # 原始 500 人物粗粒度画像库
│   ├── ref_template/          # 官方标准 Schema 与 Pilot 参考样例
│   ├── whitelist/             # 参数同义词词库、语体库与场景触发词库
│   └── generated/             # 生成产物目录（按人物文件夹隔离）
│       ├── mobile_persona_001/
│       │   ├── persona_skeleton.json   # 解耦画像骨架
│       │   ├── sessions.jsonl          # 15 个标准多轮会话
│       │   ├── memory_traces.json      # 记忆演进评测快照
│       │   └── qc_report.json          # 自动化质检报告 (100% 通过)
│       └── checkpoint.json             # 断点续跑进度
├── src/
│   ├── config.py              # 白名单配置及合法参数字典
│   ├── llm_client.py          # OpenAI SDK / DeepSeek API 封装（含成本统计与 Thinking 禁用）
│   ├── persona_generator.py   # 画像解耦与丰富度扩充模块
│   ├── dynamic_timeline_planner.py # 15 会话动态时间线与参数规划
│   ├── dialogue_generator.py  # 对话台词批量渲染与记忆注入
│   ├── memory_tracker.py      # 记忆生命周期演进跟踪器
│   ├── qc_validator.py        # 5 重质检验证器
│   └── batch_pipeline.py      # 批量流水线总控
├── scripts/
│   └── test_verification.py   # 全量质检验证脚本
├── run.py                     # 统一命令行入口
├── requirements.txt           # Python 依赖
├── .env.example               # 环境变量配置模板
└── README.md                  # 说明文档
```

---

## 🚀 快速上手

### 1. 环境安装
```bash
git clone https://github.com/wangbanjin1/cross_data_gen.git
cd cross_data_gen
pip install -r requirements.txt
```

### 2. 配置 API Key
方式一：设置环境变量
```bash
# Linux / macOS
export DEEPSEEK_API_KEY="your-deepseek-api-key"

# Windows PowerShell
$env:DEEPSEEK_API_KEY="your-deepseek-api-key"
```

方式二：创建根目录 `.env` 文件
```bash
cp .env.example .env
# 编辑 .env 中的 DEEPSEEK_API_KEY
```

### 3. 运行生成

- **生成指定范围人物**（如从第 0 个开始，生成 5 个人物）：
  ```bash
  python run.py --start 0 --count 5
  ```

- **全量质检验证**（自动扫描所有已生成人物目录并输出质检统计）：
  ```bash
  python run.py --verify
  ```

- **断点续跑**：
  若中途暂停，再次运行会自动读取 `data/generated/checkpoint.json`，跳过已完成的人物，无缝继续。

---

## 📊 质量与成本评测指标

- **质检通过率**: 100.0% (覆盖所有 5 大核心约束)
- **会话轮数分布**: 主线建联 2 轮，强化/复用严格 2 轮确认，干扰项 1 轮。
- **单人物平均耗时**: ~20 秒
- **单人物消耗 Tokens**: ~11,000 Tokens (其中 Output 约 4,000 Tokens)
- **单人物平均成本**: ~0.016 元人民币
