# Claude 订阅接入

与 Codex 共用本机 MCP 源码及虚拟环境，每个客户端会启动自己的服务进程。
同一时刻只让一个客户端操作 AutoCAD；现已实现跨客户端会话互斥；旧服务需重启以加载。

## Claude Code（默认）

项目根目录 .mcp.json 已配置本机 stdio 服务，绝对路径指向当前 .venv 的
autocad-mcp.exe，不依赖终端工作目录查找 Python 模块。
该本机配置被 Git 忽略；可公开示例为 claude-code-mcp.example.json。
CLAUDE.md 提供项目入口规则。

在 C:\kinto\Autocad-mcp 启动 Claude Code，通过 /login 选择 Claude 订阅账户；
用 /mcp 核查 kinto_autocad。首次项目 MCP 可能需要客户端的项目信任/启用操作，
本次初始化不代替账户登录或客户端确认。
项目配置未设置自动放行写操作；服务默认仅提供经筛选的工具集，实验工具保持隐藏。
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

2026-09-26 已按用户选择添加本机 Claude Desktop 配置。新进程 stdio 握手通过；桌面客户端重启加载仍须单独确认。
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

## Windows 应用包版本路径（本机已核实）

2026-09-26，实际进程来自WindowsApps/Claude，客户端配置位于用户LocalAppData/Packages/Claude_pzs8sxrjxfjjc/LocalCache/Roaming/Claude/claude_desktop_config.json。普通APPDATA/Claude中的配置不能作为此安装已接入的证据。已备份并合并实际配置，保留全部既有偏好；实际配置启动新服务进程后初始化、32个默认工具及能力查询通过。

scripts.check_client_mcp现优先使用唯一存在的应用包配置，多个候选时拒绝猜测。脚本握手仍不等于桌面客户端已重载。用户需完全退出Claude（包括托盘进程）并重新打开，在开发者设置确认kinto_autocad；本轮未强制终止正在运行的客户端。配置路径以客户端“编辑配置”打开的位置为最终依据。
