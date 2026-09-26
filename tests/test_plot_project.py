from pathlib import Path
import pytest
from scripts.plot_project_smoke import project_pages


def test_preserves_wdp_order(tmp_path):
    for name in ('z.dwg', 'a.dwg'): (tmp_path / name).touch()
    wdp = tmp_path / 'test.wdp'
    wdp.write_text('+[1]settings\n===description\nz.dwg\na.dwg\n')
    assert [p.name for p in project_pages(wdp)] == ['z.dwg', 'a.dwg']


def test_rejects_duplicate_page(tmp_path):
    (tmp_path / 'a.dwg').touch()
    wdp = tmp_path / 'test.wdp'; wdp.write_text('a.dwg\na.dwg\n')
    with pytest.raises(ValueError, match='Duplicate'): project_pages(wdp)


def test_rejects_outside_project(tmp_path):
    (tmp_path / 'a.dwg').touch(); child = tmp_path / 'child'; child.mkdir()
    wdp = child / 'test.wdp'; wdp.write_text('../a.dwg\n')
    with pytest.raises(ValueError, match='sibling'): project_pages(wdp)


def test_rejects_missing_page(tmp_path):
    wdp = tmp_path / 'test.wdp'; wdp.write_text('missing.dwg\n')
    with pytest.raises(FileNotFoundError): project_pages(wdp)


def test_rejects_empty_project(tmp_path):
    wdp = tmp_path / 'test.wdp'; wdp.write_text('+[1]nothing\n')
    with pytest.raises(ValueError, match='No supported'): project_pages(wdp)
