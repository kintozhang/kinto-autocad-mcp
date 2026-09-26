# 全工具验收清单

73个工具定义：33个默认提供，40个默认隐藏。默认开放不等于全参数范围验收。

由 profiles/tool-capabilities.json 生成；更新命令：python -m scripts.audit_api_coverage --write。API与技能对应关系见 [覆盖审计](api-skill-coverage.md)。

| 工具 | 默认提供 | 状态/范围 | 缺口/替代 | 证据 |
| --- | --- | --- | --- | --- |
| draw_line | 是 | live_sample_verified / 2D WCS line endpoints; eight sample centre marks |  | work/acceptance/dimensions-20260924-172043/report.json |
| draw_circle | 是 | live_sample_verified / Four XY circles, radius3 |  | docs/live-validation-20260924.md |
| draw_arc | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| draw_text | 是 | live_sample_verified / ASCII sample labels; multilingual fonts not accepted |  | docs/live-validation-20260924.md |
| draw_rectangle | 是 | live_sample_verified / 120x80 closed plate, area9600 |  | docs/live-validation-20260924.md |
| draw_polyline | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| zoom_extents | 是 | live_sample_verified / Sample view; not plot-scale validation |  | docs/live-validation-20260924.md |
| set_layer | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| draw_line_3d | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| draw_polyline_3d | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| draw_3d_face | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| draw_box | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| draw_sphere | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| draw_cylinder | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| draw_cone | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| zoom_3d_view | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| set_ucs | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| get_autocad_info | 是 | live_sample_verified / Observed Electrical2026 process/version; other variants not accepted |  | docs/live-validation-20260924.md |
| insert_electrical_symbol | 是 | live_sample_verified / HCR1/HT0001/HFU1/HPB11/HA1S1/HA1D3 sample insertion |  | docs/project-validation-20260924.md |
| insert_ladder | 否 | unverified / Code exists; no complete native acceptance | Command submission only; now returns submitted_unverified, not success |  |
| get_symbol_list | 是 | live_sample_verified / Real IEC2 DWG file search; six named symbols have semantic evidence |  | work/acceptance/dimensions-20260924-172043/report.json |
| set_wire_number | 否 | unverified / Code exists; no complete native acceptance | Command submission only; now returns submitted_unverified, not success |  |
| insert_plc_module | 否 | unverified / Code exists; no complete native acceptance | Command submission only; now returns submitted_unverified, not success |  |
| create_cross_reference | 否 | unverified / Code exists; no complete native acceptance | Command submission only; now returns submitted_unverified, not success |  |
| edit_component_attributes | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| draw_wire | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| number_wires | 否 | unverified / Code exists; no complete native acceptance | Command submission only; now returns submitted_unverified, not success |  |
| get_wire_numbers | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| set_wire_attributes | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| create_wire_from_to | 否 | disabled_unsafe_legacy / Code exists; no complete native acceptance | Block insertion point is not a terminal |  |
| get_component_list | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| get_component_info | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| update_component | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| delete_component | 否 | disabled_unsafe_legacy / Code exists; no complete native acceptance | Deleting block does not prove wire repair or Electrical database update |  |
| move_component | 否 | disabled_unsafe_legacy / Code exists; no complete native acceptance | Moving block does not prove wire-follow or Electrical database update |  |
| search_components | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| generate_bom | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| generate_wire_list | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| generate_terminal_plan | 否 | unverified / Code exists; no complete native acceptance | Legacy scan is not a native terminal-strip report |  |
| generate_plc_io_list | 否 | unverified / Code exists; no complete native acceptance | PLC report extraction not verified |  |
| get_project_summary | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| get_project_info | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| list_drawings | 是 | live_sample_verified / Open document list; not WDP membership |  | docs/live-validation-20260924.md |
| open_drawing | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| close_drawing | 否 | unverified / Code exists; no complete native acceptance | Unverified native effects |  |
| sync_project | 否 | unverified / Code exists; no complete native acceptance | Command submission only; now returns submitted_unverified, not success |  |
| get_active_drawing | 是 | live_sample_verified / Active DWG query |  | docs/live-validation-20260924.md |
| get_electrical_connections | 是 | live_sample_verified / X[01248]TERMnn attributes on sample symbols |  | docs/project-validation-20260924.md |
| connect_electrical_terminals | 是 | live_sample_verified / Aligned links, two three-segment offset routes, and electrically isolated crossing sample; all returned segment networks checked | Sequential duplicate prevention verified; concurrent cross-client writes and arbitrary obstructions not accepted | docs/branch-pdf-validation.md |
| set_electrical_wire_number | 是 | live_sample_verified / Normal sample wire numbers100..103 |  | docs/project-validation-20260924.md |
| get_electrical_wire | 是 | live_sample_verified / Native sample wire number/netlist/geometry |  | docs/project-validation-20260924.md |
| get_electrical_project | 是 | live_sample_verified / Two-page WDP membership |  | docs/project-validation-20260924.md |
| update_electrical_signals | 是 | live_sample_verified / Current-page source/destination signals; parent/child references excluded |  | docs/project-validation-20260924.md |
| export_electrical_project_report | 是 | live_sample_verified / Native bom, components, from_to; terminal_plan and terminal_numbers accepted on synthetic 3-page fixture |  | docs/contact-terminal-validation.md |
| get_tool_capabilities | 是 | metadata / Read-only declared capability catalogue |  |  |
| add_aligned_dimension | 是 | live_sample_verified / Measured XY dimensions120/80/100/60; non-associative |  | work/acceptance/dimensions-20260924-172043/report.json |
| add_diameter_dimension | 是 | live_sample_verified / XY circle diameter6; non-associative |  | work/acceptance/dimensions-20260924-172043/report.json |
| get_dimension_info | 是 | live_sample_verified / Aligned/diametric Measurement/type/override readback |  | work/acceptance/dimensions-20260924-172043/report.json |
| update_electrical_cross_references | 是 | live_sample_verified / HCR1 parent with HCR21 NO and HCR22 NC children across pages; native formatting and reopened attributes verified | A COM transient after submission required independent recovery verification; larger contact sets and different-location duplicates not live accepted | docs/multicontact-crossing-validation.md |
| branch_electrical_terminal_to_wire | 是 | live_sample_verified / Two aligned T taps/four HT0001 terminals; normal and fixed 501 preserved; pin caches, native project reports and reopen verified | Cross-page buses, obstacles, nonaligned branches and cross-client concurrency unverified | docs/branch-project-validation.md |
| export_electrical_project_pdf | 是 | live_sample_verified / Synthetic DIN, bilingual KINTO or TREBI A3 copies; TREBI logical page/grid/navigation preflight; two-page TREBI PDF visual/reopen/report acceptance | Synthetic templates only; visual review required; helper timeout does not cancel CAD commands; no automatic recovery | docs/trebi-pdf-validation.md |
| get_execution_diagnostics | 是 | metadata / Local operation records only; no COM access or automatic recovery |  |  |
| plan_trebi_batch | 是 | offline_and_stdio_verified / Pure TREBI batch preflight: pages/tags/reference expectations; no CAD scan | Prepared blank-page recipe only; no catalog selection | docs/trebi-batch-validation.md |
| execute_trebi_batch | 是 | live_sample_verified / Two-page IEC2 relay/contact/terminals/signals; native title/grid, wires, references, reports and independent reopen accepted | Requires prepared blank pages; only verified IEC2 subset; general 8-page limit not full-range acceptance | docs/trebi-batch-validation.md |
| plan_delta_r2_io | 是 | offline_and_stdio_verified / Read-only R2-EC0902 family channel/common/PDO-group draft; no CAD contact | D0 suffix, exact ESI, NC50 addresses and native PLC symbols pending | docs/delta-io-planning.md |
| execute_trebi_test_change | 否 | live_synthetic_verified / Exact synthetic lamp and R2 channel fixture only | Exact synthetic lamp and Y00-to-Y01 case only; default hidden; no production support | docs/trebi-test-change-validation.md |
| plan_cad_project | 是 | restricted_workflow_verified / New empty mechanical/TREBI draft projects only |  | docs/engineering-project-workflow.md |
| create_cad_project | 是 | restricted_workflow_verified / New empty mechanical/TREBI draft projects only |  | docs/engineering-project-workflow.md |
| audit_cad_project | 是 | restricted_workflow_verified / Offline version-bound evidence / restore to new directory only |  | docs/engineering-project-workflow.md |
| restore_cad_project | 是 | restricted_workflow_verified / Offline version-bound evidence / restore to new directory only |  | docs/engineering-project-workflow.md |
| recover_cad_interruption | 是 | restricted_recovery / Inspect stable saved target and release reviewed interruption for NEW operations; never replay/undo | Only block/line/text/circle model-space snapshots; unknown entities or running workers refuse recovery | docs/interruption-recovery.md |
| insert_test_parametric_connector | 否 | experimental / Blank saved TREBI test page only; native documented API | Live acceptance pending; no Delta hardware binding | docs/extended-electrical-acceptance.md |
| insert_test_plc_module | 否 | experimental / Blank saved TREBI test page only; native documented API | Live acceptance pending; no Delta hardware binding | docs/extended-electrical-acceptance.md |
