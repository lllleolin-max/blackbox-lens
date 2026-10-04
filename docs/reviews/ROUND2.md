# Independent audit — round 2

**Source:** `4ef10b40372de9202cb67a468d88987209378909` (`main`), clean before and after review. **Compared with:** `92e57271df26ff5a96de85d563a7739c8b733f68`. **Date:** 2026-10-05, Asia/Shanghai. **Auditor:** independent GPT-6.1-Sol / Ultra agent; no product code/tests edited.

**Score: 99.5/100 under the unchanged pre-implementation rubric.** All four round-1 findings are independently verified resolved. No demonstrated unresolved critical/high/medium/low defect remains in the tested scope. The remaining half-point is the previously recorded **unverified rendered-report usability property**, not a newly invented defect. This is the second distinct source version with real product repairs; the user's third implementation/review iteration is still required before release.

This score describes **AI delivery review of a bounded behavioral prototype**. It is not scientific discovery, hidden-reasoning recovery, human peer review, market validation or real-world model validation. No authenticated provider or real model was run. HTTP evidence remains local mock integration. Actual browser rendering remains unverified; source, data, escaping and self-containment are verified.

## Fixed criterion scores

| Area | Awarded / available |
|---|---:|
| Scientific validity, S1–S5 | 25 / 25 |
| Correctness, C1–C5 | 25 / 25 |
| Failure/security/privacy, F1–F4 | 20 / 20 |
| Reproducibility/tests, R1–R4 | 15 / 15 |
| Usability/docs, U1–U3 | 9.5 / 10 |
| Portability/release, P1–P2 | 5 / 5 |

Criterion awards: **S1 5, S2 5, S3 7, S4 5, S5 3; C1 8, C2 6, C3 4, C4 4, C5 3; F1 5, F2 5, F3 5, F4 5; R1 4, R2 4, R3 4, R4 3; U1 4, U2 3, U3 2.5; P1 3, P2 2**. The 3.5-point increase follows actual fixes: C3 +1, F2 +1, R1 +0.5, S5 +0.5 and P1 +0.5. No criteria or threshold changed.

## Resolution evidence

| Finding | Status and independently observed result |
|---|---|
| **R1-01 Medium — three-choice hint/hash instability** | **Resolved.** Hint selection now sorts accepted labels before selecting a wrong semantic choice. The original external three-choice fixture produces the same suite hash and `B` in both map insertion orders. The new product regression exercises all six insertion orders and confirms identical label/semantic answers. SELF_REVIEW corrects its earlier overstated repair claim. |
| **R1-02 Medium — malformed adapter metadata traceback** | **Resolved.** Strict decoding validates the complete decoded object through finite UTF-8 canonical serialization, which normalizes errors to `SuiteError`. Independent literal `1e999` and lone-surrogate manifest fixtures now produce SDK `SuiteError`, CLI exit **2**, `Error: invalid strict JSON`, **no traceback and no analysis directory**. Product regression also covers a lone surrogate JSON key. |
| **R1-03 Low — unclear standalone pooling** | **Resolved.** Generated HTML has three `Variant kind (pooled)` headers, total repeat conditions, explicit case/variant condition identity, summed valid-pair weighting and repeat-pair weighting. Numeric definitions and independent counts remain unchanged. |
| **R1-04 Low — missing source-archive docs/examples** | **Resolved.** `MANIFEST.in` includes Markdown docs and JSON examples. The auditor independently built an sdist from the exact Git archive, listed the actual archive contents and executed its checker: nine required files present, including methods/rubric/examples; source and bundled demo match. CI runs this check on built archives. |

These are real changes to adapter behavior, input validation, report explanation and distribution completeness. They are more than new report text or score changes.

## Exact execution evidence

Environment: Windows AMD64, Python **3.14.3**. All auditor-generated files live outside the product repository under `work/blackbox-lens-project/reviews/`. Full round-1 source inspection remains applicable to unchanged files; this review inspected the entire diff and every new source/test/distribution file. Product tracked tree stayed clean.

1. `git rev-parse HEAD`, `git status --porcelain`, and `git diff 92e5727 HEAD`: exact SHA above, clean tree, ten changed files. Runtime changes are `adapters.py`, `suite.py`, `report.py`; new archive inclusion/checking and regressions are separately inspected.
2. `git archive --format=zip HEAD` → `round2-source.zip`, extracted to `round2-build-src`; `python -m pip wheel --no-deps --wheel-dir <reviews>/round2-wheel <reviews>/round2-build-src`: **success**. Wheel `blackbox_lens-0.1.0-py3-none-any.whl`, **26,017 bytes**, SHA256 **`c2593cf72baccd8a414a315637ca0d04c0ec3cde189e3744473cb3d56aaa33d9`**. Log: `round2-wheel-build.txt`.
3. Fresh `round2-venv`, install only that wheel with `--no-index --no-deps`, then execute tests from outside checkout, without source-path injection: **30 tests passed in 11.652s**, exit 0. Logs: `round2-wheel-install.txt`, `round2-installed-tests.txt`.
4. `<round2-venv>/python <reviews>/probes.py`: **10/10 independent probes passed**, exit 0. Log: `round2-probes.json`. Mixed status arithmetic remains 12 planned, 11 observed, 8 valid, 1 invalid, 2 errors, 1 missing, 4 correct; strict accuracy 1/3 and valid accuracy 1/2. Eligible semantic comparisons and repeat disagreement independently reconcile. Zero-valid rates stay N/A; parser, shuffled plan, interrupt/missing slots, cached-summary tampering, malicious HTML, input caps, escaped dummy key and slow-header deadline remain correct. Configured 0.1s slow-header deadline produced `timeout` in **0.101s** in this run.
5. `<round2-venv>/python installed_smoke.py <reviews>/round2-artifacts <reviews>/round2-build-src`: installed module confirmed under that venv; version/help/plan/demo/analyze all exit 0. Default CLI demo **54/54 observed/valid, 36 correct, zero invalid/errors/missing**. SDK fixture **6 planned/valid, 4 correct**. Generated JSON and HTML are byte-identical after reanalysis. Log: `round2-installed-smoke.json`; artifacts: `round2-artifacts/cli-demo`, `cli-analysis`, `sdk-demo`.
6. `<round2-venv>/python round1_edge_evidence.py <reviews>/round2-artifacts`: original two round-1 bad-metadata fixtures now fail correctly and create no output. Log: `round2-edge-evidence.json`.
7. Isolated auditor build-tools environment (`audit-build-venv`, build 1.6.1) ran `python -m build --sdist --outdir <reviews>/round2-sdist <reviews>/round2-build-src`: **success**, declared build isolation uses setuptools 84.0.0 satisfying `>=77`. Initial global `python -m build` attempt lacked the optional development frontend; it was rerun in this dedicated tools environment and is **not a product runtime defect**. Logs: `audit-build-tools-install.txt`, `round2-sdist-build.txt`.
8. Independently opened the actual `round2-sdist/blackbox_lens-0.1.0.tar.gz`; invoked `check_sdist(Path(<reviews>/round2-sdist))` and checked generated HTML headers/weighting: **pass**, nine required archive files present. Log: `round2-archive-html-check.txt`.
9. Independently read GitHub run and job API: exact reviewed `head_sha`, completed **success**, all four **Ubuntu/Windows × Python 3.11/3.14** jobs success. [Actual CI run 37232208886](https://github.com/lllleolin-max/blackbox-lens/actions/runs/37232208886). Local auditor's machine is Windows; Ubuntu verification is the actual remote CI result.

The built and installed package still has no declared runtime dependency beyond Python's standard library. Local mocks verify the same optional HTTP boundary as round 1; no claim is made about provider-specific live compatibility, fresh sampling independence, empirical model behavior or general scientific reliability.

## Release and next-version decision

The ≥95 and zero-critical/high quality gate passes on the bounded evidence. **Do not release yet solely from this report:** complete the requested third real source version and independent review. Per-case/variant contrast visibility is a defensible next usability improvement; it must preserve pairing, excluded/missing denominators, semantic interpretation and the existing pooled totals. No new defect is asserted merely to justify the third iteration.
