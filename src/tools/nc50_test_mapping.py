"""Manual-derived NC50 candidates. Never promote assumptions to observations."""
from copy import deepcopy
from src.tools.delta_mapping import fields, literal, plan_v2

SOURCE = {
    'file': 'DELTA_IA-CNC_NC5_Application_OM_MM_EN_20240126.pdf',
    'sha256': '7057dc26fb147ebe68d64b590827ec8d5ea8bcbd859ebc08992c0367c75d71a2',
    'pdf_pages': [323, 324], 'printed_pages': ['4-112', '4-113'],
    'section': '4.10.3 EIO Remote module setting',
}


def plan(spec):
    fields(spec, ['schema_version', 'purpose', 'mapping', 'eio_assumptions'], 'NC50 test plan')
    if type(spec['schema_version']) is not int or spec['schema_version'] != 4 or spec['purpose'] != 'test_only':
        raise ValueError('Version 4 test_only required')
    if not isinstance(spec['mapping'], dict) or type(spec['mapping'].get('schema_version')) is not int or spec['mapping']['schema_version'] != 2:
        raise ValueError('An unchanged version 2 mapping is required')
    result = plan_v2(spec['mapping'])
    rows = spec['eio_assumptions']
    if not isinstance(rows, list) or len(rows) != len(result['modules']):
        raise ValueError('Exactly one EIO assumption per mapped module required')
    modules = {m['id'].casefold(): m for m in result['modules']}
    seen = {}; ports = set(); sequences = set(); occupied = set()
    for row in rows:
        fields(row, ['module_id', 'eio_sequence', 'eio_port', 'start_address', 'source'], 'EIO assumption')
        literal(row['module_id'], 'module id'); literal(row['source'], 'assumption source')
        key = row['module_id'].casefold()
        if key not in modules or key in seen:
            raise ValueError('Unknown or duplicate module assumption')
        seq, port, start = (row[k] for k in ('eio_sequence', 'eio_port', 'start_address'))
        if type(seq) is not int or seq < 1 or seq > 20 or seq in sequences:
            raise ValueError('Unique EIO sequence in bounded test scope 1..20 required')
        if type(port) is not int or not 501 <= port <= 520 or port in ports:
            raise ValueError('Unique NC50 EIO Port 501..520 required; not R2 physical Port0..3')
        if type(start) is not int or not 256 <= start <= 480:
            raise ValueError('32-point R2 Start Address must keep every X/Y point within 256..511')
        addresses = set(range(start, start + 32))
        if occupied & addresses:
            raise ValueError('R2 modules overlap reserved X/Y address ranges')
        occupied.update(addresses); ports.add(port); sequences.add(seq); seen[key] = deepcopy(row)
    candidates = []
    for signal in result['signals']:
        row = seen[signal['module_id'].casefold()]
        # R2 manual orders 16 channels in each physical port; NC5 gives 32-point range.
        ordinal = (signal['port'] % 2) * 16 + signal['channel']
        prefix = 'X' if signal['electrical_type'].endswith('_input') else 'Y'
        candidate = prefix + str(row['start_address'] + ordinal)
        explicit = signal['global_plc_address']
        candidates.append({
            'signal_id': signal['id'], 'original': deepcopy(signal['original']),
            'wire_number': signal['wire_number'], 'potential': signal['potential'],
            'module_id': signal['module_id'], 'physical_endpoint': signal['endpoint'],
            'eio_sequence_candidate': row['eio_sequence'], 'eio_port_candidate': row['eio_port'],
            'nc50_address_candidate': candidate, 'candidate_basis': 'manual_rule_with_test_assumptions',
            'pdo_candidate': {'object_index': signal['object_index'], 'subindex': signal['subindex'],
                              'bit': signal['derived_bit_candidate']},
            'process_image_offset': None, 'hardware_verified': False,
            'explicit_address_agrees': None if explicit is None else explicit.upper() == candidate,
        })
    conflicts = [c['signal_id'] for c in candidates if c['explicit_address_agrees'] is False]
    return {
        'success': True, 'status': 'test_candidates_checked', 'schema_version': 4,
        'test_plan_valid': not conflicts, 'conflicting_explicit_addresses': conflicts,
        'source': SOURCE, 'eio_assumptions': deepcopy(rows), 'candidates': candidates,
        'mapping': result, 'cad_contacted': False, 'hardware_contacted': False, 'submitted': False,
        'ready_for_drawing': False, 'production_ready': False, 'formal_export_allowed': False,
        'limitations': [
            'Candidates do not overwrite global_plc_address, station, or observed_identity',
            'Scope is R2-EC0902 only; 32 X and 32 Y points per module',
            'EIO sequence excludes servo drives; not the absolute EtherCAT slave position',
            'Port-to-byte bit order remains a candidate pending online checks',
            'No NC50 settings, PDO selection, process-image offsets or DWG are written',
            'Software test validity is separate from formal release readiness',
        ],
    }
