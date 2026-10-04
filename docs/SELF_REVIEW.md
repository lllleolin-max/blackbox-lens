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
