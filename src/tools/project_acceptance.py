"""Version-bound engineering evidence review. Never grants production approval."""
import json
from pathlib import Path
from src.autocad.engineering_archive import digest
from src.autocad.project_plot import project_pages
REQUIRED=('hardware_identity','io_mapping','tag_uniqueness','connections','cross_references','bom','terminals','save_reopen','pdf_review','engineering_review')


def audit(project_path, evidence_files):
    project=Path(project_path).resolve(strict=True)
    drawings=project_pages(project)
    subjects={str(p):digest(p) for p in [project,*drawings]}
    findings=[]; accepted={}
    for name in evidence_files:
        path=Path(name)
        try:
            data=json.loads(path.read_text(encoding='utf8'))
            kind=data['kind']
            if data.get('schema_version')!=1 or kind not in REQUIRED:raise ValueError('Unknown evidence schema/category')
            if kind in accepted:raise ValueError('Duplicate evidence category')
            if data.get('subjects')!=subjects:raise ValueError('Evidence belongs to another or modified project version')
            checks=data.get('checks')
            if not isinstance(checks,list) or not checks:raise ValueError('Nonempty check list required')
            ids=set()
            for check in checks:
                if not isinstance(check.get('id'),str) or not check['id'] or check['id'] in ids:raise ValueError('Unique check identity required')
                ids.add(check['id'])
                if check.get('status')!='pass':raise ValueError('Failed or unknown check: '+check['id'])
                source=Path(check['source_path'])
                if not source.is_absolute() or digest(source)!=check['source_sha256']:raise ValueError('Missing or changed source evidence')
            if not isinstance(data.get('reviewer'),str) or not data['reviewer'].strip():raise ValueError('Evidence reviewer/producer required')
            accepted[kind]={'path':str(path.resolve()),'sha256':digest(path),'checks':len(checks),'reviewer':data['reviewer']}
        except Exception as exc:findings.append({'path':str(path),'reason':str(exc)})
    missing=[k for k in REQUIRED if k not in accepted]
    blockers=[{'category':k,'reason':'Missing valid current-version evidence'} for k in missing]+findings
    return {'success':True,'project':str(project),'subjects':subjects,'accepted':accepted,'blockers':blockers,
            'evidence_complete':not blockers,'production_ready':False,'formal_export_allowed':False,
            'status':'evidence_complete_requires_engineering_release' if not blockers else 'blocked',
            'limitations':['Checks summarize supplied evidence; this does not independently inspect hardware or CAD',
                           'Evidence integrity is not engineering approval; formal release remains unsupported']}
