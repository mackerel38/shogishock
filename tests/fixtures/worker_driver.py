"""Test-only dependency injection. Not an alternative research CLI."""
from pathlib import Path
import sys
from surprise.research_worker import Worker, digest

root = Path.cwd()
fixture = Path(__file__).with_name('worker_stage.py')
stages = tuple((name, (sys.executable, str(fixture), name)) for name in ('deep','proof'))
worker = Worker(root, stages=stages,
                check=lambda root: {'files': {}, 'fixture': digest(root/'input.txt')},
                conflicts=lambda root: [])
try:
    if sys.argv[1] in ('run','resume'):
        raise SystemExit(worker.run(resume=sys.argv[1]=='resume'))
    getattr(worker,sys.argv[1])()
except (ValueError,RuntimeError) as ex:
    print(str(ex),file=sys.stderr)
    raise SystemExit(1)
