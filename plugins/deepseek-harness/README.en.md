# 熔岩数据 / Lava Data

金融数据量化 MCP与 AI Agent服务

Financial-data quantitative MCP and AI Agent services.

[中文](README.md)

Configuration-only bundle for hosted read-only A-share news heat, stock/concept rankings, first mentions, acceleration, historical panels, agency coverage and PIT scores. No trading execution or investment advice. Unreleased subscription APIs are not advertised.

## Tested host and limits

Isolated tests used **DSH 0.2.2-rc.1 / Node 24.22.1**. The local bundle was loaded; missing/invalid credentials, client timeout/disconnection and SDK cross-origin redirects were tested. No real key was used. Successful official tools/list and get_account still require a user test key. See [TEST-REPORT.md](TEST-REPORT.md). No marketplace PR has been made.

The npm release differs from master documentation: its client does NOT support `expandTemplates`, credential templates, `startupTimeoutMs` or `closeTimeoutMs`. These were removed. Authentication uses the official release's environment expression, with no general error-redaction guarantee. A missing key disables the connection.

## Setup

Get your own key at https://lava.ai-dolphin.com/subscribe . This bundle never creates, rotates or modifies keys. Use Node >=24.9, pnpm, and `@deepseek-ai/dsh@0.2.2-rc.1`; its CLI supplies the matching MCP client. In an external Bash terminal before starting DSH:

```bash
read -r -s -p 'LAVA_API_KEY: ' LAVA_API_KEY; printf '\n'
export LAVA_API_KEY
```

From this plugin's local directory:

```bash
dsh plugin --profile web add .
dsh web --no-open
```

Prefer an isolated DSH_HOME for evaluation. Desktop processes may not inherit shell exports; this release reads `process.env.LAVA_API_KEY`, not the newer credential-template service. The example env file is not automatically loaded by this bundle. Do not put real env files in the plugin. Model-provider credentials are separate and not configured here.

Inspect `mcp__lava__*` tools, then call only `mcp__lava__get_account` first (free on Lava). Do not publish account details. Confirm scope/budget before charged data calls. Stop on 402; do not loop retries. Missing key: disabled. After configuring a key or resolving a connection failure, reload/restart; automatic reconnect is off.

Remove: `dsh plugin --profile web remove dsh-lava-data-mcp`.

## Security

Only `https://lava.ai-dolphin.com/subscribe/v1/mcp` is supported, using an Authorization Bearer header. Never use local proxies/forwarding, loopback MCP endpoints, third-party relays or URL-embedded keys. No listener, subprocess, install scripts, telemetry or approval bypass is contributed. The host Web listener is separate.

This release does not promise general secret redaction. Runtime memory, same-user processes, untrusted plugins, HTTP debugging and upstream errors may expose secrets. Never share raw environment/logs/config exports, or put keys in prompts/tool arguments. Results reach the model and may be retained/uploaded by host session logging. Review [SECURITY.md](SECURITY.md).

Docs: https://lava.ai-dolphin.com/subscribe/docs
Security: https://github.com/dustinliang666-blip/lava-mcp/blob/main/SECURITY.md
Pinned source: https://github.com/deepseek-ai/deepseek-harness/tree/dsh-v0.2.2-rc.1
