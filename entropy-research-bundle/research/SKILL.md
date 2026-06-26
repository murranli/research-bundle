---
name: research
triggers:
  - "research"
  - "使用 research"
description: >-
  触发命令：使用 research，<你的调研问题>。例如：使用 research，评估小红书在本地生活搜索和决策场景是否有产品机会。
  信息降熵调研系统的主线编排器。把一句话预研需求，沿"目的判断→拆解→检索策略→检索执行→内容审计→报告撰写→报告生成→复盘交付"
  跑成一份带信源、可追溯的分析报告，应用于"商业投资→产品分析→设计落地"。
  只要用户提出调研/预研/竞品分析/产品分析/市场研究/可行性判断/"帮我研究/对比/评估某产品·公司·行业"
  一类需求，或想从中途（已有子问题/已有资料/拿约束直接做设计）起步，就使用本 skill。
  它通过状态文件契约调度 7 个子 skill；实际检索工具由用户的运行环境决定，可使用 Agent-Reach 或其他等价工具。
---

# research · 信息降熵调研系统主线编排器（v2.0）

你是这条调研流水线的**指挥**。你不亲自做拆解/检索/写报告，而是：判断入口 → 按状态机依次唤起子 skill → 守住审计回环与预算边界 → 最终交付。子 skill 之间不靠对话传话，全部通过**状态文件契约**在磁盘交接。

## 0. 动手前必读

执行任何一步之前，先读 `../_shared/state-contract.md`——它定义了 manifest（`run.json`）、产物文件、9 条契约规则。**这是所有协作的地基，不读会写坏接缝。** 共享脚本（在 bundle 的 `../_shared/`）是契约的执行层，用它们而不是手写文件操作：

- `state_io.py` —— 读写 manifest / 产物 / 审计日志的唯一入口
- `jsonsafe.py` —— 解析任何 LLM 或上游产出的 JSON（统一容错，禁止各 skill 自己写解析）
- `doctor.py` —— 把检索工具的 doctor/可用性输出转成渠道三档快照（内置 Agent-Reach 兼容解析）
- `render_report.py` —— 把 `05_outline.json` 渲染成自包含 HTML
- `deliver.py` —— 生成 `review.md` / `report.pdf` / `index.html` 三件套

> 路径约定：脚本与契约在 bundle 的 `_shared/`，相对本 skill 为 `../_shared/`。运行工作区（`.entropy/` 所在）默认是用户当前项目根，可 `--root` 指定。下文命令为简洁省略了 `../_shared/` 前缀，实际调用请补上（例：`python3 ../_shared/state_io.py ...`）。

## 1. 流水线与子 skill 映射

状态机固定 8 个 stage，挂在 7 个子 skill 上（目标拆解一个 skill 管 intent+decompose 两段）：

| stage | 子 skill（bundle 内同级目录） | 读入 → 写出（产物 key） |
|---|---|---|
| intent + decompose | `goal-decompose`（`research/目标拆解`） | 原始诉求 → `intent` + `questions` |
| strategy | `search-strategy`（`research/检索策略`） | `questions` + `channels` → `strategy` |
| retrieval | `retrieval-exec`（`research/检索执行`） | `strategy` → `retrieval_dir`（逐条返回） |
| audit | `content-audit`（`research/内容审计`） | `retrieval_dir` → `evidence` + 审计裁决 |
| compose | `report-compose`（`research/报告撰写`） | `evidence` → `outline` |
| render | `report-render`（`research/报告生成`） | `outline` → `report_html` |
| deliver | `review-deliver`（`research/复盘交付`） | 全程 → `deliverables/`（md + pdf + html） |

每个子 skill 都是**可独立触发**的：用户直接说"帮我把这个目标拆成子问题"会单独唤起 `goal-decompose`。子 skill 因此有**两种模式**——
- **独立模式**：用户直接调用，没有 run 上下文。就地完成、直接把结果给用户（或落一个文件），不要求建状态文件。
- **编排模式**：被本主线唤起（你会给它 `run_id` 与 `--root`）。此时严格走状态契约：读 manifest + 自己的输入产物，写自己的产物，`advance` 自己的 stage，并写审计日志。

你作为主线唤起子 skill 时，明确告知它"编排模式，run_id=…，root=…"，它才知道该走契约而非就地返回。

`review-deliver` 是**旁路角色**：它不在主链上占一个串行环节，而是在每个 stage 完成时被动消费 `audit_log.jsonl`，并在最后做终态交付。主链推进时，你只需保证每个 stage 收尾都写了审计日志（子 skill 内部已负责），交付环节自会拼装。

## 2. 启动：判断入口（支持灵活起步）

系统要能从任意位置进入。先判断用户给的是哪种起点，按契约第 4 节预填，再 `init`：

- **一句话宏观诉求**（"调研一下星巴克中国会员运营做得怎么样"）→ `entry=intent`，从头跑。
- **已有明确子问题 / 分析框架** → `entry=strategy`，把用户的目标与子问题轻量整理成 `00_intent.json` + `01_questions.json` 预填。
- **已有现成资料、只要审计+成文** → `entry=audit`，把资料结构化为 `04_evidence.json` 的 evidence 段预填。
- **拿约束直接做产品设计** → `entry=compose`，把约束整理进 `04_evidence.json` 或直接给 `05_outline.json` 的约束段。

同时判断 **scope（覆盖范围）**——注意它和执行流程是两条正交的轴（详见契约第 7 节）：执行流程永远走完整 8 段；覆盖范围则按用户真实诉求裁剪，**不是必须三段全跑**。

- 诉求只落一段（如"就做这家公司的投资判断"）→ `--scope investment`，`serves` 留空，**别外扩**到产品/设计。
- 跨段导向诉求（如"通过商业+产品分析，最终指导落地方案设计"）→ `--scope product --serves design`，并在 `--scope-note` 写明导向。此时连商业/产品分析都要**以"设计落地需要知道什么"为准**去拆解、定策略。

```bash
# 例 A：单段，从头跑
RID=$(python3 ../_shared/state_io.py init --request "判断这家公司值不值得投" --scope investment --entry intent)

# 例 B：跨段导向（分析最终服务于设计落地）
RID=$(python3 ../_shared/state_io.py init \
  --request "通过商业与产品分析指导我们的落地方案设计" \
  --scope product --serves design \
  --scope-note "所有证据都要能回答'这对最终落地设计有什么用'" --entry intent)

# 每个 run 开头给一次渠道快照
python3 ../_shared/doctor.py snapshot --run-id "$RID"
```

若自动 doctor 跑不出来（未安装对应检索工具、无代理或不在 PATH），用 `--from-file` 喂一份已保存的渠道可用性输出，或让用户先配置自己的检索工具。**`channels.unavailable` 里的渠道，下游策略一律不许用。**

## 3. 主循环：推进状态机

拿到 `RID` 后，反复执行：

1. 读 `python3 ../_shared/state_io.py next-stage "$RID"` 得到下一个待执行 stage。
2. 打开对应子 skill 的 `SKILL.md`，**按它的说明执行**（子 skill 只读自己声明的产物 + manifest，只写自己的产物）。
3. 子 skill 收尾时它会 `advance` 自己的 stage 为 `done` 并写审计日志。
4. 回到第 1 步，直到 `next-stage` 返回空。

**最小读取纪律（契约 R2）**：你作为指挥只读 manifest（小、便宜）。**不要**把各产物全文塞进自己的上下文"以防万一"——需要内容的是当前子 skill，它会自取。

## 4. 审计回环（核心新增，守边界）

`content-audit` 跑完会在 manifest 写 `audit.verdict`：

- `sufficient` → 正常进入 `compose`。
- `insufficient` → 想回环补检索。**回环前你必须验证边界（契约 R6）**：
  - 仅当 `audit.round < audit.max_rounds`（默认 3）**且** `budget.retrievals_used < budget.max_retrievals`（默认 20，前期测试值）才允许回环。
  - 允许回环：把 `audit.next_strategy_seed` 作为补充检索需求，`round += 1`，把 `strategy/retrieval/audit` 三个 stage 重置为 `pending`，回到 `strategy` 重跑（新检索 append 到 `03_retrieval/`，旧的保留）。
  - 触顶则**不再回环**：写 `budget.stop_reason`、把 `verdict` 当作 `sufficient_with_gaps` 处理，让 `open_gaps` 原样进报告的"局限与待补"。

```bash
python3 ../_shared/state_io.py log "$RID" audit loop_back "证据链不足：缺X维度的实测数据，第2轮回环"
python3 ../_shared/state_io.py set "$RID" audit.round 2
for s in strategy retrieval audit; do python3 ../_shared/state_io.py advance "$RID" $s pending; done
```

这条边界直接对应你 v1.0 的导向问题：**宁可留白等下一轮，也不能为把报告填满而把"权益体系对比"悄悄收缩成"会员权益对比"。** 原始诉求是不可妥协的基准。

## 5. 与检索工具层的交互模型（给 02/03 子 skill 的总纲）

本 bundle 只规定策略、记录与审计契约，不绑定具体检索实现。实际检索可由 Agent-Reach、OpenCLI、浏览器、网页抓取器或用户自己的工具完成。按用户期望的交互方式：**每条检索策略逐一进入可用渠道，每次返回都独立留存**，供下游消费。落地约定：

- `search-strategy` 产出"子问题 → 渠道（slug）→ 检索命令"的映射，渠道按契约 R9 选道：`channels.available` 里的渠道**一律同级**，按"子问题↔渠道匹配度"挑（如查财报走雪球/官方/全网搜索，而非小红书），`unavailable` 排除，并跨 2 类来源信度交叉验证。全网语义搜索、任意网页读取等能力由用户实际检索工具决定。
- `retrieval-exec` 逐条执行命令，**每次渠道返回 append 成一个 `03_retrieval/rNNNN.json`**（含 `req_id/channel/backend/cmd/query/raw/source_meta/fetched_at`），并 `budget.retrievals_used += 1`。先粗筛信源质量，再按信度分级，每个细分维度只深读 `budget.max_sources_per_dimension`（默认 2）个。

## 6. 收尾交付

`render` 完成后唤起 `07-review-deliver`，产出三件套到 `deliverables/`：① 工作流复盘 `review.md`（消费 `audit_log.jsonl`）；② 成品报告 `report.pdf`；③ GitHub Pages 可预览 `index.html`。然后用 `present_files`（若可用）把三件套交给用户。

## 7. 贯穿全程的纪律（来自 v1.0 问题清单）

- **JSON 解析只用 `jsonsafe.py`**，不许各 skill 各写一份（修"三份强度不一"）。
- **报告标题用观点、不用宽泛名词**（修"综合分析结论/权益类型与层次"这类）——这是 `report-compose` 的硬规则。
- **不死磕单一信源**、不为填满而堆砌——`04-audit` 与 `05-compose` 共同守。
- **检索式用中文引号**，避免破坏下游 JSON（`search-strategy` 沿用 v1.0 引号纪律）。

---

子 skill 目前是骨架占位（frontmatter + 职责声明 + 输入/输出契约），逐个填充时严格对齐本表与状态契约即可。
