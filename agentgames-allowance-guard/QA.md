# Local verification report

## Automated execution

Environment: Python 3.14.9 on Windows; standard library only.

Command, from this directory:

```bash
python3 -m unittest -v
```

Latest observed result: **8 test methods passed in 1.102s (OK)**. Added deployment configuration validation, real HTTP requests with configured HTTPS Origin, rejection of foreign/null/empty/downgraded origins and forged Host/forwarded headers, and deterministic intent summary/remediation checks. New functionality was exercised with failing tests before implementation.

`python3 smoke.py` launched the real CLI with `PUBLIC_ORIGIN=https://demo.example` and returned `/health` 200, `/` 200, matching HTTPS Origin assessment 200/PASS, and foreign Origin 403. This tests HTTP behind simulated TLS termination, not an actual TLS certificate. `node --check web/app.js` passed.

Docker and Nginx are not installed on this host. Container build, Nginx syntax/runtime, Render TLS, rate limiting, and public endpoint behavior are **not verified**; run the Docker build and remote smoke checks documented in README before publishing. Updated UI summary rendering passed JavaScript syntax checks but has not received a new browser interaction test.

Earlier suite coverage follows. Table-driven subtests cover normal and adversarial inputs; this is not a claim of exhaustive verification.

- Bounded allowlisted approval: PASS and decoded amount.
- Policy matrix: unlimited approval, untrusted spender, revocations, NFT operator on/off, invalid ABI bool, transfer, unknown selector, truncated/extra bytes, nonzero address padding, empty data, native value.
- Input boundary: missing/wrong shape, invalid address/hex, nonstring uint, negative/leading-zero/exponent/overflow values, invalid allowlists, extra fields, oversized calldata.
- Receipt: independently recomputed SHA-256, repeatability, change sensitivity, explicit non-ZK label.
- Real ephemeral loopback HTTP server: static assets, health, traversal rejection, assessment, malformed/duplicate/nonfinite JSON, wrong media type, body cap, foreign Origin, chunked framing rejection. Server is cleaned up after tests.

The tests were observed failing before their corresponding implementation slices, then passing after implementation.

## Browser checks

Real Chromium interaction against `http://127.0.0.1:8765`:

- Unlimited example: BLOCK with UNLIMITED_APPROVAL and UNTRUSTED_SPENDER.
- Bounded allowlisted example: PASS; no error text.
- Odd-length calldata (`0x0`): validation error shown and previous result hidden.
- Unknown call: REVIEW with UNKNOWN_SELECTOR. No captured JS errors during this interaction.
- Desktop geometry: no horizontal overflow.
- Mobile viewport: width 390, scroll width 390, one 358px grid column.

Screenshot capture succeeded, but image-provider analysis returned HTTP 403. Therefore visual screenshot review is **unverified**; geometry and rendered DOM checks passed. Browser used a fresh local session because the main Chrome profile was locked; no account/login was needed.

## Remaining limitations

No public deployment, public repository, competition submission, live-chain simulation, contract identity verification, ZK integration, or cryptographic signature. Download button implementation exists but an actual saved browser download was not separately inspected. This report covers local functionality, not a production security certification.
