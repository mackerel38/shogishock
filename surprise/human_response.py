"""Typed-score probability accounting; never silently renormalize missing mass."""
from .research import cp


def response_metrics(responses, reference, attacker_side, tolerances):
    covered=sum(r['human_probability'] for r in responses)
    if covered>1+1e-8:raise ValueError('probability mass exceeds one')
    sign=1 if attacker_side=='sente' else -1
    comparable=reference is not None and all(cp(r['result']) is not None for r in responses)
    accounted=sum(r['human_probability'] for r in responses if cp(r['result']) is not None)
    contribution=sum(r['human_probability']*cp(r['result']) for r in responses if cp(r['result']) is not None)
    complete=comparable and abs(covered-1)<1e-8
    expected=contribution if complete else None
    good={}
    for tolerance in tolerances:
        lower=0.0
        for r in responses:
            flag=sign*(cp(r['result'])-reference)<=tolerance if comparable else None
            r.setdefault('good_by_tolerance',{})[str(tolerance)]=flag
            if flag:lower+=r['human_probability']
        lower=min(1.0,lower)
        good[str(tolerance)]={'lower':lower,'upper':lower if complete else min(1,lower+max(0,1-covered)) if comparable else 1.0,
            'value':lower if complete else None,'reference_is_engine_estimate':True}
    return {'covered_probability':covered,'numeric_covered_probability':accounted,
        'evaluated_human_eval_sum':contribution,'human_expected_eval':expected,'E_human':expected,
        'V_optimal':reference,'human_eval_delta':expected-reference if expected is not None else None,
        'human_gap':sign*(expected-reference) if expected is not None else None,'P_good':good}
