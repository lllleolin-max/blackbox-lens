# Blackbox Lens

Small, inspectable experiments for language-model behavior: change a prompt, keep its correct answer fixed, repeat the calls, and compare semantic answers with explicit controls.

一个轻量、可核查的语言模型行为实验工具：保持正确答案不变，对提示做明确改动，加入对照并重复调用，观察语义答案、正确率和运行失败情况。

Blackbox Lens measures input–output behavior. Its reports help identify cases worth investigating; they do not expose hidden reasoning or establish general model reliability. The methodology builds on [CheckList](https://aclanthology.org/2020.acl-main.442/) and prior work on [prompt-format sensitivity](https://arxiv.org/abs/2310.11324).

## What you can test / 可以测试什么

- **Prompt sensitivity / 提示敏感性:** authored paraphrases, irrelevant context, option reordering, and misleading hints, each paired with the same case's baseline.
- **Controls / 对照:** identical prompts can reveal ordinary response variability alongside the intervention results.
- **Repeatability / 重复一致性:** semantic disagreement across repeated calls to the same prompt.
- **Correctness and availability / 正确性与可用性:** correct, incorrect, invalid, error, and missing results with visible denominators.

Runs produce JSON artifacts and a standalone HTML report. The runtime uses Python's standard library; no model SDK or plotting package is required.

运行结果包含 JSON 数据与独立 HTML 报告；运行时只使用 Python 标准库，不依赖模型 SDK 或绘图库。

## Quickstart / 快速开始

Requires Python 3.11 or newer. From the repository directory:

需要 Python 3.11 或更新版本。在仓库目录运行：

```sh
python -m pip install .
blackbox-lens demo --out demo-run --repeats 3 --seed 42
```

Open `demo-run/report.html`. Every output directory must be **new**; existing directories are rejected to preserve earlier artifacts.

打开 `demo-run/report.html`。输出目录必须尚不存在；工具拒绝覆盖已有目录，以保留先前的实验产物。

The bundled demo uses `SyntheticAdapter`, which reads the expected answers and deliberately plants option-position and hint biases. It tests the experiment pipeline and report, **not a real model**. A stable synthetic run is not evidence of live-model repeatability.

内置演示使用 `SyntheticAdapter`：它读取标准答案，并人为加入选项位置与误导提示偏差。演示用于检查流程和报告，不代表真实模型表现。

With the defaults above, the fixture produces 3 cases × 6 conditions × 3 repeats: **54 valid responses, 36 correct (66.7%)**, with no errors or missing slots. Option-order and misleading-hint conditions each flip in 9/9 pairs; control, paraphrase and irrelevant-context conditions each flip in 0/9. Every condition has zero repeated-answer disagreement. These outcomes are intentionally encoded in the fixture.

以上默认配置产生 **54 个有效响应，36 个正确答案（66.7%）**，没有错误或缺失。选项调序与误导提示各翻转 9/9 对；对照、改写和无关上下文各翻转 0/9 对；所有条件的重复答案分歧为零。这些结果是模拟器预设的行为。

## Author a suite / 编写测试集

Save the following as `suite.json`. `expected` is a stable semantic ID; each `answer_map` translates the response label into that ID. After reordering the choices, returning `B` still means `paris`.

将下列内容保存为 `suite.json`。`expected` 是稳定的语义标识，`answer_map` 将模型输出标签映射到该标识；选项调序后，输出 `B` 仍表示 `paris`。

```json
{
  "schema_version": 1,
  "title": "Capital choice control",
  "description": "All variants preserve the same correct semantic answer.",
  "cases": [
    {
      "id": "france-capital",
      "expected": "paris",
      "canonical_labels": ["paris", "rome"],
      "variants": [
        {
          "id": "original",
          "kind": "baseline",
          "prompt": "What is the capital of France? A: Paris. B: Rome. Reply A or B.",
          "answer_map": {"A": "paris", "B": "rome"}
        },
        {
          "id": "unchanged",
          "kind": "control",
          "prompt": "What is the capital of France? A: Paris. B: Rome. Reply A or B.",
          "answer_map": {"A": "paris", "B": "rome"}
        },
        {
          "id": "reordered",
          "kind": "option-order",
          "prompt": "What is the capital of France? A: Rome. B: Paris. Reply A or B.",
          "answer_map": {"A": "rome", "B": "paris"}
        }
      ]
    }
  ]
}
```

```sh
blackbox-lens plan suite.json --repeats 3 --seed 42
```

This example plans nine response slots. Supported kinds are `baseline`, `control`, `paraphrase`, `irrelevant-context`, `option-order`, and `misleading-hint`. Each case requires exactly one baseline and at least one other variant. Every answer map must be a bijection onto the case's canonical labels. Output matching strips boundary whitespace and otherwise requires an exact label; explanations are invalid responses.

此例安排 9 个响应槽位。每个案例必须含一个基线和至少一个其他变体；所有答案映射必须完整且一一对应。评分只去除输出首尾空白，随后精确匹配标签；附加解释会被记为无效响应。

**Version 1 requires the correct semantic answer to stay fixed across every variant.** Schema checks cannot establish that equivalence: review your prompts before running. Changes to facts or negation that change the correct answer need a different experimental contract. See [the methodology](docs/METHODOLOGY.md).

**第 1 版要求同一案例的所有变体保持正确语义答案不变。** 格式校验无法证明这一点，运行前需要审阅提示；改变事实或否定关系、从而改变正确答案的实验不适用于当前契约。

## Run against an endpoint / 调用模型端点

The live adapter uses the nonstreaming `/chat/completions` subset of an OpenAI-compatible API. The endpoint and model below are placeholders. Configure a provider you trust and its supported token-limit parameter.

在线适配器使用兼容 OpenAI API 的非流式 `/chat/completions` 接口。下方端点、模型和密钥均为占位值，请替换为自己的服务配置。

Bash:

```bash
export OPENAI_API_KEY='YOUR_API_KEY'
blackbox-lens run suite.json --out live-run \
  --base-url https://api.example.com/v1 --model YOUR_MODEL \
  --key-env OPENAI_API_KEY --timeout 30 --max-tokens 32 \
  --token-parameter max_tokens --max-requests 100
```

PowerShell:

```powershell
$env:OPENAI_API_KEY = 'YOUR_API_KEY'
blackbox-lens run suite.json --out live-run `
  --base-url https://api.example.com/v1 --model YOUR_MODEL `
  --key-env OPENAI_API_KEY --timeout 30 --max-tokens 32 `
  --token-parameter max_tokens --max-requests 100
```

Use `--token-parameter max_completion_tokens` if your endpoint requires it. `--no-auth` is available only for a loopback endpoint such as `http://127.0.0.1:8000/v1`. Remote endpoints require HTTPS and an API key. The adapter sets `temperature=0`; that does not guarantee deterministic provider responses. It sends fresh conversations and performs no retries or redirects. Plans exceeding the request budget are rejected before execution; the default budget is 100 requests.

For DeepSeek, pass `--thinking enabled --reasoning-effort high` or `--thinking disabled` explicitly. Enabled thinking omits `temperature`, which the provider documents as ineffective in that mode; disabled thinking sends zero. The default token budget is 4096 with explicitly enabled thinking and 32 otherwise. Use the same explicit budget when comparing modes. These are optional provider extensions; model identifiers are supplied by the caller, with no alias or price assumptions. See the [official thinking-mode documentation](https://api-docs.deepseek.com/guides/thinking_mode/) (checked 2026-10-05).

如果服务要求另一参数，可使用 `--token-parameter max_completion_tokens`。`--no-auth` 仅允许本机回环端点；远程端点要求 HTTPS 和密钥。`temperature=0` 不保证模型输出确定性。每次调用使用新会话，不自动重试或跟随重定向；超过请求预算的计划在执行前被拒绝，默认预算为 100 次。

Prompts are sent to the configured endpoint. Artifacts retain the suite, configuration and bounded raw responses; there is no automatic deletion. The configured API key is excluded from metadata and checked for literal appearances in inputs/outputs, but this is not a general secret detector. Keep unrelated credentials and sensitive data out of suites, inspect artifacts before sharing, and avoid placing real keys in shell history.

提示会发送到所配置的端点。产物保留测试集、配置和有长度限制的原始响应，不会自动删除。工具不将配置密钥写入元数据，并检查其字面值是否出现在输入或输出中，但无法检测其他敏感信息。请勿将其他凭据放入测试集，分享前检查产物，并避免将真实密钥留在命令历史中。

## Reports and reanalysis / 报告与重新分析

| Artifact | Purpose / 用途 |
| --- | --- |
| `manifest.json` | Suite, adapter metadata and planned execution / 测试集、适配器元数据和运行计划 |
| `observations.jsonl` | Recorded response slots / 已记录的响应槽位 |
| `calls/*.json` | Digest-linked sanitized per-call evidence, including failed provider responses / 含失败响应的逐次调用记录 |
| `report.json` | Counts, denominators and computed metrics / 计数、分母和计算指标 |
| `report.html` | Standalone report for inspection / 可独立打开的检查报告 |

`report.json` includes `case_contrasts`: one row for each declared case and nonbaseline variant, identifying its baseline and showing paired counts, coverage, invariance and flip rate. The HTML **Case and variant contrasts** section links case, baseline and variant identifiers to their declared prompts, so you can locate the input behind a change. Zero-flip and zero-eligible rows remain visible; rates with no valid pairs are N/A.

`report.json` 中的 `case_contrasts` 为每个案例与非基线变体提供一行记录，注明对应基线并展示配对计数、覆盖率、一致率和翻转率。HTML 的 **Case and variant contrasts** 部分将案例、基线和变体标识链接到原提示，便于定位变化来源。零翻转、零有效配对的行仍会保留；没有有效配对时，翻转率与一致率显示 N/A。

The pooled `comparisons` summaries sum these rows' integer counts by kind, then recompute rates from the pooled denominators; they do not average row percentages.

按变体类型汇总的 `comparisons` 先对这些行的整数计数求和，再用汇总分母计算比例，不对各行百分比取平均。

```sh
blackbox-lens analyze demo-run --out demo-analysis
```

Reanalysis recomputes the report from saved artifacts and writes JSON/HTML reports to a new directory, preserving the source run. It does not copy the raw run into that directory. Invalid manifests or observation records are rejected. Missing planned results remain visible rather than disappearing from the denominator.

Version 0.2 writes artifact schema 2 and continues to analyze schema-1 runs. Each observation links an exclusively created call record by SHA-256. Records include UTC start/end, client duration, the exact request JSON without authorization, HTTP status, returned ID/model/finish reason, final content, `reasoning_content`, and the full sanitized provider JSON (including all usage/cache/reasoning token fields when returned). Missing provider fields remain `null`, not invented zeros. `reasoning_content` is provider-returned text and is **not guaranteed privileged internal reasoning**. Error and truncated responses are retained with explicit status. The HTTP body limit is 1 MiB; an oversized body retains a flagged prefix and is an error. Final answers exceeding 4096 characters are also errors, with the received response preserved within the body limit. Call records have a 4 MiB serialization limit; rejected evidence is explicitly marked. Only successful, bounded final content enters exact-label scoring.

重新分析从已保存的产物重算 JSON/HTML 报告，写入新目录并保留源运行；原始运行不会复制到分析目录。不合法的记录会被拒绝。未记录的计划响应仍以缺失项显示，不会从分母中静默消失。

**Strict accuracy** is `correct / planned`; **valid accuracy** is `correct / valid`. Semantic flip rates use only pairs with two valid mapped answers. Repeated responses and shared baselines create dependence, so the report uses descriptive metrics without confidence intervals or significance tests. Read [METHODOLOGY.md](docs/METHODOLOGY.md) for definitions and limits.

**严格正确率**为 `正确 / 计划槽位`，**有效响应正确率**为 `正确 / 有效响应`。语义翻转率只使用两端均有效的配对。重复调用和复用基线会产生依赖，因此报告仅给出描述性指标，不输出置信区间或显著性检验。

## Python API / Python 接口

```python
from blackbox_lens import (
    SyntheticAdapter, analyze_run, create_plan, load_suite, run_suite,
)

suite = load_suite("suite.json")
plan = create_plan(suite, repeats=3, seed=42)
run_suite(
    suite, SyntheticAdapter(), "sdk-run",
    repeats=3, seed=42, max_requests=100,
)
report = analyze_run("sdk-run", out="sdk-analysis")
```

`OpenAICompatible(base_url, model, api_key=..., timeout=30, max_tokens=None, token_parameter="max_tokens", thinking=None, reasoning_effort=None)` provides the live adapter. Unspecified thinking preserves the original request shape and 32-token default. An explicit `thinking="enabled"` changes the default budget to 4096; `reasoning_effort` requires enabled thinking. The same suite validation and output-directory rules apply to the API.

## Paired DeepSeek study / 双模式实验

The reviewed suite and preregistered protocol are under [experiments/deepseek-2026-10-05](experiments/deepseek-2026-10-05/PROTOCOL.md). The source distribution includes that suite, answer key and the standard-library runner. Install this candidate first, then provide the credential through `DEEPSEEK_API_KEY` in the process environment:

```powershell
python tools/deepseek_batch.py experiments/deepseek-2026-10-05/suite.json `
  --out run-deepseek-20261005 --base-url https://api.deepseek.com `
  --model deepseek-flash --key-env DEEPSEEK_API_KEY --repeats 3 `
  --seed 20261005 --workers 4 --timeout 120 --max-tokens 4096 `
  --reasoning-effort high --max-requests 432
```

The batch manifest records all planned admissions before execution. Both modes use the same seeded trial plan; same-trial pairs alternate which mode is admitted first. Concurrency is limited to 1–4 workers; actual starts/completions may differ from admission order. `events.jsonl` records submissions, completions and stopping decisions. Raw records and observations are created or appended once; failed slots are never automatically retried. HTTP 401/402/403, a `length` finish, a response-size failure, three consecutive errors or ten cumulative errors stop further admissions. Already submitted calls finish and are retained. Error order is the completion-event order, and invalid labels reset consecutive error counts. Ctrl+C stops admission and waits for bounded in-flight requests; remaining planned slots stay missing. There is no resume support; analyze a partial run offline and use a separately preregistered new directory if a new attempt is warranted. Each mode has its own run artifacts and `analysis-{mode}` report directory; `batch-summary.json` records the stop reason and coverage.

`OpenAICompatible(...)` 提供在线适配器；Python 接口遵循相同的测试集校验和新输出目录规则。

## Development / 开发

Implementation validation covers offline synthetic fixtures and local mock HTTP endpoints, including installed-package tests. Live pilots and study results must be reported separately with their actual recorded scope; passing implementation tests does not establish empirical model reliability.

实现验证覆盖离线模拟数据、本机模拟 HTTP 端点与已安装包测试。在线试运行与正式实验应按实际记录单独报告；实现测试通过并不证明模型的一般可靠性。

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Audit trail / 审计记录

The [fixed rubric](docs/reviews/RUBRIC.md), [Round 1 review](docs/reviews/ROUND1.md) and [Round 2 review](docs/reviews/ROUND2.md) are historical v0.1.0 candidate audits, with stated tests, findings and limits. Their scope is delivery of that bounded prototype and its synthetic/local mock HTTP evidence. They do not audit the v0.2.0 DeepSeek extension or constitute independent human peer review or empirical validation of a real model.

[固定评分标准](docs/reviews/RUBRIC.md)、[第 1 轮审计](docs/reviews/ROUND1.md)和[第 2 轮审计](docs/reviews/ROUND2.md)记录了针对明确提交版本的 AI 审计及其测试、发现和范围限制。审计对象是本原型的交付质量及模拟、本机 HTTP 测试证据，不等同于独立人工同行评审或真实模型实证验证。

The published v0.1.0 [Round 3 release audit report](https://github.com/lllleolin-max/blackbox-lens/releases/download/v0.1.0/ROUND3.md) records that release's reviewed source SHA, decision and limitations. Read that report for the result applicable to v0.1.0; earlier reviews describe their own cited versions.

已发布的 v0.1.0 [第 3 轮发布审计报告](https://github.com/lllleolin-max/blackbox-lens/releases/download/v0.1.0/ROUND3.md)记录该版本的源码 SHA、结论和限制。请以该报告判断 v0.1.0 的结果；前两轮报告仅描述各自注明的历史版本，不代表 v0.2.0 扩展的审查结果。

See [method definitions and primary references](docs/METHODOLOGY.md). Related projects such as [CheckList](https://aclanthology.org/2020.acl-main.442/), [FormatSpread](https://arxiv.org/abs/2310.11324), and [Inspect](https://inspect.aisi.org.uk/) cover established behavioral testing, format sensitivity, and broader evaluation infrastructure. This project offers a small, focused workflow; it does not claim a new interpretability technique.

相关项目已建立行为测试、格式敏感性分析和通用评估基础设施。本项目提供聚焦的小型实验流程，不声称提出新的可解释性技术。

Released under the [MIT License](LICENSE). / 本项目采用 [MIT 许可证](LICENSE)。
