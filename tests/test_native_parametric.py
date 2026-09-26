from unittest.mock import patch
import pytest
from src.tools.native_parametric import connector_params,insert

@pytest.mark.parametrize('pins',[[],['1','1'],['bad,2'],['a\n'],[1],['x']*9,None])
def test_invalid_pins_do_not_contact_cad(pins):
    with patch('src.tools.native_parametric.get_connection') as conn:
        assert not insert('connector','a','b',1,2,'test_only',pins)['success']
    conn.assert_not_called()

def test_params_preserve_pin_order_and_no_dialog():
    p=connector_params(['4','6','12'])
    assert p[8]==1 and p[15:17]==[3,'4,6,12']

@pytest.mark.parametrize('kind',['connector','plc_fixture'])
def test_production_rejected_before_cad(kind):
    with patch('src.tools.native_parametric.get_connection') as conn:
        d=insert(kind,'a','b',1,2,'production',['1'])
        assert not d['success'] and not d['submitted']
    conn.assert_not_called()
