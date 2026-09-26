"""Native Electrical project reports and current-drawing signal updates.

API signatures: installed Electrical 2026 ACE_API.chm. CSV output uses all
native fields without headers; semantic acceptance must compare known fixtures.
"""
from pathlib import Path
import csv
import io
from src.autocad.connection import get_connection
from src.autocad.lisp_bridge import evaluate, literal, BridgeError
from src.autocad.utils import get_block_attributes
from src.tools.native_electrical import failure


def state(conn):
    result = evaluate(conn, "((lambda (/ p) (setq p (c:wd_proj_wdp_data)) (list (ace_getactiveproject) (nth 5 p) (nth 0 p))))")
    if not result[0] or not result[2] or Path(result[0]).resolve() != Path(result[2]).resolve():
        raise BridgeError("Electrical project context is stale in this drawing; activate the intended project again before continuing")
    return {"project":result[0], "drawings":result[1] or []}


def get_project():
    try:
        return {"success":True, **state(get_connection())}
    except Exception as exc:
        return failure(exc)


def guard(conn, expected):
    expected = Path(expected)
    if not expected.is_absolute() or expected.suffix.lower() != ".wdp" or not expected.is_file():
        raise ValueError("Expected an existing absolute WDP path")
    result = state(conn)
    if not result["project"] or Path(result["project"]).resolve() != expected.resolve():
        raise BridgeError("Active project does not match requested project")
    if Path(conn.get_active_document().FullName).resolve() not in {Path(p).resolve() for p in result["drawings"]}:
        raise BridgeError("Active drawing is not a member of requested project")
    return result


def guarded_expression(expected, expression):
    # Check inside CAD, not just before SendCommand.
    path = literal(str(Path(expected)).replace("\\", "/").upper())
    return '(if (= (strcase (vl-string-translate "\\\\" "/" (ace_getactiveproject))) ' + path + ') ' + expression + ' (error "Target project changed"))'


def update_signals(project_path):
    try:
        conn = get_connection()
        guard(conn, project_path)
        evaluate(conn, guarded_expression(project_path, '(progn (c:wd_mdb_freshen nil) (c:ace_sig_update (list 1 1 1 0 nil nil)) T)'), timeout=40)
        guard(conn, project_path)
        signals = []
        for obj in conn.get_active_document().ModelSpace:
            if obj.ObjectName != "AcDbBlockReference":
                continue
            attrs = get_block_attributes(obj)
            if attrs.get("SIGCODE"):
                signals.append({"handle":obj.Handle,"block":obj.Name,"attributes":attrs})
        verified = bool(signals) and all(s["attributes"].get("XREF") and s["attributes"].get("WIRENO") for s in signals)
        return {"success":bool(verified),"status":"attributes_read_back" if verified else "unverified",
                "drawing":conn.get_active_document().FullName,"signals":signals,
                "note":"Cross-page endpoint correctness must also be checked against the native From/To report."}
    except Exception as exc:
        return failure(exc)


def report_arguments(kind, output):
    if kind in {"terminal_plan", "terminal_numbers"}:
        function = "c:ace_termplan_r" if kind == "terminal_plan" else "c:wd_term_nums_rpt"
        return function, [1, 1, None, None, None, "CSV", 0, output, None]
    if kind == "bom":
        function, args = "c:wd_bomschr", [1,1,None,3,None,"CSV",0]
    elif kind == "components":
        function, args = "c:wd_compr_sch", [1,1,None,None,0,"CSV",0]
    elif kind == "from_to":
        function, args = "c:wd_frm2_r", [1,0,None,1,["*"],["*"],None,"CSV",0]
    else:
        raise ValueError("report_type must be bom, components, from_to, terminal_plan or terminal_numbers")
    return function, args + [output,None,None]


def export_report(project_path, report_type, output_path):
    try:
        output = Path(output_path)
        if not output.is_absolute() or output.suffix.lower() != ".csv":
            raise ValueError("Output must be an absolute CSV path")
        if output.exists():
            raise ValueError("Output already exists; choose a new path to avoid stale results/overwrites")
        function, args = report_arguments(report_type, output.as_posix())
        conn = get_connection()
        before = guard(conn, project_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        expression = '(progn (c:wd_mdb_freshen nil) (' + function + ' ' + literal(args) + ') T)'
        evaluate(conn, guarded_expression(project_path, expression), timeout=50)
        if guard(conn, project_path) != before:
            raise BridgeError("Project membership changed during report extraction")
        data = output.read_bytes()
        try:
            content = data.decode("utf-8-sig")
            encoding = "utf-8-sig"
        except UnicodeDecodeError:
            content = data.decode("gb18030")
            encoding = "gb18030"
        rows = [row for row in csv.reader(io.StringIO(content)) if any(row)]
        return {"success":True,"status":"native_file_read_back","project":before["project"],
                "drawings":before["drawings"],"report_type":report_type,"api":function,
                "file":str(output),"encoding":encoding,"row_count":len(rows),"rows":rows,
                "note":"All native fields, no header. Compare rows to expected design before accepting project correctness."}
    except Exception as exc:
        return failure(exc)
