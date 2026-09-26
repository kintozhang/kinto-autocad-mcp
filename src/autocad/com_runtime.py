"""Bounded retries for explicitly read-only COM calls; never retry writes."""
from pathlib import Path
import logging
import time

log = logging.getLogger(__name__)
BUSY = {0x80010001, 0x8001010A, 0x8001010B}
DISCONNECTED = {0x80010108, 0x80010007, 0x80010012, 0x800706BA}


class ComBusyError(RuntimeError):
    pass


def hresult(exc):
    value = getattr(exc, 'hresult', None)
    if value is None and exc.args and isinstance(exc.args[0], int):
        value = exc.args[0]
    return value & 0xffffffff if isinstance(value, int) else None


def read_call(read, *, attempts=8, interval=.15, label='COM read', events=None):
    """Callback MUST be read-only, including method lookup rather than invocation."""
    for attempt in range(attempts):
        try:
            value = read()
            if attempt:
                event = {'operation': label, 'retries': attempt, 'status': 'read_recovered'}
                log.info('%s', event)
                if events is not None: events.append(event)
            return value
        except Exception as exc:
            if hresult(exc) not in BUSY:
                raise
            if attempt + 1 == attempts:
                raise ComBusyError(f'{label}: AutoCAD remains busy; no write retried') from exc
            time.sleep(interval)


def wait_for_document(app, expected, *, timeout=8., interval=.15, stable_samples=2):
    """Require consecutive quiescent samples of the exact active saved path."""
    expected = Path(expected).resolve()
    deadline = time.monotonic() + timeout
    stable = 0
    while True:
        try:
            doc = app.ActiveDocument
            if Path(doc.FullName).resolve() != expected:
                raise ValueError('Active drawing changed while waiting; no write submitted')
            idle = bool(app.GetAcadState().IsQuiescent) and int(doc.GetVariable('CMDACTIVE')) == 0
            stable = stable + 1 if idle else 0
            if stable >= stable_samples:
                return doc
        except Exception as exc:
            # pywin32 can transiently expose an untyped document after Open.
            # Only this known-property readiness probe retries AttributeError.
            if hresult(exc) not in BUSY and not isinstance(exc, AttributeError):
                raise
            stable = 0
        if time.monotonic() >= deadline:
            raise ComBusyError('Target drawing did not become stably idle; no write submitted')
        time.sleep(interval)


def lookup_document_open(app, *, attempts=8):
    """Fresh metadata lookup only; caller invokes returned Open exactly once."""
    for attempt in range(attempts):
        try:
            return read_call(lambda: app.Documents.Open, label="Documents.Open method lookup")
        except AttributeError:
            if attempt + 1 == attempts:
                raise
            time.sleep(.15)


def document_full_name(app, *, attempts=8, interval=.15):
    """Retry only the known active-document metadata probe; never a write."""
    for attempt in range(attempts):
        try:
            return read_call(lambda: app.ActiveDocument.FullName,
                             attempts=1, label="ActiveDocument.FullName")
        except (AttributeError, ComBusyError) as exc:
            if attempt + 1 == attempts:
                raise ComBusyError(
                    'AutoCAD active-document metadata unavailable after bounded read retries. '
                    'Check the CAD window, remote session and modal dialogs, then verify the target drawing. '
                    'This probe did not switch documents or retry writes.'
                ) from exc
            time.sleep(interval)


def create_document_from_template(app, template, destination, *, timeout=12., interval=.15):
    """Submit Add/SaveAs once; reacquire the new document after COM metadata settles.

    Caller must hold the CAD session gate. Any exception after Add requires state
    inspection; it is never permission to replay this function.
    """
    template, destination = Path(template).resolve(), Path(destination).resolve()
    if not template.is_file() or template.suffix.lower() != '.dwt':
        raise ValueError('Existing DWT template required')
    if destination.exists() or destination.suffix.lower() != '.dwg' or not destination.parent.is_dir():
        raise ValueError('New DWG path in an existing directory required')
    before = set(read_call(lambda: [d.Name for d in app.Documents]))
    deadline = time.monotonic() + timeout

    def probe(callback):
        while True:
            try:
                return callback()
            except Exception as exc:
                if hresult(exc) not in BUSY and not isinstance(exc, AttributeError) and not (isinstance(exc, TypeError) and 'does not support enumeration' in str(exc)):
                    raise
                if time.monotonic() >= deadline:
                    raise ComBusyError('New document metadata unavailable; inspect state, do not replay') from exc
                time.sleep(interval)

    add = probe(lambda: app.Documents.Add)
    add(str(template))  # Ignore potentially untyped return proxy; never repeat Add.
    selected = None
    stable = 0
    while time.monotonic() < deadline:
        names = probe(lambda: [d.Name for d in app.Documents])
        candidates = set(names) - before
        if len(candidates) > 1:
            raise RuntimeError('Multiple new documents; stop without saving')
        if candidates:
            name = next(iter(candidates))
            if selected is not None and selected != name:
                raise RuntimeError('New document identity changed')
            selected = name
            doc = probe(lambda: app.ActiveDocument)
            if probe(lambda: doc.Name) != selected:
                raise RuntimeError('New document is not active; stop without saving')
            idle = probe(lambda: bool(app.GetAcadState().IsQuiescent) and int(doc.GetVariable('CMDACTIVE')) == 0)
            stable = stable + 1 if idle else 0
            if stable >= 2:
                def lookup_save():
                    current = app.ActiveDocument
                    if current.Name != selected:
                        raise RuntimeError('Active document changed before SaveAs')
                    return current.SaveAs
                save = probe(lookup_save)
                if destination.exists():
                    raise ValueError('Destination appeared before SaveAs')
                save(str(destination), 64)  # Never repeat a submitted write.
                ready = wait_for_document(app, destination, timeout=timeout, interval=interval)
                if not read_call(lambda: bool(ready.Saved)) or not destination.is_file():
                    raise RuntimeError('New document save not confirmed')
                return ready
        time.sleep(interval)
    raise ComBusyError('New document did not become idle; inspect state, do not replay')


def document_inventory(app, *, attempts=12, interval=.15):
    """Stable read-only inventory. Empty FullName is never a document identity.

    Name and HWND identify this snapshot only, not a durable authorization to close.
    Callers must revalidate before any operation; this function performs no writes.
    """
    previous = None
    for attempt in range(attempts):
        try:
            hwnd = int(app.HWND)
            rows = []
            for doc in app.Documents:
                name, path = str(doc.Name), str(doc.FullName)
                if not name:
                    raise ValueError('Document has no usable name')
                rows.append({'name': name, 'path': path, 'saved': bool(doc.Saved),
                             'identity': {'instance_hwnd': hwnd, 'name': name, 'path': path}})
            keys = [('saved', str(Path(r['path']).resolve()).casefold()) if r['path'] else ('unsaved', r['name'].casefold()) for r in rows]
            if len(keys) != len(set(keys)):
                raise ValueError('Ambiguous document identities')
            rows.sort(key=lambda r: (r['path'].casefold(), r['name'].casefold()))
            if int(app.HWND) != hwnd:
                raise ValueError('CAD instance changed during inventory')
            if rows == previous:
                return rows
            previous = rows
        except Exception as exc:
            if hresult(exc) not in BUSY and not isinstance(exc, AttributeError) and not (isinstance(exc, TypeError) and 'does not support enumeration' in str(exc)):
                raise
            previous = None
        if attempt + 1 < attempts:
            time.sleep(interval)
    raise ComBusyError('Document inventory did not stabilize; no writes submitted')
