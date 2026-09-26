"""Native X-zone settings for the inspected TREBI-style A3 frame only."""
import re
from pathlib import Path
from src.autocad.trebi_rules import profile
from src.autocad.lisp_bridge import evaluate,literal


def settings(sheet):
    if not isinstance(sheet,str) or not re.fullmatch(r"0|[1-9][0-9]*",sheet):
        raise ValueError("Explicit logical sheet number required")
    cfg=profile();left,_,right,top=cfg["header_bounds"]
    if cfg["zones"]!=list(range(10)) or right<=left:raise ValueError("Expected ten ascending zones")
    return {"REFNUMS":"5","SHEET":sheet,"DATUMX":str(left),"DATUMY":str(top),
            "DISTH":str((right-left)/10),"CHAR_H":",".join(map(str,cfg["zones"])),"XREFFMT":"%S.%N","ALT_XREFFMT":"%S.%N"}


def configure(conn,drawing_path,sheet):
    expected=settings(sheet);doc=conn.get_active_document()
    if Path(doc.FullName).resolve()!=Path(drawing_path).resolve():raise ValueError("Wrong drawing")
    blocks=[e for e in doc.ModelSpace if e.ObjectName=="AcDbBlockReference"]
    wd=[b for b in blocks if b.Name=="WD_M"]
    if len(wd)!=1 or sum(b.Name==profile()["block_name"] for b in blocks)!=1:
        raise ValueError("Expected one WD_M and one TREBI frame")
    before={a.TagString:a.TextString for a in wd[0].GetAttributes()}
    if not set(expected)<=set(before):raise ValueError("Missing native drawing attributes")
    edits=['(c:wd_modattrval (handent '+literal(wd[0].Handle)+') '+literal(k)+' '+literal(v)+' nil)' for k,v in expected.items()]
    changed=evaluate(conn,'(list '+' '.join(edits)+')')
    if changed!=[1]*len(expected):raise RuntimeError("Native attribute update incomplete; inspect before retry")
    # Documented 2026 API refreshes the active drawing's cached settings.
    cache=evaluate(conn,'((lambda (/ p) (setq p (c:ace_GBL_wd_m 0)) (list (nth 1 p) (nth 13 p) (nth 14 p) (nth 18 p) (nth 20 p) (nth 22 p) (nth 47 p))))')
    after={a.TagString:a.TextString for a in wd[0].GetAttributes()}
    if any(after[k]!=v for k,v in expected.items()):raise RuntimeError("Native grid readback mismatch")
    if any(after[k]!=v for k,v in before.items() if k not in expected):raise RuntimeError("Unrelated WD_M attribute changed")
    return {"before":before,"after":after,"cache":cache,"settings":expected}
