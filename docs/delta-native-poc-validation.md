# Delta 原生 POC 验证（2026-09-26）

通过真实默认 MCP 单工具调用建立一页 TREBI 格式测试工程，逻辑页 405、OF 1。R2 候选智能黑盒 76 接线点、测试指示灯、3 个端子、4 段原生连接与 3 个测试线号通过回读；保存重开后线网一致。原生 BOM 的 R2 与测试灯各 1 件，From/To 四条端点以及三项端子号/线号均做确切对照。PDF 已检查图面，未见裁切或文字重叠。

真实本地 ESI 经 plan_delta_r2_io v2 解析，两个 Revision 分开识别；合成未知 Revision 被预检拒绝。没有连接实物，NC50 地址和站号仍未知，ready_for_drawing 保持 false。

边界：当前 R2 为通用 Electrical 黑盒候选，不是参数化 PLC 验收；模块 TB1 电源/GND/FG 与输入 S/S 尚未接线；原 O518 端子、替换灯选型、默认 TREBI 批量配方仍待完成。候选测试符号和私有图纸未加入公开样例。不能据此认定完整国产化回路或安全功能合格。

修复 src/autocad/utils.py：属性读取不再吞异常、返回残缺字典；对已知 COM 忙碌 HRESULT 有限重试整份只读快照，其他错误明确向上传递。新增两项回归测试，默认 309 passed / 3 deselected。

私有证据：CAD_Projects/TREBI_Localization/electrical/poc/delta-p0-20260926-101849。首次 PDF 空字段预检失败，第二次副本属性读回失败，核对源文件哈希及未打印状态后分别恢复；第三次导出、源文件不变及视觉检查通过。保留全部失败回执，不将自动重试视为可靠性保证。


后续：模块电源/GND/FG 与 S/S 四段测试连接、IEC 正文字体及 v2 符号新图复用已验收。默认入口现已支持受限 Delta 测试配方，详见 [Delta 批量验收](delta-batch-validation.md)。前述缺口是早期阶段记录；正式选型、实物和地址匹配仍未完成。
