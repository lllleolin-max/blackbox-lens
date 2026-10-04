# Implementation self-review

This is an implementer checklist, not the independent auditor's score. Independent review findings and the frozen rubric live in `docs/reviews/`.

## Initial candidate, 2026-10-05

Actual findings addressed before the first committed candidate:

- **Semantic answer versus presentation position:** exact label lookup now always uses each variant's explicit label-to-semantic map. Regression covers baseline `A → four` and reordered `B → four`, invalid verbose/lowercase answers, and stable incorrect answers.
- **JSON object order affecting behavior:** sorting keys for the suite digest initially disagreed with an insertion-order-based synthetic choice and generated label instruction. Both generated choices/instructions now sort output labels; reordered JSON object keys retain the same behavior. The methods reviewer and root independently flagged this concern.
- **Unbounded observation line allocation:** checking a line's size after ordinary file iteration could allocate the entire hostile line. Reanalysis now uses a bounded `readline` before parsing, with line and total artifact limits.
- **JSON-escaped credential appearance:** initial byte substring detection missed a configured dummy key containing quotes/backslashes in a suite field. The independent auditor's precheck reproduced this. The check now examines decoded JSON keys and strings recursively, and refuses the run before creating artifacts or making requests.
- **Slow-header timeout drift:** ordinary socket idle timeouts can reset for each received byte. The independent auditor's precheck reproduced drift beyond the budget. A deadline-aware raw response reader applies the remaining budget to every receive, including header reads. The slow-header regression expects a timeout within a bounded wall-clock interval.
- **Interrupted runs and cached metrics:** completed rows flush after each observation. Ctrl+C produces explicit missing slots and reports. Reanalysis validates exact planned IDs/order/repeats, rejects duplicates/unplanned rows and ignores cached metrics.

Validation before initial commit: Windows, Python 3.14.3; `python -m pip install --no-build-isolation --no-deps --force-reinstall .`; `python -m unittest discover -s tests -v`: **27 tests passed**. Tests execute the installed package, not an injected source path. Local HTTP mocks verify headers, request shape, mapping, malformed/truncated/oversized responses, HTTP errors, redirect refusal, timeout, no-auth local requests and secret absence. The offline fixture produces 54 planned/valid responses, 36 correct, nine flips each for the planted option-order and hint conditions, and no flips for genuine controls.

No real authenticated provider was called, no real model was validated, and no Ubuntu execution is claimed here. CI is configured to build/install the wheel and run tests on Ubuntu and Windows with Python 3.11 and 3.14. Repeated synthetic observations are deterministic fixture rows, not independent model samples. Suite semantics are authored and reviewed by humans/agents; schema validation cannot prove that two prompts preserve ground truth.
