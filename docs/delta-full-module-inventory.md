# Delta R2 完整端子清单（2026-09-27）

已有默认工具plan_delta_r2_io新增schema_version=3。调用：

```json
{"schema_version":3,"purpose":"test_only","module_id":"IO_TEST"}
```

只读返回5个端子排分区、76个可接线端点：32DI、32继电器DO、8个输出公共端、TB1三个电源端、TB3共用S/S。TB2的N.C单独列为不可接线保留端。端点唯一键包含模块实例和端子排；TB2/X00与TB3/X00保持不同。输入共用同一S/S，输出每4路关联一个C组。

来源为已登记哈希的R2-EC系列手册P35–39；PDO分组沿用现有资料profile。全局PLC地址、电位、站号、输入模式和实物Revision均为空，ready_for_drawing/production_ready均false。此入口不生成DWG、不连接控制器，不把手册映射变成实物确认。

真实stdio调用生成76点清单，默认回归479项通过。私有输出为CAD_Projects/TREBI_Localization/electrical/poc/DELTA-FULL-20260927/module-inventory.json；当前仅为验收准备目录，还没有新DWG。

本机2026的c:wd_find_sel_plc查询R2-EC0902D0和R2-EC0902均返回nil。该查询只说明当前本机目录无匹配，不能推断所有安装或供应商库都不支持。下一步需建立专用PLC定义、验证分段模块/BOM只计一台、逐端子回读及接线报表。现有76点HBB智能黑盒及AB 1771-IAD示例都不等于该专用PLC定义。

I545＋O529完整原图路径和新Delta绑定是另一项验收；此前灯片段不因此自动升级为完整回路。本轮没有修改正式工程或原始资料。
