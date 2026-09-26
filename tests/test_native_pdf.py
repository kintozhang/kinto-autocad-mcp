from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from src.tools import native_pdf


@pytest.mark.parametrize('mode', ['', 'production', 'mechanical'])
def test_unsupported_mode_never_connects(mode):
    with patch.object(native_pdf, 'get_connection') as connect:
        assert not native_pdf.export_pdf('bad', 'bad', mode)['success']
    connect.assert_not_called()


def test_existing_output_never_connects(tmp_path):
    out = tmp_path / 'existing.pdf'; out.write_bytes(b'original')
    with patch.object(native_pdf, 'get_connection') as connect:
        assert not native_pdf.export_pdf('bad', str(out), 'synthetic_din_a3')['success']
    connect.assert_not_called()
    assert out.read_bytes() == b'original'


def test_unsaved_project_rejected():
    page = Path('test.dwg').resolve(); doc = MagicMock(FullName=str(page), Saved=False)
    app = MagicMock(); app.Documents.Count = 1; app.Documents.Item.return_value = doc
    with pytest.raises(ValueError, match='saved'): native_pdf.saved_members(app, [page])


def test_closed_member_rejected():
    app = MagicMock(); app.Documents.Count = 0
    with pytest.raises(ValueError, match='open'): native_pdf.saved_members(app, [Path('test.dwg').resolve()])


def test_wrong_project_never_plots(tmp_path):
    project = tmp_path / 'test.wdp'; project.touch()
    with patch.object(native_pdf, 'get_connection'), patch.object(native_pdf, 'guard', side_effect=ValueError('wrong project')), patch.object(native_pdf, 'plot_snapshot') as plot:
        result = native_pdf.export_pdf(str(project), str(tmp_path/'out.pdf'), 'synthetic_din_a3')
    assert not result['success'] and result['operation_directory'] is None
    plot.assert_not_called()


def test_project_order_mismatch_never_plots(tmp_path):
    project = tmp_path/'test.wdp'; project.touch()
    first, second = tmp_path/'a.dwg', tmp_path/'b.dwg'
    with patch.object(native_pdf, 'get_connection'), patch.object(native_pdf, 'guard', return_value={'drawings':[str(second),str(first)]}), patch.object(native_pdf, 'project_pages', return_value=[first,second]), patch.object(native_pdf, 'plot_snapshot') as plot:
        result = native_pdf.export_pdf(str(project), str(tmp_path/'out.pdf'), 'synthetic_din_a3')
    assert not result['success'] and 'order' in result['error']
    plot.assert_not_called()
