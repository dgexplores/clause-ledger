# Verification record

Verified on 2026-10-22, Python 3.12.

- `python -m pytest -q`: 12 passed.
- `ruff check clause_ledger tests`: passed.
- `python -m clause_ledger.evaluate --check`: six authored fixture cases passed. This is a deterministic regression check, not an independent NLP accuracy benchmark.
- `node --check clause_ledger/static/app.js`: passed.
- Browser walkthrough on localhost: load Cobalt sample, analyze, locate the exact payment quote, save a changes-requested decision, and see version 2 in history. The screenshot in `review-desk.png` captures the actual interface with source highlighting.
- Hosted API/assets smoke at `https://dg-clause-ledger.onrender.com`: root, reference, OpenAPI, JS and CSS returned 200; the conflicting-payment example was analyzed; a second session received 404 for the first session's record; a human decision produced version 2; stale replay received 409; the verifier's own synthetic record was deleted successfully.

The positive PDF test generates a searchable two-page PDF, uploads it through the real subprocess parser, checks all five findings, and verifies page/offset evidence against extracted source text. Negative tests cover malformed, blank, encrypted, oversized and eleven-page documents. The concurrent-writer test verifies exactly one decision commits against a shared version.

Quality review found and fixed two issues: expired records were previously hidden only after a later creation-triggered cleanup, and narrow wording patterns could mark explicitly negated wording clear. Reads/reviews now enforce the 24-hour cutoff; obvious same-line negation receives attention. The latter is conservative lexical handling, not semantic interpretation.

No upstream VendorGuard runtime, LLM inference, enterprise identity, OCR, legal adequacy or independent real-contract extraction accuracy was verified. The initial hosted deployment may precede the final expiry/negation changes; redeploy the latest local commit before treating hosted and local verification as identical.
