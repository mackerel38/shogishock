import json

import pytest
import shogi

from surprise.engine import Engine, Score, _parse_search
from surprise.position import Position
from surprise.research import (Store, identity, load_positions, pass_metrics,
                               relative_metrics, evaluate_candidate)


def result(value):
    return {"score": {"score_type": "cp", "score_cp": value, "mate_distance": None}}


def test_fixed_sente_scores_and_gote_derived_sign():
    sente = pass_metrics(result(-600), result(200), "sente")
    gote = pass_metrics(result(600), result(-200), "gote")
    assert sente == {"pass_eval_delta": 800, "pass_sensitivity": 800}
    assert gote == {"pass_eval_delta": -800, "pass_sensitivity": 800}
    assert pass_metrics(result(0), None, "sente")["pass_sensitivity"] is None
    mate = {"score": {"score_type": "mate", "mate_distance": 3}}
    assert pass_metrics(result(0), mate, "sente")["pass_sensitivity"] is None


def test_relative_ties_and_missing():
    rows = [{"pass_sensitivity": v} for v in [100, 100, 400, None]]
    relative_metrics(rows)
    assert rows[2]["pass_relative_median"] == 300
    assert rows[0]["pass_percentile"] == pytest.approx(1 / 3)
    assert rows[3]["pass_percentile"] is None
    assert rows[0]["pass_reference_count"] == 3


def test_transpositions_keep_histories_and_do_not_reflect():
    positions = load_positions("data/opening_seeds.yaml")
    p = Position.startpos()
    for m in "2g2f 8c8d 2f2e 8d8e 7g7f 3c3d".split():
        p = p.apply_move(m)
    row = next(x for x in positions if x["position_id"] == identity(p.sfen))
    assert len(row["alternative_move_orders"]) >= 2
    assert identity(p.sfen) == identity(" ".join(p.sfen.split()[:3]) + " 99")
    assert identity(Position.startpos().apply_move("2g2f").sfen) != identity(Position.startpos().apply_move("8g8f").sfen)
    assert max(p["ply"] for p in positions) == 40


def test_checkpoint_identity_rejects_stale_config(tmp_path):
    path = tmp_path / "scan.sqlite3"
    s = Store(path, {"nodes": 10})
    s.put({"candidate_id": "x", "candidate_eval": -600})
    s.close()
    s = Store(path, {"nodes": 10})
    assert s.get("x")["candidate_eval"] == -600
    s.close()
    with pytest.raises(ValueError, match="fingerprint"):
        Store(path, {"nodes": 20})


def test_multipv_is_reset_on_uncached_search():
    engine = object.__new__(Engine)
    engine.cache = None
    engine._key = lambda *args: "key"
    sent = []
    engine._send = sent.append
    engine._read_until = lambda _: ["readyok"]
    engine._read_until_prefix = lambda _: ["info score cp 20 pv 7g7f", "bestmove 7g7f"]
    engine.search(Position.startpos(), 10, 2)
    engine.search(Position.startpos(), 11, 1)
    assert [x for x in sent if "MultiPV" in x] == ["setoption name MultiPV value 2", "setoption name MultiPV value 1"]
    assert sent.count("isready") == 2


def test_missing_score_is_not_fabricated_zero():
    assert _parse_search(["bestmove resign"])[0].score.score_type == "unknown"


def test_interrupted_bound_does_not_replace_completed_exact_iteration():
    result = _parse_search(["info depth 4 score cp 200 nodes 700 pv 7g7f 3c3d",
                            "info depth 5 score cp 14000 upperbound nodes 1000 pv 7g7f 3c3d",
                            "bestmove 7g7f"])[0]
    assert result.score.score_cp == 200 and result.score.bound == "exact"
    assert result.depth == 4 and result.nodes == 1000
    assert len(result.raw_info) == 2


def test_bound_only_is_preserved_and_reverses_with_gote():
    from surprise.engine import _normalize_perspective
    from surprise.research import cp
    result = _parse_search(["info score cp 600 upperbound pv 3c3d", "bestmove 3c3d"])[0]
    result = _normalize_perspective(result, shogi.WHITE)
    assert result.score.score_cp == -600 and result.score.bound == "lowerbound"
    assert cp(Engine._encode_result(result)) is None


def test_check_candidate_is_retained_without_pass():
    from surprise.engine import EngineResult
    class Fake:
        def evaluate(self, p, nodes):
            return EngineResult(Score("cp", -600), pv=[])
    p = Position.from_sfen("4k4/9/9/9/9/9/9/3R5/4K4 b - 1")
    record = {"position_id": identity(p.sfen), "sfen": p.sfen, "side_to_move": "sente",
              "occurrence_count": 1, "move_distribution": {}}
    cfg = {"search": {"shallow_nodes": 10, "pass_nodes": 10},
           "research": {"large_material_loss": 700, "obvious_blunder_loss_cp": 1000}}
    best = Engine._encode_result(EngineResult(Score("cp", 100), best_move="6h5h"))
    r = evaluate_candidate(Fake(), record, "6h5h", best, cfg)
    assert r["is_check"] and not r["pass_applicable"]
    assert r["candidate_eval"] == -600 and r["candidate_eval_loss"] == 700
    assert r["pass_sensitivity"] is None


def test_scan_resume_retains_all_legal_moves(tmp_path, monkeypatch):
    import yaml
    import surprise.research as research
    from surprise.engine import EngineResult
    class Fake(Engine):
        calls = 0
        def __init__(self):
            self.cache = True
            self.binary_sha256 = "test-engine"
            self.eval_sha256 = {"nn.bin": "test-eval"}
        @classmethod
        def from_config(cls, path):
            return cls()
        def evaluate(self, p, nodes):
            Fake.calls += 1
            moves = p.legal_moves()
            return EngineResult(Score("cp", -600), best_move=moves[0], pv=[moves[0]])
        def close(self):
            pass
    monkeypatch.setattr(research, "Engine", Fake)
    seeds = tmp_path / "seeds.yaml"
    seeds.write_text(yaml.safe_dump({"source": "test", "lines": [{"id": "one", "moves": "7g7f"}]}))
    out = tmp_path / "out"
    cfg = {"engine": {}, "search": {"shallow_nodes": 10, "pass_nodes": 10},
           "research": {"seed_path": str(seeds), "output_dir": str(out), "min_ply": 0,
                        "max_ply": 1, "review_per_side": 5,
                        "large_material_loss": 700, "obvious_blunder_loss_cp": 1000}}
    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump(cfg))
    research.run_scan(str(config))
    first = json.loads((out / "candidates.json").read_text())
    calls = Fake.calls
    research.run_scan(str(config))
    assert Fake.calls == calls
    assert first == json.loads((out / "candidates.json").read_text())
    expected = len(Position.startpos().legal_moves()) + len(Position.startpos().apply_move("7g7f").legal_moves())
    assert len(first) == expected
    assert all(r["candidate_eval"] == -600 for r in first)
    assert {r["attacker_side"] for r in first} == {"sente", "gote"}
    assert json.loads((out / "manifest.json").read_text())["complete"]


def test_cache_key_includes_nnue_contents():
    e = object.__new__(Engine)
    e.path, e.eval_dir, e.binary_sha256 = "engine", "eval", "binary"
    e.threads, e.hash_mb, e.options = 1, 16, {}
    e.eval_sha256 = {"nn.bin": "first"}
    key = e._key(Position.startpos(), "search", 10, 1)
    e.eval_sha256 = {"nn.bin": "second"}
    assert e._key(Position.startpos(), "search", 10, 1) != key


def test_diverse_review_does_not_remove_high_cost_candidates():
    from surprise.research import select_diverse
    rows = [{"candidate_id": str(i), "position_id": parent, "attacker_side": "sente",
             "parent_complete": True, "pass_sensitivity": value, "pass_relative_median": value,
             "candidate_eval": -9000} for i, (parent, value) in enumerate([("a", 300), ("a", 200), ("b", 100)])]
    assert select_diverse(rows, 2)["sente"]["pass_sensitivity"] == ["0", "2"]
