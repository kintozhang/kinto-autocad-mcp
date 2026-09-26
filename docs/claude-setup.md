# Claude 订阅接入

与 Codex 共用本机 MCP 源码及虚拟环境，每个客户端会启动自己的服务进程。
同一时刻只让一个客户端操作 AutoCAD；当前未实现跨进程互斥。

## Claude Code（默认）

项目根目录 .mcp.json 已配置本机 stdio 服务，绝对路径指向当前 .venv 的
autocad-mcp.exe，不依赖终端工作目录查找 Python 模块。
该本机配置被 Git 忽略；可公开示例为 claude-code-mcp.example.json。
CLAUDE.md 提供项目入口规则。

在 C:\kinto\Autocad-mcp 启动 Claude Code，通过 /login 选择 Claude 订阅账户；
用 /mcp 核查 kinto_autocad。首次项目 MCP 可能需要客户端的项目信任/启用操作，
本次初始化不代替账户登录或客户端确认。
项目配置未设置自动放行写操作；上游服务仍注册全部工具，先只调用查询工具。
Codex 示例的 enabled_tools 不是 Claude 配置字段，不可直接复制过去。

不要给 Claude Code 配置 ANTHROPIC_API_KEY；如启动环境已有该变量，
应在用于订阅的终端中移除它后登录，避免走 API 计费。
本项目不读取或迁移订阅 token，也不把订阅当作 Python API 凭据。
未核实你的具体套餐权限或当前登录状态。

## Claude Desktop（可选）

在 Desktop 的开发者设置打开 MCP 配置文件，
将 claude-desktop-mcp.example.json 的 kinto_autocad 项合并到已有 mcpServers。
保留原有服务和设置。Windows 常见路径为
%APPDATA%\Claude\claude_desktop_config.json；实际以客户端打开的位置为准。
完全退出并重新启动客户端后检查服务。

本次仅生成 Desktop 示例，不修改它的全局配置。
本地 stdio 服务无法直接供普通 Claude 网页访问。

## Computer Use

MCP 接入不等于 Claude 自动获得 Codex 的 Computer Use 插件。
如果 Claude 环境没有可用的桌面控制工具，先用 MCP，
需要 UI 的步骤留待具备桌面控制能力的会话处理。
不为此另外使用按 API key 计费的 Computer Use API。

来源：
- https://code.claude.com/docs/en/mcp
- https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan
- https://py.sdk.modelcontextprotocol.io/get-started/real-host/