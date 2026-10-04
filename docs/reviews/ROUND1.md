# Independent audit — round 1

**Source:** `92e57271df26ff5a96de85d563a7739c8b733f68` (`main`), clean before and after review. **Date:** 2026-10-05, Asia/Shanghai. **Auditor:** independent GPT-6.1-Sol / Ultra agent; product implementation and tests were not edited by the auditor.

**Score: 96/100.** No demonstrated critical/high finding. The bounded delivery-quality threshold is met on this candidate, but **release is not yet authorized by the requested workflow**: this is only the first of at least three distinct implementation versions and independent review rounds. Two medium and two low findings remain for real implementation improvements. This score was calculated from the frozen rubric, not chosen to approach the requested score.

This is an **AI review of a bounded prototype**, not scientific discovery, hidden-reasoning recovery, independent human peer review, market validation, or real-world model validation. No authenticated provider or real model was tested. Optional HTTP evidence consists of local mock endpoints. HTML source/data/escaping were checked; actual browser rendering was **not** verified because the available browser bridges failed.

## Fixed-rubric score

| Area | Awarded / available | Basis |
|---|---:|---|
| Scientific validity (S1–S5) | 24.5 / 25 | Scope, controls, semantic identity, genuine slots, honest failure/missing denominators and descriptive caveats are supported; standalone pooled weighting needs clearer explanation. |
| Correctness (C1–C5) | 24 / 25 | Independent arithmetic, strict semantic parsing, CLI/SDK and mocked HTTP work. A supported three-choice hint fixture violates stable hash/behavior expectations. |
| Failure/security/privacy (F1–F4) | 19 / 20 | Early escaped-secret and slow-header defects are repaired; artifacts are bounded and HTML escaped. Invalid manifest adapter metadata escapes the intended validation-error boundary. |
| Reproducibility/tests (R1–R4) | 14.5 / 15 | Independently executed source and clean-wheel tests, CLI/SDK, external probes, packaging and exact-SHA CI; regressions miss the two newly reproduced edge cases. |
| Usability/docs (U1–U3) | 9.5 / 10 | Detailed bilingual docs, working help/commands, inspectable offline report; source evidence cannot fully establish rendered legibility. |
| Portability/release (P1–P2) | 4.5 / 5 | Wheel installs and operates outside checkout; four exact-SHA CI jobs succeed. Source distribution omits linked methods/examples. |

Criterion awards are: **S1 5, S2 5, S3 7, S4 5, S5 2.5; C1 8, C2 6, C3 3, C4 4, C5 3; F1 5, F2 4, F3 5, F4 5; R1 3.5, R2 4, R3 4, R4 3; U1 4, U2 3, U3 2.5; P1 2.5, P2 2**. The deductions are attached to separate failing properties: behavior correctness (C3), malformed-input handling (F2), missing regression coverage (R1), standalone interpretation clarity (S5), unverified rendering (U3), and incomplete distribution references (P1). There is no numerical-metric defect demonstrated.

## Findings

### R1-01 — Medium: three-choice planted hint still depends on map insertion order

**Location:** `src/blackbox_lens/adapters.py:82`; `docs/SELF_REVIEW.md` incorrectly states that both generated choices/instructions now sort output labels.

Use a valid case with canonical labels `["yes", "no", "maybe"]`, expected `yes`, and a `misleading-hint` variant. Compare maps `{ "A": "yes", "B": "no", "C": "maybe" }` and `{ "A": "yes", "C": "maybe", "B": "no" }`, with every other suite value unchanged. Both suites have SHA256 `e8ff749aeb96d81c4d17b595492d919b42fd62566b9307895337291342f41942`, but `SyntheticAdapter.respond` returns `B` versus `C`: different wrong semantic answers. The option-order branch and live generated label instruction are already stable; the remaining hint branch uses `next(... mapping.items() ...)`.

**Reproduction/evidence:** `probes.py`, probe `three_choice_hint_behavior_is_hash_stable`; `round1-probes.json` records failure. Supported two-choice/default demo remains correct, so this is a bounded reproducibility/correctness defect rather than broken overall metrics. Make selection stable for the supported multi-choice case and add a meaningful regression. Deduction: C3 −1; related missing regression contributes to R1.

### R1-02 — Medium: malformed adapter metadata produces uncaught exceptions and CLI tracebacks

**Location:** `src/blackbox_lens/engine.py:122`; `suite.py:51–52`; `cli.py:75`.

Copy a valid run and replace manifest adapter metadata with either `{"x": 1e999}` or `{"name": "\ud800"}` (literal JSON escape). The first is parsed into infinity and fails canonical serialization; the second fails UTF-8 encoding. The SDK raises `ValueError` / `UnicodeEncodeError`, rather than the documented invalid-artifact `SuiteError`; CLI `analyze` returns 1 with a full traceback. Both inputs are refused rather than used for metrics, so no fabricated evidence or successful analysis occurs.

**Reproduction/evidence:** `round1_edge_evidence.py`, saved fixtures `round1-overflow_adapter_number/` and `round1-surrogate_adapter_text/`, and `round1-edge-evidence.json`. Normalize these serialization/Unicode errors to a clear bounded validation error; independently validate manifest metadata text as needed. Deduction: F2 −1; related missing regression contributes to R1.

### R1-03 — Low: standalone HTML does not state pooled weighting as clearly as the methods document

**Location:** `src/blackbox_lens/report.py:68–74`.

The three tables label their row key “Condition”, but rows are aggregates by **variant kind**, potentially pooling multiple case/variant conditions with different valid coverage. `docs/METHODOLOGY.md` correctly says that baseline contrasts pool eligible pairs and repeat consistency pools valid repeat pairs rather than equal-weight case/condition rates. That precise aggregation rule is absent from the self-contained report. The arithmetic and row counts are correct; raw trial records remain inspectable.

Use “Variant kind (pooled)” and state the actual pair-weighting beside the corresponding tables. The repeat table can expose total conditions alongside eligible conditions, since the stored summary already contains that value. Deduction: S5 −0.5. This is an interpretation-clarity finding, not a causal-claim or numerical defect.

### R1-04 — Low: source archive omits linked methods and source examples

**Location:** `pyproject.toml` distribution inclusion rules / missing source-archive manifest.

Independently inspected the root-built exact-candidate `root-round1-dist/blackbox_lens-0.1.0.tar.gz`: it contains README, license, source, bundled demo and tests, but no `docs/` or `examples/`. The archive README links `docs/METHODOLOGY.md`, so a source-distribution reader cannot follow that central method explanation locally. The wheel's advertised bundled demo and the full Git checkout both work; this is **not a broken core install**.

Include referenced source documentation/examples in the source distribution, and assert archive contents. Deduction: P1 −0.5. The minimum-setuptools concern from an earlier uncommitted read is superseded: this SHA correctly declares `setuptools>=77`.

## Independent execution evidence

Environment: Windows AMD64, Python **3.14.3**, pip **25.3**. All writes by the auditor are under the external `work/blackbox-lens-project/reviews/` directory. Product source remains unchanged. Every shipped Python module, test file, packaging/CI file, README/methods/self-review, fixture and frozen rubric was inspected; the bundled demo is the same fixture content as the source example.

1. **Exact source and clean status:** `git rev-parse HEAD`; `git status --porcelain` before and after review: exact SHA above, no entries.
2. **Source regression execution:** `PYTHONPATH=<repo>/src; python -m unittest discover -s tests -v`: **27 passed**, 10.815s, exit 0. Evidence: `round1-tests.txt`.
3. **Independent external probes:** `PYTHONPATH=<repo>/src; python <reviews>/probes.py`: **9 passed / 1 failed**, exit 1. Evidence: `round1-probes.json`. Passing probes independently check 12 planned slots with 8 valid, 1 invalid, 2 errors, 1 missing, 4 correct; strict accuracy 4/12, valid accuracy 4/8; option-order 2 agreements/1 flip over 3 valid pairs; control 2 agreements/0 flips over 2 valid pairs; repeat arithmetic; zero-valid N/A rates; exact grammar; seeded execution ordering; interruption; stale report-cache tampering; malicious HTML; suite/plan bounds; map key order for two-choice position bias; and escaped dummy-key refusal.
4. **Repaired privacy and total-header timeout:** dummy key containing a quote and backslash is refused **before output directory creation**. One-byte-at-a-time headers with configured 0.1s timeout now yield `timeout` in about **0.11s**, below the independent 0.35s tolerance. No real credential used.
5. **Independent exact-source wheel:** `git archive --format=zip HEAD` to `round1-source.zip`, extracted to `round1-build-src`; `python -m pip wheel --no-deps --wheel-dir <reviews>/round1-wheel <reviews>/round1-build-src`: success. Wheel `blackbox_lens-0.1.0-py3-none-any.whl`, 25,717 bytes, SHA256 `64d28e40acf7243affc5b1f6311a3012cd3c7734eaf4bba9bc28849d9b0b6362`. Evidence: `round1-wheel-build.txt`.
6. **Clean installation and tests:** created `round1-venv`; installed only the built wheel with `--no-index --no-deps`; ran from outside checkout with no source-path injection: **27 passed**, 10.528s, exit 0. Evidence: `round1-wheel-install.txt`, `round1-installed-tests.txt`.
7. **Installed console and SDK:** `<venv>/python installed_smoke.py <reviews> <reviews>/round1-build-src`: version/help/plan/demo/analyze all exit 0; imported module confirmed inside venv site-packages. Default demo: **54 planned / observed / valid, 36 correct, 0 invalid/error/missing**. SDK minimal fixture: **6 planned / valid, 4 correct**. Reanalyzed JSON and HTML are byte-identical to original generated reports. Evidence: `round1-installed-smoke.json`, `cli-demo/`, `cli-analysis/`, `sdk-demo/`.
8. **Malformed artifact boundary:** `<venv>/python round1_edge_evidence.py`: both described invalid metadata fixtures independently produce uncaught traceback (recorded as failures, not valid runs). Evidence: `round1-edge-evidence.json`.
9. **Exact-SHA cross-platform CI status independently read:** `gh api repos/lllleolin-max/blackbox-lens/actions/runs/37231688203` and `/jobs`: completed/success, `head_sha` exact reviewed SHA; **Ubuntu and Windows, Python 3.11 and 3.14**, all four jobs success. [Actual run](https://github.com/lllleolin-max/blackbox-lens/actions/runs/37231688203). Remote CI is evidence of those executions; local auditor did not personally run Ubuntu.

The optional HTTP tests use local mocks for request shape, fresh system/user conversations, selected token parameter, authorization headers, no-auth loopback, malformed/oversized/truncated replies, HTTP failures, redirects, timeout, secret absence and semantic mapping. This is interface validation, **not** validation of every provider's compatibility or empirical behavior.

## Next round

Implement real changes for R1-01 and R1-02, add regressions, and improve the standalone interpretation/archive completeness. Freeze a distinct committed source SHA for round 2. Later rounds retain this rubric and the existing probes; new evidence may raise, lower or leave the score unchanged. A third distinct implementation/review version remains required even if round 2 already clears 95.
