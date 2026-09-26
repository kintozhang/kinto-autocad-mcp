# T 分支、重复连接和 PDF 专项（2026-09-24）

## 完成内容

- connect_electrical_terminals 写入前读取接线点所接的原生网络；两个指定点已连接时返回 already_connected、changed=false，不提交插线。反向端点请求和保存重开后重复请求同样通过；不同线层请求明确拒绝。
- 新增 branch_electrical_terminal_to_wire：仅接受源接线点与目标线段上接点对齐的直线分支。检查接点在线段上，源接线点未被接到其他网络，原生插线后验证全部请求端点和原线号继承；已经接通则不再添加图元。
- 三个 HT0001 端子的 T 形样板中，原生主线不拆段，新增一条支线及接点标识；两条 LINE 均识别三个正确端点，501 被继承。重复主线连接、反向连接、重复支线、保存重开后的重复连接均不增加图元。
- 默认工具现在为 23（总定义 60、隐藏 37），Codex 本机白名单同步，Claude Code 使用相同服务端默认列表。客户端重载本轮未测试。

证据：work/acceptance/branch-20260924-200753/report.json；复验构建脚本 scripts/branch_smoke.py --write。前一副本 branch-200636 错误地预期原生主线拆成两段，因此在线段数量断言处停止，保留为失败记录，不作通过证据。

## PDF 出图

打印副本 branch-print.dwg 从通过样板复制。真实设备列表中选择 AutoCAD PDF (High Quality Print).pc3，ISO_A3_(420.00_x_297.00_MM)，monochrome.ctb，范围适应纸张，单页横向 A3。原生 PlotToFile 使用前台出图，之后恢复 BACKGROUNDPLOT 原值。

依据：[Autodesk PlotToFile ActiveX 文档](https://help.autodesk.com/cloudhelp/2016/CHS/AutoCAD-ActiveX/files/GUID-85A6B1AF-80AA-4F56-8305-6EFD4A4D8CF8.htm)。该 API 文档为较早版本，实际设备和执行结果已在本机 2026 核对。

打印副本加了合成测试/不可施工标识；501 用已验证的 c:wd_move_wn 移离 T 接点，三端网络未改变；原模板比例属性由 1:1 改为 NTS，与适应纸张出图一致。德文图框仍为测试模板，本轮未制作双语图框。

原生 PDF 存在 XMP 流格式告警及重复 /PageMode 键。原始文件 native-branch-final.pdf、native-first-pass.pdf 留在验收目录；交付副本通过 scripts/normalize_plot_pdf.py 规范化。保留 PDF 1.7、A3 媒体框和页面内容流，前后内容流 SHA256 一致。最终 Poppler 渲染和 pdfinfo 没有格式告警；图框完整、端子和接点清楚、线号无重叠。不是将 AutoCAD 驱动本身修好，也不是重画一份替代电气图。

交付样张 output/pdf/branch-test-verified-20260924.pdf；验收配置 pdf-export.json。PDF 是单页原生出图加规范化专项，尚未封装默认 MCP 出图工具；没有实际向实体打印机发送作业。归一化脚本使用捆绑 runtime 的 pypdf，项目虚拟环境不要求安装它。

## 自动测试及边界

97 passed，3 deselected。新增重复调用不提交写入、分支坐标与越界拒绝测试。

重复保护目前是顺序调用同一活动图纸的原生网络预检，不是跨客户端并发事务或任意操作的幂等保证。线网连接已存在时返回一个现有线段作为证据，不枚举整个网络所有线段。

后续：分支项目级 From/To/BOM（本轮分支只有单图网络回读）、多分支与障碍物、多页 PDF、固定比例机械出图、中英双语模板、COM 恢复和跨客户端互斥。
