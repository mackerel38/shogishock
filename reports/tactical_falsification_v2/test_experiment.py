import json
import unittest

from experiment import HERE, ROOT, features, gate, position
from surprise.position import Position


class FrozenSemanticsTests(unittest.TestCase):
    def test_selections_legal_and_expected_before_results(self):
        data=json.loads((HERE/'selections.json').read_text())
        self.assertTrue(data['recorded_before_new_engine_evaluation'])
        self.assertEqual(len(data['cases']),4)
        for c in data['cases']:
            self.assertEqual(c['expected_class'],'should_keep')
            parent=position(c['history'].split())
            self.assertEqual(c['candidate_side'],'sente' if parent.turn==0 else 'gote')
            child=parent.apply_move(c['candidate_move'])
            for m in c['obvious_looking_replies']:
                self.assertIn(m,child.legal_moves())

    def test_original_feature_and_gate_outputs_unchanged(self):
        old=json.loads((ROOT/'reports/tactical_falsification/results.json').read_text())
        fixtures=json.loads((ROOT/'reports/tactical_falsification/fixtures.json').read_text())
        for f, saved in zip(fixtures['fixtures'],old['cases']):
            c=f['candidate'];p=Position.from_sfen(f['position']['sfen'])
            rows=[features(p,c['move'],r['move'])|{'result':r['result']} for r in f['evidence']['responses']]
            result=gate.classify(rows,c['attacker_side'],p.apply_move(c['move']).legal_moves())
            self.assertEqual(result['decision'],saved['surprise_move_decision'])
            for r in saved['obvious_replies']:
                computed=next(x for x in rows if x['move']==r['move'])
                for key in ('strong','free_major','can_be_recaptured','signals'):
                    self.assertEqual(computed[key],r[key])

    def test_mere_candidate_capture_and_pawn_contact_not_strong(self):
        p=position('2g2f 8c8d 2f2e 8d8e 7g7f 3c3d 6i7h 4a3b'.split())
        r=features(p,'2e2d','2c2d')
        self.assertIn('captures_candidate',r['signals'])
        self.assertIn('pawn_contact_capture',r['signals'])
        self.assertFalse(r['strong'])

    def test_saved_new_results_replay_and_pvs_are_legal(self):
        data=json.loads((HERE/'results.json').read_text())
        for c in data['cases']:
            p=Position.from_sfen(c['position']);child=p.apply_move(c['candidate_move'])
            result=gate.classify(c['responses'],c['candidate_side'],child.legal_moves())
            self.assertEqual(result,c['final_gate_result'])
            for r in c['responses']:
                follow=child.apply_move(r['move'])
                for m in r['result'].get('pv',[]):
                    follow=follow.apply_move(m)
        self.assertEqual(len(data['reject_regressions']),3)
        self.assertTrue(all(x['result']['decision']=='reject' for x in data['reject_regressions']))

    def test_work_caps_and_separate_decisions(self):
        data=json.loads((HERE/'results.json').read_text())
        self.assertLessEqual(data['work_totals']['new_engine_requests'],600)
        self.assertLessEqual(data['work_totals']['new_100k_requests'],12)
        self.assertEqual(data['human_policy_calls'],0)
        c=next(x for x in data['cases'] if x['id']=='user_pawn_drop_followup')
        self.assertEqual(c['final_gate_result']['decision'],'not_falsified')
        self.assertTrue(c['surprise_move_decision'].startswith('reject'))
        self.assertEqual(data['next_step_decision'],'INCONCLUSIVE')


if __name__=='__main__':
    unittest.main()
