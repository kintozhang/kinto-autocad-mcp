"""Offline, explicit-file snapshots. Never overwrite CAD projects or clear execution locks."""
import hashlib
import json
import shutil
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def member(root, relative):
    relative = Path(relative)
    if relative.is_absolute() or relative.drive or '..' in relative.parts or not relative.parts:
        raise ValueError('Expected a relative file within the project')
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('File escapes project root')
    if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != root.parent):
        raise ValueError('Symbolic links are not supported')
    return path


def backup(source, destination, files):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not source.is_dir() or not files:
        raise ValueError('Existing source and explicit nonempty file list required')
    if destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError('Archive must be outside source tree')
    rows = []
    seen = set()
    for name in files:
        path = member(source, name)
        key = Path(name).as_posix().casefold()
        if key in seen or not path.is_file():
            raise ValueError('Duplicate or missing source file')
        seen.add(key)
        rows.append({'path': Path(name).as_posix(), 'sha256': digest(path), 'size': path.stat().st_size})
    destination.mkdir(parents=True, exist_ok=False)
    # A failed copy remains without a completion manifest for inspection.
    for row in rows:
        target = member(destination / 'files', row['path'])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(member(source, row['path']), target)
        if digest(target) != row['sha256']:
            raise RuntimeError('Copied file hash mismatch')
    if any(digest(member(source, row['path'])) != row['sha256'] for row in rows):
        raise RuntimeError('Source changed during snapshot; archive incomplete')
    manifest = {'schema_version': 1, 'scope': 'explicit_saved_files_only',
                'source': str(source), 'files': rows, 'unsaved_cad_state_included': False}
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf8')
    return verify(destination)


def verify(archive):
    archive = Path(archive).resolve()
    data = json.loads((archive / 'manifest.json').read_text(encoding='utf8'))
    if data.get('schema_version') != 1 or data.get('scope') != 'explicit_saved_files_only' or not data.get('files'):
        raise ValueError('Invalid archive manifest')
    seen = set()
    for row in data['files']:
        key = row['path'].casefold()
        path = member(archive / 'files', row['path'])
        if key in seen or not path.is_file() or path.stat().st_size != row['size'] or digest(path) != row['sha256']:
            raise ValueError('Archive is incomplete or modified')
        seen.add(key)
    return data


def restore(archive, destination):
    archive, destination = Path(archive).resolve(), Path(destination).resolve()
    data = verify(archive)
    if destination.is_relative_to(archive) or archive.is_relative_to(destination):
        raise ValueError('Restore directory must be independent of archive')
    destination.mkdir(parents=True, exist_ok=False)
    for row in data['files']:
        target = member(destination, row['path'])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(member(archive / 'files', row['path']), target)
        if digest(target) != row['sha256']:
            raise RuntimeError('Restored file mismatch; do not open incomplete restore')
    return {'success': True, 'destination': str(destination), 'files': len(data['files']),
            'cad_opened': False, 'project_references_rewritten': False}


def receipt_summary(paths):
    """Execution evidence only: never promote receipts to production approval."""
    rows = []
    for name in paths:
        path = Path(name)
        try:
            data = json.loads(path.read_text(encoding='utf8'))
            success = data.get('success') is True
            steps = data.get('steps', [])
            pending = [s.get('step', '?') for s in steps if s.get('status') != 'completed']
            if data.get('status') == 'preflight_rejected' and data.get('submitted') is False:
                state = 'not_submitted'
            elif success and steps and not pending and data.get('status') in {'native_change_readback_verified', 'completed', 'native_batch_verified'}:
                state = 'execution_completed_requires_acceptance'
            else:
                state = 'unknown_or_partial_do_not_replay'
            rows.append({'path': str(path), 'sha256': digest(path), 'state': state,
                         'incomplete_steps': pending, 'failed_step': data.get('failed_step'),
                         'backup': data.get('backup'), 'save_reopen': data.get('save_reopen', 'unknown')})
        except Exception as exc:
            rows.append({'path': str(path), 'state': 'unreadable', 'error': str(exc)})
    return {'scope': 'execution_receipts_only', 'production_ready': False, 'receipts': rows,
            'requires_separate_acceptance': ['hardware_revision', 'io_mapping', 'saved_reopen',
                                             'native_networks', 'cross_references', 'reports', 'pdf_visual_review']}

def backup_saved_project(project_path, project, destination):
    from src.autocad.engineering_archive import backup
    wdp = Path(project_path).resolve()
    paths = [wdp, wdp.with_suffix('.wdt')] + [Path(p).resolve() for p in project['drawings']]
    if any(p.parent != wdp.parent for p in paths):
        raise ValueError('Restricted backup requires project files in one directory')
    data = backup(wdp.parent, destination, [p.name for p in paths])
    return {'path': str(destination), 'scope': 'saved_wdp_wdt_project_drawings_only',
            'files': data['files'], 'external_dependencies_included': False}

