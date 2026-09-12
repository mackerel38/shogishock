"""Evidence-derived handoff; no engine, policy, or rule changes."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

spec=importlib.util.spec_from_file_location('coverage_experiment',Path(__file__).with_name('experiment.py'))
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)


def main():
    candidates=e.load('candidate_coverage.json'); replies=e.load('reply_coverage.json')
    deep=e.load('deep_checks.json'); evidence=e.load('engine_evidence.json')
    proof=e.load('mate_proof_checks.json')
    assert len(proof['cases'])==2, 'Proof diagnostic incomplete'
    # The initially launched proof prototype left the board pushed on Limit.
    # That changed the printed root label, NOT the searched history or result.
    # Preserve the erroneous label while restoring the authoritative history.
    for row in proof['cases']:
        expected=e.position(row['history']).sfen
        if row['sfen']!=expected:
            row['original_erroneous_cutoff_sfen']=row['sfen']
            row['sfen']=expected
            row['label_correction']='cutoff board label restored from saved history; outcome unchanged; no rerun'
    e.save('mate_proof_checks.json',proof)
    judgments=e.load('review_judgments.json')
    old=json.loads((e.ROOT/'reports/trap_tree_benchmark/evidence.json').read_text())
    old_gate={(b['opponent_move'],c['move']):c['gate']['decision'] for b in old['branches'] for c in b['candidates']}
    assert len(deep['groups'])==6 and len(deep['mate_hypotheses'])==4, 'Incomplete work'
    assert all(g.get('stable') or g['levels'][-1]['nodes']==e.LEVELS[-1] for g in deep['groups'])
    assert all(len(m['levels'])>=3 for m in deep['mate_hypotheses'])
    for m in deep['mate_hypotheses']:
        if m.get('proof_type')=='ordinary full-legal search; not dedicated tsume solver':
            m['original_proof_type_label']=m['proof_type']
            m['proof_type']='ordinary selective adversarial search; not exhaustive AND/OR or dedicated tsume solver'
    e.save('deep_checks.json',deep)
    pv_count=0
    for q in evidence['requests'].values():
        p=e.Position.from_sfen(q['sfen'])
        for move in q['result'].get('pv',[]):p=p.apply_move(move)
        pv_count+=1

    case_c,case_r=[],[]
    for kind,items in [('candidate',candidates),('reply',replies)]:
        for item in items:
            rm=item['history'][20];group=next(g for g in deep['groups'] if g['id']==kind+'_'+rm)
            results=group['levels'][-1]['results'];p=e.position(item['history'])
            best=max(results,key=lambda m:e.rank_value(results[m],p.turn));best_cp=e.cp(results[best])
            item['deeply_checked_reply_count' if kind=='reply' else 'deeply_checked_candidate_count']=len(results)
            for r in item['rows']:
                if r['move'] not in results:continue
                result=results[r['move']];v=e.cp(result)
                gap=((best_cp-v)*(1 if p.turn==0 else -1)) if v is not None and best_cp is not None else None
                order=sorted(results,key=lambda m:e.rank_value(results[m],p.turn),reverse=True)
                stable_tail=len(group['levels'])>=3 and all(x.get('transition',{}).get('score_stable',{}).get(r['move'],False)
                    and x.get('transition',{}).get('first_move_stable',{}).get(r['move'],False) for x in group['levels'][-2:])
                md=result['score'].get('mate_distance')
                pvpos=p.apply_move(r['move'])
                for m in result.get('pv',[]):pvpos=pvpos.apply_move(m)
                detail={'root_reply':rm,'history':item['history'],'sfen':item['sfen'],'move':r['move'],
                        'in_generated_pool':r['in_union'],'old_selected':r['old_selected'],
                        'in_motive_only_pool_without_new_engine_rank':r['human_motivated'],
                        'engine_rank':order.index(r['move'])+1,'engine_rank_scope':'confirmed subset only',
                        'proposal_engine_rank_all_legal':r['engine_rank'],'deep_eval':v,'score':result['score'],
                        'nominal_nodes':group['levels'][-1]['nodes'],'same_condition_best_tested':best,
                        'same_condition_gap_cp':gap,'best_reference_eval':best_cp,
                        'reference_scope':group['reference_scope'],'comparison_group_stable':group['stable'],
                        'individual_last_two_transitions_stable':stable_tail,
                        'human_motivation_tags':r['human_motivation_tags'],
                        'human_policy_reliability':'not used; unchanged calibration limitations',
                        'forced_mate':None if md is None else {'engine_reports_winner':'sente' if md>0 else 'gote',
                            'mate_distance_from_after_reply':abs(md),'pv_terminal_checkmate':pvpos.board.is_checkmate(),
                            'formal_certificate':False},
                        'is_best_or_near_best':gap<=100 if gap is not None and group['stable'] else None,
                        'punishment_if_wrong':{'cp_gap_estimate':gap,'provisional':not group['stable'],
                            'mate':md},
                        'reply_status':'stable_subset_comparison' if group['stable'] else 'needs_review_unstable_comparison',
                        'pv':result.get('pv',[]),'display_prefix':result.get('pv',[])[:4],
                        'absolute_ply':len(item['history'])+1}
                if kind=='candidate':
                    detail.update(candidate_initial_cost_cp=gap,
                        prior_gate_decision=old_gate.get((rm,r['move'])),
                        surprise_move_decision='diagnostic_previously_rejected_not_reinstated' if old_gate.get((rm,r['move']))=='reject' else 'benchmark_option_not_production_approved',
                        entry_plausibility=judgments['entry_plausibility'][rm])
                    case_c.append(detail)
                else:
                    detail['old_upstream_candidate_existed']=(rm,'4e6g+') in old_gate
                    detail['old_omission_scope']='reply slate' if (rm,'4e6g+') in old_gate else 'upstream candidate absent; not an isolated reply-rule comparison'
                    detail.update(judgments['reply_judgments'].get(r['move'],{
                        'plausibility_class':'unvalidated_motive_hypothesis',
                        'reason':'Generated geometry or engine shortlist is not evidence of real human frequency.',
                        'surprise_move_decision':'not_applicable_opponent_reply'}))
                    case_r.append(detail)
            e.save('candidate_coverage.json' if kind=='candidate' else 'reply_coverage.json',items)

    mate_cases=[]
    for m in deep['mate_hypotheses']:
        tail=m['levels'][-1];r=tail['result'];md=r['score'].get('mate_distance')
        typed=[x for x in m['levels'] if x['result']['score']['score_type']=='mate']
        distance_stable=len(typed)>=3 and len({x['result']['score']['mate_distance'] for x in typed[-3:]})==1
        mate_cases.append({'id':m['id'],'history':m['history'],'sfen':m['sfen'],
            'engine_mate_evidence':md is not None and md<0 and tail['pv_terminal_checkmate'],
            'forced_mate':'engine_reported_not_formally_certified' if md is not None and md<0 and tail['pv_terminal_checkmate'] else 'unconfirmed',
            'mate_distance':abs(md) if md is not None else None,'distance_origin':'side to move in this saved position',
            'distance_stable':distance_stable,'first_move':r.get('best_move'),
            'first_forcing_move':None,'nominal_nodes':tail['nodes'],'pv':r.get('pv',[]),
            'display_prefix':r.get('pv',[])[:4], 'formal_certificate':False,
            'levels':[{'nodes':x['nodes'],'score':x['result']['score'],'depth':x['result']['depth'],
                       'terminal_checkmate':x['pv_terminal_checkmate']} for x in m['levels']]})
        p=e.position(m['history'])
        for move in r.get('pv',[]):
            mover=p.turn;p=p.apply_move(move)
            if mover==1 and p.is_check():mate_cases[-1]['first_forcing_move']=move;break

    target_c=[x for x in case_c if (x['root_reply']=='3d2d' and x['move']=='P*2c') or
              (x['root_reply']=='3d3f' and x['move']=='4e6g+')]
    target_r=[x for x in case_r if x['move'] in ['7h7i','7h8g','2d2a+']]
    assert all(x['in_generated_pool'] for x in target_c+target_r)
    counts={'candidate_positions':len(candidates),'reply_positions':len(replies),
            'candidate_legal':sum(x['legal_candidate_count'] for x in candidates),
            'candidate_union':sum(x['union_candidate_count'] for x in candidates),
            'reply_legal':sum(x['legal_reply_count'] for x in replies),
            'reply_union':sum(x['union_reply_count'] for x in replies),
            'deep_compared_candidates':len(case_c),'deep_compared_replies':len(case_r),
            'stable_comparison_groups':sum(g['stable'] for g in deep['groups']),
            'comparison_groups':len(deep['groups']),'validated_pv_count':pv_count,
            'new_requests':sum(not q['cache_hit'] for q in evidence['requests'].values()),
            'cache_hits':sum(q['cache_hit'] for q in evidence['requests'].values()),
            'new_engine_seconds':round(sum((q['result'].get('time_ms') or 0)/1000 for q in evidence['requests'].values() if not q['cache_hit']),2),
            'reject_regressions_passed':len(e.load('regressions.json')),
            'new_policy_calls':0,'new_human_games':0,'production_activation':False}
    all_stable=all(g['stable'] for g in deep['groups'])
    decision='YES' if all_stable and all(m['engine_mate_evidence'] for m in mate_cases) else 'INCONCLUSIVE'
    handoff={'research_question':'Can generic union generation recover quiet candidates and reasoned non-best replies on the exposed B4e benchmark, with stable tactical confirmation?',
       'source_checkpoint':{'research':'437a7ca93dcd20e645b6c1a7b63cd8a14e6f1547','display':'d5be34c898967884cf4ea1755b43c360ec01293d','plan':'9634bb81815109cb84a18f05a399096a211cec66'},
       'conclusion':'Target coverage recovered without named inclusions. Broad generated pools are motivation hypotheses, not calibrated human choices. Consult separate stability and mate results; no production approval.',
       'next_step_decision':{'value':decision,'target':'coverage method with stable tactical confirmation on this benchmark only','production_or_mass_scan_authorized':False},
       'candidate_coverage_result':{'target_recovery':'YES','generalization':'unvalidated; exposed benchmark','coverage':counts},
       'reply_coverage_result':{'target_recovery':'YES','specificity':'unvalidated; broad geometry deliberately overgenerates','old_rule_note':'R2a+ afterR2d was already displayed. Gold moves were omitted, not absent from old all-legal10k data.'},
       'deep_confirmation_result':{'all_groups_stable':all_stable,'groups':[{'id':g['id'],'stable':g['stable'],'last_nodes':g['levels'][-1]['nodes'],'last_transition':g['levels'][-1].get('transition')} for g in deep['groups']]},
       'mate_detection_result':mate_cases,
       'all_defense_proof_diagnostic':proof,
       'move_limit_policy_result':{'new_candidate_move_max_ply':22,'new_reply_move_max_ply':23,'proof_exception':'continuations of tactics initiated at22-24 may exceed30','new_post30_candidate_searches':0},
       'confirmed_facts':['All target moves legal in their specified branches and in general-rule union.','Old3 rejected examples remain reject with original stored evidence and unchanged gate.','No HP fitting/inference or independent270 reuse.','No old research tree overwritten.'],
       'unknowns':['Actual entry/reply frequencies, especially B*7g entry.','Human specificity of broad motivation tags.','Generalization beyond this exposed benchmark.','Exact shortest mate length without an exhaustive certificate.','Production obvious-gate safety remains INCONCLUSIVE.'],
       'important_numbers':counts,'candidate_cases':case_c,'reply_cases':case_r,
       'human_review_points':['P*2c quiet setup retention.','B6g+ versus alternatives afterR3f at matched budgets.','Saving the gold withG7i/G8g: human reason versus tactical consequence.','ImmediateR2a+ versus recapture first.','Entry plausibility is not conditional trap severity.'],
       'next_research_question':'Only after review: assess motive specificity on additional preselected positions and unresolved stability; do not tune this cycle retroactively.',
       'luna_tasks':'See LUNA_TASK.md; no Luna agent invoked.',
       'human_report':{'lead':'Coverage recovered; do not equate generated motives with human probabilities or treat unstable shallow rankings as facts.',
                       'decision':decision,'short_prefix_policy':'Use saved display_prefix; offer full mate PV optionally, never append unrelated long best-play tails.',
                       'do_not_claim':['new discovery','win probability','formal shortest-mate proof','production approval','all generated moves are natural']}}
    e.save('ASTRA_HANDOFF.json',handoff)
    e.save('verification.json',{'prototype_tests':11,'engine_position_cache_tests':8,'legal_pvs':pv_count,
          'plan_sha256':hashlib.sha256((e.HERE/'PLAN.md').read_bytes()).hexdigest(),
          'gate_sha256':hashlib.sha256((e.ROOT/'reports/tactical_falsification/prototype.py').read_bytes()).hexdigest()})
    print(json.dumps({'decision':decision,'numbers':counts,'mates':[(x['id'],x['mate_distance'],x['distance_stable']) for x in mate_cases]},indent=2))


if __name__=='__main__':main()
