import json

import shogi
from surprise.kif_export import ExportedKif, VariationNode, _add_branch, build_tree, to_kif


def test_candidate_exports_with_candidate_and_variation(tmp_path):
    # Unit tests remain runnable from the public source-only checkpoint.
    board = shogi.Board()
    parent = {'position_id':'fixture','sfen':board.sfen(),'move_history':[],'ply':0,'source':'synthetic-test'}
    board.push_usi('7g7f')
    row = {'candidate_id':'fixture_7g7f','position_id':'fixture','move':'7g7f',
           'attacker_side':'sente','resulting_sfen':board.sfen(),
           'best':{'pv':['7g7f']},'normal':{'pv':['3c3d']}}
    (tmp_path/'positions.json').write_text(json.dumps([parent]))
    (tmp_path/'candidates.json').write_text(json.dumps([row]))
    exported = build_tree(tmp_path, "fixture_7g7f")
    text = to_kif(exported)
    assert "[ShogiShock candidate]" in text
    assert "candidate_id: fixture_7g7f" in text
    assert "７" in text and "まで" in text


def test_parent_and_candidate_pv_labels_are_distinct():
    candidate = VariationNode(move="7g7f", comment=[
        "parent_engine_best_pv: 7g7f 3c3d",
    ])
    after = shogi.Board(); after.push_usi("7g7f")
    _add_branch(candidate, ["3c3d"], ["[engine PV after candidate]"], [], after)
    text = to_kif(ExportedKif("test", shogi.Board().sfen(), [], candidate, []))
    assert "parent_engine_best_pv:" in text
    assert "engine_optimal_pv:" not in text
    assert "[engine PV after candidate]" in text


def test_kif_contains_variation_branch():
    candidate = VariationNode(move="7g7f", comment=["[ShogiShock candidate]"])
    after = shogi.Board(); after.push_usi("7g7f")
    warnings = []
    _add_branch(candidate, ["3c3d"], ["[engine PV after candidate]"], warnings, after)
    _add_branch(candidate, ["8c8d"], ["[obvious reply]"], warnings, after)
    text = to_kif(ExportedKif("test", shogi.Board().sfen(), [], candidate, warnings))
    assert not warnings
    assert "変化：2手" in text
    assert "３四歩(33)" in text and "８四歩(83)" in text
