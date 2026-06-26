---
name: review-deliver
triggers:
  - "research/复盘交付"
  - "使用 research/复盘交付"
description: >-
  触发命令：使用 research/复盘交付，<run_id 或已有调研产物>。
  复盘与交付子 skill（旁路 + 主线 stage: deliver）。全程消费审计日志形成可回溯的工作流复盘，
  并在收尾交付三件套：复盘 md、成品 pdf、GitHub Pages 可预览 html。由 research 主线在 deliver 阶段唤起。
---

# 复盘与交付（deliver）

抽离于主链的角色：过程中是"记录者"，收尾是"交付者"。替代 v1.0 不理想的「工作流档案」产出方式。

## 契约 I/O
- 读：`audit_log.jsonl`（全程里程碑）+ 各产物 + 产物 `report_html`。
- 写：`deliverables/review.md`、`deliverables/report.pdf`、`deliverables/index.html`；`advance deliver done` + 审计日志。

## 执行方式（编排模式）
优先使用共享执行脚本生成交付三件套：

```bash
python3 ../_shared/deliver.py <run_id> --root <root>
```

脚本会：
- 从 `audit_log.jsonl` 与各阶段产物生成 `review.md`；
- 把 `06_report.html` 复制为 GitHub Pages 可预览的 `index.html`；
- 优先用 LibreOffice/soffice 把 HTML 转成 `report.pdf`，若不可用则用 reportlab 从同一份报告大纲生成内容等价 PDF。

## 三件套
1. `review.md` —— 工作流复盘：把 audit_log + 各 stage 关键产物拼成给人回溯、为下次迭代提供"抓手"的 markdown（含每步判断依据、入选/淘汰理由、缺口、成本备注）。
2. `report.pdf` —— 成品报告 PDF（由 `06_report.html` 转，遵守 pdf skill 规范）。
3. `index.html` —— GitHub Pages 可直接预览的 html。

## 设计要点
- 不在过程里现拼人类报告——只读结构化 `audit_log.jsonl`，省 token、避免重复劳动。
- 复盘强调"可接管性"：即使部分信源未抓到，读者凭检索式/候选理由/淘汰记录也能自己接手。

> GitHub Pages 发布步骤仍属"发布公开内容"，执行前需用户确认；本脚本只在本地生成可发布文件，不主动发布。
