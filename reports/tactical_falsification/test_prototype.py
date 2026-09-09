import unittest
from prototype import classify


def row(move, value, strong=True, kind='cp', bound='exact'):
    return {'move': move, 'strong': strong, 'result': {'score': {
        'score_type': kind, 'score_cp': value if kind == 'cp' else None,
        'mate_distance': value if kind == 'mate' else None, 'bound': bound,
        'perspective': 'sente'}}}


class RuleTests(unittest.TestCase):
    def test_root_not_compared(self):
        result = classify([row('a', 3681), row('b', 3691)], 'gote', ['a', 'b'])
        self.assertEqual(result['witnesses'], ['a', 'b'])

    def test_bad_capture_does_not_reject(self):
        self.assertEqual(classify([row('capture', 2000), row('other', -500, False)],
                                 'sente', ['capture', 'other'])['decision'], 'not_falsified')

    def test_equal_exchange_does_not_reject(self):
        self.assertEqual(classify([row('a', 0)], 'sente', ['a'])['decision'], 'not_falsified')

    def test_weak_capture_does_not_reject(self):
        self.assertEqual(classify([row('a', -3000, False)], 'sente', ['a'])['decision'], 'not_falsified')

    def test_incomplete_duplicate_and_bound_abstain(self):
        for rows, legal in [([row('a', -3000)], ['a', 'b']),
                            ([row('a', -3000)]*2, ['a', 'b']),
                            ([row('a', -3000, bound='lowerbound')], ['a'])]:
            self.assertEqual(classify(rows, 'sente', legal)['decision'], 'needs_verification')

    def test_mates_are_typed(self):
        self.assertEqual(classify([row('a', -3000), row('b', 5, kind='mate')],
                                 'sente', ['a', 'b'])['decision'], 'reject')
        self.assertEqual(classify([row('a', -3000), row('b', -5, kind='mate')],
                                 'sente', ['a', 'b'])['decision'], 'needs_verification')


if __name__ == '__main__':
    unittest.main()
