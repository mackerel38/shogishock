"""Conservative, explainable nonpromotion demotion; never delete records."""
import shogi


def annotate_pairs(position, rows, loss_threshold=50):
    by_move={r['move']:r for r in rows}
    for r in rows:
        r['not_escalated_reason']=[x for x in r.get('not_escalated_reason',[]) if x!='redundant_nonpromotion']
        r.update(redundant_nonpromotion=False,promotion_pair_id=None,
            promotion_alternative_eval=None,nonpromotion_eval=None,nonpromotion_loss_vs_promotion=None)
        move=shogi.Move.from_usi(r['move'])
        base=r['move'].removesuffix('+')
        if move.from_square is None or base not in by_move or base+'+' not in by_move:continue
        plain,promoted=by_move[base],by_move[base+'+']
        r['promotion_pair_id']=r['position_id']+'_'+base
        a,b=plain.get('candidate_eval'),promoted.get('candidate_eval')
        loss=(b-a)*(1 if r['attacker_side']=='sente' else -1) if a is not None and b is not None else None
        r.update(promotion_alternative_eval=b,nonpromotion_eval=a,nonpromotion_loss_vs_promotion=loss)
        if move.promotion:continue
        piece=position.board.piece_at(move.from_square)
        # Silver/knight/lance movement changes are deliberately exempt.
        eligible=piece.piece_type in (shogi.PAWN,shogi.BISHOP,shogi.ROOK)
        same_check=plain.get('is_check')==promoted.get('is_check')
        same_reply=plain.get('normal',{}).get('pv',[])[:1]==promoted.get('normal',{}).get('pv',[])[:1]
        flag=eligible and same_check and same_reply and loss is not None and loss>=loss_threshold
        r['redundant_nonpromotion']=bool(flag)
        r['nonpromotion_rule']='P/B/R only; same check status and first PV reply; promotion improves attacker CP by configured threshold; shallow heuristic, not proof'
        if flag and 'redundant_nonpromotion' not in r.setdefault('not_escalated_reason',[]):
            r['not_escalated_reason'].append('redundant_nonpromotion')
