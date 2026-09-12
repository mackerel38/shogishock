"""Operational hooks only: cancellation at safe boundaries and durable telemetry."""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
from pathlib import Path
import signal
import tempfile
import time

STOP_EXIT = 75


class StopRequested(Exception):
    pass


def atomic_json(path: Path, value) -> None:
    """Atomic replacement with file/directory durability and unique temp names."""
    fd, name = tempfile.mkstemp(prefix=path.name+'.', suffix='.tmp', dir=path.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Control:
    def __init__(self, directory=None, run_id=None, parent_pid=None):
        self.directory = Path(directory) if directory else None
        self.run_id = run_id
        self.parent_pid = parent_pid
        self.signalled = False
        self.last_poll = 0.0
        self.progress = {}

    def signal(self, *_):
        # Never raise asynchronously inside ledger writes or a board push/pop.
        self.signalled = True

    def checkpoint(self, *, force=False):
        if self.directory is None:
            return
        if self.signalled:
            raise StopRequested('signal requested a safe stop')
        now = time.monotonic()
        if not force and now - self.last_poll < 0.2:
            return
        self.last_poll = now
        if self.parent_pid is not None and os.getppid() != self.parent_pid:
            raise StopRequested('supervisor exited; stop at safe boundary')
        path = self.directory / 'worker_stop.json'
        if path.exists() and json.loads(path.read_text()).get('run_id') == self.run_id:
            raise StopRequested('stop requested')

    def emit(self, **values):
        if self.directory is not None:
            self.progress.update(values)
            atomic_json(self.directory / 'worker_event.json', self.progress | {
                'run_id': self.run_id, 'updated_at': time.time()})


control = Control()


@contextlib.contextmanager
def script_session(directory: Path):
    """Patched direct invocations also respect the worker lock.

    A supervised child borrows the inherited open-file-description lock. It
    keeps that lock alive if the supervisor dies, until its next safe stop.
    """
    global control
    old_control = control
    inherited = os.environ.get('SHOGISHOCK_WORKER_LOCK_FD')
    stream = None
    handlers = {}
    lock_path = directory / 'worker.lock'
    try:
        if inherited:
            fd = int(inherited)
            a, b = os.fstat(fd), lock_path.stat()
            if (a.st_dev, a.st_ino) != (b.st_dev, b.st_ino):
                raise RuntimeError('wrong inherited worker lock')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if Path(os.environ['SHOGISHOCK_WORKER_DIR']).resolve() != directory.resolve():
                raise RuntimeError('wrong worker directory')
            control = Control(directory, os.environ['SHOGISHOCK_WORKER_RUN_ID'],
                              int(os.environ['SHOGISHOCK_WORKER_PARENT_PID']))
            control.progress['stage'] = os.environ['SHOGISHOCK_WORKER_STAGE']
            for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
                handlers[sig] = signal.signal(sig, control.signal)
        else:
            stream = lock_path.open('a+')
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError('coverage worker/direct stage already running') from exc
        control.checkpoint(force=True)
        yield
    finally:
        for sig, handler in handlers.items():
            signal.signal(sig, handler)
        control = old_control
        if stream:
            stream.close()
