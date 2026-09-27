"""Native parent/child update. All project drawings must already be open and saved."""
from pathlib import Path
import json
import uuid
from src.autocad.connection import get_connection
from src.autocad.lisp_bridge import _LOCK, ROOT, evaluate, literal, BridgeError
from src.tools.native_project import guard, guarded_expression
from src.tools.native_electrical import failure


def snapshot(conn, project, require_saved):
    from src.autocad.com_runtime import read_call
    return read_call(lambda:_snapshot_once(conn,project,require_saved),label="complete cross-reference snapshot")


def _snapshot_once(conn, project, require_saved):
    docs = {str(Path(d.FullName).resolve()).casefold(): d for d in conn.get_application().Documents if d.FullName}
    records = []
    for filename in project["drawings"]:
        key = str(Path(filename).resolve()).casefold()
        if key not in docs:
            raise BridgeError("Open every project drawing before updating references: " + filename)
        if sum(Path(name).name.casefold() == Path(filename).name.casefold() for name in docs) != 1:
            raise BridgeError("Duplicate open drawing filenames; use unique names before native project update: " + filename)
        doc = docs[key]
        if require_saved and not doc.Saved:
            raise BridgeError("Save project drawings explicitly before updating references: " + filename)
        for obj in doc.ModelSpace:
            if obj.ObjectName != "AcDbBlockReference" or not obj.HasAttributes:
                continue
            # Unlike legacy helpers, COM read failures must propagate.
            attrs = {a.TagString.upper(): a.TextString for a in obj.GetAttributes()}
            if attrs.get("TAG1") or attrs.get("TAG2"):
                records.append({"drawing":filename,"handle":obj.Handle,"block":obj.Name,"attributes":attrs})
    return records


def pairs(records, check_references):
    parents = {}
    for row in records:
        a = row["attributes"]
        if a.get("TAG1"):
            parents.setdefault((a.get("INST", ""), a.get("LOC", ""), a["TAG1"]), []).append(row)
    children = [r for r in records if r["attributes"].get("TAG2")]
    if not children:
        raise BridgeError("No child contacts found; no reference update accepted")
    result = []
    for child in children:
        a = child["attributes"]
        matches = parents.get((a.get("INST", ""), a.get("LOC", ""), a["TAG2"]), [])
        if len(matches) != 1:
            raise BridgeError("Child requires exactly one matching INST/LOC/TAG parent: " + a["TAG2"])
        parent = matches[0]
        if a.get("FAMILY") == "CBL" and parent["attributes"].get("FAMILY") == "CBL":
            field = "XREF"
        elif a.get("CONTACT") in {"NO", "NC"}:
            field = "XREFNO" if a["CONTACT"] == "NO" else "XREFNC"
        else:
            raise BridgeError("Only NO/NC contacts or matched CBL cable references supported")
        if check_references and (not a.get("XREF") or not parent["attributes"].get(field)):
            raise BridgeError("Parent or child reference was empty after native update")
        result.append({"parent":parent,"child":child,"parent_reference_field":field})
    return result


def update(project_path):
    operation_id = uuid.uuid4().hex
    audit = ROOT / "work" / "operations" / (operation_id + ".json")
    audit.parent.mkdir(parents=True, exist_ok=True)
    submitted = False
    audit_data = {}
    def record(data):
        audit_data.update(data)
        audit.write_text(json.dumps(audit_data,ensure_ascii=False,indent=2),encoding="utf8")
    try:
        with _LOCK:
            conn = get_connection()
            before = guard(conn, project_path)
            rows = snapshot(conn, before, True)
            pairs(rows, False)  # Ambiguous or unsupported contacts fail before any write.
            record({"operation_id":operation_id,"status":"prepared","project":before,"before":rows})
            if guard(conn, project_path) != before:
                raise BridgeError("Project changed before update")
            expr = '(progn (c:wd_mdb_freshen nil) (c:wd_xref_doit ' + literal(before["drawings"]) + ' 0 1) T)'
            submitted = True
            record({"operation_id":operation_id,"status":"submission_started","project":before,"before":rows})
            evaluate(conn, guarded_expression(project_path, expr), timeout=50)
            if guard(conn, project_path) != before:
                raise BridgeError("Project changed during update")
            matched = pairs(snapshot(conn, before, False), True)
            result = {"success":True,"status":"reference_attributes_read_back","operation_id":operation_id,
                      "project":before,"pairs":matched,"retry_safe":False,"audit_file":str(audit),
                      "note":"Matched INST/LOC/TAG and nonempty references. Exact location text, save/reopen and reports require independent acceptance. No description or location propagation."}
            record(result)
            return result
    except Exception as exc:
        result = failure(exc,operation_id=operation_id,submitted=submitted,audit_file=str(audit))
        record(result)
        return result
