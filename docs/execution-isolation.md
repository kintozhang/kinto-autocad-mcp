# COM 执行隔离、目标绑定与中断诊断

2026-09-25：62项定义，25项默认开放，37项隐藏；160项默认测试通过，3项integration未运行。

## 本轮实现

- 每个已注册CAD工具在独立Python工作进程的STA主线程中执行；COM对象不在进程间传递。MCP主进程异步等待，保留跨客户端文件锁。
- 普通调用45秒，原生报表90秒，项目PDF180秒。超时只终止本次Python工作进程，最多另等5秒回收；不终止AutoCAD，也不宣称命令已撤销。Windows进程创建本身不在communicate时限内。
- 超时、工作进程异常、无有效JSON回执及工具返回失败，都保留中断标记和outcome_unknown记录，不自动重试。工具内部已捕获的失败也不再悄悄释放保护。
- MCP启动探测禁用COM回退；连接只在工作进程中建立。
- 工作进程记录实例HWND及活动DWG，常规工具访问文档时检查绑定，执行后再次核验。基础直线/圆/文字/矩形新增可选drawing_path，填写时执行前必须匹配活动DWG。未填写时绑定执行开始的活动图纸。
- 项目PDF需要切换临时副本，使用原有逐页保护并在结束检查恢复原图；项目身份检查沿用原生Electrical工具的既有WDP校验。
- 新增get_execution_diagnostics，只读取本用户LocalAppData/KintoAutoCADMCP下的运行标记和最近10条操作记录；锁占用或隔离时仍可调用，不接触COM、不清锁、不修改图纸。
- 记录包含操作编号、工具、结果/错误、工作进程PID、绑定DWG和HWND。成功记录表示工具返回完成，仍须按工具验收范围理解，不能代替审图。
- 本机Codex配置增加诊断工具，客户端超时改240秒；Claude Code无工具白名单，重启服务后可见。实际聊天客户端重连尚未验收。

## 验证证据

- tests/test_isolated.py：真实Python辅助进程挂起注入、超时终止、重复请求零重放、失败结果保留、实例/图纸变化时SendCommand零调用、异步等待期间事件循环可响应。
- tests/test_isolated_mcp.py：真实stdio协议中占锁时CAD请求拒绝，但诊断返回；启动探测不调用COM。
- work/acceptance/client-gate-20260925-072410/report.json：最终异步版本真实MCP画圆，显式绑定独立DWG；持锁时零新增，解除后仅1个圆；保存重开后圆心/半径/句柄符合预期。
- work/projects/isolated-20260925-072044/independent-reverification/report.json：新复制的三页合成工程重开后，隔离工作进程逐项通过线号202、两端连接、BOM、From/To、端子计划、端子编号的原生语义核验。后续只调整MCP异步等待和基础几何目标参数，未改电气算法。

故障注入挂起的是测试Python辅助进程，没有故意卡死AutoCAD，因此不代表真实AutoCAD所有RPC挂起场景均验收。此次未重新生成或视觉验收PDF；PDF隔离执行后的完整专项仍需补测。

## 恢复及剩余边界

查看get_execution_diagnostics，确定最后操作、PID、图纸和结果。先确认工作进程已结束，再通过AutoCAD检查是否仍有命令、模态窗口和已写入实体，并回读电气结果。保留日志，完成独立核验后才能维护性清除中断标记。当前不提供自动清锁或一键继续。

父MCP进程意外死亡时，工作进程可能继续运行；持久标记会阻止新的合作客户端操作，但不会自动杀死孤立工作进程。诊断中的PID和记录状态也不能证明CAD已停止执行。

全工具参数级目标约束、多实例显式选择、COM访问代理、事务回滚及统一项目绑定尚未完成。已拿到的原始COM对象仍可能在检查之间被使用；手动操作、Computer Use和直接COM脚本不受锁保护。返回失败统一隔离较保守，包含本来未写入的参数错误；后续可在有明确提交证据后细分状态。

设计依据：[Microsoft COM初始化](https://learn.microsoft.com/en-us/windows/win32/api/objbase/nf-objbase-coinitialize)、[Python subprocess超时处理](https://docs.python.org/3/library/subprocess.html)。本轮只实现受控执行与诊断基础，没有完成真实TREBI样板、自动恢复或工程交付。
