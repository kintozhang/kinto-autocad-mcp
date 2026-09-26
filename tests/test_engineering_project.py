import pytest
from src.tools.engineering_project import plan


def spec(tmp_path):
    return {'schema_version':1,'name':'Demo','discipline':'mechanical','output_root':str(tmp_path),'pages':['1'],'purpose':'design_draft'}


def test_mechanical_plan_no_files_created(tmp_path):
    result=plan(spec(tmp_path));assert not (tmp_path/'Demo').exists()
    assert result['project_path'] is None and len(result['drawings'])==1


@pytest.mark.parametrize('field,value',[('name','../bad'),('name','CON'),('pages',['1','1']),('pages',[]),('purpose','production'),('discipline','unknown'),('output_root','relative')])
def test_invalid_plan_rejected(tmp_path,field,value):
    data=spec(tmp_path);data[field]=value
    with pytest.raises((ValueError,TypeError)):plan(data)


def test_existing_project_not_overwritten(tmp_path):
    (tmp_path/'Demo').mkdir()
    with pytest.raises(ValueError):plan(spec(tmp_path))


def test_electrical_requires_explicit_base(tmp_path):
    data=spec(tmp_path);data['discipline']='trebi_electrical'
    with pytest.raises(ValueError,match='base'):plan(data)


def test_creation_failure_stops_before_project_commands(tmp_path):
    from unittest.mock import MagicMock,patch
    from src.tools.engineering_project import execute
    conn=MagicMock();app=conn.get_application.return_value
    app.ActiveDocument.FullName=str(tmp_path/'original.dwg')
    with patch('src.autocad.connection.get_connection',return_value=conn), patch('src.autocad.com_runtime.create_document_from_template',side_effect=RuntimeError('uncertain Add')) as create, patch('src.autocad.lisp_bridge.evaluate') as evaluate:
        data=execute(spec(tmp_path))
    assert data['status']=='partial_or_unknown' and data['submitted']
    create.assert_called_once();evaluate.assert_not_called()
    assert data['steps'][0]['status']=='failed_or_unknown'
