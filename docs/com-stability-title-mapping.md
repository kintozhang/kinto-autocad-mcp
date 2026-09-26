# COM 稳定性与标题栏字段映射（2026-09-24）

## COM 已实施修复

原 connection.is_connected 把任意 COM 异常都当作断连并清空对象。本轮区分忙碌 HRESULT、明确断连 HRESULT 和其他异常：忙碌时有限只读重试，耗尽后明确返回忙碌错误并保留对象，不重新绑定；只有明确的断连才清空连接。连接初始化不再通过 Visible=True 改动窗口状态。

src/autocad/com_runtime.py 提供 read_call，只允许传入只读操作或方法查找；默认最多8次、间隔0.15秒。SendCommand、Open、Save、Activate、AddCircle 等写操作没有自动重试。连接探测、活动文档和 ModelSpace 获取已接入只读重试；PDF 的成员快照改用索引访问集合，避免依赖瞬时失效的枚举接口。

wait_for_document 同时核对活动文档完整路径、GetAcadState().IsQuiescent 与 CMDACTIVE，要求连续两次就绪；目标变化立即拒绝，等待默认8秒。仅此已知属性探测允许临时 AttributeError 后重新获取文档；通用只读重试不会吞掉未知 AttributeError。打印副本打开和原图恢复已接入就绪检查。

依据：[Autodesk 2026 GetAcadState](https://help.autodesk.com/cloudhelp/2026/DEU/AutoCAD-ActiveX-Reference/files/GUID-820F93B4-7B83-4708-8E21-0D43D7D1C828.htm)、[Microsoft COM 错误代码](https://learn.microsoft.com/en-us/windows/win32/com/com-error-codes-3)。

## 实机及故障注入证据

work/acceptance/com-runtime-20260924-224317/report.json 为 PASS：两张独立模板副本交替激活20次并读取属性，连接对象保持一致；仅添加一个半径2的圆，图元数量只增加1，保存重开后数量和半径正确；默认 MCP 查询通过，仍为24项工具。

故障注入测试验证忙碌 HRESULT 恢复/耗尽、真正断连、未知错误不重试、持续忙碌不重新连接、目标改变拒绝、写入只提交一次，以及打开后的临时文档元数据缺失。实机20次切换成功不代表已经覆盖所有忙碌时机；首轮脚本错误地要求元数据工具返回 success 字段，失败记录 com-runtime-224146 保留，修正的是测试断言。

总回归：148 passed，3 deselected。新版就绪探测也在三页标题栏复制、保存重开以及后续原生报表复验中执行。

## 尚未解决的边界

- 不是所有工具内部的每个 COM 属性读取都已经接入重试层，后续按实际调用路径扩展。
- 8秒是轮询预算，不是阻塞 COM 调用的硬超时；单次 COM 调用挂起仍可能超出预算。
- 没有跨 Codex/Claude 进程的全局互斥，也没有独立工作进程/STA队列或 .NET 桥接。
- 写入结果未知时仍须查回执和实体，不得自动重发。崩溃、模态对话框、插件故障等不能用忙碌重试保证恢复。
- 本轮未重新出图或目视检查新字段版本 PDF；PDF 就绪检查的实际条件在同类 Open/Activate 生命周期测试中验证，后续应继续完整出图专项。

## 双语标题栏原生映射

增加 profiles/titleblock-zh-en.wdt：

```text
BLOCK = KINTO_TB_A3_ZH_EN
PROJECT = LINE1
REV = LINE10
SHEET = SHEET
```

独立工程使用同名 .wdt 文件，由 Electrical 原生 c:wd_tb_process_one 更新，不是 Python 直接写最终属性。调用签名来自本机2026 ACE_API.chm 的 c_wd_tb_process_one.html；使用16位绘图选项（第8位 SHEET）和零起始 LINE1/LINE10 索引0、9。在线格式依据：[Autodesk WDT 文件说明](https://help.autodesk.com/cloudhelp/2018/ENU/AutoCAD-Electrical/files/GUID-877CC0C4-1BB6-4F0F-97EA-CCAE81FC9F0D.htm)，已在本机2026实测。

证据 work/projects/title-mapping-20260924-224719/mapping-acceptance.json：三页 PROJECT 自动改为 KINTO NATIVE TITLE TEST，REV 从A变B，SHEET 从原来的 n/3 变为原生页号1、2、3；其他字段及电路快照保持不变，保存重开一致。independent-reverification/report.json 再次通过默认 MCP 检查202线号、BOM、From/To、端子计划和端子编号。

首轮发现图纸打开后 FullName 元数据暂缺，第二轮发现 WDP 首行 BOM 使测试项目名替换未生效，均保留失败副本；现读写显式处理 UTF-8 BOM，并先断言测试项目名已设置。

映射目前只验收这三个字段。SHEET 不含总页数；图名、图号、绘图/审核人、日期、总页数、中文项目描述更新、复杂修订等仍待验证。该映射是可复用 WDT 配置加内部验收脚本，未新增默认 MCP 批量更新工具。正式 TREBI 工程没有修改。
