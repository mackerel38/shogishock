"""Standalone supervisor for the frozen coverage-v2 contract, not a researcher."""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

from .worker_control import STOP_EXIT, atomic_json

REPORT = Path('reports/trap_tree_coverage_v2')
SOURCE_FILES = (
    'surprise/research_worker.py', 'surprise/worker_control.py',
    'scripts/shogishock_worker.py', 'scripts/shogishock-worker',
    str(REPORT/'experiment.py'), str(REPORT/'prove_mate.py'),
)
INPUT_FILES = SOURCE_FILES + tuple(str(REPORT/name) for name in (
    'PLAN.md', 'PROOF_PROTOCOL.md', 'LUNA_WORKER_TASK.md', 'candidate_coverage.json',
    'reply_coverage.json', 'mate_proof_hints.json',
)) + (
    'config/default.yaml', 'pyproject.toml',
    'surprise/engine.py', 'surprise/position.py', 'surprise/obvious.py',
    'surprise/research.py', 'reports/trap_tree_benchmark/explore.py',
    'reports/tactical_falsification_v2/experiment.py',
    'reports/tactical_falsification/prototype.py',
)
ARTIFACTS = ('engine_evidence.json', 'deep_checks.json', 'mate_proof_checks.json',
             'mate_certificate_3d3e.json', 'mate_certificate_3d2d.json')
STAGE_ARTIFACTS = {'deep': ARTIFACTS[:2], 'proof': ARTIFACTS[2:]}
STAGES = (
    ('deep', ('.venv/bin/python', str(REPORT/'experiment.py'), 'deep')),
    ('proof', ('.venv/bin/python', str(REPORT/'prove_mate.py'))),
)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def object_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def read_json(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def process_identity(pid):
    try:
        # starttime disambiguates reused PIDs; flock remains the real authority.
        fields=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
        return fields[19]
    except (OSError, IndexError):
        return None


def fingerprints(root):
    """Match Engine's path/hash rules without starting the engine."""
    import yaml
    config = yaml.safe_load((root/'config/default.yaml').read_text())
    settings = config['engine']
    binary = (root/settings['path']).resolve()
    eval_dir = Path(settings.get('eval_dir') or 'eval')
    if not eval_dir.is_absolute():
        eval_dir = binary.parent/eval_dir
    nnue = {str(p.resolve()): digest(p) for p in sorted(eval_dir.glob('*.bin'))}
    if not nnue or not os.access(binary, os.X_OK):
        raise ValueError('existing engine / NNUE unavailable; do not rebuild')
    return {
        'files': {name: digest(root/name) for name in INPUT_FILES},
        'engine': {'path': str(binary), 'binary_sha256': digest(binary),
                   'eval_sha256': nnue, 'threads': settings.get('threads', 1),
                   'hash_mb': settings.get('hash_mb', 256),
                   'options': settings.get('options') or {}},
        'runtime': {'python': sys.version, 'python_executable': str(Path(sys.executable).resolve()),
                    **{name: importlib.metadata.version(name) for name in ('python-shogi', 'PyYAML')}},
    }


def verify_contract(root):
    contract = read_json(root/REPORT/'worker_contract.json')
    if contract is None or str(root) != contract['execution_root']:
        raise ValueError('wrong execution root / missing worker contract (publication clone forbidden)')
    current = fingerprints(root)
    if current != contract['input_fingerprints']:
        raise ValueError('incompatible inputs: frozen worker contract fingerprint mismatch')
    # Existing ledger is adopted, not recalculated. These identities predate worker.
    ledger = read_json(root/REPORT/'engine_evidence.json')
    if ledger is None:
        raise ValueError('existing evidence ledger missing; refusing fresh research run')
    for name in ('binary_sha256', 'eval_sha256', 'threads', 'hash_mb'):
        if ledger.get(name) != current['engine'][name]:
            raise ValueError('incompatible existing engine ledger: '+name)
    if ledger.get('plan_sha256') != current['files'][str(REPORT/'PLAN.md')]:
        raise ValueError('incompatible existing ledger PLAN')
    # Script-owned read-only operational validation, before starting any engine.
    spec = importlib.util.spec_from_file_location('_worker_proof_preflight', root/REPORT/'prove_mate.py')
    proof = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(proof)
    proof.e.deep_progress()
    hints = read_json(root/REPORT/'mate_proof_hints.json')
    proof.completed_output(hints['source_sha256'], len(hints['hints']))
    return current


def legacy_processes(root, proc=Path('/proc')):
    """Inspect only matching stage commands; no broad process termination."""
    if (proc/'1/comm').read_text().strip() in ('codex', 'bwrap'):
        raise ValueError('limited PID namespace: run worker from the normal host terminal')
    targets = {(root/REPORT/name).resolve() for name in ('experiment.py', 'prove_mate.py')}
    found = []
    for p in proc.iterdir():
        if not p.name.isdigit() or int(p.name) == os.getpid():
            continue
        try:
            args = (p/'cmdline').read_bytes().decode(errors='replace').strip('\0').split('\0')
            names = [a for a in args if Path(a).name in ('experiment.py', 'prove_mate.py')]
            if not names:
                continue
            try:
                cwd = (p/'cwd').resolve(strict=True)
            except (OSError, RuntimeError):
                # Cannot disambiguate a matching command: fail closed.
                found.append({'pid': int(p.name), 'command': args, 'cwd': 'unreadable'})
                continue
            if any((cwd/name).resolve() in targets for name in names):
                found.append({'pid': int(p.name), 'command': args, 'cwd': str(cwd)})
        except FileNotFoundError:
            continue  # Process exited while enumerating.
        except PermissionError as exc:
            raise ValueError('cannot inspect process table safely; check /proc permissions') from exc
    return found


@contextlib.contextmanager
def exclusive_lock(path):
    with path.open('a+') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('second run refused: coverage worker/direct stage holds flock') from exc
        yield stream
        # Do not LOCK_UN: a surviving child may still share this description.


def lock_held(path):
    try:
        with exclusive_lock(path):
            return False
    except ValueError:
        return True


class Worker:
    """Injectable runner for short fake-subprocess tests. Public CLI is fixed."""
    def __init__(self, root, *, stages=STAGES, check=verify_contract, conflicts=legacy_processes):
        self.root = Path(root).resolve()
        self.directory = self.root/REPORT
        self.stages = stages
        self.check = check
        self.conflicts = conflicts
        self.state_path = self.directory/'worker_state.json'
        self.lock_path = self.directory/'worker.lock'
        self.state = None
        self.signalled = False

    def signal(self, *_):
        self.signalled = True

    def outputs(self, names=ARTIFACTS):
        return {name: digest(self.directory/name) for name in names if (self.directory/name).is_file()}

    def persist(self):
        self.state['updated_at'] = time.time()
        self.state['elapsed'] = self.base_elapsed + time.monotonic()-self.session_started
        atomic_json(self.state_path, self.state)

    def request_stop(self):
        atomic_json(self.directory/'worker_stop.json', {'run_id': self.state['run_id'], 'at': time.time()})
        self.state['stop_requested'] = True

    def stopping(self):
        stop = read_json(self.directory/'worker_stop.json', {})
        if self.signalled or stop.get('run_id') == self.state['run_id']:
            if not self.state['stop_requested']:
                self.request_stop()
            return True
        return False

    def event(self):
        event = read_json(self.directory/'worker_event.json', {})
        if event.get('run_id') == self.state['run_id'] and event.get('stage') == self.state['stage']:
            for key in ('current_case', 'current_position', 'current_budget', 'completed_cases',
                        'total_cases', 'completed_requests', 'cache_hits', 'proof_visited_states'):
                if key in event:
                    self.state[key] = event[key]

    def finish(self, status, error=None):
        self.state.update(status=status, last_error=error, finished_at=time.time())
        self.persist()
        manifest = {key: self.state[key] for key in (
            'started_at', 'finished_at', 'stages', 'input_fingerprints', 'worker_revision',
            'interrupted_count', 'resumed_count', 'last_error', 'elapsed')}
        manifest.update(execution_status=status,
                        stage_exit_codes={k: v.get('exit_code') for k, v in self.state['stages'].items()},
                        result_artifacts=self.outputs(), research_verdict=None, requires_astra_review=True,
                        contract={'post_30_continuation': 'only tactical proof continuation',
                                  'production_activation': False, 'automatic_publication': False})
        atomic_json(self.directory/'worker_manifest.json', manifest)

    def run(self, resume=False):
        if Path.cwd().resolve() != self.root:
            raise ValueError('run from the real project root')
        # Cheap root check is followed by full hashes under the single-writer lock.
        if not self.directory.is_dir():
            raise ValueError('missing coverage-v2 project directory')
        with exclusive_lock(self.lock_path) as lock:
            competing = self.conflicts(self.root)
            if competing:
                raise ValueError('legacy process conflict; no stage started: '+json.dumps(competing))
            current = self.check(self.root)
            previous = read_json(self.state_path)
            if previous and previous['input_fingerprints'] != current:
                raise ValueError('incompatible inputs: resume fingerprint mismatch')
            if previous:
                for name, stage in previous['stages'].items():
                    if stage['status'] == 'completed' and stage['artifacts'] != self.outputs(STAGE_ARTIFACTS[name]):
                        raise ValueError('completed stage artifacts changed: '+name)
                if previous['status'] == 'completed':
                    print('state: completed\nresearch verdict: NOT EVALUATED\nnext action: resume Astra and inspect artifacts')
                    return 0
                if not resume:
                    raise ValueError('unfinished worker state exists; use resume')
            elif resume:
                raise ValueError('no worker state; use run to adopt existing scientific progress')
            self.state = previous or {
                'started_at': time.time(), 'stages': {name: {'status': 'pending'} for name, _ in self.stages},
                'interrupted_count': 0, 'resumed_count': 0, 'elapsed': 0.0,
                'completed_requests': 0, 'cache_hits': 0,
            }
            if previous:
                self.state['resumed_count'] += 1
                if self.state['status'] in ('running', 'stopping'):
                    self.state['interrupted_count'] += 1  # unclean supervisor death
            self.state.update(status='running', stage=None, current_case=None, current_budget=None,
                              completed_cases=0, total_cases=0, last_error=None, stop_requested=False,
                              pid=os.getpid(), run_id=uuid.uuid4().hex, input_fingerprints=current,
                              process_identity=process_identity(os.getpid()),
                              worker_revision=object_digest({k: current['files'][k] for k in SOURCE_FILES
                                                             if k in current['files']}),
                              research_verdict=None, requires_astra_review=True)
            self.base_elapsed = self.state['elapsed']
            self.session_started = time.monotonic()
            self.persist()
            handlers = {sig: signal.signal(sig, self.signal) for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
            child = None
            try:
                with (self.directory/'worker.log').open('a', buffering=1) as log:
                    for name, command in self.stages:
                        if self.state['stages'][name]['status'] == 'completed':
                            continue
                        if self.stopping():
                            break
                        # Check again between stages: editing contract files during a run is forbidden.
                        if self.check(self.root) != current:
                            raise ValueError('incompatible inputs changed during execution')
                        self.state.update(stage=name, current_case=None, current_budget=None,
                                          completed_cases=0, total_cases=6 if name=='deep' else 2)
                        self.state['stages'][name].update(status='running', started_at=time.time())
                        atomic_json(self.directory/'worker_event.json', {'run_id': self.state['run_id'], 'stage': name})
                        env = os.environ | {
                            'SHOGISHOCK_WORKER_DIR': str(self.directory),
                            'SHOGISHOCK_WORKER_RUN_ID': self.state['run_id'],
                            'SHOGISHOCK_WORKER_PARENT_PID': str(os.getpid()),
                            'SHOGISHOCK_WORKER_LOCK_FD': str(lock.fileno()),
                            'SHOGISHOCK_WORKER_STAGE': name,
                            'PYTHONUNBUFFERED': '1',
                        }
                        log.write(f'\n{time.time()} start {name}: {list(command)!r}\n')
                        log.flush()
                        os.fsync(log.fileno())
                        # Own session: terminal Ctrl-C does not directly interrupt YaneuraOu.
                        child = subprocess.Popen(command, cwd=self.root, env=env, stdout=log,
                                                 stderr=subprocess.STDOUT, start_new_session=True,
                                                 pass_fds=(lock.fileno(),))
                        self.state['child_pid'] = child.pid
                        self.persist()
                        while child.poll() is None:
                            if self.stopping():
                                self.state['status'] = 'stopping'
                            self.event()
                            self.persist()
                            time.sleep(0.5)
                        code = child.wait()
                        child = None
                        self.state['child_pid'] = None
                        self.event()
                        stage = self.state['stages'][name]
                        stage.update(exit_code=code, finished_at=time.time())
                        if code == STOP_EXIT:
                            stage['status'] = 'interrupted'
                            self.state['stop_requested'] = True
                            break
                        if code != 0:
                            stage['status'] = 'failed'
                            raise RuntimeError(f'{name} child failed with exit code {code}; see worker.log')
                        if self.check(self.root) != current:
                            raise ValueError('incompatible inputs changed during stage; do not mix evidence')
                        stage.update(status='completed', artifacts=self.outputs(STAGE_ARTIFACTS[name]))
                        self.persist()
                    if all(s['status']=='completed' for s in self.state['stages'].values()):
                        self.finish('completed')
                        print('state: completed\nresearch verdict: NOT EVALUATED\nnext action: resume Astra and inspect artifacts')
                        return 0
                    self.state['interrupted_count'] += 1
                    self.finish('stopped')
                    print('state: stopped; saved evidence retained; use resume')
                    return STOP_EXIT
            except Exception as exc:
                if child is not None and child.poll() is None:
                    # No kill: inherited flock remains held; child stops on parent death
                    # or the request at its next safe boundary.
                    self.request_stop()
                self.finish('failed', str(exc))
                raise
            finally:
                for sig, handler in handlers.items():
                    signal.signal(sig, handler)

    def status(self):
        state = read_json(self.state_path)
        held = lock_held(self.lock_path)
        if not state:
            print('state: '+('external/direct stage running (lock held)' if held else 'not started'))
            return
        effective = state['status']
        if held and process_identity(state.get('pid')) != state.get('process_identity'):
            effective = 'supervisor absent; surviving/external stage holds lock (wait for safe boundary)'
        elif held and effective not in ('running','stopping'):
            effective = 'lock held by surviving/external stage; do not start another run'
        elif not held and effective in ('running','stopping'):
            effective = 'interrupted (no lock holder); use resume'
        elapsed = int(state.get('elapsed',0))
        print(f"state: {effective}\nstage: {state.get('stage')}\ncase: {state.get('current_case')}\n"
              f"budget: {state.get('current_budget')}\nelapsed: {elapsed//3600:02}:{elapsed//60%60:02}:{elapsed%60:02}\n"
              f"completed: {state.get('completed_cases',0)}/{state.get('total_cases',0)} stage cases/groups\n"
              f"ledger requests: {state.get('completed_requests',0)}\ncache hits: {state.get('cache_hits',0)}\n"
              f"stop requested: {state.get('stop_requested',False)}\nlast error: {state.get('last_error') or 'none'}\n"
              'research verdict: NOT EVALUATED')
        if state['status']=='completed' and not held:
            print('next action: resume Astra and inspect artifacts')

    def stop(self):
        state = read_json(self.state_path)
        if not lock_held(self.lock_path):
            print('no active worker; saved evidence retained')
            return
        if not state or state['status']=='completed':
            raise ValueError('lock belongs to a direct/external stage; no worker stop target')
        # run_id scopes the request; no PID killing and no state writer race.
        atomic_json(self.directory/'worker_stop.json', {'run_id': state['run_id'], 'at': time.time()})
        print('safe stop requested; current query may finish first (no timeout/kill)')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('run','resume','status','stop'))
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    worker = Worker(root)
    try:
        if args.command in ('run','resume'):
            return worker.run(resume=args.command=='resume')
        getattr(worker,args.command)()
        return 0
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print('worker refused/failed: '+str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
