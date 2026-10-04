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

如果服务要求另一参数，可使用 `--token-parameter max_completion_tokens`。`--no-auth` 仅允许本机回环端点；远程端点要求 HTTPS 和密钥。`temperature=0` 不保证模型输出确定性。每次调用使用新会话，不自动重试或跟随重定向；超过请求预算的计划在执行前被拒绝，默认预算为 100 次。

Prompts are sent to the configured endpoint. Artifacts retain the suite, configuration and bounded raw responses; there is no automatic deletion. The configured API key is excluded from metadata and checked for literal appearances in inputs/outputs, but this is not a general secret detector. Keep unrelated credentials and sensitive data out of suites, inspect artifacts before sharing, and avoid placing real keys in shell history.

提示会发送到所配置的端点。产物保留测试集、配置和有长度限制的原始响应，不会自动删除。工具不将配置密钥写入元数据，并检查其字面值是否出现在输入或输出中，但无法检测其他敏感信息。请勿将其他凭据放入测试集，分享前检查产物，并避免将真实密钥留在命令历史中。

## Reports and reanalysis / 报告与重新分析

| Artifact | Purpose / 用途 |
| --- | --- |
| `manifest.json` | Suite, adapter metadata and planned execution / 测试集、适配器元数据和运行计划 |
| `observations.jsonl` | Recorded response slots / 已记录的响应槽位 |
| `report.json` | Counts, denominators and computed metrics / 计数、分母和计算指标 |
| `report.html` | Standalone report for inspection / 可独立打开的检查报告 |

```sh
blackbox-lens analyze demo-run --out demo-analysis
```

Reanalysis recomputes the report from saved artifacts and writes JSON/HTML reports to a new directory, preserving the source run. It does not copy the raw run into that directory. Invalid manifests or observation records are rejected. Missing planned results remain visible rather than disappearing from the denominator.

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

`OpenAICompatible(base_url, model, api_key=..., timeout=30, max_tokens=32, token_parameter="max_tokens")` provides the live adapter. The same suite validation and output-directory rules apply to the API.

`OpenAICompatible(...)` 提供在线适配器；Python 接口遵循相同的测试集校验和新输出目录规则。

## Development / 开发

Current validation covers offline synthetic fixtures and local mock HTTP endpoints, including installed-package tests. **No real authenticated provider run or empirical model validation has been performed yet.**

当前验证覆盖离线模拟数据、本机模拟 HTTP 端点与已安装包测试。**尚未对真实、已认证的模型服务进行调用验证，也尚未开展实证模型评估。**

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
```

See [method definitions and primary references](docs/METHODOLOGY.md). Related projects such as [CheckList](https://aclanthology.org/2020.acl-main.442/), [FormatSpread](https://arxiv.org/abs/2310.11324), and [Inspect](https://inspect.aisi.org.uk/) cover established behavioral testing, format sensitivity, and broader evaluation infrastructure. This project offers a small, focused workflow; it does not claim a new interpretability technique.

相关项目已建立行为测试、格式敏感性分析和通用评估基础设施。本项目提供聚焦的小型实验流程，不声称提出新的可解释性技术。

Released under the [MIT License](LICENSE). / 本项目采用 [MIT 许可证](LICENSE)。
