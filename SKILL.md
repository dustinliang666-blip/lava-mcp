---
name: lava-news-heat
description: 查询股票和概念板块的消息面热度（熔岩）。当用户问某只股票/某个概念最近消息面热不热、被哪些机构提及、要点是什么、概念里哪些股票最热时使用。
---

# 熔岩 · 消息面热度监测

数据源：熔岩远程 MCP `https://lava.ai-dolphin.com/subscribe/v1/mcp`（Streamable HTTP，请求头 `Authorization: Bearer <API Key>`）。
所有工具只读；返回结构化文字与匿名机构 ID（agency_id），**不含多空观点与原文**。每次工具调用计费 1 次（get_account 不计费）。

## 流程

1. **个股热度**：`get_stock_news_heat(stock_name 或 ts_code, days=7)`
   - 看 `data.heat.mentions`（提及数）、`data.heat.agencies`（参与机构数），再读 `list[].summary` 归纳要点。
2. **个股关联概念**：`get_stock_concept_heat(stock_name, days=30)` → 取 `list[]` 前 5 个概念及其 `mentions`。
3. **概念内个股排行**：`get_concept_stock_heat(concept, days=7)` → 列出提及最多的个股。
4. **关键词追踪**：`search_news_flow(keyword, since)`。
5. **机构可信度**（可选）：对 `agency_id` 用 `get_agency_pit` / `get_agency_history` 看机构分（约 450~1500，中位约 1000）。
6. 余额不足（402 / INSUFFICIENT_BALANCE）或限流（429）时，如实告诉用户，不要重试轰炸。

## 输出要求

- 先给结论：热度高/中/低 + 提及数 + 参与机构数 + 时间窗。
- 要点用 3~5 条结构化短句概括，**不要推断或输出看多/看空结论**，不要编造原文。
- 机构只用 agency_id 指代，不要猜测真实机构名。
- 末尾注明：数据来自熔岩消息面热度监测，仅供研究参考，不构成投资建议。

## 参考

- 文档：https://lava.ai-dolphin.com/subscribe/docs
- OpenAPI：https://lava.ai-dolphin.com/subscribe/v1/openapi.json
