# lava-mcp · 熔岩消息面热度监测

[熔岩（Lava）](https://lava.ai-dolphin.com/subscribe) 提供 **A 股股票和概念板块的消息面热度监测** 结构化只读数据——**量化交易必备**的消息面热度信号，供系统与智能体通过远程 MCP / REST 调用。

> 只读 · 结构化要点 + 匿名机构/大V ID · **不含多空方向与原文** · 新闻命中不含标题与正文 · 不构成投资建议

## 新手 3 步

① 开通并复制 API Key（登录熔岩 → 左侧「AI数据服务」→ API Key → 新建）

② 装 Skill，或在豆包办公/WorkBuddy/千问办公填 MCP 地址 https://lava.ai-dolphin.com/subscribe/v1/mcp

③ 用中文问「某某股票最近消息面热不热」，或「最近 24 小时全市场哪些股票消息面最热」

## 远程 MCP（推荐）

| 项 | 值 |
| --- | --- |
| 传输 | Streamable HTTP |
| Endpoint | `https://lava.ai-dolphin.com/subscribe/v1/mcp` |
| 鉴权 | 请求头 `Authorization: Bearer <API Key>`（或 `X-API-Key`） |
| 客户端 | 豆包办公、WorkBuddy（BUDDY）、千问办公（QwenWork）等支持自定义 HTTP MCP 的客户端 |

开通与计费见 [落地页](https://lava.ai-dolphin.com/subscribe)：开通赠 100 元代金券；1000 次 = 5 元。

## Skill 模板

仓库内 [`SKILL.md`](./SKILL.md) 覆盖官方模板中的查询流程，并写明全市场热榜、加权、首提、多时间窗与新闻点名的参数。官方模板：

https://lava.ai-dolphin.com/subscribe/v1/skill

适用于固化「查个股 / 概念 / 全市场消息面热度、首提与新闻点名」流程。

## 文档与机器可读规范

- 产品落地页：https://lava.ai-dolphin.com/subscribe
- API 文档（canonical）：https://lava.ai-dolphin.com/subscribe/docs
- OpenAPI 3.0：https://lava.ai-dolphin.com/subscribe/v1/openapi.json
- llms.txt：https://lava.ai-dolphin.com/llms.txt
- MCP Registry：[`server.json`](./server.json)
- Glama：[`glama.json`](./glama.json)

## 主要工具（MCP）

| Tool | 用途 |
| --- | --- |
| `get_stock_news_heat` | 个股消息面热度与结构化观点列表 |
| `search_news_flow` | 关键词检索消息面结构化记录 |
| `get_concept_stock_heat` | 概念 → 个股提及排行 |
| `get_stock_concept_heat` | 个股 → 概念提及排行 |
| `get_market_hot_stocks` | 全市场个股热榜（market-wide stock heat ranking）：最近谁被提得最多 |
| `get_market_hot_concepts` | 全市场概念热榜（concept heat ranking）：最近哪些概念最热；时间窗最长 `3d` |
| `get_weighted_hot_stocks` | 高分机构/大V加权热榜（weighted heat）：默认 `min_score` 1050、`order=weighted` |
| `get_first_mention_stocks` | 首提流（first-mention stream）：此前 7 天没有提及、窗口内第一次被提到的 A 股 |
| `get_stock_heat_windows` | 单股多时间窗热度（multi-window heat）+ 逐小时 + 来源拆分 |
| `get_news_stock_hits` | 新闻命中个股（news→stock hits）：匿名 `news_id`、发布时间、媒体、命中股票；不含标题与正文 |
| `get_agency_ranking` / `get_agency_pit` / `get_agency_history` / `list_agency_pit_dates` | 匿名机构/大V评分（当前 / PIT / 时序） |
| `get_account` | 余额与用量（不计费） |

参数名与线上 MCP / OpenAPI 一致。来源 `source`：`all`（默认）/ `community` 社群/星球 / `forum` 论坛/社区 / `web` 网页 / `search` 联网搜索 / `x` X（推特）/ `news_report` 新闻/研报。机构/大V分大约 450~1500，1000 左右为中等，1050 约前 10%。

### `get_market_hot_stocks`

按时间窗统计全市场每只股票的提及次数、机构/大V数、第一次与最近一次被提到的时间，从高到低排。可只看某类来源，或只统计高分机构/大V。约 1 分钟更新。

| 参数 | 说明 |
| --- | --- |
| `window` | `1h` / `4h` / `18h` / `24h` / `3d` / `7d`，默认 `24h` |
| `market` | `ashare`＝只看 A 股（按代码合并，默认）；`all`＝含港美股等（按简称合并） |
| `source` | 来源类别，默认 `all` |
| `min_score` | 只统计机构/大V分 ≥ 该值的提及；不传则不设门槛 |
| `limit` | 返回条数，默认 50，最大 200 |

### `get_market_hot_concepts`

按时间窗统计每个概念的提及次数与机构/大V数，从高到低排（已去掉「美股」「A股」这类泛词）。约 2 分钟更新。**时间窗最长 `3d`，不要传 `7d`。**

| 参数 | 说明 |
| --- | --- |
| `window` | `1h` / `4h` / `18h` / `24h` / `3d`，默认 `24h` |
| `source` | 来源类别，默认 `all` |
| `min_score` | 只统计机构/大V分 ≥ 该值的提及；不传则不设门槛 |
| `limit` | 返回条数，默认 50，最大 200 |

### `get_weighted_hot_stocks`

只统计机构/大V分达标的提及，并按分数加权：`weighted_heat`＝每次提及的机构/大V分 ÷ 1000 再相加。分数来自 PIT 面板（PIT＝只用当时已知数据算的历史分数）。返回参与的匿名 `agency_id`（最多 20 个）。

| 参数 | 说明 |
| --- | --- |
| `days` | 回看天数，默认 3，范围 1~30 |
| `min_score` | 机构/大V分门槛，默认 1050；传 `0` 表示不设门槛 |
| `order` | `weighted`＝加权热度（默认）；`count`＝提及次数；`score`＝最高机构/大V分 |
| `as_of_date` | 可选截面日期。传入后按该日 PIT 计分，消息只算到当天 15:00（北京时间），适合回测；不传则用最新面板，消息算到现在 |
| `market` | 同 `get_market_hot_stocks`，默认 `ashare` |
| `limit` | 返回条数，默认 50，最大 200 |

### `get_first_mention_stocks`

最近 N 小时内「首次被提到」的股票：此前 7 天一次都没有被提到。返回首提时间、首提匿名 `agency_id` 与分数、来源类别，以及首提之后到现在又被提了几次。

| 参数 | 说明 |
| --- | --- |
| `hours` | 回看小时数，默认 24，范围 1~72 |
| `source` | 来源类别，默认 `all` |
| `min_score` | 只统计机构/大V分 ≥ 该值的提及；不传则不设门槛 |
| `limit` | 返回条数，默认 100，最大 200 |

### `get_stock_heat_windows`

一次给出单只股票的多时间窗热度与来源拆分：`windows[]` 为 `1h` / `4h` / `18h` / `24h` / `3d` / `7d` 的提及数、机构/大V数、高分机构/大V数与加权热度；`hourly_24h[]` 为最近 24 小时逐小时提及；`by_source_7d[]` 为最近 7 天按来源类别的次数与占比。`stock_name` 与 `ts_code` 二选一。

| 参数 | 说明 |
| --- | --- |
| `stock_name` | 股票简称，如「宁德时代」 |
| `ts_code` | 股票代码，如 `300750.SZ` |
| `min_score` | 「高分机构/大V」的分数线，默认 1050 |

### `get_news_stock_hits`

主流财经媒体（新华网、财联社、新浪财经、同花顺等）快讯/新闻与 A 股简称的命中。不给股票时看全市场，并附窗口内被点名最多的股票排行（含熔岩同期 24 小时热度）；给股票时只看点名该股的新闻。约 2 分钟更新。

每条只返回匿名 `news_id`、发布时间、媒体来源、命中股票。**不含标题，不含正文。**

| 参数 | 说明 |
| --- | --- |
| `stock_name` | 可选。股票简称（与 `ts_code` 二选一）；不传则全市场 |
| `ts_code` | 可选。股票代码，如 `300750.SZ` |
| `hours` | 回看小时数。全市场默认 24、最多 72；指定股票默认 72、最多 168 |
| `src` | 可选。只看某家媒体，精确匹配，如 `财联社` / `新浪财经` / `同花顺` / `新华网` |
| `limit` | 返回条数，默认 50，最大 200 |

## 合规边界

- 全部工具只读；勿将输出写成荐股、多空或收益承诺
- 机构/大V仅使用匿名 `agency_id`，勿猜测真实机构/大V名
- 不含多空观点，不含原文；不要编造或补写原文
- `get_news_stock_hits` 只有匿名 `news_id`、发布时间、媒体来源与命中股票，**不含标题、不含正文**
- 勿外推控制台路径（`/subscribe/v1/console` 为 noindex）

## License

文档与 Skill 模板以站点公开内容为准；本仓库仅作接入说明与分发入口。
