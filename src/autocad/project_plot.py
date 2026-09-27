"""Opt-in A3 plotting of saved synthetic WDP snapshots; never edits source DWGs."""
import argparse
import hashlib
import json
import shutil
import time
from pathlib import Path
from src.autocad.com_runtime import read_call, wait_for_document, lookup_document_open

DEVICE = 'AutoCAD PDF (High Quality Print).pc3'
MEDIA = 'ISO_A3_(420.00_x_297.00_MM)'


def project_pages(wdp):
    """Bounded fixture format: plain relative DWG entries in WDP order."""
    wdp = Path(wdp).resolve(strict=True)
    pages = []
    for line in wdp.read_text(encoding='utf-8-sig').splitlines():
        entry = line.strip()
        if not entry.lower().endswith('.dwg') or entry.startswith(('+', '===', '*')):
            continue
        path = (wdp.parent / entry).resolve(strict=True)
        if path.parent != wdp.parent or path.suffix.lower() != '.dwg':
            raise ValueError('Only sibling DWG files are supported')
        if path in pages:
            raise ValueError('Duplicate project drawing')
        pages.append(path)
    if not pages:
        raise ValueError('No supported project drawings')
    return pages


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def trebi_page(doc, total, *, allow_draft_metadata=False):
    """Read the source identity before plotting; never replace logical pages with PDF indices."""
    from src.autocad.trebi_rules import profile, validate_fields
    from src.autocad.trebi_native_grid import settings
    from src.autocad.utils import get_block_attributes
    blocks=[e for e in doc.ModelSpace if e.ObjectName=='AcDbBlockReference']
    titles=[e for e in blocks if e.Name==profile()['block_name']]
    natives=[e for e in blocks if e.Name=='WD_M']
    if len(titles)!=1 or len(natives)!=1: raise ValueError('Expected unique TREBI title and WD_M')
    title=titles[0]
    if tuple(title.InsertionPoint)!=(0.,0.,0.) or title.Rotation!=0 or any(getattr(title,k)!=1 for k in ['XScaleFactor','YScaleFactor','ZScaleFactor']):
        raise ValueError('TREBI frame must have its verified origin, scale and rotation')
    fields=get_block_attributes(title);validate_fields(fields,allow_draft_metadata=allow_draft_metadata)
    expected=settings(fields['PAGE']);native=get_block_attributes(natives[0])
    if any(native.get(k)!=v for k,v in expected.items()): raise ValueError('TREBI native grid disagrees with frame')
    if fields['OF']!=str(total): raise ValueError('TREBI OF must equal effective project drawing count')
    return {'logical_page':fields['PAGE'],'title_fields':fields,**({'draft_metadata_pending':[k for k,v in fields.items() if not v]} if allow_draft_metadata else {})}


def trebi_project(members,pages, *, allow_draft_metadata=False):
    from src.autocad.trebi_rules import page_navigation
    identities=[trebi_page(members[p],len(pages),allow_draft_metadata=allow_draft_metadata) for p in pages]
    logical=[v['logical_page'] for v in identities]
    for identity in identities:
        wanted=page_navigation(logical,identity['logical_page'])
        if any(identity['title_fields'][k]!=v for k,v in wanted.items()): raise ValueError('TREBI navigation differs from project order')
    return identities


def plot_snapshot(source, staging, app, expected_hashes=None, template_mode="synthetic_din_a3", trebi_pages=None):
    """Plot explicitly synthetic DIN A3 copies using an already guarded CAD app."""
    if template_mode not in {'synthetic_din_a3','synthetic_zh_en_a3','synthetic_trebi_a3'}:
        raise ValueError('Unsupported synthetic template mode')
    if template_mode=='synthetic_trebi_a3' and not trebi_pages:
        raise ValueError('TREBI project identities must be preflighted before plotting')
    source = Path(source).resolve(strict=True)
    pages = project_pages(source)
    staging = Path(staging).resolve()
    staging.mkdir(parents=True, exist_ok=False)
    report = {'status': 'RUNNING', 'source_project': str(source),
              'source_mode': 'saved_disk_snapshot', 'device': DEVICE, 'media': MEDIA,
              'scale': 'fit_to_page_NTS', 'pages': []}
    original_hashes = {str(p): digest(p) for p in [source, *pages]}
    if expected_hashes is not None and original_hashes != expected_hashes:
        raise RuntimeError('Source changed after preflight')
    report['source_sha256'] = original_hashes
    manifest = staging / 'plot-manifest.json'
    def record():
        manifest.write_text(json.dumps(report, indent=2), encoding='utf8')
    record()
    import pythoncom
    import win32com.client
    try:
        for index, page in enumerate(pages, 1):
            copy = staging / f'{index:02d}-{staging.name}-{page.name}'
            shutil.copy2(page, copy)
            if digest(copy) != original_hashes[str(page)]:
                raise RuntimeError('Source changed while copying')
            pdf = staging / f'{index:02d}-native.pdf'
            item = {'page': index, 'source_dwg': str(page), 'copy_dwg': str(copy),
                    'raw_pdf': str(pdf), 'status': 'COPY_CREATED'}
            report['pages'].append(item); record()
            lookup_document_open(app)(str(copy))
            doc = wait_for_document(app, copy)  # Fresh typed document after Open readiness.
            def guard():
                if Path(read_call(lambda: app.ActiveDocument.FullName, label="plot target")).resolve() != copy:
                    raise RuntimeError('Active drawing changed; stopped without retry')
            guard()
            # These are explicitly synthetic acceptance copies, not a generic template edit.
            if template_mode=='synthetic_trebi_a3':
                identity=trebi_page(doc,len(pages),allow_draft_metadata=True)
                if identity!=trebi_pages[index-1]: raise RuntimeError('Copied TREBI identity changed')
                item.update(identity)
                from src.autocad.pdf_navigation import collect
                item['navigation']=collect(doc, 'KINTO_TREBI_ELECTRICAL_A3')
                # Margin above the 0..9 header; do not cover circuit content or overwrite PAGE/OF.
                point=win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,(10.,292.,0.))
                doc.ModelSpace.AddText(f'SYNTHETIC TEST - NOT FOR CONSTRUCTION - NTS / PDF SHEET {index}/{len(pages)}',point,2.)
            else:
                wanted_block = 'kinto_tb_a3_zh_en' if template_mode == 'synthetic_zh_en_a3' else 'din_tblock_a3'
                wanted_scale = 'SCALE' if template_mode == 'synthetic_zh_en_a3' else 'MA\u00dfSTAB'.upper()
                scales = []
                for entity in doc.ModelSpace:
                    if entity.ObjectName == 'AcDbBlockReference' and entity.Name.lower() == wanted_block and entity.HasAttributes:
                        scales.extend(a for a in entity.GetAttributes() if a.TagString.upper() == wanted_scale)
                if len(scales) != 1:
                    raise ValueError('Expected one DIN A3 scale attribute in synthetic fixture')
                scales[0].TextString = 'NTS'
                point = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, (40., 255., 0.))
                doc.ModelSpace.AddText(f'SYNTHETIC TEST - NOT FOR CONSTRUCTION / PAGE {index} OF {len(pages)}', point, 3.)
            guard()
            layout = doc.ActiveLayout
            if not layout.ModelType:
                raise ValueError('Only Model layout is supported')
            layout.RefreshPlotDeviceInfo()
            if DEVICE not in layout.GetPlotDeviceNames():
                raise ValueError('Required PDF device unavailable')
            layout.ConfigName = DEVICE; layout.RefreshPlotDeviceInfo()
            if MEDIA not in layout.GetCanonicalMediaNames():
                raise ValueError('Required A3 media unavailable')
            layout.CanonicalMediaName = MEDIA
            layout.PaperUnits = 1; layout.PlotRotation = 0; layout.PlotType = 1
            layout.UseStandardScale = True; layout.StandardScale = 0; layout.CenterPlot = True
            layout.StyleSheet = 'monochrome.ctb'
            layout.PlotWithPlotStyles = True; layout.PlotWithLineweights = True
            item['settings_read_back'] = {'device': layout.ConfigName, 'media': layout.CanonicalMediaName,
                'style': layout.StyleSheet, 'rotation': layout.PlotRotation,
                'plot_type': layout.PlotType, 'standard_scale': layout.StandardScale}
            if item['settings_read_back'] != {'device': DEVICE, 'media': MEDIA, 'style': 'monochrome.ctb',
                                               'rotation': 0, 'plot_type': 1, 'standard_scale': 0}:
                raise RuntimeError('Plot settings readback mismatch')
            bg = doc.GetVariable('BACKGROUNDPLOT')
            guard(); doc.SetVariable('BACKGROUNDPLOT', 0)
            try:
                doc.Regen(1); doc.Save(); guard()
                item['status'] = 'PLOT_SUBMITTING'; record()
                ok = doc.Plot.PlotToFile(str(pdf))
            finally:
                guard(); doc.SetVariable('BACKGROUNDPLOT', bg)
            guard()
            if not ok or not pdf.is_file() or pdf.stat().st_size == 0:
                raise RuntimeError('Native plot did not produce a nonempty PDF')
            item.update(status='NATIVE_PDF_CREATED', raw_sha256=digest(pdf)); record()
        if any(digest(path) != value for path, value in original_hashes.items()):
            raise RuntimeError('Source snapshot changed during plotting')
        report.update(status='NATIVE_PAGES_CREATED', source_files_unchanged=True)
    except Exception as exc:
        report.update(status='FAILED', error=str(exc), retry_safe=False)
        raise
    finally:
        record()
    return manifest


def method(read):
    # Retry method lookup only, never re-submit a write whose result is uncertain.
    for attempt in range(10):
        try:
            return read()
        except AttributeError:
            if attempt == 9:
                raise
            time.sleep(.3)


def ready(doc):
    for attempt in range(30):
        try:
            if int(doc.GetVariable('CMDACTIVE')) == 0:
                return
        except Exception:
            if attempt == 29:
                raise
        time.sleep(.25)
    raise RuntimeError('CAD is busy; no write attempted')
