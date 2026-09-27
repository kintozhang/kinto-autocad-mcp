"""Explicit empty-project creation. No device selection or production approval."""
import json,re,uuid
from pathlib import Path
from src.autocad.engineering_archive import digest
ROOT=Path(__file__).resolve().parents[2]
TEMPLATES={'trebi_electrical':'KINTO-TREBI-Electrical-A3-ZH-EN.dwt','mechanical':'KINTO-Mechanical-A3-ZH-EN.dwt'}


def plan(spec):
    if not isinstance(spec,dict) or set(spec)-{'schema_version','name','output_root','discipline','pages','purpose','base_project'}:
        raise ValueError('Unknown project specification fields')
    if spec.get('schema_version')!=1 or spec.get('purpose') not in {'test_only','design_draft'}:
        raise ValueError('Version 1 draft/test project required')
    name=spec.get('name','')
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,47}',name) or name.upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(10)],*[f'LPT{i}' for i in range(10)]}:
        raise ValueError('Safe unique project name required')
    discipline=spec.get('discipline')
    if discipline not in TEMPLATES:raise ValueError('Choose mechanical or trebi_electrical')
    root=Path(spec.get('output_root',''))
    if not root.is_absolute():raise ValueError('Absolute output root required')
    folder=root.resolve()/name
    if folder.is_relative_to(ROOT) or folder.exists():raise ValueError('Use a new external project directory')
    pages=spec.get('pages',[])
    if not isinstance(pages,list) or not 1<=len(pages)<=8:raise ValueError('Explicit 1..8 page list required')
    manifest={'schema_version':1,'entries':[{'id':s,'kind':'drawing','logical_page':s,'include_in_total':True,'drawing_file':name+'-'+str(s)+'.dwg'} for s in pages]}
    from src.autocad.trebi_project_pages import plan as page_plan
    page_data=page_plan(manifest)
    if discipline=='trebi_electrical':
        base=Path(spec.get('base_project',''))
        if not base.is_absolute() or base.suffix.lower()!='.wdp' or not base.is_file():raise ValueError('Explicit existing base WDP required for native project settings')
    template=ROOT/'templates'/TEMPLATES[discipline]
    if not template.is_file():raise ValueError('Installed project template missing')
    drawings=folder/'drawings'
    return {'success':True,'submitted':False,'folder':str(folder),'discipline':discipline,'template':str(template),'template_sha256':digest(template),
            'manifest':manifest,'pages':page_data,'drawings':[str(drawings/e['drawing_file']) for e in manifest['entries']],
            'project_path':str(drawings/(name+'.wdp')) if discipline=='trebi_electrical' else None,
            'directories':[str(folder/s) for s in ['drawings','exports/pdf','reports','backups','evidence']], 'production_ready':False}


def execute(spec):
    from src.autocad.connection import get_connection
    from src.autocad.com_runtime import create_document_from_template,read_call,wait_for_document
    from src.autocad.lisp_bridge import evaluate,literal
    from src.tools.native_project import guard
    from src.autocad.trebi_native_grid import configure
    from src.autocad.trebi_title_mapping import apply as apply_title,WDT
    from src.autocad.utils import get_block_attributes
    try:
        planned=plan(spec);conn=get_connection();app=conn.get_application();original=app.ActiveDocument
        original_path=read_call(lambda:original.FullName)
        if not original_path:raise ValueError('Start from an identifiable saved-path document')
        if planned['discipline']=='trebi_electrical':guard(conn,spec['base_project'])
    except Exception as exc:return {'success':False,'status':'preflight_rejected','submitted':False,'error':str(exc)}
    folder=Path(planned['folder']);folder.mkdir(parents=True,exist_ok=False)
    for d in planned['directories']:Path(d).mkdir(parents=True,exist_ok=False)
    receipt=folder/'evidence/create-project.json'
    report={'success':False,'submitted':True,'status':'running','plan':planned,'steps':[],'receipt':str(receipt),'production_ready':False,'automatic_retry':False}
    def persist():receipt.write_text(json.dumps(report,indent=2),encoding='utf8')
    def step(name,fn):
        row={'step':name,'status':'entered'};report['steps'].append(row);persist()
        result=fn()
        if isinstance(result,dict) and result.get('success') is False:raise RuntimeError(str(result))
        row.update(status='completed');persist();return result
    try:
        for target in planned['drawings']:
            step('create:'+Path(target).name,lambda target=target:create_document_from_template(app,planned['template'],target))
        if planned['discipline']=='trebi_electrical':
            wdp=Path(planned['project_path']);wdp.with_suffix('.wdt').write_bytes(WDT.read_bytes())
            # Copy settings only from the explicitly validated base project, never its drawing list.
            step('select_base_settings',lambda:evaluate(conn,'(progn (c:wd_makeproj_current '+literal(str(Path(spec['base_project']).resolve()).replace('\\','/'))+') T)'))
            from src.tools.native_project import state
            if Path(state(conn)['project']).resolve()!=Path(spec['base_project']).resolve():raise RuntimeError('Base project changed')
            headers=['','KINTO DRAFT PROJECT']+['']*18+[str(len(planned['drawings']))]
            step('create_wdp',lambda:evaluate(conn,'((lambda (/ p) (setq p (c:wd_proj_wdp_data)) (c:wd_proj_wdp_write '+literal(wdp.as_posix())+' '+literal(headers)+' (nth 3 p) (nth 4 p) nil) T))'))
            step('activate_project',lambda:evaluate(conn,'(progn (c:wd_makeproj_current '+literal(wdp.as_posix())+') T)'))
            for target in planned['drawings']:
                result=step('add_page:'+Path(target).name,lambda target=target:evaluate(conn,'(c:ace_add_dwg_to_project '+literal(target.replace('\\','/'))+' (list "" "" "DRAFT NOT FOR CONSTRUCTION" nil nil))'))
                if result!=1:raise RuntimeError('Native page registration unconfirmed')
            for target,page in zip(planned['drawings'],spec['pages']):
                doc=next(d for d in app.Documents if Path(d.FullName).resolve()==Path(target).resolve())
                read_call(lambda:doc.Activate)();wait_for_document(app,target)
                step('grid:'+page,lambda:configure(conn,target,page))
                step('title:'+page,lambda:apply_title(conn,str(wdp),planned['manifest'],target))
                def save_ready():
                    ready=wait_for_document(app,target)
                    if not read_call(lambda:bool(ready.Saved)):read_call(lambda:ready.Save)()
                    wait_for_document(app,target)
                    if not read_call(lambda:bool(ready.Saved)):raise RuntimeError('Save not confirmed')
                step('save:'+page,save_ready)
        for target in planned['drawings']:
            doc=next(d for d in app.Documents if Path(d.FullName).resolve()==Path(target).resolve())
            if not read_call(lambda:bool(doc.Saved)):raise RuntimeError('Created drawing not saved')
        step('restore_original',lambda:read_call(lambda:original.Activate)())
        wait_for_document(app,original_path)
        if planned['discipline']=='trebi_electrical':
            step('restore_base_project',lambda:evaluate(conn,'(progn (c:wd_makeproj_current '+literal(str(Path(spec['base_project']).resolve()).replace('\\','/'))+') T)'))
            guard(conn,spec['base_project'])
        report.update(success=True,status='empty_project_created',save_reopen='pending_independent_verification')
        (folder/'project.json').write_text(json.dumps({'spec':spec,'plan':planned},indent=2),encoding='utf8')
    except Exception as exc:
        report.update(status='partial_or_unknown',error=str(exc))
        if report['steps']:report['steps'][-1]['status']='failed_or_unknown'
    finally:persist()
    return report
