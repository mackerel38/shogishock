from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import shogi


@dataclass(frozen=True)
class VirtualPass:
    """Analysis-only position: identical board/hands with a selected side to move."""

    position: "Position"
    attacker_side: int
    applicable: bool
    reason: str | None = None


class Position:
    def __init__(self, board: shogi.Board | None = None, sfen: str | None = None):
        if board is not None and sfen is not None:
            raise ValueError("provide board or sfen, not both")
        self.board = shogi.Board(board.sfen()) if board is not None else shogi.Board(sfen)

    @classmethod
    def startpos(cls) -> "Position":
        return cls(board=shogi.Board())

    @classmethod
    def from_sfen(cls, sfen: str) -> "Position":
        return cls(sfen=sfen)

    @property
    def sfen(self) -> str:
        return self.board.sfen()

    @property
    def turn(self) -> int:
        return self.board.turn

    def legal_moves(self) -> list[str]:
        return [m.usi() for m in self.board.legal_moves]

    def apply_move(self, move: str) -> "Position":
        child = shogi.Board(self.board.sfen())
        parsed = shogi.Move.from_usi(move)
        if parsed not in child.legal_moves:
            raise ValueError(f"illegal move {move!r} in {self.sfen}")
        child.push(parsed)
        return Position(board=child)

    def is_check(self) -> bool:
        return self.board.is_check()

    def move_history(self) -> list[str]:
        return [move.usi() for move in self.board.move_stack]

    def virtual_pass(self, attacker_side: int | str) -> VirtualPass:
        side = _side(attacker_side)
        if self.board.is_check():
            return VirtualPass(self, side, False, "current position is in check")
        # A null move after a checking move is invalid for this experiment.
        clone = shogi.Board(self.board.sfen())
        clone.turn = side
        return VirtualPass(Position(board=clone), side, True)


def _side(value: int | str) -> int:
    if value in (shogi.BLACK, "sente", "black", "先手"):
        return shogi.BLACK
    if value in (shogi.WHITE, "gote", "white", "後手"):
        return shogi.WHITE
    raise ValueError(f"unknown side: {value!r}")
