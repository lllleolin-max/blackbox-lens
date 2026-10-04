# Protocol A1: DeepSeek controlled behavioral microstudy

Authoring timestamp: 2026-10-05T06:45:45.464205+08:00. Drafted before any main-study outcomes; requires independent semantic/protocol review before execution. The completed two-call connection pilot was known at authoring and is excluded from all main metrics. Do not overwrite this protocol after main calls start; corrections or changes require a separate dated amendment with its own hash.

## Scope and hypotheses

The question is whether semantic answers change under the specified prompt variants, and whether observed correctness/availability differs between two API parameter bundles on these 12 authored cases. This is a limited-coverage diagnostic of a hosted API during one execution window. It cannot estimate a population-wide reliability rate, reveal internal mechanisms or hidden reasoning, establish explanation faithfulness, or establish a pure causal effect of enabling thinking.

Prespecified expectations, evaluated descriptively: exact-prompt controls reveal ordinary observed variability; declared paraphrases/context/reordering are ground-truth-preserving; unverified incorrect suggestions may induce changes toward their hinted semantic answers. Thinking and non-thinking bundles may differ, but no superiority direction is assumed. Zero flips or ceiling accuracy are reportable outcomes, not reasons to replace cases, strengthen hints or add harder questions after seeing data.

The suite has 12 self-contained cases: four arithmetic, four deductive and four extraction/order. Each has four distinct semantic choices and six explicit conditions. Correct baseline labels are balanced A/B/C/D at three cases each. Option-order rotates contents one position right, preserving the answer-map bijection and balancing its correct labels too. All other conditions retain the baseline map. Full derivations, all six label maps and wrong hints are in ANSWER_KEY.md. Schema validation does not prove semantic equivalence; an independent reviewer must inspect it before main.

## Frozen inputs and registration

- suite.json raw UTF-8 SHA-256: `7a2a46ab074c7dbe3fa46d1f35c6fcb139ccff22b562b1a87a73b10b327edeed`.
- suite canonical JSON SHA-256: `49f86b2a7c137f84d617ea190e63bb988b9bdfb0dcc3638c485a73ecd300f7f6` (the suite digest used in run manifests).
- ANSWER_KEY.md raw UTF-8 SHA-256: `891cd55737125d38228344c257603decda3014d4cffdd7c6e76c3f06f02bfd3f`.
- Registration revision: A1. Study date: 2026-10-05, Asia/Shanghai.
- Before main, save an external freeze record containing these hashes, this protocol's raw hash, independent review result, the exact committed runner source SHA/package version, and hashes of the sanitized parameter configuration and planned dispatch schedule. The protocol does not self-embed its own hash. Record the actual freeze timestamp; this authoring timestamp is not proof of execution verification.
- Do not start main until the suite/key/protocol and runner settings pass the pre-main review and are frozen. Do not silently repair prompts or keys after calls start.

## API bundles and execution plan

Use model alias `deepseek-flash`. Root's authenticated model-list evidence names DeepSeek-V4.1-Flash; chat responses use the alias. The provider's [model catalog](https://api-docs.deepseek.com/quick_start/pricing/) was checked on 2026-10-05 and lists this alias/version and both mode settings. An alias/catalog label does not prove immutable backend weights. Record requested and response model fields, configured base URL/endpoint and timestamps from actual sanitized records.

Common settings: three repetitions per case/variant; scheduler seed **20261005**; `max_tokens=4096`; nonstreaming chat/completions; request timeout **120 seconds**; no tools, automatic retries, redirects or response selection. Use the same fixed exact-label system instruction and fresh conversation context for every call. Record omitted as well as supplied parameters; an omitted provider setting is not known to equal a numeric value.

| Bundle | Thinking configuration | Temperature | Reasoning effort |
| --- | --- | --- | --- |
| disabled | `thinking.type=disabled` | explicitly 0 | omitted |
| enabled-high | `thinking.type=enabled` | omitted/provider behavior | explicitly high |

These bundles differ in thinking configuration, reasoning effort and temperature specification. Their comparison is descriptive, even if called 'mode comparison'. Other server defaults, cache behavior, timing and concurrency may also contribute. Do not imply that a pure thinking switch was isolated.

There are 12 × 6 × 3 = **216 planned response slots per bundle**, **432 main calls total**, plus the already completed two-call pilot. Each bundle has 180 baseline–variant comparisons; each baseline is reused for its five variants. Match baseline/variant by case and repeat within a bundle. For between-bundle contrasts, match the same case/variant/repeat identity; this matching does not establish common random seeds or independent samples.

Create the same 216-trial seeded order for both bundles. In the global dispatch queue, alternate which bundle goes first for each trial: first trial disabled then enabled-high, second enabled-high then disabled, continuing by planned trial index (108 first positions each). Run with at most **four concurrent requests**. Record intended dispatch index, actual start/end UTC times, completion/logging index and duration; request dispatch and completion order differ under concurrency. If the runner cannot implement this schedule, revise and refreeze before main. Do not switch to sequential mode blocks without a dated pre-main amendment; blocked modes would add a systematic time/order confound.

## Completed connection pilot

Root reports two successful authenticated calls asking 17+28, correct label B in both bundles, with the same 4096-token cap. Disabled: 63 prompt tokens, 1 completion token, about 566 ms. Enabled/high: 88 prompt tokens, 17 completion tokens including 15 provider-reported reasoning tokens, about 488 ms. These are root-reported pilot observations, not independently reread by this author and not main-study results. Sanitized pilot files are kept externally as `pilot-disabled.json` and `pilot-enabled.json` in the experiment evidence directory. No pilot prompt is selected into this suite on the basis of its behavior.

The pilot supports connection and response compatibility under those two settings, not general availability or correctness. It motivates starting with the common 4096 cap; it does not justify optimizing main prompts or settings for desired outcomes.

## Failure and stopping rules

A valid response is one exact mapped label after boundary-whitespace stripping. Returned explanations or unknown labels are invalid; they remain genuine outcomes and do not trigger accuracy-driven stopping. Preserve valid incorrect, invalid, adapter/provider error and missing slots separately. Keep the original finish reason, error category and bounded full received response; do not infer an answer from truncated content or silently drop a failed attempt.

Stop dispatching unsent main calls upon any authentication/billing refusal (including HTTP 401/403/402), the first output-length/cap termination, **three consecutive provider/transport errors**, or **ten cumulative provider/transport errors**. Count consecutive/cumulative failures in the logger's serialized **completion-record order**, not planned dispatch order; a completed valid or invalid response resets the consecutive provider-error counter. Cap failures also count as errors, but trigger the immediate cap stop independently. Up to the configured four in-flight requests may finish and must be logged after a stop trigger. Do not discard them; the remaining unsent planned slots stay missing. Record stop trigger, index, time and in-flight count. Operator interruption is likewise preserved as an incomplete run.

No failed-slot reruns are part of primary analysis. A mechanical cap stop may lead to a separately dated amendment using a prespecified next cap of **8192 for both bundles**, with a new two-call compatibility pilot and a fully new run identifier/schedule freeze. This requires validated runner support and independent amendment review before additional calls. Retain the original incomplete run and all attempts; report the reason, old/new caps and request totals. Do not combine selected successful attempts across runs or tune caps based on accuracy. Any change beyond this fallback requires an explicit new protocol amendment; no automatic escalation is authorized by this document.

## Prespecified descriptive analysis

Report all 216 planned slots per bundle, completion/validity coverage, correct count, strict accuracy (correct/planned), valid accuracy (correct/valid), invalid/error/missing counts, finish reasons and token/latency summaries with their eligible denominators. Usage is provider-reported; absent usage is missing, not zero. Do not estimate actual charges as exact without a billing record, and separate pilot/main/amendment usage.

Within each bundle, report per-case/variant and pooled-kind planned/observed/valid/excluded pairs; semantic invariance/flip rate; correct-to-incorrect and incorrect-to-correct counts; both-correct/both-incorrect counts. Sum integer counts then calculate pooled rates. Zero eligible denominators are unavailable, not zero. For hints, also report movement to the prespecified hinted semantic answer among eligible pairs; do not count an already-hinted baseline as a newly induced movement. For repeats, report within-prompt disagreement using all pairs of valid repeated semantic answers, plus planned/valid repeat-pair counts.

Between bundles, report descriptive paired semantic disagreement and paired correctness/availability differences at the same case/variant/repeat identities, with exclusion counts and denominators. Report per-domain/per-case detail before broad interpretation. Do not average percentages with different denominators or turn a small sample into a model ranking.

All repeated calls, shared baselines and pairwise repeat comparisons are dependent. No significance tests, binomial confidence intervals from repeat counts, p-values, causal claims, faithfulness scoring or population generalization are planned. Returned reasoning text, if provided, is provider output for recordkeeping; it is not a validated account of hidden computations and is not graded for faithfulness.

## Complete records and publication

Retain sanitized request bodies (including explicit mode/settings), planned slot IDs/order, sent/completed timestamps and serialized completion order, full received provider bodies within the declared collector bound, returned final content/reasoning content when supplied, finish reasons, usage/cache fields when supplied, HTTP/error outcomes, request IDs when available, durations, derived semantic labels, suite/key/protocol/config/source hashes and every stop/amendment/pilot event. If a collector limit prevents a complete response, record that failure explicitly; do not label a truncated record complete. No authorization headers, API key, environment dumps or secret-bearing error bodies may be published.

The root agent alone handles credentials and paid execution. This author makes no API calls and does not access credentials. Implementation/review roles remain separate. Main results and conclusions must be written only after data are final, independently checked and linked to the frozen inputs. Publish limitations and null/failed outcomes alongside any findings.
