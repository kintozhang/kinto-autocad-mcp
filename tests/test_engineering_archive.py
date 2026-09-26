import json
import pytest
from src.autocad.engineering_archive import backup, verify, restore, receipt_summary


def fixture(tmp_path):
    source = tmp_path / 'source'; source.mkdir()
    (source / 'page.dwg').write_bytes(b'original')
    (source / 'project.wdp').write_bytes(b'page.dwg')
    return source, tmp_path / 'archive'


def test_roundtrip_and_no_overwrite(tmp_path):
    source, archive = fixture(tmp_path)
    data = backup(source, archive, ['page.dwg', 'project.wdp'])
    assert not data['unsaved_cad_state_included']
    dest = tmp_path / 'restored'
    assert restore(archive, dest)['files'] == 2
    assert (dest / 'page.dwg').read_bytes() == b'original'
    with pytest.raises(FileExistsError): restore(archive, dest)
    with pytest.raises(FileExistsError): backup(source, archive, ['page.dwg'])
    assert (source / 'page.dwg').read_bytes() == b'original'


@pytest.mark.parametrize('files', [[], ['../page.dwg'], ['C:/outside.dwg'], ['missing.dwg'], ['page.dwg', 'PAGE.dwg']])
def test_invalid_inventory_rejected_before_archive(tmp_path, files):
    source, archive = fixture(tmp_path)
    with pytest.raises(ValueError): backup(source, archive, files)
    assert not archive.exists()


def test_changed_backup_cannot_restore(tmp_path):
    source, archive = fixture(tmp_path)
    backup(source, archive, ['page.dwg'])
    (archive / 'files/page.dwg').write_bytes(b'changed')
    dest = tmp_path / 'restored'
    with pytest.raises(ValueError): restore(archive, dest)
    assert not dest.exists()


def test_manifest_traversal_cannot_restore(tmp_path):
    source, archive = fixture(tmp_path)
    backup(source, archive, ['page.dwg'])
    p = archive / 'manifest.json'; data = json.loads(p.read_text())
    data['files'][0]['path'] = '../../source/page.dwg'; p.write_text(json.dumps(data))
    with pytest.raises(ValueError): verify(archive)


def test_source_mutation_during_copy_leaves_no_manifest(tmp_path, monkeypatch):
    import src.autocad.engineering_archive as module
    source, archive = fixture(tmp_path); original = module.shutil.copyfile
    def copying(src, dst):
        original(src, dst); src.write_bytes(b'changed')
    monkeypatch.setattr(module.shutil, 'copyfile', copying)
    with pytest.raises(RuntimeError): backup(source, archive, ['page.dwg'])
    assert not (archive / 'manifest.json').exists()


def test_nested_archive_rejected(tmp_path):
    source, _ = fixture(tmp_path)
    with pytest.raises(ValueError): backup(source, source / 'backup', ['page.dwg'])


@pytest.mark.parametrize('status,success,step,expected', [
    ('native_change_readback_verified', True, 'completed', 'execution_completed_requires_acceptance'),
    ('running', True, 'completed', 'unknown_or_partial_do_not_replay'),
    ('partial_or_unknown', False, 'entered', 'unknown_or_partial_do_not_replay'),
    ('native_change_readback_verified', True, 'failed_or_unknown', 'unknown_or_partial_do_not_replay'),
])
def test_receipts_never_approve_production(tmp_path, status, success, step, expected):
    p = tmp_path / 'receipt.json'
    p.write_text(json.dumps({'status': status, 'success': success, 'steps': [{'step': 'save', 'status': step}]}))
    result = receipt_summary([p])
    assert result['production_ready'] is False
    assert result['receipts'][0]['state'] == expected


def test_missing_receipt_is_unknown(tmp_path):
    assert receipt_summary([tmp_path / 'missing'])['receipts'][0]['state'] == 'unreadable'
