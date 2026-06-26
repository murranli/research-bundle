# 桌面调研技能包

把一句模糊的调研问题，拆成可检索、可审计、可交付的研究报告。

这是一个 **Agent Skills 风格的技能组合**。它只提供技能说明、状态契约和本地辅助脚本；使用哪个 Agent、哪个模型、哪个浏览器、哪个检索工具，由用户自己决定。

## 一条命令安装

```bash
curl -fsSL https://raw.githubusercontent.com/murranli/research-bundle/main/install.sh | bash
```

安装脚本会自动识别常见的 Agent Skills 目录，例如 Codex 和 Claude Code 的个人 skills 文件夹，并把技能包安装进去。

## 触发命令

`research` 执行完整流程：目标拆解 → 检索策略 → 检索执行 → 内容审计 → 报告撰写 → 报告生成 → 复盘交付。

`research/环节名` 只执行局部能力。

```text
使用 research，评估小红书在本地生活搜索和决策场景是否有产品机会。

使用 research/目标拆解，评估小红书在本地生活搜索和决策场景是否有产品机会。
使用 research/检索策略，为以下子问题设计检索方案。
使用 research/检索执行，执行这份检索策略。
使用 research/内容审计，判断这些资料是否足以支撑报告结论。
使用 research/报告撰写，把这些证据组织成报告大纲。
使用 research/报告生成，把报告大纲渲染成 HTML。
使用 research/复盘交付，生成复盘和最终交付物。
```

## 安装目录与卸载

默认安装到本机已存在的 Agent Skills 目录，例如：

```text
~/.codex/skills
~/.claude/skills
```

会安装这些目录：

```text
research/
goal-decompose/
search-strategy/
retrieval-exec/
content-audit/
report-compose/
report-render/
review-deliver/
_shared/
```

卸载整套技能包：

```bash
curl -fsSL https://raw.githubusercontent.com/murranli/research-bundle/main/uninstall.sh | bash
```

卸载脚本只删除上述技能目录和旧版入口 `entropy-research/`，不会删除你工作区里的 `.entropy/` 运行记录、报告产物或任何第三方账号配置。

## 检索工具

推荐搭配 Agent-Reach 使用，它可以提供多渠道检索能力和 doctor 可用性检查：

[github.com/murranli/agent-reach](https://github.com/murranli/agent-reach)

但 Agent-Reach 不是强依赖。没有它时，你仍然可以使用本技能包做目标拆解、检索策略、证据审计和报告生成；检索执行可以换成浏览器、搜索引擎、API、手动资料或其他工具。

## 常见问题

### 1. 它和 Agent-Reach 是什么关系？

本技能包负责研究流程：拆问题、规划检索、记录证据、审计充分性、组织报告、生成交付物。Agent-Reach 或其他检索工具负责真正取回信息。

Agent-Reach 更新、卸载或出现 bug，不会改变本技能包的研究方法；但会影响自动检索执行。检索工具不可用时，Agent 应标记渠道不可用，改用其他工具或停在待检索状态。

### 2. 安装时，有没有 Agent-Reach 有区别吗？

安装过程没有区别。安装脚本不会安装、修改或卸载 Agent-Reach，也不会写入登录态、Cookie、API key 或平台账号信息。

区别只发生在运行时：有 Agent-Reach 时，`research/检索执行` 可以参考它的渠道能力落成真实命令；没有时，需要用户提供其他搜索工具、浏览器结果、已有资料，或稍后补跑。

### 3. 安装大约多久？会不会给本地造成负担？

通常是几秒到几十秒，主要取决于 GitHub 网络速度。技能包本体只有几百 KB。

安装脚本只复制技能目录；不会启动后台服务，不会安装守护进程，不会修改 shell 配置，不会写入系统级目录，也不会配置任何第三方账号。

## 仓库结构

```text
install.sh
uninstall.sh
SECURITY.md
entropy-research-bundle/
  README.md
  _shared/
  research/
  goal-decompose/
  search-strategy/
  retrieval-exec/
  content-audit/
  report-compose/
  report-render/
  review-deliver/
  examples/
```

## 安全提醒

任何技能包本质上都是给 Agent 阅读和执行的指令。安装前建议先浏览 `SKILL.md` 和 `_shared/` 脚本，尤其当你的 Agent 拥有执行 shell 命令的权限时。

公开 fork 前，请扫描并移除本地 `.entropy/` 运行记录、登录态、原始抓取内容和任何私密资料。详见 [SECURITY.md](SECURITY.md)。
