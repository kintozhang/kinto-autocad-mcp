"""Recover supported sibling-file project snapshots to a new unique project name."""
import json,re
from pathlib import Path
from src.autocad.engineering_archive import verify,restore,digest
from src.autocad.project_plot import project_pages


def recover(archive_path, destination, project_name):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,47}',project_name) or project_name.upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(10)],*[f'LPT{i}' for i in range(10)]}:
        raise ValueError('Safe unique recovery project name required')
    archive=Path(archive_path).resolve(strict=True);data=verify(archive)
    files=archive/'files';wdps=[files/r['path'] for r in data['files'] if Path(r['path']).suffix.lower()=='.wdp']
    if len(wdps)!=1:raise ValueError('Exactly one WDP required')
    wdp=wdps[0]
    if wdp.parent!=files or not wdp.with_suffix('.wdt').is_file():raise ValueError('Sibling WDP/WDT required')
    for line in wdp.read_text(encoding='utf-8-sig').splitlines():
        entry=line.strip()
        if entry.lower().endswith('.dwg') and not entry.startswith(('+','===','*')) and (Path(entry).is_absolute() or Path(entry).name!=entry):
            raise ValueError('Only plain sibling DWG references supported; no path rewrite guessed')
    drawings=project_pages(wdp)
    inventory={r['path'].casefold() for r in data['files']}
    if any(p.name.casefold() not in inventory for p in drawings) or wdp.with_suffix('.wdt').name.casefold() not in inventory:raise ValueError('Missing archived project dependency')
    if project_name.casefold()==wdp.stem.casefold():raise ValueError('Use a different recovery project name to avoid native project cache collision')
    for suffix in ['.wdp','.wdt']:
        if (project_name+suffix).casefold() in inventory:raise ValueError('Recovery name collides with archived files')
    target=Path(destination)
    if not target.is_absolute():raise ValueError('Absolute new recovery directory required')
    restore(archive,target)
    for suffix in ['.wdp','.wdt']:(target/wdp.with_suffix(suffix).name).rename(target/(project_name+suffix))
    result={'success':True,'project_path':str(target/(project_name+'.wdp')),'drawings':[str(target/p.name) for p in drawings],
            'source_archive':str(archive),'production_ready':False,'cad_reopen_verified':False,'automatic_retry':False}
    (target/'recovery.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    return result
