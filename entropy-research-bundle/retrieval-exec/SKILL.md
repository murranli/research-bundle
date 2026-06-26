---
name: retrieval-exec
description: >-
  检索执行：把搜索策略里的渠道计划逐条对着当前检索工具坐实成真命令并执行，每次返回独立留存为带源记录；
  边检索边做两层信源粗筛，按质量与来源信度分级，每个子问题维度只深读 2 个源取回正文，全程受预算硬上限约束。
  当需要按既定检索策略真正去各渠道抓取信息、筛选信源并取回正文时使用；作为 entropy-research 主线 retrieval 段的执行体。
---

# 检索执行（retrieval）

合并 v1.0「信源筛选」+ 与实际检索工具的真实交互。你照着 `02_strategy.json` 去各渠道**真发检索**，筛出值得读的源，取回正文。你**不清洗、不提炼、不下结论**——那是下游 `content-audit` 的事；你只负责"抓到 + 筛准 + 读回正文"。

## 两种运行模式
- **独立模式**：用户直接给一份渠道计划/一组查询要你去抓。就地执行、把结果整理回给用户。
- **编排模式**：被 entropy-research 唤起（给 `run_id`/`root`），严格走契约：读 strategy、逐条落 `03_retrieval/rNNNN.json`、累加预算、收尾推进。

## 输入（编排模式）
- 读 strategy：`python3 ../_shared/state_io.py read-artifact <run_id> strategy --root <root>`。
- 看预算：`python3 ../_shared/retrieval_io.py budget <run_id> --root <root>`。
- 参考 `references/source-filter.md`（两层筛选）、`../search-strategy/references/channel-map.md`（命令模板）。

## 前置 · 坐实命令（关键）
`02_strategy.json` 里的 `cmd_hint` 是**参考模板**，不是权威命令。执行前先确认当前运行环境如何调用这个渠道：
- 若使用 Agent-Reach，可跑 `agent-reach doctor` 看渠道当前 backend，或读它安装的 skill 文档拿当前调用方式。
- 若使用其他工具，则把每个 `channel_plan` 项改写成该工具的真实命令。
- 若当前环境没有可执行检索工具，本环节应停在计划与待执行记录，不要编造检索结果。

## 主循环 · 逐子问题执行
对 strategy `plans` 里每个子问题（qid），按 `source-filter.md` 边检索边筛：

**① search（找候选）**：对该 qid 的每个 `op=search` 渠道项，执行坐实后的命令，把返回落一条记录：
```bash
<真命令> | python3 ../_shared/retrieval_io.py add-record <run_id> \
   --qid q2 --channel xiaohongshu --op search --backend OpenCLI \
   --cmd "<真命令>" --query "<query>" --raw - --root <root>
```
脚本自增 `rNNNN`、累加 `budget.retrievals_used`、返回剩余预算。

**② 第一层方向粗筛**：只看返回里的 Title/Snippet/URL/Date，剔除跑题与噪音。把裁决补回该 search 记录：
```bash
python3 ../_shared/retrieval_io.py annotate <run_id> r0001 \
  --filter '{"candidates":[{"url":"…","direction_pass":true,"note":"…"},{"url":"…","direction_pass":false,"drop_reason":"营销软文"}]}' --root <root>
```

**③ 第二层质量&信度分级 + 选 2**：把该 qid 跨渠道通过方向粗筛的候选放一起，按 信息密度/具体性/独到性/来源信度 分档，去重，**挑出 ≤`budget.max_sources_per_dimension`（默认 2）个**深读，尽量跨 2 类来源信度互补。把选取结果记进对应 search 记录的 filter（`selected_for_read:true` + 理由）。

**④ read（深读取正文）**：对选中的源发 read（jina 读网页 / 渠道 note/post 读原帖），落 read 记录（带 `source_meta`）：
```bash
<read 真命令> | python3 ../_shared/retrieval_io.py add-record <run_id> \
   --qid q2 --channel jina --op read --backend "Jina Reader" \
   --cmd "<真命令>" --query "<源URL>" --raw - \
   --source-meta '{"url":"…","author":"…","date":"…","source_type":"权威二手"}' --root <root>
```

## 预算闸门（硬约束）
- 每次 add-record 前看剩余预算；脚本在 `retrievals_used >= max_retrievals` 时**拒绝写入**并置 `budget.stop_reason=max_retrievals`。
- 触顶即停止本轮检索，如实记录"哪些 qid 还没抓够"，交给收尾与审计判断——**不要超额硬抓**。
- 节流顺序：先保证每个入选 qid 至少有 search + 1 个深读；预算紧时削减"每 qid 第 2 个深读"，而非砍掉某个 qid。

## `03_retrieval/rNNNN.json` 记录结构（由脚本生成）
```json
{
  "req_id": "r0001", "qid": "q2", "channel": "xiaohongshu", "op": "search|read",
  "backend": "OpenCLI", "cmd": "<真命令>", "query": "<查询或源URL>",
  "fetched_at": "2026-06-25T…+08:00",
  "raw": "<渠道原始返回：search 为候选列表；read 为正文>",
  "source_meta": {"url": "…", "author": "…", "date": "…", "source_type": "一手|权威二手|社群|聚合"},
  "filter": {"candidates": [{"url":"…","direction_pass":true,"quality_tier":"高","selected_for_read":true,"reason":"…"}]}
}
```
> `raw` 原样保留（不在此清洗）。`filter` 仅 search 记录有。`source_meta` 主要给 read 记录，绑定来源供下游溯源。

## 收尾（编排模式）
- `advance <run_id> retrieval done`
- `log <run_id> retrieval stage_done "N 次检索（搜X读Y），覆盖 K 个qid，深读 M 源" --root <root>`（用 `retrieval_io.py list` 与 `budget` 取数）

## 收尾自检
- 每个入选 qid 是否至少有 search + 深读？深读是否 ≤2/维度、尽量跨 2 类来源信度？
- 跑题/噪音是否在第一层就弃掉（没浪费抓取）？低质源是否没硬凑深读？
- 每条记录是否带来源、raw 是否原样未清洗？预算是否未超 max_retrievals？
