# CAD 桥接层

已验证的内部 AutoLISP 表达式由 `src/autocad/lisp_bridge.py` 安全编码和发送，原生操作位于 `src/tools/native_electrical.py`。尚不需要 .NET 桥接或额外加载 LSP 插件。

每次表达式带唯一回执，结果存入被忽略的 work/bridge。以本机2026 ACE_API.chm为依据，元件、端子连线、线号已完成独立DWG回读和保存重开。

详见 [验收记录](../docs/native-electrical-validation-20260924.md)。桥接表达式有进程内锁；新版MCP另有跨客户端进程锁与隔离工作进程，详见[执行隔离](../docs/execution-isolation.md)。直接脚本/UI仍需串行安排；超时不自动重试，部分写入须检查句柄。此目录保留给后续可复用LSP/.NET模块，避免复制两份实现。
