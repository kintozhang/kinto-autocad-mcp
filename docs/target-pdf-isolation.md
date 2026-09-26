# 统一目标参数及隔离 PDF 验收

2026-09-25：170项默认测试通过，3项integration未运行；62项定义、25项默认、37项隐藏。

## 目标约束

全部已注册CAD工具通过统一入口增加可选 expected_drawing_path（绝对DWG路径）和 expected_instance_hwnd（AutoCAD窗口句柄）。默认工具中的21项CAD工具均通过真实stdio schema检查；4项元数据/诊断工具不增加这些参数。隐藏工具开放实验模式时也使用同一入口，但这不代表隐藏工具的业务效果已验收。

填写参数时，工作进程在进入工具函数前检查目标；不匹配返回 target_rejected、submitted=false，保存not_submitted记录并正常释放锁。错误请求不会切换实例或图纸，也不会误留下结果未知的隔离标记。进入工具之后的失败、超时仍隔离，不重放。

参数默认留空以兼容旧调用，此时仍绑定执行开始的活动图纸。这不是强制填写目标，也不是自动选择另一AutoCAD实例。统一参数不等于所有原始COM访问已原子化；手动切图、直接COM、Computer Use仍须与MCP串行操作。项目WDP检查沿用各原生工具的实现。

工作进程返回内部阶段回执，明确区分not_entered与completed；MCP对外保持原有字典结构。扩展签名时显式解析类型注解，修复FastMCP把返回结果额外包在result字段中的兼容问题。

实机证据 work/acceptance/client-gate-20260925-073127/report.json：新DWG副本中错误路径及错误句柄均被拒绝、图元零新增；随后正确请求只新增一个圆，保存重开一致。原有占锁冲突也通过。

## 隔离式 PDF 完整复验

work/projects/target-pdf-20260925-073245/final-acceptance.json 为最终PASS。

- 从已验收三页合成双语项目创建独立副本，明确指定预期DWG及HWND，通过默认MCP隔离工作进程出图。
- output/pdf/target-pdf-20260925-073245.pdf：三页横向A3，NTS；顺序、内容流和页面结构通过，活动原图恢复、源文件哈希不变。
- 三页110dpi渲染逐页目视通过；每页十个中文标题栏标签可提取；页码1/2/3、版本B及中英图名显示正确。中文已验证的是标题栏，不是整图说明翻译。
- 独立重开后，线号202及两个连接、BOM、From/To、端子计划、端子编号通过；复验后源WDP/DWG哈希仍一致。

首次独立复验失败于COM的Item.Close方法获取，PDF本身已导出成功。保留原acceptance.json及失败目录；修复验收脚本为重新枚举后有限重试只读方法获取，拒绝关闭未保存图纸，Close写入本身只调用一次。独立补验记录在 independent-reverification-073525/report.json，没有重发PDF导出。

复测脚本 scripts/isolated_pdf_smoke.py --write 使用本机私有合成种子；不会覆盖正式TREBI图纸。最终PDF是功能样板，不是TREBI施工图。

下一阶段仍是自动恢复的证据核验、正式模板字段完善、TREBI原图/国产件映射及真实回路样板。此次没有新增PLC、复杂端子排、机械定比例或3D能力。
