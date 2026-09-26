# TREBI 小项目默认 MCP PDF 验收

2026-09-25：默认export_electrical_project_pdf新增template_mode="synthetic_trebi_a3"，工具数量保持64项定义/27项默认；273项默认测试通过、3项integration未运行。

## 行为

在全部成员已打开并保存、活动项目/目标一致的条件下，先核对每页唯一TREBI图框与WD_M、图框原点/比例/旋转、原生逻辑页号及X分区、OF有效页总数、PREV/NEXT清单顺序。预检失败不生成打印副本。当前PDF工具的失败仍按通用隔离策略处理，需读诊断确认，不自动重试。

通过AutoCAD的原生PlotToFile打印独立DWG副本；A3横向、monochrome.ctb、适合纸张、NTS。保留原图PAGE/OF，在图框顶部外侧另加PDF SHEET 1/2等测试标记。打印结束恢复原活动图页，核对WDP和全部源DWG的SHA256不变。此模式不等于机械定比例打印，不覆盖任意图框或任意密度的电路自动排版。

调用示意：export_electrical_project_pdf(project_path=<绝对WDP路径>, output_path=<新PDF绝对路径>, template_mode="synthetic_trebi_a3", expected_drawing_path=<当前成员DWG>, expected_instance_hwnd=<实际实例>)。输出不得覆盖已有PDF。

## 本轮证据

源工程为work/projects/trebi-batch-20260925-110804/，是前轮默认批量生成的两页合成工程；两页包含端子/跨页连接与未接线的继电器父子引用测试，不是完整设备功能电路。

- 成品：output/pdf/trebi-batch-20260925-112324.pdf
- 打印清单：output/pdf/pdf-job-15608dc85c644f57b5c7f9f3d6a6edcb/plot-manifest.json
- 综合验收：work/projects/trebi-batch-20260925-110804/pdf-acceptance-112324.json，PASS
- 出图后独立重开及四类原生报表：同工程reverification-112440/report.json，PASS
- 逐页渲染：同工程pdf-review/page-1.png及page-2.png，150 DPI人工视觉检查通过

PDF结构为2页、1191×842 pt、旋转0；合并前后内容流指纹一致。标题栏保留PAGE 54/112、OF 2和正确前后页；图框顶部0..9完整，中文/英文可读。501线号、源112.8/目标54.2、子触点112.8/线圈54.5均可见，未发现裁切或文字重叠。继电器引用符号保留在右侧图框内。

源WDP和DWG哈希不变；恢复源活动图页成功，执行隔离标记为空。重开后的位号/引用/标题栏/线号与BOM、From-To、端子计划、端子线号报表再次一致。原始MCP结果仍记录visual_review=PENDING，这是工具自动检查的边界；后续视觉和重开结果单独记录在综合验收字段，未篡改原始回执。

## 复现

运行python -m scripts.trebi_pdf_smoke <已通过批量验收的两页工程目录> --write，再运行python -m scripts.verify_trebi_native_grid <同目录>，最后用Poppler渲染全部PDF页面并检查。验收脚本限定54/112样板；工具不会因为文件生成就宣称施工图合格。

下一阶段的设备映射输入见[Delta CNC与远程I/O资料清单](delta-cnc-io-intake.md)。
