---
name: goal-decompose
triggers:
  - "research/目标拆解"
  - "使用 research/目标拆解"
description: >-
  触发命令：使用 research/目标拆解，<你的调研问题>。
  目标拆解：把模糊的调研诉求定位为"研究对象×研究目的"靶向坐标与一句标准陈述句，再按 MECE 与
  "目的×维度分析模型矩阵"降维成一组可检索的子问题（每条带反正条件、不预设立场）。
  当用户给出预研/调研诉求需要厘清边界与子问题，或直接说"帮我把这个目标拆成可调研的子问题/确定分析框架/
  定位研究坐标"时使用；也作为 research 主线 intent+decompose 两段的执行体。
---

# 目标拆解（intent + decompose）

合并 v1.0「目的判断」+「问题拆解」。你把一句模糊诉求，变成下游能无歧义执行的"坐标 + 子问题"。你**不做调研、不下结论**，只做意图定位与拆解选型。

## 两种运行模式（先判断你在哪种）

- **独立模式**：用户直接找你拆目标，没有 run 上下文。就地完成两阶段，把两段 JSON 结果直接回给用户，**不建状态文件**。
- **编排模式**：被 research 主线唤起，会明确告诉你 `run_id` 与 `root`。此时严格走《状态文件契约》——读 manifest、写产物、推进 stage、写审计日志。

契约与脚本在 bundle 的 `../_shared/`（先读 `../_shared/state-contract.md`）。下文命令以编排模式为准；独立模式跳过所有 `state_io.py` 调用、改为直接输出。

## 输入
- 编排模式：`python3 ../_shared/state_io.py get <run_id> --root <root>` 取 manifest，用其中 `original_request` 与 `scope`。
- 独立模式：用户消息即输入；`scope` 若用户没说，按"只就事论事、不外扩"处理（`primary` 据诉求判断、`serves` 留空）。

---

## 阶段 A · intent（意图定位）

读 `references/coordinate-system.md`，然后按序：

1. **解析原始输入**：抽取关键实体（公司/产品/行业名）、时间范围、地域、其他约束。
2. **定位坐标**：选最匹配的 `object_category + object_dimension` 与 `purpose`，可跨类多选（多选时 `is_composite=true`，每个坐标单独写 `focus`）。
3. **套用 scope 聚焦**（对齐契约第 7 节，硬约束）：
   - 只就 `scope.primary` 这一段定坐标，**不要外扩**到用户没要的段（没要产品/设计就别加产品/设计坐标）。
   - `scope.serves` 非空（跨段导向）时，每个 `focus` 都要朝该下游目的取向。例：`serves=design` 时，"产品能力"坐标的 focus 不写成泛泛"了解产品力"，而写成"哪些产品能力维度是落地设计必须对齐的"。
   - 把取向落进产物的 `scope_alignment`。
4. **判可执行性**（`is_actionable`）：按 `references/coordinate-system.md` 的判定与反问规则。能合理补全的轻微缺省不反问；只在缺失导致方向性偏差时反问（≤3 个、封闭式）。
5. **多轮反问**：若本轮是对上一轮澄清的回复，按参考文件的 A/B/C 规则处理（合并/放弃/继续问）。
6. **写标准陈述句**（仅 `is_actionable=true` 时）。

### `00_intent.json` schema
```json
{
  "is_actionable": true,
  "is_composite": false,
  "standard_statement": "可执行时的一句标准陈述；不可执行时为 null",
  "targets": [
    {"object_category": "产品类|公司类|行业类",
     "object_dimension": "见坐标系中文取值",
     "purpose": "认知|监测|比较|判断|决策",
     "focus": "该坐标的具体聚焦点（已套 scope 取向）"}
  ],
  "constraints": {"subjects": [], "time_range": null, "geography": null, "other": []},
  "scope_alignment": {
    "primary": "investment|product|design",
    "serves": "investment|product|design|null",
    "orientation_note": "一句话：本次分析以…为导向；据此裁剪了/未外扩到哪些段"
  },
  "clarifying_questions": ["仅 is_actionable=false 时填，否则空数组"],
  "reasoning": "一句话定位依据/边界判断理由"
}
```

### 落盘与分支（编排模式）
- 先用 `jsonsafe` 自检 JSON 合法：`echo '<json>' | python3 ../_shared/jsonsafe.py -`
- 写产物：`echo '<json>' | python3 ../_shared/state_io.py write-artifact <run_id> intent - --root <root>`
- **若 `is_actionable=true`**：`advance <run_id> intent done`，`log <run_id> intent stage_done "意图已定位：<坐标摘要>"`，继续阶段 B。
- **若 `is_actionable=false`**：`advance <run_id> intent blocked`，`log <run_id> intent needs_clarification "诉求过宽，待澄清"`，**停在这里**——把 `clarifying_questions` 原样呈现给用户，等待回复后再以多轮规则重跑本 skill。**不要进入阶段 B，不要触发下游任何检索。**（这对应你 v1.0 的"模糊需求走反问不进下游"省钱闸门。）

---

## 阶段 B · decompose（降维成子问题）

仅在 `is_actionable=true` 时执行。读 `references/model-matrix.md`，对 `targets` 中每个坐标：

1. **选型**：按"目的码-维度码"查表得标配分析模型；命中灰格则借用邻近格并在 `model_index` 标注"无标配，借用 X-Y"。
2. **拆解**：以该模型的 MECE 维度为骨架，把 `focus`/标准陈述句沿模型维度穷尽拆成子问题。
3. **scope 取向**：`scope.serves` 非空时，每条子问题补 `serves_note`，写明"答出它对最终目的有什么用"；与终点无关的维度可省略并在 `decomposition_logic` 说明。

### 子问题三条硬性要求（逐条自检，宁缺毋滥）
1. 必须是**可检索的疑问句**，不能是关键词或陈述句。
2. 必须附 **falsification（反正条件）**：写明什么样的证据/数据会反驳这个子问题的隐含假设。
3. **不预设立场**：问句中不得暗含结论（不写"为什么 X 做得好"这种预设）。

### `01_questions.json` schema
```json
{
  "decompositions": [
    {
      "coordinate": "比较 × 产品能力",
      "object_category": "产品类",
      "object_dimension": "产品能力",
      "purpose": "比较",
      "model_index": "3-1",
      "selected_model": "功能对标矩阵（搭配 Kano）",
      "decomposition_logic": "一句话说明如何用该模型维度做 MECE 拆解",
      "sub_questions": [
        {"id": "q1",
         "dimension": "对应模型的哪个维度",
         "question": "可检索的疑问句",
         "falsification": "什么证据会反驳这个子问题的隐含假设",
         "serves_note": "（scope.serves 非空时）答出它对最终目的的用处；否则空字符串"}
      ]
    }
  ]
}
```
> `id` 全局唯一（q1, q2, …），下游搜索策略/检索/审计都靠它回指，务必稳定。`targets` 有几个坐标，`decompositions` 就几个对象。

### 落盘（编排模式）
- `jsonsafe` 自检 → `write-artifact <run_id> questions -` → `advance <run_id> decompose done` → `log <run_id> decompose stage_done "拆出 N 条子问题，覆盖 M 个坐标"`。

独立模式：把两段 JSON 直接回给用户，并附一句话说明（坐标摘要 + 子问题条数）。

---

## 收尾自检
- targets 的枚举值是否全部取自坐标系、无自创？
- scope 是否做到"不缩水、不膨胀"（没把对比做窄、没给用户没要的段）？
- 每条子问题是否都满足三条硬性要求？
- 编排模式下，产物是否已落盘、stage 是否已 advance、审计日志是否已写？
