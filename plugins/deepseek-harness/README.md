# 熔岩数据

金融数据量化 MCP与 AI Agent服务

[English](README.en.md)

配置型 DeepSeek Harness bundle，通过官方 Streamable HTTP 连接熔岩只读 A 股研究数据：个股/概念消息面热度、市场热榜、首提、加速、日频面板、机构覆盖与 PIT 评分。不含交易执行，不构成投资建议；不宣称支持尚未开放的情绪/板块趋势订阅 API。

## 验证状态

已在隔离 box 安装 **DSH 0.2.2-rc.1 / Node 24.22.1**，加载本地 bundle，并进行缺 Key、假 Key、官方 client 断连/超时及 SDK 跨源重定向测试。没有使用真实 Key；官方工具列表与 get_account 成功调用仍需用户测试 Key。完整结果见 [TEST-REPORT.md](TEST-REPORT.md)。尚未提交插件市场。

重要更正：此前草稿依据 master 文档写的 `expandTemplates`、`${credential:...}`、`startupTimeoutMs`、`closeTimeoutMs` **不属于 npm 发布版 0.2.2-rc.1 的 client schema**，现已删除。该版采用官方 README 的环境变量表达式；**不能声称拥有新版的凭据模板错误脱敏或启动总超时**。缺 Key 自动禁用此连接。

## 安装和配置

1. 在 https://lava.ai-dolphin.com/subscribe 自行获取 Key；不要发给聊天、工单或截图。本插件不创建、轮换或修改任何 Key。
2. 使用 Node >=24.9、pnpm 和锁定版本 `@deepseek-ai/dsh@0.2.2-rc.1`。官方 CLI 已提供匹配 client，不要额外安装旧版 client。
3. 在启动 DSH 前，在外部 Bash 终端输入 Key（不回显，也不把真实值写入命令历史）：

```bash
read -r -s -p 'LAVA_API_KEY: ' LAVA_API_KEY; printf '\n'
export LAVA_API_KEY
```

4. **本地源目录方式**：在本插件目录运行：

```bash
dsh plugin --profile web add .
dsh web --no-open
```

在日常环境操作前推荐独立设置 `DSH_HOME` 测试，不要覆盖原 profile。桌面宿主未必继承终端环境，本版本表达式读取 `process.env.LAVA_API_KEY`，不要假定新版凭据 UI 能替代它。`.env.example` 仅说明变量名，不由本插件自动加载；不建议在插件目录放真实 `.env`。本插件不负责设置模型 API Key。

5. 首先检查工具列表，再仅调用 `mcp__lava__get_account`（熔岩不计费）；不要公开账户明细。后续查询可能扣费，先确认数据范围/预算。402/余额不足时停止，不循环重试。缺 Key 不连接；提供环境变量后重启 profile。连接失败后不自动重连，修正后重载或重启。

卸载：`dsh plugin --profile web remove dsh-lava-data-mcp`。

## 安全边界

唯一端点：`https://lava.ai-dolphin.com/subscribe/v1/mcp`；鉴权为 `Authorization: Bearer <Key>`。严禁改用本地代理、127.0.0.1、端口转发、第三方中继或 URL 携带 Key。插件不监听端口、不启动进程，无安装脚本、遥测或权限自动放行；DSH Web 自身监听与插件 MCP 连接是两回事。

该发布版没有通用凭据错误脱敏承诺。配置 dump 保留未求值表达式，但运行内存、宿主/同 UID 进程、不可信插件、HTTP 调试或异常内容仍可能泄露秘密。不要共享环境、raw logs、配置导出或会话；不要把 Key 放进提示词/工具参数。数据结果进入模型/会话，宿主日志上传设置也需检查。详见 [SECURITY.md](SECURITY.md)。

文档：https://lava.ai-dolphin.com/subscribe/docs
安全说明：https://github.com/dustinliang666-blip/lava-mcp/blob/main/SECURITY.md
已发布版本源：https://github.com/deepseek-ai/deepseek-harness/tree/dsh-v0.2.2-rc.1
