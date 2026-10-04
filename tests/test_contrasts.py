from __future__ import annotations

import json
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from blackbox_lens import Reply, Suite, SyntheticAdapter, analyze_run, run_suite
from blackbox_lens.cli import demo_suite
from test_core import FixedAdapter, small_suite

COUNT_FIELDS = ("planned_pairs", "observed_pairs", "valid_pairs", "excluded_pairs", "same", "flips",
                "correct_to_incorrect", "incorrect_to_correct", "both_correct", "both_incorrect")


class ContrastTable(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.links, self.ids = [], [], []
        self.heading = ""
        self.in_heading = self.in_table = self.in_cell = False
        self.section = False
        self.row, self.cell = [], []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.ids.append(values["id"])
        if tag == "h2":
            self.heading, self.in_heading = "", True
        if tag == "table" and self.section:
            self.in_table = True
        if self.in_table:
            if tag == "tr":
                self.row = []
            if tag == "td":
                self.cell, self.in_cell = [], True
            if tag == "a":
                self.links.append(values["href"])

    def handle_endtag(self, tag):
        if tag == "h2":
            self.in_heading = False
            self.section = self.heading == "Case and variant contrasts"
        if self.in_table:
            if tag == "td":
                self.row.append("".join(self.cell))
                self.in_cell = False
            if tag == "tr" and self.row:
                self.rows.append(self.row)
            if tag == "table":
                self.in_table = False

    def handle_data(self, data):
        if self.in_heading:
            self.heading += data
        if self.in_cell:
            self.cell.append(data)


class ContrastTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def mixed_run(self):
        suite = Suite.from_dict({"schema_version": 1, "title": "Mixed coverage contrasts", "description": "Test fixture",
            "cases": [{"id": cid, "expected": "red", "canonical_labels": ["red", "blue"],
                "variants": [{"id": vid, "kind": kind, "prompt": prompt, "answer_map": {"A": "red", "B": "blue"}}
                             for vid, kind, prompt in (
                                 ("base", "baseline", "Select red. A: red. B: blue. Reply A or B."),
                                 ("p1", "paraphrase", "Choose red. A: red. B: blue. Reply A or B."),
                                 ("p2", "paraphrase", "Pick red. A: red. B: blue. Reply A or B."))]}
                      for cid in ("alpha", "beta")]})
        answers = {"alpha/p1/2": Reply(raw="B"), "alpha/p2/1": Reply(raw="B"),
                   "alpha/p2/2": Reply(raw="not a label"), "beta/base/1": Reply(raw="B"),
                   "beta/p1/2": Reply(error="timeout"), "beta/p2/1": Reply(raw="not a label"),
                   "beta/p2/2": Reply(error="http_error")}
        run = self.root / "mixed"
        run_suite(suite, FixedAdapter(answers), run, repeats=3)
        path = run / "observations.jsonl"
        missing = {"alpha/base/3", "alpha/p2/3", "beta/p2/3"}
        observed = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        path.write_text("".join(json.dumps(v) + "\n" for v in observed if v["trial_id"] not in missing), encoding="utf-8")
        return analyze_run(run, self.root / "analyzed")

    def test_mixed_case_rows_and_pooled_counts_reconcile(self):
        report = self.mixed_run()
        c = report["counts"]
        self.assertEqual((c["planned"], c["valid"], c["invalid"], c["errors"], c["missing"], c["correct"]),
                         (18, 11, 2, 2, 3, 8))
        rows = report["case_contrasts"]
        self.assertEqual([(r["case_id"], r["variant_id"], r["baseline_variant_id"], r["kind"]) for r in rows],
                         [("alpha", "p1", "base", "paraphrase"), ("alpha", "p2", "base", "paraphrase"),
                          ("beta", "p1", "base", "paraphrase"), ("beta", "p2", "base", "paraphrase")])
        expected = [(3, 2, 2, 1, 1, 1, 1, 0, 1, 0), (3, 2, 1, 2, 0, 1, 1, 0, 0, 0),
                    (3, 3, 2, 1, 1, 1, 0, 1, 1, 0), (3, 2, 0, 3, 0, 0, 0, 0, 0, 0)]
        self.assertEqual([tuple(r[k] for k in COUNT_FIELDS) for r in rows], expected)
        self.assertEqual([r["coverage"] for r in rows], [2 / 3, 1 / 3, 2 / 3, 0])
        self.assertEqual([r["invariance"] for r in rows], [1 / 2, 0, 1 / 2, None])
        self.assertEqual([r["flip_rate"] for r in rows], [1 / 2, 1, 1 / 2, None])
        pooled = report["comparisons"]["paraphrase"]
        self.assertEqual(tuple(pooled[k] for k in COUNT_FIELDS), (12, 9, 5, 7, 2, 3, 2, 1, 2, 0))
        self.assertEqual((pooled["coverage"], pooled["invariance"], pooled["flip_rate"]), (5 / 12, 2 / 5, 3 / 5))
        for field in COUNT_FIELDS:
            self.assertEqual(sum(r[field] for r in rows), pooled[field])
        for row in rows:
            self.assertEqual(row["same"] + row["flips"], row["valid_pairs"])
            self.assertEqual(sum(row[k] for k in COUNT_FIELDS[6:]), row["valid_pairs"])
            self.assertEqual(row["valid_pairs"] + row["excluded_pairs"], row["planned_pairs"])

    def test_html_matches_mixed_json_and_uses_only_valid_fragment_links(self):
        self.mixed_run()
        parser = ContrastTable()
        parser.feed((self.root / "analyzed" / "report.html").read_text(encoding="utf-8"))
        self.assertEqual(parser.rows, [
            ["alpha", "base", "p1", "paraphrase", "2 / 3", "1", "1", "50.0%", "1", "0"],
            ["alpha", "base", "p2", "paraphrase", "1 / 3", "2", "1", "100.0%", "1", "0"],
            ["beta", "base", "p1", "paraphrase", "2 / 3", "1", "1", "50.0%", "0", "1"],
            ["beta", "base", "p2", "paraphrase", "0 / 3", "3", "0", "N/A", "0", "0"]])
        self.assertEqual(len(parser.links), 12)
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        self.assertTrue(all(link.startswith("#") and link[1:] in parser.ids for link in parser.links))

    def test_demo_breakdown_order_and_all_kind_sums(self):
        report = run_suite(demo_suite(), SyntheticAdapter(), self.root / "demo")
        rows = report["case_contrasts"]
        self.assertEqual(len(rows), 15)
        expected_ids = [(c.id, v.id) for c in demo_suite().cases for v in c.variants if v.kind != "baseline"]
        self.assertEqual([(r["case_id"], r["variant_id"]) for r in rows], expected_ids)
        for row in rows:
            self.assertEqual((row["planned_pairs"], row["valid_pairs"], row["excluded_pairs"]), (3, 3, 0))
            self.assertEqual(row["flips"], 3 if row["kind"] in {"option-order", "misleading-hint"} else 0)
        for kind, pooled in report["comparisons"].items():
            for field in COUNT_FIELDS:
                self.assertEqual(sum(r[field] for r in rows if r["kind"] == kind), pooled[field])

    def test_reanalysis_of_v1_artifacts_ignores_old_cached_report_shape(self):
        run = self.root / "old-shape"
        report = run_suite(small_suite(), SyntheticAdapter(), run)
        manifest_before = (run / "manifest.json").read_bytes()
        observations_before = (run / "observations.jsonl").read_bytes()
        report.pop("case_contrasts")
        report["counts"]["correct"] = 999
        (run / "report.json").write_text(json.dumps(report), encoding="utf-8")
        recalculated = analyze_run(run)
        self.assertEqual(recalculated["counts"]["correct"], 3)
        self.assertEqual(len(recalculated["case_contrasts"]), 1)
        self.assertEqual(recalculated["case_contrasts"][0]["flips"], 3)
        self.assertEqual((run / "manifest.json").read_bytes(), manifest_before)
        self.assertEqual((run / "observations.jsonl").read_bytes(), observations_before)

    def test_hyphenated_identifiers_do_not_collide_in_fragment_targets(self):
        value = small_suite().to_dict()
        original = value["cases"][0]
        cases = []
        for cid, vid in (("a-b", "c"), ("a", "b-c")):
            case = dict(original, id=cid, variants=[dict(v) for v in original["variants"]])
            case["variants"][1]["id"] = vid
            cases.append(case)
        value["cases"] = cases
        run_suite(Suite.from_dict(value), SyntheticAdapter(), self.root / "anchors", repeats=1)
        parser = ContrastTable()
        parser.feed((self.root / "anchors" / "report.html").read_text(encoding="utf-8"))
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        self.assertIn("#condition-3-a-b-c", parser.links)
        self.assertIn("#condition-1-a-b-c", parser.links)
        self.assertTrue(all(link[1:] in parser.ids for link in parser.links))


if __name__ == "__main__":
    unittest.main()
