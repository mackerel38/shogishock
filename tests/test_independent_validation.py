import json

from surprise.independent_validation import score
from surprise.response_calibration import SETS


def test_event_counts_distinguish_players_and_movers():
    features=[{'move':'a','sets':[1]*len(SETS),'x':[1.]},
              {'move':'b','sets':[0]*len(SETS),'x':[0.]}]
    records=[{'features':features,'existing':[.7,.3],'support':0,'game':'g','label':0},
             {'features':features,'existing':[.7,.3],'support':0,'game':'g','label':1}]
    result=score(records,'existing',{}, {'g':['p1','p2']},['p1','p1'],{'p1':1,'p2':1})
    m=result['sets']['capture_any']
    assert m['opportunity_count']==2 and m['distinct_games']==1
    assert m['distinct_players_both_sides']==2 and m['distinct_actual_movers']==1
    assert m['observed_probability']==.5 and m['predicted_probability']==.7
    assert result['abstain_fraction']==1


def test_empty_confirmation_is_not_a_success():
    result=score([],'existing',{}, {},[],{})
    assert result['overall']['n']==0
    assert result['inherited_primary_mean_brier'] is None
    assert result['sets']['capture_any']['opportunity_count']==0


def test_known_bishop_sanity_uses_obvious_reject_not_policy_mass():
    from pathlib import Path
    # Cached research evidence fixture; deliberately no Human Policy call.
    path=Path('reports/human_e2e/candidates.json')
    if not path.exists():
        import pytest
        pytest.skip('old generated evidence not present')
    row=next(r for r in json.loads(path.read_text()) if r['candidate_id']=='5c46af1026197c8aeb70_3a3b')
    assert row['obvious_reply_neutralizes'] is True
    assert 'obvious_reply_neutralizes' in row['not_escalated_reason']
