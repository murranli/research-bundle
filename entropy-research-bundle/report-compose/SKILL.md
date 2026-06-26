---
name: report-compose
triggers:
  - "research/报告撰写"
  - "使用 research/报告撰写"
description: >-
  触发命令：使用 research/报告撰写，<证据、结论或约束>。
  报告撰写：把带源证据组织成观点先行的报告大纲——每章一个被提炼的核心观点 + 论证支撑，事实/推断分明、严守溯源，
  信源不足处留白而非堆砌，结论结构依课题性质自定义。只管内容组织与逻辑，不做美化。
  当需要把一批证据/调研结论组织成有观点、有论证、可读的报告结构时使用；
  作为 research 主线 compose 段的执行体；拿约束直接做设计时也可作入口。
---

# 报告撰写（compose）

「成品报告」节点的前半——**内容组织**。你把 `04_evidence.json` 的带源证据，组织成一份观点先行、论证扎实的大纲。你**不做美化、不写 HTML**——那是 render 的事；你只决定"说什么、按什么逻辑排"。

## 两种运行模式
- **独立模式**：用户直接丢一批证据/结论要你组织成报告结构。就地产出大纲回给用户。
- **编排模式**：被 research 主线唤起（给 `run_id`/`root`），严格走契约。

## 输入（编排模式）
- 读证据：`state_io.py read-artifact <run_id> evidence`。
- 读 manifest：`original_request`、`scope`、`audit.verdict`、`audit.open_gaps`（→ 留白素材）。
- 读 intent 产物的 `standard_statement`（判是否紧扣原始诉求）。
- 参考 `references/compose-rubric.md`。

> 进入 compose 时，audit 已判 `sufficient` 或被主线按 R6 转为"带缺口进报告"（`sufficient_with_gaps`）。后者把 `open_gaps` 当作 `limitations` 的留白素材。

## 流程
1. **定 report_type**（对比/评估/探索/决策…），据此选结论组织骨架（见 rubric 第五条）。
2. **提炼 thesis**：一句话回答原始诉求的核心判断。
3. **聚类证据成章**：把证据按"能支撑同一个核心观点"聚成章节，每章：
   - `claim`＝**观点性标题**（提炼，不用宽泛名词；见 rubric 正反例）。
   - `supports`＝若干论证要点，每点绑 `evidence_refs`、标 fact/inference 与 confidence，理由具体不堆大词。
   - `scope.serves` 非空时补 `design_implication`。
4. **处理薄弱与缺口**：仅单源支撑的观点，标低置信或并入 `limitations`，**不硬撑成章**；`open_gaps`/partial 覆盖 → `limitations` 留白，明说待补。
5. **自证不缩水**：`scope_fidelity` 写明大纲完整回应了原始诉求。

## `05_outline.json` schema
```json
{
  "report_title": "中性主题题名（美化在 render）",
  "thesis": "一句话核心判断，回应原始诉求",
  "report_type": "对比 | 评估 | 探索 | 决策支持",
  "sections": [
    {
      "sid": "s1",
      "claim": "观点性章节标题（提炼，非宽泛名词）",
      "supports": [
        {"point": "具体论证要点", "evidence_refs": ["e1", "e2"], "type": "fact", "confidence": "high"}
      ],
      "covers_qids": ["q2"],
      "design_implication": "（scope.serves 非空时）本章对下游目的的启示；否则空字符串"
    }
  ],
  "limitations": [
    {"gap": "缺口描述（来自 open_gaps / partial）", "affected_qids": ["q3"], "note": "留白待补，不强行下结论"}
  ],
  "scope_fidelity": "本大纲是否完整回应原始诉求、未收缩——一句话自证"
}
```

## 落盘（编排模式）
`jsonsafe` 自检 → `write-artifact <run_id> outline -` → `advance <run_id> compose done` → `log <run_id> compose stage_done "report_type=对比，N 章，M 条留白"`。

独立模式：直接回大纲 + 一句话说明（报告类型、章数、留白处）。

## 收尾自检
- 每个章节标题是否是观点（非"综合分析结论"这类宽泛名词）？
- 每个论证点是否绑了 evidence、fact/inference 是否分明、理由是否具体不堆大词？
- 单源观点是否没硬撑成章？缺口是否进了 limitations 留白（而非灌水填满）？
- thesis 与 scope_fidelity 是否回应原始诉求、未缩水？serves 非空时各章是否有 design_implication？
