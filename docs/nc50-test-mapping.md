# NC50测试地址规划验收

默认MCP `plan_delta_r2_io` 新增schema_version=4。此版本号属于I/O规划器，与TREBI绘图批次版本独立。

依据NC5手册PDF323/324（印刷4-112/4-113，4.10.3）：EIO Port范围501..520且不可重复；Start Address范围256..511且需检查末点。R2-EC0902例子明确：起始256时输入X256..X287、输出Y256..Y287。所以32点模块最后合法起始值为480。物理端口到通道的次序结合R2手册PDF35..38、113及ESI；字节内位仍是离线候选。

EIO序号按可识别远程模块顺序，伺服驱动器不计入此排列；不能将两台R2的EIO序号直接当成含六台伺服的EtherCAT全网从站位置。EIO Port 501..520与R2物理Port0..3是不同字段。Mode在此手册用于模拟量范围，当前数字R2测试不自行设置它；Polarity/Disc及事件PDO也不推定实际配置。

## 默认入口

```json
{
  "schema_version": 4,
  "purpose": "test_only",
  "mapping": "此处传入现有v2 mapping对象，不能传字符串",
  "eio_assumptions": [
    {"module_id":"IO_A","eio_sequence":1,"eio_port":501,"start_address":256,"source":"明确的测试假设"}
  ]
}
```

完整可执行请求保存在独立验收目录。每台已登记模块须有一条假设；检查32点X/Y范围重叠、重复EIO端口/序号、方向与物理端口、共用端约束和ESI。序号1..20是当前工具的受限测试范围。已有显式PLC地址若与候选冲突，test_plan_valid=false，并返回冲突信号；绝不覆盖原地址。

返回candidates单独保存原信号、端点、线号、电位、候选NC50地址及PDO。mapping中的global_plc_address、station、observed_identity保持原输入语义；process_image_offset不推算。正式放行始终false。不得将候选包装成observations再提供给绘图或审查入口。

## 2026-09-27验收

独立目录：`C:/kinto/CAD_Projects/TREBI_Localization/electrical/poc/NC50-MAPPING-20260927`。

三个新默认stdio会话：起始256返回I545候选X256、O529候选Y256；改为288返回X288/Y288，原位号、端子、电位、线号、PDO保持不变；起始481被拒绝。561项回归通过，3项integration排除。两种Revision仍由ESI验证，未选成实物版本。此前R7图纸、报表和PDF未改动；本轮是映射规划与变更检查，不是新DWG生成或在线NC50验收。

真实资料已存于私有CAD项目，厂家原件未复制到代码仓库。手册SHA256：7057dc26fb147ebe68d64b590827ec8d5ea8bcbd859ebc08992c0367c75d71a2。


## 候选地址进入原生绘图（已独立复验）

默认execute_trebi_batch的四路径配方可选eio_assumptions，与规划器同结构。它在写入前重新计算候选，冲突或越界拒绝。按钮/灯DESC2分别写入TEST NC50 X256/Y256；R2描述写明TEST CANDIDATES - NOT VERIFIED。不将候选放入线号、SIGCODE、TERM、plc_address或observations。

最终回读核对原生属性；额外要求BOM中与对象句柄、目录号和位号对应的唯一行，其DESC1/2/3与原生属性逐项一致。未知实物绑定继续阻断正式出图。新增测试覆盖错误描述、错误句柄、缺行及批量预检拒绝。独立保存重开、四类报表和两页PDF视觉验收已通过，详见下节。


## 2026-09-27独立绘图结果

独立工程：P0-PATHS-NC50-R2-20260927。逻辑PAGE102/300，OF2。测试假设为IO_A、EIO序号1、Port501、Start Address256；按钮原信号I545的候选地址X256，灯原信号O529的候选地址Y256。候选写入DESC说明，未替换端子、线号或原信号，也未填入observations。

### 已验证

- 默认MCP批量完成原生元件、17组线网、跨页及四芯电缆生成。
- 独立关闭重开后，76个R2接点、4条路径、原生属性及四类报表逐项复验通过；报表行数BOM6、From/To15、端子计划9、端子线号9，前后相同。
- BOM以对象句柄匹配，DESC1/2/3与原生回读一致，包含候选地址说明。
- PDF两页全页视觉检查通过，6个内部链接、2个书签、0个SHX文字批注；候选标注与测试水印清晰，无遮挡裁切。
- 571项回归通过，3项integration排除；图纸源哈希不变。
- 默认audit_cad_project的P0路径检查通过。真实设备、地址/PDO绑定和工程审核仍缺失，正式出图保持阻断；不影响此次离线测试通过。

### 故障与修复记录

第一份NC50工程停在线号写入后的只读查询：独立回读证实PWR0已写入，现场保留。修复只读线网查询中被包装的COM忙碌异常；不会重复写线号、插元件或接线。标准inspect/release恢复后，在第二份空白工程复测。

第二份默认批次完成图纸与四类报表后，校验器误把配方未指定的R2 DESC1当作空值；原生符号和BOM实际均为R2-EC0902D0。修复为先验证配方指定值，再比较BOM与完整原生属性。没有重画或改写DWG；以独立保存重开及重新导出的报表完成复验。因此原批次失败回执仍保留，不标成一次无中断通过。

PDF首次预检因COM忙碌在写入前拒绝；第二次默认MCP导出成功。

绘图版本73b3743，校验修复版本49ddbc9。证据见evidence/failed-batch-validator.json、independent-reopen.json、native-verified-receipt.json、pdf-mcp2.json、pdf-visual-review.json、audit-mcp.json。测试产物与失败现场均在CAD_Projects，原R7工程保留。


## 256到288的独立重建验收

2026-09-27，使用现有代码a6db8f5及默认MCP入口完成。本轮未修改程序，沿用571项回归基线，不重复宣称本轮运行全部单元测试。

起始地址改为288后，在新的空白TREBI两页工程中重建；不是就地修改原256工程。默认批量完整一次通过，独立保存关闭重开、四类报表及PDF导出也一次成功。

### 变更与保持项

| 元件/属性 | 256基准 | 288样板 |
| --- | --- | --- |
| 按钮DESC2 | TEST NC50 X256 | TEST NC50 X288 |
| 灯DESC2 | TEST NC50 Y256 | TEST NC50 Y288 |
| R2 DESC3 | NC50 X256 / Y256 | NC50 X288 / Y288 |

原信号I545/O529、物理端子、线号、电位、四芯、插头插座配对与跨页引用保持一致。新工程的九个LINKTERM UUID重新生成，已检查UUID合法、端子分组关系一一对应。对象句柄和工程文件名是局部标识；报表比较仅规范化这些标识及已核对的端子UUID，未忽略业务字段。

### 验收结果

- 76个R2接点、17组线网和4条原生路径均通过。
- BOM6行，只出现上述三处预期描述变更；From/To15行、端子计划9行、端子线号9行与基准一致。
- 重开后四类报表逐行一致；原256项目文件哈希不变，新图源哈希在PDF导出后不变。
- PDF两页视觉通过；X288/Y288可读、无重叠裁切；6个内部链接、2个逻辑页书签、0个SHX文字批注。
- audit_cad_project的P0路径检查通过；实物、实际NC50地址/PDO与工程审核仍未知，所以正式出图保持阻断。候选测试通过不依赖实物已到位。

证据位于evidence/batch-receipt.json、independent-reopen.json、change-comparison.json、pdf-mcp.json、pdf-visual-review.json和audit-mcp.json。图纸在drawings/，四类报表在reports/，样图在exports/NC50-X288-Y288.pdf。


验收目录：`C:/kinto/CAD_Projects/TREBI_Localization/electrical/poc/P0-PATHS-NC50-288-20260927`。
