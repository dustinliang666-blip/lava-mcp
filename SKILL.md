---
name: lava-news-heat
description: 查询股票和概念板块的消息面热度（熔岩）。当用户问某只股票/某个概念最近消息面热不热、被哪些机构/大V提及、要点是什么、概念里哪些股票最热时使用。
---

# 熔岩 · 消息面热度监测

## 给人看：3 步装好

WorkBuddy 国内版 5.9.3 已实测浏览器 OAuth 授权与 get_account 调用，无需手填 Key。步骤：https://lava.ai-dolphin.com/subscribe/docs#workbuddy 。以下三步用于 API Key 方式。

1. **拿 API Key**：登录熔岩（手机号 / Google）→ 左侧点「AI数据服务」→ 上方点「API Key」：首次进入「AI数据服务」时自动送代金券并生成「默认」Key（`lvk_` 开头，默认脱敏，点眼睛显示、点复制），接入文档里的 MCP JSON 已自动填好。入口：https://lava.ai-dolphin.com/lava#/ai-data-service
2. **添加 MCP**（MCP＝让 AI 办公软件直接调数据的接口）：先确认客户端支持自定义远程 MCP，再按各软件的官方入口添加连接器，
   - 连接方式：Streamable HTTP（HTTP 表单及 JSON 类型名称以客户端版本为准）
   - 地址：`https://lava.ai-dolphin.com/subscribe/v1/mcp`
   - 请求头：`Authorization` = `Bearer lvk_你的Key`（Bearer 后有一个空格）
3. **验证后使用**：启用连接器并查看工具列表，新建任务只调用 `get_account` 检查是否成功（熔岩不计费），然后再查询数据。客户端自身费用以其规则为准。

只连接第 2 步里的托管地址。本地代理已从本仓库移除。运行过该代理的，请到熔岩数据控制台轮换 API Key：https://lava.ai-dolphin.com/subscribe

DeepSeek Harness **0.2.2-rc.1** 使用仓库内配置包 [`plugins/deepseek-harness`](./plugins/deepseek-harness/README.md)。它只连接上面的托管地址，API Key 只从环境变量 `LAVA_API_KEY` 读取，不内置 Key，不启动本地转发，也不要改连 `127.0.0.1`。官方工具列表与 `get_account` 的成功认证仍需用户自己的测试 Key。

分软件的详细步骤：https://lava.ai-dolphin.com/subscribe/docs#ai-office
费用：先送 100 元代金券，之后按请求次数扣费，约 1000 次 5 元；失败的请求不扣钱。

## 给 AI 看：数据说明

数据源：熔岩数据远程 MCP `https://lava.ai-dolphin.com/subscribe/v1/mcp`（Streamable HTTP，请求头 `Authorization: Bearer <API Key>`）。
只使用这一托管端点。不要启动本地转发进程，也不要改连 `127.0.0.1`。
所有工具只读；返回结构化文字与机构/大V ID（agency_id）。适合量化交易工具与 AI Agent 股市研究接入。每次工具调用计 1 次请求（get_account 查余额不计费）。

## 流程

1. **个股热度**：`get_stock_news_heat(stock_name 或 ts_code, days=7)`
   - 看 `data.heat.mentions`（提及数）、`data.heat.agencies`（参与机构/大V数），再读 `list[].summary` 归纳要点。
2. **个股关联概念**：`get_stock_concept_heat(stock_name, days=30)` → 取 `list[]` 前 5 个概念及其 `mentions`。
3. **概念内个股排行**：`get_concept_stock_heat(concept, days=7)` → 列出提及最多的个股。
4. **关键词追踪**：`search_news_flow(keyword, since)`。
   - **全市场热榜**：`get_market_hot_stocks(window=24h)` / `get_market_hot_concepts(window=24h)`；问“靠谱的人在提什么”用 `get_weighted_hot_stocks(days=3)`。
   - **新冒头**：`get_first_mention_stocks(hours=24)` → 此前 7 天没人提、刚被第一次提到的股票。
   - **新闻点名**：`get_news_stock_hits(hours=24)` 看全市场；`get_news_stock_hits(stock_name)` 看某股被哪些媒体点名。
   - **单股多时间窗**：`get_stock_heat_windows(stock_name) → windows[]（1h~7d）与 hourly_24h[] 逐小时走势。
   - **热度动量 / 加速榜**：get_accelerating_hot_stocks(window=24h) → 列表含 heat_chg_1d / heat_chg_3d / heat_z20（相对近 20 日日均热度的 z 分）；普通热榜 get_market_hot_stocks 也会附带这三项。
   - **日频历史面板**：get_stock_heat_panel(stock_name 或 concept, days=90) → 日频 mentions / agencies 序列，适合回测与导出。
   - **机构覆盖度**：get_agency_coverage(stock_name, days=30) → 覆盖机构数时序与 7/30 日去重、新增覆盖。
5. **机构/大V可信度**（可选）：对 `agency_id` 用 `get_agency_pit` / `get_agency_history` 看机构/大V分（约 450~1500，中位约 1000）。
6. 余额不足（402 / INSUFFICIENT_BALANCE）时，告诉用户去熔岩「AI数据服务」→「概览与充值」充值；其他报错如实转告，不要反复重试。

## 输出要求

- 先给结论：热度高/中/低 + 提及数 + 参与机构/大V数 + 时间窗。
- 要点用 3~5 条结构化短句概括，紧扣返回字段。
- 少用术语；必须用时加一句白话（如“PIT＝只用当时已知数据算的历史分数”）。
- 机构/大V请使用返回的 agency_id 指代。
- 末尾可注明数据来自熔岩消息面热度监测。

## 参考

- 文档：https://lava.ai-dolphin.com/subscribe/docs
- OpenAPI：https://lava.ai-dolphin.com/subscribe/v1/openapi.json
- 安全说明：仓库内 [SECURITY.md](./SECURITY.md)（本地代理已停用）
- DeepSeek Harness 插件：[`plugins/deepseek-harness`](./plugins/deepseek-harness/README.md)（DSH 0.2.2-rc.1，只连托管端点）
