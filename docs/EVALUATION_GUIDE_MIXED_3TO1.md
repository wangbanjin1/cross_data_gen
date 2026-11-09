# 三层认知记忆与 3:1 混合数据集端到端评测指南

本文档说明如何在远端环境（如黄区）拉取 `cross_data_gen`、`mem_system`、`intent_rag` 三个关联仓库，并一键运行 **纯三层认知记忆数据集（`cognitive_samples`）** 与 **3:1 混合评测集（`cognitive_samples_mixed_3to1`）**。

---

## 一、三仓分支与目录结构约定

评测由三个同级仓库协同完成（代码已内置同级目录自动寻址，将三个仓库克隆在同一父目录下即可直接运行，无需修改代码中的路径）：

| 仓库名称 | 远端地址 | 评测分支 | 职责说明 |
| :--- | :--- | :--- | :--- |
| **`cross_data_gen`** | `https://github.com/wangbanjin1/cross_data_gen.git` | `feature/isolated-dual-rendering` | 存放纯三层认知数据集 `data/cognitive_samples`（35 画像 / 630 会话）与 3:1 混合数据集 `data/cognitive_samples_mixed_3to1`（35 画像 / 840 会话） |
| **`mem_system`** | `https://github.com/wangbanjin1/mem_system.git` | `feature/sliding-window-and-general-experience` | 三层认知记忆引擎（事实记忆、工作记忆、经验记忆 + Stage 0 静态预置隔离） |
| **`intent_rag`** | `https://github.com/wangbanjin1/intent_rag.git` | `feature/modular-refactor` | 多轮多意图理解主干、`MemoryBridge` 三层记忆桥接器与端到端批量评测脚本 |

推荐目录布局：

```text
workspace/
├── cross_data_gen/
│   ├── data/
│   │   ├── cognitive_samples/             # 原有纯三层认知记忆数据集 (35个画像, 630个会话)
│   │   └── cognitive_samples_mixed_3to1/  # 3:1 混合数据集 (35个画像, 840个会话 = 630原生 + 210同事样本)
│   └── scripts/
│       └── build_mixed_3to1_dataset.py    # 3:1 混合数据集构建脚本
├── mem_system/
│   └── src/memory_system/                 # 记忆系统核心源码
└── intent_rag/
    ├── configs/
    │   ├── config_memory_qwen37_plus.json # 主力评测配置 (qwen3.7-plus)
    │   └── config_memory_qwen38_flash.json# 快速评测配置 (qwen3.8-flash)
    └── tools/
        └── run_e2e_cognitive_samples.py   # 端到端联合评测入口脚本
```

---

## 二、远端环境拉取与更新命令

### 1. 首次克隆三个仓库

```bash
mkdir -p workspace && cd workspace

git clone -b feature/isolated-dual-rendering https://github.com/wangbanjin1/cross_data_gen.git
git clone -b feature/sliding-window-and-general-experience https://github.com/wangbanjin1/mem_system.git
git clone -b feature/modular-refactor https://github.com/wangbanjin1/intent_rag.git
```

### 2. 已有仓库拉取最新代码

```bash
cd workspace/cross_data_gen && git fetch origin && git checkout feature/isolated-dual-rendering && git pull
cd ../mem_system && git fetch origin && git checkout feature/sliding-window-and-general-experience && git pull
cd ../intent_rag && git fetch origin && git checkout feature/modular-refactor && git pull
```

### 3. 环境变量配置

```bash
# 设置百炼或黄区兼容 OpenAI 接口的 API Key
export BAILIAN_API_KEY="sk-xxx"

# 如需改用黄区内部模型网关，可直接修改 intent_rag/configs/config_memory_qwen37_plus.json 中的:
#   embedder.api_base / embedder.model
#   llm.api_base / llm.model
# 以及 mem_system/configs/default.yaml 中的 llm 与 embedding 配置。

# 若 mem_system 未放在 intent_rag 同级目录，可通过环境变量指定路径:
# export MEMORY_SYSTEM_DIR="/abs/path/to/mem_system"
```

---

## 三、端到端评测运行方法

所有评测命令均在 `intent_rag` 根目录下执行：

```bash
cd workspace/intent_rag
```

### 1. 冒烟验证（先跑 2 个用户画像 `001,002`，共 47 个会话）

```bash
python tools/run_e2e_cognitive_samples.py \
  --dataset_dir ../cross_data_gen/data/cognitive_samples_mixed_3to1 \
  --personas 001,002 \
  --config configs/config_memory_qwen37_plus.json \
  --out eval_results/run_mixed_3to1_p001_002 \
  --workers 2
```

### 2. 全量跑 35 个混合样本（`cognitive_samples_mixed_3to1`，共 840 个会话）

```bash
python tools/run_e2e_cognitive_samples.py \
  --dataset_dir ../cross_data_gen/data/cognitive_samples_mixed_3to1 \
  --config configs/config_memory_qwen37_plus.json \
  --out eval_results/run_mixed_3to1_all35 \
  --workers 5
```

### 3. 全量跑原有纯三层认知记忆样本（`cognitive_samples`，共 630 个会话，100% 向下兼容）

```bash
python tools/run_e2e_cognitive_samples.py \
  --dataset_dir ../cross_data_gen/data/cognitive_samples \
  --config configs/config_memory_qwen37_plus.json \
  --out eval_results/run_pure_cognitive_all35 \
  --workers 5
```

### 4. 命令行参数说明

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `--dataset_dir` | 自动探测 `cognitive_samples_mixed_3to1` | 指定待测数据集目录（可切换 `cognitive_samples_mixed_3to1` 或 `cognitive_samples`） |
| `--personas` | 空（默认跑全部 35 个画像） | 逗号分隔的画像编号，例如 `001,002,005` 或 `001,014,016` |
| `--config` | `configs/config_memory_qwen38_flash.json` | 意图理解模型配置文件路径（主力评测推荐 `configs/config_memory_qwen37_plus.json`） |
| `--out` | `eval_results/run_02_cognitive_samples` | 评测结果输出目录（自动生成 `summary.json` 与 `index.html`） |
| `--workers` | `5` | 画像级并发线程数（每个画像内部按时间线顺序串行执行，画像与画像之间并发隔离） |
| `--no_html` | `False` | 加上该参数则只输出 `summary.json`，跳过 HTML 报告渲染 |

---

## 四、评测输出产物与指标解读

评测完成后，在 `--out` 指定的目录（如 `eval_results/run_mixed_3to1_all35/`）下会生成：

1. **`summary.json`**：结构化全量评测报告，包含：
   - `session_jga` / `turn_jga`：整体会话级与轮次级 JGA 准确率；
   - `by_memory_tier`：按记忆层级拆分的准确率：
     - `factual_memory`：原生事实记忆（周期习惯、场景偏好、个性化黑话映射、单次临时覆写与恢复）
     - `working_memory`：原生工作记忆（历史工单复用、顺延改期、多笔工单消歧）
     - `experiential_memory`：原生经验记忆（慢路径多轮澄清归纳、快路径主动提前缓冲建议）
     - `external_distractor`：按 3:1 混入的同事数据集会话
   - `by_memory_role`：进一步拆分同事会话的三个子集表现：
     - `colleague_memory_session`：依赖 Stage 0 预写入静态 `Profile` 的同事会话
     - `colleague_record_session`：依赖 Stage 0 预写入静态 `Record` 的同事会话
     - `colleague_self_contained`：自闭环多轮澄清/双意图/纠错/取消会话
   - `users`：每个用户画像逐会话、逐轮次的 `user_utterance`、`memory_trace`（检索命中的三维记忆节点快照）、`llm_raw`、`preds`、`eval_details` 与会话后 `memory_snapshot`。
2. **`index.html` 与 `users/USER_XXX.html`**：
   - 浏览器打开 `index.html` 即可查看分维度指标看板，并点击任意用户查看逐轮对话、记忆检索命中详情与错题对比。
