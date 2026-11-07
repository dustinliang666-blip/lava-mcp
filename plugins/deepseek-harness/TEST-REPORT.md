# 隔离验收报告

日期：2026-11-07（Asia/Shanghai，UTC+8）。未查找、读取或使用真实熔岩 Key；只使用合成字符串 lava_invalid_test。

## 环境

- Node v24.22.1；npm 11.21.1；DSH @deepseek-ai/dsh **0.2.2-rc.1**（安装成功，未改用其他版本）。
- 官方 MCP client 同版 0.2.2-rc.1；@modelcontextprotocol/client **2.2.0**。
- 本机 /workspace/lava-dsh-test/runtime，使用 env -i 白名单环境、独立 HOME 与 DSH_HOME。没有读取现有环境文件/服务器/vault。
- npm install --ignore-scripts --no-audit --no-fund；DSH plugin --profile web add /workspace/lava-deepseekharness-plugin 本地加载成功（pnpm 12.18.0）。DSH Web 在测试专用 loopback 端口正常启动，测试结束后 TERM 停止；没有启动模型任务。
- OTel 测试时禁用，无模型 API 请求/真实数据。Web 登录 URL 的宿主随机 token 已在分享用日志中脱敏。

## 实测

| 项目 | 状态 | 结果 |
| --- | --- | --- |
| 锁定版本安装与本地 bundle 加载 | 通过 | DSH --version = 0.2.2-rc.1；dump 显示 mcp-lava-data、固定 HTTPS URL 和未求值环境表达式。 |
| 缺 Key | 通过 | 标准 Web profile 正常启动；disabled 表达式禁用连接。fetch 审计在 8s 观察窗内记录 0 次到熔岩域名的请求。提供 Key 后需重启。 |
| 假 Key / 401 | 通过 | 标准 Web profile 的 fetch 审计记录 1 次 POST，hasAuthorization=true，返回 401；重连关闭，无循环重试。直接 curl 同为 HTTP/2 401，JSON 错误 -32001，响应无 Location。 |
| 假 Key 日志 | 通过（范围有限） | 官方 client 导出 apply 使用隔离日志/工具注册桩捕获日志：Version negotiation failed…HTTP 401，无假 Key/Bearer/Authorization 值；模拟 401 回显合成 header 同样未泄露。不能扩展为所有错误路径均脱敏。 |
| 连接断开 | 通过（官方 client 夹具测试） | 本机假服务立即销毁 socket；约 6ms 返回 Version negotiation probe failed: fetch failed，零工具注册，重连禁用。 |
| 挂起超时 | 通过（官方 client 夹具测试） | 假服务接收请求不回应；60003ms 返回 Version negotiation probe timed out after 60000ms，零工具注册，不自动重连。此为 SDK 握手超时，不是 startupTimeoutMs。 |
| 跨源重定向携带 Authorization | 通过（SDK 夹具范围） | 实际安装的 SDK 直接发送合成 initialize，经不同 loopback 端口的 301/302/303/307/308；目标均未收到 Authorization。301/302/303 转 GET，307/308 保持 POST。不能承诺所有未来版本/代理行为。 |
| 官方工具列表 | 需用户测试 Key | 假 Key tools/list 同为 401；握手阶段已经拒绝，未拿到真实工具列表。 |
| 官方 get_account、工具调用超时/计费错误 | 需用户测试 Key | 未调用，未产生数据查询费用；不得声称已通过成功认证链路。 |

CLI 完整 profile 的标准输出只显示 Web 启动行，并未将 MCP logger 全部输出到控制台，因此另外用实际安装 client 的公开 apply 入口捕获 warning/error（日志/工具注册服务使用桩，不是另一个 MCP 实现）。断连/挂起/401回显测试与重定向测试使用临时本地夹具，仅携带假 Key；夹具均关闭且不放入插件发行物。不要把这些测试地址用于熔岩接入。

## 修复的重要兼容问题

此前草稿把 master 文档误当成 npm 当前发布版，导致 credentials 注入依赖和模板功能并不匹配。实查已安装 client schema 后：
- 移除 inject:[credentials]、expandTemplates、credential 模板、startupTimeoutMs、closeTimeoutMs。
- 使用发布版官方示例的 process.env 表达式；新增无 Key 自动 disabled，保留固定 URL、60s 工具超时、关闭重连。
- 删除“运行时凭据解析/自动错误脱敏/20s总启动预算/5s关闭预算已支持”的不实描述。
- MIT LICENSE 与仓库根目录 LICENSE 一致（Copyright (c) 2026 Dustin Liang）；package files 增加 LICENSE/本报告。

## 安全结论

CONDITIONAL：上述有限测试未发现 Key 跨源转发、本地代理暴露或 401 日志泄露；不扩大权限。发布版没有通用秘密脱敏和宿主级隔离，且成功认证未完成。可作为待验收配置子包交父 agent 入库，但市场提交/全面可用声明必须等待用户测试 Key 验收与另行批准。详见 SECURITY.md。

## 证据位置（本机，不含真实熔岩密钥）

/workspace/lava-dsh-test/results.json：官方 client/SDK 夹具结果。
/workspace/lava-dsh-test/audit-invalid.jsonl：只含 host/path/method/header存在布尔值/status，不记录 header 值。
/workspace/lava-dsh-test/web-audit-missing.log：缺 Key 的启动记录（token 已脱敏）。
/workspace/lava-dsh-test/config-dump-final.yml：表达式未求值的配置合成结果。
/workspace/lava-dsh-test/endpoint-headers.txt、tools-list-headers.txt：官方假 Key HTTP 状态。
/workspace/lava-dsh-test/runtime/security-tests.mjs、audit-fetch.mjs：本机测试脚本，未纳入插件发行物。

参考：
https://github.com/deepseek-ai/deepseek-harness/tree/dsh-v0.2.2-rc.1/packages/mcp/mcp-client
https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.2-rc.1/README.md
