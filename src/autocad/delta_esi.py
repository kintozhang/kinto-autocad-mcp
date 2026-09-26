"""Bounded local ESI inspection; identities are declarations, never device discovery."""
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

KNOWN_REVISIONS = {0x00100000, 0x01100000}

def integer(value):
    if not isinstance(value, str):
        raise ValueError('Identity must be a hex or decimal string')
    try:
        result = int(value[2:], 16) if value.lower().startswith(('#x', '0x')) else int(value, 10)
    except ValueError:
        raise ValueError('Invalid device identity') from None
    if not 0 <= result <= 0xffffffff:
        raise ValueError('Identity outside unsigned 32-bit range')
    return result

def inspect_esi(path, expected_sha256):
    p = Path(path)
    if not p.is_absolute() or p.suffix.lower() != '.xml' or p.stat().st_size > 2_000_000:
        raise ValueError('An absolute local XML path of at most 2 MB is required')
    raw = p.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if not isinstance(expected_sha256, str) or digest != expected_sha256.lower():
        raise ValueError('ESI SHA256 mismatch')
    # Parse only simple UTF-8/ASCII ESI. No DTD, entities, or external schema fetch.
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeError:
        raise ValueError('ESI must be UTF-8/ASCII') from None
    if '\x00' in text or '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise ValueError('DTD/entities/UTF-16 ESI are not accepted')
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError('Malformed ESI XML') from exc
    if root.tag != 'EtherCATInfo' or integer(root.findtext('./Vendor/Id')) != 0x01dd:
        raise ValueError('Not a Delta EtherCATInfo document')
    devices = []
    identities = set()
    for device in root.findall('./Descriptions/Devices/Device'):
        typ = device.find('Type')
        if typ is None:
            raise ValueError('Missing device Type')
        product = integer(typ.get('ProductCode'))
        revision = integer(typ.get('RevisionNo'))
        if (product, revision) in identities:
            raise ValueError('Duplicate device identity')
        identities.add((product, revision))
        if product != 0x902 or (typ.text or '').strip() != 'R2-EC0902':
            raise ValueError('ESI contains unsupported device model')
        pdos = []
        for direction in ('RxPdo', 'TxPdo'):
            for pdo in device.findall(direction):
                pdos.append({'direction': direction, 'index': integer(pdo.findtext('Index')),
                    'attributes': dict(pdo.attrib), 'entries': [
                        {'index': integer(e.findtext('Index')), 'subindex': integer(e.findtext('SubIndex')),
                         'bits': integer(e.findtext('BitLen')), 'name': e.findtext('Name', '')}
                        for e in pdo.findall('Entry')]})
        for direction, index, obj, sm in [('RxPdo',0x1600,0x6200,'2'),('TxPdo',0x1a00,0x6000,'3')]:
            basic = [p for p in pdos if p['direction']==direction and p['index']==index]
            if len(basic)!=1 or basic[0]['attributes'].get('Mandatory')!='1' or basic[0]['attributes'].get('Sm')!=sm:
                raise ValueError('Missing or ambiguous mandatory PDO')
            if [(e['index'],e['subindex'],e['bits']) for e in basic[0]['entries']] != [(obj,s,8) for s in range(1,5)]:
                raise ValueError('Basic PDO differs from supported R2 mapping')
        devices.append({'vendor_id':'0x000001dd','product_code':f'0x{product:08x}',
            'revision':f'0x{revision:08x}', 'supported_revision':revision in KNOWN_REVISIONS,
            'pdos':pdos, 'startup_commands':[{k:n.findtext(k) for k in ('Transition','Index','SubIndex','Data','Comment')}
                for n in device.findall('./Mailbox/CoE/InitCmd')]})
    if not devices or len(devices)>16:
        raise ValueError('Expected 1..16 device descriptions')
    return {'file':str(p),'sha256':digest,'status':'parsed_basic_pdo_verified','xsd_validated':False,
            'devices':devices,'hardware_contacted':False}

def match_identity(esi, observed):
    if not isinstance(observed,dict) or set(observed)!={'vendor_id','product_code','revision','source'}:
        raise ValueError('Observed identity requires vendor_id/product_code/revision/source')
    if not isinstance(observed['source'],str) or not observed['source'].strip():
        raise ValueError('Identity observation source required')
    values = [integer(observed[k]) for k in ('vendor_id','product_code','revision')]
    if values[:2] != [0x1dd,0x902] or values[2] not in KNOWN_REVISIONS:
        raise ValueError('Unsupported observed device identity; no automatic fallback')
    hits = [d for d in esi['devices'] if integer(d['revision'])==values[2]]
    if len(hits)!=1:
        raise ValueError('Observed Revision is absent or ambiguous in this ESI')
    return {'status':'matches_supplied_observation','identity':{k:observed[k] for k in ('vendor_id','product_code','revision')},
            'observation_source':observed['source'],'hardware_contacted':False}
