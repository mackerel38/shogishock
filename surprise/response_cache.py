"""Small cache API for history-dependent response diagnostics."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Callable


def response_cache_key(*, sfen: str, move_history: list[str] | tuple[str, ...],
                       candidate_move: str, reply_move: str,
                       feature_schema: str = "response-review-v1") -> str:
    payload = {"schema": feature_schema, "sfen": sfen,
               "move_history": list(move_history), "candidate_move": candidate_move,
               "reply_move": reply_move}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


class ResponseDiagnosticCache:
    """SQLite cache whose identity includes all history-dependent inputs."""
    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(str(path))
        self.db.execute("CREATE TABLE IF NOT EXISTS response_diagnostic_cache (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self.db.commit()

    def get(self, *, sfen: str, move_history: list[str] | tuple[str, ...],
            candidate_move: str, reply_move: str, feature_schema: str = "response-review-v1") -> Any:
        key = response_cache_key(sfen=sfen, move_history=move_history, candidate_move=candidate_move,
                                 reply_move=reply_move, feature_schema=feature_schema)
        row = self.db.execute("SELECT value FROM response_diagnostic_cache WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, *, sfen: str, move_history: list[str] | tuple[str, ...],
            candidate_move: str, reply_move: str, value: Any,
            feature_schema: str = "response-review-v1") -> None:
        key = response_cache_key(sfen=sfen, move_history=move_history, candidate_move=candidate_move,
                                 reply_move=reply_move, feature_schema=feature_schema)
        self.db.execute("INSERT OR REPLACE INTO response_diagnostic_cache VALUES (?,?)",
                        (key, json.dumps(value, ensure_ascii=False)))
        self.db.commit()

    def get_or_compute(self, *, sfen: str, move_history: list[str] | tuple[str, ...],
                       candidate_move: str, reply_move: str, compute: Callable[[], Any],
                       feature_schema: str = "response-review-v1") -> Any:
        value = self.get(sfen=sfen, move_history=move_history, candidate_move=candidate_move,
                         reply_move=reply_move, feature_schema=feature_schema)
        if value is None:
            value = compute()
            self.put(sfen=sfen, move_history=move_history, candidate_move=candidate_move,
                     reply_move=reply_move, value=value, feature_schema=feature_schema)
        return value

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "ResponseDiagnosticCache": return self
    def __exit__(self, *_: object) -> None: self.close()
