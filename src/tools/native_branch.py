"""Straight terminal-to-wire T branch; native Electrical wire insertion and netlist."""
from src.tools.native_electrical import connection,entity,_points,network,inspect_wire,failure,existing_connection
from src.autocad.lisp_bridge import evaluate,literal,BridgeError,_LOCK


def point_on_segment(point, start, end):
    delta=[b-a for a,b in zip(start,end)];length=sum(v*v for v in delta)
    if not length:return False
    t=sum((p-a)*v for p,a,v in zip(point,start,delta))/length
    return -1e-9 <= t <= 1+1e-9 and sum((p-(a+t*v))**2 for p,a,v in zip(point,start,delta)) < 1e-12


def number_refresh_function(attributes, number):
    matches=[api for tag,api in [("WIRENO","c:wd_putwn"),("WIRENOF","c:wd_putwnf")] if attributes.get(tag)==number]
    if len(matches)!=1:raise BridgeError("Cannot identify the existing normal/fixed wire number")
    return matches[0]


def strict_attributes(obj):
    return {a.TagString.upper():a.TextString for a in obj.GetAttributes()}


def verify_pin_numbers(doc, nodes, number):
    if number is None:return
    for handle,tag in nodes:
        if strict_attributes(doc.HandleToObject(handle)).get(tag)!=number:
            raise BridgeError("Connected pin wire-number cache is stale: "+handle+"/"+tag+"; refresh the existing number before retry")


def branch(terminal_handle, connection_name, wire_handle, x, y):
    handles=[]
    try:
        with _LOCK:
            entity(terminal_handle);entity(wire_handle);literal([x,y,0])
            conn,doc=connection();drawing=doc.FullName
            target=inspect_wire(wire_handle)
            if not target.get("success"):raise BridgeError(str(target))
            tap=[x,y,0]
            if not point_on_segment(tap,target["start"],target["end"]):
                raise ValueError("Tap must lie on the selected wire segment")
            points=[p for p in _points(doc.HandleToObject(terminal_handle)) if p["connection"]==connection_name]
            if len(points)!=1:raise ValueError("Connection point not found")
            start=points[0]["position"];source=(terminal_handle.upper(),connection_name)
            previous={(h.upper(),tag) for h,tag in target["connections"]}
            if source in previous:
                verify_pin_numbers(doc,previous,target["wire_number"])
                return {"success":True,"status":"already_connected","changed":False,"created_wire_handles":[],"connections":target["connections"]}
            if not previous:raise ValueError("Selected wire must have an existing component network")
            if start==tap or (start[0]!=x and start[1]!=y):raise ValueError("Only distinct aligned source/tap points are supported")
            refresh_api = None
            if target["wire_number"] is not None:
                refresh_api=number_refresh_function(strict_attributes(doc.HandleToObject(target["number_block_handle"])),target["wire_number"])
            layers=evaluate(conn,"(c:ace_get_wiretype_list nil)") or []
            if existing_connection(conn,doc,start,{source},layers):
                raise ValueError("Source connection is already wired; inspect before merging networks")
            if conn.get_active_document().FullName!=drawing:raise BridgeError("Target drawing changed")
            handles=evaluate(conn,"(c:ace_insert_wire "+literal([start,tap,target["wire_layer"],0])+")") or []
            if not handles:raise BridgeError("No branch wire returned")
            expected=previous|{source};checks=[]
            for h in handles:
                check=inspect_wire(h);checks.append(check)
                if not check.get("success") or {(a.upper(),b) for a,b in check["connections"]} != expected:
                    raise BridgeError("Native branch network differs from requested junction")
                if target["wire_number"] and check["wire_number"]!=target["wire_number"]:
                    raise BridgeError("Branch wire number was not inherited")
            if refresh_api:
                # Inheriting the network number alone leaves new X?TERMxx caches blank.
                evaluate(conn,"(progn ("+refresh_api+" "+entity(handles[0])+" "+literal(target["wire_number"])+") T)")
                verify_pin_numbers(doc,expected,target["wire_number"])
                updated=inspect_wire(handles[0])
                if not updated.get("success") or updated["wire_number"]!=target["wire_number"]:
                    raise BridgeError("Number refresh readback failed")
                if number_refresh_function(strict_attributes(doc.HandleToObject(updated["number_block_handle"])),target["wire_number"])!=refresh_api:
                    raise BridgeError("Normal/fixed wire-number kind changed")
            return {"success":True,"status":"native_branch_verified","changed":True,"wire_handles":handles,
                    "connections":checks[0]["connections"],"wire_number":checks[0]["wire_number"],"tap":tap,
                    "number_refresh_api":refresh_api,"pin_number_attributes_verified":refresh_api is not None}
    except Exception as exc:return failure(exc,created_wire_handles=handles)
