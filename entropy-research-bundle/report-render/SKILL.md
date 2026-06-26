---
name: report-render
triggers:
  - "research/报告生成"
  - "使用 research/报告生成"
description: >-
  触发命令：使用 research/报告生成，<报告大纲或 run_id>。
  报告生成子 skill（主线 stage: render）。把内容大纲渲染为美观的 HTML，遵循一份轻量 Design System
  （字体/颜色/间距等基础约束）。由 research 主线在 render 阶段唤起。
---

# 报告生成（render）

「成品报告」节点的后半——美化展示，与内容组织解耦。

## 契约 I/O
- 读：产物 `outline`。
- 写：产物 `report_html`（`06_report.html`，自包含、内联 CSS、可选无 JS）；`advance render done` + 审计日志。

## 执行方式（编排模式）
优先使用共享执行脚本，避免每次由模型临场手写 HTML：

```bash
python3 ../_shared/render_report.py <run_id> --root <root>
```

脚本只做「`05_outline.json` → 自包含 HTML」的组件映射；事实判断、章节观点、留白均以上游 `report-compose` 的 `05_outline.json` 为准。若需要调整视觉风格，改脚本内 Design System，不回写内容判断。

## Design System（待定稿，保持轻量）
- 字体：中文友好正文字体 + 等宽用于数据/检索式。
- 颜色：主色 / 强调 / 事实 vs 推断的区分色 / 留白底色。
- 间距与层级：标题层级、卡片/对比表/评分条的统一间距。
- 可视化件：对比矩阵表、卡片、标签、CSS 评分条；事实/推断不同视觉标记；关键结论挂来源链接可核验。

> 后续可继续把 Design System 拆成 `assets/` 下的 CSS 变量 + 组件片段；当前最小闭环已由 `_shared/render_report.py` 承担。
