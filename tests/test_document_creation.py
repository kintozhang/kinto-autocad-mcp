from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pytest
from src.autocad.com_runtime import create_document_from_template


def setup(tmp_path, fail=False):
    template=tmp_path/'template.dwt';template.write_bytes(b'template')
    target=tmp_path/'new.dwg'
    doc=MagicMock();doc.Name='Drawing2';doc.Saved=True;doc.GetVariable.return_value=0
    app=MagicMock();app.Documents.__iter__.side_effect=lambda:iter([] if not app.Documents.Add.called else [doc])
    app.ActiveDocument=doc;app.GetAcadState.return_value.IsQuiescent=True
    if fail:doc.SaveAs.side_effect=RuntimeError('unknown write outcome')
    else:doc.SaveAs.side_effect=lambda p,v:Path(p).write_bytes(b'dwg')
    return app,doc,template,target


def test_ignore_untyped_add_return_and_save_once(tmp_path):
    app,doc,template,target=setup(tmp_path)
    app.Documents.Add.return_value=object()
    with patch('src.autocad.com_runtime.wait_for_document',return_value=doc):
        assert create_document_from_template(app,template,target,interval=0)==doc
    app.Documents.Add.assert_called_once();doc.SaveAs.assert_called_once_with(str(target),64)


def test_save_exception_never_replayed(tmp_path):
    app,doc,template,target=setup(tmp_path,True)
    with pytest.raises(RuntimeError,match='unknown'):
        create_document_from_template(app,template,target,interval=0)
    app.Documents.Add.assert_called_once();doc.SaveAs.assert_called_once()


def test_existing_target_does_not_create(tmp_path):
    app,doc,template,target=setup(tmp_path);target.write_bytes(b'original')
    with pytest.raises(ValueError):create_document_from_template(app,template,target)
    app.Documents.Add.assert_not_called();assert target.read_bytes()==b'original'


def test_multiple_new_documents_never_saved(tmp_path):
    app,doc,template,target=setup(tmp_path)
    app.Documents.__iter__.side_effect=lambda:iter([] if not app.Documents.Add.called else [doc,SimpleNamespace(Name='Drawing3')])
    with pytest.raises(RuntimeError,match='Multiple'):
        create_document_from_template(app,template,target,interval=0)
    doc.SaveAs.assert_not_called()



def test_transient_collection_metadata_retries_reads_only(tmp_path):
    app,doc,template,target=setup(tmp_path)
    remaining=[True]
    def documents():
        if not app.Documents.Add.called:return iter([])
        if remaining:
            remaining.pop();raise TypeError('This object does not support enumeration')
        return iter([doc])
    app.Documents.__iter__.side_effect=documents
    with patch('src.autocad.com_runtime.wait_for_document',return_value=doc):
        create_document_from_template(app,template,target,interval=0)
    app.Documents.Add.assert_called_once();doc.SaveAs.assert_called_once()
