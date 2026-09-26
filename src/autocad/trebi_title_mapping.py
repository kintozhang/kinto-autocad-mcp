"""Native title update for explicitly bound TREBI projects. Caller holds CAD gate."""
from pathlib import Path
from src.autocad.trebi_project_pages import plan
from src.autocad.trebi_rules import profile
from src.autocad.lisp_bridge import evaluate,literal
from src.autocad.utils import get_block_attributes
from src.tools.native_project import guard,guarded_expression
WDT=Path(__file__).resolve().parents[2]/"profiles/trebi-electrical-a3.wdt"

def binding(manifest,project_path,drawing_path):
    project=Path(project_path).resolve();drawing=Path(drawing_path).resolve();pages=plan(manifest)
    filenames={};rows={d['logical_page']:d for d in pages['drawings'] if d['include_in_total']}
    for entry in manifest['entries']:
        if entry['kind']!='drawing' or not entry['include_in_total']:continue
        name=entry.get('drawing_file')
        if not isinstance(name,str) or Path(name).name!=name or Path(name).suffix.lower()!='.dwg':raise ValueError('Explicit local DWG filename required')
        full=project.parent/name
        if str(full).casefold() in filenames:raise ValueError('Duplicate DWG binding')
        filenames[str(full).casefold()]=rows[entry['logical_page']]
    if str(drawing).casefold() not in filenames:raise ValueError('Target is not an effective bound drawing')
    return filenames,filenames[str(drawing).casefold()]['title_fields']

def title_expression(project_path,drawing_path,expression):
    target=literal(Path(drawing_path).resolve().as_posix().upper())
    check='(if (= (strcase (vl-string-translate "\\\\" "/" (strcat (getvar "DWGPREFIX") (getvar "DWGNAME")))) '+target+') '+expression+' (error "Target title drawing changed"))'
    return guarded_expression(str(project_path),check)


def apply(conn,project_path,manifest,drawing_path):
    bound,expected=binding(manifest,project_path,drawing_path)
    project=Path(project_path).resolve()
    if project.with_suffix('.wdt').read_text(encoding='utf8')!=WDT.read_text(encoding='utf8'):raise ValueError('Unverified WDT mapping')
    lines=project.read_text(encoding='utf-8-sig').splitlines()
    if [l for l in lines if l.startswith('*[20]')]!=['*[20]'+expected['OF']]:raise ValueError('LINE20 must equal explicit effective drawing count')
    state=guard(conn,str(project))
    if [str(Path(p).resolve()).casefold() for p in state['drawings']]!=list(bound):raise ValueError('WDP membership or order differs from effective drawing manifest')
    doc=conn.get_active_document()
    if Path(doc.FullName).resolve()!=Path(drawing_path).resolve():raise ValueError('Wrong active drawing')
    blocks=[e for e in doc.ModelSpace if e.ObjectName=='AcDbBlockReference']
    titles=[e for e in blocks if e.Name==profile()['block_name']];wd=[e for e in blocks if e.Name=='WD_M']
    if len(titles)!=1 or len(wd)!=1:raise ValueError('Expected unique TREBI title and WD_M')
    native=get_block_attributes(wd[0]);before=get_block_attributes(titles[0])
    if native.get('SHEET')!=expected['PAGE']:raise ValueError('Native SHEET disagrees with logical PAGE')
    if not set(expected)<=set(before):raise ValueError('Missing title attributes')
    flags=[0]*16;flags[7]=1
    expr='(progn (c:wd_tb_process_one 1 '+literal([flags,19])+') T)'
    evaluate(conn,title_expression(project,drawing_path,expr),timeout=30)
    # PREV/NEXT use manifest order; no SHEETMAX/max-logical-page assumption.
    expr='(list '+' '.join('(c:wd_modattrval (handent '+literal(titles[0].Handle)+') '+literal(k)+' '+literal(expected[k])+' nil)' for k in ['PREV','NEXT'])+')'
    if evaluate(conn,title_expression(project,drawing_path,expr))!=[1,1]:raise RuntimeError('Navigation update incomplete; inspect before retry')
    actual=get_block_attributes(titles[0])
    if actual!={**before,**expected} or get_block_attributes(wd[0])!=native:raise RuntimeError('Title mapping readback mismatch')
    if Path(conn.get_active_document().FullName).resolve()!=Path(drawing_path).resolve():raise RuntimeError('Active title drawing changed')
    if guard(conn,str(project))!=state:raise RuntimeError('Project changed during title update')
    return {'before':before,'after':actual,'expected':expected,'page_of_api':'c:wd_tb_process_one','navigation_api':'c:wd_modattrval'}
