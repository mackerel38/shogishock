import pytest

from surprise.obvious import obvious_replies, defender_gap, reply_summary, escalation_reasons
from surprise.position import Position
from surprise.reach import ReachDB, normalize_game


def cp(value):
    return {'score': {'score_type': 'cp', 'score_cp': value, 'bound': 'exact'}}


def test_capture_is_extracted_but_bad_capture_is_not_neutralizer():
    p = Position.startpos()
    for move in ['7g7f', '3c3d']:
        p = p.apply_move(move)
    obvious = obvious_replies(p, '8h2b+')
    take = next(r for r in obvious if r['move'] == '3a2b')
    assert take['reply_captures_candidate'] and 'recapture' in take['signals']
    response = take | {'result': cp(700)}
    summary = reply_summary([response], cp(-500), 'sente', 30, [50,100,200,300])
    assert response['is_good_300'] is False
    assert summary['good_reply_fraction_100'] is None
    assert len(obvious) >= 1  # extraction did not remove the tempting capture


def test_gote_sign_and_complete_reply_width():
    responses = [{'move': str(i), 'result': cp(v)} for i,v in enumerate([600,550,0])]
    summary = reply_summary(responses, cp(610), 'gote', 3, [50,100,200,300])
    assert defender_gap(550,600,'gote') == 50
    assert defender_gap(-550,-600,'sente') == 50
    assert summary['good_reply_count_50'] == 2
    assert summary['good_reply_fraction_50'] == pytest.approx(2/3)


def test_mate_is_not_cp_probability():
    replies = [{'result': {'score': {'score_type':'mate','mate_distance':3}}}]
    summary = reply_summary(replies, cp(10), 'gote', 1, [100])
    assert summary['good_reply_count_100'] is None
    assert replies[0]['is_good_100'] is None


def fixture(gid, moves):
    return normalize_game({'id':gid,'variant':'standard','status':'resign','moves':' '.join(moves),
       'players': {'sente': {'user': {'id':'test-a'}}, 'gote': {'user': {'id':'test-b'}}}},
       {'retrieved_at':'test', 'terms_url':'https://example.test/fixture'})


def test_reach_one_game_one_vote_and_duplicate_id(tmp_path):
    db=ReachDB(tmp_path/'reach.db')
    game=fixture('one',['5i5h','5a5b','5h5i','5b5a'])
    assert db.ingest(game)=='accepted'
    assert db.ingest(game)=='duplicate'
    start=next(r for r in db.export() if r['min_ply']==0)
    assert start['occurrence_count']==2
    assert start['games_reaching_position']==1 and start['reach_probability']==1
    db.close()


def test_transposition_counts_distinct_games(tmp_path):
    db=ReachDB(tmp_path/'reach.db')
    db.ingest(fixture('a',['7g7f','3c3d','2g2f','8c8d']))
    db.ingest(fixture('b',['2g2f','8c8d','7g7f','3c3d']))
    end=[r for r in db.export() if r['min_ply']==4]
    assert len(end)==1 and end[0]['games_reaching_position']==2
    assert end[0]['total_games']==2
    assert any(r['reach_probability']==.5 for r in db.export())
    db.close()


def test_bot_unknown_and_invalid_games_excluded(tmp_path):
    db=ReachDB(tmp_path/'reach.db')
    for gid, players in [('bot',{'sente':{'user':{'id':'bot','title':'BOT'}},'gote':{'user':{'id':'human'}}}),
                         ('ai',{'sente':{'aiLevel':1},'gote':{'user':{'id':'human'}}}), ('unknown',{})]:
        g=normalize_game({'id':gid,'variant':'standard','status':'resign','moves':'7g7f','players':players},{})
        assert db.ingest(g)=='excluded'
    assert db.ingest(fixture('illegal',['7g7e']))=='excluded'
    assert not db.export()
    db.close()


def test_parent_gate_does_not_gate_candidate_cost():
    cfg={'parent_favorable_cp':300,'min_reach_probability':.01,'broad_good_reply_fraction':.5}
    assert escalation_reasons(-600,.1,False,.05,cfg)==[]
    assert escalation_reasons(300,.1,False,.05,cfg)==['parent_already_favorable']
    assert escalation_reasons(0,None,True,None,cfg)==['reach_unknown','obvious_reply_neutralizes']


def test_plan_keeps_adverse_candidate_and_does_not_invent_population_reach():
    from surprise.reach_report import plan_candidate
    cfg={'parent_favorable_cp':300,'min_reach_probability':.01,
         'broad_good_reply_fraction':.5,'minimum_games_before_scan':1000,'neutralize_tolerance':100}
    row={'candidate_id':'test','position_id':'test','attacker_side':'gote','best_eval':50,'candidate_eval':600}
    plan=plan_candidate(row,None,19,None,cfg)
    assert plan['parent_attacker_advantage']==-50
    assert plan['reach_probability']==0 and plan['population_reach_probability'] is None
    assert not plan['parent_already_favorable'] and not plan['escalated']
    assert 'insufficient_reach_sample' in plan['not_escalated_reason']
    assert 'obvious_reply_unresolved' in plan['not_escalated_reason']
