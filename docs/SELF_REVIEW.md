# Implementation self-review

This is an implementer checklist, not the independent auditor's score. Independent review findings and the frozen rubric live in `docs/reviews/`.

## Initial candidate, 2026-10-05

Actual findings addressed before the first committed candidate:

- **Semantic answer versus presentation position:** exact label lookup now always uses each variant's explicit label-to-semantic map. Regression covers baseline `A → four` and reordered `B → four`, invalid verbose/lowercase answers, and stable incorrect answers.
- **JSON object order affecting behavior:** sorting keys for the suite digest initially disagreed with an insertion-order-based synthetic choice and generated label instruction. The initial candidate sorted the option-order branch and generated live label instruction. It did **not** sort the misleading-hint branch; this paragraph originally overstated the fix. The independent round 1 review reproduced the remaining defect with three labels, and round 2 fixes it below. The methods reviewer and root had independently flagged the broader concern before the initial commit.
- **Unbounded observation line allocation:** checking a line's size after ordinary file iteration could allocate the entire hostile line. Reanalysis now uses a bounded `readline` before parsing, with line and total artifact limits.
- **JSON-escaped credential appearance:** initial byte substring detection missed a configured dummy key containing quotes/backslashes in a suite field. The independent auditor's precheck reproduced this. The check now examines decoded JSON keys and strings recursively, and refuses the run before creating artifacts or making requests.
- **Slow-header timeout drift:** ordinary socket idle timeouts can reset for each received byte. The independent auditor's precheck reproduced drift beyond the budget. A deadline-aware raw response reader applies the remaining budget to every receive, including header reads. The slow-header regression expects a timeout within a bounded wall-clock interval.
- **Interrupted runs and cached metrics:** completed rows flush after each observation. Ctrl+C produces explicit missing slots and reports. Reanalysis validates exact planned IDs/order/repeats, rejects duplicates/unplanned rows and ignores cached metrics.

Validation before initial commit: Windows, Python 3.14.3; `python -m pip install --no-build-isolation --no-deps --force-reinstall .`; `python -m unittest discover -s tests -v`: **27 tests passed**. Tests execute the installed package, not an injected source path. Local HTTP mocks verify headers, request shape, mapping, malformed/truncated/oversized responses, HTTP errors, redirect refusal, timeout, no-auth local requests and secret absence. The offline fixture produces 54 planned/valid responses, 36 correct, nine flips each for the planted option-order and hint conditions, and no flips for genuine controls.

No real authenticated provider was called, no real model was validated, and no Ubuntu execution is claimed here. CI is configured to build/install the wheel and run tests on Ubuntu and Windows with Python 3.11 and 3.14. Repeated synthetic observations are deterministic fixture rows, not independent model samples. Suite semantics are authored and reviewed by humans/agents; schema validation cannot prove that two prompts preserve ground truth.

## Round 2: repairs following independent review

Review source: `92e57271df26ff5a96de85d563a7739c8b733f68`; findings recorded independently in `docs/reviews/ROUND1.md`.

- **R1-01:** misleading-hint selection now sorts output labels before choosing a wrong semantic answer. A three-choice regression tests all six map insertion orders, verifies one unchanged suite hash, and verifies the same label and semantic answer.
- **R1-02:** strict JSON decoding now validates the complete decoded object as finite UTF-8 JSON. Canonical serialization errors are normalized to `SuiteError`. Regressions use a literal overflowed exponent, a lone surrogate value and a lone surrogate key in manifest metadata; both SDK and installed CLI reject them before creating output, and CLI prints a concise error without a traceback.
- **R1-03:** the standalone report labels summaries “Variant kind (pooled)”, defines a condition as a case/variant, states summed pair weighting and displays total repeat conditions. Numeric definitions and existing results remain unchanged.
- **R1-04:** `MANIFEST.in` includes linked Markdown documentation, JSON examples and test helpers in the source distribution. `tests/check_sdist.py` opens the actual built archive, checks nine required files and checks archived source/bundled demo agreement; CI invokes it after building.

Validation: Windows, Python 3.14.3; wheel installed with `python -m pip install --no-build-isolation --no-deps --force-reinstall .`; **30 installed-package tests passed**. Source archive built with `setuptools.build_meta.build_sdist('dist')`, then `python tests/check_sdist.py` verified the actual archive. `python -m pip wheel --no-build-isolation --no-deps --wheel-dir dist dist/blackbox_lens-0.1.0.tar.gz` successfully rebuilt the wheel from that archive. The local environment lacks the optional `build` development module, so the direct declared build backend was used; CI installs `build` and runs the normal frontend. This section is implementation evidence, not an independent audit score.

## Round 3: inspect contrasts by case and exact variant

Previous source: `4ef10b40372de9202cb67a468d88987209378909`; its independent review is recorded unchanged in `docs/reviews/ROUND2.md`. This is an additional reporting capability, not a newly asserted defect or a change to the rubric.

- Added `case_contrasts`, one record per declared case and nonbaseline variant. Each records the baseline ID, integer pair counts, coverage, invariance and flip rate. Zero eligible pairs remain represented with null rates. Rows retain declared order.
- Pair outcomes are scored once at case/variant level; existing pooled-by-kind counts sum those integer fields and calculate rates from the totals. No averaging of percentages, new statistical claim or alteration to response states is introduced.
- The HTML shows each case/variant contrast and links its identifiers to the existing declared prompt details. Links are escaped fragment targets only. Length-prefixed case IDs prevent collisions between hyphenated case/variant combinations.
- Added an independently specified mixed-coverage regression: 18 slots, 11 valid, 2 invalid, 2 errors, 3 missing, 8 correct. Its four same-kind case/variant contrasts sum to 12 planned / 9 observed / 5 valid / 7 excluded pairs and 3/5 semantic flips. Tests check all directional counts, same-kind variant identity, shared-baseline exclusions, zero-eligible N/A, pooled sums, JSON/HTML parity and target links.
- Added default-demo breakdown checks (15 records), old cached-report-shape reanalysis and hyphenated identifier targets. Manifest, suite and observation schemas remain version 1; raw artifacts retain their existing format.

Validation: Windows, Python 3.14.3; rebuilt and installed the wheel with `python -m pip install --no-build-isolation --no-deps --force-reinstall .`; **35 installed-package tests passed**. `python -m blackbox_lens analyze demo-run --out run-round3-old` successfully reanalyzed the actual initial-candidate demo artifacts: all four old metric objects (`counts`, `by_kind`, `comparisons`, `repeat_consistency`) are unchanged, and 15 case contrasts are newly derived. Source archive built with the declared setuptools backend and checked with `python tests/check_sdist.py`; wheel rebuild from that archive succeeded. Independent scoring belongs to the auditor.
