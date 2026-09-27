# Delta R2 完整端子清单（2026-09-27）

已有默认工具plan_delta_r2_io新增schema_version=3。调用：

```json
{"schema_version":3,"purpose":"test_only","module_id":"IO_TEST"}
```

只读返回5个端子排分区、76个可接线端点：32DI、32继电器DO、8个输出公共端、TB1三个电源端、TB3共用S/S。TB2的N.C单独列为不可接线保留端。端点唯一键包含模块实例和端子排；TB2/X00与TB3/X00保持不同。输入共用同一S/S，输出每4路关联一个C组。

来源为已登记哈希的R2-EC系列手册P35–39；PDO分组沿用现有资料profile。全局PLC地址、电位、站号、输入模式和实物Revision均为空，ready_for_drawing/production_ready均false。此入口不生成DWG、不连接控制器，不把手册映射变成实物确认。

真实stdio调用生成76点清单，默认回归479项通过。私有输出为CAD_Projects/TREBI_Localization/electrical/poc/DELTA-FULL-20260927/module-inventory.json；当前仅为验收准备目录，还没有新DWG。

本机2026的c:wd_find_sel_plc查询R2-EC0902D0和R2-EC0902均返回nil。该查询只说明当前本机目录无匹配，不能推断所有安装或供应商库都不支持。这不构成绘制R2的阻断：R2是EtherCAT远程I/O，控制逻辑在NC50E-FE内置PLC中。可以沿用经验证的Electrical智能元件；参数化PLC I/O仅是一种可选制图表示，不是设备身份或必需前提。AB示例仅验证API，不能冒充R2。

I545＋O529完整原图路径和新Delta绑定是另一项验收；此前灯片段不因此自动升级为完整回路。本轮没有修改正式工程或原始资料。


## 远程I/O语义与现有符号复核

规划输出新增device_role=ethercat_remote_io、executes_plc_program=false、intended_controller=NC50E-FE、logic_owner=controller_internal_plc。intended_controller表达项目意图，不代表已连接实物。EtherCAT站号、物理接口及电缆分配未验证，单独保留未知；76点只包括离散I/O和电源，不包括通信连接器针脚。

每个物理端点关联现有哈希固定HBB测试符号的electrical_connection属性。批量插入的verify_insert改为使用同一完整清单，防止规划与绘图维护两份不同的端子表。TB2/X00与TB3/X00、S/S与C0..C7、模块GND与现场回流继续分别核对。

本轮通过真实MCP回读既有delta-three-page独立工程中的R2块，76个接线属性与清单全部一致，未修改几何。证据保存在DELTA-FULL-20260927/existing-symbol-readback.json和existing-symbol-validation.json。默认回归481项通过。这里只证明端子属性对应，不证明所有76点外接线、EtherCAT通讯或NC50程序已经验收。

后续优先沿用现有智能符号完善I545/O529完整链路；若因页面密度需要分段显示，再单独验证跨页身份和BOM一台计数，无需先强制改造为PLC目录条目。
