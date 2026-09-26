import copy
from unittest.mock import MagicMock,patch
import pytest
from src.autocad.trebi_title_mapping import binding,apply,WDT

def manifest():
    return {"schema_version":1,"entries":[{"id":p,"kind":"drawing","logical_page":p,"include_in_total":True,"drawing_file":p+'.dwg'} for p in ['54','112']]}

def test_binding_uses_logical_page_and_effective_count(tmp_path):
    bound,fields=binding(manifest(),tmp_path/'test.wdp',tmp_path/'112.dwg')
    assert len(bound)==2
    assert fields=={'PAGE':'112','OF':'2','PREV':'54','NEXT':'-'}

@pytest.mark.parametrize('filename',['../outside.dwg','C:/elsewhere.dwg','54.pdf','54.dwg'])
def test_invalid_or_duplicate_binding_rejected(tmp_path,filename):
    m=manifest();m['entries'][1]['drawing_file']=filename
    with pytest.raises(ValueError):binding(m,tmp_path/'test.wdp',tmp_path/'112.dwg')

def test_wrong_effective_count_rejected_without_cad(tmp_path):
    wdp=tmp_path/'test.wdp';wdp.write_text('*[20]112\n',encoding='utf8');wdp.with_suffix('.wdt').write_text(WDT.read_text(encoding='utf8'),encoding='utf8')
    conn=MagicMock()
    with patch('src.autocad.trebi_title_mapping.evaluate') as execute:
        with pytest.raises(ValueError,match='effective drawing count'):apply(conn,wdp,manifest(),tmp_path/'112.dwg')
        execute.assert_not_called()
    conn.get_active_document.assert_not_called()

def test_foreign_wdt_rejected_before_cad(tmp_path):
    wdp=tmp_path/'test.wdp';wdp.with_suffix('.wdt').write_text('BLOCK = OTHER',encoding='utf8')
    with patch('src.autocad.trebi_title_mapping.evaluate') as execute:
        with pytest.raises(ValueError,match='WDT'):apply(MagicMock(),wdp,manifest(),tmp_path/'112.dwg')
        execute.assert_not_called()

def test_extra_wdp_drawing_rejected_before_write(tmp_path):
    wdp=tmp_path/'test.wdp';wdp.write_text('*[20]2\n',encoding='utf8');wdp.with_suffix('.wdt').write_text(WDT.read_text(encoding='utf8'),encoding='utf8')
    with patch('src.autocad.trebi_title_mapping.guard',return_value={'drawings':[str(tmp_path/'54.dwg'),str(tmp_path/'112.dwg'),str(tmp_path/'extra.dwg')]}), patch('src.autocad.trebi_title_mapping.evaluate') as execute:
        with pytest.raises(ValueError,match='membership'):apply(MagicMock(),wdp,manifest(),tmp_path/'112.dwg')
        execute.assert_not_called()


@pytest.mark.parametrize('names',[['112.dwg','54.dwg'],['54.dwg','112.dwg','112.dwg']])
def test_wdp_order_and_duplicate_drawings_rejected(tmp_path,names):
    wdp=tmp_path/'test.wdp';wdp.write_text('*[20]2\n',encoding='utf8');wdp.with_suffix('.wdt').write_text(WDT.read_text(encoding='utf8'),encoding='utf8')
    with patch('src.autocad.trebi_title_mapping.guard',return_value={'drawings':[str(tmp_path/n) for n in names]}), patch('src.autocad.trebi_title_mapping.evaluate') as execute:
        with pytest.raises(ValueError,match='membership or order'):apply(MagicMock(),wdp,manifest(),tmp_path/'112.dwg')
        execute.assert_not_called()
