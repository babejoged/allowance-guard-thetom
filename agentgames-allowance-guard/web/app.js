'use strict';
const el = id => document.getElementById(id);
let receipt = null;
function clearResult() {
  receipt = null;
  el('output').hidden = true;
  el('empty').hidden = false;
  el('error').textContent = '';
}
el('form').addEventListener('input', clearResult);
for (const button of document.querySelectorAll('[data-example]')) {
  button.addEventListener('click', () => {
    clearResult();
    const kind = button.dataset.example;
    const spender = '22'.repeat(20);
    el('to').value = '0x' + '11'.repeat(20);
    el('value').value = '0';
    el('allowlist').value = kind === 'bounded' ? '0x' + spender : '';
    const selector = kind === 'operator' ? 'a22cb465' : kind === 'unknown' ? 'deadbeef' : '095ea7b3';
    const amount = kind === 'unlimited' ? 'f'.repeat(64) : (kind === 'operator' ? '1' : 'c').padStart(64, '0');
    el('data').value = '0x' + selector + '0'.repeat(24) + spender + amount;
  });
}
el('form').addEventListener('submit', async event => {
  event.preventDefault();
  clearResult();
  el('submit').disabled = true;
  const payload = {to: el('to').value, data: el('data').value, value: el('value').value,
    allowlist: el('allowlist').value === '' ? [] : el('allowlist').value.split(/\r?\n/)};
  const snapshot = JSON.stringify(payload);
  try {
    const response = await fetch('/api/assess', {method:'POST', headers:{'Content-Type':'application/json'}, body:snapshot});
    const result = await response.json();
    if (!response.ok) throw new Error(result.message || result.error);
    // Do not show a result as current if fields changed while the request ran.
    const current = {to: el('to').value, data: el('data').value, value: el('value').value,
      allowlist: el('allowlist').value === '' ? [] : el('allowlist').value.split(/\r?\n/)};
    if (JSON.stringify(current) !== snapshot) return;
    receipt = result;
    el('empty').hidden = true;
    el('output').hidden = false;
    el('decision').textContent = result.decision;
    el('decision').className = 'badge ' + result.decision;
    el('scope').textContent = result.scope;
    el('decoded').textContent = result.intent_summary + '\n\nSuggested next steps:\n' + result.remediation.map(step => '- ' + step).join('\n') + '\n\nDecoded fields:\n' + (Object.keys(result.decoded).length ? JSON.stringify(result.decoded, null, 2) : 'No supported intent decoded.');
    el('reasons').replaceChildren();
    for (const reason of result.reasons) {
      const box = document.createElement('div'); box.className = 'finding';
      const title = document.createElement('strong'); title.textContent = reason.code;
      const text = document.createElement('p'); text.textContent = reason.message;
      const evidence = document.createElement('code'); evidence.textContent = JSON.stringify(reason.evidence);
      box.append(title, text, evidence); el('reasons').append(box);
    }
    el('hash').textContent = result.receipt.sha256;
  } catch (error) { el('error').textContent = error.message; }
  finally { el('submit').disabled = false; }
});
el('download').addEventListener('click', () => {
  if (!receipt) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(receipt, null, 2)], {type:'application/json'}));
  const a = document.createElement('a'); a.href = url; a.download = 'allowance-guard-receipt.json'; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
