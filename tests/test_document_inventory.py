from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from src.autocad.com_runtime import document_inventory, ComBusyError


def doc(name, path=''):
    return SimpleNamespace(Name=name, FullName=path, Saved=False)


def test_unsaved_documents_keep_distinct_names():
    app=SimpleNamespace(HWND=7, Documents=[doc('Drawing1'),doc('Drawing2')])
    rows=document_inventory(app,interval=0)
    assert len(rows)==2 and rows[0]['identity']!=rows[1]['identity']
    assert all(r['path']=='' for r in rows)


def test_transient_enumeration_failure_recovered():
    app=MagicMock();app.HWND=7
    app.Documents.__iter__.side_effect=[TypeError('This object does not support enumeration'),iter([doc('Drawing1')]),iter([doc('Drawing1')])]
    assert document_inventory(app,interval=0)[0]['name']=='Drawing1'


def test_ambiguous_names_rejected():
    with pytest.raises(ValueError,match='Ambiguous'):
        document_inventory(SimpleNamespace(HWND=7,Documents=[doc('Drawing1'),doc('drawing1')]),interval=0)


def test_unstable_collection_rejected():
    app=MagicMock();app.HWND=7
    app.Documents.__iter__.side_effect=[iter([doc('Drawing1')]),iter([doc('Drawing2')])]
    with pytest.raises(ComBusyError):document_inventory(app,attempts=2,interval=0)


def test_unknown_exception_not_retried():
    app=MagicMock();app.HWND=7;app.Documents.__iter__.side_effect=RuntimeError('unexpected')
    with pytest.raises(RuntimeError,match='unexpected'):document_inventory(app,interval=0)
    assert app.Documents.__iter__.call_count==1


def test_same_basename_in_different_projects_is_distinct():
    app=SimpleNamespace(HWND=7, Documents=[doc('page.dwg','C:/one/page.dwg'),doc('page.dwg','C:/two/page.dwg')])
    rows=document_inventory(app,interval=0)
    assert len(rows)==2 and rows[0]['identity']!=rows[1]['identity']


def test_default_list_drawings_uses_stable_inventory():
    from unittest.mock import patch
    from src.tools.project import list_drawings
    app=SimpleNamespace(HWND=7, Documents=[doc('same.dwg','C:/a/same.dwg'),doc('same.dwg','C:/b/same.dwg')])
    app.ActiveDocument=app.Documents[1]
    conn=MagicMock();conn.get_application.return_value=app
    with patch('src.tools.project._get_conn',return_value=conn):
        result=list_drawings()
    assert result['success'] and [d['active'] for d in result['drawings']]==[False,True]
    assert all(d['sheet_number']=='' for d in result['drawings'])
