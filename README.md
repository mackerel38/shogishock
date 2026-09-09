# ShogiShock execution infrastructure

This repository provides the engine/position layer and bounded surprise-opening research pilots.
The current checkpoint is [RESEARCH_V3.md](RESEARCH_V3.md): Terashock seeds, human reach sampling,
held-out Human Policy baselines, and a small E2E. Conditional capture calibration remains inadequate;
do not proceed to a large scan. The older commands below document historical pilots, not the next research step.

## Pass research pilot (existing environment)

Do not rerun setup on an already provisioned machine. See [RESEARCH.md](RESEARCH.md) for the research contract, data limitations, and resume semantics.

```bash
.venv/bin/surprise scan --config config/pass_pilot.yaml
.venv/bin/surprise deep --config config/pass_pilot.yaml --per-side 15 --nodes 100000 1000000
```

Open `reports/pass_pilot/report_sente.html` or `reports/pass_pilot/report_gote.html`.
All legal moves are retained, raw engine scores remain sente-perspective, and relative pass statistics are calculated per parent position. The included seeds are authored opening scaffolds, **not human game frequencies**.

## Quick start

```bash
./scripts/setup.sh
source .venv/bin/activate
surprise engine-test
surprise benchmark
pytest
```

The setup detects no CPU features itself; the selected build is explicitly `TARGET_CPU=SSE42`, which is compatible with the current Intel Pentium Silver N6000. The engine reads `assets/eval/nn.bin` through the `engines/yaneuraou/eval` symlink.

## Python API

```python
from surprise.engine import Engine
from surprise.position import Position

with Engine.from_config() as engine:
    result = engine.evaluate(Position.startpos(), nodes=10_000)
    print(result.score.score_type, result.score.score_cp, result.pv)
    virtual = Position.startpos().apply_move("7g7f").virtual_pass("sente")
```

All returned scores have `score.perspective == "sente"`; `cp` and `mate` remain separate. `virtual_pass` never changes board or hands and rejects a position where the side to move is in check.

## ShogiHome export and playback

Export a small review set or one candidate as UTF-8 branching KIF:

```bash
.venv/bin/surprise export-shogihome --input reports/pass_pilot --output exports/shogihome --limit 10
.venv/bin/surprise export-shogihome --input reports/pass_pilot \
  --candidate-id eb5bc2ef917ec96fe217_9g9f --output exports/shogihome
```

ShogiHome v1.29.0 Linux AppImage is installed locally at `tools/shogihome/ShogiHome-1.29.0.AppImage`.
Launch it with `scripts/shogihome.sh`, then open a generated `.kif` and select its candidate/PV/variation lines. See [SHOGIHOME.md](SHOGIHOME.md) and [exports/README.md](exports/README.md).

## Reproduction on Vast.ai

Select an x86_64 instance whose CPU supports SSE4.2, with at least 4 GB RAM and enough persistent storage for the repository, cache, and result files. CPU price and sustained nodes/sec matter more than GPU for this workload. Then run:

```bash
git clone <repository-url> shogishock
cd shogishock
./scripts/setup.sh
surprise engine-test
surprise benchmark
```

Persist `data/` between instance runs. The Docker path is equivalent when Docker is available:

```bash
docker build -t shogishock .
docker run --rm -v "$PWD/data:/workspace/data" shogishock engine-test
```

`Engine` writes completed requests immediately to SQLite. A worker can resume by reusing the same cache file; interrupting a batch between requests does not lose completed requests.
