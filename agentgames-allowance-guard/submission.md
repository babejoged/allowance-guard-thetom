# Allowance Guard — Wildcard submission draft

**One line:** A local policy agent that explains EVM token permissions before a user signs.

**Problem:** Wallet prompts expose calldata, but users need understandable evidence about spender permissions, unlimited allowances, collection-wide operators, and unknown calls.

**Working demo:** Run `python3 server.py --port 8765` and open `http://127.0.0.1:8765`. Select Unlimited approval, Bounded approval, NFT operator, or Unknown call, then assess. Each result shows an intent decode, ordered reason codes, evidence, and a downloadable SHA-256 content receipt.

**Agent behavior:** The service automatically validates, decodes, evaluates policy, and emits a receipt. It is deterministic and does not use an LLM. It is a useful off-chain review workflow, not an autonomous wallet executor.

**Deployment artifact:** Render Docker configuration with an unprivileged Nginx gateway, exact configured HTTPS Origin validation, and documented setup. Container execution remains unverified because Docker/Nginx are unavailable locally; public deployment remains pending.

**Intent explanation:** Deterministic summary and suggested remediation are included in the UI/API and bound by the receipt hash; no LLM-generated advice or ZK proof is claimed.

**Implementation:** Python standard library HTTP service and static HTML/CSS/JavaScript UI. Strict input validation, bounded bodies, exact ABI word parsing, explicit user allowlist, no external reputation claims, no arbitrary-input network requests, no credentials or signing.

**Trust boundary:** PASS is not a safety guarantee. Contract identity, actual execution, token standard, token decimals, and on-chain state are unverified. Unknown or malformed supported calldata is REVIEW. ERC-20 approve and ERC-721 approve share a selector. All examples use fictional addresses.

**zkVerify:** Not integrated. The receipt is a SHA-256 content hash, not a zero-knowledge proof, signature, or on-chain attestation. No proof or verification claim is made.

**Verification:** `python3 -m unittest -v` runs policy/input adversarial cases, receipt reproducibility, and actual loopback HTTP requests. See `QA.md` for observed results.

**Public repository:** PENDING — not published.

**Public HTTPS endpoint:** PENDING — not deployed.

**Public demo/writeup:** PENDING — this local draft is ready to publish after review.

**Submission state:** Prepared locally; not entered or posted. Competition eligibility and final submission requirements must be confirmed before entry.

**License:** MIT.
