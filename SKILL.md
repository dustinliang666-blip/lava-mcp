---
name: lava-news-heat
description: 查询股票和概念板块的消息面热度（熔岩）。当用户问某只股票/某个概念最近消息面热不热、全市场哪些股票或概念最热、高分机构/大V在提什么、哪些股票是第一次被提到、单股各时间窗与来源热度、被哪些媒体点名、被哪些机构/大V提及、要点是什么时使用。
---

# 熔岩 · 消息面热度监测

## 给人看：3 步装好

1. **拿 API Key**：登录熔岩 → 左侧点「AI数据服务」→ 上方点「API Key」→ 点「创建」，马上复制保存（`lvk_` 开头，只显示一次）。入口：https://lava.ai-dolphin.com/lava#/ai-data-service
2. **添加 MCP**（MCP＝让 AI 办公软件直接调数据的接口）：在豆包办公 / WorkBuddy / 千问办公的「连接器」里新建自定义连接器，
   - 连接方式：Streamable HTTP（豆包里叫「HTTP」）
   - 地址：`https://lava.ai-dolphin.com/subscribe/v1/mcp`
   - 请求头：`Authorization` = `Bearer lvk_你的Key`（Bearer 后有一个空格）
3. **新建对话提问**：例如「宁德时代最近一周消息面热不热？」「最近 24 小时全市场哪些股票消息面最热？」

分软件的详细步骤：https://lava.ai-dolphin.com/subscribe#ai-office
费用：先送 100 元代金券，之后按请求次数扣费，约 1000 次 5 元；失败的请求不扣钱。

## 给 AI 看：数据说明

数据源：熔岩远程 MCP `https://lava.ai-dolphin.com/subscribe/v1/mcp`（Streamable HTTP，请求头 `Authorization: Bearer <API Key>`）。
所有工具只读；返回结构化文字与匿名机构/大V ID（agency_id），**不含多空观点与原文**。新闻命中只含匿名 news_id、发布时间、媒体来源与命中股票，**不含标题与正文**。每次工具调用计 1 次请求（get_account 查余额不计费）。

## 流程

1. **个股热度**：`get_stock_news_heat(stock_name 或 ts_code, days=7)`
   - 看 `data.heat.mentions`（提及数）、`data.heat.agencies`（参与机构/大V数），再读 `list[].summary` 归纳要点。
2. **个股关联概念**：`get_stock_concept_heat(stock_name, days=30)` → 取 `list[]` 前 5 个概念及其 `mentions`。
3. **概念内个股排行**：`get_concept_stock_heat(concept, days=7)` → 列出提及最多的个股。
4. **关键词追踪**：`search_news_flow(keyword, since)`。
5. **全市场热榜**：`get_market_hot_stocks(window=24h)`，`window` 取 `1h` / `4h` / `18h` / `24h` / `3d` / `7d`。概念用 `get_market_hot_concepts(window=24h)`，时间窗最长 `3d`（不要传 `7d`）。可选 `market`（`ashare` 默认 / `all`）、`source`、`min_score`、`limit`。
6. **高分加权**：问「靠谱的人在提什么」用 `get_weighted_hot_stocks(days=3)`。默认 `min_score` 1050（约前 10%）、`order=weighted`（也可 `count` / `score`）。回测传 `as_of_date`：分数用 PIT（PIT＝只用当时已知数据算的历史分数），消息只算到当天 15:00。看 `weighted_heat`（每次提及的机构/大V分 ÷ 1000 再相加）和匿名 `agency_id`。
7. **首提流**：`get_first_mention_stocks(hours=24)` → 此前 7 天没有提及、窗口内第一次被提到的股票。看首提时间、首提 `agency_id` 与分数、来源，以及首提之后又被提了几次。
8. **单股多时间窗**：`get_stock_heat_windows(stock_name 或 ts_code)` → `windows[]`（1h~7d 提及数、机构/大V数、高分机构/大V数、加权热度）、`hourly_24h[]` 逐小时、`by_source_7d[]` 来源占比。高分线 `min_score` 默认 1050。
9. **新闻点名**：`get_news_stock_hits(hours=24)` 看全市场；`get_news_stock_hits(stock_name)` 看某股被哪些媒体点名。只转述匿名 `news_id`、发布时间、媒体 `src`、命中股票。**不要标题、不要正文**，也不要编造。
10. **机构/大V可信度**（可选）：对 `agency_id` 用 `get_agency_pit` / `get_agency_history` 看机构/大V分（约 450~1500，中位约 1000）。
11. 余额不足（402 / INSUFFICIENT_BALANCE）时，告诉用户去熔岩「AI数据服务」→「概览与充值」充值；其他报错如实转告，不要反复重试。

## 输出要求

- 先给结论：问个股时给热度高/中/低 + 提及数 + 参与机构/大V数 + 时间窗；问全市场、加权、首提或新闻点名时，先给时间窗和前几名（提及数、加权热度或命中次数）。
- 要点用 3~5 条结构化短句概括，**不要推断或输出看多/看空结论**，不要荐股、不要承诺收益，不要编造原文。
- 新闻命中只报匿名 news_id、发布时间、媒体来源和命中股票，**不要输出或补写标题与正文**。
- 少用术语；必须用时加一句白话（如“PIT＝只用当时已知数据算的历史分数”）。
- 机构/大V只用 agency_id 指代，不要猜测真实机构/大V名。
- 末尾注明：数据来自熔岩消息面热度监测，仅供研究参考，不构成投资建议。

## 参考

- 文档：https://lava.ai-dolphin.com/subscribe/docs
- OpenAPI：https://lava.ai-dolphin.com/subscribe/v1/openapi.json
