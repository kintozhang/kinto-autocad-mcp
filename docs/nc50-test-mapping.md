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
