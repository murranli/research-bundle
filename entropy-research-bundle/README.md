# 信息降熵调研系统 v2.0 · Skill Bundle

这是 Research Bundle 的技能包本体。公开入口与安装说明见仓库根目录 `README.md`。

本目录保持 Agent Skills 风格组织：每个子目录都是一个可独立触发的 skill，`_shared/` 提供状态契约和执行脚本。主线 skill 通过磁盘状态文件把多个子 skill 连接成一条可审计的调研流水线。

## 结构

```text
entropy-research/      主线编排器：调度其余 7 个 skill
goal-decompose/        目标拆解：intent + decompose
search-strategy/       搜索策略：strategy
retrieval-exec/        检索执行：retrieval
content-audit/         内容审计：audit
report-compose/        报告撰写：compose
report-render/         报告生成：render
review-deliver/        复盘与交付：deliver
_shared/               状态契约、JSON 容错、doctor、HTML/PDF 渲染等共享脚本
examples/              脱敏示例
```

## 两条正交的轴

- **执行流程**：固定 8 段，`intent → decompose → strategy → retrieval → audit → compose → render → deliver`。
- **覆盖范围**：按用户诉求裁剪，可落在商业投资、产品分析、设计落地中的任一段或跨段导向。

流程保证可追溯，范围保证不跑偏。比如用户只要投资判断，就不要外扩到设计；用户说“分析最终指导设计落地”，则所有证据都要服务于设计取舍。

## 状态契约

所有编排模式下的交接都走 `.entropy/<run_id>/`：

- `run.json`：manifest 与阶段状态
- `00_intent.json`：标准化诉求
- `01_questions.json`：子问题
- `02_strategy.json`：检索计划
- `03_retrieval/`：逐条检索记录
- `04_evidence.json`：证据与审计
- `05_outline.json`：报告大纲
- `06_report.html`：报告 HTML
- `deliverables/`：最终 HTML/PDF/复盘

先读 `_shared/state-contract.md`，再改任何 stage 产物。

## 共享脚本

```text
_shared/state_io.py        状态读写唯一入口
_shared/jsonsafe.py        LLM JSON 容错解析
_shared/doctor.py          可用检索渠道快照
_shared/retrieval_io.py    检索记录与预算
_shared/clean.py           正文清洗与切块
_shared/render_report.py   05_outline.json → 06_report.html
_shared/deliver.py         review.md / report.pdf / index.html
```

快速自检：

```bash
cd entropy-research-bundle/_shared
python3 -m py_compile *.py
python3 -c "import jsonsafe, state_io, doctor; print('ok')"
```

## 检索渠道

本 bundle 不内置任何登录态、API key 或平台账号。`search-strategy` 会产出渠道级计划，`retrieval-exec` 记录执行结果；实际检索命令可由 Agent-Reach 或用户自己的检索工具完成。

`channels.available` 中的渠道应按“子问题与信源匹配度”选择，不按平台偏好排序。不可用渠道不得进入本轮策略。
