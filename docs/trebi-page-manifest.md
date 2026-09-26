# TREBI 有效图页清单

2026-09-25：215 项默认测试通过（3 项 integration 未运行）。本轮是离线项目规则与标题栏数据生成，不是新的 CAD 写入或原图页数核验。

## 规则

- PAGE 是稳定的逻辑图纸地址，允许跳号，不要求小于 OF，不使用 PDF 物理页序。
- OF 按清单中 kind=drawing 且 include_in_total=true 的条目数计算。必须明确是否计入，不能默认为全部文件；kind=attachment 必须排除，且不能占用逻辑页号。
- 所有图纸条目的逻辑页号必须唯一，包括被排除的图纸；同一逻辑页的多个历史版本应在版本档案中维护，不混入当前清单。
- PREV/NEXT 按清单有效图纸顺序生成，不对页号重新排序或编号。附件与排除的图纸不进入导航；排除的图纸不生成标题栏更新字段。
- 326.7 按逻辑页326、第7区解析，并检查目标是否存在于有效图页清单。不会据此跳转到PDF物理第326页。
- 新增或删除有效图页时重新生成OF和导航，已有PAGE不变。不负责自动分配新逻辑页号，也尚未自动刷新DWG。

功能页范围从 profiles/trebi-page-groups.json 读取，依据用户确认：0～14 总览/供电；50～63 配电/驱动；100～123 现场功能；300～329 主柜/I/O；400～421 其他柜体；500 操作台。范围可配置，重叠或重复组标识拒绝；范围外页号保留并标记pending，不猜测功能或自动改号。这不是对原PDF逐页分类的结论。

## 数据与运行

公开合成样例：examples/trebi-page-manifest.json。含逻辑54、112、326三张有效图，一项说明书附件，以及排除的327页。因此输出PAGE326 OF3，而不是直接写OF96。

```
.venv/Scripts/python.exe -m scripts.plan_trebi_pages examples/trebi-page-manifest.json
```

该命令只向标准输出打印规划。内部接口 src/autocad/trebi_project_pages.py 的 plan() 返回有效页数、页序、分组及每张有效图的PAGE/OF/PREV/NEXT；resolve_reference() 解析并核验逻辑引用目标。函数不修改输入、不访问CAD、不修改PDF。

本机已生成可检查结果：work/acceptance/trebi-page-manifest/title-field-plan.json。

测试覆盖PAGE326 OF96、显式顺序、附件和作废页排除、重复页号/缺少计数标记拒绝、功能组边界及不重编号的插页。96来自合成测试清单，不表示已清点原始TREBI文件。

## 下一步接入

将清单条目绑定到实际WDP成员及DWG，再做写入前一致性检查，使用新电气图框的原生WDT映射更新标题栏，并逐页回读、保存重开验收。当前未新增MCP工具、未修改现有DWG，25项默认工具保持不变。旧机械模板不受影响。

后续进展：已完成显式DWG绑定、WDP成员/顺序核对和两页原生标题栏联调，见[位号与标题栏验收](trebi-component-title-validation.md)。仍未提供默认MCP批量创建/更新入口。
