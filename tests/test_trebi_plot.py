from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
import pytest
from src.autocad.project_plot import trebi_page, trebi_project
from src.autocad.trebi_rules import profile
from src.autocad.trebi_native_grid import settings
from src.tools import native_pdf


def fixture(page='54',prev='-',next='112'):
    fields={f['tag']:'TEST' for f in profile()['fields']}
    fields.update(PAGE=page,OF='2',PREV=prev,NEXT=next)
    title=SimpleNamespace(ObjectName='AcDbBlockReference',Name=profile()['block_name'],InsertionPoint=(0.,0.,0.),Rotation=0.,XScaleFactor=1.,YScaleFactor=1.,ZScaleFactor=1.,attrs=fields)
    wd=SimpleNamespace(ObjectName='AcDbBlockReference',Name='WD_M',attrs=settings(page))
    return SimpleNamespace(ModelSpace=[title,wd])


def test_logical_page_order_survives_pdf_order():
    pages=[Path('a.dwg'),Path('b.dwg')];docs=[fixture(),fixture('112','54','-')]
    with patch('src.autocad.utils.get_block_attributes',side_effect=lambda e:e.attrs):
        result=trebi_project(dict(zip(pages,docs)),pages)
    assert [p['logical_page'] for p in result]==['54','112']
    assert result[1]['title_fields']['OF']=='2'

@pytest.mark.parametrize('bad',['of','sheet','grid','navigation','duplicate','scale','origin','rotation','missing'])
def test_invalid_source_identity_rejected(bad):
    pages=[Path('a.dwg'),Path('b.dwg')];docs=[fixture(),fixture('112','54','-')]
    title,wd=docs[1].ModelSpace
    if bad=='of':title.attrs['OF']='112'
    if bad=='sheet':wd.attrs['SHEET']='2'
    if bad=='grid':wd.attrs['DISTH']='10'
    if bad=='navigation':title.attrs['PREV']='111'
    if bad=='duplicate':docs[1]=fixture()
    if bad=='scale':title.XScaleFactor=2
    if bad=='origin':title.InsertionPoint=(1,0,0)
    if bad=='rotation':title.Rotation=1
    if bad=='missing':docs[1].ModelSpace.pop()
    with patch('src.autocad.utils.get_block_attributes',side_effect=lambda e:e.attrs):
        with pytest.raises(ValueError):trebi_project(dict(zip(pages,docs)),pages)


def test_trebi_preflight_failure_never_creates_plot_copy(tmp_path):
    from unittest.mock import MagicMock
    project=tmp_path/'test.wdp';project.touch();page=tmp_path/'a.dwg';page.touch()
    conn=MagicMock();conn.get_active_document.return_value.FullName=str(page)
    with patch.object(native_pdf,'get_connection',return_value=conn), patch.object(native_pdf,'guard',return_value={'drawings':[str(page)]}), patch.object(native_pdf,'project_pages',return_value=[page]), patch.object(native_pdf,'saved_members',return_value={page:fixture()}), patch.object(native_pdf,'trebi_project',side_effect=ValueError('wrong logical page')), patch.object(native_pdf,'plot_snapshot') as plot:
        result=native_pdf.export_pdf(str(project),str(tmp_path/'out.pdf'),'synthetic_trebi_a3')
    assert not result['success'] and result['operation_directory'] is None
    plot.assert_not_called()


def test_explicit_synthetic_draft_preserves_blank_metadata_without_forging_values():
    from src.autocad.trebi_rules import DRAFT_METADATA
    doc=fixture()
    for field in DRAFT_METADATA:doc.ModelSpace[0].attrs[field]=''
    with patch('src.autocad.utils.get_block_attributes',side_effect=lambda e:e.attrs):
        with pytest.raises(ValueError):trebi_page(doc,2)
        result=trebi_page(doc,2,allow_draft_metadata=True)
    assert set(result['draft_metadata_pending'])==DRAFT_METADATA
    assert result['title_fields']['SIGNATURE']==''

@pytest.mark.parametrize('field',['BRAND','PAGE','OF','PREV','NEXT'])
def test_draft_never_allows_blank_identity_or_navigation(field):
    doc=fixture();doc.ModelSpace[0].attrs[field]=''
    with patch('src.autocad.utils.get_block_attributes',side_effect=lambda e:e.attrs):
        with pytest.raises(ValueError):trebi_page(doc,2,allow_draft_metadata=True)
