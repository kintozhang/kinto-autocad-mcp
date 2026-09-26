# KINTO A3 绘图模板

| 用途 | DWT 文件 | 图框 |
| --- | --- | --- |
| 机械二维绘图 | KINTO-Mechanical-A3-ZH-EN.dwt | 右下角中英标题栏 |
| TREBI 国产化电气图 | KINTO-TREBI-Electrical-A3-ZH-EN.dwt | 底部整行中英标题栏，顶部 0～9 分区 |

两份均为 A3 横向，模型单位为毫米，不含元件或零件。

## 在 AutoCAD 中选择

输入 NEW，进入默认模板目录中的 KINTO 文件夹，选择对应 DWT。
如果窗口记住了其他目录，可浏览到 C:\kinto\Autocad-mcp\templates。
Electrical 项目管理器中“新建图形”的样板栏也可以浏览选择电气 DWT。
新图保存为 DWG，不覆盖 DWT。

## 新项目需要填写的内容

机械：图名、图号、比例、日期、绘图及审核等。模型按真实毫米绘制，打印比例另行设置与核对；本次不宣称机械定比例打印已验收。

电气：加入目标 WDP 工程后设置逻辑页号；OF 根据有效图页清单计算，PREV/NEXT 按清单顺序填写。模板这四项均留空。保留原生 WD_M 和页号.区域引用设置。项目 WDT 映射仍使用 profiles/trebi-electrical-a3.wdt，需要按已有工程准备流程配置；DWT 本身不创建工程、不自动生成项目页清单。图框参考 TREBI 布局，使用 KINTO 标识。

## 验证

2026-09-26，在本机 AutoCAD Electrical 2026 中完成：DWT 保存重开、从每份 DWT 新建图形、另存 DWG 后重开、对象和属性一致性检查，并核对两种图面布局。验证记录：work/acceptance/dwt-20260926/dwt-verification.json。

已安装副本位于 AutoCAD 当前 TemplateDwgPath 下的 KINTO 子目录；项目主副本位于本目录。以后修改模板后需同步安装副本。drawing-disciplines.json 中的路径是用途索引，不代表所有 MCP 工具已自动选择模板。
