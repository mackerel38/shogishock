import json
import unittest
from explore import Graph,HERE,HISTORY,gate,position,features
from surprise.position import Position


class TreeTests(unittest.TestCase):
    def test_transposition_merges_histories_and_move_number(self):
        a='7g7f 3c3d 2g2f 8c8d'.split();b='2g2f 8c8d 7g7f 3c3d'.split()
        graph=Graph();first=graph.node(position(a),a,[])
        self.assertEqual(first,graph.node(position(b),b,['alternative_order']))
        changed=Position.from_sfen(' '.join(position(a).sfen.split()[:3])+' 77')
        self.assertEqual(first,graph.node(changed,a,[]))
        self.assertEqual(len(graph.nodes),1)
        self.assertEqual(len(graph.nodes[first]['histories']),2)

    def test_frozen_reject_regressions(self):
        from explore import ROOT
        data=json.loads((ROOT/'reports/tactical_falsification/fixtures.json').read_text())
        for f in data['fixtures'][:3]:
            p=Position.from_sfen(f['position']['sfen']);c=f['candidate']
            rows=[features(p,c['move'],r['move'])|{'result':r['result']} for r in f['evidence']['responses']]
            self.assertEqual(gate.classify(rows,c['attacker_side'],p.apply_move(c['move']).legal_moves())['decision'],'reject')

    def test_tree_edges_histories_and_depth(self):
        tree=json.loads((HERE/'tree.json').read_text());nodes={n['id']:n for n in tree['nodes']}
        for n in nodes.values():
            self.assertLessEqual(n['ply'],4)
            for h in n['histories']:
                self.assertEqual(' '.join(position(HISTORY+h).sfen.split()[:3]),' '.join(n['sfen'].split()[:3]))
        for e in tree['edges']:
            p=Position.from_sfen(nodes[e['from']]['sfen'])
            self.assertEqual(' '.join(p.apply_move(e['move']).sfen.split()[:3]),' '.join(nodes[e['to']]['sfen'].split()[:3]))
            self.assertEqual(e['actor'],'opponent' if p.turn==0 else 'us')
        for b in tree['branches']:
            chosen=next(c for c in b['candidates'] if c['move']==b['our_response'])
            if b['branch_status']=='trap_branch':self.assertEqual(chosen['gate']['decision'],'not_falsified')

    def test_full_evidence_and_pv_legality(self):
        data=json.loads((HERE/'evidence.json').read_text())
        for b in data['branches']:
            p=position(HISTORY+[b['opponent_move']])
            for c in b['candidates']:
                child=p.apply_move(c['move'])
                self.assertEqual(gate.classify(c['responses'],'gote',child.legal_moves()),c['gate'])
                self.assertEqual(len(child.legal_moves()),len(c['responses']))
                for r in c['responses']:
                    follow=child.apply_move(r['move'])
                    for m in r['result']['pv']:follow=follow.apply_move(m)

    def test_reversal_not_presented_as_supported_trap(self):
        tree=json.loads((HERE/'tree.json').read_text())
        b=next(b for b in tree['branches'] if b['opponent_move']=='3d3f')
        self.assertEqual(b['branch_status'],'needs_review')
        self.assertEqual(b['best_vs_natural_gap_cp']['selected100k_pair'],-830)
        self.assertEqual(b['normal_alternative_status'],'normal_branch')


if __name__=='__main__':unittest.main()
