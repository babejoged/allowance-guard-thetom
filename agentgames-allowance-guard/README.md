# Allowance Guard

Allowance Guard is an offline, deterministic pre-signing review tool for EVM transaction intent. It helps a person pause before signing ERC-20 approvals, ERC-721/1155 operator approvals, and direct token transfers.

## Run locally

Requires Python 3.10+ and no third-party packages:

```bash
cd C:/Users/babej/Desktop/agentgames-allowance-guard
python3 server.py --port 8765
```

Open <http://127.0.0.1:8765>. The service binds to loopback by default. Run tests with:

```bash
python3 -m unittest -v
```

For a deployed HTTPS site, set an exact origin and start the service with `PUBLIC_ORIGIN=https://your-domain.example python3 server.py`. In configured deployment mode, the application never derives origin trust from `Host`, `X-Forwarded-Host`, or `X-Forwarded-Proto`; only an exact match to the configured origin is accepted. Without this setting, the local HTTP same-origin behavior is preserved. Local requests without `Origin` continue to work.

## Deploy on Render with Docker

`Dockerfile`, `deploy.py`, `nginx.conf`, and `render.yaml` provide a Render-ready deployment. Render terminates TLS; the container runs an unprivileged Nginx reverse proxy with request size, timeout, connection, and rate limits in front of the loopback Python service. Nginx strips forwarded-origin headers before proxying. Create a Render web service from this repository, set `PUBLIC_ORIGIN` to the exact public HTTPS origin (for example `https://allowance-guard.example`), and use the generated `render.yaml` settings. No secret or key is required. The host in `PUBLIC_ORIGIN` must be lowercase, with no path, query, fragment, credentials, or trailing slash.

Docker and Nginx were unavailable on the development host, so the container build and proxy process were not executed locally. The Python entrypoint validation is covered by tests; run `docker build -t allowance-guard .` and `docker run --rm -e PUBLIC_ORIGIN=https://your-domain.example -p 10000:10000 allowance-guard` on a Docker host before publishing.

## What it checks

- `approve(address,uint256)` (`0x095ea7b3`): zero revocation, finite amount, and `uint256.max` unlimited approval.
- `setApprovalForAll(address,bool)` (`0xa22cb465`): zero revocation or all-assets operator permission.
- `transfer(address,uint256)` (`0xa9059cbb`): always `REVIEW` because this is direct token movement.
- Unknown selectors, empty data, noncanonical ABI padding, wrong calldata lengths, and invalid bool values become `REVIEW`.
- A nonzero native `value` adds a `NATIVE_VALUE` review finding.
- A spender is trusted only if its exact lowercase address is in the submitted allowlist. There is no invented reputation score or network lookup.
- Every finding has a stable reason code, level, message, and evidence. The output includes a SHA-256 receipt over the assessment content. It is explicitly a content hash, not a ZK proof or signature.

`PASS` means these local rules found no higher-severity finding. It does not establish contract identity, token decimals, balance, bytecode behavior, proxy implementation, recipient safety, simulation success, or execution safety. `approve` has the same selector on ERC-20 and ERC-721, so token standard context still needs separate verification.

## Autonomous assessment workflow

The browser sends four unsigned fields to the local service. The Python service validates the JSON shape and strict hex/address/uint formats, decodes only the listed ABI layouts, applies fixed policy rules, and returns evidence plus a reproducible receipt. No LLM is used or claimed: the autonomous behavior is a deterministic local rules engine. No RPC, chain lookup, wallet, key, signing, analytics, paid service, or arbitrary-input network request exists in this project.

The HTTP service caps request bodies at 16 KiB, rejects chunked framing and duplicate JSON keys, accepts only the exact configured HTTPS origin when `PUBLIC_ORIGIN` is set, sends CSP/security headers, and serves only the three known static assets. Assessment output also includes a deterministic intent summary and remediation checklist. No LLM or ZK proof is used or claimed.

## Limitations and deployment

The included Render Docker deployment adds a hardened reverse proxy, but it does not authenticate users, persist policies, or inspect live chains. It deliberately does not sign or broadcast transactions. A future production system would need independently reviewed ABI parsing, chain-aware contract verification, authenticated policy storage, operational limits, and security review.

## API and receipt verification

`GET /health` reports service health. `POST /api/assess` accepts `Content-Type: application/json` with exactly these required fields:

```json
{"to":"0x1111111111111111111111111111111111111111","data":"0x","value":"0","allowlist":[]}
```

`to` and each allowlist member must be `0x` plus 40 hex digits. Mixed-case is accepted but EIP-55 checksums are not checked. `data` is `0x` plus zero or more complete hex bytes, capped at 4096 bytes. `value` is a canonical unsigned decimal **string** between zero and uint256.max (no signs, leading zeroes, floats, booleans, or exponent notation). Allowlist limit: 100 addresses. Unknown fields are rejected. Invalid input returns HTTP 400 with `INVALID_INPUT`; syntactically valid but unknown/malformed ABI calls return HTTP 200 with `REVIEW` evidence. Oversized HTTP bodies return 413; wrong media type returns 415.

Priority is `BLOCK > REVIEW > PASS`. Revocations do not require allowlist membership. Finite amounts are raw units; even a very large finite allowance can pass the bounded-allowance rule. Addresses are normalized to lowercase; allowlist order and duplicates are canonicalized. The input policy is supplied per request, not an independently trusted store.

To reproduce the receipt, remove the entire `receipt` field from the response, serialize the rest using Python `json.dumps(result, sort_keys=True, separators=(',', ':'), ensure_ascii=True)`, encode UTF-8, and hash with SHA-256. The hash binds the normalized input, policy version, findings and scope; anyone can recompute it, so it supplies no authenticity or independent trust.

## Competition status

This local artifact is prepared for the Wildcard category. A public repository and HTTPS demo endpoint are pending; no deployment or submission posting has been performed from this workspace. See [submission.md](submission.md) for the honest competition description.
