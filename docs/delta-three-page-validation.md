# Delta 三页 DI/DO 样板验收（2026-09-26）

默认 `plan_trebi_batch` / `execute_trebi_batch` 新增 schema_version=3、recipe=delta_di_do_three_page、purpose=test_only。旧 v1/v2 保留。

## 实机结果

- 独立逻辑页102、300、405，有效图页数3，使用底部整行TREBI图框。
- HPB11常开按钮、已校验SHA的R2智能黑盒、HLT1G指示灯、7个端子、4个原生跨页箭头，共14个插入对象。
- 11段线的接线属性、图层和线号逐项通过MCP回读；三张图保存关闭重开，属性和四个确切页区引用一致。
- 原生BOM：R2、按钮、灯各1；From/To的9行逐项符合预期，包括按钮14→TB2:X00、TB4:Y00→灯1；两种端子报表各7行。
- 三页A3 PDF经逐页渲染检查，PAGE102/300/405、OF3、前后页导航、字体与底部标题栏正常；导出回执确认源DWG文件未变。
- 341项默认测试通过，3项integration未运行；此测试数量不能代替上述实机证据。

## 映射边界

v3要求一台PNP R2、BUTTON输入Port0/X00、LAMP输出Port2/Y00，固定TEST_DI/TEST_DO和测试供电。调用现有v2 ESI/映射检查；设备实测版本、站号和NC50地址未知可保留，但本配方始终production_ready=false。错误通道、电位、线号、安全用途、未知Revision、错误页清单均在CAD访问前拒绝。

这些是合成信号，不代表I545或O518已完成国产化对应；不测试PLC程序、实物响应和O518闪烁。供电边界端子未互联，不代表完整配电方案。R2仍是有原生连接属性的黑盒，不是参数化PLC模块。

## 本轮发现与恢复

准备脚本用Documents.Item完整路径切换时失败；通过核对三张图均为已保存的空白WD_M+图框、WDP顺序正确、批量尚未开始，留存证据并恢复锁，改为精确路径枚举后激活。没有重放元件插入。

R2资产携带旧DESC3=REFERENCE O518。v3现在显式覆盖为SYNTHETIC DI DO TEST；已经生成的样板通过c:wd_modattrval修正。修改前后ModelSpace句柄、类型、图层、块名、位置、属性和直线端点快照只允许该属性差异；保存重开通过，From/To及两种端子报表逐行不变，BOM不再含O518。此修正由本机验收脚本调用原生API，不宣称通用MCP修改能力已完成。

## 待完成

在独立副本中验证原生元件替换、通道改接以及相关引用/报表更新，再封装受约束的修改入口。当前不支持将新建批量配方重放到已有内容的图纸。真实国产化信号映射和硬件验收仍独立进行。

私有验收目录：CAD_Projects/TREBI_Localization/electrical/poc/delta-three-page-20260926。spec.json、batch.json、reopen-*.json、final-*.json、description-fix.json、acceptance-summary.json和pdf.json保存独立阶段证据。早期BOM中的旧描述是历史记录，以final-bom.json为最终值。
