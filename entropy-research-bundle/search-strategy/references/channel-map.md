# 渠道能力映射表（search-strategy → retrieval-exec 共用）

> 把每个检索渠道（按规范 slug）映射到：能力、适配的话题类型、以及**命令提示模板**。
>
> ⚠️ 命令提示是 best-effort。**权威命令以运行时实际检索工具为准**，由 `retrieval-exec` 在执行时坐实，不要把这里的模板当成铁律。
>
> **选道原则（契约 R9）**：`channels.available` 里的渠道一律**同级**，不按渠道优劣预排序；选哪个只看"子问题↔渠道匹配度"——这条子问题最可能在哪个渠道拿到最有价值的信息。`unavailable` 渠道排除。

## 适配话题类型速记
- **A 客观事实/数据**（财务/市场/技术/宏观、求数值参数政策）→ exa（找权威源）+ jina（读官方页）+ xueqiu（公司/行情）+ github（技术事实）
- **B 产品/运营/策略**（怎么设计/运营/打法）→ exa + jina + 社媒深度（xiaohongshu 拆解/测评、bilibili 拆解视频、youtube、twitter、github）
- **C 口碑/体验/情绪**（用户评价/真实体验）→ xiaohongshu、reddit、twitter、v2ex、bilibili（UGC）

## 渠道清单

| slug | 能力 | 适配 | 命令提示（search / read）| 备注 |
|---|---|---|---|---|
| `exa` | 全网语义搜索 | A/B/C 通用入口 | `mcporter call exa search "<query>"` ／（取回的是候选URL，读取交给 jina）| 经 mcporter；适合"先把面铺开"找权威与深度源 |
| `jina` | 任意网页→markdown | 读取任意 URL | read：`curl https://r.jina.ai/<URL>` 或 `jina read <URL>` | 粗筛后深读的主力；A 类读官方页、B 类读长文 |
| `xiaohongshu` | 搜索+读笔记 | B/C（测评/拆解/口碑） | `opencli xiaohongshu search "<query>"` ／ `opencli xiaohongshu note <URL>` | 图文测评、实拍、体验 |
| `xueqiu` | 股票/行情/讨论/长文 | A（公司财务/资本） | `opencli xueqiu search "<query>"`（行情/讨论/专栏）| 财务、估值、投资视角 |
| `twitter` | 搜索+读推文 | B/C（动态/口碑/快讯）| `twitter search "<query>"` ／ `twitter tweet <URL>` | 含点赞数、媒体链接 |
| `github` | 代码/仓库/活动搜索 | A/B（技术事实/产品底层）| `gh search repos "<query>"` ／ `gh repo view <repo>` | 技术壁垒、开源生态 |
| `reddit` | 搜索+读帖 | B/C（海外口碑/深度讨论）| `opencli reddit search "<query>"` ／ `opencli reddit post <URL>` | 内容向：海外口碑/深度讨论 |
| `bilibili` | 搜索+视频/字幕 | B/C（拆解视频/UGC）| `opencli bilibili search "<query>"` | 内容向：海外口碑/深度讨论 |
| `youtube` | 视频/字幕提取 | B（教程/拆解）| `yt-dlp --write-auto-sub --skip-download <URL>` | 内容向：海外口碑/深度讨论 |
| `v2ex` | 社区搜索 | B/C（技术圈口碑）| 经公开 API（具体命令运行时确认）| 内容向，零配置 |
| `rss` | 订阅源拉取 | A/B（持续追踪特定源）| feedparser 拉取指定 feed | 内容向；需先有 feed URL |

## 选道原则（写进 search-strategy）
1. **按匹配度选道**：先按话题类型框出候选渠道，再问"这条子问题最可能在哪个渠道拿到最有价值的信息"。available 里的渠道同级，不按优劣预排序。反例：查财报/财务数据去小红书是错配——应走雪球/官方披露/exa。
2. **至少跨 2 类来源信度**（一手/二手/社群）交叉验证，不单押一个渠道——这是为信源独立性，与渠道优劣无关。
3. **exa + jina 是"找+读"的通用组合**：exa 语义找候选、jina 深读任意页；社媒渠道补"官方查不到的打法与真实口碑"。
4. 每条子问题给 2–3 个渠道即可（受预算约束，宁精勿多）。
5. **回环换道**：上一轮某渠道有效信息少时，下一轮优先换用尚未尝试、且对该缺口更匹配的渠道。
