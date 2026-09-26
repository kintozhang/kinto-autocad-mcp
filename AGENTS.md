# 项目工作规则

本项目以 Windows 本机 AutoCAD Electrical 2026 为目标，主要用于电气制图，
并支持简单机械二维图。Codex 订阅会话负责推理，本机 MCP 负责执行。

- 先阅读 README.md 和 docs/capabilities.md；不得把规划中的功能描述为已实现。
- 保留用户已有改动和上游许可证。真实图纸、厂家资料、密钥和机器本地配置不得放进公开样例。
- 电气操作工作流见 skills/autocad-electrical/SKILL.md；
  机械操作工作流见 skills/autocad-mechanical/SKILL.md。
- 需要控制 Windows UI 时，先读取当前可用 Computer Use 技能，并使用其官方运行入口。
- MCP 和 UI 串行操作同一 CAD 会话；写入前核对目标文档，UI 操作后重新读取状态。
- 上游命令提交不等于执行完成。未经回读验证，不报告元件、接线或报表已完成。
- 不臆造符号库名称、端子、I/O 地址、Electrical API 签名或安全参数；记录来源及待核实项。
- 默认验证使用 python -m pytest -m "not integration"。
  上游 integration 测试有 mock，不能代替真实 CAD 验收；见 tests/acceptance/README.md。
- profiles/autocad-electrical-2026.yaml 当前只是规格草案，尚未由运行时代码加载或强制执行。
- 变更 CAD 写操作时，用合成工程副本完成对象回读、保存重开及报表核验。