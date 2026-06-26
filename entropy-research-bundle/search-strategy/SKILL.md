---
name: search-strategy
triggers:
  - "research/检索策略"
  - "使用 research/检索策略"
description: >-
  触发命令：使用 research/检索策略，<子问题或调研问题>。
  搜索策略：把子问题翻译成可执行的检索方案——做概念泛化、框定时空、判话题类型(A/B/C)、生成宽搜/精搜/证伪式检索式，
  并结合当前可用检索渠道，产出"子问题→渠道→检索命令"的映射，为检索执行做好准备。
  当需要为一组调研子问题设计检索策略/选择信源渠道/准备检索命令时使用；也作为 research 主线 strategy 段、
  以及内容审计判 insufficient 后回环补检索的执行体。
---

# 搜索策略（strategy）

合并 v1.0「采集指南」+ 渠道能力判读。你把子问题，变成下游 `retrieval-exec` 能照着跑的渠道级检索计划。**你不执行检索**，只出计划。

## 两种运行模式
- **独立模式**：用户直接给一组子问题求检索策略，无 run 上下文。就地产出计划直接回给用户，不建状态文件；渠道按"假设常见渠道可用"给，并提示真实可用性以运行环境的 doctor/渠道快照为准。
- **编排模式**：被 research 主线唤起（给 `run_id`/`root`）。严格走契约。

## 输入（编排模式）
- `python3 ../_shared/state_io.py get <run_id> --root <root>` 取 manifest，用其 `scope`、`channels`（三档快照）、`budget`、`audit`。
- 读子问题产物：`python3 ../_shared/state_io.py read-artifact <run_id> questions --root <root>`。
- **回环判断**：若 `audit.round > 0` 且 `audit.next_strategy_seed` 非空，本轮是补检索——**只针对 `audit.open_gaps`/`next_strategy_seed` 出计划**，不重做全部子问题。

参考文件按需读：`references/collection-playbook.md`（打法与检索式纪律）、`references/channel-map.md`（渠道能力与命令提示）。

---

## STEP 0 · 子问题筛选（控成本，相关度优先）
- 把全部子问题放一个池子，以 `original_request` + `scope` 为基准评估每条对**原始目的**的贡献度。
- 选相关度最高的 N 条（默认 ≤4），其余记 `dropped`。**依据是相关度，不是出现顺序**；某坐标可能一条都不入选。
- **预算感知**：N 受 `budget` 约束。粗算"本轮检索次数 ≈ Σ(每子问题渠道数 + 拟深读源数)"，确保不超 `budget.max_retrievals`。前期预算紧（20 次），N 取 3–4、每子问题渠道 2–3 个为宜。
- `scope.serves` 非空时，优先选"对最终下游目的最关键"的子问题。

## STEP 1 · 逐条出计划（仅入选子问题）
对每条入选子问题：
1. **概念泛化 + 时空范围 + 话题类型(A/B/C)**：按 `collection-playbook.md` 的 STEP A/B/C。
2. **检索策略 + 检索式**：按 STEP D/E。必含证伪式；宽搜/精搜+剔噪/证伪式各 ≥1 组；**精准匹配用中文引号 “”，严禁英文双引号**；按新鲜度倾向把年份写进精搜组。
3. **渠道映射**（核心，按 `channel-map.md` + 契约 R9）：
   - `channels.available` 里的渠道**一律同级**，不按渠道优劣预排序。选道只问一件事："这条子问题最可能在哪个渠道拿到最有价值的信息？" 先按话题类型框候选，再按匹配度挑。反例：查财报/财务数据别去小红书，应走雪球/官方披露/exa。`channels.unavailable` 排除。
   - 至少跨 2 类来源信度（一手/二手/社群）交叉验证——为信源独立性，与渠道优劣无关。
   - 每子问题给 2–3 个渠道。全网语义→ `exa`，任意网页→ `jina`，社媒/社区→对应 slug。
   - 每个渠道给 `op`（search/read）、`fit_reason`（为何该渠道最匹配本子问题）、面向该渠道改写的 `query`、`credibility`（一手/二手/社群）、以及 `cmd_hint`（来自 channel-map，标注"运行时以实际检索工具为准"）。
   - **回环轮（round>1）**：读 `audit.next_strategy_seed` 与 `03_retrieval/` 里已试过的渠道，**优先换用尚未尝试、对该缺口更匹配的渠道**。
4. **scope 取向**：`scope.serves` 非空时，写 `serves_orientation`——本子问题的检索如何朝下游目的收束（例：serves=design → 优先检索能指导落地决策的实测/方案/约束，而非泛市场综述）。

## `02_strategy.json` schema
```json
{
  "round": 1,
  "global_scope": {"time_range": "以当前日期为基准计算", "geography": "", "reasoning": "范围来自上游约束还是自主判断"},
  "selection": {
    "limit": 4,
    "total_candidates": 5,
    "selected": [{"qid": "q1", "relevance_reason": "为何与原始目的高度相关"}],
    "dropped": [{"qid": "q4", "drop_reason": "为何本期暂缓"}]
  },
  "plans": [
    {
      "qid": "q1",
      "sub_question": "原文",
      "dimension": "",
      "topic_type": "A | B | C",
      "key_concepts": [],
      "synonyms_expansion": [],
      "scope": "该子问题适用的时空范围",
      "search_strategies": ["精搜", "竞品并列搜索", "证伪式"],
      "search_queries": [
        {"type": "宽搜", "query": ""},
        {"type": "精搜+剔噪", "query": "（用中文引号 “” 锁定 + - 剔噪 + 年份）"},
        {"type": "证伪式", "query": "（搜反例/质疑/翻车/差评）"}
      ],
      "channel_plan": [
        {"channel": "exa", "op": "search", "credibility": "二手",
         "fit_reason": "为何该渠道最可能给出本子问题最有价值的信息",
         "query": "面向该渠道的查询", "cmd_hint": "mcporter call exa search '…'"},
        {"channel": "xiaohongshu", "op": "search", "credibility": "社群",
         "fit_reason": "", "query": "", "cmd_hint": "opencli xiaohongshu search '…'"}
      ],
      "serves_orientation": "（scope.serves 非空时）本条检索如何朝下游目的收束；否则空字符串"
    }
  ]
}
```
> `cmd_hint` 是参考模板；**权威命令由 `retrieval-exec` 运行时对着实际检索工具坐实**，渠道换代时模板可能变。

## 落盘（编排模式）
- `jsonsafe` 自检 → `write-artifact <run_id> strategy -` → `advance <run_id> strategy done` → `log <run_id> strategy stage_done "选 N 条子问题，映射 M 次渠道检索；预算预估 K 次"`。

独立模式：直接回计划 + 一句话说明（选了几条、覆盖哪些渠道、预算预估）。

## 收尾自检
- 入选是否按相关度（非顺序）？selected+dropped 是否覆盖全部子问题？
- 每条是否含宽搜/精搜/证伪式三型，且检索式无英文双引号、含操作符？
- 渠道是否按"子问题↔匹配度"选（非渠道优劣排序）、unavailable 是否排除、是否跨 2 类来源信度、每个渠道是否写了 fit_reason？
- 预算预估是否 ≤ `budget.max_retrievals`？
- 回环轮：是否只针对 open_gaps 出计划，未重做全部？
