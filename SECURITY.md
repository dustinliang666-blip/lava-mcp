# Security

## Local proxy retired

The optional local proxy (`proxy/`) has been removed after a responsible report from [@zackchewa](https://github.com/zackchewa). Thank you for the review.

Report: https://github.com/zackchewa/awesome-china-mcp/issues/10#issuecomment-6620468523

That proxy forwarded MCP traffic to the hosted endpoint and attached the user's API key. On a kept-alive HTTP/1.1 connection, an early rejection could leave the request body unread, and that body could then be handled as another request and sent upstream with the key. A web page the user opened could spend their balance this way. With `LAVA_PROXY_ALLOW_REMOTE=1`, anyone who could reach the port could get the key attached by sending `Host: localhost`. Client sockets also had no read timeout, so a stalled body could hold a worker thread.

This repository no longer forwards requests with the user's key. The only supported path is the hosted endpoint:

https://lava.ai-dolphin.com/subscribe/v1/mcp

Send `Authorization: Bearer <API Key>` (or `X-API-Key`), or use OAuth 2.1. Docs: https://lava.ai-dolphin.com/subscribe/docs

If you ran the local proxy, rotate your 熔岩数据 API key in the console:

https://lava.ai-dolphin.com/subscribe

## 本地代理已停用

可选本地代理（`proxy/`）已删除。感谢 [@zackchewa](https://github.com/zackchewa) 的负责任报告与复查。

报告：https://github.com/zackchewa/awesome-china-mcp/issues/10#issuecomment-6620468523

该代理会把 MCP 流量转到托管端点，并附上用户的 API Key。在保持活动的 HTTP/1.1 连接上，较早的拒绝可能留下未读请求体，这段内容随后会被当成另一个请求，并带上 Key 转发到上游。用户打开的网页可以由此消耗余额。设置 `LAVA_PROXY_ALLOW_REMOTE=1` 时，任何能访问该端口的人只要发送 `Host: localhost`，请求就会被附上 Key。客户端套接字也没有读超时，停滞的请求体可以一直占用工作线程。

本仓库不再用用户的 Key 转发请求。唯一支持的接入是托管端点：

https://lava.ai-dolphin.com/subscribe/v1/mcp

请求头使用 `Authorization: Bearer <API Key>`（或 `X-API-Key`），也可以使用 OAuth 2.1。文档：https://lava.ai-dolphin.com/subscribe/docs

如果你运行过本地代理，请到熔岩数据控制台轮换 API Key：

https://lava.ai-dolphin.com/subscribe

## DeepSeek Harness plugin

[`plugins/deepseek-harness/`](./plugins/deepseek-harness/README.md) is a configuration-only bundle for DeepSeek Harness 0.2.2-rc.1. It is another way to reach the same hosted endpoint. It does not listen, spawn a forwarder or subprocess, or embed an API key. The MCP URL is fixed to https://lava.ai-dolphin.com/subscribe/v1/mcp . The key is read at runtime from the environment variable `LAVA_API_KEY`. Do not point it at `127.0.0.1` or a local forwarder.

A successful authentication check with a real test key (official tools list and `get_account`) is still pending. Details: [plugins/deepseek-harness/SECURITY.md](./plugins/deepseek-harness/SECURITY.md).

## DeepSeek Harness 插件

[`plugins/deepseek-harness/`](./plugins/deepseek-harness/README.md) 是 DeepSeek Harness 0.2.2-rc.1 的配置包，用来连接同一个托管端点。它不监听端口、不启动转发进程或子进程、不内置 API Key。MCP 地址固定为 https://lava.ai-dolphin.com/subscribe/v1/mcp ，Key 只在运行时从环境变量 `LAVA_API_KEY` 读取。不要把它指到 `127.0.0.1` 或本地转发。

用真实测试 Key 做成功认证（官方工具列表与 `get_account`）仍未完成。说明见 [plugins/deepseek-harness/SECURITY.md](./plugins/deepseek-harness/SECURITY.md)。
