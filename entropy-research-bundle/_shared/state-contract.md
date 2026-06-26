# 状态文件契约 v2.0（State File Contract）

> 这是整条流水线的"共同接缝"。7 个子 skill 不通过对话上下文互相传话，**只通过磁盘上的状态文件交接**。
> 任何子 skill 在执行前先读 manifest（`run.json`）了解全局，只读自己声明的输入产物，只写自己负责的产物。这样既能省 token、又能中途入口、断点续跑、被人回溯。

---

## 1. 目录布局

每一次调研是一个独立的 **run**，落在工作区的 `.entropy/<run_id>/` 下：

```
.entropy/<run_id>/
├── run.json                 # ★ Manifest：唯一"总是被读"的小文件（状态机 + 指针 + 预算 + 渠道快照）
├── 00_intent.json           # 目标拆解：意图坐标 + 标准陈述句 + 约束
├── 01_questions.json        # 目标拆解：子问题 + 选用的分析模型
├── 02_strategy.json         # 搜索策略：维度 → 渠道 → 具体上游命令
├── 03_retrieval/            # 检索执行：每一次"渠道返回"独立成文件（append-only）
│   ├── r0001.json           #   单条返回 {req_id, channel, backend, cmd, query, raw, source_meta, fetched_at}
│   ├── r0002.json
│   └── ...
├── 04_evidence.json         # 内容审计：清洗+提炼后的带源证据 + 缺口 + 审计裁决
├── 05_outline.json          # 报告撰写：观点先行的内容组织（论点 + 证据引用 by req_id）
├── 06_report.html           # 报告生成：成品 HTML
├── audit_log.jsonl          # 复盘与交付：append-only 事件流，每个节点里程碑一行
└── deliverables/            # 复盘与交付：终态三件套
    ├── review.md
    ├── report.pdf
    └── index.html           # GitHub Pages 可直接预览
```

`run_id` 格式：`YYYYMMDD-HHMMSS-<4位随机>`，例如 `20260625-164230-a3f1`。

设计取舍：**为什么是"manifest + 分散产物"而不是一个大 JSON。** 一个大 JSON 每个环节都要整体读进、整体写回，token 随轮次线性膨胀，且回环时易并发覆盖。分散结构让每个子 skill 只碰自己那一片；检索原文这种重资产 append 成独立文件、用 `req_id` 引用，下游（审计/报告）按需取，不必把全文塞进上下文。

---

## 2. Manifest：`run.json`

这是契约的核心。它小、便宜、总是先读。Schema：

```json
{
  "run_id": "20260625-164230-a3f1",
  "schema_version": "2.0",
  "created_at": "2026-06-25T16:42:30+08:00",
  "updated_at": "2026-06-25T16:55:01+08:00",

  "original_request": "用户最初那句话（或中途入口时的输入）",
  "scope": {                                          // 覆盖范围 ≠ 执行流程，见第 7 节
    "primary": "investment | product | design",        //   诉求的核心落点（只此一段时，别外扩）
    "serves":  "investment | product | design | null", //   若是跨段诉求，最终要导向/服务的下游目的
    "note":    "一句话：分析应聚焦什么、以什么为终点导向"
  },
  "entry_stage": "intent",                            // 本次从哪一环进入（支持中途起步）
  "current_stage": "retrieval",                       // 状态机当前所在
  "language": "zh",

  "stage_status": {
    "intent":     "done | pending | skipped | failed",
    "decompose":  "pending",
    "strategy":   "pending",
    "retrieval":  "pending",
    "audit":      "pending",
    "compose":    "pending",
    "render":     "pending",
    "deliver":    "pending"
  },

  "artifacts": {                                      // 指针，不是内容
    "intent":        "00_intent.json",
    "questions":     "01_questions.json",
    "strategy":      "02_strategy.json",
    "retrieval_dir": "03_retrieval/",
    "evidence":      "04_evidence.json",
    "outline":       "05_outline.json",
    "report_html":   "06_report.html"
  },

  "audit": {
    "round": 0,                                       // 已完成的审计回环轮次
    "max_rounds": 3,                                   // 回环硬上限（防死循环）
    "verdict": null,                                   // "sufficient" | "insufficient" | null
    "open_gaps": [],                                   // 审计认定仍缺的证据点
    "next_strategy_seed": []                            // 回环时喂给"搜索策略"的补充检索需求
  },

  "budget": {
    "max_retrievals": 20,                              // 整个 run 的检索次数硬上限（前期测试值）
    "retrievals_used": 0,
    "max_sources_per_dimension": 2,                    // 每个细分维度最多读取的信源数（前期测试值）
    "stop_reason": null                                // 触顶时记录："max_rounds" | "max_retrievals" | null
  },

    "channels": {                                        // doctor 快照（由 _shared/doctor.py 生成）
    "snapshot_at": "2026-06-25T16:42:31+08:00",
    "available":   ["xiaohongshu","xueqiu","twitter","github","reddit","bilibili","youtube","v2ex","rss","exa","jina"], // ok，全部同级
    "unavailable": ["xiaoyuzhou","linkedin"]            // warn/off，本 run 不可用
  }
}
```

`stage` 取值固定为：`intent → decompose → strategy → retrieval → audit → compose → render → deliver`。
（目标拆解一个 skill 负责 `intent` 与 `decompose` 两段；报告撰写=`compose`、报告生成=`render`。）

---

## 3. 契约规则（所有子 skill 必须遵守）

- **R1 单一可信源**：每个 stage 的产物写到第 1 节约定的文件。下游只认文件，不依赖对话里转述的中间结果。

- **R2 最小读取**：执行前只读 `run.json` + 本 skill 在自己 SKILL.md 里声明的输入产物。**禁止**为"了解一下"而全量回读历史产物——那是 token 黑洞。

- **R3 引用而非内联**：检索原文、证据全文等重资产独立成文件。`run.json`、`05_outline.json` 等只存 `req_id` / 文件路径引用。需要全文时按引用现取。

- **R4 增量写入**：`03_retrieval/` 与 `audit_log.jsonl` 一律 append，不重写已存在的条目。回环产生的新检索追加新的 `rNNNN.json`，旧的保留（可追溯）。

- **R5 状态机推进**：`current_stage` / `stage_status` 是唯一推进依据。
  - 中途入口：`entry_stage` 之前的 stage 标 `skipped`，其依赖产物由用户输入预填（见第 4 节）。
  - 断点续跑：重进时按 `stage_status` 找到第一个非 `done` 的 stage 继续。

- **R6 审计回环边界**（修问题清单"为成型而偏离诉求"）：只有 `audit.round < audit.max_rounds` **且** `budget.retrievals_used < budget.max_retrievals` 时，审计判 `insufficient` 才允许回环。触顶则强制 `verdict=sufficient_with_gaps`，把 `open_gaps` 原样带进报告的"局限与待补"——**信源不足就留白，绝不为填满而堆砌或收缩原始诉求**。

- **R7 统一 JSON 解析**（修问题清单"三份容错、强度不一"）：任何子 skill 解析 LLM/上游产出的 JSON，一律调用 `scripts/jsonsafe.py`，不得各写各的。

- **R8 审计日志 append-only**：每个 stage 完成时，写一行到 `audit_log.jsonl`（见第 5 节），供"复盘与交付"消费。子 skill 不直接拼人类可读报告，只留结构化里程碑。

- **R9 渠道按匹配度选，不按优劣预排序**：`channels.available` 里的渠道**一律同级**。选哪个，依据"子问题↔渠道匹配度"——这条子问题最可能在哪个渠道拿到最有价值的信息（如查财报选雪球/官方披露/exa，而不是小红书；查真实口碑选社媒而非官方稿）。`channels.unavailable` 一律排除。仍要求**跨 2 类来源信度**（一手/二手/社群）交叉验证，但这是为信源独立性，与渠道无优劣之分。
  - **回环换道**：若某渠道本轮有效信息少，由 `04-content-audit` 在 `next_strategy_seed` 里点明缺口并**建议尚未尝试的其他渠道**；下一轮 `02-search-strategy` 据此换道再试（哪些渠道已试，从 `03_retrieval/` 的记录可得）。

---

## 4. 中途入口的预填约定（支持灵活起步）

系统要能"从中段起步"或"拿背景信息直接做设计"。约定：**缺位的上游 stage 标 `skipped`，但它的产物文件必须由入口环节按 schema 预填**，否则下游无所适从。

| 入口场景 | entry_stage | 预填什么 |
|---|---|---|
| 一句话宏观诉求 | `intent` | 无需预填，正常从头跑 |
| 已有明确子问题/分析框架 | `strategy` | 预填 `00_intent.json` + `01_questions.json`（可由入口处轻量生成） |
| 已有现成资料、只要审计+成文 | `audit` | 预填 `04_evidence.json` 的 evidence 段（把用户资料结构化为带源证据） |
| 拿约束直接做产品设计 | `compose` | 预填 `04_evidence.json` 或直接给 `05_outline.json` 的约束段 |

---

## 5. `audit_log.jsonl` 行格式

每行一个 JSON 对象，append-only：

```json
{"ts":"2026-06-25T16:50:00+08:00","stage":"retrieval","event":"stage_done","summary":"12 条返回，覆盖 4 维度","metrics":{"retrievals":12,"channels_used":["xueqiu","twitter"]},"cost_note":"…"}
```

字段：`ts`（东八区 ISO）、`stage`、`event`（`stage_start`/`stage_done`/`loop_back`/`budget_capped`/`error`）、`summary`（一句话人话）、`metrics`（结构化指标，可选）、`cost_note`（成本备注，可选）。

---

## 6. 调用底层脚本（契约的执行层）

- `_shared/state_io.py` —— 读写 manifest 与产物的唯一入口。CLI：
  - `init --request "<一句话>" [--scope ...] [--entry ...]` → 建 run、写初始 `run.json`、打印 `run_id`
  - `get <run_id> [<dotted.key>]` → 取 manifest 或某字段
  - `set <run_id> <dotted.key> <json_value>` → 原子更新字段并刷新 `updated_at`
  - `write-artifact <run_id> <artifact_key> <path_or_-为stdin>` → 落产物 + 回填 `artifacts` 指针
  - `log <run_id> <stage> <event> <summary>` → append 一行 `audit_log.jsonl`
- `_shared/jsonsafe.py` —— 统一容错解析（去 ```json 包裹、收敛裸英文引号、schema 兜底）。被各 skill import 或 CLI 调用。
- `_shared/doctor.py` —— 运行或读取检索工具的 doctor/可用性输出，解析为 `channels` 三档快照写入 manifest。
- `_shared/render_report.py` —— render 阶段执行层，把 `05_outline.json` 转成 `06_report.html` 并推进状态。
- `_shared/deliver.py` —— deliver 阶段执行层，生成 `review.md` / `report.pdf` / `index.html` 并推进状态。

子 skill 不自行 `open()` manifest 乱改；一律走 `state_io.py`，保证写入原子、`updated_at` 与指针自动维护。

脚本与本契约都放在 bundle 的 `_shared/`。编排器与各子 skill 通过相对自身位置的 `../_shared/` 调用；运行工作区（`.entropy/` 所在）默认是用户当前项目根，可用 `--root` 指定。

---

## 7. 覆盖范围 ≠ 执行流程（最易误解，务必分清）

这是两条正交的轴：

- **执行流程**＝固定的 8 个 stage（intent→…→deliver）。**任何一次 run 都走这条流程**，无论诉求大小。它回答"系统怎么干活"。
- **覆盖范围**＝"商业投资 → 产品分析 → 设计落地"这条**分析半径**。它回答"这次要分析到哪、为谁服务"，由用户诉求决定，**不是必须三段全跑的序列**。

聚焦原则（写进 `01-goal-decompose` 与 `02-search-strategy` 的硬约束）：

- **只落一段就别外扩**：用户要的是商业投资判断，就不要顺手把关联的产品分析、设计落地也做了。`scope.primary` 标该段，`scope.serves` 留空。
- **跨段诉求要带导向**：用户希望"通过商业+产品分析，最终指导落地方案设计"，则 `scope.primary` 是分析落点、`scope.serves="design"`。此时**连商业/产品分析都要以'设计落地需要知道什么'为导向**去定坐标、拆子问题、定检索策略——产出的每一条证据都应能回答"这对最终落地有什么用"。
- 判断口径：始终以用户的**真实终点**为基准来裁剪范围与组织产出，既不缩水（把"权益体系对比"做成"会员权益对比"），也不膨胀（没要设计却硬给设计建议）。

`scope` 写在 manifest 顶层，下游每个 stage 都应回看它来校准自己的颗粒度与取向。
