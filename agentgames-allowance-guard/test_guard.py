import unittest
import importlib.util

A = '0x' + '11' * 20
B = '0x' + '22' * 20

def tx(selector='095ea7b3', amount=12, allow=True):
    return {'to': A, 'data': '0x' + selector + '0' * 24 + B[2:] + format(amount, '064x'), 'value': '0', 'allowlist': [B] if allow else []}

class AssessmentTests(unittest.TestCase):
    def test_bounded_allowlisted_approval(self):
        self.assertIsNotNone(importlib.util.find_spec('guard'), 'assessment module must exist')
        from guard import assess
        r = assess(tx())
        self.assertEqual(r['decision'], 'PASS')
        self.assertEqual(r['decoded']['amount'], '12')
        self.assertIn('BOUNDED_APPROVAL', [x['code'] for x in r['reasons']])

    def test_actionable_summary_and_remediation(self):
        from guard import assess
        result = assess(tx(amount=2**256-1, allow=False))
        self.assertIn('intent_summary', result)
        self.assertIn(B, result['intent_summary'])
        self.assertIn('approve', result['intent_summary'])
        self.assertTrue(any('minimum' in step for step in result['remediation']))
        unknown = assess(tx('deadbeef'))
        self.assertIn('not decoded', unknown['intent_summary'])
        self.assertTrue(any('ABI' in step for step in unknown['remediation']))
        self.assertEqual(result, assess(tx(amount=2**256-1, allow=False)))

    def test_policy_decisions(self):
        from guard import assess
        cases = [
            (tx(amount=2**256-1), 'BLOCK', 'UNLIMITED_APPROVAL'),
            (tx(allow=False), 'REVIEW', 'UNTRUSTED_SPENDER'),
            (tx(amount=0, allow=False), 'PASS', 'APPROVAL_REVOKED'),
            (tx('a22cb465', 1), 'BLOCK', 'ALL_ASSETS_APPROVAL'),
            (tx('a22cb465', 0, False), 'PASS', 'APPROVAL_REVOKED'),
            (tx('a22cb465', 2), 'REVIEW', 'MALFORMED_CALLDATA'),
            (tx('a9059cbb', 42), 'REVIEW', 'TOKEN_TRANSFER'),
            (tx('deadbeef'), 'REVIEW', 'UNKNOWN_SELECTOR'),
            (dict(tx(), data='0x095ea7b3'), 'REVIEW', 'MALFORMED_CALLDATA'),
            (dict(tx(), data=tx()['data']+'00'), 'REVIEW', 'MALFORMED_CALLDATA'),
            (dict(tx(), data='0x095ea7b3'+'f'*24+B[2:]+'0'*64), 'REVIEW', 'MALFORMED_CALLDATA'),
            (dict(tx(), data='0x'), 'REVIEW', 'EMPTY_CALLDATA'),
            (dict(tx(), value='1'), 'REVIEW', 'NATIVE_VALUE'),
        ]
        for p, decision, code in cases:
            with self.subTest(code=code):
                r = assess(p)
                self.assertEqual(r['decision'], decision)
                self.assertIn(code, [x['code'] for x in r['reasons']])
                self.assertTrue(all('evidence' in x for x in r['reasons']))

    def test_receipt_hash_is_reproducible_and_binds_policy(self):
        import hashlib
        import json
        from guard import assess
        r = assess(tx())
        self.assertIn('receipt', r)
        receipt = r.pop('receipt')
        expected = hashlib.sha256(json.dumps(r, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()
        self.assertEqual(receipt['sha256'], expected)
        self.assertIn('not a ZK proof', receipt['label'])
        self.assertEqual(assess(tx()), assess(tx()))
        self.assertNotEqual(receipt['sha256'], assess(tx(amount=13))['receipt']['sha256'])

class ValidationTests(unittest.TestCase):
    def test_strict_input_boundary(self):
        from guard import assess
        bad = [None, [], {}, dict(tx(), to='0x1'), dict(tx(), data='0x0'),
               dict(tx(), data='0xgg'), dict(tx(), value=True), dict(tx(), value=-1),
               dict(tx(), value='01'), dict(tx(), value='1e9'), dict(tx(), value=str(2**256)),
               dict(tx(), allowlist='anything'), dict(tx(), allowlist=['0x1']),
               dict(tx(), chainId=1), dict(tx(), data='0x' + '00'*4097)]
        for p in bad:
            with self.subTest(payload=p):
                with self.assertRaises(ValueError):
                    assess(p)

if __name__ == '__main__':
    unittest.main()
