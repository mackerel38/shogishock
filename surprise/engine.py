from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import shogi

from .position import Position

CACHE_SCHEMA_VERSION = 5


@dataclass(frozen=True)
class Score:
    score_type: str
    score_cp: int | None = None
    mate_distance: int | None = None
    perspective: str = "sente"
    bound: str = "exact"


@dataclass
class EngineResult:
    score: Score
    best_move: str | None = None
    pv: list[str] = field(default_factory=list)
    depth: int | None = None
    nodes: int | None = None
    time_ms: int | None = None
    raw_info: list[str] = field(default_factory=list)
    reported_best_move: str | None = None


class Engine:
    def __init__(self, path: str, eval_dir: str | None = None, threads: int = 1,
                 hash_mb: int = 256, options: dict[str, Any] | None = None,
                 cache_path: str | None = None):
        self.path = str(Path(path).resolve())
        self.eval_dir = eval_dir
        self.threads = threads
        self.hash_mb = hash_mb
        self.options = options or {}
        # Fingerprint once per process; cache identity must include NNUE contents.
        self.binary_sha256 = hashlib.sha256(Path(self.path).read_bytes()).hexdigest()
        eval_path = Path(eval_dir or "eval")
        if not eval_path.is_absolute():
            eval_path = Path(self.path).parent / eval_path
        self.eval_sha256 = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sorted(eval_path.glob("*.bin"))}
        self.cache = Cache(cache_path) if cache_path else None
        self._proc: subprocess.Popen[str] | None = None
        self._usi_lines: list[str] = []
        self._start()

    @classmethod
    def from_config(cls, path: str = "config/default.yaml") -> "Engine":
        import yaml
        with open(path, encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh)
        e = cfg["engine"]
        c = cfg.get("cache", {}).get("path")
        return cls(e["path"], e.get("eval_dir"), e.get("threads", 1),
                   e.get("hash_mb", 256), e.get("options"), c)

    def _start(self) -> None:
        if not os.path.isfile(self.path) or not os.access(self.path, os.X_OK):
            raise FileNotFoundError(f"engine is not executable: {self.path}")
        self._proc = subprocess.Popen([self.path], stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      text=True, bufsize=1)
        self._send("usi")
        self._read_until("usiok")
        self._send(f"setoption name Threads value {self.threads}")
        self._send(f"setoption name USI_Hash value {self.hash_mb}")
        if self.eval_dir:
            self._send(f"setoption name EvalDir value {self.eval_dir}")
        for name, value in self.options.items():
            self._send(f"setoption name {name} value {value}")
        self._send("isready")
        self._read_until("readyok")

    def _send(self, line: str) -> None:
        assert self._proc and self._proc.stdin
        self._proc.stdin.write(line + "\n")
        self._proc.stdin.flush()

    def _read_until(self, marker: str) -> list[str]:
        assert self._proc and self._proc.stdout
        lines = []
        for line in self._proc.stdout:
            line = line.rstrip("\n")
            lines.append(line)
            if line == marker:
                return lines
        raise RuntimeError(f"engine exited while waiting for {marker!r}: {lines[-5:]}")

    def search(self, position: Position, nodes: int, multipv: int = 1) -> list[EngineResult]:
        if nodes <= 0 or multipv <= 0:
            raise ValueError("nodes and multipv must be positive")
        key = self._key(position, "search", nodes, multipv)
        if self.cache:
            cached = self.cache.get(key)
            if cached is not None:
                return [self._decode_result(x) for x in cached]
        self._send("stop")
        # This YaneuraOu implements usinewgame as a no-op. isready clears TT
        # and search state; otherwise a cached request depends on prior queries.
        self._send("isready")
        self._read_until("readyok")
        self._send("usinewgame")
        self._send(f"position sfen {position.sfen}")
        self._send(f"setoption name MultiPV value {multipv}")
        self._send(f"go nodes {int(nodes)}")
        lines = self._read_until_prefix("bestmove")
        results = _parse_search(lines)
        results = [_normalize_perspective(x, position.turn) for x in results]
        if self.cache:
            self.cache.put(key, [self._encode_result(x) for x in results])
        return results

    def _read_until_prefix(self, prefix: str) -> list[str]:
        assert self._proc and self._proc.stdout
        lines = []
        for line in self._proc.stdout:
            line = line.rstrip("\n")
            lines.append(line)
            if line.startswith(prefix + " ") or line == prefix:
                return lines
        raise RuntimeError("engine exited before bestmove")

    def evaluate(self, position: Position, nodes: int) -> EngineResult:
        return self.search(position, nodes, 1)[0]

    def get_best_move(self, position: Position, nodes: int) -> str | None:
        return self.evaluate(position, nodes).best_move

    def evaluate_after_move(self, position: Position, move: str, nodes: int) -> EngineResult:
        return self.evaluate(position.apply_move(move), nodes)

    def close(self) -> None:
        if self._proc and self._proc.poll() is None:
            try:
                self._send("quit")
                self._proc.wait(timeout=3)
            except (BrokenPipeError, subprocess.TimeoutExpired):
                self._proc.kill()
        if self.cache:
            self.cache.close()

    def __enter__(self) -> "Engine": return self
    def __exit__(self, *_: object) -> None: self.close()

    def _key(self, p: Position, kind: str, nodes: int, multipv: int) -> str:
        payload = {"schema": CACHE_SCHEMA_VERSION, "sfen": p.sfen, "kind": kind, "nodes": nodes, "multipv": multipv,
                   "engine": self.path, "binary_sha256": self.binary_sha256, "eval_dir": self.eval_dir,
                   "eval_sha256": self.eval_sha256,
                   "threads": self.threads, "hash_mb": self.hash_mb, "options": self.options}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def _encode_result(r: EngineResult) -> dict[str, Any]: return r.__dict__ | {"score": r.score.__dict__}
    @staticmethod
    def _decode_result(x: dict[str, Any]) -> EngineResult:
        return EngineResult(score=Score(**x["score"]), **{k: v for k, v in x.items() if k != "score"})


class Cache:
    def __init__(self, path: str):
        import sqlite3
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS engine_cache (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self.db.commit()
    def get(self, key: str) -> Any:
        row = self.db.execute("SELECT value FROM engine_cache WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None
    def put(self, key: str, value: Any) -> None:
        self.db.execute("INSERT OR REPLACE INTO engine_cache VALUES (?,?)", (key, json.dumps(value)))
        self.db.commit()
    def close(self) -> None: self.db.close()


def _parse_score(tokens: list[str]) -> Score:
    if tokens[0] == "cp": return Score("cp", score_cp=int(tokens[1]))
    if tokens[0] == "mate": return Score("mate", mate_distance=int(tokens[1]))
    raise ValueError(f"unknown score: {tokens}")


def _parse_search(lines: list[str]) -> list[EngineResult]:
    latest: dict[int, EngineResult] = {}
    exact: dict[int, EngineResult] = {}
    for line in lines:
        if not line.startswith("info ") or " score " not in line: continue
        t = line.split(); multipv = int(t[t.index("multipv") + 1]) if "multipv" in t else 1
        i = t.index("score") + 1; score = _parse_score(t[i:i+2])
        bound = "upperbound" if "upperbound" in t else "lowerbound" if "lowerbound" in t else "exact"
        score = Score(score.score_type, score.score_cp, score.mate_distance, "sente", bound)
        pv = t[t.index("pv") + 1:] if "pv" in t else []
        latest[multipv] = EngineResult(score=score, pv=pv,
            depth=int(t[t.index("depth") + 1]) if "depth" in t else None,
            nodes=int(t[t.index("nodes") + 1]) if "nodes" in t else None,
            time_ms=int(t[t.index("time") + 1]) if "time" in t else None, raw_info=[line])
        if bound == "exact":
            exact[multipv] = latest[multipv]
    best = lines[-1].split()[1] if lines and lines[-1].startswith("bestmove ") else None
    results = []
    for k in sorted(latest):
        result = exact.get(k, latest[k])
        result.best_move = result.pv[0] if result.pv else best
        result.reported_best_move = best
        if result is not latest[k]:
            result.raw_info += latest[k].raw_info
        # Actual request work, even when the score is from a completed earlier depth.
        result.nodes = latest[k].nodes
        result.time_ms = latest[k].time_ms
        results.append(result)
    return results or [EngineResult(Score("unknown"), best_move=best, reported_best_move=best)]


def _normalize_perspective(result: EngineResult, turn: int) -> EngineResult:
    """Convert USI's side-to-move score to the project's fixed sente perspective."""
    if turn == shogi.BLACK:
        result.score = Score(result.score.score_type, result.score.score_cp,
                             result.score.mate_distance, "sente", result.score.bound)
    else:
        cp = -result.score.score_cp if result.score.score_cp is not None else None
        mate = -result.score.mate_distance if result.score.mate_distance is not None else None
        bound = {"exact": "exact", "upperbound": "lowerbound", "lowerbound": "upperbound"}[result.score.bound]
        result.score = Score(result.score.score_type, cp, mate, "sente", bound)
    return result
