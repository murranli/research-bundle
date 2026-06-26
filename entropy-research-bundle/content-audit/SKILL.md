---
name: content-audit
triggers:
  - "research/内容审计"
  - "使用 research/内容审计"
description: >-
  触发命令：使用 research/内容审计，<资料、证据或调研问题>。
  内容审计：把检索回来的正文清洗、提炼成带源证据，并对照原始诉求判断证据链是否扎实、能否回答课题；
  不足则指出缺口与建议换用的渠道，供主线在边界内回环补检索。
  当需要判断已有信息是否足以支撑某调研课题、把零散资料整理成带出处的证据、或决定是否要继续补充信源时使用；
  作为 research 主线 audit 段的执行体，是回环闭合的关键。
---

# 内容审计（audit）★v2 新增核心

合并 v1.0「内容清洗」+「内容提炼」，叠加新增的**证据链充分性裁决**。你把 raw 正文变成带源证据，并诚实回答一个问题：**这些证据够不够回答原始诉求？** 不够就指明缺口。你**不写报告**——那是 compose 的事。

## 两种运行模式
- **独立模式**：用户直接丢一批资料/链接内容要你"整理成带出处的证据并判断够不够答某问题"。就地产出证据 + 裁决回给用户。
- **编排模式**：被 research 主线唤起（给 `run_id`/`root`），严格走契约。

## 输入（编排模式）
- 读子问题：`state_io.py read-artifact <run_id> questions`（对照覆盖度）。
- 读检索记录：`03_retrieval/` 下全部记录，**重点取 `op=read` 的正文**；search 记录的 `filter` 用于了解哪些渠道已试过。
- 读 manifest：`scope`、`audit`、`budget`、`original_request`。
- 参考 `references/audit-rubric.md`。

## STEP 1 · 清洗（修 v1.0 旧问题）
对每条 read 记录，用脚本做机械去噪 + 按原文切块（**不做关键词计数、保原文序**）：
```bash
python3 ../_shared/clean.py 03_retrieval/r0004.json
# → {"blocks":[{"idx":0,"text":"…"}], "dropped_noise":N}
```
然后**由你语义判断**哪些块与该来源对应的子问题相关——不靠词频。入选块按 `idx` 保序。

## STEP 2 · 提炼带源证据
从清洗块提炼能回答子问题的证据，逐条绑定来源（按 `audit-rubric.md`）：
- 每条证据：`fact`/`inference` 分明，`confidence` 分级，关键单源证据标 `single_source=true`，冲突互记 `contradicts`。
- 溯源严格：`req_id` + `url` + `source_type`；原文定位 ≤15 字，不整段复制。

## STEP 3 · 覆盖度 + 裁决（核心）
对照 **`original_request` / standard_statement**（不是"已抓到的内容"）逐子问题判 covered/partial/uncovered，并查"是否诉求被悄悄缩水"（防导向问题）。综合给 `verdict`：
- `sufficient` → 进 compose。
- `insufficient` → 为每个缺口写 `gap` + `suggest_channels`（**尚未试过、按匹配度更优的渠道**），汇成 `next_strategy_seed`。

## `04_evidence.json` schema
```json
{
  "round": 1,
  "evidence": [
    {"eid": "e1", "qid": "q2", "claim": "理想唤醒时延约0.48s、问界0.52s（标准化测试）",
     "type": "fact", "confidence": "high", "single_source": false, "contradicts": [],
     "sources": [{"req_id": "r0004", "url": "…", "source_type": "权威二手", "locus": "时延0.48s"}]}
  ],
  "coverage": [
    {"qid": "q2", "status": "covered", "evidence": ["e1"], "note": ""},
    {"qid": "q3", "status": "partial", "evidence": ["e5"], "note": "仅单一社群源，缺跨屏延迟/失败率数据"}
  ],
  "audit": {
    "verdict": "insufficient",
    "reasoning": "q2/q1 covered；q3 仅单源且缺关键数据。",
    "scope_drift_check": "仍紧扣'指导交互设计'原始诉求，未收缩",
    "single_source_warnings": ["e5"],
    "open_gaps": [
      {"qid": "q3", "gap": "缺跨屏流转的延迟/失败率等可量化数据", "suggest_channels": ["youtube", "exa"]}
    ]
  }
}
```

## 落盘 + 回写 manifest（编排模式）
```bash
echo '<04_evidence.json>' | python3 ../_shared/state_io.py write-artifact <run_id> evidence - --root <root>
python3 ../_shared/state_io.py set <run_id> audit.verdict '"insufficient"' --root <root>
python3 ../_shared/state_io.py set <run_id> audit.open_gaps '<gaps json>' --root <root>
python3 ../_shared/state_io.py set <run_id> audit.next_strategy_seed '<seed json>' --root <root>
python3 ../_shared/state_io.py advance <run_id> audit done --root <root>
python3 ../_shared/state_io.py log <run_id> audit stage_done "verdict=insufficient，缺口1处(q3)" --root <root>
```
**始终把自己的 stage 推进为 done，并写诚实裁决——是否回环由主线按 R6（轮次<上限 且 预算未超）裁定，不要自己重置 stage。** 触顶时主线会把 insufficient 当作"带缺口进报告留白"。

独立模式：直接回证据清单 + 覆盖度 + 裁决，并说明缺口与建议渠道。

## 收尾自检
- 每条证据是否绑定来源、fact/inference 分明、单源是否标记？
- 覆盖度是否对照原始诉求（非缩水版）判定？
- insufficient 时 open_gaps 是否具体、suggest_channels 是否避开已试渠道？
- 清洗是否保了原文序、未用关键词计数？
