# TREBI 位号计划与电气标题栏联调

2026-09-25。244项默认自动测试通过，3项integration未运行。仍为62项工具定义、25项默认工具；新位号规划和标题栏映射为内部模块与验收脚本，尚未新增默认MCP接口。

## 位号规则

src/autocad/trebi_component_tags.py 的 plan_tags(manifest, components) 在绘图前生成位号计划：

- primary 明确 owner_page（所属功能页）、drawing_page（实际绘制页）和类别。Q/F/T/K/M/A/B/S 支持生成 `-页号类别序号`，例如 -112K1。
- child 明确 parent_id，继承对应主元件位号，不使用触点所在页重新编号；第54页的触点仍可属于第112页的 -112K1。
- existing_tag 保留，不自动改号。所属页与绘制页不同，或已有位号不符合新规则时，给出复核提示。没有实现既有DWG批量重编号。
- 先预留已有位号与明确指定的sequence，再按稳定组件ID顺序分配可用序号。重复物理元件位号、序号冲突、无主元件的触点、触点位号不一致或无效图页均拒绝。
- X类端子排/连接器和W类电缆使用independent显式位号；不自动加页码。此处登记物理设备标识，不把同一端子排的每个针脚当作不同物理设备；端子/针脚编号仍需另行处理。

规划目前使用项目内单一位号命名空间，多INST/LOC项目拒绝。计划只知道传入清单；对既有工程必须先收集完整设备清单并填existing_tag。生成结果需作为已分配身份保存，不能省略既有设备后再运行而声称全项目不会重号。MCP insert_electrical_symbol 本身仍接受显式属性，尚未自动扫描项目分配位号。

公开合成样例与只读预览：

```
.venv/Scripts/python.exe -m scripts.plan_trebi_components examples/trebi-page-manifest.json examples/trebi-component-plan.json
```

## 标题栏接入

profiles/trebi-electrical-a3.wdt 使用 `PAGE = SHEET`、`OF = LINE20`，块为KINTO_TREBI_ELECTRICAL_A3。LINE20是本项目明确保留的有效图页总数字段，创建合成工程时从清单计算；不使用最大逻辑页号或PDF页数。原生c:wd_tb_process_one更新PAGE/OF；PREV/NEXT通过c:wd_modattrval更新为清单顺序。后两项不是WDT原生导航宏。

src/autocad/trebi_title_mapping.py 写入前核对：清单DWG绑定、实际WDP成员与顺序、WDT内容、LINE20有效页数、唯一图框/WD_M及SHEET一致。LISP内部同时校验固定WDP和固定DWG路径。未知映射、图页总数不一致、重复DWG或页序不符即拒绝；不会静默覆盖原项目的LINE20。

这不是自动监视器：新增/撤销图纸后要先更新清单及项目有效总数，再显式调用更新。其他标题字段（客户、图名、完整修订记录等）尚未纳入这份WDT。本轮机械模板未修改。

## 本轮实机与失败记录

- work/projects/trebi-zones-20260925-102012：活动文档FullName读取失败，发生在SendCommand之前，无WDP/DWG创建。Computer Use确认界面后，切到CAD前台，COM恢复可读；有恢复证据，不将其描述为根治COM异常。
- work/projects/trebi-zones-20260925-102445：创建WDP时标题列表首项占位遗漏，原本LINE20落在LINE19；总数预检拒绝，标题仍为测试初值999。保留失败副本和回读记录，修正的是创建列表索引。
- work/projects/trebi-zones-20260925-102651：PAGE/OF/PREV/NEXT由999更新为54/2/-/112与112/2/54/-。计划生成-112K1，经默认MCP插入线圈及异页触点。更新引用后出现COM拒绝调用，原始acceptance.json保留FAILED。独立回读确认源/目标112.8与54.2、触点/线圈112.8与54.5、线号501；未重复执行跨页更新。reference-readback.json与recovery-evidence.json记录实际结果、无关元件属性保持不变和保存。
- 同目录guarded-title-validation.json：固定DWG目标保护下，两页原生标题更新再次通过，电路属性不变。

最终独立验收 work/projects/trebi-zones-20260925-102651/reverification-103406/report.json 为 PASS：标题字段、引用和原生设置保存重开一致；线号501，BOM继电器-112K1数量1、端子数量2，From-To跨页54/112及两类端子报表通过。原始FAILED记录不覆盖；会话隔离标记已按证据清理。功能安全回路未验证，本次继电器仅用于位号/关联测试；合成型号不是采购型号。尚未执行本轮电路PDF和逐页视觉验收。

## 依据

位号与页号规则来自用户确认。原生API签名来自本机2026 ACE_API.chm的c:wd_proj_wdp_write、c:wd_tb_process_one、c:wd_modattrval；标题列表占位及LINE20映射以本机WDP和回读结果核实。
