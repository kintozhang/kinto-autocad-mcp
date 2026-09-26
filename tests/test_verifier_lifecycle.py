from unittest.mock import MagicMock,patch
import pytest
from scripts.verify_pdf_project import lookup_saved_close


def test_close_lookup_refreshes_metadata_without_repeating_write(tmp_path):
    close=MagicMock()
    class Document:
        FullName=str(tmp_path/'test.dwg')
        Saved=True
        reads=0
        @property
        def Close(self):
            self.reads+=1
            if self.reads==1:raise AttributeError('Close')
            return close
    doc=Document();app=MagicMock();app.Documents.Count=1;app.Documents.Item.return_value=doc
    with patch('scripts.verify_pdf_project.time.sleep'):
        lookup_saved_close(app,doc.FullName)(False)
    close.assert_called_once_with(False)
    assert doc.reads==2


def test_close_lookup_refuses_unsaved(tmp_path):
    doc=MagicMock();doc.FullName=str(tmp_path/'test.dwg');doc.Saved=False
    app=MagicMock();app.Documents.Count=1;app.Documents.Item.return_value=doc
    with pytest.raises(ValueError,match='unsaved'):
        lookup_saved_close(app,doc.FullName)
    doc.Close.assert_not_called()


def test_open_metadata_retry_never_repeats_invocation():
    from src.autocad.com_runtime import lookup_document_open
    method=MagicMock()
    class Documents:
        reads=0
        @property
        def Open(self):
            self.reads+=1
            if self.reads==1:raise AttributeError("Open")
            return method
    app=MagicMock();app.Documents=Documents()
    with patch("src.autocad.com_runtime.time.sleep"):
        lookup_document_open(app)("test.dwg")
    assert app.Documents.reads==2
    method.assert_called_once_with("test.dwg")


def test_open_invocation_failure_is_not_retried():
    from src.autocad.com_runtime import lookup_document_open
    app=MagicMock();app.Documents.Open.side_effect=AttributeError("inside actual Open")
    with pytest.raises(AttributeError):lookup_document_open(app)("test.dwg")
    app.Documents.Open.assert_called_once_with("test.dwg")
