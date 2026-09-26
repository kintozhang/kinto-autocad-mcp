# 中英双语电气标题栏验收（2026-09-24）

## 已完成

在独立三页合成工程中，用自建 KINTO_TB_A3_ZH_EN 替换德文 DIN_tblock_a3 标题栏，保留外围坐标图框、WD_M、电气元件、接线和引用。新标题栏位于原区域，188 × 55 图形单位；采用已验证的 Windows 黑体 simhei.ttf，字体族回读接受 SimHei 或本地化的“黑体”。

字段配置位于 profiles/titleblock-zh-en.json，由 src/autocad/bilingual_titleblock.py 实际加载。字段为 PROJECT、TITLE、DRAWING_NO、SHEET、REV、SCALE、DRAWN_BY、CHECKED_BY、DATE、STATUS，分别对应项目、图名、图号、页码、版本、比例、绘图、审核、日期、状态，标签同时显示中文和英文。

三页字段逐项回读和保存重开通过；元件属性、线段几何与图框替换前相同。BOM、From/To、端子计划、端子编号通过原有合成工程语义校验。字体修正后，四个 DWG（三页工程加模板种子）再次保存重开并核查字体族及电路不变。

现有默认 export_electrical_project_pdf 增加 template_mode=synthetic_zh_en_a3，仍为适应纸张/NTS/合成测试出图，不增加工具数量：61 项定义、24 项默认、37 项隐藏。

## 文件与证据

- 最终三页 PDF：output/pdf/electrical-bilingual-20260924.pdf。默认 MCP 导出，A3 横向，PDF 逐页内容流/纸张尺寸回读通过。
- 可复用空白 DWG 种子：work/projects/bilingual-20260924-221032/KINTO-A3-ZH-EN-SEED-221509.dwg。无示例电路，含图框和待填写字段；不是已验收的 DWT 安装包。
- 三页工程及分阶段回读：work/projects/bilingual-20260924-221032/acceptance.json。
- 字体修正后保存重开：同目录 font-repair.json；最终 MCP 出图：final-font-export.json；最终视觉和中文提取：final-acceptance.json。
- 三页均以 120 dpi 渲染检查：中文清晰、无缺字/越界或明显重叠，图框/线号/引用可读；pypdf 能在每页提取“项目”等中文字段。未将属性回读当作字体显示通过。

## 失败记录与修正

保留首轮长命令未完成、字体查找/样式创建失败、INSERT 句柄时机错误等副本。长生成表达式改为每段400字符传入、完整字符串回读一致后执行一次；带属性的 INSERT 在 SEQEND 后取句柄。没有更改安全设置或可信路径。

最初 msyh.ttc 配置在保存后字体族为空，PDF 中文为问号，失败样张 first-bilingual-font-failed.pdf 保留；最终改为 simhei.ttf，并在 FontFile 设置后调用 SetFont，检查字体族。不能据此认定所有 TTC 字体均不支持，只是这次配置失败。

多次 COM 瞬时拒绝导致阶段中断；保留 interrupted*.json 以及失败的出图目录，恢复时检查已完成阶段，没有重复插入已生成块。字体样式方法查找/电路快照仅对只读 RPC 拒绝做有限重读；新增打开打印副本后的0.5秒稳定间隔并不等于解决 COM 并发或硬超时。

最终结果由分阶段恢复与独立检查取得，不是一轮全流程无故障通过。

## 使用边界

- 标题栏采用显式字段赋值；SHEET 是可见属性，不与 Electrical 项目页号自动双向绑定。未实现 WD_TB 项目标题栏批量更新或自动修订。
- 当前内部生成器及 scripts/bilingual_smoke.py 只用于独立合成测试副本；未新增通用模板安装/替换 MCP 工具。
- 模板种子基于本机安装的 Autodesk 模板生成，留在忽略目录；公共配置/生成代码不包含字体文件或原厂模板二进制。
- 本轮没有翻译整张电气图的所有说明，仅完成双语标题栏。固定比例机械出图、长字段自适应、正式公司图框和真实 TREBI 工程尚未验收。
- 本机依赖黑体 TTF；其他电脑必须重新验证字体及 PDF。136 项单元回归测试通过，3 项上游集成测试未运行。
