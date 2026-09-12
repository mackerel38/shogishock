import importlib.util
from pathlib import Path
import unittest

P=Path(__file__).with_name('experiment.py')
spec=importlib.util.spec_from_file_location('coverage_experiment',P)
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)


class CoverageTests(unittest.TestCase):
    def test_quiet_pawn_drop_general_rule(self):
        p=e.position(e.HISTORY+['3d2d'])
        self.assertIn('pawn_drop_setup',e.motive(p,'P*2c')['human_motivation_tags'])
        self.assertIn('pawn_drop_setup',e.motive(p,'P*2e')['human_motivation_tags'])

    def test_gold_motives(self):
        for root in e.ROOT_MOVES:
            p=e.position(e.HISTORY+[root,'4e6g+'])
            for move in ['7h7i','7h8g']:
                f=e.motive(p,move)
                self.assertIn('escape_attacked_piece',f['human_motivation_tags'])
                self.assertTrue(f['heuristic_only'])

    def test_rook_counterattack_and_legality(self):
        p=e.position(e.HISTORY+['3d2d','4e6g+'])
        self.assertIn('counterattack',e.motive(p,'2d2a+')['human_motivation_tags'])
        q=e.position(e.HISTORY+['3d3e','4e6g+'])
        self.assertNotIn('2d2a+',q.legal_moves())

    def test_100cp_is_not_10k_confirmation(self):
        a={'score':{'score_type':'cp','score_cp':0,'bound':'exact'},'best_move':'x','pv':['x','y']}
        b=a|{'score':a['score']|{'score_cp':101}}
        self.assertFalse(e.transition({'m':a},{'m':b},0)['stable'])

    def test_mate_is_not_centipawn(self):
        r={'score':{'score_type':'mate','mate_distance':-19,'bound':'exact'},'best_move':'x','pv':['x']}
        self.assertIsNone(e.cp(r))
        self.assertTrue(e.transition({'m':r},{'m':r},0)['stable'])

    def test_position_identity_ignores_only_number(self):
        p=e.position(e.HISTORY)
        self.assertEqual(e.identity(p.sfen),e.identity(' '.join(p.sfen.split()[:3])+' 1'))
        self.assertNotEqual(e.identity(p.sfen),e.identity(p.apply_move('3d2d').sfen))

    def test_original_rejects(self):
        e.regressions()
        self.assertEqual([x['verdict']['decision'] for x in e.load('regressions.json')],['reject']*3)

    def test_proof_terminal_and_one_ply(self):
        ps=importlib.util.spec_from_file_location('mate_proof_test',P.with_name('prove_mate.py'))
        proof=importlib.util.module_from_spec(ps);ps.loader.exec_module(proof)
        item=next(x for x in e.load('deep_checks.json')['mate_hypotheses'] if x['id']=='3d3e_before_rook')
        r=next(x['result'] for x in item['levels'] if x['pv_terminal_checkmate'])
        b=e.position(item['history']).board
        for move in r['pv'][:-1]:b.push(e.shogi.Move.from_usi(move))
        solver=proof.Proof({});root=solver.search(b,1)
        self.assertIsNotNone(root)
        self.assertEqual(proof.verify(root,solver.proven),1)
        b.push(e.shogi.Move.from_usi(r['pv'][-1]))
        terminal=proof.Proof({});root=terminal.search(b,0)
        self.assertEqual(proof.verify(root,terminal.proven),0)

    def test_proof_cannot_omit_defender_moves(self):
        ps=importlib.util.spec_from_file_location('mate_proof_test',P.with_name('prove_mate.py'))
        proof=importlib.util.module_from_spec(ps);ps.loader.exec_module(proof)
        node={'sfen':e.Position.startpos().sfen,'remaining':2,'terminal':False,'children':{}}
        with self.assertRaises(AssertionError):proof.verify('root',{'root':node})


if __name__=='__main__':unittest.main()
