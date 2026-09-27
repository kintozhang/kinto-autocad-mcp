"""Saved batch reopening and independent native readback; never replays drawing writes."""
from copy import deepcopy
from pathlib import Path
from src.autocad.com_runtime import read_call, wait_for_document, lookup_document_open
from src.autocad.engineering_archive import digest


def validate_saved_targets(metadata, expected):
    by_path={str(Path(row['path']).resolve()).casefold():row for row in metadata}
    if len(by_path)!=len(metadata):raise ValueError('Duplicate open document identity')
    for name in expected:
        row=by_path.get(str(Path(name).resolve()).casefold())
        if row is None or row['saved'] is not True or row['read_only'] is not False:
            raise ValueError('Reopen requires each exact batch drawing open, saved and writable')


def verify(conn,app,recipe,report,folder,docs,activate,step):
    from src.autocad.utils import get_block_attributes
    from src.tools.native_electrical import _points,inspect_wire
    from src.tools.native_project import export_report
    from src.tools.delta_path_acceptance import verify_native
    targets=report['drawings'];folder=Path(folder);folder.mkdir(exist_ok=True)
    metadata=read_call(lambda:[{'path':d.FullName,'saved':bool(d.Saved),'read_only':bool(d.ReadOnly)} for d in app.Documents if d.FullName])
    validate_saved_targets(metadata,targets)
    before={str(Path(p).resolve()):digest(Path(p)) for p in [report['project'],*targets]}
    fresh={key:deepcopy(report[key]) for key in ('entities','references','device_inventory','final_wires','reports')}
    for page,path in zip(recipe['pages']['logical_pages'],targets,strict=True):
        def reopen():
            doc=activate(path)
            if not read_call(lambda:bool(doc.Saved)):raise RuntimeError('Unsaved target changed before close')
            # False cannot discard user changes: Saved was checked immediately above.
            read_call(lambda:doc.Close)(False)
            new=lookup_document_open(app)(str(Path(path).resolve()))
            wait_for_document(app,path)
            docs[str(Path(path).resolve()).casefold()]=new
            return {'success':True,'path':path}
        step('reopen:'+page,reopen);activate(path)
        def snapshot():
            doc=conn.get_active_document();inventory=[]
            for obj in doc.ModelSpace:
                if obj.ObjectName!='AcDbBlockReference' or not obj.HasAttributes:continue
                attrs=get_block_attributes(obj)
                if any(attrs.get(k) for k in ('TAG1','TAG2','TAGSTRIP')):inventory.append({'handle':obj.Handle,'attributes':attrs})
            for c in recipe['components']+recipe.get('cable_markers',[]):
                if c['drawing_page']!=page:continue
                ident=c['id'];obj=doc.HandleToObject(report['entities'][ident]['handle'])
                fresh['references'][ident]=get_block_attributes(obj)
                fresh['entities'][ident]['connection_points']=_points(obj)
            fresh['device_inventory'][page]=inventory
        step('reopen_inventory:'+page,lambda:read_call(snapshot,label='reopened component inventory'))
        for link in recipe['connections']:
            if Path(report['entities'][link['from_id']]['drawing']).resolve()!=Path(path).resolve():continue
            fresh['final_wires'][link['id']]=step('reopen_wire:'+link['id'],lambda:inspect_wire(report['wires'][link['id']]['wire_handles'][0]))
    for kind in ('bom','from_to','terminal_plan','terminal_numbers'):
        fresh['reports'][kind]=step('reopen_report:'+kind,lambda:export_report(report['project'],kind,str(folder/(kind+'.csv'))))
    result=verify_native(recipe,fresh)
    after={p:digest(Path(p)) for p in before}
    if before!=after:raise RuntimeError('Saved project files changed during readback')
    return {'success':True,'status':'saved_reopened_native_verified','subjects':after,'native':result,'snapshot':fresh}
