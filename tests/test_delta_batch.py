import copy
import hashlib
from unittest.mock import patch
import pytest
from src.tools.trebi_batch import plan, execute
from src.tools import delta_batch

@pytest.fixture
def spec(tmp_path,monkeypatch):
    asset=tmp_path/"HBB1_KINTO_R2_EC0902_TEST.dwg"
    asset.write_bytes(b"synthetic asset for parser tests, not CAD acceptance")
    monkeypatch.setattr(delta_batch,"ASSET_SHA256",hashlib.sha256(asset.read_bytes()).hexdigest())
    return {"schema_version":2,"recipe":"delta_r2_output_poc","purpose":"test_only","symbol_path":str(asset),
      "manifest":{"schema_version":1,"entries":[{"id":"p","kind":"drawing","logical_page":"405","include_in_total":True,"drawing_file":"test.dwg"}]}}

def test_default_batch_dispatch_keeps_identity_and_power_domains_separate(spec):
    p=plan(spec)
    assert not p["production_ready"] and not p["submitted"]
    assert len(p["components"])==9 and len(p["connections"])==8
    assert p["components"][0]["attributes"]["TAG1"]=="-405A1"
    assert p["pages"]["effective_drawing_count"]==1
    links={w["wire_number"]:w["wire_layer"] for w in p["connections"]}
    assert links["PWR0"]!=links["TEST0"]
    assert links["PWR24"]!=links["TEST24"]
    assert links["FG_TEST"] not in {links["PWR0"],links["TEST0"]}
    assert "O518" not in links and "Y00" not in links

@pytest.mark.parametrize("case",["production","tampered_asset","missing_asset","override_components","extra_page","bad_filename","wrong_recipe"])
def test_rejects_before_any_cad_contact(spec,case):
    if case=="production":spec["purpose"]="production"
    if case=="tampered_asset":__import__("pathlib").Path(spec["symbol_path"]).write_bytes(b"changed")
    if case=="missing_asset":__import__("pathlib").Path(spec["symbol_path"]).unlink()
    if case=="override_components":spec["components"]=[]
    if case=="extra_page":spec["manifest"]["entries"].append({"id":"extra","kind":"attachment","include_in_total":False})
    if case=="bad_filename":spec["manifest"]["entries"][0]["drawing_file"]="../other.dwg"
    if case=="wrong_recipe":spec["recipe"]="arbitrary"
    with patch("src.autocad.connection.get_connection") as conn:
        result=execute("C:/test.wdp",spec,"C:/test.dwg")
    assert result["status"]=="preflight_rejected" and not result["submitted"]
    conn.assert_not_called()

def test_wrong_native_pin_inventory_stops_before_wires():
    with pytest.raises(RuntimeError,match="terminal inventory"):
        delta_batch.verify_insert({"connection_points":[{"connection":"X2TERM73","terminal":"TB1:24V"}]*76})

def test_asset_becoming_unreadable_is_a_controlled_preflight_error(spec):
    from pathlib import Path
    with patch.object(Path,'read_bytes',side_effect=PermissionError('asset busy')):
        with pytest.raises(ValueError,match='Cannot read verified R2 asset'):
            plan(spec)
