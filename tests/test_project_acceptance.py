import json
from pathlib import Path
import pytest
from src.tools.project_acceptance import audit,REQUIRED
from src.autocad.engineering_archive import digest,backup
from src.tools.project_recovery import recover


def project(tmp_path):
    folder=tmp_path/'project';folder.mkdir()
    (folder/'page.dwg').write_bytes(b'dwg')
    (folder/'p.wdt').write_text('mapping')
    p=folder/'p.wdp';p.write_text('page.dwg\n')
    return p


def test_missing_evidence_blocks(tmp_path):
    r=audit(project(tmp_path),[])
    assert len(r['blockers'])==len(REQUIRED) and not r['formal_export_allowed']


def test_complete_evidence_never_auto_approves_engineering(tmp_path):
    p=project(tmp_path);subjects=audit(p,[])['subjects'];files=[]
    source=tmp_path/'source.json';source.write_text('raw evidence')
    for kind in REQUIRED:
        e=tmp_path/(kind+'.json');e.write_text(json.dumps({'schema_version':1,'kind':kind,'subjects':subjects,'reviewer':'test reviewer',
            'checks':[{'id':'one','status':'pass','source_path':str(source),'source_sha256':digest(source)}]}));files.append(str(e))
    r=audit(p,files);assert r['evidence_complete'] and not r['production_ready']
    source.write_text('changed');assert not audit(p,files)['evidence_complete']


def test_stale_drawing_evidence_blocked(tmp_path):
    p=project(tmp_path);subjects=audit(p,[])['subjects']
    e=tmp_path/'e.json';e.write_text(json.dumps({'schema_version':1,'kind':'bom','subjects':subjects,'checks':[]}))
    (p.parent/'page.dwg').write_bytes(b'new revision')
    assert 'modified project' in str(audit(p,[str(e)])['blockers'])


def test_recover_new_name_preserves_data(tmp_path):
    p=project(tmp_path);archive=tmp_path/'archive';backup(p.parent,archive,['p.wdp','p.wdt','page.dwg'])
    r=recover(archive,tmp_path/'restored','NEW-PROJECT')
    assert Path(r['project_path']).name=='NEW-PROJECT.wdp'
    assert Path(r['drawings'][0]).read_bytes()==b'dwg'
    assert not r['cad_reopen_verified']
    with pytest.raises(FileExistsError):recover(archive,tmp_path/'restored','NEW-PROJECT')


def test_recovery_same_name_rejected(tmp_path):
    p=project(tmp_path);archive=tmp_path/'archive';backup(p.parent,archive,['p.wdp','p.wdt','page.dwg'])
    with pytest.raises(ValueError,match='different'):recover(archive,tmp_path/'restore','p')


def test_recovery_absolute_references_rejected(tmp_path):
    p=project(tmp_path);p.write_text(str(p.parent/'page.dwg'))
    archive=tmp_path/'archive';backup(p.parent,archive,['p.wdp','p.wdt','page.dwg'])
    with pytest.raises(ValueError,match='plain sibling'):recover(archive,tmp_path/'restore','NEW')
