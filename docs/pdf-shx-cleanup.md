# PDF SHX 批注清理（2026-09-26）

默认PDF合并流程移除标题严格匹配AutoCAD SHX Text、类型为Square/Text的导出器批注，以及以这些批注为Parent的Popup。保留其他用户批注、Link及书签；不修改DWG字体和打印环境变量。适用于所有经过pdf_merge.merge的MCP导出模板。

重新读取输出验证无SHX批注，保留既有页面内容流/尺寸/旋转验证及导航目的地验证。返回shx_annotations_removed及shx_removed_per_page，便于审计。

使用三页修改样板的原生打印快照，经同一合并流程重建DELTA-CHANGE-Clean-Linked.pdf：移除125项（11/102/12），保留8个内部链接、3个书签；三页PNG与清理前逐页SHA256相同。原PDF和原DWG保留。365项默认测试通过，3项integration未运行。

SHX矢量文字仍显示，但不再附带可点击文字批注。移除的是导出器附加的文字副本，不会把矢量笔画转换为可选择文字；如果阅读器之前依赖批注内容搜索SHX文字，这部分搜索能力会随批注移除。

验收回执位于私有change-validation/pdf-clean.json。已有MCP进程需重新连接以加载代码；本轮没有改动持久客户端配置或推送GitHub。
