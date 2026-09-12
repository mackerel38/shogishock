"""Short fake stage, never imports or starts the shogi engine."""
import json
from pathlib import Path
import sys
import time

from surprise import worker_control as wc

directory = Path.cwd()/'reports/trap_tree_coverage_v2'
stage = sys.argv[1]
try:
    with wc.script_session(directory):
        if (directory/(stage+'.fail')).exists():
            raise SystemExit(9)
        path = directory/('deep_checks.json' if stage=='deep' else 'mate_proof_checks.json')
        saved = json.loads(path.read_text()) if path.exists() else {'done': [], 'decision': 'INCONCLUSIVE'}
        wc.control.emit(current_case=stage, total_cases=2, completed_cases=len(saved['done']))
        for request in range(2):
            if request in saved['done']:
                continue
            wc.control.checkpoint(force=True)
            wc.atomic_json(directory/'query_started.json', {'stage': stage, 'request': request})
            # An in-flight engine call ignores cancellation until it is saved.
            while (directory/'hold_query').exists():
                time.sleep(0.01)
            time.sleep(0.02)
            saved['done'].append(request)
            wc.atomic_json(path, saved)
            wc.control.emit(completed_cases=len(saved['done']), completed_requests=len(saved['done']),
                            current_budget=123, cache_hits=0)
            wc.control.checkpoint(force=True)
except wc.StopRequested:
    raise SystemExit(wc.STOP_EXIT)
