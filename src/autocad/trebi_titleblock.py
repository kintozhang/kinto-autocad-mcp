"""Internal TREBI-style frame creation, restricted to inspected empty test seeds."""
from pathlib import Path
from uuid import uuid4
from src.autocad.trebi_rules import validate_fields
from src.autocad.bilingual_titleblock import entity
from src.autocad.lisp_bridge import evaluate,literal,_LOCK


def expression(values, remove_handles):
    cfg=validate_fields(values);name=cfg["block_name"];style=cfg["style_name"]
    code=[entity([(0,"BLOCK"),(2,name),(70,2),(10,[0,0,0])])]
    for x1,y1,x2,y2 in cfg["lines"]:
        code.append(entity([(0,"LINE"),(8,"0"),(10,[x1,y1,0]),(11,[x2,y2,0])]))
    for zone in cfg["zones"]:
        code.append(entity([(0,"TEXT"),(8,"0"),(10,[29+40*zone,284.5,0]),(40,3),(1,str(zone)),(7,style)]))
    for field in cfg["fields"]:
        code.append(entity([(0,"TEXT"),(8,"0"),(10,[*field["label_xy"],0]),(40,field.get("label_height",1.8)),(1,field["label"]),(7,style)]))
        code.append(entity([(0,"ATTDEF"),(8,"0"),(10,[*field["value_xy"],0]),(40,field["height"]),
                            (1,values[field["tag"]]),(2,field["tag"]),(3,field["label"]),(70,0),(7,style)]))
    code.extend([entity([(0,"ENDBLK")]),entity([(0,"INSERT"),(8,"0"),(2,name),(66,1),(10,[0,0,0])])])
    for f in cfg["fields"]:
        code.append(entity([(0,"ATTRIB"),(8,"0"),(10,[*f["value_xy"],0]),(40,f["height"]),(1,values[f["tag"]]),(2,f["tag"]),(70,0),(7,style)]))
    code.extend([entity([(0,"SEQEND")]),'(setq kintoTrebiFrame (entlast))'])
    for handle in remove_handles:code.append('(entdel (handent '+literal(handle)+'))')
    code.append('(cdr (assoc 5 (entget kintoTrebiFrame)))')
    import re
    return re.sub(r'\(error ("[^"]*")\)',r'(progn (princ \1) (exit))','(progn '+' '.join(code)+')')


def install_empty_seed(conn,path,values):
    cfg=validate_fields(values);doc=conn.get_active_document()
    if Path(doc.FullName).resolve()!=Path(path).resolve():raise ValueError("Wrong drawing")
    objects=list(doc.ModelSpace)
    # This intentionally refuses any circuit or unfamiliar seed geometry.
    names=sorted(e.Name for e in objects if e.ObjectName=="AcDbBlockReference")
    if len(objects)!=3 or names!=sorted(["WD_M","KINTO_TB_A3_ZH_EN","DIN_border_a3"]):
        raise ValueError("Expected empty accepted seed: WD_M + old frame + title only")
    if doc.TextStyles.Item(cfg["style_name"]).GetFont()[0] not in {"SimHei","黑体"}:
        raise ValueError("Verified Chinese font required")
    remove=[e.Handle for e in objects if e.ObjectName!="AcDbBlockReference" or e.Name!="WD_M"]
    code=expression(values,remove);variable="kintoTrebiSource"+uuid4().hex
    with _LOCK:
        evaluate(conn,'(setq '+variable+' "")')
        for i in range(0,len(code),400):
            evaluate(conn,'(setq '+variable+' (strcat '+variable+' '+literal(code[i:i+400])+'))')
        if evaluate(conn,variable)!=code:raise RuntimeError("Source readback mismatch")
        handle=evaluate(conn,'(eval (read '+variable+'))')
        evaluate(conn,'(setq '+variable+' nil)')
    block=doc.HandleToObject(handle)
    actual={a.TagString:a.TextString for a in block.GetAttributes()}
    if actual!=values:raise RuntimeError("Frame attributes differ")
    return {"block":cfg["block_name"],"handle":handle,"attributes":actual,"native_grid":"not_configured"}
