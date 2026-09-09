"""Copy an explicit public allowlist into an isolated clone; never touch source git/data."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
REMOTE='https://github.com/mackerel38/shogishock.git'
DOCS=['.gitignore','pyproject.toml','Dockerfile','README.md','HANDOFF.md','PAUSE.md','RESEARCH.md',
      'RESEARCH_V2.md','RESEARCH_V3.md','SHOGIHOME.md','BACKUP.md','CHECKPOINTING.md','PUBLIC_CHECKPOINT.md']
REPORTS={
 'reports/independent_policy_validation':['SAMPLING_PLAN.md','LUNA_TASK.md','frozen_model_fingerprint.json',
    'acquisition_status.json','dataset_fingerprint.json','dataset_summary.json','measurement_seal.json',
    'metrics.json','exploratory_comparison.json','report.html','REVIEW.md','analysis.md','decision.json'],
 'reports/response_calibration':['PLAN.md','analysis.md','metrics.json','decision.json',
    'provenance.json','review_provenance.json','bootstrap.json','victim_slices.json','review.json','review.html','REVIEW.md'],
 'reports/pass_pilot':['analysis.md','checkpoint.json','manifest.json','summary.json'],
 'reports/reach_pilot':['analysis.md','SOURCES.md','pilot_summary.json','pilot_diagnostics.json',
    'diagnostic_manifest.json','confirmation_selection.json','reach_summary.json','planning_summary.json','report_sente.html','report_gote.html'],
 'reports/terashock_seed_audit':['analysis.md','summary.json','manifest.json'],
 'reports/human_pilot':['SAMPLING_PLAN.md','SEED_UNIVERSE_AMENDMENT.md','SPLIT_CORRECTION.md','analysis.md',
    'sampling_config.json','sampling_summary.json'],
 'reports/human_policy_v2':['analysis.md','policy_metrics.json','policy_decision.json','behavior_calibration.json',
    'book_policy_slices.json','seed_reach_join_summary.json','calibration.html'],
 'reports/human_e2e':['analysis.md','candidates.json','human_responses.json','manifest.json','summary.json',
    'report_sente.html','report_gote.html'],
 'reports/response_set_review':['review_manifest.json','report_actual_candidate.html',
    'report_diagnostic_counterexample.html','report_control.html'],
}


def main(target):
    target=Path(target).resolve()
    if target==ROOT or ROOT in target.parents or not (target/'.git').is_dir():
        raise ValueError('target must be a separate verified Git clone')
    remote=subprocess.check_output(['git','-C',str(target),'remote','get-url','origin'],text=True).strip()
    if remote!=REMOTE:raise ValueError('unexpected remote')
    paths=[Path(p) for p in DOCS]
    for directory,extensions in [('surprise',{'.py'}),('tests',{'.py'}),('config',{'.yaml'}),
                                  ('scripts',{'.py','.mjs','.sh'})]:
        paths += [p.relative_to(ROOT) for p in (ROOT/directory).iterdir() if p.is_file() and p.suffix in extensions]
    paths.append(Path('data/opening_seeds.yaml'))
    paths.append(Path('exports/README.md'))
    paths += [Path(directory)/name for directory,names in REPORTS.items() for name in names]
    paths += [p.relative_to(ROOT) for p in (ROOT/'exports/human_e2e').glob('*.kif')]
    paths += [p.relative_to(ROOT) for p in (ROOT/'exports/human_e2e').glob('*.json')]
    for classification in ('actual_candidate','diagnostic_counterexample','control'):
        paths += [p.relative_to(ROOT) for p in (ROOT/'reports/response_calibration'/classification).glob('manifest.json')]
        paths += [p.relative_to(ROOT) for p in (ROOT/'exports/response_calibration'/classification).glob('*.kif')]
        paths += [p.relative_to(ROOT) for p in (ROOT/'reports/response_set_review'/classification).glob('manifest.json')]
        paths += [p.relative_to(ROOT) for p in (ROOT/'exports/response_set_review'/classification).glob('*.kif')]
        paths += [p.relative_to(ROOT) for p in (ROOT/'exports/response_set_review'/classification).glob('*.json')]
    # Old schema-5 explicit reply analyses are engine-generated, not human raw data.
    for kind in ('obvious','confirm'):
        paths += [p.relative_to(ROOT) for p in (ROOT/'reports/reach_pilot'/kind).glob('*.json')]
    published={}
    for rel in sorted(set(paths)):
        source=ROOT/rel
        if not source.is_file():raise ValueError(f'missing expected public file: {rel}')
        destination=target/rel;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,destination)
        published[str(rel)]=hashlib.sha256(destination.read_bytes()).hexdigest()
    # Minimal position metadata needed for HTML/KIF replay, without raw book rows.
    rel=Path('reports/human_e2e/positions.json')
    positions=json.loads((ROOT/rel).read_text())
    keys={'position_id','sfen','side_to_move','ply','move_history','source','parent_book_eval_sente',
          'reach_probability','sample_count','distinct_players_reaching','total_games','occurrence_count',
          'move_distribution','frequency_semantics'}
    destination=target/rel
    destination.write_text(json.dumps([{k:v for k,v in p.items() if k in keys} for p in positions],ensure_ascii=False,indent=2)+'\n')
    published[str(rel)]=hashlib.sha256(destination.read_bytes()).hexdigest()
    manifest={'scope':'public code, aggregated human metrics, generated engine research; not raw training data',
        'sanitized':['reports/human_e2e/positions.json'],
        'excluded':['credentials','engine binary','NNUE','venv','ShogiHome AppImage','human raw games','SQLite','raw/extracted book'],
        'files_sha256':published}
    (target/'PUBLICATION_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'files':len(published),'target':str(target),'bytes':sum((target/p).stat().st_size for p in published)}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--target',required=True);main(p.parse_args().target)
