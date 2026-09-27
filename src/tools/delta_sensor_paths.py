"""Three-wire sensor path preflight; native full-path qualification is pending."""
from copy import deepcopy
from pathlib import Path
import re
from src.tools.delta_mapping import fields, literal, plan_v2
from src.tools.delta_module_inventory import plan as inventory_plan
from src.autocad.trebi_project_pages import plan as page_plan

ROLES = ('sensor_supply', 'sensor_return', 'sensor_signal')

def plan(spec):
    fields(spec, ['schema_version', 'recipe', 'purpose', 'manifest', 'mapping', 'routes', 'sensor'], 'sensor path recipe')
    if type(spec['schema_version']) is not int or spec['schema_version'] != 5 or spec['recipe'] != 'remote_io_sensor_paths' or spec['purpose'] != 'test_only':
        raise ValueError('Version 5 test_only sensor path preflight required')
    pages = page_plan(spec['manifest'])
    entries = spec['manifest']['entries']
    if len(entries) != 2 or pages['logical_pages'] != ['102', '300'] or pages['effective_drawing_count'] != 2:
        raise ValueError('Effective pages 102 and 300 required')
    names = [e.get('drawing_file') for e in entries]
    if any(not isinstance(n, str) or Path(n).name != n or Path(n).suffix.lower() != '.dwg' for n in names) or len({n.casefold() for n in names}) != 2:
        raise ValueError('Unique local drawing filenames required')
    sensor = spec['sensor']
    fields(sensor, ['tag', 'symbol', 'test_input_mode', 'hardware_model', 'hardware_output_type', 'source'], 'sensor')
    if sensor['symbol'] != 'VPX11IN3' or sensor['test_input_mode'] != 'PNP':
        raise ValueError('Only verified three-wire symbol with explicit PNP test assumption supported')
    for key in ('tag', 'source'): literal(sensor[key], key)
    # A supplied physical model is not independently verified by this preflight.
    for key in ('hardware_model', 'hardware_output_type'): literal(sensor[key], key, True)
    if not re.fullmatch(r'-102B[1-9][0-9]*', sensor['tag']):
        raise ValueError('Sensor owner page must be 102')
    routes = spec['routes']
    if not isinstance(routes, list) or len(routes) != 3:
        raise ValueError('Supply, return and signal routes all required')
    by_id = {}; cores = set(); pins = set(); terminals = set(); pairs = set(); cables = set(); strips = set()
    expected = dict(zip(ROLES, [('1', '24IE', 'TEST24', 'TEST_24V'), ('3', '0V', 'TEST0', 'TEST_0V'), ('4', 'I546', 'TEST_I546', 'TEST_SIGNAL')]))
    for route in routes:
        fields(route, ['id', 'original', 'strip', 'terminal', 'cable', 'core', 'socket', 'plug', 'socket_pin', 'plug_pin', 'device', 'device_terminal', 'wire_number', 'wire_layer', 'source'], 'sensor route')
        for key, value in route.items(): literal(value, key)
        role = route['id']
        if role not in ROLES or role in by_id: raise ValueError('Unique sensor route roles required')
        for key in ('strip', 'terminal', 'cable', 'core', 'socket', 'plug', 'socket_pin', 'plug_pin'):
            if not re.fullmatch(r'[-A-Za-z0-9_]{1,32}', route[key]): raise ValueError('Simple route identities required')
        if (route['device_terminal'], route['original'], route['wire_number'], route['wire_layer']) != expected[role] or route['device'] != sensor['tag']:
            raise ValueError('Sensor pin, original identity and test network must remain distinct')
        if route['socket_pin'] != route['plug_pin']: raise ValueError('Mating pin mismatch')
        if (route['core'], route['socket_pin']) != dict(zip(ROLES, [('1','4'), ('2','5'), ('4','7')]))[role]:
            raise ValueError('I546 reference cable core/pin differs')
        for seen, key in [(cores, (route['cable'].casefold(), route['core'].casefold())), (pins, (route['socket'].casefold(), route['socket_pin'].casefold())), (terminals, (route['strip'].casefold(), route['terminal'].casefold()))]:
            if key in seen: raise ValueError('Duplicate cable core, pin or terminal')
            seen.add(key)
        pairs.add((route['socket'], route['plug'])); cables.add(route['cable']); strips.add(route['strip']); by_id[role] = deepcopy(route)
    if len(pairs) != 1 or len(cables) != 1 or len(strips) != 1: raise ValueError('One mating pair, cable and strip required')
    socket, plug = next(iter(pairs))
    if len({s.casefold() for s in (socket, plug, next(iter(cables)), next(iter(strips)), sensor['tag'])}) != 5:
        raise ValueError('Physical identities collide')
    if type(spec['mapping'].get('schema_version')) is not int or spec['mapping']['schema_version'] != 2:
        raise ValueError('Version 2 localization mapping required')
    mapping = plan_v2(spec['mapping'])
    if len(spec['mapping']['modules']) != 1 or spec['mapping']['modules'][0]['input_mode'] != 'PNP' or len(mapping['signals']) != 1:
        raise ValueError('One PNP remote IO and one sensor input required')
    signal = mapping['signals'][0]
    if signal['id'] != 'SENSOR' or spec['mapping']['signals'][0]['direction'] != 'input' or spec['mapping']['signals'][0]['purpose'] != 'ordinary_control' or signal['original']['signal'] != 'I546' or signal['potential'] != 'TEST_24V' or signal['wire_number'] != 'TEST_I546':
        raise ValueError('Ordinary I546 test input mapping required')
    target = spec['mapping']['signals'][0]['target']
    inventory = inventory_plan({'schema_version': 3, 'purpose': 'test_only', 'module_id': target['module_id']})
    matches = [p for section in inventory['sections'] for p in section['terminals'] if p.get('role') == 'input' and (p.get('port'), p.get('channel')) == (target['port'], target['channel'])]
    if len(matches) != 1: raise ValueError('Unique documented R2 input required')
    return dict(success=True, submitted=False, cad_contacted=False, status='sensor_paths_preflight_only',
        execution_supported=False, production_ready=False, formal_export_allowed=False,
        pages=pages, sensor=deepcopy(sensor), routes=[by_id[r] for r in ROLES], mapping=mapping,
        target_endpoint=matches[0], input_common={'electrical_connection': 'X8TERM76', 'test_potential': 'TEST_0V'},
        sensor_connections={'X2TERM02': '1', 'X2TERM03': '3', 'X8TERM01': '4'},
        pending=mapping['pending'] + ['Sensor physical model/output type unverified', 'Native full sensor path batch, shared loads, reopen, reports and PDF qualification pending'],
        limitations=['Connector mating is declared; no fictitious jumper', 'No hardware contacted; target is a test assignment', 'Existing branch test is not complete shared-load acceptance'])
