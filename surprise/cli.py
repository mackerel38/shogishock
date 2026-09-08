from __future__ import annotations
import argparse, json, os, platform, subprocess, sys, time
from pathlib import Path
from .engine import Engine
from .position import Position

def main() -> None:
    p = argparse.ArgumentParser(prog="surprise")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("setup"); sub.add_parser("engine-test"); sub.add_parser("benchmark")
    scan = sub.add_parser("scan", help="Resume all-legal-move pass pilot and render reports")
    scan.add_argument("--config", default="config/default.yaml")
    scan.add_argument("--max-positions", type=int)
    scan.add_argument("--report-only", action="store_true")
    deep = sub.add_parser("deep", help="Deepen raw/relative top candidates, separately by side")
    deep.add_argument("--config", default="config/default.yaml")
    deep.add_argument("--per-side", type=int, default=15)
    deep.add_argument("--nodes", type=int, nargs="+", default=[100000, 1000000])
    audit = sub.add_parser("audit", help="Evaluate every legal reply to stratified examples; no human probabilities")
    audit.add_argument("--config", default="config/pass_pilot.yaml")
    audit.add_argument("--nodes", type=int, default=100000)
    args = p.parse_args()
    if args.command == "setup":
        subprocess.run(["bash", "scripts/setup.sh"], check=True)
    elif args.command == "engine-test": engine_test()
    elif args.command == "scan":
        from .research import run_scan
        run_scan(args.config, args.max_positions, args.report_only)
    elif args.command == "deep":
        from .research import run_deep
        run_deep(args.config, args.per_side, args.nodes)
    elif args.command == "audit":
        from .audit import run_audit
        run_audit(args.config, args.nodes)
    else: benchmark()

def engine_test() -> None:
    with Engine.from_config() as e:
        r = e.search(Position.startpos(), 10000, 2)
        print(json.dumps([x.__dict__ | {"score": x.score.__dict__} for x in r], ensure_ascii=False, indent=2))
        print("[OK] USI handshake / cp parsing / PV parsing / MultiPV or fallback")

def benchmark() -> None:
    with Engine.from_config() as e:
        if e.cache:
            e.cache.close()
            e.cache = None
        start = time.perf_counter(); r = e.evaluate(Position.startpos(), 100000)
        elapsed = time.perf_counter() - start
        print(json.dumps({"nodes": r.nodes, "elapsed_sec": elapsed, "nodes_per_sec": (r.nodes or 0)/elapsed,
                          "threads": e.threads, "cpu": platform.processor() or platform.machine()}, indent=2))


if __name__ == "__main__":
    main()
