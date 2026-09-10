"""Offline evidence assembly; Astra's statuses never feed back into move selection."""
import json
from pathlib import Path
from collections import Counter
from surprise.research import cp,write_json
from explore import assemble,HISTORY,position,identity

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def main():
    evidence=json.loads((HERE/'evidence.json').read_text());tree=assemble(evidence)
    judgments=json.loads((HERE/'interpretation.json').read_text());checks=json.loads((HERE/'confirmation.json').read_text())
    engine=json.loads((HERE/'engine_evidence.json').read_text())
    summaries=[]
    for b,original in zip(tree['branches'],evidence['branches']):
        move=b['opponent_move'];j=judgments['branches'][move]
        c=next(c for c in original['candidates'] if c['move']==b['our_response'])
        pair=[r for r in checks if r['branch']==move]
        good=next(r for r in pair if r['role']=='best10k');wrong=next(r for r in pair if r['role']=='highest_salience_error10k')
        checked_gap=cp(good['result'])-cp(wrong['result'])
        b['mechanical_branch_status']=b['branch_status'];b.update(j)
        b['candidate_initial_cost_cp']=c['candidate_initial_cost_cp']
        b['opponent_natural_replies']=[{'move':r['move'],'gap10k':r['gap'],'naturalness_proxy':r['salience']|{'signals':r['signals']}}
                                       for r in c['responses'] if r['move'] in c['displayed_replies'] and r['natural_proxy']]
        b['opponent_best_replies']=[{'move':r['move'],'gap10k':r['gap']} for r in c['responses'] if r['gap'] is not None and r['gap']<=100]
        b['best_vs_natural_gap_cp']={'full10k':next(r['gap'] for r in c['responses'] if r['move']==wrong['reply']),
            'selected100k_pair':checked_gap,'correct10k_reply':good['reply'],'error10k_reply':wrong['reply'],
            'warning':'Negative100k gap means the alleged error is better. Not a full100k best-defense reference.'}
        b['penalty_if_opponent_misses']=b['best_vs_natural_gap_cp']
        b['continuation_depth']=4;b['confirmation']=pair
        b['human_policy_reliability']='No model used; no calibrated frequencies or repertoire success probability'
        pc=position(HISTORY+[move,b['our_response']]);node=next(n for n in tree['nodes'] if n['id']==identity(pc.sfen));node['status']=b['branch_status']
        if j.get('normal_alternative'):
            pn=position(HISTORY+[move,j['normal_alternative']]);next(n for n in tree['nodes'] if n['id']==identity(pn.sfen))['status']='normal_branch'
        summaries.append({
            'opponent_move':move,'why_opponent_move_is_plausible':b['plausibility'],'root_loss_cp':b['root_loss'],
            'our_response':b['our_response'],'initial_cost':c['candidate_initial_cost_cp'],'initial_cost_scope':c['cost_reference_scope'],
            'best_defense':b['opponent_best_replies'],'opponent_natural_replies':b['opponent_natural_replies'],
            'natural_wrong_responses':[r|{'label_scope':'alleged error at10k; check100k contradiction before display'} for r in b['opponent_natural_replies'] if r['gap10k']>=300],
            'punishment_if_missed':b['best_vs_natural_gap_cp'],'branch_status':b['branch_status'],
            'mechanical_branch_status':b['mechanical_branch_status'],'known_or_unknown_motif':j['known_or_unknown_motif'],
            'human_review_point':j['human_review_point'],'compensation':j['compensation'],
            'surprise_move_decision':j['surprise_move_decision'],'human_policy_reliability':b['human_policy_reliability'],
            'normal_alternative':j.get('normal_alternative')})
    for n in tree['nodes']:n['absolute_ply_min']=20+n['ply']
    tree['role_scope']='All best_reply/punishment edge roles describe10k selection, NOT validated100k quality; use branch confirmation/status warnings.'
    tree['root_ancestry_audit']={'source':'reports/tactical_falsification_v2/results.json:prefix_deviation_audits and bishop_block_rook_sacrifice.prefix_trajectory through20ply',
        'interpretation':'Known sharp20ply setup, no old17.B7g scaffold. Prior root881cp versus child155cp horizon swing remains a warning; not an independent exhaustive naturalness audit.'}
    tree['trap_tree_method_result']=judgments['trap_tree_method_result'];tree['next_step_decision']=judgments['next_step_decision']
    tree['novelty_result']=judgments['novelty_result']
    write_json(HERE/'tree.json',tree)
    numbers={'root_legal_replies':len(evidence['root_replies']),'root_branches':len(summaries),
        'tested_our_candidates':sum(len(b['candidates']) for b in evidence['branches']),
        'full_candidate_reply_evaluations':sum(len(c['responses']) for b in evidence['branches'] for c in b['candidates']),
        'gate_rejected_candidates':sum(c['gate']['decision']=='reject' for b in evidence['branches'] for c in b['candidates']),
        'new_engine_requests':engine['new_requests'],'cache_hits':engine['cache_hits'],'new100k':engine['new100k'],
        'confirmation_positions':len(checks),'nominal_requested_nodes':sum(r['nodes'] for r in engine['requests'].values()),
        'nodes':len(tree['nodes']),'edges':len(tree['edges']),
        'nodes_with_multiple_histories':sum(len(n['histories'])>1 for n in tree['nodes']),
        'branch_status_counts':dict(Counter(b['branch_status'] for b in summaries)),
        'root_losses_cp':[b['root_loss_cp'] for b in summaries],
        'selected_pair_gaps100k':[b['punishment_if_missed']['selected100k_pair'] for b in summaries],
        'regressions_passed':len(evidence['regressions']),'human_policy_calls':0}
    handoff={
        'research_question':'Can a bounded mechanical search construct a meaningful opening trap graph across opponent deviations?',
        'source_checkpoint':{'research':'d58a9b3bef8e909d67fd452578277860cdfacb11','display':'94e1b24e99c811e82415f9c1ef0792993dc8b68a','plan':'b52514e49a056d7a6beeaa0f296e4d850aa26efb','before_confirmation':'a38a7c5f7cbfe3295601a60a43770d1d75c7839b'},
        'root_position':{'sfen':evidence['root_sfen'],'history':HISTORY,'us':'gote','turn':'sente'},
        'conclusion':'Graph construction and two conditional tactical contrasts succeeded. One natural defense refutes the tested continuation and one trap ranking reverses at100k. The candidate slate also missed the quiet P*2c reference. Meaningful reliable repertoire construction remains INCONCLUSIVE.',
        'next_step_decision':judgments['next_step_decision'],'decision_target':judgments['decision_target'],
        'trap_tree_method_result':judgments['trap_tree_method_result'],'novelty_result':judgments['novelty_result'],
        'confirmed_facts':['4 opponent branches,8 our candidates, maximum4ply generated without forced reference continuations',
            '3 newly evaluated candidates rejected by frozen gate;3 saved reject regressions still reject',
            'Mechanical trap flags were4; research statuses are2 traps,1 tested-continuation refutation,1 needs_review',
            'B*7g branch wrong gold recapture has1080cp selected100k deficit; R3e horse-capture branch455cp',
            'R3f alleged gold-recapture error improves by830cp versus the10k-preferred bishop check at100k',
            'No engine/policy replacement, external opening lookup, model use, mass scan or production activation'],
        'unknowns':['Actual human branch probabilities, salience and difficulty','Reliability of550cp shallow initial-cost estimate',
            'Full100k reply rankings','Broader repertoire coverage and exact-line novelty','Benefit over a larger engine shortlist or quiet-move proposal baseline',
            'Whether R2d Gx6g followed by R8h+ poses further difficult decisions beyond the4ply tree; local refutation is not a global practical verdict'],
        'important_numbers':numbers,'tree_summary':{'file':'tree.json','data':'evidence.json','depth':4,'normal_option':'R3f branch -> Bx3f Px3f;10k only',
            'transposition':'Board/turn/hands identity; actual merge count reported, commuting-order unit test separate'},
        'branches':summaries,
        'human_policy_reliability':{'used':False,'prior_independent_validation':'NO','repertoire_success_probability':None},
        'human_report':{'lead':'A small tree was built, but4 shallow trap flags did not all survive scrutiny; benchmark verdict INCONCLUSIVE.',
            'show':'Four-branch tree, gold versus bishop recapture, natural Gx6g refutation, R3f ranking reversal, normal alternative',
            'avoid':['Blind rediscovery','Novel discovery','Human probabilities','Unique hard defense','Production readiness','All branches are traps'],
            'raw_eval_convention':'positive=sente advantage; gote advantage remains negative',
            'roles':'Graph edge labels are10k mechanical roles; do not hide later contradictory100k evidence'},
        'human_review_points':[b['human_review_point'] for b in summaries],
        'next_research_question':'Only after review: improve quiet candidate coverage and response salience/robustness without changing this frozen benchmark retrospectively.',
        'luna_tasks':'LUNA_TASK.md: deterministic KIF/tree display only; no Luna agent invoked',
        'verification':{'tests_passed':22,'tree_tests':5,'frozen_gate_tests':6,'existing_tests':11,'legal_reply_PVs_checked':694,
                        'new_KIF_or_GUI_review':False},
        'production_gate_decision':'INCONCLUSIVE, unchanged','stop':True}
    write_json(HERE/'ASTRA_HANDOFF.json',handoff)
    print(json.dumps(numbers,indent=2))


if __name__=='__main__':main()
