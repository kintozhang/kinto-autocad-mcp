# 三页原生 PDF 验收（2026-09-24）

## 结果与证据

独立打印副本按 CONTACT-TERMINAL.wdp 的原有页序导出：01-SUPPLY、02-CONTROL、03-CONTACT。三次 AutoCAD Electrical 2026 ActiveX PlotToFile 均返回成功并生成非空 PDF；合并交付为 output/pdf/electrical-three-page-20260924.pdf。

- 原生设备 AutoCAD PDF (High Quality Print).pc3；ISO_A3_(420.00_x_297.00_MM)；monochrome.ctb；横向 A3；范围适应纸张。
- 每页在打印副本加合成测试/不可施工及 PAGE n OF 3 标识；DIN 图框比例改为 NTS。未修改电气连接或重新计算引用。
- 源 WDP 与三张源 DWG 的 SHA256 在作业前后相同。使用已验收磁盘快照，不保存当前 AutoCAD 中未保存的源图；这不表示导出了内存中的最新编辑。
- PDF 1.7，共三页，1191 × 842 pt；合并前后逐页内容流、MediaBox、CropBox、旋转一致。三页内容流哈希各不相同。
- Poppler pdfinfo 和全三页 PNG 渲染无格式告警。逐页目视检查图框、页序、英文测试标识、德文文字、线号及父子/跨页引用：无裁切或明显重叠。

原始出图、打印 DWG 副本、配置回读及源文件哈希保存在 work/acceptance/multipage-pdf-20260924/plot-manifest.json。交付文件旁 electrical-three-page-20260924.verification.json 记录合并结构及目视验收结果。原生 PDF 的重复 /PageMode 告警仍存在；合并时仅复制页面及资源，不复制有问题的文档 XMP。并非修复 AutoCAD 驱动本身。

首轮合并校验曾将 pypdf ContentStream 对象按布尔值判断，导致错误的空内容哈希；first-merge-verification.json 保留为无效校验记录。已改为显式 is not None，并用三个不同的真实内容流测试防回归，最终三页内容哈希重新核验通过。

## 重现

1. 使用项目虚拟环境运行：

```powershell
.\.venv\Scripts\python.exe -m scripts.plot_project_smoke <合成工程.wdp> <新的打印副本目录> --write
```

此脚本只支持同目录、UTF-8 WDP 的普通相对 DWG 条目，以及 DIN_tblock_a3 测试图框。输出目录必须全新，按 WDP 顺序串行出图；保留失败记录，不自动重试 CAD 写操作。不适用于任意客户工程、嵌套图纸、多布局或并发客户端。

2. 使用包含 pypdf 的 Python 运行时（本机验收使用 Codex 捆绑运行时），执行：

```powershell
python -m scripts.merge_plot_project <打印目录>/plot-manifest.json <新的交付文件.pdf>
```

输入哈希、页序、重复输入、纸张尺寸和旋转必须通过；拒绝覆盖输出和已有 partial 文件。合并后必须另行渲染并逐页查看，结构校验不等于视觉验收。输出目录需预先存在。项目默认虚拟环境未增加 pypdf 依赖。

## 测试与边界

项目默认回归：116 passed，7 skipped，3 deselected；7 项跳过为可选 pypdf 测试，已在捆绑 PDF 运行时通过 unittest 单独执行（7/7）。覆盖 WDP 顺序及重复/越界/缺页拒绝、真实非空内容流、输出保护、输入篡改和未完成作业拒绝。

本轮不增加 MCP 默认工具：仍为 60 项定义、23 项默认、37 项隐藏。出图目前是原生 COM 验收脚本加 PDF 合并脚本；不是默认 MCP 多页导出能力。本轮未重新执行电气报表验收，图源沿用上一轮已验收合成工程。

后续优先：封装带目标项目与输出约束的 MCP 导出工具；制作中英双语图框；固定比例机械 PDF；大型工程及多布局出图。德国模板文字仍保留，尚未验证中文字体。
