"""Guarded synthetic DIN A3 snapshot PDF export. No model/API dependency."""
import json
from pathlib import Path
from uuid import uuid4
from src.autocad.com_runtime import read_call, wait_for_document
from src.autocad.connection import get_connection
from src.autocad.lisp_bridge import _LOCK
from src.autocad.project_plot import project_pages, digest, plot_snapshot, trebi_project
from src.tools.native_project import guard


def output_target(value):
    path = Path(value)
    if not path.is_absolute() or path.suffix.lower() != '.pdf':
        raise ValueError('Output must be an absolute PDF path')
    path = path.resolve()
    if not path.parent.is_dir():
        raise ValueError('Output parent directory must exist')
    if path.exists() or path.with_suffix('.partial.pdf').exists():
        raise ValueError('Output or partial PDF already exists; no overwrite')
    return path


def saved_members(app, pages):
    def snapshot():
        found = {}
        docs = app.Documents
        for i in range(docs.Count):
            doc = docs.Item(i)
            path = Path(doc.FullName).resolve()
            if path in pages:
                if path in found:
                    raise ValueError('Duplicate open project drawing')
                if not doc.Saved:
                    raise ValueError('All project drawings must be saved before export')
                found[path] = doc
        if set(found) != set(pages):
            raise ValueError('All project drawings must be open before export')
        return found
    return read_call(snapshot, label='saved project members')


def export_pdf(project_path, output_path, template_mode):
    operation = None
    try:
        if template_mode not in {'synthetic_din_a3', 'synthetic_zh_en_a3', 'synthetic_trebi_a3'}:
            raise ValueError('Only synthetic DIN, bilingual or TREBI A3 test exports are supported')
        output = output_target(output_path)
        project = Path(project_path)
        if not project.is_absolute() or project.suffix.lower() != '.wdp':
            raise ValueError('Expected an absolute WDP path')
        project = project.resolve(strict=True)
        # Optional dependency must be ready before any CAD/file mutation.
        from src.autocad.pdf_merge import merge
        with _LOCK:
            conn = get_connection()
            state = guard(conn, str(project))
            pages = project_pages(project)
            if pages != [Path(p).resolve() for p in state['drawings']]:
                raise ValueError('Parsed WDP order differs from Electrical project order')
            app = conn.get_application()
            original = conn.get_active_document()
            original_path = Path(original.FullName).resolve()
            members=saved_members(app, pages)
            trebi=trebi_project(members,pages) if template_mode=='synthetic_trebi_a3' else None
            hashes = {str(p): digest(p) for p in [project, *pages]}
            operation = output.parent / ('pdf-job-' + uuid4().hex)
            # plot_snapshot creates the fresh operation directory and retains failure receipts.
            manifest = plot_snapshot(project, operation, app, hashes, template_mode=template_mode, trebi_pages=trebi)
            active = Path(app.ActiveDocument.FullName).resolve()
            if active.parent != operation:
                raise RuntimeError('Active document changed; stopped without restoring over user navigation')
            original.Activate()
            wait_for_document(app, original_path)
            if Path(app.ActiveDocument.FullName).resolve() != original_path:
                raise RuntimeError('Original active drawing restoration failed')
            if [Path(p).resolve() for p in guard(conn, str(project))['drawings']] != pages:
                raise RuntimeError('Project membership changed during plot')
            saved_members(app, pages)
            if any(digest(p) != h for p, h in hashes.items()):
                raise RuntimeError('Source snapshot changed during export')
            result = merge(manifest, output)
            result.update(success=True, status='pdf_structure_verified', project=str(project),
                          operation_directory=str(operation), source_files_unchanged=True,
                          active_drawing_restored=True, template_mode=template_mode,
                          note='Synthetic test PDF only. Visual review PENDING; no construction/design acceptance.')
            if trebi is not None:
                result['logical_page_order']=[p['logical_page'] for p in trebi]
            (operation / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf8')
            return result
    except Exception as exc:
        result = {'success': False, 'error': str(exc), 'retry_safe': False,
                  'operation_directory': str(operation) if operation else None,
                  'status': 'partial_or_unknown' if operation else 'preflight_rejected',
                  'submitted': True if operation else False}
        if operation and operation.is_dir():
            (operation / 'error.json').write_text(json.dumps(result, indent=2), encoding='utf8')
        return result
