from surprise.position import Position
import shogi

def test_sfen_roundtrip_and_moves():
    p = Position.startpos()
    assert Position.from_sfen(p.sfen).sfen == p.sfen
    assert "7g7f" in p.legal_moves()
    assert p.apply_move("7g7f").turn == shogi.WHITE

def test_virtual_pass_preserves_board_and_changes_turn():
    p = Position.startpos().apply_move("7g7f")
    v = p.virtual_pass("sente")
    assert v.applicable and v.position.sfen.split()[0] == p.sfen.split()[0]
    assert v.position.board.sfen().split()[2] == p.board.sfen().split()[2]
    assert v.position.turn == shogi.BLACK

def test_check_disables_virtual_pass():
    p = Position.from_sfen("4k4/9/9/9/9/9/9/4R4/4K4 w - 1")
    assert not p.virtual_pass("sente").applicable
