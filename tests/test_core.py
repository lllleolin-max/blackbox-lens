from __future__ import annotations

import copy
import json
from itertools import permutations
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from blackbox_lens import Reply, Suite, SuiteError, SyntheticAdapter, analyze_run, create_plan, run_suite
from blackbox_lens.cli import demo_suite
from blackbox_lens.suite import MAX_RAW_CHARS, decode_json


def small_suite() -> Suite:
    value = demo_suite().to_dict()
    value["cases"] = value["cases"][:1]
    value["cases"][0]["variants"] = [value["cases"][0]["variants"][0], value["cases"][0]["variants"][4]]
    return Suite.from_dict(value)


class FixedAdapter:
    metadata = {"kind": "test-fixture"}

    def __init__(self, answers=None):
        self.answers = answers or {}
        self.calls = []

    def respond(self, trial):
        self.calls.append(trial.id)
        return self.answers.get(trial.id, Reply(raw="A"))


class SuiteTests(unittest.TestCase):
    def test_mapping_canonical_identity(self):
        suite = small_suite()
        case = suite.cases[0]
        self.assertEqual(case.variants[0].answer_map["A"], "four")
        self.assertEqual(case.variants[1].answer_map["A"], "five")

    def test_reject_bad_suite_fields(self):
        for mutation in (
            lambda x: x.update(extra=1),
            lambda x: x.update(schema_version=True),
            lambda x: x.update(cases=[]),
            lambda x: x["cases"][0].update(expected="unknown"),
            lambda x: x["cases"][0].update(canonical_labels=["four", "four"]),
            lambda x: x["cases"][0]["variants"][0].update(kind="control"),
            lambda x: x["cases"][0]["variants"][0].update(prompt=""),
            lambda x: x["cases"][0]["variants"][0].update(prompt="x" * 32769),
            lambda x: x["cases"][0]["variants"][1].update(id="base"),
            lambda x: x["cases"][0]["variants"][1].update(answer_map={"A": "four", "B": "four"}),
            lambda x: x["cases"][0]["variants"][1].update(answer_map={"A A": "four", "B": "five"}),
        ):
            with self.subTest(mutation=mutation):
                value = small_suite().to_dict()
                mutation(value)
                with self.assertRaises(SuiteError):
                    Suite.from_dict(value)

    def test_strict_json(self):
        for text in ('{"a": 1, "a": 2}', '{"a": NaN}', '{"a": Infinity}', '{', 'null trailing'):
            with self.subTest(text=text), self.assertRaises(SuiteError):
                decode_json(text)

    def test_repeats_seed_and_cap(self):
        suite = small_suite()
        for repeats in (True, 0, -1, 101, 1.5):
            with self.subTest(repeats=repeats), self.assertRaises(SuiteError):
                create_plan(suite, repeats=repeats)
        for seed in (True, -1, 2**32, 1.5):
            with self.subTest(seed=seed), self.assertRaises(SuiteError):
                create_plan(suite, seed=seed)
        self.assertEqual([t.id for t in create_plan(suite)], [t.id for t in create_plan(suite)])
        self.assertNotEqual([t.id for t in create_plan(suite, seed=42)], [t.id for t in create_plan(suite, seed=43)])
        with self.assertRaises(SuiteError):
            create_plan(demo_suite(), repeats=100)

    def test_map_object_order_does_not_change_fixture(self):
        original = small_suite()
        changed = original.to_dict()
        for variant in changed["cases"][0]["variants"]:
            variant["answer_map"] = dict(reversed(list(variant["answer_map"].items())))
        reordered = Suite.from_dict(changed)
        self.assertEqual(original.sha256, reordered.sha256)
        a, b = create_plan(original), create_plan(reordered)
        self.assertEqual([SyntheticAdapter().respond(t) for t in a], [SyntheticAdapter().respond(t) for t in b])

    def test_three_choice_hint_stable_across_all_map_orders(self):
        value = small_suite().to_dict()
        case = value["cases"][0]
        case.update(expected="yes", canonical_labels=["yes", "no", "maybe"])
        case["variants"][1].update(kind="misleading-hint", id="hint")
        signatures, hints = set(), set()
        for items in permutations((("A", "yes"), ("B", "no"), ("C", "maybe"))):
            for variant in case["variants"]:
                variant["answer_map"] = dict(items)
                variant["prompt"] = "Choose yes. A: yes. B: no. C: maybe. Reply A, B or C."
            suite = Suite.from_dict(value)
            signatures.add(suite.sha256)
            trial = next(t for t in create_plan(suite, repeats=1) if t.variant.kind == "misleading-hint")
            reply = SyntheticAdapter().respond(trial)
            hints.add((reply.raw, trial.variant.answer_map[reply.raw]))
        self.assertEqual(len(signatures), 1)
        self.assertEqual(hints, {("B", "no")})


class RunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def run_fixture(self, adapter=None, repeats=3):
        return run_suite(small_suite(), adapter or FixedAdapter(), self.root / "run", repeats=repeats)

    def test_offline_demo_truth_and_controls(self):
        report = run_suite(demo_suite(), SyntheticAdapter(), self.root / "demo")
        self.assertEqual(report["counts"]["planned"], 54)
        self.assertEqual(report["counts"]["correct"], 36)
        self.assertEqual(report["counts"]["strict_accuracy"], 2 / 3)
        self.assertEqual(report["comparisons"]["control"]["invariance"], 1)
        self.assertEqual(report["comparisons"]["option-order"]["flip_rate"], 1)
        self.assertEqual(report["comparisons"]["misleading-hint"]["correct_to_incorrect"], 9)
        self.assertTrue(all(r["disagreement_rate"] == 0 for r in report["repeat_consistency"].values()))
        cases = report["manifest"]["suite"]["cases"]
        self.assertTrue(all(c["variants"][0]["prompt"] == c["variants"][1]["prompt"] for c in cases))

    def test_exact_label_no_extraction(self):
        answers = {"addition/base/1": Reply(raw=" \nA\t"), "addition/order/1": Reply(raw="B"),
                   "addition/base/2": Reply(raw="a"), "addition/order/2": Reply(raw="A or B"),
                   "addition/base/3": Reply(raw="Answer: A"), "addition/order/3": Reply(raw="")}
        report = self.run_fixture(FixedAdapter(answers))
        self.assertEqual(report["counts"]["valid"], 2)
        self.assertEqual(report["counts"]["invalid"], 4)
        self.assertEqual(report["counts"]["correct"], 2)
        p = report["comparisons"]["option-order"]
        self.assertEqual((p["valid_pairs"], p["excluded_pairs"], p["same"], p["flips"]), (1, 2, 1, 0))

    def test_mixed_directional_counts_and_repeat_disagreement(self):
        answers = {"addition/base/1": Reply(raw="A"), "addition/order/1": Reply(raw="A"),
                   "addition/base/2": Reply(raw="B"), "addition/order/2": Reply(raw="B"),
                   "addition/base/3": Reply(error="timeout"), "addition/order/3": Reply(raw="invalid")}
        report = self.run_fixture(FixedAdapter(answers))
        c = report["counts"]
        self.assertEqual((c["planned"], c["valid"], c["invalid"], c["errors"], c["correct"]), (6, 4, 1, 1, 2))
        self.assertEqual((c["strict_accuracy"], c["valid_accuracy"]), (1 / 3, 1 / 2))
        p = report["comparisons"]["option-order"]
        self.assertEqual((p["valid_pairs"], p["flips"], p["correct_to_incorrect"], p["incorrect_to_correct"]), (2, 2, 1, 1))
        self.assertEqual(report["repeat_consistency"]["baseline"]["disagreement_rate"], 1)

    def test_invariance_can_be_wrong(self):
        report = self.run_fixture(FixedAdapter({"addition/base/1": Reply(raw="B"), "addition/order/1": Reply(raw="A")}), repeats=1)
        pair = report["comparisons"]["option-order"]
        self.assertEqual((pair["invariance"], pair["both_incorrect"]), (1, 1))

    def test_missing_and_empty_comparisons(self):
        self.run_fixture()
        path = self.root / "run" / "observations.jsonl"
        path.write_text("", encoding="utf-8")
        report = analyze_run(self.root / "run", self.root / "new report 中文")
        self.assertFalse(report["complete"])
        self.assertEqual((report["counts"]["missing"], report["counts"]["strict_accuracy"]), (6, 0))
        self.assertIsNone(report["counts"]["valid_accuracy"])
        self.assertIsNone(report["comparisons"]["option-order"]["flip_rate"])
        self.assertIsNone(report["repeat_consistency"]["baseline"]["disagreement_rate"])

    def test_partial_missing_baseline_is_excluded(self):
        self.run_fixture()
        path = self.root / "run" / "observations.jsonl"
        values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        values = [v for v in values if v["trial_id"] != "addition/base/2"]
        path.write_text("\n".join(json.dumps(v) for v in values) + "\n", encoding="utf-8")
        p = analyze_run(self.root / "run")["comparisons"]["option-order"]
        self.assertEqual((p["planned_pairs"], p["observed_pairs"], p["valid_pairs"]), (3, 2, 2))

    def test_cache_not_trusted(self):
        expected = self.run_fixture()
        (self.root / "run" / "report.json").write_text('{"correct": 999}', encoding="utf-8")
        self.assertEqual(expected, analyze_run(self.root / "run"))

    def test_unknown_duplicate_or_corrupt_observation_rejected(self):
        self.run_fixture()
        path = self.root / "run" / "observations.jsonl"
        original = path.read_text(encoding="utf-8")
        first = json.loads(original.splitlines()[0])
        alternatives = [original + original.splitlines()[0] + "\n"]
        for update in ({"trial_id": "addition/base/4"}, {"trial_id": "other/base/1"},
                       {"duration_ms": float("nan")}, {"duration_ms": True},
                       {"error": "secret error", "raw": None}, {"raw": "X" * (MAX_RAW_CHARS + 1)},
                       {"error": "timeout", "raw": "A"}, {"extra": 1}):
            changed = dict(first, **update)
            alternatives.append(json.dumps(changed) + "\n")
        for content in alternatives:
            with self.subTest(content=content[:80]):
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(SuiteError):
                    analyze_run(self.root / "run")

    def test_manifest_count_digest_schema_seed_tampering(self):
        self.run_fixture()
        path = self.root / "run" / "manifest.json"
        original = json.loads(path.read_text(encoding="utf-8"))
        for update in ({"order": original["order"][:-1]}, {"order": list(reversed(original["order"]))},
                       {"suite_sha256": "0" * 64}, {"schema_version": 2}, {"repeats": True}, {"seed": -1}):
            path.write_text(json.dumps(dict(original, **update)), encoding="utf-8")
            with self.subTest(update=update), self.assertRaises(SuiteError):
                analyze_run(self.root / "run")

    def test_invalid_manifest_json_metadata_has_bounded_sdk_cli_errors(self):
        self.run_fixture()
        path = self.root / "run" / "manifest.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["adapter"] = "BADMETADATA"
        template = json.dumps(value)
        for index, metadata in enumerate(('{"x": 1e999}', '{"name": "\\ud800"}', '{"\\ud800": "value"}')):
            with self.subTest(metadata=metadata):
                path.write_text(template.replace('"BADMETADATA"', metadata), encoding="utf-8")
                out = self.root / f"invalid-analysis-{index}"
                with self.assertRaises(SuiteError):
                    analyze_run(self.root / "run", out)
                result = subprocess.run([sys.executable, "-m", "blackbox_lens", "analyze", str(self.root / "run"),
                                         "--out", str(out)], capture_output=True, text=True, cwd=self.root)
                self.assertEqual(result.returncode, 2)
                self.assertTrue(result.stderr.startswith("Error:"), result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse(out.exists())

    def test_pooled_report_labels_and_weighting_are_explicit(self):
        self.run_fixture()
        html = (self.root / "run" / "report.html").read_text(encoding="utf-8")
        self.assertEqual(html.count("<th>Variant kind (pooled)</th>"), 3)
        self.assertIn("<th>Total conditions</th>", html)
        self.assertIn("rates divide pooled valid-pair counts", html)
        self.assertIn("disagreement divides pooled disagreeing pairs by pooled valid pairs", html)
        self.assertIn("A condition is one case and variant", html)

    def test_exclusive_outputs_and_request_cap(self):
        directory = self.root / "already exists"
        directory.mkdir()
        sentinel = directory / "sentinel"
        sentinel.write_text("keep")
        adapter = FixedAdapter()
        with self.assertRaises(SuiteError):
            run_suite(small_suite(), adapter, directory)
        with self.assertRaises(SuiteError):
            run_suite(small_suite(), adapter, self.root / "no-run", max_requests=1)
        self.assertEqual(sentinel.read_text(), "keep")
        self.assertEqual(adapter.calls, [])
        self.assertFalse((self.root / "no-run").exists())

    def test_adapter_exception_and_oversize_are_not_success(self):
        class Broken(FixedAdapter):
            def respond(self, trial):
                if trial.variant.kind == "baseline":
                    raise RuntimeError("do not copy this secret exception")
                return Reply(raw="A" * (MAX_RAW_CHARS + 1))
        report = self.run_fixture(Broken(), repeats=1)
        self.assertEqual(report["counts"]["errors"], 2)
        self.assertEqual(report["counts"]["correct"], 0)
        self.assertNotIn("secret exception", (self.root / "run" / "observations.jsonl").read_text())

    def test_interrupt_preserves_incomplete_artifacts(self):
        class Interrupted(FixedAdapter):
            def respond(self, trial):
                if self.calls:
                    raise KeyboardInterrupt
                self.calls.append(trial.id)
                return Reply(raw="A")
        with self.assertRaises(KeyboardInterrupt):
            self.run_fixture(Interrupted())
        report = analyze_run(self.root / "run")
        self.assertEqual((report["counts"]["observed"], report["counts"]["missing"]), (1, 5))
        self.assertTrue((self.root / "run" / "report.html").exists())

    def test_html_is_escaped_and_network_free(self):
        value = small_suite().to_dict()
        attack = '</script><img src="https://evil.test/x" onerror="alert(1)"><svg/onload=alert(1)>'
        value["title"] = attack
        value["description"] = attack
        value["cases"][0]["variants"][0]["prompt"] = attack
        run_suite(Suite.from_dict(value), FixedAdapter({"addition/base/1": Reply(raw=attack)}), self.root / "safe", repeats=1)
        html = (self.root / "safe" / "report.html").read_text(encoding="utf-8")
        tags = []
        class Tags(HTMLParser):
            def handle_starttag(self, tag, attrs):
                tags.append(tag)
        Tags().feed(html)
        self.assertFalse({"script", "img", "svg", "iframe", "link"} & set(tags))
        self.assertIn("&lt;/script&gt;", html)
        self.assertIn("default-src 'none'", html)

    def test_cli_installed_package_flow(self):
        out = self.root / "cli path 中文"
        result = subprocess.run([sys.executable, "-m", "blackbox_lens", "demo", "--out", str(out)],
                                cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run([sys.executable, "-m", "blackbox_lens", "analyze", str(out), "--out", str(self.root / "recompute")],
                                cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
