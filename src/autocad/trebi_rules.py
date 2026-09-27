"""TREBI drawing conventions; never infer electrical connectivity from text labels."""
import json
import re
from pathlib import Path
PROFILE=Path(__file__).resolve().parents[2]/"profiles/trebi-electrical-a3.json"

def profile():
    return json.loads(PROFILE.read_text(encoding="utf8"))

def page_reference(value, *, context):
    if context not in {"wire_reference","component_reference","module_position"}:
        raise ValueError("Explicit reference context required")
    match=re.fullmatch(r"(0|[1-9][0-9]*)\.([0-9])",value)
    if not match:raise ValueError("Expected logical page.zone with zone 0..9")
    return {"logical_page":match[1],"zone":int(match[2]),"context":context}

def page_navigation(pages, current):
    if len(pages)!=len(set(pages)) or current not in pages:
        raise ValueError("Logical pages must be unique and current page present")
    if any(not re.fullmatch(r"0|[1-9][0-9]*",p) for p in pages):
        raise ValueError("Explicit logical page labels required")
    i=pages.index(current)
    return {"PAGE":current,"PREV":pages[i-1] if i else "-","NEXT":pages[i+1] if i+1<len(pages) else "-"}

def zone_at(x):
    left,_,right,_=profile()["header_bounds"]
    if not left<=x<=right:raise ValueError("Outside drawing frame")
    return min(9,int((x-left)/((right-left)/10)))

DRAFT_METADATA={"REV","CHANGES","REV_DATE","SIGNATURE","PLAN","ORDER","CUSTOMER","DESCRIPTION","PLANNER","DATE"}


def validate_fields(values, *, allow_draft_metadata=False):
    cfg=profile()
    if set(values)!={f["tag"] for f in cfg["fields"]}:raise ValueError("Exact declared title fields required")
    for field in cfg["fields"]:
        value=values[field["tag"]]
        if (not isinstance(value,str) or (not value and not (allow_draft_metadata and field["tag"] in DRAFT_METADATA))
                or len(value)>field["max_chars"] or any(ord(c)<32 for c in value)):
            raise ValueError("Invalid title field: "+field["tag"])
    for key in ("PAGE","OF","PREV","NEXT"):
        if not re.fullmatch(r"[0-9]+|-",values[key]):raise ValueError("Invalid page field")
    return cfg
