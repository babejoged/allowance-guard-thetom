"""Deterministic, offline EVM intent assessment. No signing or RPC."""

import re

MAX_UINT = 2**256 - 1


def address(value):
    if not isinstance(value, str) or not re.fullmatch(r'0x[0-9a-fA-F]{40}', value):
        raise ValueError('Address must be 0x followed by exactly 40 hex digits')
    return value.lower()


def validate(payload):
    if not isinstance(payload, dict) or set(payload) != {'to', 'data', 'value', 'allowlist'}:
        raise ValueError('Required fields only: to, data, value, allowlist')
    to = address(payload['to'])
    data = payload['data']
    if not isinstance(data, str) or len(data) > 8194 or not re.fullmatch(r'0x(?:[0-9a-fA-F]{2})*', data):
        raise ValueError('Calldata must be even-length 0x hex, at most 4096 bytes')
    value = payload['value']
    if not isinstance(value, str) or len(value) > 78 or not re.fullmatch(r'0|[1-9][0-9]*', value) or int(value) > MAX_UINT:
        raise ValueError('Value must be a canonical decimal uint256 string in wei')
    allow = payload['allowlist']
    if not isinstance(allow, list) or len(allow) > 100:
        raise ValueError('Allowlist must be an array of at most 100 addresses')
    return {'to': to, 'data': data.lower(), 'value': value,
            'allowlist': sorted(set(address(a) for a in allow))}


def assess(payload):
    payload = validate(payload)
    reasons, decoded = [], {}
    def reason(code, level, message, **evidence):
        reasons.append(dict(code=code, level=level, message=message, evidence=evidence))

    data = payload['data'][2:]
    selector = data[:8]
    methods = {'095ea7b3': 'approve', 'a22cb465': 'setApprovalForAll', 'a9059cbb': 'transfer'}
    if not data:
        reason('EMPTY_CALLDATA', 'REVIEW', 'Empty calldata: recipient behavior is unknown.')
    elif selector not in methods:
        reason('UNKNOWN_SELECTOR', 'REVIEW', 'Unsupported selector; manual inspection required.', selector='0x'+selector)
    elif len(data) != 136 or data[8:32] != '0'*24 or (selector == 'a22cb465' and int(data[72:], 16) not in (0, 1)):
        reason('MALFORMED_CALLDATA', 'REVIEW', 'Expected exactly two canonical ABI words; address padding must be zero and bool must be 0 or 1.', bytes=len(data)//2)
    else:
        target, amount = '0x'+data[32:72], int(data[72:], 16)
        decoded = {'method': methods[selector], 'selector': '0x'+selector,
                   'recipient' if selector == 'a9059cbb' else 'spender': target}
        if selector == 'a22cb465':
            decoded['approved'] = bool(amount)
        else:
            decoded['amount'] = str(amount)
        if selector == 'a9059cbb':
            reason('TOKEN_TRANSFER', 'REVIEW', 'Direct token movement: verify recipient and raw amount.', recipient=target, amount=str(amount))
        elif amount == 0:
            reason('APPROVAL_REVOKED', 'PASS', 'Calldata requests removal of this approval.', spender=target)
        else:
            if selector == 'a22cb465':
                reason('ALL_ASSETS_APPROVAL', 'BLOCK', 'Operator permission covers all NFTs in this collection.', spender=target)
            elif amount == MAX_UINT:
                reason('UNLIMITED_APPROVAL', 'BLOCK', 'Maximum uint256 allowance requested.', amount=str(amount))
            else:
                reason('BOUNDED_APPROVAL', 'PASS', 'Finite raw-unit allowance requested; verify its size.', amount=str(amount))
            if target not in payload['allowlist']:
                reason('UNTRUSTED_SPENDER', 'REVIEW', 'Spender is absent from your explicit allowlist; no reputation lookup performed.', spender=target)
            else:
                reason('ALLOWLIST_MATCH', 'PASS', 'Spender matches your supplied allowlist.', spender=target)
    if int(payload['value']):
        reason('NATIVE_VALUE', 'REVIEW', 'Transaction also sends native currency; confirm wei value.', wei=payload['value'])
    rank = {'PASS': 0, 'REVIEW': 1, 'BLOCK': 2}
    result = {'decision': max((r['level'] for r in reasons), key=rank.get),
            'decoded': decoded, 'reasons': reasons, 'input': payload,
            'policy_version': '1.0.0',
            'scope': 'Offline ABI interpretation only. PASS is not a safety guarantee; contract identity and execution are unverified.'}
    summary = f"Call to {payload['to']}: intent not decoded; manual review required."
    if decoded:
        target = decoded.get('spender', decoded.get('recipient'))
        detail = ('enabled' if decoded['approved'] else 'disabled') if 'approved' in decoded else decoded['amount'] + ' raw units / token ID (standard unverified)'
        summary = f"{decoded['method']} at {payload['to']} for {target}: {detail}."
    summary += f" Native value: {payload['value']} wei."
    actions = {
        'UNLIMITED_APPROVAL': 'Request only the minimum necessary allowance after verifying token standard and decimals.',
        'ALL_ASSETS_APPROVAL': 'Decline collection-wide permission unless essential; verify operator identity independently.',
        'UNTRUSTED_SPENDER': 'Verify the spender using an independent trusted source before changing your allowlist.',
        'BOUNDED_APPROVAL': 'Check the raw amount or token ID against the intended asset and permission.',
        'APPROVAL_REVOKED': 'Verify the contract and spender; revocation only takes effect after a successful on-chain transaction.',
        'TOKEN_TRANSFER': 'Confirm the recipient, token standard, and raw amount before signing.',
        'NATIVE_VALUE': 'Confirm that the native wei amount is intended.',
        'UNKNOWN_SELECTOR': 'Obtain the verified contract ABI and review or simulate this call before signing.',
        'MALFORMED_CALLDATA': 'Rebuild calldata from the verified ABI; do not sign this malformed request.',
        'EMPTY_CALLDATA': 'Verify recipient behavior and native value before signing.'
    }
    result['intent_summary'] = summary
    result['remediation'] = [actions[r['code']] for r in reasons if r['code'] in actions]
    import hashlib
    import json
    digest = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')).hexdigest()
    result['receipt'] = {'sha256': digest, 'label': 'SHA-256 content hash, not a ZK proof or signature'}
    return result
