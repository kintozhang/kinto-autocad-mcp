"""Plan stable TREBI device tags before CAD insertion; flat project namespace."""
import re
from src.autocad.trebi_project_pages import plan as page_plan
PAGE_FAMILIES=frozenset("QFTKMABS")

def plan_tags(manifest, components):
    active=set(page_plan(manifest)["logical_pages"])
    if not isinstance(components,list):raise ValueError("Component list required")
    by_id={};tags={};used=set();warnings=[]
    def check_tag(value):
        if not isinstance(value,str) or not re.fullmatch(r"-[A-Za-z0-9][A-Za-z0-9_-]*",value):
            raise ValueError("Explicit simple device tag required")
        return value
    for c in components:
        identifier=c.get("id")
        if not isinstance(identifier,str) or not identifier.strip() or identifier in by_id:raise ValueError("Unique component id required")
        by_id[identifier]=c
        if c.get("drawing_page") not in active:raise ValueError("Component drawing page is not effective")
        if c.get("installation") or c.get("location"):raise ValueError("Multiple INST/LOC namespaces not yet supported")
        role=c.get("role")
        if role not in {"primary","child","independent"}:raise ValueError("Explicit component role required")
        if role=="child":
            if "sequence" in c or "owner_page" in c:raise ValueError("Child inherits parent identity")
            continue
        if role=="primary":
            if c.get("family") not in PAGE_FAMILIES:raise ValueError("Family requires an explicit independent tag policy")
            if c.get("owner_page") not in active:raise ValueError("Explicit effective owner page required")
            if "sequence" in c and (type(c["sequence"]) is not int or c["sequence"]<1):raise ValueError("Positive integer sequence required")
        elif "sequence" in c:raise ValueError("Independent devices cannot auto-number")
        if c.get("existing_tag") is not None:
            if "sequence" in c:raise ValueError("Existing tag cannot be combined with renumbering")
            tag=check_tag(c["existing_tag"])
            if tag.casefold() in used:raise ValueError("Duplicate physical device tag")
            used.add(tag.casefold());tags[identifier]=tag
        elif role=="independent":raise ValueError("Terminal strips, connectors and cables require explicit tags")
    # Reserve explicit sequences before assigning any automatic sequence.
    for identifier,c in by_id.items():
        if c["role"]=="primary" and identifier not in tags and "sequence" in c:
            tag=f'-{c["owner_page"]}{c["family"]}{c["sequence"]}'
            if tag.casefold() in used:raise ValueError("Requested sequence collides with an existing device")
            tags[identifier]=tag;used.add(tag.casefold())
    for identifier in sorted(by_id):
        c=by_id[identifier]
        if c["role"]=="primary" and identifier not in tags:
            prefix=f'-{c["owner_page"]}{c["family"]}';n=1
            while (prefix+str(n)).casefold() in used:n+=1
            tags[identifier]=prefix+str(n);used.add(tags[identifier].casefold())
    for identifier,c in by_id.items():
        if c["role"]=="child":
            parent=by_id.get(c.get("parent_id"))
            if parent is None or parent["role"]!="primary":raise ValueError("Child requires one primary parent id")
            tag=tags[parent["id"]]
            if c.get("existing_tag") not in (None,tag):raise ValueError("Child tag disagrees with its parent")
            tags[identifier]=tag
        elif c["role"]=="primary":
            if c["drawing_page"]!=c["owner_page"]:warnings.append({"id":identifier,"reason":"drawing_page_differs_from_owner; owner_identity_retained"})
            if c.get("existing_tag") and not re.fullmatch(re.escape('-'+c["owner_page"]+c["family"])+r'[1-9][0-9]*',tags[identifier]):
                warnings.append({"id":identifier,"reason":"existing_tag_outside_page_convention; preserved_for_review"})
    return {"components":[{"id":c["id"],"role":c["role"],"drawing_page":c["drawing_page"],"tag":tags[c["id"]],
                           "origin":"parent" if c["role"]=="child" else "preserved" if c.get("existing_tag") else "generated"} for c in components],
            "warnings":warnings,"scope":"flat_project_namespace; independent_tags_are_device_ids_not_terminal_pins"}
