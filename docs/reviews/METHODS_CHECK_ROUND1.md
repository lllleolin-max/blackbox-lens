# Round 1 method sanity audit

- Candidate: `92e57271df26ff5a96de85d563a7739c8b733f68`.
- Reviewed on: 2026-10-05.
- Scope: committed demo, metric definitions and report labels; read-only product review. Overall scoring and security/schema probes belong to the independent auditor.
- Artifacts: `root-round1-demo/manifest.json`, `observations.jsonl`, `report.json`, `report.html` from the root agent's installed-wheel run. The saved suite is identical to the committed bundled demo.
- Product writes: none. This report is the only file written during this audit.

## Conclusion

The checked demo semantics and metric arithmetic are sound. No scientific-method or denominator blocker was found. One minor standalone-report clarification would make the existing pooled grouping easier to interpret; it does not require changing the numeric results. This audit assigns no overall score and does not treat synthetic results as empirical model validation.

## Passed checks and evidence

| Check | Evidence |
| --- | --- |
| Ground truth remains fixed | The three cases ask 2+2, France's capital, and 3×3. All paraphrases preserve those questions; irrelevant context adds no answer-relevant fact; option-order variants only reverse choice contents. The hints report an unsupported previous suggestion, leaving the actual correct answer unchanged. Semantic answers remain `four`, `paris`, and `nine`. |
| Exact-prompt control | For each of the three cases, baseline and `control` prompt strings and answer maps are exactly equal. The demo therefore has genuine unchanged-input controls. |
| Option-order mapping | Every reordered prompt swaps the displayed A/B meanings and swaps the map values accordingly. A retained A response correctly becomes the wrong semantic answer after reordering; comparisons operate on semantic IDs. |
| Raw scoring reconciliation | An independent script read 54 observation lines without importing the product. Re-mapping the raw labels with the committed maps yields 54 valid responses and 36 correct, matching both JSON totals and HTML cards. Invalid/error/missing counts are all zero. |
| Accuracy denominators | Strict and valid accuracy both equal `36/54 = 2/3`. Each kind has nine slots. Baseline, control, paraphrase and irrelevant-context are 9/9 correct; option-order and misleading-hint are 0/9. |
| Paired comparisons | Each nonbaseline kind has nine planned, observed and eligible pairs, with zero exclusions. Order/hint each have nine flips and nine correct-to-incorrect transitions; control/paraphrase/context each have zero flips and nine both-correct pairs. |
| Repeat-pair arithmetic | Each kind contains three case/variant conditions with three repeats. Its denominator is `3 × choose(3,2) = 9`, not nine independent trials. All nine pairs agree in this deliberately deterministic fixture. The JSON and HTML agree. |
| Pooling matches the written contract | Source totals by kind, pooling pair counts across cases/variants. Repeat disagreement divides total disagreeing valid pairs by total valid pairs. METHODOLOGY explicitly documents this weighting rather than implying equal-weight case averages. |
| Parsing and missingness interpretation | The report explains exact-label parsing after surrounding whitespace stripping, valid-only pair eligibility, invalid/error/missing exclusions and N/A for zero denominators. Its known-error count conventions agree with the method contract. This all-valid fixture alone does not test mixed-failure behavior; the independent auditor owns those probes. |
| Claim limits | The HTML prominently states that the fixture reads expected answers and plants biases, and is not a language-model measurement. It describes repeat pairs as dependent and disclaims inferential, causal and generalization conclusions. README separately states that real authenticated providers and empirical model behavior remain unvalidated. |

For the repeat formula, an independent arithmetic sanity example with valid answers A,A,B has three unordered pairs, two disagreements and rate 2/3. With A,A,invalid, only one of three planned pairs is eligible and disagreement is zero; the valid-pair coverage must accompany that zero. These are mathematical definition checks, not claims of additional product execution.

## One actionable clarity finding

**[P3] Label the standalone tables as pooled variant-kind summaries and explain their weighting.**

The response, baseline-contrast and repetition tables all use the first-column heading `Condition`, but their rows are `baseline`, `control`, `paraphrase`, etc., each pooled across the three cases. The repeat row shows three eligible conditions and nine valid pairs. Its nearby paragraph explains comparisons within a case/variant but does not explicitly state how those comparisons are then pooled. See committed `src/blackbox_lens/report.py` lines 70, 72 and 74 for the headers, and line 73 for the paragraph beginning `Within each case and variant`; the rendered root HTML shows the same wording. METHODOLOGY already supplies the correct explanation.

Suggested change: name those columns `Variant kind (pooled)` or equivalent and add: “Rows sum counts across case/variant conditions of the same kind. Rates divide pooled eligible counts; they are not averages of per-case percentages. A repeat condition is one case and variant, and conditions with more valid repeat pairs receive more weight.” This helps someone reading the standalone report without the repository docs. No computed field needs changing.

No further issue is inferred merely because additional versions are desired. The candidate's other checked method claims are appropriately bounded.

## Source grounding

The source references support the scope actually claimed by the project:

- [CheckList, ACL 2020](https://aclanthology.org/2020.acl-main.442/) establishes behavioral test types including invariance and directional expectations. The project acknowledges prior work and limits v1 to fixed-ground-truth cases.
- [Sclar et al., ICLR 2024](https://arxiv.org/abs/2310.11324) studies prompt-format sensitivity. The docs do not present this small authored suite as a replication of FormatSpread or a comprehensive format-space estimate.
- [Zheng et al., ICLR 2024](https://arxiv.org/abs/2309.03882) studies option-ID/position sensitivity. Canonical semantic mapping is an appropriate safeguard for the comparisons here.
- [Turpin et al., NeurIPS 2023](https://arxiv.org/html/2305.04388v2) motivates caution about explanation faithfulness. The docs explicitly say this exact-label tool does not evaluate rationales or prove faithfulness.
- [Inspect official documentation](https://inspect.aisi.org.uk/) supports the comparison to broader evaluation infrastructure. The project claims a focused workflow rather than methodological novelty.

These primary URLs were read and verified during the preceding source review on 2026-10-05. The report makes no first-of-its-kind claim and does not attribute its synthesized metric definitions verbatim to the cited papers.
