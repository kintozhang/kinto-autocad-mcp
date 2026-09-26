import copy
import pytest
from src.autocad.trebi_component_tags import plan_tags
M={"schema_version":1,"entries":[{"id":p,"kind":"drawing","logical_page":p,"include_in_total":True} for p in ["54","112","326"]]}
def primary(identifier="coil",**kw):
    return {"id":identifier,"role":"primary","drawing_page":"112","owner_page":"112","family":"K",**kw}
def test_child_on_another_page_keeps_parent_tag():
    cs=[{"id":"contact","role":"child","drawing_page":"54","parent_id":"coil"},primary()]
    before=copy.deepcopy(cs);r=plan_tags(M,cs)
    assert [c["tag"] for c in r["components"]]==["-112K1","-112K1"] and cs==before

def test_reserved_tags_and_sequences_precede_automatic_allocation():
    cs=[primary('a'),primary('b',existing_tag='-112K1'),primary('c',sequence=2)]
    assert [c['tag'] for c in plan_tags(M,cs)['components']]==['-112K3','-112K1','-112K2']
    assert {c['id']:c['tag'] for c in plan_tags(M,cs)['components']}=={c['id']:c['tag'] for c in plan_tags(M,list(reversed(cs)))['components']}

def test_move_and_existing_exception_do_not_renumber():
    r=plan_tags(M,[primary(drawing_page='326',existing_tag='-112K7'),primary('old',existing_tag='-10K1')])
    assert [c['tag'] for c in r['components']]==['-112K7','-10K1']
    assert len(r['warnings'])==2

@pytest.mark.parametrize('tag',['-X15','-W102-1','-1Xm-4'])
def test_independent_tags_preserved(tag):
    assert plan_tags(M,[{'id':'device','role':'independent','drawing_page':'54','existing_tag':tag}])['components'][0]['tag']==tag

@pytest.mark.parametrize('cs',[
 [primary(),primary()],
 [primary('a',existing_tag='-112K1'),primary('b',existing_tag='-112K1')],
 [primary('a',sequence=1),primary('b',existing_tag='-112K1')],
 [primary(family='X')],[primary(owner_page='500')],[primary(drawing_page='500')],
 [primary(sequence=True)],[primary(sequence=0)],[primary(existing_tag='-112K1',sequence=2)],
 [{'id':'x','role':'independent','drawing_page':'54'}],
 [{'id':'x','role':'child','drawing_page':'54','parent_id':'missing'}],
 [primary(),{'id':'x','role':'child','drawing_page':'54','parent_id':'coil','existing_tag':'-54K1'}],
 [primary(location='CAB1')],
])
def test_conflicts_and_unsupported_policies_rejected(cs):
    with pytest.raises(ValueError):plan_tags(M,cs)
