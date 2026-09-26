"""Electrical 2026 operations based on the installed ACE_API.chm."""
from __future__ import annotations
import re
from src.autocad.connection import get_connection
from src.autocad.lisp_bridge import evaluate, literal, BridgeError
from src.autocad.utils import get_block_attributes

HANDLE = re.compile(r"^[0-9A-Fa-f]+$")
CONNECTION = re.compile(r"^X[01248]TERM([0-9]{2})$")


def connection():
    conn = get_connection()
    doc = conn.get_active_document()
    if not any(o.ObjectName == "AcDbBlockReference" and o.Name.upper() == "WD_M"
               for o in doc.ModelSpace):
        raise BridgeError("Drawing needs a WD_M insert from a verified Electrical template")
    return conn, doc


def entity(handle):
    if not HANDLE.fullmatch(handle):
        raise ValueError("Invalid entity handle")
    return "(handent " + literal(handle) + ")"


def failure(exc, **details):
    return {"success": False, "status": "unverified", "error": str(exc),
            "retry_safe": False, **details}


def insert_symbol(symbol_name, x, y, rotation=0, attributes=None):
    created = None
    try:
        requested = attributes or {}
        literal([x, y, 0])
        for key, value in requested.items():
            if not re.fullmatch(r"[A-Za-z0-9_]+", key) or not isinstance(value, str):
                raise ValueError("Attributes require literal names and string values")
            literal(value)
        if rotation != 0:
            raise ValueError("Use the correct horizontal/vertical library symbol; rotation is not supported yet")
        conn, doc = connection()
        before = {o.Handle for o in doc.ModelSpace}
        # ACE_API 2026: bit 4 suppresses auto-tag generation. Otherwise an explicit
        # TAG1 can disagree with the automatically generated VIA_WD_BASETAG.
        options = 6 if any(k.upper() in {"TAG1", "TAGSTRIP"} for k in requested) else 2
        handle = evaluate(conn, "(c:wd_insym2 " + literal(symbol_name.replace("\\", "/")) +
                          " " + literal([x,y,0]) + " 1.0 " + str(options) + ")")
        if not isinstance(handle,str) or handle in before:
            raise BridgeError("Native insertion did not return a new entity handle")
        created = handle
        obj = doc.HandleToObject(handle)
        if obj.ObjectName != "AcDbBlockReference":
            raise BridgeError("Native insertion returned a non-block")
        for key,value in requested.items():
            updated = evaluate(conn, "(c:wd_modattrval " + entity(handle) + " " +
                               literal(key.upper()) + " " + literal(value) + " nil)")
            if updated != 1:
                raise BridgeError("Attribute not updated: " + key)
        actual = get_block_attributes(obj)
        if any(actual.get(k.upper()) != v for k,v in requested.items()):
            raise BridgeError("Attribute readback mismatch")
        return {"success": True, "status":"native_insert_verified", "handle":handle,
                "block":obj.Name, "position":list(obj.InsertionPoint), "attributes":actual,
                "connection_points":_points(obj), "api":"c:wd_insym2"}
    except Exception as exc:
        return failure(exc, created_handle=created)


def _points(obj):
    attrs = get_block_attributes(obj)
    points = []
    for attr in obj.GetAttributes():
        tag = attr.TagString.upper()
        match = CONNECTION.fullmatch(tag)
        if match:
            points.append({"connection":tag, "position":list(attr.InsertionPoint),
                           "terminal":attrs.get("TERM"+match.group(1), "")})
    return points


def get_connections(handle):
    try:
        entity(handle)
        _, doc = connection()
        obj = doc.HandleToObject(handle)
        if obj.ObjectName != "AcDbBlockReference":
            raise ValueError("Expected a component block")
        return {"success":True,"handle":handle,"connection_points":_points(obj)}
    except Exception as exc:
        return failure(exc)


def network(conn, wire_handle):
    # nth 9 = component connection list, per c:wd_get_wire_netlst.
    expr = ("(mapcar '(lambda (i) (list (cdr (assoc 5 (entget (car i)))) "
            "(cdr (assoc 2 (entget (cadr i)))))) "
            "(nth 9 (c:wd_get_wire_netlst " + entity(wire_handle) + " 1)))")
    return evaluate(conn,expr) or []


def existing_connection(conn, doc, start, expected, layers):
    """Inspect only native wires meeting this exact component connection point."""
    for obj in doc.ModelSpace:
        if obj.ObjectName != "AcDbLine" or obj.Layer not in layers:
            continue
        if not any(sum((a-b)**2 for a,b in zip(start,p)) < 1e-12 for p in [obj.StartPoint,obj.EndPoint]):
            continue
        nodes = network(conn,obj.Handle)
        if expected <= {(h.upper(),tag) for h,tag in nodes}:
            return {"wire_handles":[obj.Handle],"connections":nodes,"wire_layer":obj.Layer}
    return None


def connect_terminals(from_handle, from_connection, to_handle, to_connection, wire_layer="MCP_WIRE"):
    handles = []
    try:
        if not wire_layer.strip():
            raise ValueError("Wire layer cannot be empty")
        literal(wire_layer)
        conn,doc = connection()
        def point(handle, tag):
            entity(handle)
            matches = [p for p in _points(doc.HandleToObject(handle)) if p["connection"]==tag]
            if len(matches)!=1:
                raise ValueError("Connection attribute not found: "+tag)
            return matches[0]["position"]
        start,end=point(from_handle,from_connection),point(to_handle,to_connection)
        if start==end:
            raise ValueError("Connections must be distinct")
        layers=evaluate(conn,"(c:ace_get_wiretype_list nil)") or []
        expected={(from_handle.upper(),from_connection),(to_handle.upper(),to_connection)}
        existing = existing_connection(conn,doc,start,expected,layers)
        if existing:
            if existing["wire_layer"] != wire_layer:
                raise BridgeError("Requested terminals are already connected on a different wire layer")
            return {"success":True,"status":"already_connected","changed":False,
                    "created_wire_handles":[],"start":start,"end":end,**existing}
        if wire_layer not in layers:
            result=evaluate(conn,"(c:ace_new_wiretype "+literal(wire_layer)+" nil nil)")
            if result!=wire_layer:
                raise BridgeError("Native wire type creation failed")
        # Native auto-path mode can add a self-loop through an aligned terminal.
        # Option 0 passed the controlled 2026 comparison; retain routing for bends.
        options = 0 if start[0] == end[0] or start[1] == end[1] else 4
        route_start, route_end = start, end
        reversed_route = False
        if options == 4:
            from_attrs = get_block_attributes(doc.HandleToObject(from_handle))
            to_attrs = get_block_attributes(doc.HandleToObject(to_handle))
            # 2026 can append a terminal self-loop when auto-routing ends there.
            # The controlled offset fixture passed when routed from the terminal.
            if to_attrs.get("TAGSTRIP") and not from_attrs.get("TAGSTRIP"):
                route_start, route_end = end, start
                reversed_route = True
        handles=evaluate(conn,"(c:ace_insert_wire (list "+literal(route_start)+" "+literal(route_end)+" "+
                         literal(wire_layer)+" " + str(options) + "))")
        if not handles:
            raise BridgeError("No wire handles returned")
        for handle in handles:
            obj=doc.HandleToObject(handle)
            if obj.ObjectName!="AcDbLine" or obj.Layer!=wire_layer:
                raise BridgeError("Wire object readback mismatch")
        networks = [network(conn, handle) for handle in handles]
        nodes = networks[0]
        expected={(from_handle.upper(),from_connection),(to_handle.upper(),to_connection)}
        actual={(h.upper(),tag) for h,tag in nodes}
        if any(not expected <= {(h.upper(), tag) for h, tag in segment} for segment in networks):
            raise BridgeError("A returned wire segment does not connect both requested terminals; inspect created_wire_handles before retry")
        if not expected<=actual:
            raise BridgeError("Native netlist did not confirm both requested terminals; inspect before retry")
        return {"success":True,"status":"native_network_verified","wire_handles":handles,
                "connections":nodes,"start":start,"end":end,"wire_layer":wire_layer,
                "native_options":options,"native_route_reversed":reversed_route}
    except Exception as exc:
        return failure(exc, created_wire_handles=handles)


def set_number(wire_handle, number):
    try:
        if not number.strip():
            raise ValueError("Wire number cannot be empty")
        conn,doc=connection()
        if doc.HandleToObject(wire_handle).ObjectName!="AcDbLine":
            raise ValueError("Expected a wire LINE")
        wire=entity(wire_handle)
        literal(number)
        layers = evaluate(conn, "(c:ace_get_wiretype_list nil)") or []
        if doc.HandleToObject(wire_handle).Layer not in layers:
            raise ValueError("LINE is not on a registered Electrical wire layer")
        evaluate(conn,"(progn (c:wd_putwn "+wire+" "+literal(number)+") T)")
        result = inspect_wire(wire_handle)
        if not result.get("success") or result.get("wire_number") != number:
            raise BridgeError("Native wire number readback mismatch: " + str(result))
        return {**result, "status": "native_wire_number_verified"}
    except Exception as exc:
        return failure(exc)

def inspect_wire(wire_handle):
    """Read native network and number without changing either."""
    try:
        wire = entity(wire_handle)
        conn, doc = connection()
        obj = doc.HandleToObject(wire_handle)
        layers = evaluate(conn, "(c:ace_get_wiretype_list nil)") or []
        if obj.ObjectName != "AcDbLine" or obj.Layer not in layers:
            raise ValueError("Expected a LINE on a registered Electrical wire layer")
        result = evaluate(conn, "((lambda (/ r) (setq r (c:ace_get_wnum " + wire +
                          ')) (if r (list (car r) (cdr (assoc 5 (entget (cadr r))))) )))')
        return {"success": True, "wire_handle": wire_handle,
                "wire_number": result[0] if result else None,
                "number_block_handle": result[1] if result else None,
                "connections": network(conn, wire_handle), "wire_layer": obj.Layer,
                "start": list(obj.StartPoint), "end": list(obj.EndPoint)}
    except Exception as exc:
        return failure(exc)
