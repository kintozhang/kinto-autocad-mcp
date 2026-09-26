import io
from pypdf import PdfWriter,PdfReader
from pypdf.generic import DictionaryObject,NameObject,TextStringObject,ArrayObject,NumberObject
from src.autocad.pdf_merge import remove_shx_annotations,fingerprint

def annotation(subtype,title):
    return DictionaryObject({NameObject('/Type'):NameObject('/Annot'),NameObject('/Subtype'):NameObject(subtype),NameObject('/T'):TextStringObject(title),NameObject('/Contents'):TextStringObject('9'),NameObject('/Rect'):ArrayObject([NumberObject(v) for v in [10,10,20,20]])})

def test_only_shx_notes_and_owned_popups_removed():
    w=PdfWriter();p=w.add_blank_page(1191,842);w.add_outline_item('PAGE 300',0)
    shx=w._add_object(annotation('/Square','AutoCAD SHX Text'))
    text=w._add_object(annotation('/Text','AutoCAD SHX Text'))
    popup=annotation('/Popup','');popup[NameObject('/Parent')]=shx
    user=w._add_object(annotation('/Square','Reviewer'))
    other=w._add_object(annotation('/Text','Other note'))
    user_popup=annotation('/Popup','');user_popup[NameObject('/Parent')]=user
    link=w._add_object(annotation('/Link','AutoCAD SHX Text'))
    p[NameObject('/Annots')]=ArrayObject([shx,text,w._add_object(popup),user,other,w._add_object(user_popup),link])
    before=fingerprint(p)
    assert remove_shx_annotations(p)==3
    assert remove_shx_annotations(p)==0
    assert fingerprint(p)==before
    out=io.BytesIO();w.write(out);r=PdfReader(out)
    assert [a.get_object()['/Subtype'] for a in r.pages[0]['/Annots']]==['/Square','/Text','/Popup','/Link']
    assert r.outline[0].title=='PAGE 300'

def test_empty_annotation_array_removed_without_touching_blank_page():
    w=PdfWriter();p=w.add_blank_page(1191,842)
    assert remove_shx_annotations(p)==0
    p[NameObject('/Annots')]=ArrayObject([w._add_object(annotation('/Square','AutoCAD SHX Text'))])
    assert remove_shx_annotations(p)==1 and '/Annots' not in p
