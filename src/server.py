"""Main MCP server entry point for AutoCAD (Electrical and Standard).

Supports both AutoCAD Electrical (full 34+ tools) and AutoCAD Standard
(drawing + 2D/3D geometry tools).  The active variant is auto-detected at
startup via :mod:`src.autocad.detector`.

Uses FastMCP from the ``mcp`` library to register tools and serve them over
stdio transport so that Claude Code (and other MCP clients) can invoke them.

Usage
-----
Run as a module::

    python -m src.server

Or via the installed script::

    autocad-mcp
"""

from __future__ import annotations

import logging
import sys
from typing import Any

# ---------------------------------------------------------------------------
# Logging configuration (before any other imports that log)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MCP server bootstrap
# ---------------------------------------------------------------------------
try:
    from mcp.server.fastmcp import FastMCP
except ImportError as _exc:
    logger.critical(
        "The 'mcp' package is not installed.  Run: pip install mcp>=1.0.0\n%s",
        _exc,
    )
    sys.exit(1)

from src.config import get_config
from src.autocad.connection import get_connection, AutoCADConnectionError
from src.autocad.detector import detect as _detect_autocad

# Load config early so tools can use it
_cfg = get_config()
_mcp_cfg = _cfg.mcp

# Detect AutoCAD variant (Electrical / Standard / none)
_acad_info = _detect_autocad(allow_com=False)
logger.info(
    "AutoCAD variant: %s | running: %s | method: %s",
    _acad_info.variant, _acad_info.running, _acad_info.detection_method,
)

# Initialise FastMCP (mcp>=1.2 removed the 'version' parameter)
mcp = FastMCP(
    name=_mcp_cfg.get("server_name", "autocad-mcp"),
)

from src.tool_policy import register
registered_tool = register(mcp)

# ---------------------------------------------------------------------------
# Lazy AutoCAD connection (attempt at startup but don't fail if not running)
# ---------------------------------------------------------------------------

def _attempt_autocad_connect() -> None:
    """Try to connect to AutoCAD; log a warning if unavailable."""
    ac_cfg = _cfg.autocad
    com_obj = ac_cfg.get("com_object", "AutoCAD.Application")
    timeout = int(ac_cfg.get("timeout", 30))
    try:
        conn = get_connection(com_object=com_obj, timeout=timeout, auto_connect=True)
        logger.info("AutoCAD connection established: %s", conn._get_version_string())
    except AutoCADConnectionError as exc:
        logger.warning(
            "AutoCAD is not running at startup – tools will return an error "
            "until AutoCAD Electrical 2025 is launched.\n  %s",
            exc,
        )
    except Exception as exc:
        logger.warning("AutoCAD connection attempt failed: %s", exc)


# ---------------------------------------------------------------------------
# Import tool modules
# ---------------------------------------------------------------------------
from src.tools import drawing, electrical, wires, components, reports, project
from src.tools import drawing3d


# ===========================================================================
# Drawing tools  (2D — available for both Standard and Electrical)
# ===========================================================================

@registered_tool()
def draw_line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    layer: str = "0",
    drawing_path: str = "",
) -> dict[str, Any]:
    """Optional drawing_path must match the active DWG; worker validates before entry. Draw a line from (x1, y1) to (x2, y2) on the specified layer.

    Returns a dict with success status and the entity handle on success.
    """
    return drawing.draw_line(x1, y1, x2, y2, layer)


@registered_tool()
def draw_circle(
    cx: float,
    cy: float,
    radius: float,
    layer: str = "0",
    drawing_path: str = "",
) -> dict[str, Any]:
    """Optional drawing_path must match the active DWG; worker validates before entry. Draw a circle at centre (cx, cy) with the given radius."""
    return drawing.draw_circle(cx, cy, radius, layer)


@registered_tool()
def draw_arc(
    cx: float,
    cy: float,
    radius: float,
    start_angle: float,
    end_angle: float,
    layer: str = "0",
) -> dict[str, Any]:
    """Draw an arc centred at (cx, cy).

    Angles are in degrees; 0° = East, counter-clockwise positive.
    """
    return drawing.draw_arc(cx, cy, radius, start_angle, end_angle, layer)


@registered_tool()
def draw_text(
    x: float,
    y: float,
    text: str,
    height: float = 2.5,
    layer: str = "0",
    drawing_path: str = "",
) -> dict[str, Any]:
    """Optional drawing_path must match the active DWG; worker validates before entry. Place a single-line text entity at (x, y) with the given height."""
    return drawing.draw_text(x, y, text, height, layer)


@registered_tool()
def draw_rectangle(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    layer: str = "0",
    drawing_path: str = "",
) -> dict[str, Any]:
    """Optional drawing_path must match the active DWG; worker validates before entry. Draw a closed rectangular polyline from corner (x1, y1) to (x2, y2)."""
    return drawing.draw_rectangle(x1, y1, x2, y2, layer)


@registered_tool()
def draw_polyline(
    points: list,
    closed: bool = False,
    layer: str = "0",
) -> dict[str, Any]:
    """Draw a 2-D lightweight polyline through a list of [x, y] points.

    Parameters
    ----------
    points : list of [x, y]   At least 2 vertices.
    closed : bool             Close the polyline (last → first vertex).
    layer : str               Target layer.
    """
    return drawing.draw_polyline(points, closed, layer)


@registered_tool()
def zoom_extents() -> dict[str, Any]:
    """Zoom the active viewport to fit all entities (ZOOM E)."""
    return drawing.zoom_extents()


@registered_tool()
def set_layer(
    layer_name: str,
    color: int = 7,
    linetype: str = "Continuous",
    make_active: bool = True,
) -> dict[str, Any]:
    """Create or configure a layer and optionally make it active.

    Parameters
    ----------
    layer_name : str    Layer name.
    color : int         ACI color (1=Red, 2=Yellow, 3=Green, 5=Blue, 7=White).
    linetype : str      Linetype (e.g. 'Continuous', 'DASHED').
    make_active : bool  Set as the active layer.
    """
    return drawing.set_layer(layer_name, color, linetype, make_active)


# ===========================================================================
# 3D Drawing tools  (Standard and Electrical)
# ===========================================================================

@registered_tool()
def draw_line_3d(
    x1: float, y1: float, z1: float,
    x2: float, y2: float, z2: float,
    layer: str = "0",
) -> dict[str, Any]:
    """Draw a 3-D line between two XYZ points.

    Parameters
    ----------
    x1, y1, z1 : float   Start point.
    x2, y2, z2 : float   End point.
    layer : str           Target layer.
    """
    return drawing3d.draw_line_3d(x1, y1, z1, x2, y2, z2, layer)


@registered_tool()
def draw_polyline_3d(
    points: list,
    closed: bool = False,
    layer: str = "0",
) -> dict[str, Any]:
    """Draw a 3-D polyline through a list of [x, y, z] points.

    Parameters
    ----------
    points : list of [x, y, z]   At least 2 vertices.
    closed : bool                Close the polyline.
    layer : str                  Target layer.
    """
    return drawing3d.draw_polyline_3d(points, closed, layer)


@registered_tool()
def draw_3d_face(
    x1: float, y1: float, z1: float,
    x2: float, y2: float, z2: float,
    x3: float, y3: float, z3: float,
    x4: float = None, y4: float = None, z4: float = None,
    layer: str = "0",
) -> dict[str, Any]:
    """Draw a 3DFACE (triangle or quad) in 3-D space.

    For a triangle, leave x4/y4/z4 as None (third point is duplicated).
    """
    return drawing3d.draw_3d_face(x1, y1, z1, x2, y2, z2, x3, y3, z3,
                                   x4, y4, z4, layer)


@registered_tool()
def draw_box(
    origin_x: float, origin_y: float, origin_z: float,
    length: float, width: float, height: float,
    layer: str = "0",
) -> dict[str, Any]:
    """Draw a 3-D solid box (ACIS — requires full AutoCAD with 3D Modeling).

    Returns ``{"note": "ACIS_NOT_AVAILABLE"}`` if the license doesn't permit it.
    """
    return drawing3d.draw_box(origin_x, origin_y, origin_z,
                               length, width, height, layer)


@registered_tool()
def draw_sphere(
    cx: float, cy: float, cz: float,
    radius: float,
    layer: str = "0",
) -> dict[str, Any]:
    """Draw a 3-D solid sphere (ACIS)."""
    return drawing3d.draw_sphere(cx, cy, cz, radius, layer)


@registered_tool()
def draw_cylinder(
    cx: float, cy: float, cz: float,
    radius: float, height: float,
    layer: str = "0",
) -> dict[str, Any]:
    """Draw a 3-D solid cylinder (ACIS)."""
    return drawing3d.draw_cylinder(cx, cy, cz, radius, height, layer)


@registered_tool()
def draw_cone(
    cx: float, cy: float, cz: float,
    base_radius: float, height: float,
    layer: str = "0",
) -> dict[str, Any]:
    """Draw a 3-D solid cone (ACIS)."""
    return drawing3d.draw_cone(cx, cy, cz, base_radius, height, layer)


@registered_tool()
def zoom_3d_view(view_type: str = "SE_ISOMETRIC") -> dict[str, Any]:
    """Switch to a 3-D view preset and zoom to extents.

    view_type options: SE_ISOMETRIC, SW_ISOMETRIC, NE_ISOMETRIC, NW_ISOMETRIC,
    TOP, FRONT, RIGHT, LEFT, BACK, BOTTOM, PERSPECTIVE.
    """
    return drawing3d.zoom_3d_view(view_type)


@registered_tool()
def set_ucs(
    origin_x: float = 0.0, origin_y: float = 0.0, origin_z: float = 0.0,
    x_axis_x: float = 1.0, x_axis_y: float = 0.0, x_axis_z: float = 0.0,
    y_axis_x: float = 0.0, y_axis_y: float = 1.0, y_axis_z: float = 0.0,
    name: str = "MCP_UCS",
) -> dict[str, Any]:
    """Define and activate a named User Coordinate System for 3-D work."""
    return drawing3d.set_ucs(
        origin_x, origin_y, origin_z,
        x_axis_x, x_axis_y, x_axis_z,
        y_axis_x, y_axis_y, y_axis_z,
        name,
    )


@registered_tool()
def get_autocad_info() -> dict[str, Any]:
    """Return detected AutoCAD variant, version, features, and running state.

    Useful for discovering whether AutoCAD Electrical or Standard is active
    and which feature groups are enabled.
    """
    return _acad_info.to_dict()


# ===========================================================================
# Electrical tools  (AutoCAD Electrical only)
# ===========================================================================

@registered_tool()
def insert_electrical_symbol(
    symbol_name: str,
    x: float,
    y: float,
    rotation: float = 0.0,
    attributes: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Insert through c:wd_insym2 and verify the new block and attributes.

    Use an installed symbol name/path (e.g. HCR1 or HT0001). Requires a saved
    Electrical drawing with WD_M. Rotation must be zero; choose H/V symbols.
    Partial failures include created_handle: inspect before retrying.
    """
    return electrical.insert_electrical_symbol(symbol_name, x, y, rotation, attributes)


@registered_tool()
def insert_ladder(
    x_start: float,
    y_start: float,
    rung_spacing: float = 25.4,
    rung_count: int = 10,
    voltage: str = "120V",
    phase: str = "1P",
) -> dict[str, Any]:
    """Create a ladder diagram using AutoCAD Electrical's WDLADDER command.

    Parameters
    ----------
    x_start, y_start : float
        Origin of the ladder (top-left).
    rung_spacing : float
        Vertical distance between rungs in drawing units (25.4 = 1 inch).
    rung_count : int
        Number of rungs.
    voltage : str
        Voltage label (e.g. "120V", "24VDC").
    phase : str
        "1P" for single-phase or "3P" for three-phase.
    """
    return electrical.insert_ladder(x_start, y_start, rung_spacing, rung_count, voltage, phase)


@registered_tool()
def get_symbol_list(category: str = "", library_path: str | None = None,
                    query: str = "", limit: int = 100, offset: int = 0) -> dict[str, Any]:
    """List real installed DWG files with pagination. File presence does not verify a symbol.

    Categories are limited to coils/terminals/fuses/buttons/signals validated examples.
    Use category='' plus query to discover other files without inferred categories.
    """
    return electrical.get_symbol_list(category, library_path, query, limit, offset)

@registered_tool()
def set_wire_number(
    wire_number: str,
    x: float,
    y: float,
) -> dict[str, Any]:
    """Place a wire number tag at the given coordinates using WDWNUM."""
    return electrical.set_wire_number(wire_number, x, y)


@registered_tool()
def insert_plc_module(
    module_type: str,
    rack: int,
    slot: int,
    x: float,
    y: float,
) -> dict[str, Any]:
    """Insert a PLC I/O module symbol.

    Parameters
    ----------
    module_type : str
        "input", "output", "analog_input", or "analog_output".
    rack : int
        PLC rack number (0-based).
    slot : int
        Slot number within the rack (0-based).
    x, y : float
        Insertion point.
    """
    return electrical.insert_plc_module(module_type, rack, slot, x, y)


@registered_tool()
def create_cross_reference(
    source_tag: str,
    dest_sheet: str,
    dest_ref: str,
) -> dict[str, Any]:
    """Create a cross-reference link between a source component and a destination.

    Parameters
    ----------
    source_tag : str
        TAG1 of the source component (e.g. "101CR").
    dest_sheet : str
        Destination drawing sheet number (e.g. "3").
    dest_ref : str
        Reference designation on the destination sheet (e.g. "B12").
    """
    return electrical.create_cross_reference(source_tag, dest_sheet, dest_ref)


@registered_tool()
def edit_component_attributes(
    tag1: str,
    attributes_dict: dict[str, str],
) -> dict[str, Any]:
    """Update attribute values on a component identified by TAG1.

    Parameters
    ----------
    tag1 : str
        The component's TAG1 identifier.
    attributes_dict : dict[str, str]
        Attribute tag → new value mapping.
    """
    return electrical.edit_component_attributes(tag1, attributes_dict)


# ===========================================================================
# Wire tools
# ===========================================================================

@registered_tool()
def draw_wire(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    wire_layer: str = "WIRES",
) -> dict[str, Any]:
    """Draw a wire segment on the WIRES layer (or custom layer).

    Parameters
    ----------
    x1, y1 : float
        Wire start point.
    x2, y2 : float
        Wire end point.
    wire_layer : str
        Target layer (default "WIRES").
    """
    return wires.draw_wire(x1, y1, x2, y2, wire_layer)


@registered_tool()
def number_wires(
    sheet: str | None = None,
    project: str | None = None,
) -> dict[str, Any]:
    """Run AutoCAD Electrical's WDANNO wire-numbering command.

    Parameters
    ----------
    sheet : str or None
        Sheet to limit scope; None uses the active drawing.
    project : str or None
        When provided, triggers project-wide numbering.
    """
    return wires.number_wires(sheet, project)


@registered_tool()
def get_wire_numbers(sheet: str | None = None) -> dict[str, Any]:
    """Return all wire number tags in the active drawing."""
    return wires.get_wire_numbers(sheet)


@registered_tool()
def set_wire_attributes(
    tag: str,
    attributes: dict[str, str],
) -> dict[str, Any]:
    """Modify attributes on a wire entity identified by its wire-number tag.

    Parameters
    ----------
    tag : str
        Wire number / tag to locate.
    attributes : dict[str, str]
        Attribute tag → new value mapping.
    """
    return wires.set_wire_attributes(tag, attributes)


@registered_tool()
def create_wire_from_to(
    from_component: str,
    to_component: str,
) -> dict[str, Any]:
    """Route a wire between two components identified by their TAG1 values.

    Parameters
    ----------
    from_component : str
        TAG1 of the source component.
    to_component : str
        TAG1 of the destination component.
    """
    return wires.create_wire_from_to(from_component, to_component)


# ===========================================================================
# Component tools
# ===========================================================================

@registered_tool()
def get_component_list(drawing: str | None = None) -> dict[str, Any]:
    """List all AutoCAD Electrical components in the active drawing."""
    return components.get_component_list(drawing)


@registered_tool()
def get_component_info(tag1: str) -> dict[str, Any]:
    """Return full attribute information for the component with the given TAG1."""
    return components.get_component_info(tag1)


@registered_tool()
def update_component(
    tag1: str,
    attributes: dict[str, str],
) -> dict[str, Any]:
    """Update attribute values on the component identified by TAG1.

    Parameters
    ----------
    tag1 : str
        TAG1 of the target component.
    attributes : dict[str, str]
        Attribute tag → new value pairs.
    """
    return components.update_component(tag1, attributes)


@registered_tool()
def delete_component(tag1: str) -> dict[str, Any]:
    """Remove the component identified by TAG1 from the current drawing."""
    return components.delete_component(tag1)


@registered_tool()
def move_component(
    tag1: str,
    new_x: float,
    new_y: float,
) -> dict[str, Any]:
    """Move a component identified by TAG1 to new coordinates (new_x, new_y)."""
    return components.move_component(tag1, new_x, new_y)


@registered_tool()
def search_components(filter_criteria: dict[str, str]) -> dict[str, Any]:
    """Search for components matching one or more attribute criteria.

    Parameters
    ----------
    filter_criteria : dict[str, str]
        Attribute tag → expected value.  Use a trailing ``*`` for prefix
        matching, e.g. ``{"TAG1": "CR*", "MFG": "ALLEN-BRADLEY"}``.
    """
    return components.search_components(filter_criteria)


# ===========================================================================
# Report tools
# ===========================================================================

@registered_tool()
def generate_bom(
    output_format: str = "csv",
    output_path: str | None = None,
) -> dict[str, Any]:
    """Generate a Bill of Materials for the active drawing.

    Parameters
    ----------
    output_format : str
        "csv" (default) or "wdreport" to use AutoCAD Electrical's WDREPORT.
    output_path : str or None
        Output file path; defaults to a timestamped file in Documents.
    """
    return reports.generate_bom(output_format, output_path)


@registered_tool()
def generate_wire_list(output_path: str | None = None) -> dict[str, Any]:
    """Generate a wire connection list (from-to report) as a CSV file."""
    return reports.generate_wire_list(output_path)


@registered_tool()
def generate_terminal_plan(output_path: str | None = None) -> dict[str, Any]:
    """Generate a terminal strip report as a CSV file."""
    return reports.generate_terminal_plan(output_path)


@registered_tool()
def generate_plc_io_list(output_path: str | None = None) -> dict[str, Any]:
    """Generate a PLC I/O list as a CSV file."""
    return reports.generate_plc_io_list(output_path)


@registered_tool()
def get_project_summary() -> dict[str, Any]:
    """Return a summary of open drawings, total components, and wire counts."""
    return reports.get_project_summary()


# ===========================================================================
# Project tools
# ===========================================================================

@registered_tool()
def get_project_info() -> dict[str, Any]:
    """Return information about the current AutoCAD Electrical project."""
    return project.get_project_info()


@registered_tool()
def list_drawings() -> dict[str, Any]:
    """List all drawings currently open in AutoCAD."""
    return project.list_drawings()


@registered_tool()
def open_drawing(sheet_number_or_name: str) -> dict[str, Any]:
    """Switch to or open a drawing by sheet number or filename.

    Parameters
    ----------
    sheet_number_or_name : str
        Sheet number (e.g. "3") or drawing filename (e.g. "Sheet_03.dwg").
    """
    return project.open_drawing(sheet_number_or_name)


@registered_tool()
def close_drawing(save: bool = True) -> dict[str, Any]:
    """Close the currently active drawing.

    Parameters
    ----------
    save : bool
        Save the drawing before closing (default True).
    """
    return project.close_drawing(save)


@registered_tool()
def sync_project() -> dict[str, Any]:
    """Run a project-wide update via AutoCAD Electrical's WDSYNCH command."""
    return project.sync_project()


@registered_tool()
def get_active_drawing() -> dict[str, Any]:
    """Return information about the currently active drawing."""
    return project.get_active_drawing()


# ===========================================================================
# Entry point
# ===========================================================================

@registered_tool()
def get_electrical_connections(handle: str) -> dict[str, Any]:
    """Read a component's real X?TERM connection points and terminal labels."""
    from src.tools.native_electrical import get_connections
    return get_connections(handle)


@registered_tool()
def connect_electrical_terminals(from_handle: str, from_connection: str,
                                 to_handle: str, to_connection: str,
                                 wire_layer: str = "MCP_WIRE") -> dict[str, Any]:
    """Connect specific X?TERM attributes using Electrical native wire routing and netlist verification."""
    from src.tools.native_electrical import connect_terminals
    return connect_terminals(from_handle, from_connection, to_handle, to_connection, wire_layer)


@registered_tool()
def set_electrical_wire_number(wire_handle: str, number: str) -> dict[str, Any]:
    """Set a normal wire number through Electrical and read it back from its native network."""
    from src.tools.native_electrical import set_number
    return set_number(wire_handle, number)


@registered_tool()
def get_electrical_wire(wire_handle: str) -> dict[str, Any]:
    """Read native wire number, raw endpoints, network wire handles and geometry.

    Parametric P/J endpoints can be omitted by the native netlist API; success
    means the read completed, not that connectivity passed. TREBI v4 additionally
    verifies connector paths against handle-bound native From/To reports.
    """
    from src.tools.native_electrical import inspect_wire
    return inspect_wire(wire_handle)


@registered_tool()
def get_electrical_project() -> dict[str, Any]:
    """Read active WDP and its exact drawing membership from Electrical."""
    from src.tools.native_project import get_project
    return get_project()


@registered_tool()
def update_electrical_signals(project_path: str) -> dict[str, Any]:
    """Update CURRENT drawing's source/destination references and wire numbers.

    Requires expected active WDP. Save all project drawings first; repeat on each
    target drawing. Read back signal attributes and verify native From/To output.
    """
    from src.tools.native_project import update_signals
    return update_signals(project_path)


@registered_tool()
def branch_electrical_terminal_to_wire(terminal_handle: str, connection_name: str,
                                       wire_handle: str, x: float, y: float) -> dict[str, Any]:
    """Add a straight aligned T branch from an unwired component pin to a wire.

    The tap must lie on the selected segment. Verifies all three or more native
    endpoints and inherited number. Already-connected calls do not draw again.
    """
    from src.tools.native_branch import branch
    return branch(terminal_handle, connection_name, wire_handle, x, y)


@registered_tool()
def update_electrical_cross_references(project_path: str) -> dict[str, Any]:
    """Update native parent/child references in a matching project.

    All member drawings must be open and saved. Reject ambiguous INST/LOC/TAG
    matches before writing. Returns both parent and child attributes, plus audit.
    Exact reference positions and saved files still require independent checking.
    """
    from src.tools.native_cross_references import update
    return update(project_path)


@registered_tool()
def export_electrical_project_report(project_path: str, report_type: str,
                                     output_path: str) -> dict[str, Any]:
    """Export native bom, components, from_to, terminal_plan or terminal_numbers CSV.

    Save project drawings first. Requires matching active WDP/member drawing and
    a new absolute CSV path. Returned native rows have no header; file creation
    alone does not prove design correctness.
    """
    from src.tools.native_project import export_report
    return export_report(project_path, report_type, output_path)


@registered_tool()
def get_tool_capabilities() -> dict[str, Any]:
    """List all implemented tool statuses, default exposure, gaps and replacements."""
    from src.tool_policy import catalogue
    return {"success":True,"tools":catalogue()}


@registered_tool()
def add_aligned_dimension(drawing_path: str, x1: float, y1: float, x2: float, y2: float,
                          text_x: float, text_y: float) -> dict[str, Any]:
    """Create and read a native measured aligned dimension. Not associative to source geometry."""
    from src.tools.dimensions import aligned
    return aligned(drawing_path,x1,y1,x2,y2,text_x,text_y)


@registered_tool()
def add_diameter_dimension(drawing_path: str, circle_handle: str, leader_length: float = 8.0) -> dict[str, Any]:
    """Create native diameter dimension from an XY circle. Source association is not maintained."""
    from src.tools.dimensions import diameter
    return diameter(drawing_path,circle_handle,leader_length)


@registered_tool()
def get_dimension_info(drawing_path: str, handle: str) -> dict[str, Any]:
    """Read native dimension measurement, object type and text override."""
    from src.tools.dimensions import inspect
    return inspect(drawing_path,handle)


@registered_tool()
def export_electrical_project_pdf(project_path: str, output_path: str,
                                  template_mode: str) -> dict[str, Any]:
    """Export synthetic DIN A3 model-space test project to a new multipage PDF.

    template_mode must be synthetic_din_a3, synthetic_zh_en_a3 or synthetic_trebi_a3. All project pages must be open/saved
    and active project must match. Copies get NTS and test-only/page labels.
    TREBI preserves logical PAGE/OF and validates native grid/navigation before plotting.
    Requires optional pdf dependency. Uses fit-to-page monochrome A3, preserves
    source DWGs, restores original active drawing on success. Returns structural
    checks only; visual review is still required. No automatic retry on failure.
    """
    from src.tools.native_pdf import export_pdf
    return export_pdf(project_path, output_path, template_mode)


@registered_tool()
def execute_trebi_test_change(project_path: str, drawing_path: str, spec: dict[str, Any]) -> dict[str, Any]:
    """Restricted saved synthetic fixture only: lamp replacement or Y00-to-Y01 rewire. No production support; partial failures never replay."""
    from src.tools.trebi_test_changes import execute
    return execute(project_path, drawing_path, spec)


@registered_tool()
def get_execution_diagnostics() -> dict[str, Any]:
    """Read local operation receipts and interruption marker without contacting AutoCAD."""
    from src.autocad.isolated import diagnose
    return diagnose()


@registered_tool()
def plan_trebi_batch(spec: dict[str, Any]) -> dict[str, Any]:
    """Plan bounded TREBI logical pages, inherited tags and exact references without CAD.

    Version 5 preflights test-only three-wire sensor paths; execution is not qualified.
    Does not scan existing drawings or select replacement catalog parts.
    """
    from src.tools.trebi_batch import plan
    try:
        return plan(spec)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        return {"success": False, "status": "preflight_rejected", "submitted": False, "error": str(exc)}


@registered_tool()
def execute_trebi_batch(project_path: str, spec: dict[str, Any], drawing_path: str) -> dict[str, Any]:
    """Execute TREBI v1, Delta test_only v2 (one page) v3 (three DI/DO pages) or v4 (split connector/cable paths).

    Version 5 sensor paths are planning-only and are rejected before batch writes.
    All pages must be open/saved, WDT and LINE20 must match manifest. Applies
    grid/title rules, inserts relay/NO contact/terminals/signal arrows, connects
    v1 horizontal wires or fixed v2 Delta wiring, numbers, references and reports.
    Stops on first failure; partial writes are never rolled back or replayed.
    Returns durable per-step receipt. Independent reopen/visual review required.
    """
    from src.tools.trebi_batch import execute
    return execute(project_path, spec, drawing_path)


@registered_tool()
def plan_delta_r2_io(spec: dict[str, Any]) -> dict[str, Any]:
    """Read-only R2-EC0902 EtherCAT remote I/O port/common/PDO draft with source pages.
    PLC logic belongs to the NC50 controller, not R2. Communication ports are separate from discrete I/O.

    Version 4 checks test_only NC50 EIO assumptions around a v2 mapping; candidate
    addresses remain separate from observed bindings. See docs/nc50-test-mapping.md.
    Version 3 returns the full 76-terminal inventory: schema_version=3, purpose=test_only, module_id.
    Version 1 plans manual-based channels. Version 2 reads a hash-pinned local ESI,
    matches supplied device observations, and keeps original signals, terminals,
    potentials, wire numbers and explicit PLC addresses separate. Never contacts
    hardware or CAD; drawing readiness remains false.
    """
    from src.tools.delta_io import plan
    try:
        return plan(spec)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        return {"success":False,"status":"preflight_rejected","submitted":False,"cad_contacted":False,"error":str(exc)}


@registered_tool()
def insert_test_parametric_connector(project_path: str, drawing_path: str, x: float, y: float, pins: list[str], purpose: str) -> dict[str, Any]:
    """Experimental native connector, 1..8 pins, on a blank saved TREBI test page. No production support."""
    from src.tools.native_parametric import insert
    return insert('connector', project_path, drawing_path, x, y, purpose, pins)


@registered_tool()
def insert_test_plc_module(project_path: str, drawing_path: str, x: float, y: float, purpose: str) -> dict[str, Any]:
    """Experimental whole-module 1771-IAD API fixture on blank saved TREBI page. NOT Delta. Requires independent wiring/report/reopen acceptance."""
    from src.tools.native_parametric import insert
    return insert('plc_fixture', project_path, drawing_path, x, y, purpose)


@registered_tool()
def recover_cad_interruption(action: str, expected_drawing_path: str, expected_instance_hwnd: int,
                             operation_id: str = "", snapshot_id: str = "") -> dict[str, Any]:
    """Inspect quarantine then release exactly reviewed saved CAD state. Never replay/undo. Inspect first; release needs returned operation_id and snapshot_id. Unsupported entities, active worker or changed state reject."""
    from src.autocad.recovery import inspect_or_release
    try:
        return inspect_or_release(action, expected_drawing_path, expected_instance_hwnd, operation_id, snapshot_id)
    except Exception as exc:
        return {"success": False, "status": "recovery_rejected", "error": str(exc), "submitted": False}


@registered_tool()
def plan_cad_project(spec: dict[str, Any]) -> dict[str, Any]:
    """Plan new external mechanical/TREBI draft project; no CAD writes. Schema v1: name, output_root, discipline, pages, purpose; electrical also requires base_project."""
    from src.tools.engineering_project import plan
    try:return plan(spec)
    except Exception as exc:return {'success':False,'submitted':False,'status':'preflight_rejected','error':str(exc)}


@registered_tool()
def create_cad_project(spec: dict[str, Any]) -> dict[str, Any]:
    """Create new empty draft project using verified mechanical/TREBI DWT. Never overwrite. Electrical requires explicit active base WDP for settings; partial outcomes must not be replayed."""
    from src.tools.engineering_project import execute
    return execute(spec)


@registered_tool()
def audit_cad_project(project_path: str, evidence_files: list[str]) -> dict[str, Any]:
    """Read-only version-bound evidence summary for hardware, mapping, tags, wiring, references, reports, reopen and PDF. Missing/unknown/stale evidence blocks release; never claims hardware verification or production approval."""
    from src.tools.project_acceptance import audit
    try:return audit(project_path,evidence_files)
    except Exception as exc:return {'success':False,'submitted':False,'error':str(exc)}


@registered_tool()
def restore_cad_project(archive_path: str, destination: str, project_name: str) -> dict[str, Any]:
    """Restore verified saved sibling-file snapshot into a NEW directory and NEW WDP/WDT name. No CAD calls or overwrite; requires separate CAD reopen/report acceptance. Never replay a partial restore."""
    from src.tools.project_recovery import recover
    try:return recover(archive_path,destination,project_name)
    except Exception as exc:return {'success':False,'status':'restore_failed_inspect_destination','error':str(exc),'automatic_retry':False}


def main() -> None:
    """Start the MCP server (stdio transport)."""
    logger.info(
        "Starting %s v%s",
        _mcp_cfg.get("server_name", "autocad-electrical-mcp"),
        _mcp_cfg.get("server_version", "1.0.0"),
    )
    logger.info("Local MCP transport; model authentication belongs to the subscription client")

    # Attempt AutoCAD connection at startup (non-fatal)
    # CAD connects only inside bounded workers, never on MCP startup.

    # Run the MCP server (blocks until the client disconnects)
    mcp.run()


if __name__ == "__main__":
    main()
