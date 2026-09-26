# 工具治理与映射补齐：本轮执行结果

2026-09-24，本轮五项计划已执行。当前58个工具定义（原54+能力查询1+尺寸3）；21个默认提供、37个默认隐藏。完整范围见[工具清单](tool-inventory.md)。这不是58个工具全部通过验收。

## 已完成

1. **逐项盘点**：profiles/tool-capabilities.json为默认暴露与验收状态的单一来源；新增工具缺少条目时服务启动失败。
2. **运行时隔离**：默认MCP只注册21个工具；隐藏工具调用返回不存在。实验模式需显式设置KINTO_MCP_EXPERIMENTAL=1，不能视为验证资格。
3. **已知问题处理**：get_symbol_list改为本机真实DWG检索和分页；类别仅覆盖6个已验证符号，不虚构完整目录。create_wire_from_to、move_component、delete_component停止执行。旧梯形图、编号、PLC、父子引用及同步提交命令后返回submitted_unverified；旧WDREPORT分支也不再返回成功。
4. **机械补齐**：新增add_aligned_dimension、add_diameter_dimension、get_dimension_info。目标DWG检查、原生Measurement回读、空TextOverride；标注为非关联，不会自动跟踪源几何修改。
5. **双样板回归**：机械新图及电气两页项目均通过真实MCP；默认工具集与清单一致，隐藏工具不可被普通客户端调用。

## 实机证据

机械：work/acceptance/dimensions-20260924-172043/plate-dimensioned.dwg与report.json。19个对象，120×80外形、四个Ø6孔、孔距100×60；5个原生尺寸对象测量值120/80/100/60/6，保存重开一致；8条孔中心短线端点正确。Computer Use图面检查通过。没有完成尺寸与源实体关联、几何公差或打印验收。

电气：work/projects/relay-demo-20260924-164801/verification-20260924-172348/verification.json为PASS。默认模式重新打开两页、核对9符号、8导线段及原生报表；BOM4类5件，From/To4条，保持正确。

测试：74项非集成测试通过，3项上游mock集成测试未运行。包含代码与清单一致性、真实stdio默认列表、隐藏工具不可调用、已停用入口不连接CAD、真实库查询、尺寸输入校验及已有电气验收测试。

AutoCAD实测中发现实时缩放命令会持续拒绝COM调用；Computer Use确认后退出缩放，继续成功。另一次电气回归遇到不完整属性读取，复查无持续差异；验收保留差异并有限重读，没有改写图纸去迁就期望值。早期失败记录不作为成功证据。

## 客户端与使用边界

本机.codex/config.toml的enabled_tools已同步21项，.mcp.json明确使用非实验模式；两者都是被Git忽略的本地配置。配置未改变订阅登录、密钥或审批策略。已建立的客户端连接尚未核验热更新；应以重连后实际列出的工具为准。

机械常用入口：draw_line、draw_rectangle、draw_circle、draw_text，以及两个尺寸创建工具和get_dimension_info。

电气常用入口：真实符号查询→原生符号插入→读取X?TERMnn→指定端子连接→原生线号→源/目标更新→原生项目报表。

未完成映射：PLC、父子触点、复杂端子排、目录/子装配、国产器件型号与引脚、圆角/修剪/偏移、公差/剖面、打印/PDF、3D与大项目性能。完整DWG文件列表不是完整语义符号映射，测试CAT不是采购映射。

## 依据

- [Autodesk AddDimAligned](https://help.autodesk.com/cloudhelp/2026/DEU/AutoCAD-ActiveX-Reference/files/GUID-9F5CE147-3787-4DD9-8028-8E89BF02A357.htm)
- [Autodesk AddDimDiametric](https://help.autodesk.com/cloudhelp/2023/DEU/AutoCAD-ActiveX-Reference/files/GUID-A713EB17-E229-48E7-BFA3-AF7DE13B09BF.htm)，本机2026实测确认。
- [OpenAI Codex配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)：enabled_tools为工具允许列表。
