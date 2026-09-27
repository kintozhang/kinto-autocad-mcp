import copy
import io
import pytest
from pypdf import PdfReader,PdfWriter
from pypdf.generic import DecodedStreamObject,NameObject
from src.autocad.pdf_navigation import add_navigation,verify,frame_bounds
from src.autocad.pdf_merge import fingerprint

def fixture():
    writer=PdfWriter();entries=[]
    for logical in ['102','300','405']:
        p=writer.add_blank_page(1191,842);s=DecodedStreamObject()
        s.set_data(b'70 48 m 1120 48 l 1120 780.375 l 70 780.375 l h S')
        p[NameObject('/Contents')]=writer._add_object(s)
        entries.append({'logical_page':logical,'navigation':{'schema_version':1,'links':[]}})
    entries[0]['navigation']['links']=[{'label':'300.1','target_page':'300','zone':1,'bounds_mm':[205,198,212,201]}]
    entries[1]['navigation']['links']=[{'label':'405','target_page':'405','zone':None,'bounds_mm':[401,12,407,15]}]
    return writer,entries

def test_logical_page_not_pdf_index_and_content_preserved():
    w,e=fixture();before=[fingerprint(p) for p in w.pages];expected=add_navigation(w,e)
    stream=io.BytesIO();w.write(stream);r=PdfReader(stream);verify(r,expected)
    assert [fingerprint(p) for p in r.pages]==before
    assert [v['target_pdf_page'] for v in expected['links']]==[2,3]
    assert expected['links'][0]['fit_type']=='/FitR'
    assert expected['links'][1]['fit_type']=='/Fit'
    assert expected['bookmarks']==['102','300','405']

@pytest.mark.parametrize('case',['missing','duplicate','partial','zone','bounds','schema','no_frame'])
def test_reject_unsafe_navigation(case):
    w,e=fixture()
    if case=='missing':e[0]['navigation']['links'][0]['target_page']='326'
    if case=='duplicate':e[1]['logical_page']='102'
    if case=='partial':e[1].pop('navigation')
    if case=='zone':e[0]['navigation']['links'][0]['zone']=10
    if case=='bounds':e[0]['navigation']['links'][0]['bounds_mm']=[0,0,500,600]
    if case=='schema':e[0]['navigation']['schema_version']=2
    if case=='no_frame':del w.pages[0]['/Contents']
    with pytest.raises(ValueError):add_navigation(w,e)

def test_no_navigation_keeps_non_trebi_exports():
    w,e=fixture();assert add_navigation(w,[{}, {}, {}])['status']=='not_requested'

def test_tampered_destination_fails_readback():
    w,e=fixture();expected=add_navigation(w,e);expected['links'][0]['target_pdf_page']=3
    stream=io.BytesIO();w.write(stream)
    with pytest.raises(ValueError,match='readback'):verify(PdfReader(stream),expected)


def test_navigation_restarts_read_only_snapshot_after_untyped_proxy():
    from types import SimpleNamespace
    from src.autocad.pdf_navigation import collect
    class Block:
        ObjectName='AcDbBlockReference';HasAttributes=True;Name='TITLE';Handle='AB';calls=0
        def GetAttributes(self):
            self.calls+=1
            if self.calls==1:raise AttributeError('GetAttributes.TagString')
            return [SimpleNamespace(TagString='NEXT',TextString='300',Invisible=False,GetBoundingBox=lambda:((401,12,0),(407,15,0)))]
    b=Block();result=collect(SimpleNamespace(ModelSpace=[b]),'TITLE')
    assert b.calls==2 and result['links'][0]['target_page']=='300'
