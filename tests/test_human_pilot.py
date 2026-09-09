import pytest
import shogi

from surprise.book_seeds import bounded_positions, parse_book
from surprise.human_data import wilson
from surprise.human_data import digest
from surprise.human_policy import describe, Policy, split_games, metric
from surprise.kif_export import ExportedKif, VariationNode, _add_branch, to_kif
from surprise.position import Position
from surprise.promotion import annotate_pairs


def test_wilson_distinguishes_sample_size():
    a,b=wilson(1,20),wilson(50,1000)
    assert a[1]-a[0]>b[1]-b[0]


def test_player_split_has_no_cross_player_leakage():
    games={str(i):{'players':[str(i%50),str((i*7+3)%50)],'date':i} for i in range(200)}
    s=split_games(games,'player','test')
    groups=[{p for g in s[k] for p in games[g]['players']} for k in ('train','validation','test')]
    assert not(groups[0]&groups[1] or groups[1]&groups[2] or groups[0]&groups[2])
    assert s['purged']


def test_sampling_hash_does_not_predetermine_split():
    seed='test-domain'
    selected=sorted(map(str,range(1000)),key=lambda p:digest(seed+p))[:200]
    games={p:{'players':[p,p],'date':i} for i,p in enumerate(selected)}
    split=split_games(games,'player',seed)
    assert len(split['validation'])>10 and len(split['test'])>10


def test_policy_sums_to_one_for_unseen_and_seen():
    p=describe(shogi.Board().sfen());data={'positions':{'p':p}}
    train=[{'pid':'p','move':'7g7f','prefix':''} for _ in range(10)]
    model=Policy(data,train)
    for kind in ('uniform','popularity','exact','prefix','behavior','hierarchical'):
        for pid in ('p','new'):
            q=model.predict(p,pid,'',kind,temperature=1.25)
            assert sum(q)==pytest.approx(1) and min(q)>0
    assert model.predict(p,'p','','exact')[p['moves'].index('7g7f')]>0.7


def test_book_bfs_uses_actual_depth_not_sfen_number():
    b=shogi.Board();s=b.sfen();b.push_usi('7g7f');child=' '.join(b.sfen().split()[:3])+' 99'
    book,_=parse_book([f'sfen {s}','7g7f 3c3d 30 9 100',f'sfen {child}','3c3d 2g2f -20 8 999'])
    rows,d=bounded_positions(book,1)
    assert [r['ply'] for r in rows]==[0,1]
    assert rows[1]['parent_book_eval_sente']==20
    assert rows[1]['recorded_move_numbers']==[99]


def test_nonpromotion_conservative_pair_rule():
    p=Position.from_sfen('4k4/9/4R4/9/9/9/9/9/4K4 b - 1')
    rows=[{'move':m,'candidate_eval':v,'attacker_side':'sente','position_id':'p','is_check':False,'normal':{'pv':['5a4a']}}
          for m,v in [('5c4c',0),('5c4c+',100)]]
    annotate_pairs(p,rows)
    assert rows[0]['redundant_nonpromotion'] and not rows[1]['redundant_nonpromotion']
    p=Position.from_sfen('4k4/9/4S4/9/9/9/9/9/4K4 b - 1')
    annotate_pairs(p,rows)
    assert not rows[0]['redundant_nonpromotion']


def test_kif_variation_start_not_main_pv_end():
    candidate=VariationNode(move='7g7f');after=shogi.Board();after.push_usi('7g7f');warnings=[]
    _add_branch(candidate,['3c3d','2g2f','8c8d'],['main'],warnings,after)
    _add_branch(candidate,['8c8d','2g2f'],['alternative'],warnings,after)
    text=to_kif(ExportedKif('test',shogi.Board().sfen(),[],candidate,warnings))
    assert '変化：2手' in text and '変化：5手' not in text
    assert '手合割：平手' in text and '開始局面：' not in text
    from surprise.human_review import validate_kif
    assert validate_kif(text)['variation_headers']==1


def test_partial_human_mass_and_gote_sign():
    from surprise.human_response import response_metrics
    cp=lambda v:{'score':{'score_type':'cp','score_cp':v,'bound':'exact'}}
    replies=[{'human_probability':.7,'result':cp(500)},{'human_probability':.2,'result':cp(-100)}]
    m=response_metrics(replies,500,'gote',[100])
    assert m['covered_probability']==pytest.approx(.9)
    assert m['P_good']['100']['lower']==pytest.approx(.7)
    assert m['P_good']['100']['upper']==pytest.approx(.8)
    assert m['human_gap'] is None and m['human_expected_eval'] is None
    replies.append({'human_probability':.1,'result':cp(500)})
    m=response_metrics(replies,500,'gote',[100])
    assert m['human_expected_eval']==pytest.approx(380)
    assert m['human_gap']==pytest.approx(120)
