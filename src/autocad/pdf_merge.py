"""Merge native plot pages in manifest order; verify streams, size and rotation."""
import argparse
import hashlib
import json
from pathlib import Path
from pypdf import PdfReader, PdfWriter


def fingerprint(page):
    content = page.get_contents()
    return {'content_sha256': hashlib.sha256(content.get_data() if content is not None else b'').hexdigest(),
            'mediabox': [float(v) for v in page.mediabox],
            'cropbox': [float(v) for v in page.cropbox], 'rotation': page.rotation}


def merge(manifest_path, output):
    manifest_path, output = Path(manifest_path).resolve(strict=True), Path(output).resolve()
    if output.exists():
        raise ValueError('Output already exists; no overwrite permitted')
    manifest = json.loads(manifest_path.read_text(encoding='utf8'))
    entries = manifest['pages']
    if manifest['status'] != 'NATIVE_PAGES_CREATED' or not entries:
        raise ValueError('Native plot job is incomplete')
    if [p['page'] for p in entries] != list(range(1, len(entries) + 1)):
        raise ValueError('Manifest page order is invalid')
    paths = [Path(e['raw_pdf']).resolve(strict=True) for e in entries]
    if len(set(paths)) != len(paths) or output in paths:
        raise ValueError('Duplicate inputs or output conflicts')
    writer = PdfWriter()
    readers, expected = [], []
    for entry, path in zip(entries, paths):
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['raw_sha256']:
            raise ValueError('Raw PDF hash mismatch')
        reader = PdfReader(path); readers.append(reader)
        if len(reader.pages) != 1:
            raise ValueError('Each native input must contain exactly one page')
        page = reader.pages[0]; fp = fingerprint(page)
        width, height = fp['mediabox'][2] - fp['mediabox'][0], fp['mediabox'][3] - fp['mediabox'][1]
        if abs(width - 1190.55) > 2 or abs(height - 841.89) > 2 or fp['rotation'] != 0:
            raise ValueError('Expected unrotated landscape A3')
        expected.append(fp)
        # Copy page resources with pypdf; malformed document XMP is intentionally not copied.
        writer.add_page(page)
    writer.pdf_header = max(r.pdf_header for r in readers)
    writer.add_metadata({'/Title': 'Synthetic electrical project - NOT FOR CONSTRUCTION'})
    temp = output.with_suffix('.partial.pdf')
    if temp.exists():
        raise ValueError('Partial file exists; inspect previous job first')
    with temp.open('xb') as stream:
        writer.write(stream)
    result = PdfReader(temp, strict=True)
    if [fingerprint(p) for p in result.pages] != expected:
        raise ValueError('Merged page streams, order or geometry changed; partial file retained')
    temp.rename(output)
    return {'status': 'STRUCTURE_VERIFIED', 'pages': len(expected),
            'output': str(output), 'page_fingerprints': expected,
            'page_order': [e['source_dwg'] for e in entries], 'visual_review': 'PENDING'}
