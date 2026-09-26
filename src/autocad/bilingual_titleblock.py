"""Internal bilingual title block builder for isolated synthetic drawings only."""
import json
import os
import re
import time
from uuid import uuid4
from pathlib import Path
from src.autocad.lisp_bridge import evaluate, literal, _LOCK

PROFILE = Path(__file__).resolve().parents[2] / 'profiles/titleblock-zh-en.json'


def profile():
    return json.loads(PROFILE.read_text(encoding='utf-8-sig'))


def validate_values(values):
    cfg = profile()
    if set(values) != {f['tag'] for f in cfg['fields']}:
        raise ValueError('Exactly the declared title block fields are required')
    for field in cfg['fields']:
        value = values[field['tag']]
        if not isinstance(value, str) or not value or len(value) > field['max_chars']:
            raise ValueError('Invalid or overlong field: ' + field['tag'])
        literal(value)
    if values['SCALE'] != 'NTS':
        raise ValueError('Synthetic fit-to-page template requires NTS')
    return cfg


def entity(pairs):
    return '(or (entmake (list ' + ' '.join('(cons '+str(k)+' '+literal(v)+')' for k,v in pairs) + ')) (error "Title block entity creation failed"))'


def build_expression(values, old_handle):
    cfg = validate_values(values); name=cfg['block_name']; style=cfg['style_name']
    font_path=(Path(os.environ.get('WINDIR', 'C:/Windows'))/'Fonts'/cfg['font_file']).as_posix()
    code=['(if (tblsearch "BLOCK" '+literal(name)+') (error "Bilingual block already exists"))',
          '(if (not (findfile '+literal(font_path)+')) (error "Required Chinese font unavailable"))',
          '(if (not (tblsearch "STYLE" '+literal(style)+')) (error "Create the verified text style first"))',
          entity([(0,'BLOCK'),(2,name),(70,2),(10,[0.,0.,0.])])]
    lines=[(0,0,188,0),(188,0,188,55),(188,55,0,55),(0,55,0,0),(0,19,188,19),(0,38,188,38),
           (85,38,85,55),(85,19,85,38),(118,19,118,38),(145,19,145,38),
           (50,0,50,19),(100,0,100,19),(145,0,145,19)]
    for x1,y1,x2,y2 in lines:
        code.append(entity([(0,'LINE'),(8,'0'),(10,[x1,y1,0]),(11,[x2,y2,0])]))
    for f in cfg['fields']:
        code.append(entity([(0,'TEXT'),(8,'0'),(10,[*f['label_xy'],0]),(40,2.1),(1,f['label']),(7,style)]))
        code.append(entity([(0,'ATTDEF'),(8,'0'),(10,[*f['value_xy'],0]),(40,f['height']),
                            (1,values[f['tag']]),(2,f['tag']),(3,f['label']),(70,0),(7,style)]))
    code.append(entity([(0,'ENDBLK')]))
    origin=cfg['origin']
    code.append(entity([(0,'INSERT'),(8,'0'),(2,name),(66,1),(10,origin)]))
    for f in cfg['fields']:
        point=[origin[0]+f['value_xy'][0],origin[1]+f['value_xy'][1],0]
        code.append(entity([(0,'ATTRIB'),(8,'0'),(10,point),(40,f['height']),(1,values[f['tag']]),
                            (2,f['tag']),(70,0),(7,style)]))
    code.append(entity([(0,'SEQEND')]))
    # INSERT becomes entlast only after its attribute sequence is completed.
    code.append('(setq kintoNewTb (entlast))')
    # Only the explicitly inspected old title block is removed from this test copy.
    code.append('(entdel (handent '+literal(old_handle)+'))')
    code.append('(cdr (assoc 5 (entget kintoNewTb)))')
    expression='(progn '+' '.join(code)+')'
    return re.sub(r'\(error ("[^"]*")\)', r'(progn (princ \1) (exit))', expression)


def install(conn, drawing_path, values):
    cfg=validate_values(values)
    doc=conn.get_active_document()
    if Path(doc.FullName).resolve()!=Path(drawing_path).resolve():
        raise ValueError('Wrong target drawing')
    old=[e for e in doc.ModelSpace if e.ObjectName=='AcDbBlockReference' and e.Name.lower()=='din_tblock_a3']
    if len(old)!=1:
        raise ValueError('Expected one original DIN title block')
    for attempt in range(10):
        try:
            add_style=doc.TextStyles.Add
            break
        except Exception as exc:
            if getattr(exc,'hresult',None)!=-2147418111 or attempt==9:raise
            time.sleep(.3)
    style=add_style(cfg['style_name'])
    style.FontFile=str(Path(os.environ.get('WINDIR', 'C:/Windows'))/'Fonts'/cfg['font_file'])
    style.SetFont(cfg['font_family'], False, False, 134, 34)
    if style.GetFont()[0] not in cfg['font_family_names']:
        raise RuntimeError('Chinese font family did not read back correctly')
    expression=build_expression(values,old[0].Handle)
    # Keep each command short. A large SendCommand expression can leave CAD
    # awaiting continuation. Accumulate escaped source, read back, then execute once.
    variable='kintoTbSource'+uuid4().hex
    with _LOCK:
        evaluate(conn,'(setq '+variable+' "")')
        for start in range(0,len(expression),400):
            evaluate(conn,'(setq '+variable+' (strcat '+variable+' '+literal(expression[start:start+400])+'))')
        if evaluate(conn,variable)!=expression:
            raise RuntimeError('Generated title block source did not read back exactly')
        handle=evaluate(conn,'(eval (read '+variable+'))')
        evaluate(conn,'(setq '+variable+' nil)')
    block=doc.HandleToObject(handle)
    actual={a.TagString:a.TextString for a in block.GetAttributes()}
    if actual!=values:
        raise RuntimeError('Bilingual attributes did not read back exactly')
    return {'handle':handle,'block':cfg['block_name'],'attributes':actual}
