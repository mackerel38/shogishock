import shogi

from surprise.response_calibration import features, tilt, shrink, SETS, event_metric
from surprise.human_policy import Policy, describe


def board_after(history):
    board = shogi.Board()
    for move in history:
        board.push_usi(move)
    return board.sfen()


def test_bishop_fixture_is_not_capture_of_candidate():
    history = '2g2f 3c3d 7g7f 3a3b'.split()
    fs = {r['move']:r for r in features(board_after(history), history)}
    for move in ('8h2b', '8h2b+'):
        f = fs[move]
        flags = dict(zip(SETS, f['sets']))
        assert flags['capture_any'] and flags['high_value_capture'] and flags['material_recovery']
        assert not flags['captures_candidate'] and not flags['recapture']
        assert not f['can_be_recaptured']
        assert f['victim_piece_type'] == shogi.BISHOP
    assert fs['8h2b+']['sets'][-1] and not fs['8h2b']['sets'][-1]


def test_recapture_requires_actual_history():
    history = '7g7f 3c3d 8h2b+'.split()
    fs = {r['move']:r for r in features(board_after(history), history)}
    flags = dict(zip(SETS, fs['3a2b']['sets']))
    assert flags['recapture'] and flags['captures_candidate']


def test_probability_tilt_and_overlapping_sets_normalize():
    fs = [{'x':[1,1]}, {'x':[1,0]}, {'x':[0,0]}]
    q = tilt([.2,.3,.5], fs, [1,1])
    assert abs(sum(q)-1) < 1e-12 and all(p>0 for p in q)
    assert q[0] > .2
    assert all(abs(a-b)<1e-12 for a,b in zip(tilt([.2,.3,.5],fs,[0,0]), [.2,.3,.5]))


def test_shrinkage_keeps_single_observation():
    p = describe(shogi.Board().sfen())
    data = {'positions':{'start':p}}
    row = {'pid':'start','move':'7g7f','prefix':''}
    model = Policy(data,[row])
    fallback = model.predict(p,'start','','behavior')
    hard = model.predict(p,'start','','hierarchical',2)
    smooth = shrink(model,p,'start','',5)
    i = p['moves'].index('7g7f')
    assert hard == fallback and smooth[i] > hard[i]
    assert abs(sum(smooth)-1) < 1e-12


def test_event_brier_and_empty_support():
    m = event_metric([(.2,1,'g'),(.8,0,'h')])
    assert m['sample_count'] == 2 and m['observed_probability'] == .5
    assert abs(m['brier']-.64) < 1e-12
    assert event_metric([])['sample_count'] == 0
