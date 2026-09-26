import json
from pathlib import Path
import pytest
from scripts.verify_branch_project import validate

def evidence():
    return json.loads((Path(__file__).parent/"fixtures/branch-project-evidence.json").read_text(encoding="utf8"))

def test_actual_synthetic_report_evidence():
    assert validate(evidence())["status"]=="PASS"

@pytest.mark.parametrize("fault",["blank_branch_number","wrong_bom","disconnected_graph","wrong_plan_remote","duplicate_plan","duplicate_handle","missing_saved_endpoint"])
def test_independent_validator_rejects_corrupt_evidence(fault):
    r=evidence();v=r["reports"]
    if fault=="blank_branch_number":v["terminal_numbers"]["rows"][2][2]=""
    elif fault=="wrong_bom":v["bom"]["rows"][0][1]="5"
    elif fault=="disconnected_graph":
        for row,(a,b) in zip(v["from_to"]["rows"],[("1","2"),("2","3"),("3","1")]):row[3]=a;row[6]=b
    elif fault=="wrong_plan_remote":v["terminal_plan"]["rows"][0][22]="99"
    elif fault=="duplicate_plan":v["terminal_plan"]["rows"].append(v["terminal_plan"]["rows"][0])
    elif fault=="duplicate_handle":v["terminal_numbers"]["rows"][1][27]=v["terminal_numbers"]["rows"][0][27]
    else:r["after"][0]["connections"].pop()
    with pytest.raises(AssertionError):validate(r)
