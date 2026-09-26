# Delta R2 默认批量入口（2026-09-26）

默认 `plan_trebi_batch` / `execute_trebi_batch` 新增 schema_version 2 的受限测试配方。
原 schema_version 1 的继电器、触点、端子及跨页流程保持原有约束。

```json
{
  "schema_version": 2,
  "recipe": "delta_r2_output_poc",
  "purpose": "test_only",
  "symbol_path": "C:/private-symbols/HBB1_KINTO_R2_EC0902_TEST.dwg",
  "manifest": {
    "schema_version": 1,
    "entries": [{"id": "405", "kind": "drawing", "logical_page": "405",
      "include_in_total": true, "drawing_file": "DELTA-BATCH-405.dwg"}]
  }
}
```

示例符号路径需要指向本机已验收的 v2 文件，文件不随代码分发。规划器核对文件 SHA-256；旧版或修改后的资产会拒绝。
本机独立新图的 MCP 插入、76 个接线点、字体和保存重开通过后，才固定此哈希。

配方固定生成 R2 黑盒、测试指示灯、7 个端子及 8 段导线。位号由逻辑页生成 A1/H1。
模块电源 PWR24/PWR0 与 I/O TEST24/TEST0 分层；FG_TEST 独立；TEST518 是测试线号，不是 O518、Y00 或 NC50 地址。
底部 73..76 接线点使用 X8TERM 朝下；插入后须精确核对 76 个端子名称，才能继续接线。
不能覆盖元件或连线配方；purpose=production 明确拒绝。PLC 地址、实物 Revision、原端子和替换件选型尚未确认。

执行仍要求已打开并保存的单页空白 TREBI 工程、正确 WDT/LINE20 和显式 drawing_path、expected_drawing_path、expected_instance_hwnd。
已有图纸内容在写入前拒绝；中途失败保留回执，不自动回滚或重放。

实机证据位于 CAD_Projects/TREBI_Localization/electrical/poc/delta-batch-v2-20260926：
真实默认 MCP 批量生成通过；保存重开后 8 段线网逐项核对，BOM 两项各 1 件、From/To 8 条、端子 7 项与前次独立 POC 逐字段一致。
完整实际供电、保护选型和接地设计尚未完成；相同 TEST0 的边界端子并不表示图中画出了端子间实体连接。
该配方是通用智能黑盒测试，不是参数化 PLC 模块或正式国产化项目。

新增 9 项自动测试覆盖正式用途拒绝、符号篡改/缺失、配方覆盖拒绝及电源标识分离；默认回归 318 passed / 3 deselected。

本轮原生 PDF 导出及全页渲染检查通过：IEC 正文可读，无重叠或裁切，PAGE 405 / OF 1，打印过程源 DWG 哈希保持不变。

后续功能复核（2026-09-26）：私有原 PLC 的 O518 含两档闪烁，按备份采样推算快档约 1.953 Hz，而 R2 手册继电器输出工作频率为 1 Hz。该测试配方仅验证静态接线，不能作为正式 O518 等价替代；目标输出驱动选型暂不冻结。私有证据见 CAD_Projects/TREBI_Localization/reviews/o518-mapping-20260926/logic-review.md，原 PLC 未写入代码仓库。

## 批量入口异常处理加固（2026-09-26 后续）

最终验收增加导线句柄/接线点及图层核对，不再仅核对线号；每段校验独立记录 verify_wire 步骤。可捕获异常明确保存 failed_step、failed_or_unknown 和错误文本，仍禁止自动重放；进程被强制终止时 entered 状态仍表示结果未知。符号文件不可读转为受控预检错误。

默认回归 325 passed / 3 deselected。此前保存重开的 8 份真实原生线网回执全部通过新增校验。本轮实时读取被目标检查拒绝（target_rejected / <unknown>.FullName / submitted=false），没有新 CAD 写入，不计作新增实机验收。证据：独立工程 hardening-raw-io_supply.json。

## 文档查询恢复与实时复验

同日后续通过 Computer Use 恢复 AutoCAD 前台，确认活动 DELTA-BATCH-405 图纸与命令行空闲后，8 段导线的新端点/图层/线号校验全部通过真实默认 MCP 只读调用。证据为工程 hardened-wire-readback.json。本轮未保存、重开或修改图纸，不能解释为新增保存重开验收。窗口恢复后查询成功仅说明本次恢复有效，不证明所有 COM 故障均已解决。

活动文档元数据探测耗尽有限重试后，现返回明确的 ComBusyError，提示检查 CAD 窗口、远程会话及弹窗，并保留原异常原因；不自动切换文档、不重试写入。默认回归 326 passed / 3 deselected。

## 真实 MCP 拒绝路径验收

正式用途、错误活动目标、已填充图纸重复执行三个请求均返回 submitted=false；各请求完成后互斥标记均释放。调整预检顺序，已有内容优先报告 populated drawings，而不是被 unsaved 提示掩盖。未保存任何现有修改。

前后对比实体句柄/类型/图层、块属性、导线坐标、文档保存状态及 DWG/WDP/WDT 哈希完全一致。证据：测试工程 negative-preflight-populated-first/acceptance.json 及 before/after.json。旧顺序结果保留在 negative-preflight。326 项默认测试通过。此验证证明这三种受控拒绝不会提交绘图，不代表进程崩溃后的自动续跑已实现。

中途失败专项：四种适配层故障注入通过，默认回归 330 passed / 3 deselected。恢复检查见 [批量中断处理](batch-recovery.md)；无自动续跑，未在真实 CAD 中注入崩溃。
