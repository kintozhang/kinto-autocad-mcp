# Kinto AutoCAD MCP

先读取 AGENTS.md、README.md 和 docs/capabilities.md。
使用 Claude 订阅登录，通过本机 MCP 调用 CAD；不使用 API key 或上游 Web 模型层。

电气工作流：skills/autocad-electrical/SKILL.md。
机械工作流：skills/autocad-mechanical/SKILL.md。
这些工作流可作为文件读取；它们引用的 Codex Computer Use 插件不自动适用于 Claude。
Claude 中只有实际存在并已配置的桌面工具才能执行 UI 操作；
若没有桌面工具，报告需要界面处理的具体步骤，不假装已操作。

不要与 Codex 同时控制同一个 AutoCAD 会话；当前尚无跨进程互斥锁。
初始化阶段先使用查询工具，写图必须在合成工程副本按验收流程开展。