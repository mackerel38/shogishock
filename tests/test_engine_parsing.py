from surprise.engine import Score, _parse_search, _normalize_perspective
import shogi

def test_parse_cp_and_pv():
    r = _parse_search(["info depth 5 score cp 123 nodes 99 time 2 pv 7g7f 3c3d", "bestmove 7g7f"])[0]
    assert r.score == Score("cp", score_cp=123)
    assert r.best_move == "7g7f" and r.pv == ["7g7f", "3c3d"]

def test_parse_mate():
    assert _parse_search(["info depth 1 score mate -3 pv 7g7f", "bestmove 7g7f"])[0].score == Score("mate", mate_distance=-3)

def test_sente_perspective_conversion():
    r = _parse_search(["info depth 1 score cp 250 pv 7g7f", "bestmove 7g7f"])[0]
    assert _normalize_perspective(r, shogi.WHITE).score.score_cp == -250
