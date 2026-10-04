# Blackbox Lens — fixed independent delivery audit rubric

Frozen before the first implementation review on 2026-10-05 (Asia/Shanghai). This rubric is stable across all review rounds. Product implementation authors must not write the independent auditor's findings or determine its score.

## Scope and meaning of a score

This is an **AI review of a bounded behavioral-interpretability prototype**. It is not a scientific discovery, recovery of hidden reasoning, validation of a real-world model, independent human peer review, or market validation. The audit assesses whether the advertised CLI/SDK performs its specified experiment and reports observations honestly, with a safe and reproducible artifact pipeline.

The core is a Python-standard-library CLI/SDK with explicit controlled baseline and variant suites, canonical semantic option labels, repeated trials and shuffled presentation, an offline planted-bias demo, an optional OpenAI-compatible HTTP backend, bounded observations, metrics recomputed from those observations, and a self-contained HTML report. Actual authenticated model calls are unavailable without credentials; mocked HTTP interface evidence is accepted for the optional integration only if that boundary is explicit in the product and audit reports.

The requested release threshold is **at least 95/100**, **zero unresolved critical or high severity findings**, and independently observed functioning of every advertised core capability. A raw sum of 95 or greater with a failed gate is capped at 94 and is **not release-ready**. The threshold is a decision gate, not a target to steer scoring toward. A lower score must be reported honestly. Three review rounds must cite distinct, committed product source versions with actual product improvements; reworded reports do not count as new versions.

## Evidence and scoring rules

- Score each criterion in half-point increments against direct evidence; start at zero and award the parts substantiated. Full points require all stated properties. Partial points require a stated proportion and a concrete reason. Unknown or untested claims receive no credit for the unverified property.
- Use exact source SHA and tree cleanliness, execution command, exit result, test count where available, fixture input and observed output. A claim that a test exists is weaker than independently executing it. Inspect every shipped source file and entry point; inspect tests, packaging, documentation, sample suites and generated reports.
- Independently recompute numeric metrics from artifact observations; do not trust implementation tests or cached summary fields alone. Include failure and adversarial fixtures.
- Critical/high findings veto release irrespective of numerical points. Do not double-charge the same defect across unrelated categories; a defect may remove points in multiple categories only when each records a separate failing property.
- Record limitations, including no live paid/authenticated API runs and no external model/generalization claims. A score is attached to a source version and finite test environment, not to future changes or all possible inputs.
- Keep findings and independent probes outside the product repository. The auditor does not edit product code, product tests, or release assets. Implementation improvements must be made by the implementer.

## Weighted criteria (100 points)

| ID | Area | Points | Conditions for full credit |
|---|---|---:|---|
| S1 | Scientific scope | 5 | README, CLI, SDK and report describe observable outputs and bounded contrasts; no claim to infer private reasoning, consciousness, causal mechanism, or general real-world validity; offline planted bias is explicit. |
| S2 | Experimental identity and control | 5 | Baseline/variant identity, question/context, canonical semantic label-to-option mapping, repeat index, seed/order and backend provenance survive execution and artifact serialization. Controls are explicit and comparable; suites cannot silently regroup distinct items. |
| S3 | Denominators and missingness | 7 | Reported totals expose all scheduled, observed, valid, invalid, error and incomplete outcomes; comparative denominators and exclusions are explicit; unsupported/missing observations cannot silently become zero effect or valid evidence. |
| S4 | Repeats and presentation | 5 | Canonical labels survive shuffled order; scheduled repeats are genuine separate observations. Deterministic/offline repeats are described accurately and are not sold as independent model samples or confidence. Order and condition effects are distinguishable. |
| S5 | Descriptive interpretation | 3 | Metrics have correct bounded interpretation, evidence is inspectable and caveats are visible; small samples, exclusions and backend limitations do not produce causal or statistical certainty. |
| C1 | Metric correctness | 8 | Independent arithmetic matches recomputation on mixed valid/invalid/error/incomplete fixtures, baseline/variant contrasts and no-comparison cases; corrupted cached summaries cannot alter metrics. Numerical outputs remain finite and are correctly rounded/presented. |
| C2 | Canonical semantic parsing | 6 | Parsing and validation identify canonical semantic labels irrespective of presentation order; ambiguity, duplicate labels and unknown/malformed choices are rejected or classified explicitly, with honest counts. |
| C3 | Offline core and SDK | 4 | Documented CLI demo and SDK run end to end with planted bias visible, deterministic reproduction possible and complete inspectable artifacts. Baseline and variants behave as documented. |
| C4 | Optional HTTP adapter | 4 | Mock HTTP integration independently verifies request shape, endpoint/header handling, accepted response parsing, and deterministic error handling. Optional nature and absence of live backend validation are disclosed. |
| C5 | Report/data fidelity | 3 | JSON and HTML faithfully expose recomputed metrics, observations and provenance; a report built from supported saved artifacts works and contradicting metadata is not silently trusted. |
| F1 | Backend and execution failure | 5 | Timeout, HTTP errors, invalid JSON, malformed response and interrupted/incomplete runs are observable and do not fabricate successful choices; partial failures preserve honest denominators. |
| F2 | Validation and resource bounds | 5 | Suite/artifact schema and dangerous edge inputs fail clearly; sensible input, repeat, timeout and response/output bounds prevent accidental unbounded work, invalid numbers or misleading outputs. |
| F3 | Credentials and privacy | 5 | Secrets come from appropriate environment/config input, do not enter artifact, report or errors; prompts/responses and backend URLs are handled with bounded, explained raw-observation retention and no secret-bearing leakage. Local-only and network behaviors are clear. |
| F4 | HTML and filesystem safety | 5 | All untrusted fields are escaped in report text/attributes/script contexts; malicious prompts/outputs cannot run script or fetch resources. Report is self-contained, and documented output paths do not cause unexpected file overwrites or path traversal. |
| R1 | Meaningful regression suite | 4 | Product tests cover behavioral controls, semantic parsing, arithmetic/denominators, failure handling, HTML safety, backend mock and documented CLI/SDK without merely restating implementation. |
| R2 | Independent execution | 4 | Auditor independently executes the regression suite, documented CLI/SDK flow and adversarial probes on the cited SHA, with results recorded. Relevant failures are fixed and rerun in later rounds. |
| R3 | Artifact reproducibility | 4 | Artifact version, suite/condition identity, backend/model, seeds/order/repeats and bounded raw outcomes are sufficient to recompute the advertised metrics and inspect exclusions; corruption is rejected clearly. |
| R4 | Review traceability | 3 | Exact version, environment and limitations are recorded; each review round is independently evidenced and repeatable. Release candidate and package correspond to the final reviewed committed source. |
| U1 | Documentation completeness | 4 | README and examples provide accurate install, CLI/SDK, suite schema, API setup, metrics, raw retention and limitations, including expected outputs and error states. Advertised features are supported by the implementation. |
| U2 | CLI/SDK usability | 3 | Help, successful commands, validation failures and optional-dependency/credential errors are clear; core flows work without guessing undocumented commands or config. |
| U3 | Self-contained report usability | 3 | Offline HTML opens without network assets, contains legible totals/contrasts/observations/limitations and allows traceability from metric to input outcomes; report handling works on mixed or empty comparable data. |
| P1 | Distribution and clean install | 3 | Wheel independently builds and installs into a clean environment; package exports, console command, version metadata and bundled examples/docs (if advertised as available after install) function. |
| P2 | Runtime and portability | 2 | Core runtime uses only stdlib and declared supported Python; no accidental workspace files, undeclared runtime deps, absolute machine paths or platform-specific assumption blocks documented core use. Windows run is verified; other platforms are not claimed verified without evidence. |

## Severity definitions

- **Critical:** likely credential exfiltration, remote code execution, destructive write, or wholesale fabrication of experiment evidence that cannot be distinguished from actual observations.
- **High:** advertised core flow broken; materially incorrect experimental comparison/denominator/label attribution; uncontrolled resource work; credible persistent script execution or secret leak; fake causal/scientific certainty undermining the central interpretation.
- **Medium:** bounded non-core correctness or handling defect, incomplete important provenance/test coverage/documentation, poor error behavior, or a narrowly triggered robustness problem without a high impact.
- **Low:** minor clarity, usability or packaging issue that leaves core evidence correct and safe.
- **Informational:** limitation or worthwhile improvement without a demonstrated defect. No automatic deduction solely because an enhancement could exist.

## Round report requirements

Each report records: source SHA and clean/dirty status; score by all six areas and criterion deductions; release gate result; all open and resolved findings with severity, affected source locations, reproduction and actual result; commands and test outcomes; generated audit artifact locations; mocked versus live integration boundary; and source differences from the previous round. If blockers remain, conclude that another implementation version is required rather than massaging the score.

## Fixed critical probe checklist

1. Execute documented offline CLI and SDK; repeat fixed seed, inspect planted baseline/variant behavior and changed seed/order.
2. Label-first, position-like, unknown, duplicate, whitespace, verbose and ambiguous choices; confirm shuffle does not change semantic identity and canonical mapping is included.
3. Recompute all metrics independently on fixtures containing unequal group sizes, invalids, backend errors, incomplete schedules, no baseline, no usable comparison and no valid outcomes.
4. Tamper cached summaries, artifact schema, suite/condition identities, canonical options, repeat indices, duplicate observations and scheduled totals; require reject/explicit treatment and no silent comparable zero.
5. Distinguish deterministic offline repeated rows from fresh API requests; count requests and match every observation to condition/repeat/order.
6. Use stdlib HTTP mock server for valid request, shuffled labels, malformed JSON, wrong choice/shape, non-2xx, timeout, overlong response and key-bearing errors; inspect secret absence throughout JSON/HTML/errors.
7. Put closing-script tags, tags/quotes/event handlers, external URLs and control characters into suite text, model name, backend errors and returned text; inspect HTML escape behavior and network references.
8. Exercise negative/zero/extreme repeats, NaN/infinity, empty/duplicate labels, malformed JSON schema, raw-response limit, large input/output and output collisions as relevant to supported contracts.
9. Build wheel independently, install cleanly, run console/SDK from outside source checkout and confirm runtime imports do not require undeclared dependencies.
10. Inspect all shipping files and test/documentation consistency; record finite limitations, exact SHA and improvements across all three versions.
