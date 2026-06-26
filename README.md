# 信息降熵调研技能包（Research Bundle）

把一句模糊的调研问题，拆成可检索、可审计、可交付的研究报告。

这是一个 **Agent Skills 风格的技能组合**，包含目标拆解、检索策略、检索执行记录、证据审计、报告撰写、HTML/PDF 生成和工作流复盘。它只提供技能说明、状态契约和本地辅助脚本；使用哪个 Agent、哪个模型、哪个浏览器、哪个检索工具，由用户自己决定。

## 一条命令安装

```bash
curl -fsSL https://raw.githubusercontent.com/murranli/research-bundle/main/install.sh | bash
```

安装脚本会自动识别常见的 Agent Skills 目录，例如 Codex 和 Claude Code 的个人 skills 文件夹，并把技能包安装进去。

如果你想明确指定安装目录：

```bash
curl -fsSL https://raw.githubusercontent.com/murranli/research-bundle/main/install.sh | bash -s -- --target "$HOME/.claude/skills"
```

安装后，重启或刷新你的 Agent，然后可以这样调用：

```text
使用 entropy-research，评估小红书在本地生活搜索和决策场景是否有产品机会。
```

## 小白用户常见问题

### 1. 它和 Agent-Reach 是什么关系？

Research Bundle 是“研究流程和技能包”，Agent-Reach 是一种“可选的检索工具层”。两者不是绑定关系。

- 本技能包负责：拆问题、规划检索、记录证据、审计充分性、组织报告、生成交付物。
- Agent-Reach 或其他检索工具负责：真正去网页、社媒、社区或搜索渠道取回信息。

因此，Agent-Reach 更新、卸载或出现 bug，**不会改变本技能包的研究方法和文档表达**；但会影响“自动检索执行”这一步。如果检索工具不可用，Agent 应该把相关渠道标记为不可用，改用其他工具、手动资料或停在待检索状态，而不是编造结果。

### 2. 安装时，已经装了 Agent-Reach 和没装有什么区别？

安装过程没有区别。

安装脚本不会安装、修改或卸载 Agent-Reach，也不会写入任何登录态、Cookie、API key 或平台账号信息。它只复制本仓库里的技能目录。

区别只发生在运行时：

- 已安装 Agent-Reach：`retrieval-exec` 可以参考它的 doctor/渠道能力，把检索计划落成真实命令。
- 未安装 Agent-Reach：技能包仍然可以做目标拆解、检索策略、证据审计、报告生成；真检索部分需要用户提供其他工具、浏览器结果、已有资料，或稍后补跑。

### 3. 安装大约多久？会不会给本地造成负担？

通常是几秒到几十秒，主要取决于 GitHub 网络速度。

技能包本体很轻，目前 `entropy-research-bundle/` 约几百 KB。安装脚本只做这些事：

- 下载或读取本仓库
- 复制 9 个目录到 Agent Skills 目录
- 如果已有同名目录，先备份到 `.research-bundle-backup-时间戳/`
- 安装完成后清理临时下载目录

它不会启动后台服务，不会安装守护进程，不会修改 shell 配置，不会写入系统级目录，也不会配置任何第三方账号。卸载时删除对应 skills 目录即可。

## 会安装哪些目录

```text
entropy-research/      主线编排器
goal-decompose/        目标拆解
search-strategy/       检索策略
retrieval-exec/        检索执行记录
content-audit/         证据审计
report-compose/        报告撰写
report-render/         HTML 报告生成
review-deliver/        工作流复盘和最终交付
_shared/               状态契约和辅助脚本
```

这些 skill 通过运行工作区里的 `.entropy/<run_id>/` 状态目录交接信息。真实调研产生的 `.entropy/` 默认被 git 忽略，不会被提交到公开仓库。

## 运行要求

- 需要 Python 3，用于本地状态读写和报告生成脚本。
- 检索工具不强绑定。当前命令提示兼容 Agent-Reach/OpenCLI 风格渠道，也可以替换成用户自己的浏览器、搜索、抓取或 API 工具。
- 本仓库不包含账号 Cookie、API key、登录状态或检索凭证。

## 仓库结构

```text
install.sh
SECURITY.md
entropy-research-bundle/
  README.md
  _shared/
  entropy-research/
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
