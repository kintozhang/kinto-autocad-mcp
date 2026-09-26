from unittest.mock import MagicMock, patch
import copy
import json
from pathlib import Path
import pytest
from src.tools import native_project as project
from scripts.verify_small_project import validate_reports


def test_existing_report_is_not_overwritten(tmp_path):
    out=tmp_path/"bom.csv";out.write_text("original",encoding="utf8")
    with patch.object(project,"get_connection") as connect:
        result=project.export_report("unused.wdp","bom",str(out))
    assert not result["success"] and out.read_text()=="original"
    connect.assert_not_called()


def test_invalid_report_type_never_connects(tmp_path):
    with patch.object(project,"get_connection") as connect:
        assert not project.export_report("unused.wdp","unknown",str(tmp_path/"new.csv"))["success"]
    connect.assert_not_called()


def test_wrong_project_is_rejected_before_report_generation(tmp_path):
    wdp=tmp_path/"requested.wdp";wdp.touch()
    conn=MagicMock()
    with patch.object(project,"state",return_value={"project":str(tmp_path/"other.wdp"),"drawings":[]}):
        with pytest.raises(project.BridgeError,match="does not match"):
            project.guard(conn,str(wdp))
    conn.get_active_document.assert_not_called()


def test_foreign_active_drawing_is_rejected(tmp_path):
    wdp=tmp_path/"requested.wdp";wdp.touch()
    conn=MagicMock();conn.get_active_document.return_value.FullName=str(tmp_path/"foreign.dwg")
    with patch.object(project,"state",return_value={"project":str(wdp),"drawings":[str(tmp_path/"member.dwg")]}):
        with pytest.raises(project.BridgeError,match="not a member"):
            project.guard(conn,str(wdp))


@pytest.mark.parametrize("fault",["missing_connection","wrong_terminal","extra_bom","wrong_quantity"])
def test_design_acceptance_detects_bad_native_reports(fault):
    spec=json.loads((Path(__file__).resolve().parents[1]/"examples/relay-demo/design.json").read_text())
    bom=[["",str(q),"1",cat,"KINTO_TEST"] for cat,q in spec["bom"].items()]
    connections=[]
    for number,ft,fp,tt,tp,fs,ts in spec["connections"]:
        connections.append([number,"",ft,fp,"",tt,tp,"","","","",fs,ts])
    reports={"bom":{"rows":bom},"components":{"rows":[["",t] for t in spec["component_tags"]]},"from_to":{"rows":connections}}
    validate_reports(reports,spec)
    if fault=="missing_connection": connections.pop()
    elif fault=="wrong_terminal": connections[1][6]="WRONG"
    elif fault=="extra_bom": bom.append(bom[0])
    else: bom[0][1]="99"
    with pytest.raises(AssertionError): validate_reports(reports,spec)


@pytest.mark.parametrize("kind,api", [("terminal_plan", "c:ace_termplan_r"), ("terminal_numbers", "c:wd_term_nums_rpt")])
def test_terminal_report_signature(kind, api):
    function, args = project.report_arguments(kind, "C:/test/result.csv")
    assert function == api
    assert args == [1, 1, None, None, None, "CSV", 0, "C:/test/result.csv", None]


def test_stale_document_project_context_is_rejected():
    with patch.object(project, "evaluate", return_value=["C:/new/project.wdp", ["C:/old/page.dwg"], "C:/old/project.wdp"]):
        with pytest.raises(project.BridgeError, match="context is stale"):
            project.state(MagicMock())
