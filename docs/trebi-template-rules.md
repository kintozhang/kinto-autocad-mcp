# TREBI 电气规则与独立模板

2026-09-25，本轮178项默认测试通过；默认工具仍25项。本轮实现的是模板及规则基础，不是整套TREBI原图重建。

## 模板分离

- profiles/titleblock-zh-en.json、KINTO_TB_A3_ZH_EN及既有空白种子保留，作为机械图框基础。机械固定比例、关联标注仍需专项验证。
- profiles/trebi-electrical-a3.json定义独立电气图框KINTO_TREBI_ELECTRICAL_A3。A3横向，底部贯穿400mm内框宽度、约30mm高；顶部0至9十区。尺寸按原图比例规范化，不声称取得原始CAD精确尺寸。
- 标题栏按参考图组织：左侧修订/变更/日期/签署，中部项目标识，右侧图号/订单/客户/图名/设计/日期，最右PAGE、OF及前后逻辑页。自有项目标识使用KINTO，不复制TREBI商标。
- 15项字段可读取、保存重开；前后页标签初次输出拥挤，已缩短并调整字号，最终原生PDF目视通过。
- profiles/drawing-disciplines.json明确两个图框的用途；不是所有现有MCP调用的自动模板切换器。旧电气合成样板继续作为回归证据，不作为新的TREBI模板。

## 原图依据

只读来源：Trebi_Wiki/raw/electrical/16601-01-rev3（电气图）.pdf。153物理页；本轮目视核对物理第31页，对应逻辑PAGE102。源PDF哈希及153页初步索引存于私有work/trebi-reference/page-index.json，152页提取到PAGE/OF字段，其余为封面；未对全部索引逐页目视验收。

原图PAGE102右下角打印OF96，前后页101/103。不能用153替换OF，也不能把逻辑页码改成PDF顺序。用户已明确OF表示项目有效图页总数；原图是否实际包含96张有效图页尚未逐项清点。新项目按显式有效图页清单计算，见[图页清单规则](trebi-page-manifest.md)。

该页I545信息框显示MODULE -300A2、TERMINAL 2；与先前文字示例中的端子5不同，后续I/O映射以原图逐项核验为准。此处只记证据，不建立整机I/O映射或修改知识库原资料。

## 已落地规则

src/autocad/trebi_rules.py读取电气配置，提供逻辑页码导航（保留跳号）、0..9分区计算、页号.区号格式和明确上下文校验。wire_reference、component_reference、module_position分开；I545、X15:5、2.4-B不能当TREBI页区引用解析。PAGE与OF、PREV/NEXT独立，不用页数自动覆盖。

src/autocad/trebi_titleblock.py仅允许在确认仅有WD_M、DIN_border_a3和旧双语标题栏的空白种子副本安装新图框；包含电路或未知对象即拒绝。保留WD_M，替换边框和标题栏，未开放默认MCP安装工具。

## 实机与边界

work/acceptance/trebi-frame-20260925-084127/final-acceptance.json：2个模型空间对象（WD_M和新图框），15个属性保存重开一致，原生A3 PDF与最终渲染通过。

首次前置检查误以为旧边框是多段线，实际为DIN_border_a3块，因此拒绝且未修改种子。经保存状态、命令空闲、原始对象、进程退出及磁盘哈希核对后保留恢复证据并解除标记；未盲目重试图框写入。

后续两页原生引用及保存重开报表已通过，见 [原生页区引用验收](trebi-native-grid-validation.md)。本页的178项测试为图框阶段历史记录；当前193项通过。WDT字段、项目创建和默认MCP模板选择仍待接入；电位隔离、PLC/电缆/连接器等TREBI语义映射另行实现。

空白模板无电路，所以本轮未生成BOM或接线报表。测试OF96仅用于参考布局，实际国产化项目必须按明确项目规则填写。
