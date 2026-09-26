"""Optional PDF-runtime regression tests: python -m unittest discover -s tests -p test_pdf_merge.py."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

PDF_AVAILABLE = importlib.util.find_spec('pypdf') is not None
if PDF_AVAILABLE:
    from pypdf import PdfWriter, PdfReader
    from pypdf.generic import DecodedStreamObject, NameObject
    from scripts.merge_plot_project import merge, fingerprint


@unittest.skipUnless(PDF_AVAILABLE, 'Run with a Python runtime containing pypdf')
class MergeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / 'manifest.json'
        self.output = self.root / 'out.pdf'
        self.entries = []
        for index in (1, 2, 3):
            path = self.root / f'{index}.pdf'
            writer = PdfWriter(); page = writer.add_blank_page(1191, 842)
            content = DecodedStreamObject()
            content.set_data(f'q {index} 0 0 {index} 0 0 cm Q'.encode())
            page[NameObject('/Contents')] = writer._add_object(content)
            with path.open('wb') as stream: writer.write(stream)
            self.entries.append({'page': index, 'source_dwg': f'{index}.dwg', 'raw_pdf': str(path),
                                 'raw_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        self.save()

    def save(self, status='NATIVE_PAGES_CREATED'):
        self.manifest.write_text(json.dumps({'status': status, 'pages': self.entries}))

    def test_preserves_distinct_nonempty_streams_in_order(self):
        result = merge(self.manifest, self.output)
        hashes = [p['content_sha256'] for p in result['page_fingerprints']]
        self.assertEqual(len(set(hashes)), 3)
        self.assertNotIn(hashlib.sha256(b'').hexdigest(), hashes)
        self.assertEqual([fingerprint(p) for p in PdfReader(self.output).pages], result['page_fingerprints'])

    def test_no_overwrite(self):
        self.output.write_bytes(b'original')
        with self.assertRaisesRegex(ValueError, 'already exists'): merge(self.manifest, self.output)
        self.assertEqual(self.output.read_bytes(), b'original')

    def test_rejects_bad_order(self):
        self.entries.reverse(); self.save()
        with self.assertRaisesRegex(ValueError, 'order'): merge(self.manifest, self.output)

    def test_rejects_duplicate_input(self):
        self.entries[1]['raw_pdf'] = self.entries[0]['raw_pdf']; self.save()
        with self.assertRaisesRegex(ValueError, 'Duplicate'): merge(self.manifest, self.output)

    def test_rejects_changed_input(self):
        self.entries[0]['raw_sha256'] = 'wrong'; self.save()
        with self.assertRaisesRegex(ValueError, 'hash mismatch'): merge(self.manifest, self.output)

    def test_rejects_incomplete_job(self):
        self.save('FAILED')
        with self.assertRaisesRegex(ValueError, 'incomplete'): merge(self.manifest, self.output)

    def test_retains_existing_partial(self):
        partial = self.output.with_suffix('.partial.pdf'); partial.write_bytes(b'evidence')
        with self.assertRaisesRegex(ValueError, 'Partial'): merge(self.manifest, self.output)
        self.assertEqual(partial.read_bytes(), b'evidence')
