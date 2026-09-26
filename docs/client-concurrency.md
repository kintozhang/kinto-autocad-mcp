# Codex / Claude 跨进程互斥验收

2026-09-24：所有已注册 MCP 工具在执行函数前获取同一 Windows 用户的非阻塞文件锁，范围覆盖整个工具调用。同一用户不同仓库副本共用 `%LOCALAPPDATA%/KintoAutoCADMCP/session.lock`；没有客户端专用锁路径配置。

冲突返回 `success=false, status=cad_in_use, submitted=false`，不排队、不重试、不进入工具函数。使用 functools.wraps 保留工具签名，默认仍为24项，61项定义、37项隐藏。Codex 和 Claude 的既有本地启动配置无需增加模型 API key；已经启动的旧 MCP 服务必须重新连接才能加载保护。

实现依据：[Python msvcrt.locking 文档](https://docs.python.org/3/library/msvcrt.html#msvcrt.locking)。锁定第0字节，运行标记写在后续字节；正常返回后清空标记。进程死亡或未捕获异常保留运行标记，后续获取锁仍返回 previous_client_interrupted，重复请求不会自动解除。

## 验证

- 152项默认测试通过，3项 integration 未运行。
- 真实独立进程争用、释放后重新获取、进程异常退出后的连续拦截通过。
- 工具签名保持、冲突时函数体零调用、异常留下标记通过。
- `work/acceptance/client-gate-20260924-231811/report.json`：真实 stdio MCP 画圆请求在另一个进程持锁时被拒绝；独立合成DWG对象数不变。释放后相同请求只增加1个圆；保存重开后圆心(40,100,0)、半径2及句柄回读通过。
- 验收使用受控持锁进程与真实 MCP 服务，没有同时操作 Codex 和 Claude 两个聊天界面。不是客户端热重载验收。

复测：`.venv/Scripts/python.exe -m scripts.client_gate_smoke --write`。仅使用已验收的本机双语空白DWG种子创建新副本，不覆盖正式工程。本次没有修改电气逻辑，因此没有重复原生电气报表验收。

## 中断恢复与边界

遇到 previous_client_interrupted 时，先停止本用户全部相关 MCP 服务，通过 AutoCAD 界面检查活动图纸、未完成命令、实体及保存状态，并核对最后一次操作是否落地。备份锁文件和验收记录，确认状态后才可由维护人员清除运行标记并重启服务；不要仅凭PID已退出判断写入未发生。当前没有自动恢复或公开清锁工具。

文件锁仅约束采用本实现的 MCP 服务。旧版本、直接 COM/CLI、Computer Use、手动操作及其他 Windows 用户不受其控制；仍需串行操作。启动时只读连接探测不在工具锁内。工具正常返回（包括自行捕获错误并返回失败）会释放锁；此机制不判断失败请求是否已经部分写入。超时/失败仍必须回读，不能自动重放写入。COM调用阻塞期间锁持续持有，尚无独立STA工作进程或COM硬超时终止机制。
