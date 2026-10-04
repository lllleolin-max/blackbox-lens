# Methodology / 方法说明

Blackbox Lens is a behavioral evaluation workbench. It compares observable responses to explicit prompt variants, controls and repeated calls. A run is a diagnostic on its authored suite and recorded configuration, not an estimate of unrestricted model performance or a view of hidden reasoning.

Blackbox Lens 比较提示变体、对照和重复调用的可观察输出。结果只描述所编写的测试集与所记录配置下的行为，不代表模型整体表现，也不揭示隐藏推理。

Primary sources below were verified on 2026-10-05. The experiment contract and reporting choices are this project's synthesis, rather than metrics claimed to come verbatim from any paper.

## 1. Suite contract

Version 1 supports **ground-truth-preserving variants**. A case contains:

- `id`: unique case identifier.
- `expected`: one correct semantic ID.
- `canonical_labels`: 2–16 distinct semantic IDs, including `expected`.
- `variants`: 2–12 explicit prompts, exactly one with `kind="baseline"`.

Each variant contains exactly `id`, `kind`, `prompt` and `answer_map`. Its answer map must be a bijection from accepted output labels to all case semantic IDs. Supported kinds are `baseline`, `control`, `paraphrase`, `irrelevant-context`, `option-order` and `misleading-hint`. Identifiers and output labels use 1–64 ASCII letters, digits, underscores or hyphens. A suite contains exactly `schema_version`, `title`, `description` and `cases`, with schema version 1 and 1–100 cases. Duplicate JSON keys and undocumented fields are rejected.

Stable semantic scoring prevents a position artifact:

| Prompt | Mapping | Response | Meaning |
| --- | --- | --- | --- |
| Baseline: A Paris; B Rome | `A → paris`, `B → rome` | A | paris |
| Reordered: A Rome; B Paris | `A → rome`, `B → paris` | B | paris |

Those responses agree. Baseline A and reordered A disagree. A flip must compare semantic IDs, not letters. Option position sensitivity is documented prior work, so both position and semantic output should remain inspectable. [Zheng et al., ICLR 2024](https://arxiv.org/abs/2309.03882).

The correct answer must stay the same in every variant. Label-preserving perturbations correspond to CheckList's invariance tests; changed facts or negation may instead require a directional expectation and different ground truth, which this schema does not implement. A misleading hint is an input intervention that must leave the task's actual correct answer fixed; it is not automatically a semantically equivalent instruction. The suite author must review this judgement. Validation establishes structure, not semantic equivalence. Record intended interventions and rationale in `description`. [Ribeiro et al., ACL 2020](https://aclanthology.org/2020.acl-main.442/).

**中文要点：** 所有变体必须保持正确语义答案不变；选项调序后必须同步修改答案映射。格式校验不等于语义等价校验。会改变标准答案的事实修改或否定实验，不适用于第 1 版。

## 2. Controls, repetition and execution

Prefer one declared intervention per comparison. If wording and option order change together, the result describes that combined intervention. Add an exact-prompt `control` variant to measure disagreement between unchanged prompts, and include simple known-answer cases to check the scorer. The bundled synthetic demo includes an exact-prompt control.

Each case/variant receives the requested number of repetitions. Baseline–variant comparisons are matched within case and repetition. One baseline response is shared across that repetition's variant comparisons; those comparisons therefore depend on the same observation.

The scheduler uses a recorded seed to shuffle request order. This reproduces the plan, not provider responses. Request order is separate from option order: request order changes scheduling; option order changes the input and requires its own map. The live adapter sends a fresh system/user conversation each time, requests a single exact label, sets `temperature=0`, and makes no retries or redirects. It does not promise model determinism or independently sampled responses.

The synthetic adapter deliberately reads expected labels and applies planted position/hint biases. It verifies scoring and reporting behavior; its output is not empirical evidence about a model. A repeated cached response from an external endpoint also does not establish fresh-sample repeatability.

An unchanged-prompt control helps reveal ordinary variability. Do not subtract its disagreement rate from another flip rate and label the result a causal effect. The comparisons involve different stimuli, observations and validity patterns. Counterbalancing or shuffling scheduling reduces simple order confounds but cannot remove every provider, time or context effect.

**中文要点：** 同一案例、同一轮次内进行配对；复用的基线产生依赖。种子控制请求顺序，不保证模型输出可复现。对照揭示普通波动；模拟演示不是模型证据。

## 3. Response states and scoring

The declared response grammar accepts an exact output label after stripping boundary whitespace. A returned explanation, unsupported label or other text is invalid, even if a human could infer the intended answer. This explicit rule avoids changing a parser after seeing results. Raw output remains available for inspection when retained.

Every planned response slot is accounted for:

| State | Meaning |
| --- | --- |
| Valid | The returned label maps to a canonical semantic ID; it can be correct or incorrect. |
| Invalid | A returned response fails the label grammar. |
| Error | A provider, transport or adapter failure prevents a usable response. |
| Missing | No observation exists for a planned slot. |

These response-slot categories are mutually exclusive. Missing results are reconstructed against the saved plan during analysis. A returned truncated or unsupported API response may be an adapter error rather than a grammar-invalid answer; inspect the recorded error category.

## 4. Metric definitions

For each condition let `P` be planned response slots, `V` valid responses, and `C` correct valid responses. Display counts with every rate; empty denominators yield an unavailable value rather than zero.

| Metric | Definition | Interpretation |
| --- | --- | --- |
| Strict accuracy | `C / P` | Invalid, error and missing slots count as unsuccessful. This includes pipeline availability. |
| Valid accuracy | `C / V` | Correctness conditional on a valid label; read alongside coverage. |
| Valid coverage, calculated from counts | `V / P` | Share of planned slots producing accepted labels. |
| Paired flip rate | `changed semantic answers / E` | `E` includes only baseline–variant pairs with two valid mapped answers. |
| Paired accuracy change, derived from transition counts | `(wrong-to-correct − correct-to-wrong) / E` | A derivable quantity; the report stores transition counts rather than a separate delta field. |
| Correct-to-wrong / wrong-to-correct | Counts over eligible pairs | Distinguish regressions from improvements. |

The report groups eligible, planned and excluded pair counts by variant kind. These are pair-weighted totals, not equal-weight case averages. Response-state counts and raw trial rows explain excluded comparisons. A wrong answer can stay stable; two different wrong answers can flip. Correctness and consistency must therefore be interpreted separately. If variants of different difficulty or validity are grouped by kind, inspect the individual prompts and cases before drawing a general conclusion.

### Case and variant contrasts

`report.case_contrasts` is a list with one record per declared case and nonbaseline variant, summarizing its paired repetitions against that case's baseline. Records remain distinct even when several variants have the same kind, and include zero-flip and zero-eligible cases. Each record contains:

| Fields | Definition |
| --- | --- |
| `case_id`, `variant_id`, `baseline_variant_id`, `kind` | The exact contrast identity; variant IDs are only unique within a case. |
| `planned_pairs`, `observed_pairs`, `valid_pairs`, `excluded_pairs` | Planned pairs; pairs with both observations present; pairs with both semantic answers valid; planned minus valid pairs. Recorded invalid/error responses are observed but not valid. |
| `same`, `flips` | Same or different semantic answers among valid pairs. |
| `correct_to_incorrect`, `incorrect_to_correct`, `both_correct`, `both_incorrect` | Correctness-transition counts among the same valid pairs. |
| `coverage`, `invariance`, `flip_rate` | Valid/planned, same/valid and flips/valid pairs. |

If `valid_pairs` is zero, `invariance` and `flip_rate` are `null` in JSON and N/A in HTML; coverage is zero for a nonzero planned denominator. Pair identity and baseline reuse follow the existing case/repetition contract. A missing baseline can therefore exclude more than one variant comparison; excluded pairs must not be interpreted as distinct failed response slots.

The pooled `comparisons` object sums these records' integer counts by kind and recomputes rates from the summed numerators and denominators. It does not average row rates. For example, row flip counts of 1/2, 1/1 and 1/2 pool to 3/5, not the mean percentage 2/3. The added breakdown changes traceability, not eligibility or the estimator.

The standalone HTML **Case and variant contrasts** table links case, baseline and variant identifiers to their existing declared prompt details. It introduces no JavaScript or new suite-input fields. Reanalysis produces this breakdown from saved observations, so existing run artifacts remain usable.

**中文要点：** `case_contrasts` 按案例与具体非基线变体逐行展示，保留同类型的多个变体、零翻转与零有效配对。复用基线导致多个排除配对时，不能把它们当作多个独立失败响应。汇总先加整数计数再计算比例；明细增加可追溯性，不改变评分规则。

### Repeat disagreement

For repeated answers to the **same case and variant**, let `n` be the number of valid repeats and `n_c` the count of semantic ID `c`. Repeat disagreement is:

```text
1 − Σc [n_c × (n_c − 1)] / [n × (n − 1)]
```

This is the proportion of unordered pairs of valid repeats that disagree within that case/variant. It is unavailable when `n < 2`. The report aggregates by kind as total disagreeing repeat pairs divided by total valid repeat pairs, rather than averaging the per-prompt rates; conditions with more valid repeats receive more weight. Read its planned/valid pair counts and the response coverage together. Excluding failures can make the remaining answers appear stable. Pairs formed from the same repeats overlap, so their count is not an independent sample size.

**中文要点：** 严格正确率将错误、无效和缺失响应计为未成功；有效正确率只看有效响应。翻转率只使用两端都有效的语义配对。零分母应显示不可计算，不能显示 0%。一致不等于正确。

## 5. Uncertainty and claims

Metrics are descriptive. Repeating the same prompt, sharing baselines across variants, and forming pairwise comparisons from repeated answers create dependence. Do not treat those records as independent task samples to construct binomial confidence intervals or significance tests. More repeats do not compensate for a small, selectively authored suite. A later population-level study would need a prespecified item sampling plan and an uncertainty method that preserves item/family dependence.

Formatting sensitivity is established prior work. FormatSpread examines performance across sampled plausible prompt formats; a few hand-authored variants here do not estimate that complete format space. Neither a low observed flip rate nor a high accuracy on a small suite establishes universal robustness. [Sclar et al., ICLR 2024](https://arxiv.org/abs/2310.11324).

Use statements such as: “Under this suite and recorded configuration, 4 of 12 eligible pairs changed semantic answer.” Attribute an observed change to the tested input intervention only with the relevant design assumptions and controls; do not infer an internal mechanism from answer changes alone.

Generated rationales that sound plausible do not establish explanation faithfulness. Turpin et al. demonstrate unmentioned biasing influences and explicitly describe their own evaluation as a necessary, not sufficient, test of faithfulness. Blackbox Lens' exact-label scorer does not evaluate rationales, and no result here proves or disproves reasoning faithfulness by itself. [Turpin et al., NeurIPS 2023, limitations](https://arxiv.org/html/2305.04388v2).

**中文要点：** 结果是描述性统计，重复调用不是独立题目。小型测试集不能证明普遍鲁棒性；答案变化不能直接定位内部机制，本工具也不检验解释忠实性。

## 6. Provenance, retention and reanalysis

A run saves `manifest.json`, `observations.jsonl`, `calls/*.json`, `report.json` and `report.html`. The manifest includes the suite, its hash, adapter metadata and execution plan. Schema-2 observations retain trial IDs, bounded final output or errors, elapsed durations and SHA-256 references to sanitized per-call evidence. Schema-1 observations remain analyzable. HTTP call records preserve the received provider JSON, returned metadata and exact request JSON without authorization; failed responses remain visible. Analysis validates internal request/response/observation consistency and UTC ordering. File hashes detect corruption relative to the journal; they do not authenticate locally editable artifacts. Monotonic client duration need not equal a UTC clock delta. Reanalysis recomputes results against the saved plan and writes JSON/HTML reports to a fresh output directory, leaving the source intact. That new analysis directory contains reports, not a second raw run. Existing output directories are rejected.

The live adapter supports one nonstreaming chat/completions response, a configurable output-token limit, and a timeout bounded to 600 seconds (the DeepSeek study explicitly selects 120). It does not stream, retry, follow redirects or use a model SDK. Remote connections require HTTPS and authentication; loopback endpoints can opt out of authentication. Request budgets are checked before execution. Provider behavior and model versions beyond available metadata remain external limitations. `reasoning_content` is provider-returned text, not guaranteed privileged internal reasoning.

Concrete resource bounds:

| Resource | Limit |
| --- | --- |
| Suite JSON | 1 MiB (1,048,576 bytes), including the canonical suite representation |
| Each prompt | 32,768 characters |
| Each final answer accepted for scoring | 4,096 characters; larger final content is retained within the body bound but scored as an error |
| HTTP response body | 1 MiB (1,048,576 bytes); oversized bodies retain a flagged prefix |
| Each serialized call record | 4 MiB (4,194,304 bytes), including provider JSON and metadata |
| Planned calls | Hard maximum 1,000 per suite run; live runs default to an explicit budget of 100; two-mode batch maximum 2,000 |
| Repeats per case/variant | 1–100 |
| Request timeout | Greater than zero and at most 600 seconds; study budget 120 seconds |

Oversized and incomplete HTTP responses become errors rather than silently truncated accepted answers, including a body that closes before its declared Content-Length even if its received prefix is valid JSON. These are pipeline limits, not guarantees about a provider's internal token accounting or computation. Implementation validation uses offline synthetic fixtures and local mock HTTP endpoints. Authenticated pilot and formal-study evidence are recorded separately with actual call counts and provenance; implementation tests establish neither empirical model reliability nor hidden reasoning recovery.

**中文要点：** 测试集最多 1 MiB，单条提示最多 32,768 字符；评分用最终答案最多 4,096 字符，提供商响应体另行保留，最多 1 MiB，逐次记录最多 4 MiB。单模式计划最多 1,000 次调用，双模式批次最多 2,000 次；每条件重复 1–100 次，超时最多 600 秒，本次研究选用 120 秒。超长或传输不完整响应记为错误。实现测试、在线试运行和正式实验按实际证据分别记录，不能将本机测试视为模型可靠性证明。

The configured key is not stored in adapter metadata; literal occurrences in saved inputs or returned output are checked. This narrowly scoped check does not detect other secrets, transformed credentials or sensitive prompt content. Suite text and accepted raw responses are retained without automatic deletion. Inspect artifacts and endpoint policies before sending or sharing sensitive material.

## 7. Related work and references

Blackbox Lens combines a focused workflow and transparent reporting. It does not introduce behavioral testing, option-order robustness testing or a new interpretability method. The related tools are intellectual context, not runtime dependencies:

- Marco Tulio Ribeiro, Tongshuang Wu, Carlos Guestrin and Sameer Singh. **Beyond Accuracy: Behavioral Testing of NLP Models with CheckList.** ACL 2020. [Paper and metadata](https://aclanthology.org/2020.acl-main.442/).
- Melanie Sclar, Yejin Choi, Yulia Tsvetkov and Alane Suhr. **Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design or: How I learned to start worrying about prompt formatting.** ICLR 2024. [Primary paper](https://arxiv.org/abs/2310.11324).
- Chujie Zheng, Hao Zhou, Fandong Meng, Jie Zhou and Minlie Huang. **Large Language Models Are Not Robust Multiple Choice Selectors.** ICLR 2024. [Primary paper](https://arxiv.org/abs/2309.03882).
- Miles Turpin, Julian Michael, Ethan Perez and Samuel R. Bowman. **Language Models Don't Always Say What They Think: Unfaithful Explanations in Chain-of-Thought Prompting.** NeurIPS 2023. [Primary paper](https://arxiv.org/abs/2305.04388).
- **Inspect:** general evaluation components, scoring and log inspection. [Official project documentation](https://inspect.aisi.org.uk/).
