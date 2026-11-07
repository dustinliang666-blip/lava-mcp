# 安全复审

## 结论：CONDITIONAL（仅可作为待完整认证验收的配置包入库，不能宣称全面安全验证/市场已发布）

本次只用了合成假 Key `lava_invalid_test`，从未查找/读取/使用/轮换真实熔岩 Key。DSH 0.2.2-rc.1 与 MCP client 0.2.2-rc.1、SDK @modelcontextprotocol/client 2.2.0 的本机验证见 TEST-REPORT.md。

- Key 仅从用户启动环境在运行时读取，Authorization header 只配置到官方 HTTPS 地址。无写密钥文件、日志、第三方转发逻辑；不能把“代码无记录逻辑”说成“全宿主永不泄露”。
- 缺环境变量自动禁用连接，避免发送 Bearer undefined。变量补好后需重启/重载。没有默认真实值或可覆盖 URL 的用户输入。
- 官方端点假 Key 实测 HTTP 401，无 Location 重定向；401 客户端日志未出现假 Key、Bearer 或 Authorization header。模拟 401 回显同样未泄露。但本发布版没有通用错误脱敏功能，不能推广到所有工具错误/日志路径。
- SDK 跨源（不同端口）301/302/303/307/308 实测均未把 Authorization 带到目标；307/308 仍转发请求体，所以不能把秘密放进工具参数。相同 origin 的请求自然仍可能带 header；固定地址并非网络级 egress 策略。
- 插件不监听端口、不运行本地转发/stdio 子进程，无安装/构建脚本。测试夹具在隔离测试目录暂用 loopback 临时端口，只服务合成请求，测试后已关闭；夹具不是插件发行文件或接入建议。DSH Web 自身监听属于宿主。
- 无权限升级、无审批白名单、无遥测新增。远端动态工具发现仍需核对只读范围；不自动执行收费数据查询。
- 断连立即可见失败且无自动重试；挂起握手约 60s 后失败。`toolCallTimeoutMs` 60s 只控制工具/资源调用，不是自定义启动总预算。原草稿的 20s startup/5s close 字段在 npm 发布版不支持，已删除；不声称关闭有 5s 上限。

## 必须明确的剩余风险

1. **Medium：宿主级秘密保护不足。** 本发布版只能用环境表达式，没有 master 新增的 credential template/redaction。恶意插件、同 UID 进程、未受限 agent、HTTP debug、原始异常/配置导出都可能泄露 Key。只在可信宿主使用，禁止分享 raw logs/环境，不要让 agent 主动读取 Key。若要求强隔离/全面自动脱敏，应等待并验证支持该功能的发布版，不要用未经发布的 master 功能冒充。
2. **Medium：未完成成功认证链路。** 真实 tools/list、get_account、付费查询、实际工具调用超时/错误响应的脱敏均未验证；需要用户自行提供测试环境中的 Key 后验收，本轮不索取/读取 Key。
3. **Low：宿主日志与模型数据处理。** 成功结果/远端 instructions 会进入模型或会话，宿主可上传会话/反馈数据。根据隐私需求关闭/检查宿主上传设置；本测试用 env -i 的隔离 HOME/DSH_HOME、关闭 OTel、无模型请求，未上传真实数据。宿主 Web 自动生成的登录 token 已从分享用日志脱敏。

## 上市场前的门槛

- 用用户专用测试 Key 在可信环境完成官方 tools/list 和免费 get_account；不要公开余额/账户明细。
- 核对无交易/写入工具，确认计费范围；不要为验收调用付费工具。
- 执行 npm pack 白名单检查，复核版本兼容范围及仓库路径。
- 若采用未来的凭据模板，必须重新实装验证 schema 和日志脱敏，不依据 master 文档猜测兼容。
- **市场 PR 必须再次获得用户批准；本轮绝不提交。**

依据（版本化参考，避免 master 漂移）：
https://github.com/deepseek-ai/deepseek-harness/tree/dsh-v0.2.2-rc.1/packages/mcp/mcp-client
https://github.com/dustinliang666-blip/lava-mcp/blob/main/SECURITY.md
