# Windows 安装与 Codex 接入

目标是 Codex 订阅登录 → 本机 stdio MCP → AutoCAD。
无需在本项目填写 OPENAI_API_KEY、ANTHROPIC_API_KEY，也无需运行 Web 聊天界面或 Ollama。

## 安装

在仓库根目录使用 Windows Python 3.11+，不要使用 WSL Python 连接本机 COM：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -m "not integration"
```

此阶段保留上游依赖；Web/供应商依赖将在下一阶段拆分。config.yaml 中供应商配置
仅供上游模式使用，src.server 的工具调用不经过模型供应商。

## Codex

docs/codex-mcp.example.toml 是配置片段，不会自动应用。
将其合并到 Codex MCP 设置使用的配置中，保留已有服务器；目录不同则调整路径。
示例最初只暴露查询工具。通过真实 CAD 验收后再扩大工具范围。

启动命令为项目虚拟环境的 python.exe，参数为 -m src.server。
启动前打开 AutoCAD Electrical 2026 和合成测试图纸；MCP 连接与 CAD 许可是独立的。
现有上游检测器未完成 2026 适配，返回的版本/能力须与实际界面核对。
配置的查询工具限制不消除上游启动检测/连接的行为。

profiles/ 当前是后续适配草案，不由现有服务自动读取。
本次初始化不更改 Codex 全局设置，也不加载 AutoLISP。

来源：
- https://learn.chatgpt.com/docs/extend/mcp?surface=cli
- https://learn.chatgpt.com/docs/auth
## 本机已生成的配置

初始化已将示例复制为项目 .codex/config.toml；在 Codex 中打开并信任本项目后，
由客户端加载。尚未在订阅会话验证调用。全局配置未修改。
Claude Code 的 .mcp.json 也已生成，详见 claude-setup.md。

## SDK 兼容性

上游使用 mcp.server.fastmcp，MCP SDK 2.x 已移除此导入路径。
本 fork 初始化将依赖限制为 mcp>=1.28,<2；迁移 2.x 需要单独适配和验证。
来源：https://py.sdk.modelcontextprotocol.io/v1/
