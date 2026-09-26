"""Explicit project page manifest. Pure planning: no CAD or PDF mutations."""
import json
import re
from pathlib import Path
from src.autocad.trebi_rules import page_navigation, page_reference
GROUPS=Path(__file__).resolve().parents[2]/"profiles/trebi-page-groups.json"

def plan(manifest, groups=None):
    if manifest.get("schema_version")!=1:
        raise ValueError("Unsupported manifest version")
    entries=manifest.get("entries")
    if not isinstance(entries,list) or not entries:
        raise ValueError("Explicit nonempty entries required")
    groups=json.loads(GROUPS.read_text(encoding="utf8"))["groups"] if groups is None else groups
    group_ids=set();ranges=[]
    for group in groups:
        a,b=group["first"],group["last"]
        if type(a) is not int or type(b) is not int or a<0 or b<a or group["id"] in group_ids:
            raise ValueError("Invalid or duplicate page group")
        if any(a<=y and x<=b for x,y in ranges):raise ValueError("Overlapping page groups")
        group_ids.add(group["id"]);ranges.append((a,b))
    ids=set();pages=[];drawings=[];attachments=[]
    for entry in entries:
        identifier=entry.get("id")
        if not isinstance(identifier,str) or not identifier.strip() or identifier in ids:
            raise ValueError("Unique nonempty entry id required")
        ids.add(identifier)
        included=entry.get("include_in_total")
        if type(included) is not bool:raise ValueError("Explicit include_in_total boolean required")
        if entry.get("kind")=="attachment":
            if included or "logical_page" in entry:raise ValueError("Attachments cannot count as logical drawings")
            attachments.append(identifier);continue
        if entry.get("kind")!="drawing":raise ValueError("Unknown entry kind")
        page=entry.get("logical_page")
        if not isinstance(page,str) or not re.fullmatch(r"0|[1-9][0-9]*",page):
            raise ValueError("Explicit logical page string required")
        if page in pages:raise ValueError("Duplicate logical page")
        pages.append(page);drawings.append(entry)
    active=[e["logical_page"] for e in drawings if e["include_in_total"]]
    if not active:raise ValueError("At least one effective drawing required")
    result=[]
    for entry in drawings:
        page=entry["logical_page"]
        matched=next((g for g in groups if g["first"]<=int(page)<=g["last"]),None)
        result.append({"id":entry["id"],"logical_page":page,"include_in_total":entry["include_in_total"],
            "group":matched["id"] if matched else None,"classification":"configured" if matched else "pending",
            "title_fields":{**page_navigation(active,page),"OF":str(len(active))} if entry["include_in_total"] else None})
    return {"effective_drawing_count":len(active),"logical_pages":active,"drawings":result,"attachments":attachments}

def resolve_reference(manifest, value, *, context):
    project=plan(manifest);reference=page_reference(value,context=context)
    match=next((d for d in project["drawings"] if d["logical_page"]==reference["logical_page"] and d["include_in_total"]),None)
    if match is None:raise ValueError("Reference target is absent or excluded from effective drawings")
    return {**reference,"entry_id":match["id"]}
