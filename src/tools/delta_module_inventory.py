"""Read-only complete R2 family terminal inventory; no inferred PLC addresses."""
import json
import re
from pathlib import Path

PROFILE = Path(__file__).resolve().parents[2] / "profiles/delta-r2-ec0902.json"


def plan(spec):
    if not isinstance(spec, dict) or set(spec) != {"schema_version", "purpose", "module_id"}:
        raise ValueError("Inventory v3 requires schema_version, purpose and module_id")
    if type(spec["schema_version"]) is not int or spec["schema_version"] != 3 or spec["purpose"] != "test_only":
        raise ValueError("Only inventory v3 test_only is supported")
    module = spec["module_id"]
    if not isinstance(module, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", module):
        raise ValueError("Explicit simple module instance required")
    cfg = json.loads(PROFILE.read_text(encoding="utf8"))
    sections = []
    for port in cfg["ports"]:
        number = port["port"]
        connector = port["connector"]
        terminals = []
        for channel in range(port["count"]):
            terminal = f"{port['prefix']}{channel:02d}"
            common = port.get("input_common") or f"{connector}:C{port['first_common'] + channel // 4}"
            terminals.append({
                "endpoint": f"{module}/{connector}/{terminal}", "terminal": terminal,
                "role": port["direction"], "port": number, "channel": channel,
                "common_endpoint": f"{module}/" + common.replace(":", "/"),
                "electrical_type": "sink_source_input" if number < 2 else "relay_no_dry_contact",
                "object_index": port["object_index"],
                "subindex": port["first_subindex"] + channel // 8,
                "derived_bit_candidate": channel % 8,
                "global_plc_address": None, "potential": None,
                "source_pdf_page": cfg["source"]["pdf_pages"][f"port{number}"]})
        if number >= 2:
            for group in range(port["first_common"], port["first_common"] + 4):
                terminals.append({"endpoint": f"{module}/{connector}/C{group}",
                    "terminal": f"C{group}", "role": "relay_common", "potential": None,
                    "source_pdf_page": cfg["source"]["pdf_pages"][f"port{number}"]})
        elif number == 1:
            terminals.append({"endpoint": f"{module}/TB3/S/S", "terminal": "S/S",
                "role": "shared_input_common", "shared_ports": [0, 1],
                "potential": None, "source_pdf_page": 36})
        sections.append({"connector": connector, "port": number, "terminals": terminals})
    sections.append({"connector": "TB1", "port": None, "terminals": [
        {"endpoint": f"{module}/TB1/{name}", "terminal": name, "role": "module_power",
         "potential": None, "source_pdf_page": 39} for name in ["24V", "GND", "FG"]]})
    all_points = [t for section in sections for t in section["terminals"]]
    return {"success": True, "status": "documented_full_terminal_inventory", "cad_contacted": False,
        "submitted": False, "module_id": module, "documented_family": cfg["family"],
        "source": cfg["source"], "sections": sections, "connectable_terminal_count": len(all_points),
        "nonconnectable": [{"connector": "TB2", "terminal": "N.C", "source_pdf_page": 35}],
        "hardware_revision": None, "station": None, "input_mode": None,
        "ready_for_drawing": False, "production_ready": False,
        "pending": ["Dedicated native PLC symbol and reports", "Physical device identity and Revision",
                    "NC50 addresses and station", "Input mode and common potentials", "Per-terminal wiring acceptance"]}
