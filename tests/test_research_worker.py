"""No production engine work: temporary directories and small subprocesses."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from surprise import worker_control as wc
from surprise.research_worker import REPORT, INPUT_FILES, Worker, atomic_json, digest, fingerprints, legacy_processes, lock_held

ROOT=Path(__file__).resolve().parents[1]
DRIVER=ROOT/'tests/fixtures/worker_driver.py'


def module(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.directory=self.root/REPORT;self.directory.mkdir(parents=True)
        (self.root/'input.txt').write_text('frozen')
        self.env=os.environ | {'PYTHONPATH':str(ROOT)}
        self.processes=[]

    def tearDown(self):
        (self.directory/'hold_query').unlink(missing_ok=True)
        for p in self.processes:
            if p.poll() is None:
                p.send_signal(signal.SIGTERM)
            try:p.communicate(timeout=8)
            except subprocess.TimeoutExpired:
                p.kill();p.communicate()
        self.tmp.cleanup()

    def start(self,command='run'):
        p=subprocess.Popen([sys.executable,str(DRIVER),command],cwd=self.root,env=self.env,
                           stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.processes.append(p)
        return p

    def done(self,p,code=0):
        out,err=p.communicate(timeout=12)
        self.assertEqual(p.returncode,code,(out,err))
        return out+err

    def wait_for(self,predicate):
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            if predicate():return
            time.sleep(0.02)
        self.fail('short fixture deadline exceeded')

    def state(self):return json.loads((self.directory/'worker_state.json').read_text())

    def held_query(self):
        (self.directory/'hold_query').touch()
        p=self.start()
        self.wait_for(lambda:(self.directory/'query_started.json').exists())
        return p

    def test_flock_second_refusal_status_and_safe_stop(self):
        p=self.held_query()
        self.assertTrue(lock_held(self.directory/'worker.lock'))
        self.assertIn('second run refused',self.done(self.start(),1))
        self.assertIn('state: running',self.done(self.start('status')))
        self.assertIn('safe stop requested',self.done(self.start('stop')))
        self.wait_for(lambda:self.state()['stop_requested'])
        self.assertIsNone(p.poll())  # Query not killed by stop command.
        self.assertFalse((self.directory/'deep_checks.json').exists())
        (self.directory/'hold_query').unlink()
        self.done(p,75)
        self.assertEqual(json.loads((self.directory/'deep_checks.json').read_text())['done'],[0])
        self.assertFalse((self.directory/'mate_proof_checks.json').exists())
        self.assertFalse(lock_held(self.directory/'worker.lock'))
        self.done(self.start('resume'))
        self.assertEqual(self.state()['resumed_count'],1)
        self.assertEqual(json.loads((self.directory/'deep_checks.json').read_text())['done'],[0,1])

    def test_signals_save_query_and_stop(self):
        for sig in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP):
            with self.subTest(sig=sig):
                p=self.held_query()
                p.send_signal(sig)
                self.wait_for(lambda:self.state()['stop_requested'])
                (self.directory/'hold_query').unlink()
                self.done(p,75)
                self.assertEqual(json.loads((self.directory/'deep_checks.json').read_text())['done'],[0])
                # Reset ONLY this disposable fixture for the next signal.
                for f in self.directory.iterdir():f.unlink()

    def test_child_signal_is_cooperative(self):
        p=self.held_query()
        self.wait_for(lambda:self.state().get('child_pid'))
        os.kill(self.state()['child_pid'],signal.SIGTERM)
        self.assertIsNone(p.poll())
        (self.directory/'hold_query').unlink()
        self.done(p,75)
        self.assertEqual(json.loads((self.directory/'deep_checks.json').read_text())['done'],[0])

    def test_supervisor_death_keeps_lock_until_child_safe_boundary(self):
        p=self.held_query();p.kill();p.wait(timeout=3)
        self.assertTrue(lock_held(self.directory/'worker.lock'))
        self.assertIn('second run refused',self.done(self.start('resume'),1))
        (self.directory/'hold_query').unlink()
        self.wait_for(lambda:not lock_held(self.directory/'worker.lock'))
        self.assertEqual(json.loads((self.directory/'deep_checks.json').read_text())['done'],[0])
        self.done(self.start('resume'))
        self.assertEqual(self.state()['interrupted_count'],1)

    def test_child_failure_then_resume_skips_completed_stage(self):
        (self.directory/'proof.fail').touch()
        self.assertIn('exit code 9',self.done(self.start(),1))
        before=(self.directory/'deep_checks.json').stat().st_mtime_ns
        self.assertEqual(self.state()['stages']['deep']['status'],'completed')
        (self.directory/'proof.fail').unlink()
        self.done(self.start('resume'))
        self.assertEqual(before,(self.directory/'deep_checks.json').stat().st_mtime_ns)
        manifest=json.loads((self.directory/'worker_manifest.json').read_text())
        self.assertEqual(manifest['execution_status'],'completed')
        self.assertIsNone(manifest['research_verdict'])
        self.assertTrue(manifest['requires_astra_review'])
        self.assertEqual(json.loads((self.directory/'mate_proof_checks.json').read_text())['decision'],'INCONCLUSIVE')
        self.assertIn('research verdict: NOT EVALUATED',self.done(self.start('status')))
        self.done(self.start('resume'))  # Completed means no retry to obtain YES.
        self.assertEqual(before,(self.directory/'deep_checks.json').stat().st_mtime_ns)

    def test_input_mismatch_refuses_without_rewriting_state(self):
        (self.directory/'deep.fail').touch()
        self.done(self.start(),1)
        state=digest(self.directory/'worker_state.json')
        (self.root/'input.txt').write_text('changed')
        self.assertIn('incompatible inputs',self.done(self.start('resume'),1))
        self.assertEqual(state,digest(self.directory/'worker_state.json'))

    def test_fingerprint_covers_files_engine_and_nnue_without_execution(self):
        for name in INPUT_FILES:
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('frozen')
        (self.root/'config/default.yaml').write_text('engine:\n  path: engine/bin\n  eval_dir: eval\n')
        binary=self.root/'engine/bin';binary.parent.mkdir();binary.write_text('not executable machine code')
        binary.chmod(0o700)
        nnue=self.root/'engine/eval/nn.bin';nnue.parent.mkdir();nnue.write_text('weights')
        before=fingerprints(self.root)
        self.assertEqual(set(before['files']),set(INPUT_FILES))
        nnue.write_text('changed weights')
        self.assertNotEqual(before,fingerprints(self.root))
        self.assertEqual(before['engine']['binary_sha256'],digest(binary))

    def test_completed_artifact_tamper_refuses(self):
        self.done(self.start())
        (self.directory/'deep_checks.json').write_text('{}')
        self.assertIn('artifacts changed',self.done(self.start('resume'),1))

    def test_legacy_process_detection_and_refusal(self):
        proc=self.root/'proc';(proc/'1').mkdir(parents=True)
        (proc/'1/comm').write_text('systemd')
        (proc/'1/cmdline').write_bytes(b'init\0')
        (proc/'999999').mkdir()
        (proc/'999999/cmdline').write_bytes(b'.venv/bin/python\0reports/trap_tree_coverage_v2/experiment.py\0deep\0')
        (proc/'999999/cwd').symlink_to(self.root,target_is_directory=True)
        rows=legacy_processes(self.root,proc)
        self.assertEqual([r['pid'] for r in rows],[999999])
        worker=Worker(self.root,check=lambda r:self.fail('fingerprint before legacy refusal'),conflicts=lambda r:rows)
        with contextlib.chdir(self.root),self.assertRaisesRegex(ValueError,'legacy process conflict'):
            worker.run()


class ScriptResumeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proof=module(ROOT/REPORT/'prove_mate.py','worker_test_proof')
        cls.e=cls.proof.e

    def proof_fixture(self):
        source={'source_sha256':'frozen-fixture','hints':{}}
        results={'hint_source_sha256':source['source_sha256'],'hint_positions':0,
                 'new_engine_calls':0,'root_limit_including_rook_move':19,'cases':[]}
        for rm in ('3d3e','3d2d'):
            results['cases'].append({'root_reply':rm,
                'history':self.e.HISTORY+[rm,'4e6g+','7h7i','8f8h+'],
                'sfen':'historical cutoff descendant label preserved verbatim',
                'visited_states':100001,'cutoff':True,'certified':False,
                'mate_distance_after_rook':None,'decision':'INCONCLUSIVE',
                'verification_error':None,'proven_substates':3})
        return source,results

    def test_completed_inconclusive_cases_skipped_verbatim(self):
        with tempfile.TemporaryDirectory() as tmp:
            here=Path(tmp)
            source,results=self.proof_fixture()
            # Use real completed metadata with intentionally historical SFEN labels.
            atomic_json(here/'mate_proof_hints.json',source)
            atomic_json(here/'mate_proof_checks.json',results)
            before=(here/'mate_proof_checks.json').read_bytes()
            with patch.object(self.e,'HERE',here),patch.object(self.proof.Proof,'search',side_effect=AssertionError('must skip completed cases')):
                self.proof.main()
            self.assertEqual(before,(here/'mate_proof_checks.json').read_bytes())

    def test_interrupted_proof_restarts_only_unfinished_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            here=Path(tmp)
            source,results=self.proof_fixture()
            results['cases']=results['cases'][:1]
            atomic_json(here/'mate_proof_hints.json',source)
            atomic_json(here/'mate_proof_checks.json',results)
            seen=[]
            def interrupted(solver,b,remaining):
                seen.append((solver.visited,b.sfen(),remaining,solver.hints))
                raise wc.StopRequested('fixture interruption')
            with patch.object(self.e,'HERE',here):
                with patch.object(self.proof.Proof,'search',interrupted),self.assertRaises(wc.StopRequested):
                    self.proof.main()
                self.assertEqual(json.loads((here/'mate_proof_checks.json').read_text()),results)
                def cutoff(solver,b,remaining):
                    seen.append((solver.visited,b.sfen(),remaining,solver.hints))
                    solver.visited=100001;raise self.proof.Limit()
                with patch.object(self.proof.Proof,'search',cutoff),contextlib.redirect_stdout(io.StringIO()):
                    self.proof.main()
            self.assertEqual(seen[0],seen[1])  # fresh solver, same root/depth/hints
            self.assertEqual(seen[0][0],0)
            self.assertEqual(len(json.loads((here/'mate_proof_checks.json').read_text())['cases']),2)

    def test_cancellation_unwinds_board_and_stack(self):
        b=self.e.Position.startpos().board;original=b.sfen()
        solver=self.proof.Proof({})
        with patch.object(wc.control,'checkpoint',side_effect=[None,wc.StopRequested('stop')]):
            with self.assertRaises(wc.StopRequested):solver.search(b,2)
        self.assertEqual(b.sfen(),original)
        self.assertFalse(solver.stack)

    def test_deep_ledger_cached_query_and_query_boundary_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            here=Path(tmp)
            class FakeEngine:
                cache=None
                def search(*args):raise AssertionError('completed query must not run')
            memo=self.e.Memo.__new__(self.e.Memo);memo.engine=FakeEngine()
            p=self.e.Position.startpos();key=f'{p.sfen}|100000|1'
            memo.data={'requests':{key:{'result':{'saved':True},'cache_hit':False}}}
            with patch.object(self.e,'HERE',here):
                self.assertEqual(memo.query(p,100000),{'saved':True})
                with patch.object(wc.control,'checkpoint',side_effect=wc.StopRequested('stop')):
                    with self.assertRaises(wc.StopRequested):memo.query(p,100000)

    def test_real_memo_saves_before_cooperative_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            here=Path(tmp)
            from surprise.engine import EngineResult,Score
            class FakeCache:
                def get(self,key):return None
            class FakeEngine:
                cache=FakeCache()
                def _key(self,*args):return 'fake-key'
                def search(self,*args):return [EngineResult(Score('cp',score_cp=1))]
            memo=self.e.Memo.__new__(self.e.Memo);memo.engine=FakeEngine();memo.data={'requests':{}}
            p=self.e.Position.startpos()
            with patch.object(self.e,'HERE',here),patch.object(wc.control,'checkpoint',side_effect=[None,wc.StopRequested('stop')]):
                with self.assertRaises(wc.StopRequested):memo.query(p,100000)
            saved=json.loads((here/'engine_evidence.json').read_text())
            self.assertEqual(saved['requests'][f'{p.sfen}|100000|1']['result']['score']['score_cp'],1)

    def test_completed_deep_groups_do_not_query_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            here=Path(tmp)
            for name in ('candidate_coverage.json','reply_coverage.json'):
                (here/name).write_bytes((ROOT/REPORT/name).read_bytes())
            with patch.object(self.e,'HERE',here):
                templates=list(self.e.deep_groups())
                for group in templates:
                    group['levels']=[{'nodes':n,'results':{m:{} for m in group['moves']}} for n in self.e.LEVELS]
                    group['stable']=False  # endpoint completion != stable scientific verdict
                atomic_json(here/'deep_checks.json',{'groups':templates})
                self.assertTrue(self.e.deep_progress()['complete'])
                class NoQuery:
                    def query(*args):raise AssertionError('completed group queried')
                self.e.deep(NoQuery())


if __name__=='__main__':unittest.main()
