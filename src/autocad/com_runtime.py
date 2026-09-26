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
        except (AttributeError, ComBusyError):
            if attempt + 1 == attempts:
                raise
            time.sleep(interval)
