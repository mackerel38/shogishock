"""Assemble explicit Astra interpretations with saved evidence; no new analysis calls."""
import hashlib
import json
from pathlib import Path
from surprise.research import write_json

HERE=Path(__file__).resolve().parent


def main():
    results=json.loads((HERE/'results.json').read_text())
    judgments=json.loads((HERE/'interpretations.json').read_text())
    confirmations=json.loads((HERE/'confirmation_results.json').read_text())
    selection=json.loads((HERE/'confirmation_plan.json').read_text())
    engine=json.loads((HERE/'engine_evidence.json').read_text())
    for c in results['cases']:
        c.update(judgments['cases'][c['id']])
        c['evaluation_after_reply']={r['move']:r['engine_eval'] for r in c['responses']
            if r['move'] in c['obvious_looking_replies'] or r['same_condition_gap']==0}
        c['same_condition_gap']={r['move']:r['same_condition_gap'] for r in c['responses']
            if r['move'] in c['obvious_looking_replies']}
        c['good_reply_counts_not_probabilities']={str(t):sum(r['same_condition_gap'] is not None and r['same_condition_gap']<=t for r in c['responses'])
                                                 for t in (50,100,200,300)}
        c['strong_naturalness_proxy_count']=sum(r['strong'] for r in c['responses'])
        labels={x['label'] for x in selection['positions'] if x['case_id']==c['id']}
        c['confirmation_100k_selected_subset']=[r for r in confirmations if r['label'] in labels]
        c['confirmation_scope']='Selected child pairs/subsets, NOT full100k best-reply evaluation; frozen gate remains10k.'
    results['next_step_decision']=judgments['next_step_decision']
    results['decision_target']=judgments['decision_target']
    results['work_totals']={k:engine[k] for k in ('new_engine_requests','new_100k_requests','cache_hits')}
    results['work_totals']['nominal_requested_nodes']=sum(r['nominal_nodes'] for r in engine['requests'].values())
    results['work_totals']['recorded_search_nodes']=sum(max(z.get('nodes') or 0 for z in r['results']) for r in engine['requests'].values())
    results['work_totals']['candidate_alternatives_compared']=sum(len(x['alternatives']) for x in results['bounded_alternatives'])
    write_json(HERE/'results.json',results)
    handoff={
        'research_question':'Does the frozen tactical prefilter wrongly reject viable opening traps/sacrifices when starting histories are natural?',
        'source_checkpoint':{'original_research':'903f13a4c8a093709596e6716c35cce3dc071b5f',
            'latest_review_lineage':'86595f9a0fb8c22a68a47e0532a311ce6bc6de8a',
            'gate_freeze':'1d0c529','prospective_selection':'b6b747e651d15677ca1e69803422880ade2d01b9',
            'pre100k_checkpoint':'813b4be'},
        'conclusion':judgments['conclusion'],'next_step_decision':judgments['next_step_decision'],
        'decision_target':judgments['decision_target'],'large_search_authorized':False,
        'confirmed_facts':[
            'Three established reject regressions remain reject using saved evidence;0 new regression engine calls.',
            'Frozen gate and obvious features unchanged; original two long-history controls withdrawn as production safety evidence.',
            'Both prospectively selected opening controls survive all12 frozen sensitivity combinations at10k.',
            'One cleaner23ply control; second22ply control remains borderline because preceding R3e loses454cp against R2d at100k.',
            'User19.R2b+ rejects at frozen gate;21.P*8b passes narrow gate but research review rejects the current proposal.',
            'N*8f is not the sole adequate response. No Human Policy probabilities, new games, refit, mass scan,1M/10M or Vast.'
        ],
        'unknowns':['Human naturalness/choice probabilities and practical surprise value',
            'Independent poison/sacrifice coverage beyond this correlated opening family',
            'Exhaustive prefix tactical correctness and full100k response ranking',
            'Better practical surprise near R8i+; limited shortlist found only less-bad continuations'],
        'important_numbers':results['work_totals']|{
            'prospective_controls':2,'provisionally_cleaner_controls':1,'borderline_controls':1,
            'exploratory_user_hypotheses':2,'actual_candidates':0,'reject_regressions':3,
            'full10k_response_counts':[len(c['responses']) for c in results['cases']],
            'poisoned_rook_gap10k':800,'poisoned_rook_selected_pair_gap100k':1133,
            'bad_gold_recapture_gap10k':416,'bad_gold_selected_pair_gap100k':455,
            'R3e_vs_R2d_loss100k':454,'old_B7g_vs_P8g_loss100k':2447,
            'user_SxR_score100k':-2478,
            'user_pawn_defenses100k':{'N*8f':-2588,'8i8b':-2756,'7a8b':-2864},
            'score_convention':'All raw CP is sente-oriented.100k gaps are selected pairs, not full-search optimal gaps.'},
        'cases':[{k:v for k,v in c.items() if k not in ('responses','prefix_trajectory','parent_result','candidate_result')}
                 for c in results['cases']],
        'human_policy_reliability':{'used':False,'unchanged_independent_validation_decision':'NO',
            'warning':'Do not infer human move probabilities or difficulty from engine rank, forced lines or gate non-rejection.'},
        'human_report':{
            'lead':'INCONCLUSIVE for production rejection. One cleaner sacrifice example survives, but control quality/coverage is still insufficient.',
            'important_comparisons':'Immediate rook capture versus rook invasion; gold recapture versus bishop-drop defense; oldB7g versusP8g; three defenses toP8b.',
            'do_not_claim':['Two fully admitted independent controls','The old long controls establish safety',
                'A new promising surprise was found','N8f is a uniquely difficult defense','Gate non-rejection means a viable candidate'],
            'terminology':'Use concrete purpose labels: 明白な悪手を正しく除外できるかの検証局面 / 成立する可能性のある罠や捨て駒を誤って除外しないかの検証局面. Do not abbreviate purpose to 固定例確認.',
            'next_stage':'Human review; Luna deterministic KIF/display only. Additional safety research needs Astra and separate authorization.'},
        'human_review_points':[{'id':c['id'],'point':c['human_review_point']} for c in results['cases']],
        'luna_tasks':'LUNA_TASK.md; no automatic activation, engine calls or research changes.',
        'verification':{'tests_passed':22,'new_cycle_tests':5,'frozen_gate_tests':6,'existing_position_pipeline_tests':11,
            'pv_legality':'All372 explicit reply PVs validated from the correct reply-child position',
            'remaining_review':'New KIF/display assembly assigned to Luna; GUI review not performed'},
        'evidence_sha256':{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest()
            for name in ('PLAN.md','selections.json','results.json','engine_evidence.json','confirmation_plan.json','confirmation_results.json')},
        'stop':True}
    write_json(HERE/'ASTRA_HANDOFF.json',handoff)
    print(json.dumps(handoff['important_numbers'],indent=2))


if __name__=='__main__':
    main()
