from unittest.mock import MagicMock, PropertyMock, patch
from pathlib import Path
import pytest
from src.autocad.com_runtime import read_call, wait_for_document, ComBusyError
from src.autocad.connection import AutoCADConnection, AutoCADBusyError


class RpcError(Exception):
    def __init__(self, code):
        self.hresult=code
        super().__init__(code)


@pytest.mark.parametrize('code',[-2147418111,0x8001010A,0x8001010B])
def test_busy_read_recovers(code):
    read=MagicMock(side_effect=[RpcError(code),42]);events=[]
    assert read_call(read,interval=0,events=events)==42
    assert events[0]['retries']==1


def test_busy_exhausted_bounded():
    read=MagicMock(side_effect=RpcError(-2147418111))
    with pytest.raises(ComBusyError):read_call(read,attempts=3,interval=0)
    assert read.call_count==3


def test_unknown_error_not_retried():
    read=MagicMock(side_effect=AttributeError('missing member'))
    with pytest.raises(AttributeError):read_call(read,interval=0)
    read.assert_called_once()


def test_busy_probe_preserves_connection():
    conn=AutoCADConnection();app=MagicMock();conn._app=app
    with patch.object(type(app),'Name',new_callable=PropertyMock,create=True,side_effect=RpcError(-2147418111)),patch('src.autocad.com_runtime.time.sleep'):
        with pytest.raises(AutoCADBusyError):conn.is_connected()
    assert conn._app is app


def test_disconnected_probe_clears_connection():
    conn=AutoCADConnection();app=MagicMock();conn._app=app
    with patch.object(type(app),'Name',new_callable=PropertyMock,create=True,side_effect=RpcError(0x80010108)):
        assert not conn.is_connected()
    assert conn._app is None


def test_write_is_submitted_only_once():
    conn=AutoCADConnection();doc=MagicMock();doc.SendCommand.side_effect=RpcError(-2147418111)
    with patch.object(conn,'ensure_connected'),patch.object(conn,'get_active_document',return_value=doc):
        with pytest.raises(RuntimeError):conn.send_command('TEST')
    doc.SendCommand.assert_called_once()


def test_readiness_rejects_target_change():
    app=MagicMock();app.ActiveDocument.FullName=str(Path('wrong.dwg').resolve())
    with pytest.raises(ValueError,match='changed'):wait_for_document(app,Path('expected.dwg'))


def test_readiness_times_out_without_write():
    app=MagicMock();app.ActiveDocument.FullName=str(Path('expected.dwg').resolve())
    app.GetAcadState.return_value.IsQuiescent=False
    with pytest.raises(ComBusyError):wait_for_document(app,Path('expected.dwg'),timeout=0)
    app.ActiveDocument.SendCommand.assert_not_called()


def test_readiness_recovers_transient_document_metadata():
    class Document:
        def GetVariable(self, name):return 0
    app=MagicMock();doc=Document();app.ActiveDocument=doc
    path=str(Path('expected.dwg').resolve())
    app.GetAcadState.return_value.IsQuiescent=True
    with patch.object(type(doc),'FullName',new_callable=PropertyMock,create=True,side_effect=[AttributeError('untyped document'),path,path]),patch('src.autocad.com_runtime.time.sleep'):
        assert wait_for_document(app,path) is doc


def test_busy_singleton_does_not_reattach():
    from src.autocad import connection
    conn=AutoCADConnection();conn._app=MagicMock()
    with patch.object(connection,'_connection_instance',conn),patch.object(conn,'is_connected',side_effect=AutoCADBusyError('busy')),patch.object(conn,'connect') as connect:
        with pytest.raises(AutoCADBusyError):connection.get_connection()
    connect.assert_not_called()


def test_document_name_exhaustion_reports_actionable_read_only_diagnostic():
    from src.autocad.com_runtime import document_full_name
    class App:
        calls=0
        @property
        def ActiveDocument(self):
            self.calls+=1
            raise AttributeError('<unknown>.FullName')
    app=App()
    with pytest.raises(ComBusyError,match='active-document metadata unavailable') as error:
        document_full_name(app,attempts=3,interval=0)
    assert app.calls==3
    assert isinstance(error.value.__cause__,AttributeError)
